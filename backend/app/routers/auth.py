from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import admin_required, create_token, current_user, hash_password, verify_password
from ..database import get_db
from ..models import User
from ..schemas import LoginIn, PasswordChange, UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/api", tags=["auth & users"])


@router.post("/auth/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username.strip()).first()
    if not user or not user.is_active or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Wrong username or password")
    return {"token": create_token(user), "user": UserOut.model_validate(user)}


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user


@router.post("/auth/change-password")
def change_password(data: PasswordChange, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if not verify_password(data.old_password, user.password_hash):
        raise HTTPException(400, "Current password is wrong")
    if len(data.new_password) < 6:
        raise HTTPException(400, "New password must have at least 6 characters")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"ok": True}


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(admin_required)):
    return db.query(User).order_by(User.id).all()


@router.post("/users", response_model=UserOut)
def create_user(data: UserCreate, db: Session = Depends(get_db), _: User = Depends(admin_required)):
    username = data.username.strip()
    if not username or len(data.password) < 6:
        raise HTTPException(400, "Username is required and password must have at least 6 characters")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(400, "This username is already used")
    u = User(username=username, full_name=data.full_name, role=data.role,
             password_hash=hash_password(data.password))
    db.add(u)
    db.commit()
    return u


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db), me_: User = Depends(admin_required)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    if data.full_name is not None:
        u.full_name = data.full_name
    if data.role is not None:
        u.role = data.role
    if data.is_active is not None:
        if u.id == me_.id and not data.is_active:
            raise HTTPException(400, "You cannot disable your own account")
        u.is_active = data.is_active
    if data.password:
        if len(data.password) < 6:
            raise HTTPException(400, "Password must have at least 6 characters")
        u.password_hash = hash_password(data.password)
    db.commit()
    return u
