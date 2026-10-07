"""Business rules: settings, due dates, fines, numbering."""
from datetime import date, timedelta
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .models import AppSetting, Book, Holiday, Member, Payment, User, dec

DEFAULT_SETTINGS = {
    "library_name": "Public Library",
    "library_address": "",
    "library_phone": "",
    "loan_days": "14",
    "grace_days": "2",
    "fine_per_day": "2",
    "charge_grace_days": "no",
    "damage_multiplier": "2",
    "membership_years": "1",
    "membership_prefix": "M",
    "max_books_child": "2",
    "max_books_student": "2",
    "max_books_adult": "2",
    "max_books_lifetime": "3",
    "max_books_default": "2",
    "non_lending_sections": "Reference",
    "receipt_footer": "Thank you. Please keep this receipt.",
}


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


def add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # 29 Feb
        return d.replace(year=d.year + years, day=28)


# ---------- Numbering ----------
def next_membership_no(db: Session, prefix: str) -> str:
    n = (db.query(func.max(Member.id)).scalar() or 0) + 1
    while True:
        code = f"{prefix}{n:05d}"
        if not db.query(Member.id).filter(Member.membership_no == code).first():
            return code
        n += 1


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
