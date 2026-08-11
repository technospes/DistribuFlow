from sqlalchemy.orm import Session
from app.repositories import product_repository

def list_available_products(db: Session):
    """Business logic to list available products."""
    # Here we just pass through to the repository. 
    # Later, we might add logic to format the data for the AI.
    return product_repository.get_all_active_products(db)

def find_product_by_sku(db: Session, sku: str):
    """Business logic to find a specific product."""
    return product_repository.get_product_by_sku(db, sku)