import os
from datetime import datetime
from uuid import UUID
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping
from io import BytesIO
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
import qrcode
from pathlib import Path

from app.models.nomen import Nomenclature, Stock
from app.models.auth import User
from app.models.sklads import Sklads

pdfmetrics.registerFont(TTFont('Arial', './static/Arial.ttf'))
addMapping('Arial', 0, 0, 'Arial')

STATIC_DIR = Path("./static/docs")
STATIC_DIR.mkdir(parents=True, exist_ok=True)


class PDFService:
    def __init__(self, db: Session):
        self.db = db

    def _get_org(self, current_user: User) -> UUID:
        if not current_user.connect_organization:
            raise HTTPException(status_code=403, detail="User not linked to an organization")
        return UUID(current_user.connect_organization)

    def genreport(self, current_user: User, sklad_id: str | None = None) -> dict:
        org_id = self._get_org(current_user)

        query = self.db.query(
            Nomenclature.name,
            Nomenclature.article,
            Nomenclature.unit,
            func.sum(Stock.quantity).label("quantity")
        ).join(Stock, Stock.nomenclature_id == Nomenclature.id)

        query = query.filter(
            Nomenclature.organization_id == org_id,
            Nomenclature.is_deleted == False
        )

        if sklad_id:
            query = query.filter(Stock.sklad_id == sklad_id)

        query = query.group_by(Nomenclature.name, Nomenclature.article, Nomenclature.unit)
        items = query.all()

        if not items:
            raise HTTPException(status_code=404, detail="No products found for report")

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=20*mm)
        styles = getSampleStyleSheet()
        styles["Normal"].fontName = "Arial"
        styles["Title"].fontName = "Arial"
        content = []

        title_text = "Остатки по складам" if sklad_id is None else "Остатки по выбранному складу"
        content.append(Paragraph(title_text, styles["Title"]))
        content.append(Spacer(1, 12))

        data = [["Название", "Артикул", "Ед.", "Количество"]]
        for item in items:
            data.append([item.name, item.article, item.unit, str(item.quantity)])

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Arial"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (2, 1), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Arial"),
            ("FONTSIZE", (0, 0), (-1, 0), 12),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ]))
        content.append(table)
        doc.build(content)

        pdf_bytes = buffer.getvalue()
        buffer.close()

        org_dir = STATIC_DIR / str(org_id)
        org_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"report_{'sklad_' + sklad_id + '_' if sklad_id else ''}{timestamp}.pdf"
        file_path = org_dir / filename

        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        download_url = f"/static/docs/{org_id}/{filename}"

        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(f"https://rsue.devoriole.ru{download_url}")
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)

        return {
            "file_path": str(file_path),
            "download_url": download_url,
            "qr_code": qr_buffer,
            "filename": filename
        }