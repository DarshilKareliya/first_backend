from datetime import timedelta
import uuid
from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import EmailStr
from app.schemas.user import UserCreate, OTPVerify, UserLogin, Resendotp, ForgotPasswordRequest, ResetPasswordRequest
from app.services.auth import generate_otp, get_current_user, hash_password, verify_password, create_token, resend_otp_logic
from app.services.email import send_otp_email
from app.utils.redis_conn import redis_conn
from app.models.User import User
from app.db.session import SessionLocal
from app.config import settings
from app.db.session import get_db
from sqlalchemy.orm import Session
from jose import jwt, JWTError


router = APIRouter()

@router.post("/signup")
def signup(user: UserCreate):
    db = SessionLocal()

    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(400, detail="Email already registered")

    otp = generate_otp()
    print("otp generated", otp)

    redis_conn.setex(f"otp:{user.email}", 600, otp)
    print(f"✅ OTP stored in Redis with key: otp:{user.email}")
    try:
        hashed = hash_password(user.password)
        print("✅ Hashed Password:", hashed)
        redis_conn.setex(f"temp_pass:{user.email}", 600, hashed)
    except Exception as e:
        print("❌ Hashing or Redis error:", str(e))
        raise HTTPException(500, detail="Internal server error during signup")
    # try:
    #     send_otp_email(user.email, otp)
    # except Exception as e:
    #     print("❌ Email send failed:", str(e))
    #     raise HTTPException(500, detail="OTP email failed. Try again.")

    return {"msg": "OTP sent to email"}


@router.post("/verify-otp")
def verify_otp(data: OTPVerify):
    saved_otp = redis_conn.get(f"otp:{data.email}")
    if saved_otp != data.otp:
        raise HTTPException(400, detail="Invalid OTP")

    db = SessionLocal()
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, detail="User already verified")

    new_user = User(
        email=data.email,
        username=data.email.split("@")[0],
        hashed_password=redis_conn.get(f"temp_pass:{data.email}"),
        is_verified=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    redis_conn.delete(f"otp:{data.email}")
    redis_conn.delete(f"temp_pass:{data.email}")

    return {"msg": "Signup complete"}

@router.post("/login")
def login(data: UserLogin):
    db = SessionLocal()
    user = db.query(User).filter(
        (User.email == data.username_or_email) |
        (User.username == data.username_or_email)
    ).first()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, detail="Invalid credentials")

    if not user.is_verified:
        raise HTTPException(403, detail="Email not verified")

    access_token = create_token({"sub": user.email}, token_type="access")
    user_id = str(user.id)
    jti = str(uuid.uuid4())
    refresh_token = create_token({"sub": user_id}, timedelta(days=7), token_type="refresh", jti=jti)

    # Store in Redis with jti
    redis_conn.setex(f"refresh_token:{user_id}:{jti}", 7 * 24 * 3600, refresh_token)

    return {    
    "access_token": access_token,
    "refresh_token": refresh_token,
    "token_type": "bearer"
    }

@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest):
    db = SessionLocal()
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(400, detail="Email not registered")

    otp = generate_otp()
    redis_conn.setex(f"otp:{data.email}", 600, otp)

    try:
        send_otp_email(data.email, otp)
    except Exception as e:
        raise HTTPException(500, detail="OTP email failed. Try again.")

    return {"msg": "OTP sent to email"}

@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest):
    saved_otp = redis_conn.get(f"otp:{data.email}")
    if saved_otp != data.otp:
        raise HTTPException(400, detail="Invalid OTP")

    db = SessionLocal()
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(400, detail="User not found")

    user.hashed_password = hash_password(data.new_password)
    db.commit()

    redis_conn.delete(f"otp:{data.email}")
    return {"msg": "Password reset successful"}

@router.post("/resend-otp/signup")
def resend_otp_signup(data: Resendotp):
    if not redis_conn.get(f"temp_pass:{data.email}"):
        raise HTTPException(404, detail="No signup in progress for this email")

    return {"msg": resend_otp_logic(data.email, "signup")}

@router.post("/resend-otp/forgot")
def resend_otp_forgot(data: Resendotp):
    db = SessionLocal()
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(404, detail="User not found")

    return {"msg": resend_otp_logic(data.email, "forgot")}

@router.post("/refresh")
def refresh_token(request: Request, db: Session = Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    refresh_token = auth_header.split(" ")[1]

    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")

        user_id = payload.get("sub")
        jti = payload.get("jti")
        key = f"refresh_token:{user_id}:{jti}"

        stored_token = redis_conn.get(key)
        if not stored_token or stored_token.decode() != refresh_token:
            raise HTTPException(status_code=401, detail="Refresh token invalid or expired")

        # Invalidate old token
        redis_conn.delete(key)

        # Generate new refresh token (ROTATION!)
        new_jti = str(uuid.uuid4())
        new_refresh_token = create_token({"sub": user_id}, timedelta(days=7), token_type="refresh", jti=new_jti)
        redis_conn.setex(f"refresh_token:{user_id}:{new_jti}", 7 * 24 * 3600, new_refresh_token)

        # New access token
        new_access_token = create_token({"sub": user_id}, token_type="access")

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    
@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    # Wildcard delete: delete all refresh tokens for the user
    keys = redis_conn.keys(f"refresh_token:{current_user.id}:*")
    for key in keys:
        redis_conn.delete(key)
    return {"message": "Logged out successfully"}
