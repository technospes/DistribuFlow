from sqlalchemy.orm import Session
import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(backend_dir)

from app.database.session import SessionLocal
from app.database.models.product import Product
from app.database.models.distributor import Distributor

def seed_data(db: Session):
    # 1. Seed Products (Alkush Industries - Pukhraj Hair Oils)
    print("Seeding full product catalog...")
    products = [
        Product(
            sku="PUKH-COCO-100",
            product_name="Pukhraj Coconut Oil",
            category="Hair Oil",
            variant="Coconut",
            size_ml=100,
            packing_type="PET Bottle",
            price_per_carton=2400.00,
            units_per_carton=50,
            stock_available=500,
            minimum_stock=50,
            description="Pure coconut oil for daily nourishment.",
            benefits="Deep conditioning, prevents hair fall.",
            is_active=True
        ),
        Product(
            sku="PUKH-JASMINE-100",
            product_name="Pukhraj Jasmine Coconut Oil",
            category="Hair Oil",
            variant="Jasmine",
            size_ml=100,
            packing_type="PET Bottle",
            price_per_carton=2600.00,
            units_per_carton=50,
            stock_available=300,
            minimum_stock=30,
            description="Non-sticky coconut oil with Jasmine fragrance.",
            benefits="Light nourishment, pleasant scent.",
            is_active=True
        ),
        Product(
            sku="PUKH-AMLA-200",
            product_name="Pukhraj Amla Oil",
            category="Hair Oil",
            variant="Amla",
            size_ml=200,
            packing_type="PET Bottle",
            price_per_carton=3200.00,
            units_per_carton=40,
            stock_available=200,
            minimum_stock=20,
            description="Amla enriched hair oil.",
            benefits="Promotes hair growth, prevents premature greying.",
            is_active=True
        ),
        Product(
            sku="PUKH-THANDA-100",
            product_name="Pukhraj Thanda Oil",
            category="Cooling Oil",
            variant="Mint/Cooling",
            size_ml=100,
            packing_type="PET Bottle",
            price_per_carton=3000.00,
            units_per_carton=50,
            stock_available=400,
            minimum_stock=50,
            description="Cooling hair oil for summer relief.",
            benefits="Relieves headache, stress, and fatigue.",
            is_active=True
        )
    ]
    
    for p in products:
        existing = db.query(Product).filter(Product.sku == p.sku).first()
        if not existing:
            db.add(p)
        else:
            existing.stock_available = p.stock_available
            existing.price_per_carton = p.price_per_carton
            existing.is_active = True

    # 2. Seed Distributors (Includes your active WhatsApp test number + Sharma Traders)
    print("Seeding active distributors...")
    distributors_data = [
        {
            "company_name": "Ayush Shukla Enterprise",
            "owner_name": "Ayush Shukla",
            "phone_number": "919548902855",
            "city": "Greater Noida",
            "state": "Uttar Pradesh",
            "credit_limit": 50000.00,
            "status": "active"
        },
        {
            "company_name": "Sharma Traders",
            "owner_name": "Rahul Sharma",
            "phone_number": "919876543210",
            "city": "Roorkee",
            "state": "Uttarakhand",
            "credit_limit": 50000.00,
            "status": "active"
        }
    ]

    for d_data in distributors_data:
        existing_dist = db.query(Distributor).filter(Distributor.phone_number == d_data["phone_number"]).first()
        if not existing_dist:
            distributor = Distributor(**d_data, credit_used=0.00)
            db.add(distributor)
        else:
            existing_dist.status = "active"
            existing_dist.credit_limit = d_data["credit_limit"]

    db.commit()
    print("Hybrid database seeding completed successfully!")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()