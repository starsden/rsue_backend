from app.models.models import UserCreate, UserLogin, User, TokenData
from app.core.core import get_db
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Depends
import jwt
import datetime
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
        db_user = self.db.query(User).filter(User.email == user.email).first()
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists ><(((*>"
            )

        hash_password = ph.hash(user.password[:72])
        db_user = User(
            fullName=user.fullName,
            email=user.email,
            phone=user.phone,
            password=hash_password,
            role=user.role,
            companyName=user.companyName,
            timezone="UTC",
            is_active=True,
            email_verified=False
        )

        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        return {
            "message": ".·´¯`·.·´¯`·.¸¸.·´¯`·.¸><(((º>",
            "user_id": str(db_user.id),
            "role": db_user.role
        }

    async def login(self, user: UserLogin):
        db_user = self.db.query(User).filter(User.email == user.email).first()
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found! Otter is sad :("
            )

        try:
            ph.verify(db_user.password, user.password[:72])
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Wrong password! Otter is angry!"
            )

        payload = {
            "sub": user.email,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
            "user_id": str(db_user.id),
            "role": db_user.role
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": str(db_user.id),
            "role": db_user.role
        }

    # Получить текущего пользователя по токену
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
