from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.auth.password_policy import validate_password
from app.db import get_async_db

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    user_id: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_async_db)):
    pw_error = validate_password(body.password)
    if pw_error:
        raise HTTPException(status_code=400, detail=pw_error)

    existing = await db.execute(
        text("SELECT id FROM users WHERE email = :email"), {"email": body.email}
    )
    if existing.fetchone():
        raise HTTPException(status_code=400, detail="Email already registered")

    result = await db.execute(
        text(
            "INSERT INTO users (email, password_hash) VALUES (:email, :pw) RETURNING id"
        ),
        {"email": body.email, "pw": hash_password(body.password)},
    )
    row = result.fetchone()
    user_id = str(row[0])

    # Create default portfolio
    await db.execute(
        text("INSERT INTO portfolios (user_id, name) VALUES (:uid, 'My Portfolio')"),
        {"uid": user_id},
    )

    return {
        "user_id": user_id,
        "access_token": create_access_token(user_id),
        "refresh_token": create_refresh_token(user_id),
        "token_type": "bearer",
    }


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(
        text("SELECT id, password_hash FROM users WHERE email = :email"), {"email": body.email}
    )
    row = result.fetchone()
    if not row or not verify_password(body.password, row[1]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id = str(row[0])
    return TokenResponse(
        user_id=user_id,
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_async_db)):
    payload = decode_token(body.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload["sub"]
    result = await db.execute(text("SELECT id FROM users WHERE id = :uid"), {"uid": user_id})
    if not result.fetchone():
        raise HTTPException(status_code=401, detail="User not found")

    return TokenResponse(
        user_id=user_id,
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )
