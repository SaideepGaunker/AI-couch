"""
Custom exceptions and error handling
"""
from typing import Any, Dict, Optional, List
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)


class BaseCustomException(Exception):
    """Base class for custom exceptions"""
    
    def __init__(
        self,
        message: str,
        error_code: str = None,
        details: Dict[str, Any] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(BaseCustomException):
    """Validation error"""
    
    def __init__(self, message: str, field: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details={"field": field, **(details or {})},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )


class AuthenticationError(BaseCustomException):
    """Authentication error"""
    
    def __init__(self, message: str = "Authentication failed", details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            details=details,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class AuthorizationError(BaseCustomException):
    """Authorization error"""
    
    def __init__(self, message: str = "Access denied", details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            details=details,
            status_code=status.HTTP_403_FORBIDDEN
        )


class NotFoundError(BaseCustomException):
    """Resource not found error"""
    
    def __init__(self, resource: str, identifier: Any = None, details: Dict[str, Any] = None):
        message = f"{resource} not found"
        if identifier:
            message += f" (ID: {identifier})"
        
        super().__init__(
            message=message,
            error_code="NOT_FOUND_ERROR",
            details={"resource": resource, "identifier": identifier, **(details or {})},
            status_code=status.HTTP_404_NOT_FOUND
        )


class ConflictError(BaseCustomException):
    """Resource conflict error"""
    
    def __init__(self, message: str, resource: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="CONFLICT_ERROR",
            details={"resource": resource, **(details or {})},
            status_code=status.HTTP_409_CONFLICT
        )


class RateLimitError(BaseCustomException):
    """Rate limit exceeded error"""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = None):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            details={"retry_after": retry_after},
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )


class ExternalServiceError(BaseCustomException):
    """External service error"""
    
    def __init__(self, service: str, message: str = None, details: Dict[str, Any] = None):
        message = message or f"{service} service unavailable"
        super().__init__(
            message=message,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service, **(details or {})},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


class DatabaseError(BaseCustomException):
    """Database operation error"""
    
    def __init__(self, operation: str, message: str = None, details: Dict[str, Any] = None):
        message = message or f"Database {operation} failed"
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            details={"operation": operation, **(details or {})},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class BusinessLogicError(BaseCustomException):
    """Business logic error"""
    
    def __init__(self, message: str, rule: str = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="BUSINESS_LOGIC_ERROR",
            details={"rule": rule, **(details or {})},
            status_code=status.HTTP_400_BAD_REQUEST
        )


class SessionError(BaseCustomException):
    """Session-related error"""
    
    def __init__(self, message: str, session_id: int = None, details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="SESSION_ERROR",
            details={"session_id": session_id, **(details or {})},
            status_code=status.HTTP_400_BAD_REQUEST
        )


def handle_database_error(e: Exception, operation: str) -> DatabaseError:
    """Convert database exceptions to custom errors"""
    logger.error(f"Database error during {operation}: {str(e)}")
    
    error_message = str(e).lower()
    
    if "duplicate entry" in error_message or "unique constraint" in error_message:
        return ConflictError(f"Resource already exists", details={"operation": operation})
    elif "foreign key constraint" in error_message:
        return ValidationError(f"Invalid reference in {operation}")
    elif "connection" in error_message:
        return DatabaseError(operation, "Database connection failed")
    else:
        return DatabaseError(operation, str(e))


def handle_external_service_error(e: Exception, service: str) -> ExternalServiceError:
    """Convert external service exceptions to custom errors"""
    logger.error(f"External service error ({service}): {str(e)}")
    
    error_message = str(e).lower()
    
    if "timeout" in error_message:
        return ExternalServiceError(service, f"{service} request timed out")
    elif "connection" in error_message:
        return ExternalServiceError(service, f"Cannot connect to {service}")
    elif "unauthorized" in error_message or "403" in error_message:
        return ExternalServiceError(service, f"{service} authentication failed")
    elif "rate limit" in error_message or "429" in error_message:
        return RateLimitError(f"{service} rate limit exceeded")
    else:
        return ExternalServiceError(service, str(e))


async def custom_exception_handler(request, exc: BaseCustomException):
    """Custom exception handler for FastAPI"""
    logger.error(
        f"Custom exception: {exc.error_code} - {exc.message} "
        f"(Path: {request.url.path}, Details: {exc.details})"
    )
    
    return HTTPException(
        status_code=exc.status_code,
        detail={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details
        }
    )


def safe_execute(func, *args, **kwargs):
    """Safely execute a function with error handling"""
    try:
        return func(*args, **kwargs)
    except BaseCustomException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
        raise BaseCustomException(
            message="An unexpected error occurred",
            error_code="INTERNAL_ERROR",
            details={"function": func.__name__, "error": str(e)}
        )


