from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

class DistributorBase(BaseModel):
    company_name: Optional[str] = None
    owner_name: Optional[str] = None
    phone_number: str
    email: Optional[str] = None
    gst_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    credit_limit: Optional[float] = None

class DistributorResponse(DistributorBase):
    id: UUID
    credit_used: float
    status: str
    assigned_sales_executive: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class LeadResponse(BaseModel):
    id: UUID
    phone_number: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True