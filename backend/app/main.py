from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import hash_password
from .config import settings
from .database import Base, SessionLocal, engine
from .models import User
from .routers import auth, books, circulation, codes, holidays, members, payments, reports, search
from .routers import settings as settings_router


def init_db():
    Base.metadata.create_all(engine)
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


@app.get("/api/health")
def health():
    return {"status": "ok"}
