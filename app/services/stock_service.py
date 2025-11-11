from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from typing import List
from uuid import UUID

from app.models.stock_oper import StockOperation, OperationType, StockOperationCreate, StockOperationResponse
from app.models.nomen import Stock, Nomenclature
from app.models.sklads import Sklads
from app.models.auth import User
from typing import Optional


class StockOperationService:
    def __init__(self, db: Session):
        self.db = db

    def _get_orga_id(self, current_user: User) -> UUID:
        if not current_user.connect_organization:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not associated with any organization"
            )
        return UUID(current_user.connect_organization)

    def _validate_sklad_belongs_to_org(self, sklad_id: UUID, organization_id: UUID):
        sklad = self.db.query(Sklads).filter(
            Sklads.id == sklad_id,
            Sklads.organization_id == organization_id,
            Sklads.is_deleted == False
        ).first()
        
        if not sklad:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Warehouse not found or does not belong to your organization"
            )
        return sklad

    def _validate_nomen(self, nomenclature_id: UUID, organization_id: UUID):
        nomen = self.db.query(Nomenclature).filter(
            Nomenclature.id == nomenclature_id,
            Nomenclature.organization_id == organization_id,
            Nomenclature.is_deleted == False
        ).first()
        
        if not nomen:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nomenclature not found or does not belong to your organization"
            )
        return nomen

    def _get_or_create_stock(self, nomenclature_id: UUID, sklad_id: UUID) -> Stock:
        stock = self.db.query(Stock).filter(
            Stock.nomenclature_id == nomenclature_id,
            Stock.sklad_id == sklad_id
        ).first()
        
        if not stock:
            stock = Stock(
                nomenclature_id=nomenclature_id,
                sklad_id=sklad_id,
                quantity=0,
                reserved=0
            )
            self.db.add(stock)
            self.db.flush()
        
        return stock

    def _check_stock_availability(self, nomenclature_id: UUID, sklad_id: UUID, required_quantity: int):
        stock = self.db.query(Stock).filter(
            Stock.nomenclature_id == nomenclature_id,
            Stock.sklad_id == sklad_id
        ).first()
        
        if not stock or stock.quantity < required_quantity:
            available = stock.quantity if stock else 0
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Available: {available}, Required: {required_quantity}"
            )

    def create_operation(self, operation_data: StockOperationCreate, current_user: User) -> StockOperationResponse:
        organization_id = self._get_orga_id(current_user)
        self._validate_nomen(operation_data.nomenclature_id, organization_id)
        if operation_data.from_sklad_id:
            self._validate_sklad_belongs_to_org(operation_data.from_sklad_id, organization_id)
        if operation_data.to_sklad_id:
            self._validate_sklad_belongs_to_org(operation_data.to_sklad_id, organization_id)

        if operation_data.operation_type == OperationType.TRANSFER:
            return self._process_transfer(operation_data, organization_id, current_user.id)
        elif operation_data.operation_type == OperationType.SALE:
            return self._process_sale(operation_data, organization_id, current_user.id)
        elif operation_data.operation_type == OperationType.DISPOSAL:
            return self._process_disposal(operation_data, organization_id, current_user.id)
        elif operation_data.operation_type == OperationType.ADJUSTMENT:
            return self._process_adjustment(operation_data, organization_id, current_user.id)
        elif operation_data.operation_type == OperationType.RECEIPT:
            return self._process_receipt(operation_data, organization_id, current_user.id)
        elif operation_data.operation_type == OperationType.RETURN:
            return self._process_return(operation_data, organization_id, current_user.id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unknown operation type"
            )

    def _process_transfer(self, operation_data: StockOperationCreate, organization_id: UUID, user_id: UUID) -> StockOperationResponse:
        self._check_stock_availability(operation_data.nomenclature_id, operation_data.from_sklad_id, operation_data.quantity)

        from_stock = self._get_or_create_stock(operation_data.nomenclature_id, operation_data.from_sklad_id)
        from_stock.quantity -= operation_data.quantity

        to_stock = self._get_or_create_stock(operation_data.nomenclature_id, operation_data.to_sklad_id)
        to_stock.quantity += operation_data.quantity

        operation = StockOperation(
            organization_id=organization_id,
            operation_type=OperationType.TRANSFER,
            from_sklad_id=operation_data.from_sklad_id,
            to_sklad_id=operation_data.to_sklad_id,
            nomenclature_id=operation_data.nomenclature_id,
            quantity=operation_data.quantity,
            performed_by=user_id,
            comment=operation_data.comment,
            operation_metadata=operation_data.operation_metadata or {}
        )
        
        try:
            self.db.add(operation)
            self.db.commit()
            self.db.refresh(operation)
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error creating operation"
            )
        
        return StockOperationResponse.from_orm(operation)

    def _process_sale(self, operation_data: StockOperationCreate, organization_id: UUID, user_id: UUID) -> StockOperationResponse:
        self._check_stock_availability(operation_data.nomenclature_id, operation_data.from_sklad_id, operation_data.quantity)

        stock = self._get_or_create_stock(operation_data.nomenclature_id, operation_data.from_sklad_id)
        stock.quantity -= operation_data.quantity
        

        operation = StockOperation(
            organization_id=organization_id,
            operation_type=OperationType.SALE,
            from_sklad_id=operation_data.from_sklad_id,
            to_sklad_id=None,
            nomenclature_id=operation_data.nomenclature_id,
            quantity=operation_data.quantity,
            performed_by=user_id,
            comment=operation_data.comment,
            operation_metadata=operation_data.operation_metadata or {}
        )
        
        try:
            self.db.add(operation)
            self.db.commit()
            self.db.refresh(operation)
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error creating operation"
            )
        
        return StockOperationResponse.from_orm(operation)

    def _process_disposal(self, operation_data: StockOperationCreate, organization_id: UUID, user_id: UUID) -> StockOperationResponse:
        self._check_stock_availability(
            operation_data.nomenclature_id,
            operation_data.from_sklad_id,
            operation_data.quantity
        )

        stock = self._get_or_create_stock(operation_data.nomenclature_id, operation_data.from_sklad_id)
        stock.quantity -= operation_data.quantity

        operation = StockOperation(
            organization_id=organization_id,
            operation_type=OperationType.DISPOSAL,
            from_sklad_id=operation_data.from_sklad_id,
            to_sklad_id=None,
            nomenclature_id=operation_data.nomenclature_id,
            quantity=operation_data.quantity,
            performed_by=user_id,
            comment=operation_data.comment,
            operation_metadata=operation_data.operation_metadata or {}
        )
        
        try:
            self.db.add(operation)
            self.db.commit()
            self.db.refresh(operation)
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error creating operation"
            )
        
        return StockOperationResponse.from_orm(operation)

    def _process_adjustment(self, operation_data: StockOperationCreate, organization_id: UUID, user_id: UUID) -> StockOperationResponse:
        if not operation_data.from_sklad_id and not operation_data.to_sklad_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="from_sklad_id or to_sklad_id is required for ADJUSTMENT"
            )
        
        sklad_id = operation_data.to_sklad_id or operation_data.from_sklad_id
        stock = self._get_or_create_stock(operation_data.nomenclature_id, sklad_id)

        stock.quantity += operation_data.quantity
        
        if stock.quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stock quantity cannot be negative after adjustment"
            )

        operation = StockOperation(
            organization_id=organization_id,
            operation_type=OperationType.ADJUSTMENT,
            from_sklad_id=operation_data.from_sklad_id,
            to_sklad_id=operation_data.to_sklad_id,
            nomenclature_id=operation_data.nomenclature_id,
            quantity=operation_data.quantity,
            performed_by=user_id,
            comment=operation_data.comment,
            operation_metadata=operation_data.operation_metadata or {}
        )
        
        try:
            self.db.add(operation)
            self.db.commit()
            self.db.refresh(operation)
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error creating operation"
            )
        
        return StockOperationResponse.from_orm(operation)

    def _process_receipt(self, operation_data: StockOperationCreate, organization_id: UUID, user_id: UUID) -> StockOperationResponse:
        stock = self._get_or_create_stock(operation_data.nomenclature_id, operation_data.to_sklad_id)
        stock.quantity += operation_data.quantity

        operation = StockOperation(
            organization_id=organization_id,
            operation_type=OperationType.RECEIPT,
            from_sklad_id=None,
            to_sklad_id=operation_data.to_sklad_id,
            nomenclature_id=operation_data.nomenclature_id,
            quantity=operation_data.quantity,
            performed_by=user_id,
            comment=operation_data.comment,
            operation_metadata=operation_data.operation_metadata or {}
        )
        
        try:
            self.db.add(operation)
            self.db.commit()
            self.db.refresh(operation)
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error creating operation"
            )
        
        return StockOperationResponse.from_orm(operation)

    def _process_return(self, operation_data: StockOperationCreate, organization_id: UUID, user_id: UUID) -> StockOperationResponse:
        stock = self._get_or_create_stock(operation_data.nomenclature_id, operation_data.to_sklad_id)
        stock.quantity += operation_data.quantity
        operation = StockOperation(
            organization_id=organization_id,
            operation_type=OperationType.RETURN,
            from_sklad_id=None,
            to_sklad_id=operation_data.to_sklad_id,
            nomenclature_id=operation_data.nomenclature_id,
            quantity=operation_data.quantity,
            performed_by=user_id,
            comment=operation_data.comment,
            operation_metadata=operation_data.operation_metadata or {}
        )
        
        try:
            self.db.add(operation)
            self.db.commit()
            self.db.refresh(operation)
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error creating operation"
            )
        
        return StockOperationResponse.from_orm(operation)

    def get_operations(self, organization_id: UUID, skip: int = 0, limit: int = 100, operation_type: Optional[OperationType] = None, nomenclature_id: Optional[UUID] = None,
        sklad_id: Optional[UUID] = None) -> List[StockOperationResponse]:
        query = self.db.query(StockOperation).filter(StockOperation.organization_id == organization_id)
        
        if operation_type:
            query = query.filter(StockOperation.operation_type == operation_type)
        
        if nomenclature_id:
            query = query.filter(StockOperation.nomenclature_id == nomenclature_id)
        
        if sklad_id:
            query = query.filter(
                (StockOperation.from_sklad_id == sklad_id) |
                (StockOperation.to_sklad_id == sklad_id)
            )
        
        operations = query.order_by(StockOperation.created_at.desc()).offset(skip).limit(limit).all()
        return [StockOperationResponse.from_orm(op) for op in operations]

    def get_operation_by_id(self, operation_id: UUID, organization_id: UUID) -> StockOperationResponse:
        operation = self.db.query(StockOperation).filter(
            StockOperation.id == operation_id,
            StockOperation.organization_id == organization_id
        ).first()
        
        if not operation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operation not found"
            )
        
        return StockOperationResponse.from_orm(operation)

