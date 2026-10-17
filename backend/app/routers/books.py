from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import current_user
from ..config import settings
from ..database import get_db
from ..images import copy_picture, delete_picture, picture_response, save_picture
from ..models import AVAILABLE, DAMAGED, ISSUED, LOST, WITHDRAWN, Book, User
from ..schemas import AddCopiesIn, BookIn, BookOut, BookPage, DoneIn, LoanOut, PictureIn, SameBookIn, StatusIn
from ..services import book_search_filter, copy_counts, log_action, match_title, next_acc_no

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
    return {"total": total, "items": copy_counts(db, items)}


@router.get("/title-match")
def title_match(isbn: str = "", title: str = "", persons: str = "", db: Session = Depends(get_db), _: User = Depends(current_user)):
    """While a new book is typed: is it already in the library? (to add copies instead of typing it again)"""
    return [BookOut.model_validate(b) for b in copy_counts(db, match_title(db, isbn, title, persons))]


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
def create_book(data: BookIn, copy_of: Optional[int] = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """A new book. copy_of: it is another copy of that book (linked to it)."""
    b = Book(status=AVAILABLE)
    _apply(db, b, data, user)
    db.add(b)
    db.flush()
    src = db.get(Book, copy_of) if copy_of else None
    b.title_id = (src.title_id or src.id) if src else b.id
    log_action(db, user, "book_add", f"Added book \"{b.title}\" ({b.section or 'no section'})", "book", b.id, b.acc_no)
    db.commit()
    db.refresh(b)
    return b


@router.get("/{book_id}")
def book_detail(book_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    b = get_book_or_404(db, book_id)
    copy_counts(db, [b])
    return {"book": BookOut.model_validate(b), "loans": [LoanOut.model_validate(l) for l in b.loans[:200]]}


# ---------- Copies of the same book ----------
def _copies_of(db: Session, b: Book) -> list[Book]:
    return db.query(Book).filter(func.coalesce(Book.title_id, Book.id) == (b.title_id or b.id)).order_by(Book.id).all()


@router.get("/{book_id}/copies")
def copies(book_id: int, db: Session = Depends(get_db), _: User = Depends(current_user)):
    """Every copy of this book: where each one is (in the library, with whom, damaged...)."""
    b = get_book_or_404(db, book_id)
    items = _copies_of(db, b)
    use = [x for x in items if not x.withdrawn]
    count = lambda st: sum(1 for x in use if x.status == st)
    return {
        "total": len(use), "in_library": count(AVAILABLE), "with_members": count(ISSUED),
        "damaged": count(DAMAGED), "lost": count(LOST), "withdrawn": len(items) - len(use),
        "items": [BookOut.model_validate(x) for x in items],
    }


FIELDS_NOT_COPIED = {"id", "acc_no", "status", "label_done", "label_done_at", "label_done_by", "withdrawn", "withdrawn_by",
                     "withdrawn_date", "created_at", "updated_at", "date_entered", "entered_by", "cover_image"}


@router.post("/{book_id}/add-copies")
def add_copies(book_id: int, data: AddCopiesIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """More copies of a book the library already has (bought again, or donated). The details come from
    this book; only what differs (year, edition, price, place) is given. Each copy gets its own Acc. No."""
    src = get_book_or_404(db, book_id)
    accs = [a.strip() for a in data.acc_nos if a.strip()]
    count = len(accs) or data.count
    if count < 1 or count > 200:
        raise HTTPException(400, "Add between 1 and 200 copies at a time")
    if len(set(accs)) != len(accs):
        raise HTTPException(400, "The same Acc. No. is given twice")
    for a in accs:
        clash = db.query(Book).filter(Book.acc_no == a).first()
        if clash:
            raise HTTPException(400, f"Acc. No. {a} is already used by \"{clash.title}\"")
    base = {c.key: getattr(src, c.key) for c in Book.__table__.columns if c.key not in FIELDS_NOT_COPIED}
    base["title_id"] = src.title_id or src.id
    for k in ("year_of_publication", "edition", "price", "rack_no", "shelf_no", "remarks"):
        v = getattr(data, k)
        if v is not None:
            base[k] = v
    made = []
    for n in range(count):
        b = Book(**base, acc_no=accs[n] if accs else next_acc_no(db), status=AVAILABLE,
                 date_entered=date.today(), entered_by=user.display_name)
        db.add(b)
        db.flush()
        if src.cover_image:
            try:  # the same front cover; a missing picture file does not stop the copies being added
                b.cover_image = copy_picture(settings.COVERS_DIR, src.cover_image, b.id)
            except HTTPException:
                pass
        made.append(b)
    log_action(db, user, "book_add", f"Added {count} cop{'y' if count == 1 else 'ies'} of \"{src.title}\": "
               + ", ".join(b.acc_no for b in made), "book", src.id, src.acc_no)
    db.commit()
    total = db.query(Book).filter(Book.title_id == base["title_id"], Book.withdrawn.is_(False)).count()
    return {"added": [BookOut.model_validate(b) for b in made], "copies": total}


@router.post("/{book_id}/same-as")
def same_as(book_id: int, data: SameBookIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Staff correct the link: this book (with its copies) is the same book as the one with that Acc. No."""
    b = get_book_or_404(db, book_id)
    other = db.query(Book).filter(func.lower(Book.acc_no) == data.code.strip().lower()).first()
    if not other:
        raise HTTPException(404, f"No book with Acc. No. {data.code}")
    a, o = b.title_id or b.id, other.title_id or other.id
    if a == o:
        raise HTTPException(400, "These are already copies of the same book")
    target = min(a, o)
    db.query(Book).filter(func.coalesce(Book.title_id, Book.id).in_([a, o])).update(
        {Book.title_id: target}, synchronize_session=False)
    db.expire_all()  # books already loaded must see the new link
    log_action(db, user, "book_edit", f"Linked \"{b.title}\" ({b.acc_no}) as the same book as \"{other.title}\" ({other.acc_no})",
               "book", b.id, b.acc_no)
    db.commit()
    return copies(book_id, db, user)


@router.post("/{book_id}/separate")
def separate(book_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Staff correct the link: this copy is a different book from the others it was linked to."""
    b = get_book_or_404(db, book_id)
    tid = b.title_id or b.id
    rest = [x for x in _copies_of(db, b) if x.id != b.id]
    if not rest:
        raise HTTPException(400, "This book has no other copies linked to it")
    if tid == b.id:  # this copy gave the others their number: they take the next one's
        new = min(x.id for x in rest)
        for x in rest:
            x.title_id = new
    b.title_id = b.id
    log_action(db, user, "book_edit", f"Separated \"{b.title}\" ({b.acc_no}) from the other copies", "book", b.id, b.acc_no)
    db.commit()
    return copies(book_id, db, user)


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
