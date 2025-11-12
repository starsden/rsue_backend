from fastapi import APIRouter, Depends, Query, Path, Body, status, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.core import get_db
from app.core.security import get_me
from app.models.sklad_docs import SkladDocumentCreate, SkladDocumentUpdate, SkladDocumentResponse, SkladDocumentItemCreate, SkladDocumentItemUpdate, SkladDocumentItemResponse
from app.models.auth import User
from app.services.sdocs_service import SkladDocumentService

docs = APIRouter(prefix="/api/docsklad", tags=["Sklad Documents"])

@docs.post("/create", response_model=SkladDocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(data: SkladDocumentCreate = Body(...), db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    service = SkladDocumentService(db)
    return service.create_document(data, current_user)

@docs.get("/list", response_model=List[SkladDocumentResponse])
def list_documents(sklad_id: Optional[UUID] = Query(None), db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    service = SkladDocumentService(db)
    org_id = UUID(current_user.connect_organization) if current_user.connect_organization else None
    if not org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not associated with any organization")
    return service.get_documents(org_id, sklad_id)

@docs.get("/{doc_id}", response_model=SkladDocumentResponse)
def get_document(doc_id: UUID = Path(...), db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    service = SkladDocumentService(db)
    org_id = UUID(current_user.connect_organization) if current_user.connect_organization else None
    if not org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not associated with any organization")
    return service.get_document_by_id(doc_id, org_id)

@docs.put("/{doc_id}", response_model=SkladDocumentResponse)
def update_document(doc_id: UUID = Path(...), data: SkladDocumentUpdate = Body(...), db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    service = SkladDocumentService(db)
    org_id = UUID(current_user.connect_organization) if current_user.connect_organization else None
    if not org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not associated with any organization")
    return service.update_document(doc_id, data, org_id)

@docs.delete("/{doc_id}", status_code=status.HTTP_200_OK)
def delete_document(doc_id: UUID = Path(...), db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    service = SkladDocumentService(db)
    org_id = UUID(current_user.connect_organization) if current_user.connect_organization else None
    if not org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not associated with any organization")
    return service.delete_document(doc_id, org_id)

@docs.post("/{doc_id}/items", response_model=SkladDocumentItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(doc_id: UUID = Path(...), data: SkladDocumentItemCreate = Body(...), db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    service = SkladDocumentService(db)
    org_id = UUID(current_user.connect_organization) if current_user.connect_organization else None
    if not org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not associated with any organization")
    return service.create_item(doc_id, data, org_id)

@docs.get("/{doc_id}/items", response_model=List[SkladDocumentItemResponse])
def list_items(doc_id: UUID = Path(...), item_id: Optional[UUID] = Query(None), db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    service = SkladDocumentService(db)
    org_id = UUID(current_user.connect_organization) if current_user.connect_organization else None
    if not org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not associated with any organization")
    items = service.get_items(doc_id, org_id)
    if item_id:
        filtered = [item for item in items if item.id == item_id]
        return filtered if filtered else []
    return items


@docs.put("/items/{item_id}", response_model=SkladDocumentItemResponse)
def update_item(item_id: UUID = Path(...), data: SkladDocumentItemUpdate = Body(...), db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    service = SkladDocumentService(db)
    org_id = UUID(current_user.connect_organization) if current_user.connect_organization else None
    if not org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not associated with any organization")
    return service.update_item(item_id, data, org_id)

@docs.delete("/items/{item_id}", status_code=status.HTTP_200_OK)
def delete_item(item_id: UUID = Path(...), db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    service = SkladDocumentService(db)
    org_id = UUID(current_user.connect_organization) if current_user.connect_organization else None
    if not org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not associated with any organization")
    return service.delete_item(item_id, org_id)

