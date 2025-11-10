from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping

from app.models.nomen import Nomenclature, Stock
from app.models.auth import User
from app.models.sklads import Sklads

pdfmetrics.registerFont(TTFont('Kreadon', './static/Arial.ttf'))
addMapping('Kreadon', 0, 0, 'Kreadon')


class PDFService:
    def __init__(self, db: Session):
        self.db = db

    def _get_org(self, current_user: User):
        if not current_user.connect_organization:
            raise HTTPException(status_code=403, detail="User not linked to an organization")
        return current_user.connect_organization

    def genreport(self, current_user: User, sklad_id: str | None = None) -> bytes:
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
        styles["Normal"].fontName = "Kreadon"
        styles["Title"].fontName = "Kreadon"
        content = []

        title_text = "Остатки по складам" if sklad_id is None else "Остатки по выбранному складу"
        content.append(Paragraph(title_text, styles["Title"]))
        content.append(Spacer(1, 12))

        data = [["Название", "Артикул", "Ед.", "Количество"]]
        for item in items:
            data.append([
                item.name,
                item.article,
                item.unit,
                str(item.quantity)
            ])

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "Kreadon"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (2, 1), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 12),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ]))
        content.append(table)

        doc.build(content)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
