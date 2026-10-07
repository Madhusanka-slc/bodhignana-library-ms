from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import admin_required, current_user
from ..database import get_db
from ..models import AppSetting, User
from ..services import DEFAULT_SETTINGS, get_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def read_settings(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return get_settings(db)


@router.put("")
def save_settings(data: dict, db: Session = Depends(get_db), _: User = Depends(admin_required)):
    for key, value in data.items():
        if key not in DEFAULT_SETTINGS:
            continue
        row = db.get(AppSetting, key)
        if row:
            row.value = str(value)
        else:
            db.add(AppSetting(key=key, value=str(value)))
    db.commit()
    return get_settings(db)
