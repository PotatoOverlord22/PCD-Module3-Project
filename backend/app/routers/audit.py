from fastapi import APIRouter, Depends
from app.auth import require_admin
from app.middleware.audit_log import get_audit_log

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit_log(user: dict = Depends(require_admin)):
    return get_audit_log()
