"""
Interview Prep AI Coach - Main FastAPI Application
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from app.core.config import settings
from app.core.logging_config import setup_logging, LoggingMiddleware
from app.core.exceptions import BaseCustomException, custom_exception_handler, error_tracker
from app.core.cache import cache_service, session_manager
from app.api.v1.api import api_router
from app.db.database import engine, check_database_health
from app.db import models
from app.core.middleware import (
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware,
    RequestSizeLimitMiddleware
)

# Setup logging first
setup_logging()
logger = logging.getLogger(__name__)

# Create database tables
try:
    models.Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Failed to create database tables: {e}")
    raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Interview Prep AI Coach API...")
    
    # Check database health
    if not check_database_health():
        logger.error("Database health check failed!")
        raise Exception("Database is not accessible")
    
    # Initialize cache service
    logger.info("Cache service initialized")
    
    # Start background tasks
    import asyncio
    from app.core.background_tasks import start_background_tasks
    asyncio.create_task(start_background_tasks())
    
    logger.info("API startup completed successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Interview Prep AI Coach API...")
    
    # Cleanup cache
    cache_service.clear()
    logger.info("Cache cleared")
    
    logger.info("API shutdown completed")

app = FastAPI(
    title="Interview Prep AI Coach API",
    description="AI-powered interview preparation platform with real-time feedback",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
)

# Add custom exception handler
@app.exception_handler(BaseCustomException)
async def handle_custom_exception(request: Request, exc: BaseCustomException):
    error_tracker.track_error(exc, {"path": request.url.path, "method": request.method})
    return await custom_exception_handler(request, exc)

# Add global exception handler
@app.exception_handler(Exception)
async def handle_general_exception(request: Request, exc: Exception):
    from app.services.error_handling_service import error_service
    
    # Create error context
    context = error_service.create_error_context(
        path=request.url.path,
        method=request.method,
        user_agent=request.headers.get("user-agent", ""),
        ip_address=request.client.host if request.client else "unknown"
    )
    
    # Handle the error
    error_response = error_service.handle_error(exc, context)
    
    return JSONResponse(
        status_code=error_response["status_code"],
        content={
            "error": error_response["error_code"],
            "message": error_response["user_friendly_message"],
            "details": error_response["details"] if settings.DEBUG else {},
            "recovery_suggestions": error_response["recovery_suggestions"],
            "timestamp": error_response["timestamp"]
        }
    )

# Add middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware, max_size=settings.MAX_FILE_SIZE)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "Interview Prep AI Coach API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    try:
        # Basic database health check
        db_healthy = check_database_health()
        
        return {
            "status": "healthy" if db_healthy else "unhealthy",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "database": "healthy" if db_healthy else "unhealthy"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT,
            "error": str(e)
        }