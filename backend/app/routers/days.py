from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user
from app.services.data_service import data_service
from app.services.privacy import redact_day, redact_days

router = APIRouter(prefix="/days", tags=["days"])


@router.get("")
def list_days(user: dict = Depends(get_current_user)):
    return redact_days(data_service.get_all_days(), user["role"])


@router.get("/{date}")
def get_day(date: str, user: dict = Depends(get_current_user)):
    day = data_service.get_day(date)
    if not day:
        raise HTTPException(status_code=404, detail="Day not found")
    return redact_day(day, user["role"])
