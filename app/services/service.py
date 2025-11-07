from app.models.models import UserCreate, UserLogin, User
from app.core.core import get_db
from app.utils.smtp import send_verification_email, generate_verification_code
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Depends
import jwt
from datetime import datetime, timedelta, timezone
from argon2 import PasswordHasher
from uuid import UUID
from fastapi.security import OAuth2PasswordBearer

ph = PasswordHasher()
SECRET_KEY = "eyJhbGciOiJIUzI1NiJ9.ew0KICAic3ViIjogIjEyMzQ1Njc4OTAiLA0KICAibmFtZSI6ICJBbmlzaCBOYXRoIiwNCiAgImlhdCI6IDE1MTYyMzkwMjINCn0.32CLvsmRfKbQ4ERFs4u66TSOIBKhmg28jM6LqDHgVYM"
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        role = payload.get("role")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role != role:
        raise HTTPException(status_code=401, detail="Invalid user")

    return user


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
            # "email": str(user.email)
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

    async def get_me(self, token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("user_id")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "id": str(user.id),
            "fullName": user.fullName,
            "email": user.email,
            "role": user.role,
            "email_verified": user.email_verified
        }
    async def get_me(self, token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("user_id")
            if user_id is None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        return {
            "id": str(user.id),
            "fullName": user.fullName,
            "email": user.email,
            "role": user.role
        }

def auth_service(db: Session):
    return AuthService(db)
