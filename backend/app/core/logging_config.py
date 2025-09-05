"""
Centralized logging configuration
"""
import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Dict, Any

from app.core.config import settings


class ColoredFormatter(logging.Formatter):
    """Colored log formatter for console output"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        if hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)


def setup_logging():
    """Configure application logging"""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for all logs
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(settings.LOG_FORMAT)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)
    
    # Performance log handler
    perf_handler = logging.handlers.RotatingFileHandler(
        log_dir / "performance.log",
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3
    )
    perf_handler.setLevel(logging.INFO)
    perf_formatter = logging.Formatter(
        '%(asctime)s - PERF - %(message)s'
    )
    perf_handler.setFormatter(perf_formatter)
    
    # Create performance logger
    perf_logger = logging.getLogger("performance")
    perf_logger.addHandler(perf_handler)
    perf_logger.setLevel(logging.INFO)
    perf_logger.propagate = False
    
    # Configure specific loggers
    configure_logger_levels()
    
    logging.info("Logging system initialized")


def configure_logger_levels():
    """Configure specific logger levels"""
    logger_configs = {
        "sqlalchemy.engine": logging.WARNING,
        "sqlalchemy.pool": logging.WARNING,
        "uvicorn.access": logging.WARNING,
        "httpx": logging.WARNING,
        "urllib3": logging.WARNING,
    }
    
    for logger_name, level in logger_configs.items():
        logging.getLogger(logger_name).setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance"""
    return logging.getLogger(name)


def log_performance(operation: str, duration: float, metadata: Dict[str, Any] = None):
    """Log performance metrics"""
    perf_logger = logging.getLogger("performance")
    metadata_str = f" | {metadata}" if metadata else ""
    perf_logger.info(f"{operation} | {duration:.3f}s{metadata_str}")


from starlette.middleware.base import BaseHTTPMiddleware

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging"""
    
    def __init__(self, app):
        super().__init__(app)
        self.logger = get_logger("middleware")
    
    async def dispatch(self, request, call_next):
        import time
        start_time = time.time()
        
        # Log request
        self.logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Log response
            self.logger.info(
                f"Response: {response.status_code} "
                f"in {duration:.3f}s"
            )
            
            # Log performance for slow requests
            if duration > 1.0:
                log_performance(
                    f"SLOW_REQUEST_{request.method}_{request.url.path}",
                    duration,
                    {"status": response.status_code}
                )
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"in {duration:.3f}s - {str(e)}"
            )
            raise