from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import current_user
from ..config import settings
from ..database import get_db
from ..images import copy_picture, delete_picture, picture_response, save_picture
from ..models import AVAILABLE, DAMAGED, ISSUED, LOST, WITHDRAWN, Book, User
from ..schemas import BookIn, BookOut, BookPage, DoneIn, LoanOut, PictureIn, StatusIn
from ..services import book_search_filter, log_action, next_acc_no

router = APIRouter(prefix="/api/books", tags=["books"])
covers = APIRouter(prefix="/api/covers", tags=["books"])
COVER_MAX = (600, 900)  # pixels; front covers are stored no larger than this


def get_book_or_404(db: Session, book_id: int) -> Book:
    b = db.get(Book, book_id)
    if not b:
        raise HTTPException(404, "Book not found")
    return b


@router.get("", response_model=BookPage)
def list_books(q: str = "", section: str = "", status: str = "", label: str = "", page: int = 1, size: int = 25,
               db: Session = Depends(get_db), _: User = Depends(current_user)):
    query = db.query(Book)
    if q.strip():
        query = query.filter(book_search_filter(q))
    if section:
        query = query.filter(Book.section == section)
    if status:
        query = query.filter(Book.status == status)
    if label in ("yes", "no"):
        query = query.filter(Book.label_done.is_(label == "yes"))
    total = query.count()
    size = max(1, min(size, 500))
    # When searching, an exact Acc. No. comes first
    order = [(func.lower(Book.acc_no) == q.strip().lower()).desc()] if q.strip() else []
    items = query.order_by(*order, Book.id.desc()).offset((max(page, 1) - 1) * size).limit(size).all()
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
    db.flush()
    log_action(db, user, "book_add", f"Added book \"{b.title}\" ({b.section or 'no section'})", "book", b.id, b.acc_no)
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
    log_action(db, user, "book_edit", f"Edited book \"{b.title}\"", "book", b.id, b.acc_no)
    db.commit()
    db.refresh(b)
    return b


# ---------- QR label: is the printed label stuck on the book? ----------
def _set_label(b: Book, done: bool, user: User):
    b.label_done = done
    b.label_done_at = datetime.now() if done else None
    b.label_done_by = user.display_name if done else ""


@router.post("/labels")
def set_labels(data: DoneIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Mark several books at once as labelled / not labelled."""
    books = db.query(Book).filter(Book.id.in_(data.ids[:2000])).all() if data.ids else []
    changed = [b for b in books if b.label_done != data.done]
    for b in changed:
        _set_label(b, data.done, user)
    if changed:
        nos = ", ".join(b.acc_no for b in changed[:15]) + (" ..." if len(changed) > 15 else "")
        log_action(db, user, "book_label", f"Marked {len(changed)} book(s) as {'labelled' if data.done else 'not labelled'}: {nos}",
                   "book", changed[0].id if len(changed) == 1 else None, changed[0].acc_no if len(changed) == 1 else "")
    db.commit()
    return {"changed": len(changed)}


@router.post("/{book_id}/label", response_model=BookOut)
def set_label(book_id: int, data: DoneIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    b = get_book_or_404(db, book_id)
    _set_label(b, data.done, user)
    log_action(db, user, "book_label", f"Marked \"{b.title}\" as {'labelled' if data.done else 'not labelled'}", "book", b.id, b.acc_no)
    db.commit()
    db.refresh(b)
    return b


# ---------- Front cover pictures (optional) ----------
@router.post("/{book_id}/cover", response_model=BookOut)
def set_cover(book_id: int, data: PictureIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Save a front cover picture (sent as a data URL), or copy the cover of another copy."""
    b = get_book_or_404(db, book_id)
    if data.copy_from:
        name = copy_picture(settings.COVERS_DIR, get_book_or_404(db, data.copy_from).cover_image, b.id)
    else:
        name = save_picture(data.image, settings.COVERS_DIR, b.id, COVER_MAX)
    delete_picture(settings.COVERS_DIR, b.cover_image)
    b.cover_image = name
    log_action(db, user, "book_cover", f"Set the front cover of \"{b.title}\"", "book", b.id, b.acc_no)
    db.commit()
    db.refresh(b)
    return b


@router.delete("/{book_id}/cover", response_model=BookOut)
def remove_cover(book_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    b = get_book_or_404(db, book_id)
    delete_picture(settings.COVERS_DIR, b.cover_image)
    b.cover_image = ""
    log_action(db, user, "book_cover", f"Removed the front cover of \"{b.title}\"", "book", b.id, b.acc_no)
    db.commit()
    db.refresh(b)
    return b


@covers.get("/{name}")
def cover_file(name: str):
    return picture_response(settings.COVERS_DIR, name)


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
    log_action(db, user, "book_status", f"Marked \"{b.title}\" as {data.status.lower()}"
               + (f" ({data.reason})" if data.reason else ""), "book", b.id, b.acc_no)
    db.commit()
    db.refresh(b)
    return b
