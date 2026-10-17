from decimal import Decimal
from datetime import date, datetime
from typing import Annotated, Optional

from pydantic import BaseModel, BeforeValidator, ConfigDict


def _empty_to_none(v):
    return None if v == "" else v


def _none_to_empty(v):
    return "" if v is None else v


def _to_number(v):
    return 0 if v in ("", None) else v


OptDate = Annotated[Optional[date], BeforeValidator(_empty_to_none)]
Str = Annotated[str, BeforeValidator(_none_to_empty)]
Money = Annotated[float, BeforeValidator(_to_number)]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Users ----------
class UserOut(ORM):
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool


class UserCreate(BaseModel):
    username: str
    full_name: Str = ""
    password: str
    role: str = "staff"


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class LoginIn(BaseModel):
    username: str
    password: str


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


# ---------- Members ----------
class MemberIn(BaseModel):
    membership_no: Str = ""
    name: Str = ""
    address: Str = ""
    nic_no: Str = ""
    birthday: OptDate = None
    membership_type: Str = "STUDENT"
    email: Str = ""
    telephone: Str = ""
    registered_date: OptDate = None
    expiry_date: OptDate = None
    renewal_date: OptDate = None
    guarantor_name: Str = ""
    guarantor_address: Str = ""
    school: Str = ""
    notes: Str = ""
    is_active: bool = True


class MemberBrief(ORM):
    id: int
    membership_no: str
    name: str
    membership_type: str
    telephone: str


