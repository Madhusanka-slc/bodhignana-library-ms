from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import admin_required, current_user
from ..database import get_db
from ..models import AppSetting, User
from ..services import DEFAULT_SETTINGS, get_settings, log_action

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def read_settings(db: Session = Depends(get_db), _: User = Depends(current_user)):
    return get_settings(db)


@router.put("")
def save_settings(data: dict, db: Session = Depends(get_db), user: User = Depends(admin_required)):
    before = get_settings(db)
    changed = []
    for key, value in data.items():
        if key not in DEFAULT_SETTINGS:
            continue
        if str(before.get(key, "")) != str(value):
            changed.append(f"{key.replace('_', ' ')}: {before.get(key, '')} -> {value}")
        row = db.get(AppSetting, key)
        if row:
            row.value = str(value)
        else:
            db.add(AppSetting(key=key, value=str(value)))
    if changed:
        log_action(db, user, "settings", "Changed settings - " + "; ".join(changed), "settings")
    db.commit()
    return get_settings(db)
