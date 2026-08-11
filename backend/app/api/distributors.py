from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.dependencies import get_db
from app.schemas.distributor import DistributorResponse
from app.services import distributor_service
from app.database.models.distributor import Distributor

router = APIRouter()

@router.get("/", response_model=List[DistributorResponse])
def list_all_distributors(db: Session = Depends(get_db)):
    """Retrieve all distributors for the dashboard."""
    return db.query(Distributor).order_by(Distributor.created_at.desc()).all()

@router.get("/{phone_number}", response_model=DistributorResponse)
def read_distributor(phone_number: str, db: Session = Depends(get_db)):
    """Retrieve a distributor by their WhatsApp phone number."""
    distributor = distributor_service.retrieve_distributor_profile(db, phone_number)
    
    if not distributor:
        # MVP Rule 1: Unknown Distributor -> Lead Creation happens via webhook logic later.
        # For the dashboard/REST API, we just return a 404.
        raise HTTPException(status_code=404, detail="Distributor not found")
    
    return distributor