class MemberOut(MemberIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    photo_url: Optional[str] = None
    created_by: Str = ""
    card_done: bool = False
    card_done_at: Optional[datetime] = None
    card_done_by: Str = ""
    age: Optional[int] = None
    is_expired: bool = False
    borrowed_acc_nos: str = ""
    created_at: datetime


class MemberPage(BaseModel):
    total: int
    items: list[MemberOut]


class RenewIn(BaseModel):
    years: Optional[int] = None  # empty = the usual period for the member's type
    fee: Money = 0


# ---------- Books ----------
class BookIn(BaseModel):
    acc_no: Str = ""
    title: Str = ""
    sinhala_title: Str = ""
    tamil_title: Str = ""
    sinhala_title_formal: Str = ""
    parent_title: Str = ""
    parent_title_2: Str = ""
    persons: Str = ""
    corporate_body: Str = ""
    meeting: Str = ""
    edition: Str = ""
    publisher: Str = ""
    year_of_publication: Str = ""
    physical_description: Str = ""
    series: Str = ""
    citation: Str = ""
    isbn: Str = ""
    issn: Str = ""
    record_type: Str = ""
    bibliographic_level: Str = ""
    item_identifier: Str = ""
    medium: Str = ""
    heading_identifier: Str = ""
    heading: Str = ""
    material_type: Str = ""
    section: Str = ""
    price: Money = 0
    remarks: Str = ""
    date_entered: OptDate = None
    class_no_scheme: Str = ""
    call_no: Str = ""
    keyword_1: Str = ""
    keyword_2: Str = ""
    keyword_3: Str = ""
    keyword_4: Str = ""
    notes_bib: Str = ""
    notes_contents: Str = ""
    abstracts: Str = ""
    broad_headings: Str = ""
    geographical_code: Str = ""
    entered_by: Str = ""
    user_code: Str = ""
    rack_no: Str = ""
    shelf_no: Str = ""


class BookBrief(ORM):
    id: int
    acc_no: str
    title: str
    persons: str
    section: str
    price: Money
    call_no: str
    location: str
    status: str


class BookOut(BookIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    cover_url: Optional[str] = None
    label_done: bool = False
    label_done_at: Optional[datetime] = None
    label_done_by: Str = ""
    withdrawn: bool
    withdrawn_by: Str = ""
    withdrawn_date: Optional[date] = None
    created_at: datetime
    date_borrowed: Optional[date] = None
    due_date: Optional[date] = None
    borrower_id: Optional[int] = None
    borrower_name: Optional[str] = None
    borrower_no: Optional[str] = None
    location: str = ""
    # copies of the same book
    title_id: Optional[int] = None
    copies: int = 0
    copies_in: int = 0
    copies_out: int = 0


class AddCopiesIn(BaseModel):
    """More copies of a book the library already has: the details are taken from that book.
    Only what can differ between copies is given here."""
    count: int = 1
    acc_nos: list[str] = []  # empty: the next numbers are given
    year_of_publication: Optional[str] = None
    edition: Optional[str] = None
    price: Optional[Decimal] = None
    rack_no: Optional[str] = None
    shelf_no: Optional[str] = None
    remarks: Optional[str] = None


class SameBookIn(BaseModel):
    code: str  # Acc. No. of a copy of the other book


class BookPage(BaseModel):
    total: int
    items: list[BookOut]


class DoneIn(BaseModel):
    done: bool = True
    ids: list[int] = []  # for marking several books at once


class PictureIn(BaseModel):
    image: Optional[str] = None  # a picture as a data URL (data:image/jpeg;base64,...)
    copy_from: Optional[int] = None  # books only: use the cover of this other copy


class StatusIn(BaseModel):
    status: str
    reason: Str = ""


# ---------- Loans ----------
class LoanOut(ORM):
    id: int
    issue_date: date
    due_date: date
    return_date: Optional[date] = None
    issued_by: str
    returned_by: str
    is_damaged: bool
    late_days: int
    late_fine: Money
    damage_fine: Money
    total_fine: Money
    paid_amount: Money
    balance: Money
    ref: str = ""
    issue_fee: Money = 0
    is_lost: bool = False
    lost_fine: Money = 0
    total_due: Money = 0
    due_parts: list[dict] = []
    days_overdue: int
    is_overdue: bool
    notes: str
    book: BookBrief
    member: MemberBrief


class IssueIn(BaseModel):
    member_id: int
    acc_nos: list[str]
    issue_date: OptDate = None


class IssueGroupItem(BaseModel):
    member_id: int
    acc_nos: list[str]


class IssueGroupIn(BaseModel):
    """Several members who came together, each with their own books."""
    items: list[IssueGroupItem]
    issue_date: OptDate = None


class CancelIssueIn(BaseModel):
    """Undo an issue made today (to correct a mistake before the member leaves)."""
    loan_ids: list[int]


class ReturnIn(BaseModel):
    acc_no: str
    damaged: bool = False
    lost: bool = False
    notes: Str = ""
    return_date: OptDate = None
    collect_payment: bool = True


class ReturnItem(BaseModel):
    acc_no: str
    damaged: bool = False
    lost: bool = False  # missing: the member cannot bring the book back


class ChargeIn(BaseModel):
    """An extra charge added by staff for one of the member's books."""
    loan_id: int
    kind: str  # "damage" or "lost"
    amount: Optional[Money] = None  # empty = worked out from the book price and the settings


class ReturnManyIn(BaseModel):
    """Several books handed back on one visit (each keeps its own due date and fine)."""
    items: list[ReturnItem]
    notes: Str = ""
    return_date: OptDate = None
    collect_payment: bool = True


# ---------- Payments ----------
class PaymentIn(BaseModel):
    member_id: int
    loan_id: Optional[int] = None
    payment_type: str = "OTHER"
    amount: Money
    notes: Str = ""


class CollectIn(BaseModel):
    """Pay everything owed for these books at once, on one receipt.
    The books can belong to several members (a group visit); member_id, when given, must own them all."""
    member_id: Optional[int] = None
    loan_ids: list[int]


class PaymentOut(ORM):
    id: int
    receipt_no: str
    member_id: int
    loan_id: Optional[int] = None
    payment_type: str
    amount: Money
    paid_at: datetime
    received_by: str
    notes: str
    ref: str = ""
    member_name: str
    member_no: str
    book_acc_no: Optional[str] = None
    book_title: Optional[str] = None


# ---------- Holidays ----------
class HolidayIn(BaseModel):
    day: date
    description: Str = "Holiday"


class HolidayOut(ORM):
    id: int
    day: date
    description: str


class BulkHolidayIn(BaseModel):
    year: int
    weekday: int  # 0 = Monday ... 6 = Sunday
    description: Str = "Closed"
