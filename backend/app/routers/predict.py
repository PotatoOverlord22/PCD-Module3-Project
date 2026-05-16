from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.auth import get_current_user
from app.services.ml_service import ml_service
from app.services.privacy import redact_predict_response

router = APIRouter(prefix="/predict", tags=["predict"])


class SensorEvent(BaseModel):
    time: str
    sensor: str
    state: str


class PredictRequest(BaseModel):
    date: str
    events: list[SensorEvent]


@router.post("")
def predict_day(request: PredictRequest, user: dict = Depends(get_current_user)):
    events = [e.model_dump() for e in request.events]
    results = ml_service.predict_day(events)
    response = {
        "date": request.date,
        "rooms": results,
        "total_events": len(request.events),
    }
    return redact_predict_response(response, user["role"])
