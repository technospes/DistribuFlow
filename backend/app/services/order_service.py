from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timezone
from typing import List, Tuple
from uuid import UUID
import threading

from app.schemas.order import OrderCreate, OrderStatus, CreditStatus, PaymentType, AvailabilityStatus
from app.repositories import order_repository, distributor_repository, product_repository
from app.database.models.distributor import Distributor
from app.services.invoice_service import generate_invoice_pdf
import logging
import httpx
from fastapi import BackgroundTasks

logger = logging.getLogger(__name__)

def _validate_distributor(db: Session, phone: str) -> Distributor:
    """Validates the distributor exists and is active (Rule 1 & 13)."""
    distributor = distributor_repository.get_distributor_by_phone(db, phone)
    if not distributor or distributor.status != "active":
        raise HTTPException(status_code=400, detail="Distributor is not active or does not exist.")
    return distributor

def _validate_and_calculate_stock(db: Session, items_in: list) -> Tuple[List[dict], float]:
    """Validates products, calculates subtotals, and checks stock (Rule 3)."""
    total_amount = 0.0
    processed_items = []
    
    for item_in in items_in:
        product = product_repository.get_product_by_sku(db, item_in.product_sku)
        if not product:
            raise HTTPException(status_code=400, detail=f"Product SKU {item_in.product_sku} not found.")
            
        subtotal = float(product.price_per_carton) * item_in.quantity_cartons
        total_amount += subtotal
        
        # Stock Check
        availability = AvailabilityStatus.FULL
        if item_in.quantity_cartons > product.stock_available:
            availability = AvailabilityStatus.PARTIAL
            
        processed_items.append({
            "product_id": product.id,
            "quantity_cartons": item_in.quantity_cartons,
            "price": product.price_per_carton,
            "subtotal": subtotal,
            "availability_status": availability.value
        })
        
    return processed_items, total_amount

def _validate_credit(distributor: Distributor, total_amount: float, payment_type: PaymentType) -> CreditStatus:
    """Validates credit limits if payment type is credit (Rule 2)."""
    if payment_type == PaymentType.CREDIT:
        if distributor.credit_limit is not None:
            if (float(distributor.credit_used) + total_amount) > float(distributor.credit_limit):
                return CreditStatus.HOLD
            return CreditStatus.OK
    return CreditStatus.NA

def _generate_order_number(db: Session) -> str:
    """Generates ORD-YYYYMMDD-NNNNN (Rule 8)."""
    today_str = datetime.now().strftime("%Y%m%d")
    prefix = f"ORD-{today_str}-"
    
    last_order_number = order_repository.get_latest_order_number_for_today(db, prefix)
    
    if last_order_number:
        last_sequence = int(last_order_number.split("-")[-1])
        new_sequence = last_sequence + 1
    else:
        new_sequence = 1
        
    return f"{prefix}{new_sequence:05d}"

def _notify_sales_manager(order_data: dict, distributor_phone: str):
    """Fire-and-forget notification to n8n (decoupled from order transaction)."""
    webhook_url = "http://localhost:5678/webhook/admin-alert" # Changed to localhost for venv
    try:
        payload = {
            "event": "new_order",
            "distributor_phone": distributor_phone,
            "order_number": order_data["order_number"],
            "total_amount": float(order_data["total_amount"]),
            "status": order_data["status"],
            "requested_delivery_date": order_data.get("requested_delivery_date")
        }
        # Short timeout so it fails fast in the background if n8n is down
        httpx.post(webhook_url, json=payload, timeout=2.0)
    except Exception as e:
        logger.warning(f"Failed to notify sales manager for order {order_data['order_number']}. Error: {e}")

def process_draft_order(db: Session, order_in: OrderCreate, background_tasks: BackgroundTasks = None):
    """Core business logic for creating a draft order."""
    
    # 1. Validate Distributor
    distributor = _validate_distributor(db, order_in.distributor_phone)
    
    # 2. Validate Products and Stock
    processed_items, total_amount = _validate_and_calculate_stock(db, order_in.items)

    # 3. Validate Credit
    credit_status = _validate_credit(distributor, total_amount, order_in.payment_type)

    # 4. Determine Initial Status
    initial_status = OrderStatus.DRAFT
    if credit_status == CreditStatus.HOLD:
        initial_status = OrderStatus.CREDIT_HOLD

    # 5. Generate Order Number
    order_number = _generate_order_number(db)

    # 6. Prepare Order Data
    order_data = {
        "order_number": order_number,
        "distributor_id": distributor.id,
        "status": initial_status.value,
        "credit_status": credit_status.value,
        "total_amount": total_amount,
        "payment_type": order_in.payment_type.value,
        "delivery_address": order_in.delivery_address,
        "requested_delivery_date": order_in.requested_delivery_date,
        "remarks": order_in.remarks
    }

    # 7. Save via Repository
    saved_order = order_repository.create_order(db, order_data, processed_items)
    
    # 8. Fire decoupled notification
    if background_tasks:
        background_tasks.add_task(_notify_sales_manager, order_data, distributor.phone_number)
    else:
        # When called from LangGraph, background_tasks is None. Spawn a quick thread!
        threading.Thread(target=_notify_sales_manager, args=(order_data, distributor.phone_number)).start()
        
    return saved_order

def approve_order(db: Session, order_id: UUID, approved_by: str = "Sales Manager"):
    """
    Business logic for approving an order. 
    Enforces valid state transitions and triggers invoice generation (Rule 6).
    """
    order = order_repository.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # IDEMPOTENCY CHECK: If already approved, just ensure invoice exists and return
    if order.status == OrderStatus.APPROVED.value:
        try:
            generate_invoice_pdf(db, order.id, generated_by=approved_by)
        except Exception:
            logger.exception("Invoice generation failed on idempotent approval for order %s", order.id)
        return order

    # Validate State Transition
    valid_states_for_approval = [OrderStatus.DRAFT.value, OrderStatus.CREDIT_HOLD.value]
    if order.status not in valid_states_for_approval:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot approve order in current status: {order.status}"
        )

    # Perform Approval Logic
    order.status = OrderStatus.APPROVED.value
    order.sales_approved = True
    order.approved_by = approved_by
    order.approved_at = datetime.now(timezone.utc)

    # Update via Repository
    updated_order = order_repository.update_order(db, order)
    
    # Trigger Rule 6: Generate Invoice PDF automatically upon approval
    try:
        generate_invoice_pdf(db, order.id, generated_by=approved_by)
    except Exception:
        # We don't want to fail the approval if PDF generation fails, 
        # but we should log it. In a real system, this might be a background task.
        logger.exception("Invoice generation failed for order %s", order.id)

    return updated_order

def cancel_order(db: Session, order_id: UUID, cancelled_by: str = "Sales Manager"):
    """
    Business logic for cancelling an order.
    """
    order = order_repository.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # IDEMPOTENCY CHECK
    if order.status == OrderStatus.CANCELLED.value:
        return order

    # Validate State Transition
    valid_states_for_cancellation = [OrderStatus.DRAFT.value, OrderStatus.CREDIT_HOLD.value]
    if order.status not in valid_states_for_cancellation:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot cancel order in current status: {order.status}"
        )

    # Perform Cancellation Logic
    order.status = OrderStatus.CANCELLED.value
    order.remarks = f"Cancelled by {cancelled_by}"
    
    updated_order = order_repository.update_order(db, order)
    return updated_order