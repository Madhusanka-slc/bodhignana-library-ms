from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..models import AVAILABLE, DAMAGED, ISSUED, Book, Loan, Member, User
from ..schemas import BookOut, IssueIn, LoanOut, MemberOut, PaymentOut, ReturnIn
from ..services import (calc_late, compute_due_date, damage_fine_for, find_book_by_code,
                        find_member_by_code, get_settings, log_action, max_books_for, non_lending_sections,
                        num, record_payment)

router = APIRouter(prefix="/api/circulation", tags=["issue & return"])


@router.get("/scan")
def scan(code: str, db: Session = Depends(get_db), _: User = Depends(current_user)):
    """Work out what a scanned / typed code is: a member card, a book, or an ISBN."""
    code = code.strip()
    if not code:
        raise HTTPException(400, "Empty code")
    m = find_member_by_code(db, code)
    if m:
        return {"type": "member", "member": MemberOut.model_validate(m)}
    b = find_book_by_code(db, code)
    if b:
        return {"type": "book", "book": BookOut.model_validate(b)}
    clean = code.replace("-", "")
    copies = db.query(Book).filter(func.replace(Book.isbn, "-", "") == clean).all()
    if copies:
        return {"type": "isbn", "books": [BookOut.model_validate(x) for x in copies]}
    raise HTTPException(404, f"No member or book found for \"{code}\"")


def _member_status(m: Member, st: dict) -> dict:
    loans = m.active_loans
    blocks, warnings = [], []
    if not m.is_active:
        blocks.append("This member is not active.")
    if m.is_expired:
        blocks.append(f"Membership expired on {m.expiry_date}. Please renew the membership first.")
    max_books = max_books_for(m, st)
    if len(loans) >= max_books:
        blocks.append(f"This member already has {len(loans)} book(s). The limit is {max_books}.")
    overdue = [l for l in loans if l.is_overdue]
    if overdue:
        warnings.append(f"{len(overdue)} book(s) are overdue and not returned yet.")
    unpaid = sum(l.balance for l in m.loans)
    if unpaid > 0:
        warnings.append(f"Unpaid fines: Rs. {unpaid:.2f}")
    return {
        "member": MemberOut.model_validate(m),
        "loans": [LoanOut.model_validate(l) for l in loans],
        "max_books": max_books,
        "can_borrow": max(0, max_books - len(loans)),
        "blocks": blocks,
        "warnings": warnings,
        "unpaid": float(unpaid),
    }


