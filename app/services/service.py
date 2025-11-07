# service.py
from app.models.auth import UserCreate, UserLogin, User
from app.core.core import get_db
from app.utils.smtp import send_verification_email, generate_verification_code
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
        code = generate_verification_code()
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
            send_verification_email(user.email, code)
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

        return {"message": "Email verified successfully!"}

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
            "sub": user.email,
            "user_id": str(db_user.id),
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

    async def get_me(self, current_user: User = Depends(get_me)):
        return {
            "id": str(current_user.id),
            "fullName": current_user.fullName,
            "email": current_user.email,
            "role": current_user.role,
            "email_verified": current_user.email_verified
        }


def auth_service(db: Session = Depends(get_db)):
    return AuthService(db)