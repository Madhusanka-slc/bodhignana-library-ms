from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import User

_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.TOKEN_HOURS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def current_user(
    cred: HTTPAuthorizationCredentials = Depends(_bearer), db: Session = Depends(get_db)
) -> User:
    if not cred:
        raise HTTPException(401, "Please log in")
    try:
        payload = jwt.decode(cred.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        user = db.get(User, int(payload["sub"]))
    except Exception:
        raise HTTPException(401, "Your session has expired. Please log in again.")
    if not user or not user.is_active:
        raise HTTPException(401, "Please log in")
    return user


def admin_required(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Only an administrator can do this")
    return user
