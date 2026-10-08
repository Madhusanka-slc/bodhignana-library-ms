from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import inspect, text
from fastapi.middleware.cors import CORSMiddleware

from .auth import hash_password
from .config import settings
from .database import Base, SessionLocal, engine
from .models import User
from .routers import auth, books, circulation, codes, holidays, members, payments, reports, search
from .routers import settings as settings_router


def upgrade_db():
    """Add columns that newer versions need to a database created by an older version."""
    loan_cols = {c["name"] for c in inspect(engine).get_columns("loans")}
    book_cols = {c["name"] for c in inspect(engine).get_columns("books")}
    member_cols = {c["name"] for c in inspect(engine).get_columns("members")}
    with engine.begin() as conn:
        if "returned_at" not in loan_cols:
            conn.execute(text("ALTER TABLE loans ADD COLUMN returned_at TIMESTAMP"))
        if "cover_image" not in book_cols:
            conn.execute(text("ALTER TABLE books ADD COLUMN cover_image VARCHAR(200) NOT NULL DEFAULT ''"))
        if "photo_image" not in member_cols:
            conn.execute(text("ALTER TABLE members ADD COLUMN photo_image VARCHAR(200) NOT NULL DEFAULT ''"))
        if "created_by" not in member_cols:
            conn.execute(text("ALTER TABLE members ADD COLUMN created_by VARCHAR(100) NOT NULL DEFAULT ''"))


def init_db():
    Base.metadata.create_all(engine)
    upgrade_db()
    with SessionLocal() as db:
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
