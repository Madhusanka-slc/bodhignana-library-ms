from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..models import Loan, Member, Payment, User
from ..schemas import PaymentIn, PaymentOut
from ..services import loan_payment_type, log_action, record_payment

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.get("", response_model=list[PaymentOut])
def list_payments(member_id: Optional[int] = None, limit: int = 100, db: Session = Depends(get_db),
                  _: User = Depends(current_user)):
    q = db.query(Payment)
    if member_id:
        q = q.filter(Payment.member_id == member_id)
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


@router.get("/{payment_id}", response_model=PaymentOut)
def get_payment(payment_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    p = db.get(Payment, payment_id)
    if not p:
        raise HTTPException(404, "Payment not found")
    return p
