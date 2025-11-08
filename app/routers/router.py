from fastapi import APIRouter, Depends
from app.models.auth import UserCreate, UserLogin, VerifyEmailRequest, UserResponse, User
from fastapi.security import OAuth2PasswordBearer
from app.services.service import auth_service
from app.core.core import get_db, SessionLocal as Session
from app.core.security import get_me
from uuid import UUID


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
router = APIRouter(prefix="/api")

auth_tags=["Authentication Methods"]
mero_tag=["Event Managment"]
tckt_tags=["Tickets Methods"]

@router.post("/auth/reg", tags=auth_tags, summary="Регистрация пользователя")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    service = auth_service(db)
    return await service.register(user)


@router.post("/auth/login", tags=auth_tags, summary="Вход пользователя")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    service = auth_service(db)
    return await service.login(user)


@router.get("/auth/me", response_model=UserResponse, tags=["Authentication"])
async def get_me(current_user: User = Depends(get_me)):
    return UserResponse(
        id=str(current_user.id),
        username=current_user.fullName,
        email=current_user.email,
        role=current_user.role,
    )

@router.post("/auth/verify", tags=auth_tags, summary="Подтверждение почты")
async def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    service = auth_service(db)
    return await service.verify_email(request.email, request.code)

