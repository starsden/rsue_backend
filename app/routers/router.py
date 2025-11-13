from fastapi import APIRouter, Depends, Query
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from uuid import UUID

from app.core.core import get_db, SessionLocal as Session
from app.core.security import get_me
from app.models.auth import (
    User,
    UserCreate,
    UserLogin,
    UserResponse,
    VerifyEmailRequest,
    ResendVerificationRequest,
)
from app.models.user_profile import CurrentUserResponse
from app.services.invitation_service import list_user
from app.services.service import auth_service, send_ver


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
router = APIRouter(prefix="/api")

auth_tags=["Authentication Methods"]
h = ["Are you okey?"]

@router.post("/health", tags=h)
async def health():
    return {"status": "otter said: i'm okey! thank u <3"}

@router.post("/auth/reg", tags=auth_tags, summary="Регистрация пользователя")
async def register(user: UserCreate, invite: Optional[str] = Query(None), db: Session = Depends(get_db)):
    service = auth_service(db)
    return await service.register(user, invite)

@router.post("/auth/login", tags=auth_tags, summary="Вход пользователя")
async def login(user: UserLogin, invite: Optional[str] = Query(None), db: Session = Depends(get_db)):
    service = auth_service(db)
    return await service.login(user, invite)


@router.get("/auth/me", response_model=CurrentUserResponse, tags=auth_tags)
async def get_me(current_user: User = Depends(get_me), db: Session = Depends(get_db)):
    invitations = list_user(db, current_user=current_user)
    return CurrentUserResponse(
        id=str(current_user.id),
        username=current_user.fullName,
        email=current_user.email,
        role=current_user.role,
        choosen_sklad=current_user.choosen_sklad,
        invitations=invitations,
    )

@router.post("/auth/verify", tags=auth_tags, summary="Подтверждение почты")
async def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    service = auth_service(db)
    return await service.verify_email(request.email, request.code)


@router.post("/auth/resend", tags=auth_tags, summary="Повторная отправка кода подтверждения")
async def resend_verification_code(request: ResendVerificationRequest, db: Session = Depends(get_db)):
    service = auth_service(db)
    return await service.resend_ver(request.email)