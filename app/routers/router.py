from fastapi import APIRouter, Depends
from app.models.models import UserCreate, UserLogin
from fastapi.security import OAuth2PasswordBearer
from app.services.service import auth_service
from app.core.core import get_db, SessionLocal as Session
from uuid import UUID
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
router = APIRouter(prefix="/api")

auth_tags=["Authentication Methods"]
mero_tag=["Event Managment"]
tckt_tags=["Tickets Methods"]

@router.post("/auth/reg", tags=auth_tags)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    service = auth_service(db)
    return await service.register(user)


@router.post("/auth/login", tags=auth_tags)
async def login(user: UserLogin, db: Session = Depends(get_db)):
    service = auth_service(db)
    return await service.login(user)


@router.get("/auth/me", tags=auth_tags)
async def get_me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    service = auth_service(db)
    return await service.get_me(token)

