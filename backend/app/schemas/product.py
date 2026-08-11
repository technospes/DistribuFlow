from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class ProductBase(BaseModel):
    sku: str
    product_name: str
    category: Optional[str] = None
    variant: Optional[str] = None
    size_ml: Optional[int] = None
    packing_type: Optional[str] = None
    price_per_carton: float
    units_per_carton: Optional[int] = None
    description: Optional[str] = None
    benefits: Optional[str] = None
    is_active: bool = True

class ProductResponse(ProductBase):
    id: UUID
    stock_available: int
    minimum_stock: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProductSummary(BaseModel):
    id: UUID
    sku: str
    product_name: str
    price_per_carton: float
    stock_available: int

    class Config:
        from_attributes = True