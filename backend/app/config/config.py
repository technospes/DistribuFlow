import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # This reads from the .env file or environment variables
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://admin:adminpassword@localhost:5432/aidoms"
    )
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    class Config:
        env_file = ".env"

settings = Settings()