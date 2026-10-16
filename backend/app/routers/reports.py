from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..models import AVAILABLE, ISSUED, AuditLog, Book, Loan, Member, Payment, User
from ..schemas import LoanOut, MemberOut, PaymentOut
from ..services import (add_years, book_search_filter, calc_late, get_settings,
                        member_search_filter)

router = APIRouter(prefix="/api/reports", tags=["reports"], dependencies=[Depends(current_user)])


def _day_range(d: date):
    return datetime.combine(d, time.min), datetime.combine(d + timedelta(days=1), time.min)


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    today = date.today()
    start, end = _day_range(today)
    active_loans = db.query(Loan).filter(Loan.return_date.is_(None))
    return {
        "members_total": db.query(Member).count(),
        "members_active": db.query(Member).filter(Member.is_active.is_(True)).count(),
        "books_total": db.query(Book).filter(Book.withdrawn.is_(False)).count(),
        "books_available": db.query(Book).filter(Book.status == AVAILABLE).count(),
        "books_issued": db.query(Book).filter(Book.status == ISSUED).count(),
        "overdue": active_loans.filter(Loan.due_date < today).count(),
        "issued_today": db.query(Loan).filter(Loan.issue_date == today).count(),
        "returned_today": db.query(Loan).filter(Loan.return_date == today).count(),
        "books_added_today": db.query(Book).filter(Book.created_at >= start, Book.created_at < end).count(),
        "members_added_today": db.query(Member).filter(Member.created_at >= start, Member.created_at < end).count(),
        "collected_today": float(
            db.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(Payment.paid_at >= start, Payment.paid_at < end).scalar() or 0
        ),
    }


@router.get("/today-activity")
def today_activity(db: Session = Depends(get_db)):
    """Everything that happened at the counter today, newest first."""
    today = date.today()
    start, end = _day_range(today)
    events = []

    def add(when, kind, **data):
        events.append({"time": when.isoformat() if when else None, "kind": kind, **data})

    payments = db.query(Payment).filter(Payment.paid_at >= start, Payment.paid_at < end).all()
    paid = {p.loan_id: p for p in payments if p.loan_id}
    returned_ids = set()
    for l in db.query(Loan).filter(or_(Loan.issue_date == today, Loan.return_date == today)).all():
        who = {"member_id": l.member_id, "member_name": l.member.name, "member_no": l.member.membership_no,
               "book_id": l.book_id, "acc_no": l.book.acc_no, "title": l.book.title,
               # for the details popup on Home
               "author": l.book.persons, "section": l.book.section, "ref": l.ref,
               "issue_date": l.issue_date.isoformat(), "loan_due": l.due_date.isoformat(),
               "return_date": l.return_date.isoformat() if l.return_date else None,
               "issue_fee": float(l.issue_fee), "late_fine": float(l.late_fine), "damage_fine": float(l.damage_fine),
               "lost_fine": float(l.lost_fine), "lost": l.is_lost, "balance": float(l.balance)}
        if l.issue_date == today:
            add(l.created_at, "issue", due_date=l.due_date.isoformat(), by=l.issued_by, **who)
        if l.return_date == today:
            p = paid.get(l.id)
            returned_ids.add(l.id)
            add(l.returned_at or (p.paid_at if p else None), "return", late_days=l.late_days,
                fine=float(l.total_fine), damaged=l.is_damaged, receipt_no=p.receipt_no if p else None,
                by=l.returned_by, **who)
    for m in db.query(Member).filter(Member.created_at >= start, Member.created_at < end):
        add(m.created_at, "member", member_id=m.id, member_name=m.name, member_no=m.membership_no,
            membership_type=m.membership_type, by=m.created_by, telephone=m.telephone, address=m.address,
            expiry_date=m.expiry_date.isoformat() if m.expiry_date else None)
    for b in db.query(Book).filter(Book.created_at >= start, Book.created_at < end):
        add(b.created_at, "book", book_id=b.id, acc_no=b.acc_no, title=b.title, section=b.section, by=b.entered_by,
            author=b.persons, call_no=b.call_no, price=float(b.price), publisher=b.publisher)
    # every payment is listed (one receipt can hold a return charge and issue fees together);
    # Home shows one line per receipt with its full total
    for p in payments:
        add(p.paid_at, "payment", member_id=p.member_id, member_name=p.member_name, member_no=p.member_no,
            receipt_no=p.receipt_no, amount=float(p.amount), payment_type=p.payment_type, by=p.received_by)
    events.sort(key=lambda e: e["time"] or "", reverse=True)
    return {"count": len(events), "items": events}