class ErrorTracker:
    """Track and analyze errors"""
    
    def __init__(self):
        self.error_counts = {}
        self.recent_errors = []
        self.error_patterns = {}
    
    def track_error(self, error: BaseCustomException, context: Dict[str, Any] = None):
        """Track an error occurrence"""
        import datetime
        
        error_key = f"{error.error_code}:{error.message}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        timestamp = datetime.datetime.now().isoformat()
        error_entry = {
            "timestamp": timestamp,
            "error_code": error.error_code,
            "message": error.message,
            "status_code": error.status_code,
            "context": context or {},
            "user_friendly_message": self._get_user_friendly_message(error)
        }
        
        self.recent_errors.append(error_entry)
        
        # Track error patterns
        self._track_error_pattern(error, context)
        
        # Keep only last 100 errors
        if len(self.recent_errors) > 100:
            self.recent_errors = self.recent_errors[-100:]
    
    def _track_error_pattern(self, error: BaseCustomException, context: Dict[str, Any] = None):
        """Track error patterns for analysis"""
        pattern_key = error.error_code
        if pattern_key not in self.error_patterns:
            self.error_patterns[pattern_key] = {
                "count": 0,
                "first_seen": None,
                "last_seen": None,
                "common_contexts": {}
            }
        
        import datetime
        now = datetime.datetime.now().isoformat()
        
        pattern = self.error_patterns[pattern_key]
        pattern["count"] += 1
        pattern["last_seen"] = now
        
        if pattern["first_seen"] is None:
            pattern["first_seen"] = now
        
        # Track common context patterns
        if context:
            for key, value in context.items():
                if key not in pattern["common_contexts"]:
                    pattern["common_contexts"][key] = {}
                
                str_value = str(value)
                if str_value not in pattern["common_contexts"][key]:
                    pattern["common_contexts"][key][str_value] = 0
                pattern["common_contexts"][key][str_value] += 1
    
    def _get_user_friendly_message(self, error: BaseCustomException) -> str:
        """Generate user-friendly error messages"""
        user_friendly_messages = {
            "VALIDATION_ERROR": "Please check your input and try again.",
            "AUTHENTICATION_ERROR": "Please log in to continue.",
            "AUTHORIZATION_ERROR": "You don't have permission to perform this action.",
            "NOT_FOUND_ERROR": "The requested resource was not found.",
            "CONFLICT_ERROR": "This action conflicts with existing data.",
            "RATE_LIMIT_ERROR": "Too many requests. Please wait before trying again.",
            "EXTERNAL_SERVICE_ERROR": "A service is temporarily unavailable. Please try again later.",
            "DATABASE_ERROR": "A database error occurred. Please try again.",
            "BUSINESS_LOGIC_ERROR": "This action cannot be completed due to business rules.",
            "SESSION_ERROR": "Your session has expired or is invalid. Please refresh and try again.",
            "INTERNAL_ERROR": "An unexpected error occurred. Please try again or contact support."
        }
        
        return user_friendly_messages.get(error.error_code, "An error occurred. Please try again.")
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            "total_errors": sum(self.error_counts.values()),
            "unique_errors": len(self.error_counts),
            "top_errors": sorted(
                self.error_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            "recent_errors": self.recent_errors[-10:],
            "error_patterns": self.error_patterns
        }
    
    def get_recovery_suggestions(self, error_code: str) -> List[str]:
        """Get recovery suggestions for specific error types"""
        recovery_suggestions = {
            "VALIDATION_ERROR": [
                "Check that all required fields are filled",
                "Verify data formats match requirements",
                "Review field length limits"
            ],
            "AUTHENTICATION_ERROR": [
                "Log out and log back in",
                "Clear browser cache and cookies",
                "Check if your account is locked"
            ],
            "AUTHORIZATION_ERROR": [
                "Contact your administrator for access",
                "Verify you're using the correct account",
                "Check if your permissions have changed"
            ],
            "NOT_FOUND_ERROR": [
                "Verify the resource still exists",
                "Check the URL or ID is correct",
                "Refresh the page and try again"
            ],
            "EXTERNAL_SERVICE_ERROR": [
                "Wait a few minutes and try again",
                "Check your internet connection",
                "Try using a different browser"
            ],
            "SESSION_ERROR": [
                "Refresh the page",
                "Log out and log back in",
                "Clear browser cache"
            ]
        }
        
        return recovery_suggestions.get(error_code, [
            "Refresh the page and try again",
            "Contact support if the problem persists"
        ])


class GracefulDegradationManager:
    """Manage graceful degradation for non-critical features"""
    
    def __init__(self):
        self.disabled_features = set()
        self.fallback_data = {}
    
    def disable_feature(self, feature_name: str, reason: str = None):
        """Disable a non-critical feature"""
        self.disabled_features.add(feature_name)
        logger.warning(f"Feature '{feature_name}' disabled: {reason}")
    
    def enable_feature(self, feature_name: str):
        """Re-enable a previously disabled feature"""
        self.disabled_features.discard(feature_name)
        logger.info(f"Feature '{feature_name}' re-enabled")
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled"""
        return feature_name not in self.disabled_features
    
    def set_fallback_data(self, feature_name: str, data: Any):
        """Set fallback data for a feature"""
        self.fallback_data[feature_name] = data
    
    def get_fallback_data(self, feature_name: str) -> Any:
        """Get fallback data for a feature"""
        return self.fallback_data.get(feature_name)
    
    def execute_with_fallback(self, feature_name: str, primary_func, fallback_func=None, fallback_data=None):
        """Execute function with fallback handling"""
        if not self.is_feature_enabled(feature_name):
            if fallback_func:
                return fallback_func()
            elif fallback_data is not None:
                return fallback_data
            else:
                return self.get_fallback_data(feature_name)
        
        try:
            return primary_func()
        except Exception as e:
            logger.error(f"Feature '{feature_name}' failed: {str(e)}")
            self.disable_feature(feature_name, str(e))
            
            if fallback_func:
                return fallback_func()
            elif fallback_data is not None:
                return fallback_data
            else:
                return self.get_fallback_data(feature_name)


# Global instances
error_tracker = ErrorTracker()
graceful_degradation = GracefulDegradationManager()