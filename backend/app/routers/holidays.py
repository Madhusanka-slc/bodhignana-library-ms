from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..models import Holiday, User
from ..schemas import BulkHolidayIn, HolidayIn, HolidayOut
from ..services import log_action

router = APIRouter(prefix="/api/holidays", tags=["holidays"])


@router.get("", response_model=list[HolidayOut])
def list_holidays(year: int = 0, db: Session = Depends(get_db), _: User = Depends(current_user)):
    year = year or date.today().year
    return (db.query(Holiday).filter(Holiday.day >= date(year, 1, 1), Holiday.day <= date(year, 12, 31))
            .order_by(Holiday.day).all())


@router.post("", response_model=HolidayOut)
def add_holiday(data: HolidayIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    h = db.query(Holiday).filter(Holiday.day == data.day).first()
    if h:
        h.description = data.description
    else:
        h = Holiday(day=data.day, description=data.description)
        db.add(h)
    db.flush()
    log_action(db, user, "holiday", f"Marked {data.day} as a holiday ({data.description})", "holiday", h.id)
    db.commit()
    return h


@router.post("/bulk-weekday")
def add_weekday(data: BulkHolidayIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Mark every Sunday (or any weekday) of a year as a holiday."""
    if not 0 <= data.weekday <= 6:
        raise HTTPException(400, "Weekday must be 0 (Monday) to 6 (Sunday)")
    d = date(data.year, 1, 1)
    existing = {h.day for h in db.query(Holiday.day).filter(
        Holiday.day >= d, Holiday.day <= date(data.year, 12, 31)).all()}
    added = 0
    while d.year == data.year:
        if d.weekday() == data.weekday and d not in existing:
            db.add(Holiday(day=d, description=data.description))
            added += 1
        d += timedelta(days=1)
    day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][data.weekday]
    log_action(db, user, "holiday", f"Marked every {day_name} of {data.year} as a holiday ({added} days, {data.description})",
               "holiday")
    db.commit()
    return {"added": added}


@router.delete("/{holiday_id}")
def delete_holiday(holiday_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    h = db.get(Holiday, holiday_id)
    if h:
        log_action(db, user, "holiday", f"Removed the holiday on {h.day} ({h.description})", "holiday", h.id)
        db.delete(h)
        db.commit()
    return {"ok": True}