def _loan_rows(db: Session, loans, st):
    today = date.today()
    rows = []
    for l in loans:
        row = LoanOut.model_validate(l).model_dump(mode="json")
        row["estimated_fine"] = float(calc_late(db, l.due_date, today, st)[1])
        rows.append(row)
    return rows


@router.get("/overdue")
def overdue(db: Session = Depends(get_db)):
    st = get_settings(db)
    loans = (db.query(Loan).filter(Loan.return_date.is_(None), Loan.due_date < date.today())
             .order_by(Loan.due_date).all())
    rows = _loan_rows(db, loans, st)
    return {"count": len(rows), "items": rows, "total": sum(r["estimated_fine"] for r in rows)}


@router.get("/pending-returns")
def pending_returns(section: str = "", db: Session = Depends(get_db)):
    st = get_settings(db)
    q = db.query(Loan).join(Book).filter(Loan.return_date.is_(None))
    if section:
        q = q.filter(Book.section == section)
    rows = _loan_rows(db, q.order_by(Loan.due_date).all(), st)
    return {"count": len(rows), "items": rows}


@router.get("/members-with-overdue")
def members_with_overdue(db: Session = Depends(get_db)):
    """Members who have not returned books on time."""
    loans = (db.query(Loan).filter(Loan.return_date.is_(None), Loan.due_date < date.today())
             .order_by(Loan.due_date).all())
    grouped = defaultdict(list)
    for l in loans:
        grouped[l.member_id].append(l)
    rows = []
    for ls in grouped.values():
        m = ls[0].member
        rows.append({
            "member": MemberOut.model_validate(m).model_dump(mode="json"),
            "count": len(ls),
            "books": "; ".join(f"{l.book.acc_no} - {l.book.title}" for l in ls),
            "oldest_due": min(l.due_date for l in ls).isoformat(),
        })
    rows.sort(key=lambda r: r["oldest_due"])
    return {"count": len(rows), "items": rows}


@router.get("/members-by-age")
def members_by_age(min_age: int = 10, max_age: int = 11, membership_type: str = "",
                   db: Session = Depends(get_db)):
    q = db.query(Member).filter(Member.birthday.isnot(None), Member.is_active.is_(True))
    if membership_type:
        q = q.filter(Member.membership_type == membership_type)
    rows = [MemberOut.model_validate(m).model_dump(mode="json") for m in q.order_by(Member.name).all()
            if m.age is not None and min_age <= m.age <= max_age]
    return {"count": len(rows), "items": rows}


@router.get("/inactive-members")
def inactive_members(mode: str = "no_borrow", months: int = 6, limit: int = 1000, db: Session = Depends(get_db)):
    if mode == "status":
        q = db.query(Member).filter(Member.is_active.is_(False)).order_by(Member.name)
        return {"count": q.count(), "items": [_member_row(m) for m in _limited(q, limit)]}
    cutoff = date.today() - timedelta(days=30 * months)
    last = (db.query(Loan.member_id, func.max(Loan.issue_date).label("last"))
            .group_by(Loan.member_id).subquery())
    q = (db.query(Member, last.c.last).outerjoin(last, last.c.member_id == Member.id)
         .filter(Member.is_active.is_(True))
         .filter(or_(last.c.last.is_(None), last.c.last < cutoff))
         .order_by(Member.name))
    rows = []
    for m, last_date in _limited(q, limit):
        row = _member_row(m)
        row["last_borrowed"] = last_date.isoformat() if last_date else None
        rows.append(row)
    return {"count": q.count(), "items": rows}


