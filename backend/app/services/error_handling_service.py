"""
Comprehensive Error Handling Service
"""
import logging
import traceback
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from functools import wraps

from app.core.exceptions import (
    BaseCustomException, ValidationError, AuthenticationError, 
    NotFoundError, ExternalServiceError, DatabaseError,
    error_tracker, graceful_degradation
)

logger = logging.getLogger(__name__)


class ErrorHandlingService:
    """Service for comprehensive error handling and recovery"""
    
    def __init__(self):
        self.retry_configs = {
            "database": {"max_retries": 3, "delay": 1, "backoff": 2},
            "external_api": {"max_retries": 2, "delay": 2, "backoff": 1.5},
            "file_operation": {"max_retries": 2, "delay": 0.5, "backoff": 1}
        }
        self.circuit_breakers = {}
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle any error and return structured response"""
        try:
            # Convert to custom exception if needed
            if not isinstance(error, BaseCustomException):
                custom_error = self._convert_to_custom_exception(error, context)
            else:
                custom_error = error
            
            # Track the error
            error_tracker.track_error(custom_error, context)
            
            # Log the error
            self._log_error(custom_error, context)
            
            # Get recovery suggestions
            recovery_suggestions = error_tracker.get_recovery_suggestions(custom_error.error_code)
            
            # Return structured error response
            return {
                "error": True,
                "error_code": custom_error.error_code,
                "message": custom_error.message,
                "user_friendly_message": error_tracker._get_user_friendly_message(custom_error),
                "status_code": custom_error.status_code,
                "details": custom_error.details,
                "recovery_suggestions": recovery_suggestions,
                "timestamp": datetime.now().isoformat(),
                "context": context or {}
            }
            
        except Exception as e:
            # Fallback error handling
            logger.critical(f"Error in error handling: {str(e)}")
            return {
                "error": True,
                "error_code": "CRITICAL_ERROR",
                "message": "A critical error occurred in error handling",
                "user_friendly_message": "Something went wrong. Please contact support.",
                "status_code": 500,
                "details": {},
                "recovery_suggestions": ["Contact support immediately"],
                "timestamp": datetime.now().isoformat()
            }
    
    def _convert_to_custom_exception(self, error: Exception, context: Dict[str, Any] = None) -> BaseCustomException:
        """Convert standard exceptions to custom exceptions"""
        error_str = str(error).lower()
        
        # Database errors
        if any(keyword in error_str for keyword in ["database", "sql", "connection", "timeout"]):
            return DatabaseError("database_operation", str(error))
        
        # Validation errors
        elif any(keyword in error_str for keyword in ["validation", "invalid", "required", "format"]):
            return ValidationError(str(error))
        
        # Authentication errors
        elif any(keyword in error_str for keyword in ["auth", "token", "unauthorized", "forbidden"]):
            return AuthenticationError(str(error))
        
        # Not found errors
        elif any(keyword in error_str for keyword in ["not found", "missing", "does not exist"]):
            resource = context.get("resource", "Resource") if context else "Resource"
            return NotFoundError(resource)
        
        # External service errors
        elif any(keyword in error_str for keyword in ["request", "http", "api", "service"]):
            service = context.get("service", "External service") if context else "External service"
            return ExternalServiceError(service, str(error))
        
        # Default to generic error
        else:
            return BaseCustomException(
                message=str(error),
                error_code="INTERNAL_ERROR",
                details={"original_error": type(error).__name__}
            )
    
    def _log_error(self, error: BaseCustomException, context: Dict[str, Any] = None):
        """Log error with appropriate level and context"""
        log_data = {
            "error_code": error.error_code,
            "message": error.message,
            "status_code": error.status_code,
            "details": error.details,
            "context": context or {}
        }
        
        # Log with appropriate level based on error type
        if error.status_code >= 500:
            logger.error(f"Server Error: {log_data}")
        elif error.status_code >= 400:
            logger.warning(f"Client Error: {log_data}")
        else:
            logger.info(f"Error: {log_data}")
    
    def with_retry(self, operation_type: str = "default"):
        """Decorator for retry logic"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                config = self.retry_configs.get(operation_type, {"max_retries": 1, "delay": 1, "backoff": 1})
                max_retries = config["max_retries"]
                delay = config["delay"]
                backoff = config["backoff"]
                
                last_exception = None
                
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        
                        if attempt < max_retries:
                            logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}")
                            import time
                            time.sleep(delay)
                            delay *= backoff
                        else:
                            logger.error(f"All {max_retries + 1} attempts failed for {func.__name__}")
                
                # If all retries failed, raise the last exception
                raise last_exception
            
            return wrapper
        return decorator
    
    def with_circuit_breaker(self, service_name: str, failure_threshold: int = 5, timeout: int = 60):
        """Decorator for circuit breaker pattern"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if service_name not in self.circuit_breakers:
                    self.circuit_breakers[service_name] = {
                        "failures": 0,
                        "last_failure": None,
                        "state": "closed"  # closed, open, half-open
                    }
                
                breaker = self.circuit_breakers[service_name]
                
                # Check if circuit is open
                if breaker["state"] == "open":
                    if breaker["last_failure"] and \
                       datetime.now() - breaker["last_failure"] > timedelta(seconds=timeout):
                        breaker["state"] = "half-open"
                        logger.info(f"Circuit breaker for {service_name} moved to half-open")
                    else:
                        raise ExternalServiceError(
                            service_name, 
                            f"Circuit breaker is open for {service_name}"
                        )
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Reset on success
                    if breaker["state"] == "half-open":
                        breaker["state"] = "closed"
                        breaker["failures"] = 0
                        logger.info(f"Circuit breaker for {service_name} closed")
                    
                    return result
                    
                except Exception as e:
                    breaker["failures"] += 1
                    breaker["last_failure"] = datetime.now()
                    
                    if breaker["failures"] >= failure_threshold:
                        breaker["state"] = "open"
                        logger.error(f"Circuit breaker for {service_name} opened after {failure_threshold} failures")
                    
                    raise e
            
            return wrapper
        return decorator
    
    def with_graceful_degradation(self, feature_name: str, fallback_data: Any = None):
        """Decorator for graceful degradation"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return graceful_degradation.execute_with_fallback(
                    feature_name=feature_name,
                    primary_func=lambda: func(*args, **kwargs),
                    fallback_data=fallback_data
                )
            
            return wrapper
        return decorator
    
    def safe_execute(self, func: Callable, context: Dict[str, Any] = None, 
                    fallback_result: Any = None) -> Dict[str, Any]:
        """Safely execute a function with comprehensive error handling"""
        try:
            result = func()
            return {
                "success": True,
                "data": result,
                "error": None
            }
        except Exception as e:
            error_response = self.handle_error(e, context)
            return {
                "success": False,
                "data": fallback_result,
                "error": error_response
            }
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        stats = error_tracker.get_error_stats()
        
        # Add circuit breaker status
        stats["circuit_breakers"] = {}
        for service, breaker in self.circuit_breakers.items():
            stats["circuit_breakers"][service] = {
                "state": breaker["state"],
                "failures": breaker["failures"],
                "last_failure": breaker["last_failure"].isoformat() if breaker["last_failure"] else None
            }
        
        # Add graceful degradation status
        stats["disabled_features"] = list(graceful_degradation.disabled_features)
        
        return stats
    
    def reset_circuit_breaker(self, service_name: str):
        """Manually reset a circuit breaker"""
        if service_name in self.circuit_breakers:
            self.circuit_breakers[service_name] = {
                "failures": 0,
                "last_failure": None,
                "state": "closed"
            }
            logger.info(f"Circuit breaker for {service_name} manually reset")
    
    def enable_feature(self, feature_name: str):
        """Re-enable a gracefully degraded feature"""
        graceful_degradation.enable_feature(feature_name)
    
    def create_error_context(self, **kwargs) -> Dict[str, Any]:
        """Create error context with common fields"""
        context = {
            "timestamp": datetime.now().isoformat(),
            "service": "interview_coach",
            **kwargs
        }
        return context