@router.get("/member-status/{member_id}")
def member_status(member_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    m = db.get(Member, member_id)
    if not m:
        raise HTTPException(404, "Member not found")
    return _member_status(m, get_settings(db))


@router.post("/issue")
def issue_books(data: IssueIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    st = get_settings(db)
    m = db.get(Member, data.member_id)
    if not m:
        raise HTTPException(404, "Member not found")
    acc_nos = list(dict.fromkeys(a.strip() for a in data.acc_nos if a.strip()))
    if not acc_nos:
        raise HTTPException(400, "Please scan at least one book")
    if not m.is_active:
        raise HTTPException(400, "This member is not active")
    if m.is_expired:
        raise HTTPException(400, f"Membership expired on {m.expiry_date}. Please renew first.")
    max_books = max_books_for(m, st)
    if len(m.active_loans) + len(acc_nos) > max_books:
        raise HTTPException(400, f"This member can have only {max_books} book(s) at a time "
                                 f"(already has {len(m.active_loans)}).")
    blocked_sections = non_lending_sections(st)
    books = []
    for acc in acc_nos:
        b = find_book_by_code(db, acc)
        if not b:
            raise HTTPException(404, f"Book {acc} not found")
        if b.status == ISSUED:
            raise HTTPException(400, f"\"{b.title}\" ({b.acc_no}) is already issued to {b.borrower_name}")
        if b.status != AVAILABLE:
            raise HTTPException(400, f"\"{b.title}\" ({b.acc_no}) cannot be issued. Status: {b.status}")
        if b.section.strip().lower() in blocked_sections:
            raise HTTPException(400, f"\"{b.title}\" is a {b.section} book and cannot be taken out")
        books.append(b)

    issue_date = data.issue_date or date.today()
    due = compute_due_date(db, issue_date, st)
    loans = []
    for b in books:
        loan = Loan(book=b, member=m, issue_date=issue_date, due_date=due, issued_by=user.display_name)
        b.status = ISSUED
        db.add(loan)
        loans.append(loan)
    db.flush()
    for loan in loans:
        log_action(db, user, "issue", f"Issued \"{loan.book.title}\" to {m.name} ({m.membership_no}), due {due}",
                   "loan", loan.id, loan.book.acc_no)
    db.commit()
    return {"due_date": due, "loans": [LoanOut.model_validate(l) for l in loans]}


def _active_loan(db: Session, acc_no: str) -> Loan:
    b = find_book_by_code(db, acc_no)
    if not b:
        raise HTTPException(404, f"Book {acc_no} not found")
    loan = db.query(Loan).filter(Loan.book_id == b.id, Loan.return_date.is_(None)).first()
    if not loan:
        raise HTTPException(400, f"\"{b.title}\" is not issued to anyone. It is already in the library.")
    return loan


def _fines(db: Session, loan: Loan, returned: date, damaged: bool, st: dict) -> dict:
    late_days, late_fine = calc_late(db, loan.due_date, returned, st)
    dmg = damage_fine_for(loan.book, st) if damaged else 0
    return {
        "late_days": late_days,
        "calendar_days_late": max((returned - loan.due_date).days, 0),
        "grace_days": int(num(st, "grace_days", 2)),
        "fine_per_day": num(st, "fine_per_day", 2),
        "damage_multiplier": num(st, "damage_multiplier", 2),
        "late_fine": float(late_fine),
        "damage_fine": float(dmg),
        "total": float(late_fine + dmg),
    }


@router.get("/return-preview")
def return_preview(acc_no: str, damaged: bool = False, return_date: Optional[date] = None,
                   db: Session = Depends(get_db), _: User = Depends(current_user)):
    st = get_settings(db)
    loan = _active_loan(db, acc_no)
    returned = return_date or date.today()
    return {"loan": LoanOut.model_validate(loan), "return_date": returned,
            **_fines(db, loan, returned, damaged, st)}


@router.post("/return")
def return_book(data: ReturnIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    st = get_settings(db)
    loan = _active_loan(db, data.acc_no)
    returned = data.return_date or date.today()
    f = _fines(db, loan, returned, data.damaged, st)
    loan.return_date = returned
    loan.returned_at = datetime.now()
    loan.returned_by = user.display_name
    loan.is_damaged = data.damaged
    loan.late_days = f["late_days"]
    loan.late_fine = f["late_fine"]
    loan.damage_fine = f["damage_fine"]
    loan.notes = data.notes
    loan.book.status = DAMAGED if data.damaged else AVAILABLE

    payment = None
    if data.collect_payment and f["total"] > 0:
        if f["late_fine"] and f["damage_fine"]:
            ptype = "FINE"
        elif f["damage_fine"]:
            ptype = "DAMAGE_FINE"
        else:
            ptype = "LATE_FINE"
        payment = record_payment(db, loan.member, f["total"], ptype, user, loan=loan,
                                 notes=f"{f['late_days']} late day(s)" + (", damaged" if data.damaged else ""))
    detail = []
    if f["late_days"]:
        detail.append(f"{f['late_days']} day(s) late")
    if data.damaged:
        detail.append("damaged")
    if f["total"]:
        detail.append(f"fine Rs. {f['total']:.2f}" + (f" paid (receipt {payment.receipt_no})" if payment else " not paid"))
    log_action(db, user, "return", f"Returned \"{loan.book.title}\" from {loan.member.name} ({loan.member.membership_no})"
               + (" - " + ", ".join(detail) if detail else ", on time"), "loan", loan.id, loan.book.acc_no)
    db.commit()
    db.refresh(loan)
    return {
        "loan": LoanOut.model_validate(loan),
        "payment": PaymentOut.model_validate(payment) if payment else None,
        **f,
    }


@router.post("/renew/{loan_id}")
def renew_loan(loan_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Give the member more time with the same book."""
    loan = db.get(Loan, loan_id)
    if not loan or loan.return_date:
        raise HTTPException(400, "This book is not currently issued")
    if loan.is_overdue:
        raise HTTPException(400, "This book is overdue. Please return it and pay the fine first.")
    loan.due_date = compute_due_date(db, date.today(), get_settings(db))
    log_action(db, user, "renew_loan", f"Gave {loan.member.name} more time for \"{loan.book.title}\", new due date {loan.due_date}",
               "loan", loan.id, loan.book.acc_no)
    db.commit()
    return LoanOut.model_validate(loan)