@router.get("/unpaid-fines")
def unpaid_fines(db: Session = Depends(get_db)):
    loans = (db.query(Loan).filter(or_(Loan.late_fine > 0, Loan.damage_fine > 0, Loan.lost_fine > 0, Loan.issue_fee > 0))
             .order_by(Loan.return_date.desc()).all())
    rows = [LoanOut.model_validate(l).model_dump(mode="json") for l in loans if l.balance > 0]
    return {"count": len(rows), "items": rows, "total": sum(r["balance"] for r in rows)}


@router.get("/expiring-members")
def expiring_members(days: int = 30, db: Session = Depends(get_db)):
    limit = date.today() + timedelta(days=days)
    ms = (db.query(Member).filter(Member.is_active.is_(True), Member.expiry_date.isnot(None),
                                  Member.expiry_date <= limit)
          .order_by(Member.expiry_date).all())
    rows = [_member_row(m) for m in ms]
    return {"count": len(rows), "items": rows}


@router.get("/section-summary")
def section_summary(db: Session = Depends(get_db)):
    data = defaultdict(lambda: {"total": 0, "available": 0, "issued": 0, "other": 0})
    for section, status, n in db.query(Book.section, Book.status, func.count(Book.id)).group_by(
            Book.section, Book.status).all():
        d = data[section or "(no section)"]
        d["total"] += n
        if status == AVAILABLE:
            d["available"] += n
        elif status == ISSUED:
            d["issued"] += n
        else:
            d["other"] += n
    rows = [{"section": k, **v} for k, v in sorted(data.items())]
    return {"count": len(rows), "items": rows, "total": sum(r["total"] for r in rows)}


@router.get("/membership-summary")
def membership_summary(db: Session = Depends(get_db)):
    data = defaultdict(lambda: {"total": 0, "active": 0, "expired": 0})
    for m in db.query(Member).all():
        d = data[m.membership_type]
        d["total"] += 1
        if m.is_active:
            d["active"] += 1
        if m.is_expired:
            d["expired"] += 1
    rows = [{"membership_type": k, **v} for k, v in sorted(data.items())]
    return {"count": len(rows), "items": rows, "total": sum(r["total"] for r in rows)}


@router.get("/payments")
def payments_report(from_date: Optional[date] = None, to_date: Optional[date] = None,
                    payment_type: str = "", db: Session = Depends(get_db)):
    from_date = from_date or date.today().replace(day=1)
    to_date = to_date or date.today()
    q = db.query(Payment).filter(Payment.paid_at >= _day_range(from_date)[0],
                                 Payment.paid_at < _day_range(to_date)[1])
    if payment_type:
        q = q.filter(Payment.payment_type == payment_type)
    rows = [PaymentOut.model_validate(p).model_dump(mode="json") for p in q.order_by(Payment.paid_at).all()]
    return {"count": len(rows), "items": rows, "total": sum(r["amount"] for r in rows)}


# ================================================================
# Filter-based reports. Every filter is optional; combine them freely.
# List reports return the first `limit` rows (0 = all, used by Excel export)
# together with the full count.
# ================================================================
LIST_LIMIT = 1000

DEWEY = {
    "0": "000 General works & computers", "1": "100 Philosophy & psychology", "2": "200 Religion",
    "3": "300 Social sciences", "4": "400 Language", "5": "500 Science", "6": "600 Technology",
    "7": "700 Arts & recreation", "8": "800 Literature", "9": "900 History & geography",
}
AGE_GROUPS = [(0, 5, "Under 6"), (6, 10, "6 - 10"), (11, 15, "11 - 15"), (16, 18, "16 - 18"), (19, 25, "19 - 25"),
              (26, 40, "26 - 40"), (41, 60, "41 - 60"), (61, 200, "Over 60")]
NOT_RECORDED = "(not recorded)"


def _limited(q, limit: int):
    return q.limit(limit).all() if limit and limit > 0 else q.all()


