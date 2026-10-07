from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..models import AVAILABLE, ISSUED, Book, Loan, Member, Payment
from ..schemas import LoanOut, MemberOut, PaymentOut
from ..services import calc_late, get_settings

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
        "collected_today": float(
            db.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(Payment.paid_at >= start, Payment.paid_at < end).scalar() or 0
        ),
    }


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
def inactive_members(mode: str = "no_borrow", months: int = 6, db: Session = Depends(get_db)):
    if mode == "status":
        ms = db.query(Member).filter(Member.is_active.is_(False)).order_by(Member.name).all()
        rows = [MemberOut.model_validate(m).model_dump(mode="json") for m in ms]
        return {"count": len(rows), "items": rows}
    cutoff = date.today() - timedelta(days=30 * months)
    last = (db.query(Loan.member_id, func.max(Loan.issue_date).label("last"))
            .group_by(Loan.member_id).subquery())
    res = (db.query(Member, last.c.last).outerjoin(last, last.c.member_id == Member.id)
           .filter(Member.is_active.is_(True))
           .filter(or_(last.c.last.is_(None), last.c.last < cutoff))
           .order_by(Member.name).all())
    rows = []
    for m, last_date in res:
        row = MemberOut.model_validate(m).model_dump(mode="json")
        row["last_borrowed"] = last_date.isoformat() if last_date else None
        rows.append(row)
    return {"count": len(rows), "items": rows}


@router.get("/unpaid-fines")
def unpaid_fines(db: Session = Depends(get_db)):
    loans = (db.query(Loan).filter(or_(Loan.late_fine > 0, Loan.damage_fine > 0))
             .order_by(Loan.return_date.desc()).all())
    rows = [LoanOut.model_validate(l).model_dump(mode="json") for l in loans if l.balance > 0]
    return {"count": len(rows), "items": rows, "total": sum(r["balance"] for r in rows)}


@router.get("/expiring-members")
def expiring_members(days: int = 30, db: Session = Depends(get_db)):
    limit = date.today() + timedelta(days=days)
    ms = (db.query(Member).filter(Member.is_active.is_(True), Member.expiry_date.isnot(None),
                                  Member.expiry_date <= limit)
          .order_by(Member.expiry_date).all())
    rows = [MemberOut.model_validate(m).model_dump(mode="json") for m in ms]
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
