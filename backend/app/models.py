from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

# Book status values
AVAILABLE = "AVAILABLE"
ISSUED = "ISSUED"
DAMAGED = "DAMAGED"
LOST = "LOST"
WITHDRAWN = "WITHDRAWN"


def _now() -> datetime:
    return datetime.now()


def txt(length: Optional[int] = None):
    """Text column that is never NULL (empty string by default)."""
    return mapped_column(String(length) if length else Text, default="", nullable=False)


def dec(value) -> Decimal:
    return Decimal(str(value or 0))


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    full_name: Mapped[str] = txt(120)
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="staff")  # admin | staff
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    @property
    def display_name(self) -> str:
        return self.full_name or self.username


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True)
    membership_no: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    address: Mapped[str] = txt()
    nic_no: Mapped[str] = txt(20)
    birthday: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    membership_type: Mapped[str] = mapped_column(String(20), default="STUDENT")
    email: Mapped[str] = txt(120)
    telephone: Mapped[str] = txt(30)
    registered_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, default=date.today)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    renewal_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    guarantor_name: Mapped[str] = txt(200)
    guarantor_address: Mapped[str] = txt()
    school: Mapped[str] = txt(200)
    notes: Mapped[str] = txt()
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    loans: Mapped[list["Loan"]] = relationship(back_populates="member", order_by="Loan.id.desc()")

    @property
    def age(self) -> Optional[int]:
        if not self.birthday:
            return None
        t = date.today()
        b = self.birthday
        return t.year - b.year - ((t.month, t.day) < (b.month, b.day))

    @property
    def is_expired(self) -> bool:
        return bool(self.expiry_date and self.expiry_date < date.today())

    @property
    def active_loans(self) -> list["Loan"]:
        return [l for l in self.loans if l.return_date is None]

    @property
    def borrowed_acc_nos(self) -> str:
        """The 'Acc. No/s' of books the member has right now."""
        return ", ".join(l.book.acc_no for l in self.active_loans)