def _acc_order():
    """Acc. Nos. are text; order 9 before 10 by sorting on length first."""
    return func.length(Book.acc_no), Book.acc_no


def _book_row(b: Book) -> dict:
    return {
        "id": b.id, "acc_no": b.acc_no, "title": b.title, "persons": b.persons, "publisher": b.publisher,
        "year_of_publication": b.year_of_publication, "section": b.section, "class_no_scheme": b.class_no_scheme,
        "call_no": b.call_no, "isbn": b.isbn, "price": float(b.price or 0), "status": b.status,
        "date_entered": b.date_entered.isoformat() if b.date_entered else None, "location": b.location,
        "label_done": b.label_done, "label_done_at": b.label_done_at.isoformat() if b.label_done_at else None,
        "label_done_by": b.label_done_by,
    }


def _member_row(m: Member) -> dict:
    return {
        "id": m.id, "membership_no": m.membership_no, "name": m.name, "membership_type": m.membership_type,
        "age": m.age, "birthday": m.birthday.isoformat() if m.birthday else None, "nic_no": m.nic_no,
        "telephone": m.telephone, "address": m.address, "school": m.school,
        "registered_date": m.registered_date.isoformat() if m.registered_date else None,
        "expiry_date": m.expiry_date.isoformat() if m.expiry_date else None,
        "is_active": m.is_active, "is_expired": m.is_expired,
        "card_done": m.card_done, "card_done_at": m.card_done_at.isoformat() if m.card_done_at else None,
        "card_done_by": m.card_done_by,
    }


def _date_between(col, from_date: Optional[date], to_date: Optional[date]):
    conds = []
    if from_date:
        conds.append(col >= from_date)
    if to_date:
        conds.append(col <= to_date)
    return and_(*conds) if conds else None


# ---------------------------------------------------------------- books
@router.get("/books")
def books_report(q: str = "", section: str = "", status: str = "", subject: str = "",
                 entered_from: Optional[date] = None, entered_to: Optional[date] = None,
                 year_from: str = "", year_to: str = "",
                 price_min: Optional[float] = None, price_max: Optional[float] = None, label: str = "",
                 sort: str = "acc_no", limit: int = LIST_LIMIT, db: Session = Depends(get_db)):
    query = db.query(Book)
    if q.strip():
        query = query.filter(book_search_filter(q))
    if section:
        query = query.filter(Book.section == ("" if section == "-" else section))
    if status:
        query = query.filter(Book.status == status)
    if subject:
        query = query.filter(Book.class_no_scheme.like(f"{subject}%"))
    cond = _date_between(Book.date_entered, entered_from, entered_to)
    if cond is not None:
        query = query.filter(cond)
    year = func.substr(Book.year_of_publication, 1, 4)
    if year_from.strip():
        query = query.filter(year >= year_from.strip())
    if year_to.strip():
        query = query.filter(year <= year_to.strip())
    if price_min is not None:
        query = query.filter(Book.price >= price_min)
    if price_max is not None:
        query = query.filter(Book.price <= price_max)
    if label in ("yes", "no"):
        query = query.filter(Book.label_done.is_(label == "yes"))

    count = query.count()
    value = float(query.with_entities(func.coalesce(func.sum(Book.price), 0)).scalar() or 0)
    order = {"title": (Book.title,), "newest": (Book.date_entered.desc().nullslast(), Book.id.desc())}.get(sort, _acc_order())
    rows = [_book_row(b) for b in _limited(query.order_by(*order), limit)]
    return {"count": count, "items": rows, "total": value}


