"""Business rules: settings, due dates, fines, numbering."""
from datetime import date, timedelta
from typing import Optional
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from .models import AppSetting, AuditLog, Book, Holiday, Member, Payment, User, dec

DEFAULT_SETTINGS = {
    "library_name": "Public Library",
    "library_address": "",
    "library_phone": "",
    "loan_days": "14",
    "grace_days": "2",
    "fine_per_day": "2",
    "charge_grace_days": "no",
    "damage_multiplier": "2",         # damaged book charge = this x the book's price
    "lost_multiplier": "2",           # missing book charge = this x the book's price
    "issue_fee_child": "2",           # fee for each book issued, by membership type (Rs. 2 a book)
    "issue_fee_student": "2",
    "issue_fee_adult": "2",
    "issue_fee_lifetime": "2",
    "issue_fee_default": "2",
    "membership_fee_child": "0",      # filled in when "Membership fee" is chosen on the Payment screen
    "membership_fee_student": "0",
    "membership_fee_adult": "0",
    "membership_fee_lifetime": "0",
    "txn_last_no": "0",               # last issue reference number given out
    "membership_years": "3",          # membership period for types not listed below
    "membership_years_child": "3",
    "membership_years_student": "3",
    "membership_years_adult": "3",
    "membership_prefix": "",          # e.g. "M" gives M10256; empty gives plain numbers like the old system
    "membership_last_no": "0",        # the last number given out automatically (never given twice)
    "max_books_child": "2",
    "max_books_student": "2",
    "max_books_adult": "2",
    "max_books_lifetime": "3",
    "max_books_default": "2",
    "non_lending_sections": "Reference",
    "receipt_footer": "Thank you. Please keep this receipt.",
}


def log_action(db: Session, user: Optional[User], action: str, summary: str,
               entity: str = "", entity_id: Optional[int] = None, ref: str = ""):
    """Record who did what. Saved together with the change itself (same commit)."""
    db.add(AuditLog(user_id=user.id if user else None, user_name=user.display_name if user else "",
                    action=action, entity=entity, entity_id=entity_id, ref=ref or "", summary=summary))


def get_settings(db: Session) -> dict:
    s = dict(DEFAULT_SETTINGS)
    for row in db.query(AppSetting).all():
        s[row.key] = row.value
    return s


def num(st: dict, key: str, default: float = 0) -> float:
    try:
        return float(st.get(key, default))
    except (TypeError, ValueError):
        return default


def non_lending_sections(st: dict) -> set[str]:
    return {x.strip().lower() for x in st.get("non_lending_sections", "").split(",") if x.strip()}


def max_books_for(member: Member, st: dict) -> int:
    default = num(st, "max_books_default", 2)
    return int(num(st, f"max_books_{(member.membership_type or '').lower()}", default))


# ---------- Calendar / fines ----------
def holidays_between(db: Session, start: date, end: date) -> set[date]:
    rows = db.query(Holiday.day).filter(Holiday.day >= start, Holiday.day <= end).all()
    return {r[0] for r in rows}


def next_open_day(db: Session, d: date) -> date:
    hs = holidays_between(db, d, d + timedelta(days=60))
    while d in hs:
        d += timedelta(days=1)
    return d


def compute_due_date(db: Session, issue_date: date, st: dict) -> date:
    due = issue_date + timedelta(days=int(num(st, "loan_days", 14)))
    return next_open_day(db, due)


def calc_late(db: Session, due: date, returned: date, st: dict) -> tuple[int, Decimal]:
    """Returns (late open days, late fine).

    Late days are counted from the day after the due date up to the return date,
    skipping days marked as holidays. The first `grace_days` late days are free.
    If charge_grace_days is 'yes', once the grace period is passed the grace days
    are charged too.
    """
    if returned <= due:
        return 0, Decimal(0)
    hs = holidays_between(db, due + timedelta(days=1), returned)
    late = sum(
        1 for i in range(1, (returned - due).days + 1) if due + timedelta(days=i) not in hs
    )
    grace = int(num(st, "grace_days", 2))
    rate = dec(st.get("fine_per_day", "2"))
    if late <= grace:
        return late, Decimal(0)
    chargeable = late if st.get("charge_grace_days") == "yes" else late - grace
    return late, rate * chargeable


def damage_fine_for(book: Book, st: dict) -> Decimal:
    return dec(book.price) * dec(st.get("damage_multiplier", "2"))


def lost_fine_for(book: Book, st: dict) -> Decimal:
    return dec(book.price) * dec(st.get("lost_multiplier", "2"))


def issue_fee_for(member: Member, st: dict) -> Decimal:
    """The fee for one book issued to this member (0 = no fee for that membership type)."""
    return max(dec(num(st, f"issue_fee_{(member.membership_type or '').lower()}", num(st, "issue_fee_default", 0))), Decimal(0))


def next_txn_ref(db: Session) -> str:
    """The reference number for one issue (all the books issued together share it).
    Given out one at a time, like membership numbers, so two counters never get the same one."""
    if db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": 7215002})
    row = db.get(AppSetting, "txn_last_no", populate_existing=True)
    n = (int(row.value) if row and (row.value or "").isdigit() else 0) + 1
    if row:
        row.value = str(n)
    else:
        db.add(AppSetting(key="txn_last_no", value=str(n)))
    db.flush()
    return f"T{date.today().year}-{n:06d}"


