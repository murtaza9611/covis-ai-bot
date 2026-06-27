from pydantic_settings import BaseSettings
from src.settings import settings


class Settings(BaseSettings):
    TABLE_NAME: str = "chat_history"
    DATABSE_URL: str = settings.DATABASE_URL  # Add this line for DATABASE_URL
    SCHEMA_NAME: str = settings.SCHEMA_NAME


settings = Settings()