@router.get("/book-summary")
def book_summary(group_by: str = "section", section: str = "", db: Session = Depends(get_db)):
    """Number of books per section / subject / status / year entered / year published."""
    keys = {
        "subject": func.substr(Book.class_no_scheme, 1, 1),
        "year_entered": func.extract("year", Book.date_entered),
        "year_published": func.substr(Book.year_of_publication, 1, 4),
        "status": Book.status,
    }
    key = keys.get(group_by, Book.section)
    query = db.query(key, Book.status, func.count(Book.id), func.coalesce(func.sum(Book.price), 0))
    if section:
        query = query.filter(Book.section == section)
    data = defaultdict(lambda: {"total": 0, "available": 0, "issued": 0, "other": 0, "value": 0.0})
    for k, status, n, value in query.group_by(key, Book.status).all():
        if group_by == "subject":
            label = DEWEY.get(k or "", NOT_RECORDED if not k else "Other")
        elif group_by == "year_entered":
            label = str(int(k)) if k else NOT_RECORDED
        else:
            label = k or NOT_RECORDED
        d = data[label]
        d["total"] += n
        d["value"] += float(value)
        d[{AVAILABLE: "available", ISSUED: "issued"}.get(status, "other")] += n
    rows = [{"group": k, **v} for k, v in sorted(data.items(), key=lambda x: (x[0] == NOT_RECORDED, x[0]))]
    return {"count": len(rows), "items": rows, "total": sum(r["total"] for r in rows)}


@router.get("/popular-books")
def popular_books(from_date: Optional[date] = None, to_date: Optional[date] = None, section: str = "",
                  top: int = 50, db: Session = Depends(get_db)):
    n = func.count(Loan.id).label("n")
    query = db.query(Book, n).join(Loan, Loan.book_id == Book.id)
    cond = _date_between(Loan.issue_date, from_date, to_date)
    if cond is not None:
        query = query.filter(cond)
    if section:
        query = query.filter(Book.section == section)
    res = query.group_by(Book.id).order_by(n.desc(), Book.title).limit(max(1, top)).all()
    rows = [{**_book_row(b), "times": times} for b, times in res]
    return {"count": len(rows), "items": rows}


@router.get("/never-borrowed")
def never_borrowed(section: str = "", subject: str = "", entered_before: Optional[date] = None,
                   limit: int = LIST_LIMIT, db: Session = Depends(get_db)):
    query = db.query(Book).filter(~Book.loans.any(), Book.withdrawn.is_(False))
    if section:
        query = query.filter(Book.section == section)
    if subject:
        query = query.filter(Book.class_no_scheme.like(f"{subject}%"))
    if entered_before:
        query = query.filter(Book.date_entered < entered_before)
    count = query.count()
    rows = [_book_row(b) for b in _limited(query.order_by(*_acc_order()), limit)]
    return {"count": count, "items": rows}


# ---------------------------------------------------------------- members
@router.get("/members")
def members_report(q: str = "", membership_type: str = "", active: str = "yes",
                   min_age: Optional[int] = None, max_age: Optional[int] = None,
                   registered_from: Optional[date] = None, registered_to: Optional[date] = None,
                   expiry: str = "", school: str = "", card: str = "", sort: str = "name",
                   limit: int = LIST_LIMIT, db: Session = Depends(get_db)):
    today = date.today()
    query = db.query(Member)
    if q.strip():
        query = query.filter(or_(member_search_filter(q), Member.address.ilike(f"%{q.strip()}%")))
    if membership_type:
        query = query.filter(Member.membership_type == membership_type)
    if active in ("yes", "no"):
        query = query.filter(Member.is_active.is_(active == "yes"))
    if min_age is not None:
        query = query.filter(Member.birthday <= add_years(today, -min_age))
    if max_age is not None:
        query = query.filter(Member.birthday > add_years(today, -(max_age + 1)))
    cond = _date_between(Member.registered_date, registered_from, registered_to)
    if cond is not None:
        query = query.filter(cond)
    not_life = Member.membership_type != "LIFETIME"
    if expiry == "expired":
        query = query.filter(not_life, Member.expiry_date < today)
    elif expiry == "expiring":
        query = query.filter(not_life, Member.expiry_date >= today, Member.expiry_date <= today + timedelta(days=30))
    elif expiry == "valid":
        query = query.filter(or_(~not_life, Member.expiry_date.is_(None), Member.expiry_date >= today))
    elif expiry == "none":
        query = query.filter(not_life, Member.expiry_date.is_(None))
    if school.strip():
        query = query.filter(Member.school.ilike(f"%{school.strip()}%"))
    if card in ("yes", "no"):
        query = query.filter(Member.card_done.is_(card == "yes"))

    count = query.count()
    order = {
        "membership_no": (func.length(Member.membership_no), Member.membership_no),
        "newest": (Member.registered_date.desc().nullslast(), Member.id.desc()),
        "age": (Member.birthday.desc().nullslast(),),
    }.get(sort, (Member.name,))
    rows = [_member_row(m) for m in _limited(query.order_by(*order), limit)]
    return {"count": count, "items": rows}


