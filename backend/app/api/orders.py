from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.dependencies import get_db
from app.schemas.order import OrderCreate, OrderResponse
from app.services import order_service
from app.repositories import order_repository
from app.database.models.order import Order
from typing import List

router = APIRouter()

@router.get("/", response_model=List[OrderResponse])
def list_all_orders(db: Session = Depends(get_db)):
    """Retrieve all orders for the dashboard."""
    orders = db.query(Order).order_by(Order.created_at.desc()).all()
    return orders

@router.post("/", response_model=OrderResponse)
def create_draft_order(order_in: OrderCreate, db: Session = Depends(get_db)):
    """Create a new draft order applying business rules (Credit, Stock)."""
    return order_service.process_draft_order(db, order_in)

@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: UUID, db: Session = Depends(get_db)):
    """Retrieve an order by ID."""
    order = order_repository.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.post("/{order_id}/approve", response_model=OrderResponse)
def approve_order(order_id: UUID, approved_by: str = "Sales Manager", db: Session = Depends(get_db)):
    """Approve a draft or credit-held order via the Service layer."""
    return order_service.approve_order(db, order_id, approved_by)

@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(order_id: UUID, cancelled_by: str = "Sales Manager", db: Session = Depends(get_db)):
    """Cancel a draft or credit-held order."""
    return order_service.cancel_order(db, order_id, cancelled_by)