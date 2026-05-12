from fastapi import APIRouter, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends
from app.auth import USERS, create_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends()):
    user = USERS.get(form.username)
    if not user or user["password"] != form.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(form.username, user["role"])
    return {"access_token": token, "token_type": "bearer", "role": user["role"]}