@router.get("/member-summary")
def member_summary(group_by: str = "type", db: Session = Depends(get_db)):
    """Number of members per type / age group / registration year / school / status."""
    today = date.today()
    data = defaultdict(lambda: {"total": 0, "active": 0, "expired": 0})
    cols = (Member.membership_type, Member.birthday, Member.registered_date, Member.school,
            Member.is_active, Member.expiry_date)
    for mtype, birthday, registered, school, is_active, expiry in db.query(*cols).all():
        if group_by == "age":
            label = NOT_RECORDED
            if birthday:
                age = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
                label = next((g for lo, hi, g in AGE_GROUPS if lo <= age <= hi), NOT_RECORDED)
        elif group_by == "year_registered":
            label = str(registered.year) if registered else NOT_RECORDED
        elif group_by == "school":
            label = (school or "").strip() or NOT_RECORDED
        elif group_by == "status":
            label = "Active" if is_active else "Not active"
        else:
            label = mtype
        d = data[label]
        d["total"] += 1
        d["active"] += 1 if is_active else 0
        d["expired"] += 1 if (expiry and expiry < today and mtype != "LIFETIME") else 0
    if group_by == "age":
        order = [g for _, _, g in AGE_GROUPS] + [NOT_RECORDED]
        items = sorted(data.items(), key=lambda x: order.index(x[0]))
    elif group_by == "school":
        items = sorted(data.items(), key=lambda x: (x[0] == NOT_RECORDED, -x[1]["total"]))
    else:
        items = sorted(data.items(), key=lambda x: (x[0] == NOT_RECORDED, x[0]))
    rows = [{"group": k, **v} for k, v in items]
    return {"count": len(rows), "items": rows, "total": sum(r["total"] for r in rows)}


# ---------------------------------------------------------------- books & members
@router.get("/loans")
def loans_report(from_date: Optional[date] = None, to_date: Optional[date] = None, state: str = "",
                 section: str = "", membership_type: str = "", member_no: str = "", acc_no: str = "",
                 limit: int = LIST_LIMIT, db: Session = Depends(get_db)):
    """Borrowing records: who took which book, when, and whether it came back."""
    today = date.today()
    query = db.query(Loan).join(Book, Loan.book_id == Book.id).join(Member, Loan.member_id == Member.id)
    cond = _date_between(Loan.issue_date, from_date, to_date)
    if cond is not None:
        query = query.filter(cond)
    if state == "out":
        query = query.filter(Loan.return_date.is_(None))
    elif state == "overdue":
        query = query.filter(Loan.return_date.is_(None), Loan.due_date < today)
    elif state == "returned":
        query = query.filter(Loan.return_date.isnot(None))
    elif state == "late":
        query = query.filter(Loan.return_date.isnot(None), Loan.late_days > 0)
    elif state == "damaged":
        query = query.filter(Loan.is_damaged.is_(True))
    if section:
        query = query.filter(Book.section == section)
    if membership_type:
        query = query.filter(Member.membership_type == membership_type)
    if member_no.strip():
        query = query.filter(func.upper(Member.membership_no) == member_no.strip().upper())
    if acc_no.strip():
        query = query.filter(func.upper(Book.acc_no) == acc_no.strip().upper())

    count = query.count()
    fines = float(query.with_entities(func.coalesce(func.sum(Loan.late_fine + Loan.damage_fine), 0)).scalar() or 0)
    loans = _limited(query.order_by(Loan.issue_date.desc(), Loan.id.desc()), limit)
    rows = [LoanOut.model_validate(l).model_dump(mode="json") for l in loans]
    return {"count": count, "items": rows, "total": fines}


