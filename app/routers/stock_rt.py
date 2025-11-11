from fastapi import APIRouter, Depends, Query, Path, Body, status, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.core import get_db
from app.core.security import get_me
from app.models.stock_oper import StockOperationCreate, StockOperationResponse, OperationType
from app.models.auth import User
from app.services.stock_service import StockOperationService

stockk = APIRouter(prefix="/api/stock", tags=["Stock Operations"])


@stockk.post("/create/", response_model=StockOperationResponse, status_code=status.HTTP_201_CREATED)
async def create_operation(data: StockOperationCreate = Body(...), db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    service = StockOperationService(db)
    return service.create_operation(data, current_user)


@stockk.get("/all/", response_model=List[StockOperationResponse])
async def get_operations(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000), operation_type: Optional[str] = Query(None, description="Filter by operation type"), nomenclature_id: Optional[UUID] = Query(None, description="Filter by nomenclature ID"),
    sklad_id: Optional[UUID] = Query(None, description="Filter by warehouse ID"), db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    service = StockOperationService(db)
    organization_id = UUID(current_user.connect_organization) if current_user.connect_organization else None
    
    if not organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with any organization"
        )
    
    op_type = None
    if operation_type:
        try:
            op_type = OperationType[operation_type.upper()]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid operation type: {operation_type}"
            )
    
    return service.get_operations(
        organization_id=organization_id,
        skip=skip,
        limit=limit,
        operation_type=op_type,
        nomenclature_id=nomenclature_id,
        sklad_id=sklad_id
    )


@stockk.get("/{operation_id}", response_model=StockOperationResponse)
async def get_operation(operation_id: UUID = Path(...), db: Session = Depends(get_db), current_user: User = Depends(get_me)):
    service = StockOperationService(db)
    organization_id = UUID(current_user.connect_organization) if current_user.connect_organization else None
    
    if not organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with any organization"
        )
    
    return service.get_operation_by_id(operation_id, organization_id)

