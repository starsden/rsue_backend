from datetime import datetime, timedelta, timezone
from typing import Iterable, Literal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.orga import Orga, Invitation, InvitationResponse, OrganizationInvitationCreate
from app.models.user_profile import InvitationActionResponse, UserDashboardResponse, UserLookupItem, UserSearchResponse
from app.utils.qr import generate_token
from app.utils.smtp import send_invitation


ALLOWED_MANAGER_ROLES = {"Founder", "Admin", "Manager"}


def manager(current_user: User, org_id: UUID) -> None:
    if current_user.connect_organization != str(org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization",
        )
    if current_user.role not in ALLOWED_MANAGER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient role to manage invitations",
        )


def _single_param_validator(*, email: str | None, phone: str | None, full_name: str | None) -> tuple[str, str]:
    provided = {
        "email": email.strip() if email else None,
        "phone": phone.strip() if phone else None,
        "full_name": full_name.strip() if full_name else None,
    }
    cleaned = {key: value for key, value in provided.items() if value}
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide exactly one search parameter",
        )
    if len(cleaned) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide only one search parameter at a time",
        )
    return next(iter(cleaned.items()))


def _into_lookup_item(users: Iterable[User]) -> list[UserLookupItem]:
    return [
        UserLookupItem(
            id=user.id,
            full_name=user.fullName,
            email=user.email,
            phone=user.phone,
            role=user.role,
            connect_organization=user.connect_organization,
        )
        for user in users
    ]


def search_by_parameter(db: Session, *, current_user: User, org_id: UUID, email: str | None, phone: str | None, full_name: str | None) -> UserSearchResponse:
    manager(current_user, org_id)
    lookup_key, lookup_value = _single_param_validator(email=email, phone=phone, full_name=full_name)

    query = db.query(User)
    match lookup_key:
        case "email":
            query = query.filter(User.email.ilike(lookup_value))
        case "phone":
            query = query.filter(User.phone.ilike(f"%{lookup_value}%"))
        case "full_name":
            query = query.filter(User.fullName.ilike(f"%{lookup_value}%"))
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported search parameter",
            )

    users = query.order_by(User.created_at.desc()).limit(10).all()
    return UserSearchResponse(results=_into_lookup_item(users))


def _resolve_single_user(db: Session, *, identifier_type: str, identifier_value: str) -> User:
    match identifier_type:
        case "email":
            user = (
                db.query(User)
                .filter(User.email.ilike(identifier_value.strip()))
                .first()
            )
        case "phone":
            user = (
                db.query(User)
                .filter(User.phone.ilike(f"%{identifier_value.strip()}%"))
                .first()
            )
        case "full_name":
            user = (
                db.query(User)
                .filter(User.fullName.ilike(f"%{identifier_value.strip()}%"))
                .first()
            )
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported identifier type",
            )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found for provided identifier",
        )

    return user


def create_invite(db: Session, *, org_id: UUID, payload: OrganizationInvitationCreate, current_user: User) -> InvitationResponse:
    manager(current_user, org_id)

    organization = (
        db.query(Orga)
        .filter(Orga.id == org_id, Orga.is_deleted == False)
        .first()
    )
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    recipient = _resolve_single_user(
        db,
        identifier_type=payload.identifier_type,
        identifier_value=payload.identifier_value,
    )

    if recipient.connect_organization == str(org_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already belongs to this organization",
        )

    existing_invite = (
        db.query(Invitation)
        .filter(
            Invitation.organization_id == org_id,
            Invitation.email == recipient.email,
            Invitation.status == "pending",
        )
        .first()
    )
    if existing_invite:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Active invitation already exists for this user",
        )

    token = generate_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=payload.expires_in_hours)

    invitation = Invitation(
        organization_id=org_id,
        user_id=recipient.id,
        token=token,
        email=recipient.email,
        fullName=recipient.fullName,
        phone=recipient.phone,
        role=payload.role,
        status="pending",
        is_used=False,
        expires_at=expires_at,
    )

    db.add(invitation)
    db.flush()
    invite_url = f"https://rsue.devoriole.ru/auth?invite={token}"
    try:
        send_invitation(recipient.email, recipient.fullName, organization.legalName, invite_url)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to send invitation email: {exc}",
        )

    db.commit()
    db.refresh(invitation)

    return InvitationResponse.model_validate(invitation)


def cancel_invite(db: Session, *,  org_id: UUID, invitation_id: UUID, current_user: User) -> InvitationActionResponse:
    manager(current_user, org_id)

    invitation = (
        db.query(Invitation)
        .filter(
            Invitation.id == invitation_id,
            Invitation.organization_id == org_id,
        )
        .first()
    )
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found"
        )

    if invitation.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending invitations can be cancelled",
        )

    invitation.status = "cancelled"
    invitation.responded_at = datetime.now(timezone.utc)
    invitation.is_used = False
    db.commit()

    return InvitationActionResponse(
        invitation_id=invitation.id,
        status=invitation.status,
        message="Invitation cancelled",
        responded_at=invitation.responded_at,
    )


def list_user(db: Session, *, current_user: User) -> list[InvitationResponse]:
    invitations = (
        db.query(Invitation)
        .filter(
            or_(
                Invitation.user_id == current_user.id,
                Invitation.email == current_user.email,
            )
        )
        .order_by(Invitation.created_at.desc())
        .all()
    )

    return [
        InvitationResponse.model_validate(invitation) for invitation in invitations
    ]


def get_user(db: Session, *, current_user: User) -> UserDashboardResponse:
    invitations = list_user(db, current_user=current_user)

    return UserDashboardResponse(
        id=current_user.id,
        fullName=current_user.fullName,
        email=current_user.email,
        phone=current_user.phone,
        role=current_user.role,
        connect_organization=current_user.connect_organization,
        invitations=invitations,
    )


def respond_to_invite(db: Session, *, invitation_id: UUID, current_user: User, action: Literal["accept", "decline"]) -> InvitationActionResponse:
    invitation = (
        db.query(Invitation)
        .filter(Invitation.id == invitation_id)
        .first()
    )
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found"
        )

    if invitation.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invitation is not pending",
        )

    if invitation.expires_at <= datetime.now(timezone.utc):
        invitation.status = "cancelled"
        invitation.responded_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invitation expired",
        )

    if invitation.user_id and invitation.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invitation assigned to another user",
        )

    email_matches = invitation.email == current_user.email
    if invitation.user_id == current_user.id:
        email_matches = True

    if not email_matches:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invitation email mismatch",
        )

    now = datetime.now(timezone.utc)
    invitation.responded_at = now

    if action == "accept":
        existing_org = current_user.connect_organization
        target_org = str(invitation.organization_id)
        if existing_org and existing_org != target_org:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already connected to an organization",
            )

        current_user.connect_organization = target_org
        invitation.user_id = invitation.user_id or current_user.id
        invitation.status = "accepted"
        invitation.is_used = True
        invitation.used_at = now
        message = "Invitation accepted"
    else:
        invitation.status = "declined"
        invitation.is_used = False
        message = "Invitation declined"

    db.commit()

    return InvitationActionResponse(
        invitation_id=invitation.id,
        status=invitation.status,
        message=message,
        responded_at=invitation.responded_at,
    )

