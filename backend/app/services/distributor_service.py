from sqlalchemy.orm import Session
from app.repositories import distributor_repository

def retrieve_distributor_profile(db: Session, phone_number: str):
    """Business logic to retrieve distributor details."""
    # Pass through to repository
    return distributor_repository.get_distributor_by_phone(db, phone_number)