class Book(Base):
    """One physical copy of a book. Each copy has its own Accession No (Acc. No.)."""

    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    acc_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    title: Mapped[str] = txt()
    sinhala_title: Mapped[str] = txt()
    tamil_title: Mapped[str] = txt()
    sinhala_title_formal: Mapped[str] = txt()
    parent_title: Mapped[str] = txt()
    parent_title_2: Mapped[str] = txt()
    persons: Mapped[str] = txt()
    corporate_body: Mapped[str] = txt()
    meeting: Mapped[str] = txt()
    edition: Mapped[str] = txt(100)
    publisher: Mapped[str] = txt()
    year_of_publication: Mapped[str] = txt(20)
    physical_description: Mapped[str] = txt()
    series: Mapped[str] = txt()
    citation: Mapped[str] = txt()
    isbn: Mapped[str] = txt(30)
    issn: Mapped[str] = txt(30)
    record_type: Mapped[str] = txt(100)
    bibliographic_level: Mapped[str] = txt(100)
    item_identifier: Mapped[str] = txt(100)
    medium: Mapped[str] = txt(100)
    heading_identifier: Mapped[str] = txt(100)
    heading: Mapped[str] = txt()
    material_type: Mapped[str] = txt(100)
    section: Mapped[str] = txt(50)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    remarks: Mapped[str] = txt()
    date_entered: Mapped[Optional[date]] = mapped_column(Date, nullable=True, default=date.today)
    class_no_scheme: Mapped[str] = txt(100)
    call_no: Mapped[str] = txt(100)
    keyword_1: Mapped[str] = txt(200)
    keyword_2: Mapped[str] = txt(200)
    keyword_3: Mapped[str] = txt(200)
    keyword_4: Mapped[str] = txt(200)
    notes_bib: Mapped[str] = txt()
    notes_contents: Mapped[str] = txt()
    abstracts: Mapped[str] = txt()
    broad_headings: Mapped[str] = txt()
    geographical_code: Mapped[str] = txt(50)
    entered_by: Mapped[str] = txt(100)
    user_code: Mapped[str] = txt(50)
    rack_no: Mapped[str] = txt(30)
    shelf_no: Mapped[str] = txt(30)
    status: Mapped[str] = mapped_column(String(20), default=AVAILABLE, index=True)
    withdrawn: Mapped[bool] = mapped_column(Boolean, default=False)
    withdrawn_by: Mapped[str] = txt(100)
    withdrawn_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    loans: Mapped[list["Loan"]] = relationship(back_populates="book", order_by="Loan.id.desc()")

    @property
    def current_loan(self) -> Optional["Loan"]:
        return next((l for l in self.loans if l.return_date is None), None)

    @property
    def date_borrowed(self) -> Optional[date]:
        cl = self.current_loan
        return cl.issue_date if cl else None

    @property
    def due_date(self) -> Optional[date]:
        cl = self.current_loan
        return cl.due_date if cl else None

    @property
    def borrower_id(self) -> Optional[int]:
        cl = self.current_loan
        return cl.member.id if cl else None

    @property
    def borrower_name(self) -> Optional[str]:
        cl = self.current_loan
        return cl.member.name if cl else None

    @property
    def borrower_no(self) -> Optional[str]:
        cl = self.current_loan
        return cl.member.membership_no if cl else None

    @property
    def location(self) -> str:
        parts = []
        if self.rack_no:
            parts.append(f"Rack {self.rack_no}")
        if self.shelf_no:
            parts.append(f"Shelf {self.shelf_no}")
        return " / ".join(parts)


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), index=True)
    issue_date: Mapped[date] = mapped_column(Date, default=date.today)
    due_date: Mapped[date] = mapped_column(Date)
    return_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    issued_by: Mapped[str] = txt(100)
    returned_by: Mapped[str] = txt(100)
    is_damaged: Mapped[bool] = mapped_column(Boolean, default=False)
    late_days: Mapped[int] = mapped_column(Integer, default=0)
    late_fine: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    damage_fine: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    notes: Mapped[str] = txt()
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    book: Mapped["Book"] = relationship(back_populates="loans")
    member: Mapped["Member"] = relationship(back_populates="loans")
    payments: Mapped[list["Payment"]] = relationship(back_populates="loan")

    @property
    def total_fine(self) -> Decimal:
        return dec(self.late_fine) + dec(self.damage_fine)

    @property
    def paid_amount(self) -> Decimal:
        return sum((dec(p.amount) for p in self.payments), Decimal(0))

    @property
    def balance(self) -> Decimal:
        return max(self.total_fine - self.paid_amount, Decimal(0))

    @property
    def days_overdue(self) -> int:
        end = self.return_date or date.today()
        return max((end - self.due_date).days, 0)

    @property
    def is_overdue(self) -> bool:
        return self.return_date is None and self.due_date < date.today()


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    receipt_no: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id"), index=True)
    loan_id: Mapped[Optional[int]] = mapped_column(ForeignKey("loans.id"), nullable=True)
    payment_type: Mapped[str] = mapped_column(String(30), default="OTHER")
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    paid_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)
    received_by: Mapped[str] = txt(100)
    notes: Mapped[str] = txt()

    member: Mapped["Member"] = relationship()
    loan: Mapped[Optional["Loan"]] = relationship(back_populates="payments")

    @property
    def member_name(self) -> str:
        return self.member.name if self.member else ""

    @property
    def member_no(self) -> str:
        return self.member.membership_no if self.member else ""

    @property
    def book_acc_no(self) -> Optional[str]:
        return self.loan.book.acc_no if self.loan else None

    @property
    def book_title(self) -> Optional[str]:
        return self.loan.book.title if self.loan else None


class Holiday(Base):
    __tablename__ = "holidays"

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(Date, unique=True, index=True)
    description: Mapped[str] = txt(200)


class AppSetting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
