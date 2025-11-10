from io import BytesIO
from fastapi import APIRouter, Depends, Response, Query, Body
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, model_validator

from fastapi import HTTPException

from app.core.core import get_db
from app.core.security import get_me
from app.models.auth import User
from app.models.docs import InventoryToken
from app.services.reports import PDFService
from typing import Optional
from uuid import UUID
from app.models.docs import InventoryReportRequest, VerifyByHash


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
@pdf.post("/inventory")
async def get_inventory_report(
    request: InventoryReportRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_me)
):
    pdf_service = PDFService(db)
    result = pdf_service.gen_report(current_user, sklad=request.sklad, sklad_id=request.sklad_id)

    return JSONResponse({
        "message": "Inventory report generated successfully!",
        "url": result["download_url"],
        "qr": result["qr_code"].getvalue().hex(),
        "path": result["file_path"],
        "filename": result["filename"]
    })

@pdf.post("/inventory/download", response_class=StreamingResponse)
async def download_inventory_report(
    request: InventoryReportRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_me)
):
    pdf_service = PDFService(db)
    result = pdf_service.gen_report(current_user, sklad=request.sklad, sklad_id=request.sklad_id)

    with open(result["file_path"], "rb") as f:
        pdf_content = f.read()

    return StreamingResponse(
        BytesIO(pdf_content),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={result['filename']}"}
    )

@pdf.get("/inventory/view/{token}")
async def view_inventory(token: str, db: Session = Depends(get_db)):
    from datetime import datetime, timezone
    
    inventory_token = db.query(InventoryToken).filter(
        InventoryToken.token == token,
        InventoryToken.is_active == True
    ).first()
    
    if not inventory_token:
        raise HTTPException(status_code=404, detail="Inventory report not found or expired")

    if inventory_token.expires_at:
        if datetime.now(timezone.utc) > inventory_token.expires_at:
            raise HTTPException(status_code=410, detail="Inventory report has expired")
    
    return JSONResponse({
        "organization": inventory_token.report_data.get("organization"),
        "sklad": inventory_token.report_data.get("sklad"),
        "items": inventory_token.report_data.get("items"),
        "created_at": inventory_token.report_data.get("created_at"),
        "items_count": inventory_token.report_data.get("items_count"),
        "signature_hash": inventory_token.signature_hash,
        "report_id": str(inventory_token.id)
    })

@pdf.post("/inventory/verify")
async def verify_by_hash(request: VerifyByHash = Body(...), db: Session = Depends(get_db)):

    pdf_service = PDFService(db)
    result = pdf_service.verify_by_hash(request.signature_hash)
    
    return JSONResponse(result)