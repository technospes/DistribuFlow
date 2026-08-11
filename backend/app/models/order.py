from sqlalchemy import Column, String, Boolean, Numeric, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.database.session import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    order_number = Column(String, unique=True, index=True, nullable=False) # ORD-YYYYMMDD-NNNNN
    distributor_id = Column(UUID(as_uuid=True), ForeignKey("distributors.id"), nullable=False)
    status = Column(String, default="Draft", nullable=False)
    credit_status = Column(String, default="na", nullable=False) # 'ok' | 'hold' | 'na'
    total_amount = Column(Numeric, nullable=False)
    payment_type = Column(String, nullable=False) # 'credit' | 'cod' | 'prepaid'
    delivery_address = Column(String, nullable=True)
    requested_delivery_date = Column(String, nullable=True)
    remarks = Column(String, nullable=True)
    sales_approved = Column(Boolean, default=False)
    approved_by = Column(String, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    distributor = relationship("Distributor", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    invoice = relationship("Invoice", back_populates="order", uselist=False)
    payments = relationship("Payment", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    quantity_cartons = Column(Integer, nullable=False)
    fulfilled_cartons = Column(Integer, nullable=True)
    availability_status = Column(String, default="full", nullable=False) # 'full' | 'partial' | 'backorder'
    price = Column(Numeric, nullable=False)
    subtotal = Column(Numeric, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")