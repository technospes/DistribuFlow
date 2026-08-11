from sqlalchemy.orm import Session
from app.database.models.distributor import Distributor

def get_distributor_by_phone(db: Session, phone_number: str):
    """Fetch a distributor record by their unique phone number."""
    return db.query(Distributor).filter(Distributor.phone_number == phone_number).first()