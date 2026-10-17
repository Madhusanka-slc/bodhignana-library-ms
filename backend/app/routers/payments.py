from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..models import Loan, Member, Payment, User
from ..schemas import CollectIn, PaymentIn, PaymentOut
from ..services import loan_payment_type, log_action, next_receipt_no, record_payment

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.get("", response_model=list[PaymentOut])
def list_payments(member_id: Optional[int] = None, receipt_no: str = "", limit: int = 100, db: Session = Depends(get_db),
                  _: User = Depends(current_user)):
    q = db.query(Payment)
    if member_id:
        q = q.filter(Payment.member_id == member_id)
    if receipt_no:  # every line of one receipt
        return q.filter(Payment.receipt_no == receipt_no).order_by(Payment.id).all()
    return q.order_by(Payment.id.desc()).limit(min(limit, 1000)).all()


@router.post("", response_model=PaymentOut)
def create_payment(data: PaymentIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    m = db.get(Member, data.member_id)
    if not m:
        raise HTTPException(404, "Member not found")
    loan = None
    if data.loan_id:
        loan = db.get(Loan, data.loan_id)
        if not loan or loan.member_id != m.id:
            raise HTTPException(400, "This fine does not belong to this member")
    ptype = data.payment_type
    if ptype == "AUTO":  # a payment for a book: named after what is still unpaid on it
        if not loan:
            raise HTTPException(400, "Choose what the payment is for")
        ptype = loan_payment_type(loan)
    p = record_payment(db, m, data.amount, ptype, user, loan=loan, notes=data.notes)
    log_action(db, user, "payment", f"Received Rs. {float(p.amount):.2f} from {m.name} ({m.membership_no}) - "
               f"{p.payment_type.replace('_', ' ').lower()}" + (f": {data.notes}" if data.notes else ""),
               "payment", p.id, p.receipt_no)
    db.commit()
    db.refresh(p)
    return p


@router.post("/collect", response_model=list[PaymentOut])
def collect(data: CollectIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Pay everything still owed for these books, all on ONE receipt (one line per book inside it).
    The books can belong to several members who came together (a group visit): each line is
    still recorded under the member who owes it, so their own records and reports stay right."""
    loans = [db.get(Loan, i) for i in dict.fromkeys(data.loan_ids)]
    if any(l is None for l in loans):
        raise HTTPException(404, "Some of these charges were not found")
    if data.member_id is not None and any(l.member_id != data.member_id for l in loans):
        raise HTTPException(400, "These charges do not belong to this member")
    owed = [l for l in loans if l.balance > 0]
    if not owed:
        raise HTTPException(400, "Nothing is owed for these books")
    owed.sort(key=lambda l: (l.member_id, l.id))  # each member's lines together on the receipt
    receipt = next_receipt_no(db)
    payments = []
    for l in owed:
        parts = ", ".join({"issue_fee": "issue fee", "late": f"late ({l.late_days} day(s))", "damage": "damaged",
                           "lost": "missing"}[p["kind"]] for p in l.due_parts)
        payments.append(record_payment(db, l.member, l.balance, loan_payment_type(l), user, loan=l, notes=parts, receipt_no=receipt))
    total = sum(float(p.amount) for p in payments)
    members = list(dict.fromkeys(l.member for l in owed))
    who = (f"{members[0].name} ({members[0].membership_no})" if len(members) == 1
           else f"a group of {len(members)} members ({', '.join(m.membership_no for m in members)})")
    log_action(db, user, "payment", f"Received Rs. {total:.2f} from {who} for "
               f"{len(payments)} book(s), receipt {receipt}", "payment", payments[0].id, receipt)
    db.commit()
    for p in payments:
        db.refresh(p)
    return payments


@router.get("/{payment_id}", response_model=PaymentOut)
def get_payment(payment_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    p = db.get(Payment, payment_id)
    if not p:
        raise HTTPException(404, "Payment not found")
    return p
