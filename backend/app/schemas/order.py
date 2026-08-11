from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from enum import Enum

# Import ProductSummary so we can bundle it into the Order item response
from app.schemas.product import ProductSummary

# --- Enums for Strict Typing ---
class OrderStatus(str, Enum):
    DRAFT = "Draft"
    CREDIT_HOLD = "Credit Hold"
    APPROVED = "Approved"
    DISPATCHED = "Dispatched"
    CANCELLED = "Cancelled"

class PaymentType(str, Enum):
    CREDIT = "credit"
    CASH = "cash"
    ADVANCE = "advance"

class CreditStatus(str, Enum):
    OK = "ok"
    HOLD = "hold"
    NA = "na"

class AvailabilityStatus(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    BACKORDER = "backorder"

# --- Order Item Schemas ---
class OrderItemCreate(BaseModel):
    product_sku: str
    quantity_cartons: int = Field(gt=0) # Must be greater than 0

class OrderItemResponse(BaseModel):
    id: UUID
    product_id: UUID
    quantity_cartons: int
    fulfilled_cartons: Optional[int] = None
    availability_status: AvailabilityStatus
    price: float
    subtotal: float
    
    # We include the product details so the frontend doesn't get a 404 error fetching by UUID
    product: Optional[ProductSummary] = None

    class Config:
        from_attributes = True

# --- Order Schemas ---
class OrderCreate(BaseModel):
    distributor_phone: str
    payment_type: PaymentType
    items: List[OrderItemCreate]
    delivery_address: Optional[str] = None
    requested_delivery_date: Optional[str] = None
    remarks: Optional[str] = None

class OrderResponse(BaseModel):
    id: UUID
    order_number: str
    distributor_id: UUID
    status: OrderStatus
    credit_status: CreditStatus
    total_amount: float
    payment_type: PaymentType
    delivery_address: Optional[str] = None
    requested_delivery_date: Optional[str] = None
    remarks: Optional[str] = None
    sales_approved: bool
    items: List[OrderItemResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True