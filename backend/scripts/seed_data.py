from sqlalchemy.orm import Session
import os
import sys

# Add the backend directory to the sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)

from app.database.session import SessionLocal
from app.database.models import Distributor, Product

def seed_database():
    db: Session = SessionLocal()
    try:
        # 1. Seed/Update Distributor
        # Using the exact phone number from the WhatsApp tests
        test_phone = "919548902855" 
        
        distributor = db.query(Distributor).filter(Distributor.phone_number == test_phone).first()
        if not distributor:
            print(f"Creating test distributor with phone: {test_phone}")
            distributor = Distributor(
                company_name="Test Distributor",
                owner_name="Test Owner",
                phone_number=test_phone,
                credit_limit=50000.0,  # 50k limit to test normal vs hold logic
                credit_used=0.0,
                status="active" # Must be 'active' to pass Rule 1!
            )
            db.add(distributor)
        else:
            print(f"Distributor {test_phone} exists. Forcing status to 'active' and resetting credit_used to 0.")
            distributor.status = "active"
            distributor.credit_limit = 50000.0
            distributor.credit_used = 0.0

        # 2. Seed Product intelligently
        # We look for PUKH-COCO-100 first to avoid duplicates.
        sku = "PUKH-COCO-100"
        product = db.query(Product).filter(Product.sku == sku).first()
        
        if not product:
            print(f"Creating product: Coconut Oil 100ml ({sku})")
            product = Product(
                sku=sku,
                product_name="Coconut Oil",
                size_ml=100,
                price_per_carton=2400.00,
                stock_available=100 # Plenty of stock for testing
            )
            db.add(product)
        else:
            print(f"Product {sku} exists. Refreshing stock to 100 and price to 2400.")
            product.stock_available = 100
            product.price_per_carton = 2400.00

        db.commit()
        print("\nDatabase seeding completed successfully! You are ready to test.")

    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()