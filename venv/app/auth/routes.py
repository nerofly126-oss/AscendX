from fastapi import (
    APIRouter, Depends, HTTPException, Request, BackgroundTasks
)
from sqlalchemy.orm import Session
from fastapi_mail import FastMail, MessageSchema
from slowapi import Limiter
from slowapi.util import get_remote_address
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from datetime import datetime
import secrets
import re

from app.database import SessionLocal
from app.models import User
from app.schemas import (
    UserCreate, UserLogin, TokenPair,
    RefreshRequest, ResetPasswordRequest,
    GoogleOneTapRequest, ForgotPasswordRequest
)
from app.auth.utils import (
    hash_password, verify_password,
    create_access_token, verify_token
)
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])
limiter = Limiter(key_func=get_remote_address)



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



def validate_password_strength(password: str):
    if len(password) < 8:
        raise HTTPException(400, "Password too short")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(400, "Missing uppercase letter")
    if not re.search(r"[0-9]", password):
        raise HTTPException(400, "Missing number")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise HTTPException(400, "Missing special character")
    


def generate_tokens(user_id: int):
    access = create_access_token({"sub": str(user_id)}, expires_minutes=15)
    refresh_raw = secrets.token_hex(32)
    refresh_hashed = hash_password(refresh_raw)
    return access, refresh_raw, refresh_hashed


@router.post("/signup")
@limiter.limit("5/minute")
def signup(
    request: Request,
    user: UserCreate,
    db: Session = Depends(get_db)
):
    validate_password_strength(user.password)

    if db.query(User).filter(
        (User.username == user.username) | (User.email == user.email)
    ).first():
        raise HTTPException(400, "User already exists")

    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hash_password(user.password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access, refresh_raw, refresh_hashed = generate_tokens(new_user.id)
    new_user.refresh_token = refresh_hashed
    db.commit()

    return TokenPair(access_token=access, refresh_token=refresh_raw)


@router.post("/login")
@limiter.limit("10/minute")
def login(
    request: Request,
    user: UserLogin,
    db: Session = Depends(get_db)
):
    db_user = db.query(User).filter(User.username == user.username).first()

    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(401, "Invalid credentials")

    access, refresh_raw, refresh_hashed = generate_tokens(db_user.id)
    db_user.refresh_token = refresh_hashed
    db.commit()

    return TokenPair(access_token=access, refresh_token=refresh_raw)


@router.post("/refresh")
def refresh(
    data: RefreshRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.refresh_token.isnot(None)).first()

    if not user or not verify_password(data.refresh_token, user.refresh_token):
        raise HTTPException(401, "Invalid refresh token")

    access, new_refresh_raw, new_refresh_hashed = generate_tokens(user.id)
    user.refresh_token = new_refresh_hashed
    db.commit()

    return TokenPair(access_token=access, refresh_token=new_refresh_raw)


@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(404, "Email not found")

    token = create_access_token(
        {"sub": str(user.id), "pwd": user.password_changed_at.isoformat()},
        expires_minutes=15
    )

    reset_link = f"http://localhost:3000/reset-password?token={token}"

    message = MessageSchema(
        subject="Password Reset",
        recipients=[data.email],
        body=f"Reset here: {reset_link}",
        subtype="plain"
    )

    FastMail(settings.mail_config).send_message(message)
    return {"message": "Password reset link sent"}


@router.post("/reset-password")
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    payload = verify_token(data.token)
    if not payload:
        raise HTTPException(400, "Invalid or expired token")

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(404, "User not found")

    if payload.get("pwd") != user.password_changed_at.isoformat():
        raise HTTPException(401, "Token already used")

    validate_password_strength(data.new_password)

    user.hashed_password = hash_password(data.new_password)
    user.password_changed_at = datetime.utcnow()
    user.refresh_token = None
    db.commit()

    return {"message": "Password updated"}


@router.post("/google/one-tap")
def google_one_tap(
    data: GoogleOneTapRequest,
    db: Session = Depends(get_db)
):
    try:
        google_user = id_token.verify_oauth2_token(
            data.id_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
    except Exception:
        raise HTTPException(400, "Invalid Google token")

    email = google_user["email"]
    base_username = email.split("@")[0]
    username = base_username

    i = 1
    while db.query(User).filter(User.username == username).first():
        username = f"{base_username}{i}"
        i += 1

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            username=username,
            email=email,
            hashed_password=hash_password(secrets.token_hex(16))
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    access, refresh_raw, refresh_hashed = generate_tokens(user.id)
    user.refresh_token = refresh_hashed
    db.commit()

    return TokenPair(access_token=access, refresh_token=refresh_raw)