# What a payment for a loan is called, from what is still unpaid on it
PART_PAYMENT_TYPE = {"issue_fee": "ISSUE_FEE", "late": "LATE_FINE", "damage": "DAMAGE_FINE", "lost": "LOST_FINE"}


def loan_payment_type(loan) -> str:
    kinds = [p["kind"] for p in loan.due_parts]
    return PART_PAYMENT_TYPE[kinds[0]] if len(kinds) == 1 else "FINE"


def add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # 29 Feb
        return d.replace(year=d.year + years, day=28)


# ---------- Numbering ----------
def membership_years_for(membership_type: str, st: dict) -> int:
    """How many years a membership of this type lasts (Life Time never expires)."""
    default = num(st, "membership_years", 3)
    return max(1, int(num(st, f"membership_years_{(membership_type or '').lower()}", default)))


def membership_expiry(membership_type: str, registered: Optional[date], renewed: Optional[date], st: dict) -> Optional[date]:
    """Expiry = the last renewal date (or, if never renewed, the registration date) + the period for the type."""
    start = renewed or registered
    if membership_type == "LIFETIME" or not start:
        return None
    return add_years(start, membership_years_for(membership_type, st))


def _highest_membership_no(db: Session, prefix: str) -> int:
    """The biggest number in use among membership numbers that look like <prefix><digits>."""
    best = 0
    q = db.query(Member.membership_no)
    if prefix:
        q = q.filter(Member.membership_no.like(prefix + "%"))
    for (code,) in q:
        tail = (code or "")[len(prefix):]
        if tail.isdigit() and len(tail) <= 9:
            best = max(best, int(tail))
    return best


def peek_membership_no(db: Session, st: dict) -> str:
    """The number the next new member would get (for showing only; nothing is reserved)."""
    prefix = st.get("membership_prefix", "")
    return f"{prefix}{max(int(num(st, 'membership_last_no', 0)), _highest_membership_no(db, prefix)) + 1}"


def next_membership_no(db: Session, prefix: str) -> str:
    """Give out the next membership number: one more than the last one given out or in use.

    Two people saving a new member at the same moment must not get the same number, so the
    database is asked to let only one of them in here at a time (the lock lasts until this
    save is committed). The unique index on membership_no is the final safety net.
    """
    if db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": 7215001})
    row = db.get(AppSetting, "membership_last_no", populate_existing=True)
    last = int(row.value) if row and (row.value or "").isdigit() else 0
    n = max(last, _highest_membership_no(db, prefix)) + 1
    if row:
        row.value = str(n)
    else:
        db.add(AppSetting(key="membership_last_no", value=str(n)))
    db.flush()  # write the counter now, so it is saved (or undone) together with the new member
    return f"{prefix}{n}"


def next_acc_no(db: Session) -> str:
    n = (db.query(func.max(Book.id)).scalar() or 0) + 1
    while True:
        code = f"B{n:06d}"
        if not db.query(Book.id).filter(Book.acc_no == code).first():
            return code
        n += 1


def next_receipt_no(db: Session) -> str:
    prefix = f"R{date.today().year}-"
    last = (
        db.query(Payment.receipt_no)
        .filter(Payment.receipt_no.like(prefix + "%"))
        .order_by(Payment.id.desc())
        .first()
    )
    n = int(last[0].split("-")[1]) + 1 if last else 1
    return f"{prefix}{n:06d}"


def record_payment(
    db: Session, member: Member, amount, payment_type: str, user: User, loan=None, notes: str = ""
) -> Payment:
    amount = dec(amount)
    if amount <= 0:
        raise HTTPException(400, "Amount must be more than zero")
    p = Payment(
        receipt_no=next_receipt_no(db),
        member=member,
        loan=loan,
        payment_type=payment_type,
        amount=amount,
        received_by=user.display_name,
        notes=notes,
        ref=loan.ref if loan is not None else "",
    )
    db.add(p)
    db.flush()
    return p


# ---------- Search helpers ----------
def book_search_filter(q: str):
    like = f"%{q.strip()}%"
    cols = [
        Book.title, Book.sinhala_title, Book.tamil_title, Book.sinhala_title_formal,
        Book.persons, Book.acc_no, Book.isbn, Book.call_no, Book.publisher, Book.series,
        Book.corporate_body, Book.keyword_1, Book.keyword_2, Book.keyword_3, Book.keyword_4,
    ]
    return or_(*[c.ilike(like) for c in cols])


def member_search_filter(q: str):
    like = f"%{q.strip()}%"
    cols = [Member.name, Member.membership_no, Member.nic_no, Member.telephone, Member.school]
    return or_(*[c.ilike(like) for c in cols])


def find_member_by_code(db: Session, code: str):
    return db.query(Member).filter(func.upper(Member.membership_no) == code.strip().upper()).first()


def find_book_by_code(db: Session, code: str):
    code = code.strip()
    if not code:
        return None
    return (
        db.query(Book).filter(func.upper(Book.acc_no) == code.upper()).first()
        or db.query(Book).filter(Book.item_identifier == code).first()
    )
