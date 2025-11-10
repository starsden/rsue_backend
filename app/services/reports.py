import os
import tempfile
import hashlib
import secrets
import string
from datetime import datetime, timedelta, timezone
from uuid import UUID
from pathlib import Path
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, KeepTogether, PageBreak
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
import qrcode
import barcode
from barcode.writer import ImageWriter
from PIL import Image as PILImage

from app.models.nomen import Nomenclature, Stock
from app.models.auth import User
from app.models.sklads import Sklads
from app.models.orga import Orga
from app.models.docs import InventoryToken
from typing import Optional

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

    def _generate_token(self, length: int = 32) -> str:
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    def _generate_hash(self, data: dict) -> str:
        data_string = f"{data.get('org_id')}{data.get('sklad_id', '')}{data.get('timestamp')}{data.get('items_count')}"
        return hashlib.sha256(data_string.encode()).hexdigest()[:32]
    
    def verify_signature(self, report_id: UUID, org_id: str, sklad_id: str, timestamp: str, items_count: int) -> dict:
        inventory_token = self.db.query(InventoryToken).filter(
            InventoryToken.id == report_id,
            InventoryToken.is_active == True
        ).first()
        
        if not inventory_token:
            return {
                "valid": False,
                "error": "Report not found or inactive"
            }

        hash_data = {
            'org_id': org_id,
            'sklad_id': sklad_id if sklad_id else '',
            'timestamp': timestamp,
            'items_count': items_count
        }
        calculated_hash = self._generate_hash(hash_data)

        is_valid = calculated_hash == inventory_token.signature_hash
        
        return {
            "valid": is_valid,
            "stored_hash": inventory_token.signature_hash,
            "calculated_hash": calculated_hash,
            "match": is_valid,
            "report_id": str(inventory_token.id),
            "organization_id": str(inventory_token.organization_id)
        }
    
    def verify_by_hash(self, signature_hash: str) -> dict:
        inventory_token = self.db.query(InventoryToken).filter(
            InventoryToken.signature_hash == signature_hash,
            InventoryToken.is_active == True
        ).first()
        
        if not inventory_token:
            return {
                "valid": False,
                "error": "Document with this signature not found or inactive"
            }

        report_data = inventory_token.report_data
        org_id = report_data.get('organization', {}).get('id', '')
        sklad_id = report_data.get('sklad', {}).get('id', '') if report_data.get('sklad') else ''
        timestamp = report_data.get('created_at', '')
        items_count = report_data.get('items_count', 0)

        hash_data = {
            'org_id': org_id,
            'sklad_id': sklad_id if sklad_id else '',
            'timestamp': timestamp,
            'items_count': items_count
        }
        calculated_hash = self._generate_hash(hash_data)

        is_valid = calculated_hash == inventory_token.signature_hash
        
        return {
            "valid": is_valid,
            "stored_hash": inventory_token.signature_hash,
            "calculated_hash": calculated_hash,
            "match": is_valid,
            "report_id": str(inventory_token.id),
            "organization_id": str(inventory_token.organization_id),
            "organization_name": report_data.get('organization', {}).get('legalName', ''),
            "created_at": report_data.get('created_at', ''),
            "items_count": items_count,
            "sklad_name": report_data.get('sklad', {}).get('name') if report_data.get('sklad') else None
        }

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

    def gen_report(self, current_user: User, sklad: bool, sklad_id: Optional[UUID] = None) -> dict:
        org_id = self._get_org(current_user)

        organization = self.db.query(Orga).filter(Orga.id == org_id, Orga.is_deleted == False).first()
        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")

        if sklad:
            if not sklad_id:
                raise HTTPException(status_code=400, detail="sklad_id is required when sklad=True")
            
            sklad_obj = self.db.query(Sklads).filter(
                Sklads.id == sklad_id,
                Sklads.organization_id == org_id,
                Sklads.is_deleted == False
            ).first()
            
            if not sklad_obj:
                raise HTTPException(status_code=404, detail="Warehouse not found")

        if sklad:
            query = self.db.query(
                Nomenclature.name,
                Nomenclature.article,
                Nomenclature.barcode,
                Nomenclature.unit,
                Stock.quantity,
                Sklads.name.label("sklad_name")
            ).join(Stock, Stock.nomenclature_id == Nomenclature.id)\
             .join(Sklads, Sklads.id == Stock.sklad_id)\
             .filter(
                Nomenclature.organization_id == org_id,
                Nomenclature.is_deleted == False,
                Stock.sklad_id == sklad_id
            )
        else:
            query = self.db.query(
                Nomenclature.name,
                Nomenclature.article,
                Nomenclature.barcode,
                Nomenclature.unit,
                Stock.quantity,
                Sklads.name.label("sklad_name")
            ).join(Stock, Stock.nomenclature_id == Nomenclature.id)\
             .join(Sklads, Sklads.id == Stock.sklad_id)\
             .filter(
                Nomenclature.organization_id == org_id,
                Nomenclature.is_deleted == False,
                Sklads.is_deleted == False
            )

        items = query.order_by(Sklads.name, Nomenclature.name).all()

        if not items:
            raise HTTPException(status_code=404, detail="No inventory data found for report")
        timestamp = datetime.now(timezone.utc)
        timestamp_str = timestamp.strftime("%Y-%m-%d_%H-%M-%S")
        token = self._generate_token()

        hash_data = {
            'org_id': str(org_id),
            'sklad_id': str(sklad_id) if sklad_id else '',
            'timestamp': timestamp_str,
            'items_count': len(items)
        }
        signature_hash = self._generate_hash(hash_data)
        report_data = {
            'organization': {
                'id': str(organization.id),
                'legalName': organization.legalName,
                'inn': organization.inn,
                'address': organization.address,
                'description': organization.description
            },
            'sklad': {
                'id': str(sklad_obj.id),
                'name': sklad_obj.name,
                'code': sklad_obj.code
            } if sklad else None,
            'items': [
                {
                    'name': item.name,
                    'article': item.article,
                    'barcode': item.barcode,
                    'unit': item.unit,
                    'quantity': item.quantity,
                    'sklad_name': item.sklad_name if not sklad else None
                } for item in items
            ],
            'created_at': timestamp.isoformat(),
            'items_count': len(items)
        }

        inventory_token = InventoryToken(
            organization_id=org_id,
            sklad_id=sklad_id if sklad else None,
            token=token,
            signature_hash=signature_hash,
            report_data=report_data,
            expires_at=None,
            is_active=True
        )
        self.db.add(inventory_token)
        self.db.commit()
        self.db.refresh(inventory_token)

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, 
                                topMargin=20*mm, bottomMargin=40*mm)
        styles = getSampleStyleSheet()
        styles["Normal"].fontName = "Arial"
        styles["Title"].fontName = "Arial"
        styles["Heading2"].fontName = "Arial"

        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_LEFT
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=20,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=12,
            alignment=TA_LEFT,
            fontName='Arial'
        )
        
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=8,
            spaceBefore=4,
            fontName='Arial'
        )
        
        info_style = ParagraphStyle(
            'CustomInfo',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=6,
            leftIndent=8,
            fontName='Arial'
        )
        
        content = []

        if sklad:
            title_text = f"ИНВЕНТАРИЗАЦИЯ СКЛАДА<br/>{sklad_obj.name}"
        else:
            title_text = f"ИНВЕНТАРИЗАЦИЯ ОРГАНИЗАЦИИ<br/>{organization.legalName}"
        
        content.append(Paragraph(title_text, title_style))
        content.append(Spacer(1, 8))
        content.append(Paragraph("<b>Информация об организации</b>", header_style))
        
        org_info_html = f"""
        <para leftIndent="10" spaceAfter="4">
        <b>Организация:</b> {organization.legalName}
        </para>
        """
        content.append(Paragraph(org_info_html, info_style))
        
        if organization.inn:
            org_info_html = f"""
            <para leftIndent="10" spaceAfter="4">
            <b>ИНН:</b> {organization.inn}
            </para>
            """
            content.append(Paragraph(org_info_html, info_style))
        
        if organization.description:
            org_info_html = f"""
            <para leftIndent="10" spaceAfter="4">
            <b>Описание:</b> {organization.description}
            </para>
            """
            content.append(Paragraph(org_info_html, info_style))
        
        if organization.address:
            addr = organization.address
            address_str = f"{addr.get('country', '')}, {addr.get('city', '')}, {addr.get('street', '')}, {addr.get('postalCode', '')}"
            org_info_html = f"""
            <para leftIndent="10" spaceAfter="4">
            <b>Адрес:</b> {address_str}
            </para>
            """
            content.append(Paragraph(org_info_html, info_style))
        
        content.append(Spacer(1, 10))

        date_text = f"<b>Дата создания:</b> {timestamp.strftime('%d.%m.%Y %H:%M')}"
        content.append(Paragraph(date_text, header_style))
        content.append(Spacer(1, 16))

        if sklad:
            data = [["Название", "Артикул", "Штрих-код", "Ед.", "Количество"]]
            for item in items:
                barcode_value = item.barcode if item.barcode else "-"
                data.append([
                    item.name,
                    item.article,
                    barcode_value,
                    item.unit,
                    str(item.quantity)
                ])
        else:
            data = [["Склад", "Название", "Артикул", "Штрих-код", "Ед.", "Количество"]]
            for item in items:
                barcode_value = item.barcode if item.barcode else "-"
                data.append([
                    item.sklad_name,
                    item.name,
                    item.article,
                    barcode_value,
                    item.unit,
                    str(item.quantity)
                ])

        table = Table(data, repeatRows=1)
        

        header_bg_color = colors.HexColor('#3498db')
        header_text_color = colors.white
        even_row_bg = colors.HexColor('#f8f9fa')
        odd_row_bg = colors.white
        border_color = colors.HexColor('#dee2e6')
        
        table_style = [
            ("FONTNAME", (0, 0), (-1, -1), "Arial"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 1, border_color),

            ("BACKGROUND", (0, 0), (-1, 0), header_bg_color),
            ("TEXTCOLOR", (0, 0), (-1, 0), header_text_color),
            ("FONTNAME", (0, 0), (-1, 0), "Arial"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("TOPPADDING", (0, 0), (-1, 0), 12),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),

            ("TOPPADDING", (0, 1), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
            ("LEFTPADDING", (0, 1), (-1, -1), 6),
            ("RIGHTPADDING", (0, 1), (-1, -1), 6),
            ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),

            ("ALIGN", (-2, 1), (-1, -1), "CENTER"),
        ]
        
        if sklad:
            table_style.append(("ALIGN", (2, 1), (2, -1), "CENTER"))
        else:
            table_style.append(("ALIGN", (3, 1), (3, -1), "CENTER"))

        for i in range(1, len(data)):
            if i % 2 == 0:
                table_style.append(("BACKGROUND", (0, i), (-1, i), even_row_bg))
            else:
                table_style.append(("BACKGROUND", (0, i), (-1, i), odd_row_bg))
        
        table.setStyle(TableStyle(table_style))
        content.append(table)
        content.append(Spacer(1, 12))
        

        code128 = barcode.get_barcode_class('code128')
        barcode_instance = code128(signature_hash, writer=ImageWriter())

        barcode_tmp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        barcode_tmp_file.close()
        barcode_instance.write(barcode_tmp_file.name)
        barcode_img_path = barcode_tmp_file.name

        online_url = f"https://rsue.devoriole.ru/api/report/inventory/view/{token}"
        qr = qrcode.QRCode(version=1, box_size=8, border=4)
        qr.add_data(online_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_tmp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        qr_tmp_file.close()
        qr_img.save(qr_tmp_file.name)
        qr_img_path = qr_tmp_file.name

        class InventoryDocTemplate(SimpleDocTemplate):
            def __init__(self, *args, **kwargs):
                self.barcode_img = kwargs.pop('barcode_img', None)
                self.qr_img = kwargs.pop('qr_img', None)
                super().__init__(*args, **kwargs)
            
            def afterPage(self):
                if self.barcode_img and self.qr_img:
                    self.canv.saveState()

                    barcode_width = 60*mm
                    barcode_height = 15*mm
                    barcode_x = 15*mm
                    barcode_y = 18*mm

                    self.canv.setFillColor(colors.white)
                    self.canv.rect(barcode_x - 2*mm, barcode_y - 2*mm, 
                                  barcode_width + 4*mm, barcode_height + 8*mm, 
                                  fill=1, stroke=0)
                    
                    self.canv.drawImage(self.barcode_img, barcode_x, barcode_y, 
                                      width=barcode_width, height=barcode_height, 
                                      preserveAspectRatio=True)

                    self.canv.setFont("Arial", 8)
                    self.canv.setFillColor(colors.HexColor('#2c3e50'))
                    text_width = self.canv.stringWidth("Электронная подпись", "Arial", 8)
                    self.canv.drawString(barcode_x + (barcode_width - text_width) / 2, 
                                        barcode_y - 4*mm, "Электронная подпись")
                    

                    qr_size = 25*mm
                    qr_x = A4[0] - 15*mm - qr_size
                    qr_y = 18*mm

                    self.canv.setFillColor(colors.white)
                    self.canv.rect(qr_x - 2*mm, qr_y - 2*mm, 
                                  qr_size + 4*mm, qr_size + 8*mm, 
                                  fill=1, stroke=0)
                    
                    self.canv.drawImage(self.qr_img, qr_x, qr_y,
                                      width=qr_size, height=qr_size, 
                                      preserveAspectRatio=True)

                    self.canv.setFont("Arial", 8)
                    self.canv.setFillColor(colors.HexColor('#2c3e50'))
                    text_width = self.canv.stringWidth("Онлайн просмотр", "Arial", 8)
                    self.canv.drawString(qr_x + (qr_size - text_width) / 2, 
                                        qr_y - 4*mm, "Онлайн просмотр")
                    
                    self.canv.restoreState()

        doc = InventoryDocTemplate(buffer, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm,
                                   topMargin=20*mm, bottomMargin=40*mm,
                                   barcode_img=barcode_img_path, qr_img=qr_img_path)
        
        try:
            doc.build(content)
            pdf_bytes = buffer.getvalue()
        finally:
            buffer.close()
            if os.path.exists(barcode_img_path):
                os.unlink(barcode_img_path)
            if os.path.exists(qr_img_path):
                os.unlink(qr_img_path)

        org_dir = STATIC_DIR / str(org_id)
        org_dir.mkdir(parents=True, exist_ok=True)

        timestamp_file = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if sklad:
            filename = f"inventory_sklad_{sklad_id}_{timestamp_file}.pdf"
        else:
            filename = f"inventory_org_{org_id}_{timestamp_file}.pdf"
        file_path = org_dir / filename

        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        download_url = f"/static/docs/{org_id}/{filename}"

        qr_download = qrcode.QRCode(version=1, box_size=10, border=4)
        qr_download.add_data(f"https://rsue.devoriole.ru{download_url}")
        qr_download.make(fit=True)
        qr_download_img = qr_download.make_image(fill_color="black", back_color="white")
        qr_download_buffer = BytesIO()
        qr_download_img.save(qr_download_buffer, format='PNG')
        qr_download_buffer.seek(0)

        return {
            "file_path": str(file_path),
            "download_url": download_url,
            "qr_code": qr_download_buffer,
            "filename": filename,
            "token": token,
            "signature_hash": signature_hash,
            "online_url": online_url
        }