@router.get("/top-borrowers")
def top_borrowers(from_date: Optional[date] = None, to_date: Optional[date] = None, membership_type: str = "",
                  top: int = 50, db: Session = Depends(get_db)):
    n = func.count(Loan.id).label("n")
    query = db.query(Member, n).join(Loan, Loan.member_id == Member.id)
    cond = _date_between(Loan.issue_date, from_date, to_date)
    if cond is not None:
        query = query.filter(cond)
    if membership_type:
        query = query.filter(Member.membership_type == membership_type)
    res = query.group_by(Member.id).order_by(n.desc(), Member.name).limit(max(1, top)).all()
    rows = [{**_member_row(m), "times": times} for m, times in res]
    return {"count": len(rows), "items": rows}


@router.get("/circulation-summary")
def circulation_summary(from_date: Optional[date] = None, to_date: Optional[date] = None,
                        group_by: str = "month", db: Session = Depends(get_db)):
    """Books issued and returned, per day / month / section / membership type."""
    to_date = to_date or date.today()
    from_date = from_date or to_date.replace(month=1, day=1)
    loans = (db.query(Loan).join(Book, Loan.book_id == Book.id).join(Member, Loan.member_id == Member.id)
             .filter(or_(Loan.issue_date.between(from_date, to_date), Loan.return_date.between(from_date, to_date)))
             .all())
    data = defaultdict(lambda: {"issued": 0, "returned": 0, "late": 0, "fines": 0.0})

    def label(loan, d):
        if group_by == "day":
            return d.isoformat()
        if group_by == "section":
            return loan.book.section or NOT_RECORDED
        if group_by == "membership_type":
            return loan.member.membership_type
        return d.strftime("%Y-%m")

    for l in loans:
        if from_date <= l.issue_date <= to_date:
            data[label(l, l.issue_date)]["issued"] += 1
        if l.return_date and from_date <= l.return_date <= to_date:
            d = data[label(l, l.return_date)]
            d["returned"] += 1
            d["late"] += 1 if l.late_days > 0 else 0
            d["fines"] += float(l.late_fine + l.damage_fine)
    rows = [{"group": k, **v} for k, v in sorted(data.items())]
    return {"count": len(rows), "items": rows, "total": sum(r["issued"] for r in rows)}


# ---------------------------------------------------------------- staff activity
ACTION_GROUPS = {
    "issue": ["issue"], "return": ["return"], "renew_loan": ["renew_loan"], "payment": ["payment"],
    "member_add": ["member_add"], "member_change": ["member_edit", "member_photo", "member_renew", "member_card"],
    "book_add": ["book_add"], "book_change": ["book_edit", "book_cover", "book_status", "book_label"],
    "holiday": ["holiday"], "settings": ["settings", "user"], "login": ["login"],
}


@router.get("/staff-list")
def staff_list(db: Session = Depends(get_db)):
    """Staff accounts, for the "Staff" filter."""
    users = db.query(User).order_by(User.full_name, User.username).all()
    return [{"id": u.id, "name": u.display_name, "role": u.role, "is_active": u.is_active} for u in users]


@router.get("/staff-activity")
def staff_activity(user_id: Optional[int] = None, action: str = "", from_date: Optional[date] = None,
                   to_date: Optional[date] = None, q: str = "", limit: int = LIST_LIMIT, db: Session = Depends(get_db)):
    """Who did what and when, newest first."""
    query = db.query(AuditLog)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action.in_(ACTION_GROUPS.get(action, [action])))
    if from_date:
        query = query.filter(AuditLog.at >= _day_range(from_date)[0])
    if to_date:
        query = query.filter(AuditLog.at < _day_range(to_date)[1])
    if q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(or_(AuditLog.ref.ilike(like), AuditLog.summary.ilike(like)))
    count = query.count()
    rows = [{"id": a.id, "at": a.at.isoformat(), "user_name": a.user_name, "action": a.action, "entity": a.entity,
             "entity_id": a.entity_id, "ref": a.ref, "summary": a.summary}
            for a in _limited(query.order_by(AuditLog.at.desc(), AuditLog.id.desc()), limit)]
    return {"count": count, "items": rows}


