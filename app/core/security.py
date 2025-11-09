from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.core import get_db
from app.models.auth import User
import jwt
from uuid import UUID
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

SECRET_KEY = "eyJhbGciOiJIUzI1NiJ9.ew0KICAic3ViIjogIjEyMzQ1Njc4OTAiLA0KICAibmFtZSI6ICJBbmlzaCBOYXRoIiwNCiAgImlhdCI6IDE1MTYyMzkwMjINCn0.32CLvsmRfKbQ4ERFs4u66TSOIBKhmg28jM6LqDHgVYM"
ALGORITHM = "HS256"

ph = PasswordHasher()
async def get_me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        if not user_id or not role:
            raise HTTPException(status_code=401, detail="The otter ate the token(´ ε ` )♡")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Otter did not wait and went home with the token ┐(‘～` )┌")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="The otter ate the token(´ ε ` )♡")

    try:
        UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user ID format")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Otter didn't find you in the system!")
    if not user.email_verified:
        raise HTTPException(status_code=403, detail="Otter did not find such an email in the system!")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="You haven't played with an otter in a long time(")
    if user.role != role:
        raise HTTPException(status_code=403, detail="Role mismatch")

    return user

def get_hash(password: str) -> str:
    return ph.hash(password[:72])

def verify_password(plain_password: str, password: str) -> bool:
    try:
        ph.verify(password, plain_password[:72])
        return True
    except VerifyMismatchError:
        return False
    except Exception:
        return False