from fastapi import APIRouter, Depends
from app.auth import get_current_user
from app.services.data_service import data_service
from app.services.privacy import redact_days

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.get("")
def list_anomalies(user: dict = Depends(get_current_user)):
    return redact_days(data_service.get_anomalies(), user["role"])


@router.get("/evaluation")
def get_evaluation(user: dict = Depends(get_current_user)):
    # Evaluation metrics are aggregate, not per-day activity — admin-style data.
    # We keep them unredacted; the Evaluation tab is admin-only on the frontend.
    return data_service.get_evaluation()