@router.get("/staff-summary")
def staff_summary(from_date: Optional[date] = None, to_date: Optional[date] = None, db: Session = Depends(get_db)):
    """How much each staff member did in a period."""
    to_date = to_date or date.today()
    from_date = from_date or to_date.replace(day=1)
    start, end = _day_range(from_date)[0], _day_range(to_date)[1]
    data = defaultdict(lambda: {"issue": 0, "return": 0, "member_add": 0, "book_add": 0, "changes": 0,
                                "payments": 0, "amount": 0.0, "login": 0, "total": 0})
    names = {}
    for uid, name, action, n in (db.query(AuditLog.user_id, AuditLog.user_name, AuditLog.action, func.count(AuditLog.id))
                                 .filter(AuditLog.at >= start, AuditLog.at < end)
                                 .group_by(AuditLog.user_id, AuditLog.user_name, AuditLog.action).all()):
        d = data[uid]
        names[uid] = name
        key = action if action in ("issue", "return", "member_add", "book_add", "login") else (
            "payments" if action == "payment" else "changes")
        d[key] += n
        if action != "login":
            d["total"] += n
    # money each staff member took in (all payments, also fines paid at the return desk)
    users = {u.display_name: u.id for u in db.query(User).all()}
    for name, n, amount in (db.query(Payment.received_by, func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0))
                            .filter(Payment.paid_at >= start, Payment.paid_at < end).group_by(Payment.received_by).all()):
        uid = users.get(name)
        data[uid]["payments"] = max(data[uid]["payments"], n)
        data[uid]["amount"] = float(amount)
        names.setdefault(uid, name)
    rows = [{"group": names.get(uid) or "(unknown)", **v} for uid, v in data.items()]
    rows.sort(key=lambda r: -r["total"])
    return {"count": len(rows), "items": rows, "total": sum(r["total"] for r in rows)}


# ---------------------------------------------------------------- QR labels and member cards
@router.get("/label-progress")
def label_progress(what: str = "books_section", db: Session = Depends(get_db)):
    """How far the QR labelling has got: done, remaining and percent, per group.

    what = books_section | books_subject | books_status | members_type
    """
    data = defaultdict(lambda: {"total": 0, "done": 0})
    if what == "members_type":
        query = (db.query(Member.membership_type, Member.card_done, func.count(Member.id))
                 .filter(Member.is_active.is_(True)).group_by(Member.membership_type, Member.card_done))
        label = lambda k: k or NOT_RECORDED  # noqa: E731
    else:
        key = {"books_subject": func.substr(Book.class_no_scheme, 1, 1), "books_status": Book.status}.get(what, Book.section)
        query = (db.query(key, Book.label_done, func.count(Book.id))
                 .filter(Book.withdrawn.is_(False)).group_by(key, Book.label_done))
        if what == "books_subject":
            label = lambda k: DEWEY.get(k or "", NOT_RECORDED if not k else "Other")  # noqa: E731
        else:
            label = lambda k: k or NOT_RECORDED  # noqa: E731
    for k, done, n in query.all():
        d = data[label(k)]
        d["total"] += n
        d["done"] += n if done else 0
    rows = [{"group": k, "total": v["total"], "done": v["done"], "remaining": v["total"] - v["done"],
             "percent": round(100 * v["done"] / v["total"], 1) if v["total"] else 0}
            for k, v in sorted(data.items(), key=lambda x: (x[0] == NOT_RECORDED, x[0]))]
    total = sum(r["total"] for r in rows)
    done = sum(r["done"] for r in rows)
    rows.append({"group": "All", "total": total, "done": done, "remaining": total - done,
                 "percent": round(100 * done / total, 1) if total else 0, "is_total": True})
    return {"count": len(rows) - 1, "items": rows, "total": done, "all": total}
