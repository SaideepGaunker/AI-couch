"""
Configuration settings for the Interview Prep AI Coach application
"""
import os
from typing import List
from pydantic import field_validator, validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import secrets


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Interview Prep AI Coach"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str = "mysql+pymysql://root:mySQL@localhost:3306/interview_prep_db"
    
    # Security - Use environment variables or generate secure defaults
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["*"]  # Allow all origins for development
    
    # AI Services
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "AIzaSyCwlSlBdFgWIFR40jyFkR1AfwlTJIqEblY")
    
    # Redis Configuration (for caching and session storage)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_ENABLED: bool = False  # Set to True when Redis is available
    
    # Cache Configuration
    CACHE_TTL: int = 300  # 5 minutes default cache TTL
    QUESTION_CACHE_TTL: int = 3600  # 1 hour for questions
    SESSION_CACHE_TTL: int = 1800  # 30 minutes for sessions
    
    # Rate Limiting - More permissive for development
    RATE_LIMIT_ENABLED: bool = False  # Disable for development
    DEFAULT_RATE_LIMIT: int = 1000  # requests per minute
    AUTH_RATE_LIMIT: int = 100  # auth requests per minute
    
    # Email Configuration
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", "")
    MAIL_FROM: str = os.getenv("MAIL_FROM", "")
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_TLS: bool = True
    MAIL_SSL: bool = False
    
    # File Upload
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "uploads"
    
    # Performance Settings
    MAX_WORKERS: int = 4
    WORKER_TIMEOUT: int = 30
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Session Management
    SESSION_CLEANUP_INTERVAL: int = 3600  # 1 hour
    MAX_ACTIVE_SESSIONS_PER_USER: int = 5
    
    # AI Service Timeouts
    GEMINI_TIMEOUT: int = 30
    GEMINI_MAX_RETRIES: int = 3
    
    @validator('ALLOWED_HOSTS', pre=True)
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(',')]
        return v
    
    @validator('DEBUG', pre=True)
    def parse_debug(cls, v):
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'on')
        return v

    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Validate critical settings
if not settings.SECRET_KEY:
    raise ValueError("SECRET_KEY must be set")

if not settings.DATABASE_URL:
    raise ValueError("DATABASE_URL must be set")