# Global error handling service instance
error_service = ErrorHandlingService()


def handle_api_errors(func: Callable):
    """Decorator for API endpoint error handling"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except BaseCustomException as e:
            # Custom exceptions are already properly formatted
            raise e
        except Exception as e:
            # Convert unexpected exceptions
            context = error_service.create_error_context(
                endpoint=func.__name__,
                args=str(args)[:200],  # Limit length
                kwargs=str(kwargs)[:200]
            )
            
            error_response = error_service.handle_error(e, context)
            
            # Convert to HTTP exception
            from fastapi import HTTPException
            raise HTTPException(
                status_code=error_response["status_code"],
                detail={
                    "error": error_response["error_code"],
                    "message": error_response["user_friendly_message"],
                    "details": error_response["details"],
                    "recovery_suggestions": error_response["recovery_suggestions"]
                }
            )
    
    return wrapper


def log_performance(operation_name: str):
    """Decorator for performance logging"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log performance
                perf_logger = logging.getLogger("performance")
                perf_logger.info(f"{operation_name} completed in {duration:.3f}s")
                
                # Log slow operations
                if duration > 2.0:
                    logger.warning(f"Slow operation: {operation_name} took {duration:.3f}s")
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"{operation_name} failed after {duration:.3f}s: {str(e)}")
                raise
        
        return wrapper
    return decorator