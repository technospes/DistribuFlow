from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Literal
from app.core.dependencies import get_db
from app.database.models import Product, Distributor
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Pydantic Schemas for Admin Inputs (Hardened) ---
class StockUpdate(BaseModel):
    stock_available: int = Field(ge=0, description="Stock cannot be negative")

class CreditUpdate(BaseModel):
    credit_used: float = Field(ge=0, description="Credit used cannot be negative")

class ProductCreateAdmin(BaseModel):
    sku: str
    product_name: str
    size_ml: Optional[int] = Field(default=None, gt=0, description="Size must be greater than 0")
    price_per_carton: float = Field(gt=0, description="Price must be greater than 0")
    stock_available: int = Field(default=0, ge=0, description="Stock cannot be negative")

class DistributorCreateAdmin(BaseModel):
    company_name: str
    owner_name: str
    phone_number: str
    address: Optional[str] = None
    credit_limit: float = Field(default=0.0, ge=0, description="Credit limit cannot be negative")
    # Enforcing Rule 13: Only valid statuses allowed
    status: Literal["lead", "active", "inactive"] = "active"

# --- Endpoints ---

@router.post("/products")
def create_product(payload: ProductCreateAdmin, db: Session = Depends(get_db)):
    """Admin endpoint to create a new product."""
    existing = db.query(Product).filter(Product.sku == payload.sku).first()
    if existing:
        raise HTTPException(status_code=400, detail="Product with this SKU already exists.")
    
    new_product = Product(
        sku=payload.sku,
        product_name=payload.product_name,
        size_ml=payload.size_ml,
        price_per_carton=payload.price_per_carton,
        stock_available=payload.stock_available,
        is_active=True
    )
    db.add(new_product)
    # Note: PostgreSQL unique constraint on 'sku' acts as the final safeguard here
    db.commit()
    db.refresh(new_product)
    logger.info(f"Admin created new product: {payload.sku}")
    return new_product

@router.post("/distributors")
def create_distributor(payload: DistributorCreateAdmin, db: Session = Depends(get_db)):
    """Admin endpoint to create a new distributor."""
    existing = db.query(Distributor).filter(Distributor.phone_number == payload.phone_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Distributor with this phone number already exists.")
    
    new_distributor = Distributor(
        company_name=payload.company_name,
        owner_name=payload.owner_name,
        phone_number=payload.phone_number,
        address=payload.address,
        credit_limit=payload.credit_limit,
        status=payload.status,
        credit_used=0.0
    )
    db.add(new_distributor)
    # Note: PostgreSQL unique constraint on 'phone_number' acts as the final safeguard
    db.commit()
    db.refresh(new_distributor)
    logger.info(f"Admin created new distributor: {payload.phone_number}")
    return new_distributor

@router.patch("/products/{sku}/stock")
def update_product_stock(sku: str, payload: StockUpdate, db: Session = Depends(get_db)):
    """Admin endpoint to manually update stock levels (Rule 12)."""
    product = db.query(Product).filter(Product.sku == sku).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # In a full V2, this would also insert into an `inventory_adjustments` table
    product.stock_available = payload.stock_available
    db.commit()
    logger.info(f"Admin updated stock for {sku} to {payload.stock_available}")
    return {"message": "Stock updated successfully", "new_stock": product.stock_available}

@router.patch("/distributors/{phone}/credit")
def update_distributor_credit(phone: str, payload: CreditUpdate, db: Session = Depends(get_db)):
    """Admin endpoint to manually update utilized credit (Rule 12)."""
    distributor = db.query(Distributor).filter(Distributor.phone_number == phone).first()
    if not distributor:
        raise HTTPException(status_code=404, detail="Distributor not found")
    
    # In a full V2, this would also insert into a `credit_adjustments` table
    distributor.credit_used = payload.credit_used
    db.commit()
    logger.info(f"Admin updated credit_used for {phone} to {payload.credit_used}")
    return {"message": "Credit updated successfully", "new_credit_used": distributor.credit_used}