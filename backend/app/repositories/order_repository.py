from sqlalchemy.orm import Session
from uuid import UUID

from app.database.models.order import Order, OrderItem

def create_order(db: Session, order_data: dict, items_data: list) -> Order:
    """
    Strictly handles database insertion. 
    Business logic (like order numbers) is handled by the Service.
    """
    
    # Create Main Order
    db_order = Order(
        order_number=order_data["order_number"],
        distributor_id=order_data["distributor_id"],
        status=order_data["status"],
        credit_status=order_data["credit_status"],
        total_amount=order_data["total_amount"],
        payment_type=order_data["payment_type"],
        delivery_address=order_data.get("delivery_address"),
        remarks=order_data.get("remarks")
    )
    db.add(db_order)
    db.flush() # Flush to get the db_order.id
    
    # Create Order Items
    for item in items_data:
        db_item = OrderItem(
            order_id=db_order.id,
            product_id=item["product_id"],
            quantity_cartons=item["quantity_cartons"],
            price=item["price"],
            subtotal=item["subtotal"],
            availability_status=item["availability_status"]
        )
        db.add(db_item)
        
    db.commit()
    db.refresh(db_order)
    return db_order

def get_order_by_id(db: Session, order_id: UUID) -> Order:
    return db.query(Order).filter(Order.id == order_id).first()

def get_latest_order_number_for_today(db: Session, prefix: str) -> str:
    """Helper for the service to determine the next sequence number."""
    last_order = db.query(Order).filter(Order.order_number.like(f"{prefix}%")).order_by(Order.order_number.desc()).first()
    if last_order:
        return last_order.order_number
    return None

def update_order(db: Session, db_order: Order) -> Order:
    """Commits changes made to an existing order object to the database."""
    db.commit()
    db.refresh(db_order)
    return db_order