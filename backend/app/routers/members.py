from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import current_user
from ..config import settings
from ..database import get_db
from ..images import delete_picture, picture_response, save_picture
from ..models import Member, Payment, User
from ..schemas import LoanOut, MemberIn, MemberOut, MemberPage, PaymentOut, PictureIn, RenewIn
from ..services import (add_years, get_settings, log_action, member_search_filter, next_membership_no,
                        num, record_payment)

router = APIRouter(prefix="/api/members", tags=["members"])
photos = APIRouter(prefix="/api/photos", tags=["members"])
PHOTO_MAX = (480, 600)  # pixels; member photos are stored no larger than this


def get_member_or_404(db: Session, member_id: int) -> Member:
    m = db.get(Member, member_id)
    if not m:
        raise HTTPException(404, "Member not found")
    return m


@router.get("", response_model=MemberPage)
def list_members(q: str = "", membership_type: str = "", active: str = "", page: int = 1,
                 size: int = 25, db: Session = Depends(get_db), _: User = Depends(current_user)):
    query = db.query(Member)
    if q.strip():
        query = query.filter(member_search_filter(q))
    if membership_type:
        query = query.filter(Member.membership_type == membership_type)
    if active in ("true", "false"):
        query = query.filter(Member.is_active == (active == "true"))
    total = query.count()
    size = max(1, min(size, 500))
    items = query.order_by(Member.id.desc()).offset((max(page, 1) - 1) * size).limit(size).all()
    return {"total": total, "items": items}


def _apply(db: Session, m: Member, data: MemberIn, st: dict, is_new: bool):
    values = data.model_dump()
    values["name"] = values["name"].strip()
    if not values["name"]:
        raise HTTPException(400, "Member name is required")
    code = values["membership_no"].strip()
    if not code:
        if not is_new:
            raise HTTPException(400, "Membership No is required")
        code = next_membership_no(db, st.get("membership_prefix", "M"))
    clash = db.query(Member).filter(Member.membership_no == code, Member.id != (m.id or 0)).first()
    if clash:
        raise HTTPException(400, f"Membership No {code} is already used by {clash.name}")
    values["membership_no"] = code
    # Members imported from the old system may have no registration date; keep it empty on edit.
    values["registered_date"] = values["registered_date"] or m.registered_date or (date.today() if is_new else None)
    if not values["expiry_date"] and values["membership_type"] != "LIFETIME" and is_new:
        values["expiry_date"] = add_years(values["registered_date"], int(num(st, "membership_years", 1)))
    for k, v in values.items():
        setattr(m, k, v)


@router.post("", response_model=MemberOut)
def create_member(data: MemberIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    m = Member()
    _apply(db, m, data, get_settings(db), is_new=True)
    m.created_by = user.display_name
    db.add(m)
    db.flush()
    log_action(db, user, "member_add", f"Registered {m.name} ({m.membership_type.title()})", "member", m.id, m.membership_no)
    db.commit()
    db.refresh(m)
    return m


@router.put("/{member_id}", response_model=MemberOut)
def update_member(member_id: int, data: MemberIn, db: Session = Depends(get_db),
                  user: User = Depends(current_user)):
    m = get_member_or_404(db, member_id)
    was_active = m.is_active
    _apply(db, m, data, get_settings(db), is_new=False)
    if was_active != m.is_active:
        log_action(db, user, "member_edit", f"Made {m.name} {'active' if m.is_active else 'not active'}",
                   "member", m.id, m.membership_no)
    else:
        log_action(db, user, "member_edit", f"Edited member {m.name}", "member", m.id, m.membership_no)
    db.commit()
    db.refresh(m)
    return m


@router.get("/{member_id}")
def member_detail(member_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    m = get_member_or_404(db, member_id)
    payments = (db.query(Payment).filter(Payment.member_id == m.id)
                .order_by(Payment.id.desc()).limit(100).all())
    return {
        "member": MemberOut.model_validate(m),
        "current_loans": [LoanOut.model_validate(l) for l in m.active_loans],
        "history": [LoanOut.model_validate(l) for l in m.loans if l.return_date][:200],
        "fines": [LoanOut.model_validate(l) for l in m.loans if l.balance > 0],
        "unpaid": float(sum(l.balance for l in m.loans)),
        "payments": [PaymentOut.model_validate(p) for p in payments],
    }


# ---------- Member photo (optional) ----------
@router.post("/{member_id}/photo", response_model=MemberOut)
def set_photo(member_id: int, data: PictureIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    m = get_member_or_404(db, member_id)
    name = save_picture(data.image, settings.PHOTOS_DIR, m.id, PHOTO_MAX)
    delete_picture(settings.PHOTOS_DIR, m.photo_image)
    m.photo_image = name
    log_action(db, user, "member_photo", f"Set the photo of {m.name}", "member", m.id, m.membership_no)
    db.commit()
    db.refresh(m)
    return m


@router.delete("/{member_id}/photo", response_model=MemberOut)
def remove_photo(member_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    m = get_member_or_404(db, member_id)
    delete_picture(settings.PHOTOS_DIR, m.photo_image)
    m.photo_image = ""
    log_action(db, user, "member_photo", f"Removed the photo of {m.name}", "member", m.id, m.membership_no)
    db.commit()
    db.refresh(m)
    return m


@photos.get("/{name}")
def photo_file(name: str):
    return picture_response(settings.PHOTOS_DIR, name)


@router.post("/{member_id}/renew")
def renew_membership(member_id: int, data: RenewIn, db: Session = Depends(get_db),
                     user: User = Depends(current_user)):
    m = get_member_or_404(db, member_id)
    today = date.today()
    m.renewal_date = today
    if m.membership_type != "LIFETIME":
        base = m.expiry_date if m.expiry_date and m.expiry_date > today else today
        m.expiry_date = add_years(base, max(1, data.years))
    m.is_active = True
    payment = None
    if data.fee and data.fee > 0:
        payment = record_payment(db, m, data.fee, "MEMBERSHIP", user,
                                 notes=f"Membership renewal ({data.years} year)")
    until = "life time" if m.membership_type == "LIFETIME" else m.expiry_date.isoformat()
    log_action(db, user, "member_renew", f"Renewed the membership of {m.name} until {until}"
               + (f", fee Rs. {float(data.fee):.2f} (receipt {payment.receipt_no})" if payment else ""),
               "member", m.id, m.membership_no)
    db.commit()
    return {
        "member": MemberOut.model_validate(m),
        "payment": PaymentOut.model_validate(payment) if payment else None,
    }
