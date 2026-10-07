from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..models import AVAILABLE, DAMAGED, ISSUED, LOST, WITHDRAWN, Book, User
from ..schemas import BookIn, BookOut, BookPage, LoanOut, StatusIn
from ..services import book_search_filter, next_acc_no

router = APIRouter(prefix="/api/books", tags=["books"])


def get_book_or_404(db: Session, book_id: int) -> Book:
    b = db.get(Book, book_id)
    if not b:
        raise HTTPException(404, "Book not found")
    return b


@router.get("", response_model=BookPage)
def list_books(q: str = "", section: str = "", status: str = "", page: int = 1, size: int = 25,
               db: Session = Depends(get_db), _: User = Depends(current_user)):
    query = db.query(Book)
    if q.strip():
        query = query.filter(book_search_filter(q))
    if section:
        query = query.filter(Book.section == section)
    if status:
        query = query.filter(Book.status == status)
    total = query.count()
    size = max(1, min(size, 500))
    items = query.order_by(Book.id.desc()).offset((max(page, 1) - 1) * size).limit(size).all()
    return {"total": total, "items": items}


def _apply(db: Session, b: Book, data: BookIn, user: User):
    values = data.model_dump()
    values["title"] = values["title"].strip()
    if not values["title"]:
        raise HTTPException(400, "Title is required")
    acc = values["acc_no"].strip() or (next_acc_no(db) if not b.id else "")
    if not acc:
        raise HTTPException(400, "Acc. No. is required")
    clash = db.query(Book).filter(Book.acc_no == acc, Book.id != (b.id or 0)).first()
    if clash:
        raise HTTPException(400, f"Acc. No. {acc} is already used by \"{clash.title}\"")
    values["acc_no"] = acc
    values["date_entered"] = values["date_entered"] or b.date_entered or date.today()
    values["entered_by"] = values["entered_by"] or b.entered_by or user.display_name
    for k, v in values.items():
        setattr(b, k, v)


@router.post("", response_model=BookOut)
def create_book(data: BookIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    b = Book(status=AVAILABLE)
    _apply(db, b, data, user)
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


@router.get("/{book_id}")
def book_detail(book_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    b = get_book_or_404(db, book_id)
    return {"book": BookOut.model_validate(b), "loans": [LoanOut.model_validate(l) for l in b.loans[:200]]}


@router.put("/{book_id}", response_model=BookOut)
def update_book(book_id: int, data: BookIn, db: Session = Depends(get_db),
                user: User = Depends(current_user)):
    b = get_book_or_404(db, book_id)
    _apply(db, b, data, user)
    db.commit()
    db.refresh(b)
    return b


@router.post("/{book_id}/status", response_model=BookOut)
def change_status(book_id: int, data: StatusIn, db: Session = Depends(get_db),
                  user: User = Depends(current_user)):
    """Mark a book Available / Damaged / Lost / Withdrawn."""
    b = get_book_or_404(db, book_id)
    if data.status not in (AVAILABLE, DAMAGED, LOST, WITHDRAWN):
        raise HTTPException(400, "Unknown status")
    if b.status == ISSUED:
        raise HTTPException(400, "This book is issued. Please return it first.")
    b.status = data.status
    if data.status == WITHDRAWN:
        b.withdrawn = True
        b.withdrawn_by = user.display_name
        b.withdrawn_date = date.today()
    else:
        b.withdrawn = False
        b.withdrawn_by = ""
        b.withdrawn_date = None
    if data.reason:
        note = f"[{date.today()}] {data.status}: {data.reason}"
        b.remarks = f"{b.remarks}\n{note}".strip()
    db.commit()
    db.refresh(b)
    return b
