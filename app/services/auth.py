import random
from fastapi import HTTPException, Depends, status
from app.services.email import send_otp_email
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone
from app.config import settings
from typing import Literal
from app.utils.redis_conn import redis_conn
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.models.User import User
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_otp():
    return str(random.randint(100000, 999999))

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def create_token(data: dict, expires_delta: timedelta = None, token_type: str = "access", jti: str = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({
        "exp": expire,
        "type": token_type,     # ← This is new
        "jti": jti or str(uuid.uuid4())  # ← For refresh token tracking
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def resend_otp_logic(email: str, context: Literal["signup", "forgot"]) -> str:
    otp = generate_otp()
    redis_key = f"otp:{email}"

    # For signup, also refresh temp_pass TTL
    if context == "signup":
        hashed_pass = redis_conn.get(f"temp_pass:{email}")
        if not hashed_pass:
            raise HTTPException(400, detail="Signup session expired. Please sign up again.")
        redis_conn.setex(f"temp_pass:{email}", 600, hashed_pass)
        print(f"♻️ Refreshed TTL for temp_pass:{email}")

    redis_conn.setex(redis_key, 600, otp)
    print(f"🔁 Resent OTP {otp} stored at {redis_key}")

    try:
        send_otp_email(email, otp)
        return "OTP resent successfully"
    except Exception as e:
        print("❌ Email send failed:", str(e))
        raise HTTPException(500, detail="Failed to send OTP")
    
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user