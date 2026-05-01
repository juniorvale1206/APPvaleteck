from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request

from core.config import JWT_ACCESS_MINUTES
from core.database import db
from core.rate_limit import limiter
from core.security import (
    create_access_token, create_refresh_token,
    decode_refresh_token, get_current_user, verify_password,
)
from models.auth import (
    LoginInput, RefreshIn, RefreshOut,
    TokenOut, UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
@limiter.limit("10/minute")
async def login(request: Request, payload: LoginInput):
    email = payload.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    access = create_access_token(user["id"], email)
    refresh = create_refresh_token(user["id"], email)
    return TokenOut(
        token=access,
        access_token=access,
        refresh_token=refresh,
        expires_in=JWT_ACCESS_MINUTES * 60,
        user=UserOut(id=user["id"], email=user["email"], name=user["name"], role=user["role"]),
    )


@router.post("/refresh", response_model=RefreshOut)
@limiter.limit("30/minute")
async def refresh(request: Request, payload: RefreshIn):
    data = decode_refresh_token(payload.refresh_token)
    user = await db.users.find_one({"id": data["sub"]})
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    access = create_access_token(user["id"], user["email"])
    new_refresh = create_refresh_token(user["id"], user["email"])
    return RefreshOut(
        token=access,
        access_token=access,
        refresh_token=new_refresh,
        expires_in=JWT_ACCESS_MINUTES * 60,
    )


@router.get("/me", response_model=UserOut)
async def me(user=Depends(get_current_user)):
    return UserOut(id=user["id"], email=user["email"], name=user["name"], role=user["role"])


@router.post("/logout")
async def logout(user=Depends(get_current_user)):
    return {"ok": True}
