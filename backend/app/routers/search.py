from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..models import Book, Member
from ..schemas import BookOut, MemberOut
from ..services import book_search_filter, member_search_filter

router = APIRouter(prefix="/api/search", tags=["search"], dependencies=[Depends(current_user)])


@router.get("")
def search(q: str = "", section: str = "", include_members: bool = True, db: Session = Depends(get_db)):
    """One search box for everything: books (with where to find them) and members."""
    q = q.strip()
    if not q and not section:
        return {"books": [], "members": []}
    bq = db.query(Book).filter(Book.withdrawn.is_(False))
    if q:
        bq = bq.filter(book_search_filter(q))
    if section:
        bq = bq.filter(Book.section == section)
    # An exact Acc. No. / membership no. comes first, then the rest by name
    exact_book = (func.lower(Book.acc_no) == q.lower()).desc()
    books = bq.order_by(exact_book, Book.title, Book.acc_no).limit(100).all()
    members = []
    if include_members and q:
        members = db.query(Member).filter(member_search_filter(q)).order_by((func.lower(Member.membership_no) == q.lower()).desc(), Member.name).limit(30).all()
    return {
        "books": [BookOut.model_validate(b) for b in books],
        "members": [MemberOut.model_validate(m) for m in members],
    }
