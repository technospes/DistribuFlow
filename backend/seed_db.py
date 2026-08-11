# backend/seed_db.py
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.database.models.product import Product
from app.database.models.distributor import Distributor

def seed_data(db: Session):
    # 1. Seed Products (Alkush Industries - Pukhraj Hair Oils)
    print("Seeding products...")
    products = [
        Product(
            sku="PUKH-COCO-100",
            product_name="Pukhraj Coconut Oil",
            category="Hair Oil",
            variant="Coconut",
            size_ml=100,
            packing_type="PET Bottle",
            price_per_carton=2400.00, # Example: 50 bottles * 48rs
            units_per_carton=50,
            stock_available=500, # Manually maintained per Rule 12
            minimum_stock=50,
            description="Pure coconut oil for daily nourishment.",
            benefits="Deep conditioning, prevents hair fall."
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
            benefits="Light nourishment, pleasant scent."
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
            benefits="Promotes hair growth, prevents premature greying."
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
            benefits="Relieves headache, stress, and fatigue."
        )
    ]
    
    for p in products:
        # Check if exists to avoid duplicates if run twice
        existing = db.query(Product).filter(Product.sku == p.sku).first()
        if not existing:
            db.add(p)

    # 2. Seed Demo Distributor (Must set status = 'active' per Rule 13)
    print("Seeding demo distributor...")
    demo_phone = "919876543210" # Use a test number you will use in WhatsApp
    existing_dist = db.query(Distributor).filter(Distributor.phone_number == demo_phone).first()
    
    if not existing_dist:
        distributor = Distributor(
            company_name="Sharma Traders",
            owner_name="Rahul Sharma",
            phone_number=demo_phone,
            city="Roorkee",
            state="Uttarakhand",
            credit_limit=50000.00,
            credit_used=0.00,
            status="active" # CRITICAL: Rule 13
        )
        db.add(distributor)

    db.commit()
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()