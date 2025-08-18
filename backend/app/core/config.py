"""
Configuration settings for the Interview Prep AI Coach application
"""
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Interview Prep AI Coach"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "mysql+pymysql://root:admin@server/interview_prep_db"
    
    # Security
    SECRET_KEY: str = "4b5f3a72e4d0b68339d6e0a5d4021c9a8b86fef39414a84c63f8a132f54f1c78"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS - Don't load from env to avoid JSON parsing issues
    ALLOWED_HOSTS: List[str] = ["http://localhost:4200", "http://localhost:3000"]
    
    # AI Services
    GEMINI_API_KEY: str = "AIzaSyBPheiRK87uOc7mrraKDeFE3GUluueNy04"
    
    
    # Email Configuration
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False
    
    # File Upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "uploads"
    
    # No validator needed since we're not loading from env

    # Pydantic v2 settings configuration
    # Load env from backend/.env if it exists, otherwise use defaults
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()