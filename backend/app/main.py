from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import inspect, text
from fastapi.middleware.cors import CORSMiddleware

from .auth import hash_password
from .config import settings
from .services import group_titles
from .database import Base, SessionLocal, engine
from .models import User
from .routers import auth, books, circulation, codes, holidays, members, payments, reports, search
from .routers import settings as settings_router


def upgrade_db():
    """Add columns that newer versions need to a database created by an older version."""
    loan_cols = {c["name"] for c in inspect(engine).get_columns("loans")}
    book_cols = {c["name"] for c in inspect(engine).get_columns("books")}
    member_cols = {c["name"] for c in inspect(engine).get_columns("members")}
    # Look everything up BEFORE changing anything: a look-up made while the change below is still open would wait for it forever
    payment_cols = {c["name"] for c in inspect(engine).get_columns("payments")}
    receipt_unique = any(ix["name"] == "ix_payments_receipt_no" and ix.get("unique") for ix in inspect(engine).get_indexes("payments"))
    with engine.begin() as conn:
        if "returned_at" not in loan_cols:
            conn.execute(text("ALTER TABLE loans ADD COLUMN returned_at TIMESTAMP"))
        if "ref" not in loan_cols:
            conn.execute(text("ALTER TABLE loans ADD COLUMN ref VARCHAR(20) NOT NULL DEFAULT ''"))
            conn.execute(text("ALTER TABLE loans ADD COLUMN issue_fee NUMERIC(10, 2) NOT NULL DEFAULT 0"))
            conn.execute(text("ALTER TABLE loans ADD COLUMN is_lost BOOLEAN NOT NULL DEFAULT FALSE"))
            conn.execute(text("ALTER TABLE loans ADD COLUMN lost_fine NUMERIC(10, 2) NOT NULL DEFAULT 0"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_loans_ref ON loans (ref)"))
        # receipt numbers may now repeat (one receipt for several books): the index must not be unique
        if receipt_unique:
            conn.execute(text("DROP INDEX ix_payments_receipt_no"))
            conn.execute(text("CREATE INDEX ix_payments_receipt_no ON payments (receipt_no)"))
        if "ref" not in payment_cols:
            conn.execute(text("ALTER TABLE payments ADD COLUMN ref VARCHAR(20) NOT NULL DEFAULT ''"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_payments_ref ON payments (ref)"))
        if "title_id" not in book_cols:
            conn.execute(text("ALTER TABLE books ADD COLUMN title_id INTEGER"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_books_title_id ON books (title_id)"))
        if "cover_image" not in book_cols:
            conn.execute(text("ALTER TABLE books ADD COLUMN cover_image VARCHAR(200) NOT NULL DEFAULT ''"))
        if "photo_image" not in member_cols:
            conn.execute(text("ALTER TABLE members ADD COLUMN photo_image VARCHAR(200) NOT NULL DEFAULT ''"))
        if "created_by" not in member_cols:
            conn.execute(text("ALTER TABLE members ADD COLUMN created_by VARCHAR(100) NOT NULL DEFAULT ''"))
        for table, cols, prefix in (("books", book_cols, "label"), ("members", member_cols, "card")):
            if f"{prefix}_done" not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {prefix}_done BOOLEAN NOT NULL DEFAULT FALSE"))
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {prefix}_done_at TIMESTAMP"))
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {prefix}_done_by VARCHAR(100) NOT NULL DEFAULT ''"))
                conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{table}_{prefix}_done ON {table} ({prefix}_done)"))


def init_db():
    Base.metadata.create_all(engine)
    upgrade_db()
    with SessionLocal() as db:
        # Copies of the same book: linked automatically the first time (staff can correct them later).
        # A book saved without a link (older way of adding) is a book of its own.
        if db.execute(text("SELECT 1 FROM books WHERE title_id IS NOT NULL LIMIT 1")).first() is None:
            group_titles(db)
        else:
            db.execute(text("UPDATE books SET title_id = id WHERE title_id IS NULL"))
            db.commit()
        if not db.query(User).first():
            db.add(User(username=settings.ADMIN_USERNAME, full_name="Administrator", role="admin",
                        password_hash=hash_password(settings.ADMIN_PASSWORD)))
            db.commit()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Library Management System", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

for r in (auth, members, books, circulation, search, reports, payments, holidays, settings_router, codes):
    app.include_router(r.router)
app.include_router(books.covers)  # cover pictures and member photos are public so <img> tags can load them
app.include_router(members.photos)


@app.get("/api/health")
def health():
    return {"status": "ok"}
