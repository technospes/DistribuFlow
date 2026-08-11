from app.database.session import SessionLocal

def get_db():
    """Dependency to yield a database session and close it automatically."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()