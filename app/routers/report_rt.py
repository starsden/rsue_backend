from io import BytesIO

from fastapi import APIRouter, Depends, Response, Query
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse, StreamingResponse

from app.core.core import get_db
from app.core.security import get_me
from app.models.auth import User
from app.services.reports import PDFService
from typing import Optional

pdf = APIRouter(prefix="/api/report", tags=["PDF Reports"])

@pdf.get("/stock")
async def get_stock_report(sklad_id: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    pdf_service = PDFService(db)
    result = pdf_service.genreport(current_user, sklad_id)

    return JSONResponse({
        "message": "Otter has compiled a report for you! <3",
        "url": result["download_url"],
        "qr": result["qr_code"].getvalue().hex(),
        "path": result["file_path"]
    })

@pdf.get("/download", response_class=StreamingResponse)
async def download_stock_report(sklad_id: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    pdf_service = PDFService(db)
    result = pdf_service.genreport(current_user, sklad_id)

    with open(result["file_path"], "rb") as f:
        pdf_content = f.read()

    return StreamingResponse(
        BytesIO(pdf_content),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={result['filename']}"}
    )