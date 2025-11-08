from app.models.orga import QrCode
from app.utils.qr import generate_token, make_qr_base64
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from uuid import UUID

class QrService:
    def create_qr(self, db: Session, organization_id: UUID, expires_in: int = 86400):
        db.query(QrCode).filter( QrCode.organization_id == organization_id, QrCode.is_active == True).update({"is_active": False})

        token = generate_token()
        join_url = f"https://rsue.devoriole.ru/api/orga/join/{token}"
        qr_base64 = make_qr_base64(join_url)

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        qr = QrCode(
            organization_id=organization_id,
            token=token,
            expires_at=expires_at
        )
        db.add(qr)
        db.commit()
        db.refresh(qr)

        return {
            "qr_image": f"data:image/svg+xml;base64,{qr_base64}",
            "join_url": join_url,
            "expires_at": expires_at,
            "token": token
        }