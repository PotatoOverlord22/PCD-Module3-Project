from fastapi import APIRouter, Depends
from app.auth import get_current_user
from app.services.data_service import data_service

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.get("")
def list_anomalies(user: dict = Depends(get_current_user)):
    return data_service.get_anomalies()


@router.get("/evaluation")
def get_evaluation(user: dict = Depends(get_current_user)):
    return data_service.get_evaluation()
