from fastapi import APIRouter
from pydantic import BaseModel

from app.auth import login
from app.config import get_settings

router = APIRouter(prefix="/api/auth")


class LoginRequest(BaseModel):
    password: str


@router.post("/login")
def login_route(body: LoginRequest) -> dict:
    return {"token": login(body.password)}


@router.get("/status")
def status_route() -> dict:
    return {"auth_enabled": bool(get_settings().dashboard_token)}
