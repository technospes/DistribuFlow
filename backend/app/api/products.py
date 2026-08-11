from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.dependencies import get_db
from app.schemas.product import ProductResponse, ProductSummary
from app.services import catalog_service

router = APIRouter()

@router.get("/", response_model=List[ProductSummary])
def read_products(db: Session = Depends(get_db)):
    """Retrieve all active products from the catalog (Summary View)."""
    return catalog_service.list_available_products(db)

@router.get("/{sku}", response_model=ProductResponse)
def read_product_details(sku: str, db: Session = Depends(get_db)):
    """Retrieve full details for a specific product by SKU."""
    product = catalog_service.find_product_by_sku(db, sku)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product