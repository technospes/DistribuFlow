from sqlalchemy.orm import Session
from app.database.models.product import Product

def get_all_active_products(db: Session):
    """Fetch all products marked as active from the database."""
    return db.query(Product).filter(Product.is_active == True).all()

def get_product_by_sku(db: Session, sku: str):
    """Fetch a specific product by its exact SKU."""
    return db.query(Product).filter(Product.sku == sku, Product.is_active == True).first()