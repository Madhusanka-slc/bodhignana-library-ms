from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..models import AVAILABLE, DAMAGED, ISSUED, LOST, Book, Loan, Member, User, dec
from ..schemas import BookOut, CancelIssueIn, ChargeIn, IssueIn, LoanOut, MemberOut, PaymentOut, ReturnIn, ReturnManyIn
from ..services import (calc_late, compute_due_date, damage_fine_for, find_book_by_code, find_member_by_code,
                        get_settings, issue_fee_for, loan_payment_type, log_action, lost_fine_for,
                        max_books_for, next_receipt_no, next_txn_ref, non_lending_sections, num,
                        record_payment)

router = APIRouter(prefix="/api/circulation", tags=["issue & return"])


@router.get("/scan")
def scan(code: str, prefer: str = "member", db: Session = Depends(get_db), _: User = Depends(current_user)):
    """Work out what a scanned / typed code is: a member card, a book, or an ISBN.

    Membership numbers and Acc. Nos. are both plain numbers, so the same number can be a member
    and a book. `prefer` says which one the screen is waiting for ("member" or "book")."""
    code = code.strip()
    if not code:
        raise HTTPException(400, "Empty code")
    if prefer == "book":
        b = find_book_by_code(db, code)
        if b:
            return {"type": "book", "book": BookOut.model_validate(b)}
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
        warnings.append(f"{len(overdue)} book(s) overdue.")
    fines = [l for l in m.loans if l.balance > 0]
    unpaid = sum(l.balance for l in fines)
    if unpaid > 0:
        warnings.append(f"Unpaid: Rs. {unpaid:.2f}, added to this payment.")
    recent_from = date.today() - timedelta(days=60)
    recent = [l for l in m.loans if l.return_date and l.return_date >= recent_from and not l.is_lost]
    return {
        "member": MemberOut.model_validate(m),
        "loans": [LoanOut.model_validate(l) for l in loans],
        "fines": [LoanOut.model_validate(l) for l in fines],
        # books handed back in the last 60 days (a damage charge can still be added for them)
        "recent_returns": [LoanOut.model_validate(l) for l in sorted(recent, key=lambda l: l.return_date, reverse=True)[:10]],
        "issue_fee": float(issue_fee_for(m, st)),
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
    # Unpaid charges from earlier (e.g. a late return) do not stop an issue: they are paid on the
    # Payment step together with this issue's fees, on one receipt.
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
    ref = next_txn_ref(db)       # one reference for everything issued in this visit
    fee = issue_fee_for(m, st)   # fee per book for this member's type
    loans = []
    for b in books:
        loan = Loan(book=b, member=m, issue_date=issue_date, due_date=due, issued_by=user.display_name,
                    ref=ref, issue_fee=fee)
        b.status = ISSUED
        db.add(loan)
        loans.append(loan)
    db.flush()
    for loan in loans:
        log_action(db, user, "issue", f"Issued \"{loan.book.title}\" to {m.name} ({m.membership_no}), due {due}, ref {ref}",
                   "loan", loan.id, loan.book.acc_no)
    db.commit()
    db.refresh(m)
    return {"due_date": due, "ref": ref, "fee_per_book": float(fee), "fee_total": float(fee * len(loans)),
            "loans": [LoanOut.model_validate(l) for l in loans], "status": _member_status(m, st)}


@router.post("/cancel-issue")
def cancel_issue(data: CancelIssueIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Take back an issue made today, so the books can be changed. Only while nothing has been paid for it:
    the borrowing records are removed and the books are 'in library' again."""
    loans = [db.get(Loan, i) for i in dict.fromkeys(data.loan_ids)]
    if not loans or any(l is None for l in loans):
        raise HTTPException(404, "These books are no longer issued. Please start again.")
    member = loans[0].member
    for l in loans:
        if l.member_id != member.id:
            raise HTTPException(400, "These books were not issued to the same member")
        if l.return_date is not None:
            raise HTTPException(400, f"\"{l.book.title}\" has already been returned")
        if l.issue_date != date.today():
            raise HTTPException(400, "Only an issue made today can be changed here. Use Return book instead.")
        if l.payments:
            raise HTTPException(400, "A payment has already been taken for these books, so they cannot be changed here. "
                                     "Use Return book instead.")
    for l in loans:
        log_action(db, user, "issue", f"Cancelled the issue of \"{l.book.title}\" to {member.name} ({member.membership_no})"
                   + (f", ref {l.ref}" if l.ref else ""), "loan", l.id, l.book.acc_no)
        l.book.status = AVAILABLE
        db.delete(l)
    db.commit()
    db.refresh(member)
    return _member_status(member, get_settings(db))


def _active_loan(db: Session, acc_no: str) -> Loan:
    b = find_book_by_code(db, acc_no)
    if not b:
        raise HTTPException(404, f"Book {acc_no} not found")
    loan = db.query(Loan).filter(Loan.book_id == b.id, Loan.return_date.is_(None)).first()
    if not loan:
        raise HTTPException(400, f"\"{b.title}\" is not issued to anyone. It is already in the library.")
    return loan


def _fines(db: Session, loan: Loan, returned: date, damaged: bool, st: dict, lost: bool = False) -> dict:
    late_days, late_fine = calc_late(db, loan.due_date, returned, st)
    dmg = damage_fine_for(loan.book, st) if damaged and not lost else 0
    lost_fine = lost_fine_for(loan.book, st) if lost else 0
    if lost:  # a missing book is charged as missing only, not also as late
        late_fine = 0
    fee_due = max(dec(loan.issue_fee) - loan.paid_amount, 0)  # issue fee not paid yet
    return {
        "lost": lost,
        "lost_multiplier": num(st, "lost_multiplier", 2),
        "lost_fine": float(lost_fine),
        "fee_due": float(fee_due),
        "late_days": late_days,
        "calendar_days_late": max((returned - loan.due_date).days, 0),
        "grace_days": int(num(st, "grace_days", 2)),
        "fine_per_day": num(st, "fine_per_day", 2),
        "damage_multiplier": num(st, "damage_multiplier", 2),
        "late_fine": float(late_fine),
        "damage_fine": float(dmg),
        # everything that will be owed for this book once it is handed back, less what is already paid
        "total": float(max(dec(loan.issue_fee) + dec(loan.damage_fine) + dec(late_fine) + dec(dmg) + dec(lost_fine)
                           - loan.paid_amount, 0)),
    }


@router.get("/return-preview")
def return_preview(acc_no: str, damaged: bool = False, lost: bool = False, return_date: Optional[date] = None,
                   db: Session = Depends(get_db), _: User = Depends(current_user)):
    st = get_settings(db)
    loan = _active_loan(db, acc_no)
    returned = return_date or date.today()
    return {"loan": LoanOut.model_validate(loan), "return_date": returned,
            **_fines(db, loan, returned, damaged, st, lost)}


def _do_return(db: Session, user: User, st: dict, loan: Loan, returned: date, damaged: bool, notes: str,
               collect: bool, lost: bool = False, receipt: list = None):
    """Mark one loan returned (or the book missing), work out its charges from its own due date,
    and take the payment if asked."""
    f = _fines(db, loan, returned, damaged, st, lost)
    loan.return_date = returned
    loan.returned_at = datetime.now()
    loan.returned_by = user.display_name
    loan.is_damaged = damaged and not lost
    loan.is_lost = lost
    loan.late_days = f["late_days"]
    loan.late_fine = f["late_fine"]
    loan.damage_fine = dec(loan.damage_fine) + dec(f["damage_fine"]) if f["damage_fine"] else loan.damage_fine
    loan.lost_fine = f["lost_fine"]
    if notes:
        loan.notes = notes
    loan.book.status = LOST if lost else DAMAGED if damaged else AVAILABLE

    payment = None
    if collect and loan.balance > 0:  # everything still owed for this book (fee not yet paid, and penalties)
        note = ", ".join(x for x in (f"{f['late_days']} late day(s)" if f["late_fine"] else "",
                                     "damaged" if f["damage_fine"] else "", "missing" if lost else "") if x)
        if receipt is not None and not receipt:  # the first payment of this return gives the receipt its number
            receipt.append(next_receipt_no(db))
        payment = record_payment(db, loan.member, loan.balance, loan_payment_type(loan), user, loan=loan, notes=note,
                                 receipt_no=receipt[0] if receipt else None)
    detail = []
    if f["late_days"] and not lost:
        detail.append(f"{f['late_days']} day(s) late")
    if lost:
        detail.append("book missing")
    elif damaged:
        detail.append("damaged")
    if f["total"]:
        detail.append(f"fine Rs. {f['total']:.2f}" + (f" paid (receipt {payment.receipt_no})" if payment else " not paid"))
    log_action(db, user, "return", f"{'Missing book' if lost else 'Returned'} \"{loan.book.title}\" from {loan.member.name} ({loan.member.membership_no})"
               + (" - " + ", ".join(detail) if detail else ", on time"), "loan", loan.id, loan.book.acc_no)
    return payment, f


@router.post("/return")
def return_book(data: ReturnIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    st = get_settings(db)
    loan = _active_loan(db, data.acc_no)
    payment, f = _do_return(db, user, st, loan, data.return_date or date.today(), data.damaged, data.notes,
                            data.collect_payment, data.lost)
    db.commit()
    db.refresh(loan)
    return {
        "loan": LoanOut.model_validate(loan),
        "payment": PaymentOut.model_validate(payment) if payment else None,
        **f,
    }


@router.post("/return-many")
def return_many(data: ReturnManyIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Return several books in one go. All or nothing: if one book cannot be returned, none are."""
    st = get_settings(db)
    returned = data.return_date or date.today()
    acc_nos = [i.acc_no.strip() for i in data.items if i.acc_no.strip()]
    if not acc_nos:
        raise HTTPException(400, "Please choose at least one book")
    if len(set(acc_nos)) != len(acc_nos):
        raise HTTPException(400, "The same book is in the list twice")
    loans = [(_active_loan(db, i.acc_no), i.damaged, i.lost) for i in data.items]
    results = []
    receipt = []  # one receipt for everything paid at this return
    for loan, damaged, lost in loans:
        payment, f = _do_return(db, user, st, loan, returned, damaged, data.notes, data.collect_payment, lost, receipt)
        results.append((loan, payment, f))
    db.commit()
    member = loans[0][0].member
    db.refresh(member)
    return {
        "items": [{"loan": LoanOut.model_validate(l), "payment": PaymentOut.model_validate(p) if p else None, **f}
                  for l, p, f in results],
        "total": float(sum(f["total"] for _, _, f in results)),
        "status": _member_status(member, st),
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


@router.post("/charge")
def add_charge(data: ChargeIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Staff add an extra charge for one of the member's books: damaged, or missing.
    The amount comes from the book's price and the settings unless another amount is given.
    It is then collected like any other unpaid charge."""
    st = get_settings(db)
    loan = db.get(Loan, data.loan_id)
    if not loan:
        raise HTTPException(404, "That borrowing record was not found")
    if data.kind == "lost":
        if loan.return_date:
            raise HTTPException(400, "This book has already been returned, so it cannot be marked missing.")
        _do_return(db, user, st, loan, date.today(), False, "", False, lost=True)
        if data.amount is not None:
            loan.lost_fine = max(dec(data.amount), 0)
        amount = loan.lost_fine
    elif data.kind == "damage":
        amount = dec(data.amount) if data.amount is not None else damage_fine_for(loan.book, st)
        if amount <= 0:
            raise HTTPException(400, "The charge must be more than zero. Check the book price, or type the amount.")
        loan.damage_fine = dec(loan.damage_fine) + amount
        loan.is_damaged = True
        if loan.return_date and loan.book.status == AVAILABLE:
            loan.book.status = DAMAGED
        log_action(db, user, "return", f"Damage charge Rs. {float(amount):.2f} added for \"{loan.book.title}\" "
                   f"({loan.member.name}, {loan.member.membership_no})", "loan", loan.id, loan.book.acc_no)
    else:
        raise HTTPException(400, "Unknown kind of charge")
    db.commit()
    db.refresh(loan.member)
    return {"loan": LoanOut.model_validate(loan), "amount": float(amount), "status": _member_status(loan.member, st)}
