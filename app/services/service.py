from app.models.auth import UserCreate, UserLogin, User
from app.core.core import get_db
from app.utils.smtp import send_ver, gen_code, welcome
from app.core.security import get_me
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Depends
import jwt
from datetime import datetime, timedelta, timezone
from argon2 import PasswordHasher

ph = PasswordHasher()
SECRET_KEY = "eyJhbGciOiJIUzI1NiJ9.ew0KICAic3ViIjogIjEyMzQ1Njc4OTAiLA0KICAibmFtZSI6ICJBbmlzaCBOYXRoIiwNCiAgImlhdCI6IDE1MTYyMzkwMjINCn0.32CLvsmRfKbQ4ERFs4u66TSOIBKhmg28jM6LqDHgVYM"
ALGORITHM = "HS256"


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    async def register(self, user: UserCreate):
        if self.db.query(User).filter(User.email == user.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists ><(((*>"
            )

        hashed_password = ph.hash(user.password[:72])
        code = gen_code()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        db_user = User(
            fullName=user.fullName,
            email=user.email,
            phone=user.phone,
            password=hashed_password,
            role=user.role or "User",
            companyName=user.companyName,
            timezone="UTC",
            is_active=False,
            email_verified=False,
            ver_code=code,
            code_expires_at=expires_at
        )

        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        try:
            send_ver(user.email, code)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email"
            )

        return {
            "message": "Check your email for verification code",
            "user_id": str(db_user.id)
        }

    async def verify_email(self, email: str, code: str):
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.email_verified:
            raise HTTPException(status_code=400, detail="Email already verified")

        if user.ver_code != code:
            raise HTTPException(status_code=400, detail="Invalid verification code")

        if datetime.utcnow() > user.code_expires_at:
            raise HTTPException(status_code=400, detail="Verification code expired")

        user.email_verified = True
        user.is_active = True
        user.ver_code = None
        user.code_expires_at = None

        self.db.commit()

        try:
            welcome(user.email)
        except Exception:
            pass

        return {"message": "cool!"}

    async def resend_ver(self, email: str):
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="Otter did not find such a user")

        if user.email_verified:
            raise HTTPException(status_code=400, detail="Otter has already seen such mail somewhere! Try another email")

        if user.code_expires_at and datetime.utcnow() < user.code_expires_at:
            raise HTTPException(
                status_code=429,
                detail="stop! i don't like this. please wait "
            )

        new_code = gen_code()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        user.ver_code = new_code
        user.code_expires_at = expires_at
        self.db.commit()

        try:
            send_ver(email, new_code)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail="failed to send verification email :( sorry.."
            )

        return {
            "message": "you lost your previous code! the otter is angry!",
            "expires_in": 600
        }

    async def login(self, user: UserLogin):
        db_user = self.db.query(User).filter(User.email == user.email).first()
        if not db_user:
            raise HTTPException(status_code=401, detail="User not found! Otter is sad :(")

        if not db_user.email_verified:
            raise HTTPException(status_code=403, detail="Please verify your email first")

        try:
            ph.verify(db_user.password, user.password[:72])
        except:
            raise HTTPException(status_code=401, detail="Wrong password! Otter is angry!")

        payload = {
            "sub": str(db_user.id),
            "role": db_user.role,
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": str(db_user.id),
            "role": db_user.role
        }


def auth_service(db: Session = Depends(get_db)):
    return AuthService(db)