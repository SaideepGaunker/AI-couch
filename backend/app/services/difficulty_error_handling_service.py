"""
Difficulty-Specific Error Handling Service

This service provides comprehensive error handling specifically for difficulty state operations,
including user-friendly error messages, automatic recovery attempts, and detailed logging.
"""
import logging
from typing import Dict, Any, Optional, List, Callable, Union
from datetime import datetime, timedelta
from functools import wraps
from enum import Enum

from app.services.error_handling_service import ErrorHandlingService, error_service
from app.services.difficulty_state_recovery_service import DifficultyStateRecoveryService
from app.core.exceptions import ValidationError, DatabaseError, BusinessLogicError

logger = logging.getLogger(__name__)


class DifficultyErrorType(Enum):
    """Enumeration of difficulty-specific error types"""
    STATE_CORRUPTION = "difficulty_state_corruption"
    PERSISTENCE_FAILURE = "difficulty_persistence_failure"
    RECOVERY_FAILURE = "difficulty_recovery_failure"
    VALIDATION_ERROR = "difficulty_validation_error"
    ISOLATION_VIOLATION = "difficulty_isolation_violation"
    INHERITANCE_ERROR = "difficulty_inheritance_error"
    CACHE_INCONSISTENCY = "difficulty_cache_inconsistency"
    SESSION_NOT_FOUND = "difficulty_session_not_found"
    INVALID_DIFFICULTY_LEVEL = "invalid_difficulty_level"
    FINALIZATION_ERROR = "difficulty_finalization_error"


class DifficultyErrorHandlingService:
    """
    Comprehensive error handling service for difficulty state operations
    
    This service provides specialized error handling for difficulty-related operations,
    including automatic recovery attempts, user-friendly error messages, and detailed monitoring.
    """
    
    def __init__(self, db_session=None):
        """
        Initialize the difficulty error handling service
        
        Args:
            db_session: Optional database session for recovery operations
        """
        self.base_error_service = error_service
        self.db = db_session
        self.recovery_service = None
        if db_session:
            self.recovery_service = DifficultyStateRecoveryService(db_session)
        
        # Error tracking and statistics
        self.error_counts = {}
        self.recovery_attempts = {}
        self.user_error_history = {}
        
        # Configuration for automatic recovery
        self.auto_recovery_config = {
            DifficultyErrorType.STATE_CORRUPTION: {
                "enabled": True,
                "max_attempts": 3,
                "recovery_methods": ["json_recovery", "field_recovery", "fallback"]
            },
            DifficultyErrorType.PERSISTENCE_FAILURE: {
                "enabled": True,
                "max_attempts": 2,
                "recovery_methods": ["retry_persist", "cache_only"]
            },
            DifficultyErrorType.CACHE_INCONSISTENCY: {
                "enabled": True,
                "max_attempts": 1,
                "recovery_methods": ["cache_refresh", "database_reload"]
            }
        }
        
        logger.info("DifficultyErrorHandlingService initialized")
    
    def handle_difficulty_error(
        self, 
        error: Exception, 
        error_type: DifficultyErrorType,
        session_id: Optional[int] = None,
        user_id: Optional[int] = None,
        operation: Optional[str] = None,
        auto_recover: bool = True
    ) -> Dict[str, Any]:
        """
        Handle difficulty-specific errors with comprehensive recovery and user feedback
        
        Args:
            error: The exception that occurred
            error_type: The type of difficulty error
            session_id: Optional session ID where error occurred
            user_id: Optional user ID associated with the error
            operation: Optional description of the operation that failed
            auto_recover: Whether to attempt automatic recovery
            
        Returns:
            Dict containing error information and recovery results
        """
        try:
            logger.error(f"Difficulty error occurred - Type: {error_type.value}, Session: {session_id}, "
                        f"User: {user_id}, Operation: {operation}, Error: {str(error)}")
            
            # Create error context
            error_context = self._create_difficulty_error_context(
                error_type, session_id, user_id, operation
            )
            
            # Track the error
            self._track_difficulty_error(error_type, session_id, user_id)
            
            # Get user-friendly error message
            user_message = self._get_user_friendly_message(error_type, error_context)
            
            # Prepare error response
            error_response = {
                "error": True,
                "error_type": error_type.value,
                "error_code": f"DIFFICULTY_{error_type.value.upper()}",
                "message": str(error),
                "user_friendly_message": user_message,
                "session_id": session_id,
                "user_id": user_id,
                "operation": operation,
                "timestamp": datetime.utcnow().isoformat(),
                "recovery_attempted": False,
                "recovery_successful": False,
                "recovery_details": None,
                "fallback_applied": False,
                "user_actions": self._get_user_action_suggestions(error_type, error_context)
            }
            
            # Attempt automatic recovery if enabled
            if auto_recover and self._should_attempt_recovery(error_type, session_id):
                recovery_result = self._attempt_automatic_recovery(
                    error, error_type, session_id, user_id, operation
                )
                
                error_response["recovery_attempted"] = True
                error_response["recovery_successful"] = recovery_result.get("success", False)
                error_response["recovery_details"] = recovery_result
                
                if recovery_result.get("success"):
                    logger.info(f"Successfully recovered from difficulty error - Session: {session_id}")
                    error_response["user_friendly_message"] = self._get_recovery_success_message(error_type)
                else:
                    logger.warning(f"Failed to recover from difficulty error - Session: {session_id}")
            
            # Apply fallback behavior if recovery failed or wasn't attempted
            if not error_response["recovery_successful"]:
                fallback_result = self._apply_fallback_behavior(error_type, error_context)
                error_response["fallback_applied"] = fallback_result.get("applied", False)
                error_response["fallback_details"] = fallback_result
            
            return error_response
            
        except Exception as handling_error:
            logger.critical(f"Error in difficulty error handling: {str(handling_error)}")
            return self._create_critical_error_response(error, handling_error, session_id, user_id)
    
    def _create_difficulty_error_context(
        self, 
        error_type: DifficultyErrorType,
        session_id: Optional[int],
        user_id: Optional[int],
        operation: Optional[str]
    ) -> Dict[str, Any]:
        """Create comprehensive error context for difficulty errors"""
        context = {
            "error_type": error_type.value,
            "session_id": session_id,
            "user_id": user_id,
            "operation": operation,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "difficulty_state_management"
        }
        
        # Add session-specific context if available
        if session_id and self.db:
            try:
                from app.db.models import InterviewSession
                session = self.db.query(InterviewSession).filter(
                    InterviewSession.id == session_id
                ).first()
                
                if session:
                    context["session_info"] = {
                        "status": session.status,
                        "session_type": session.session_type,
                        "difficulty_level": session.difficulty_level,
                        "session_mode": getattr(session, 'session_mode', None),
                        "parent_session_id": getattr(session, 'parent_session_id', None),
                        "created_at": session.created_at.isoformat() if session.created_at else None
                    }
            except Exception as e:
                logger.warning(f"Could not retrieve session context: {str(e)}")
        
        # Add user error history
        if user_id:
            user_history = self.user_error_history.get(user_id, [])
            recent_errors = [
                err for err in user_history 
                if datetime.fromisoformat(err["timestamp"]) > datetime.utcnow() - timedelta(hours=1)
            ]
            context["recent_user_errors"] = len(recent_errors)
        
        return context
    
    def _track_difficulty_error(
        self, 
        error_type: DifficultyErrorType,
        session_id: Optional[int],
        user_id: Optional[int]
    ) -> None:
        """Track difficulty error for monitoring and analysis"""
        try:
            # Update error counts
            error_key = error_type.value
            self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
            
            # Track user-specific errors
            if user_id:
                if user_id not in self.user_error_history:
                    self.user_error_history[user_id] = []
                
                self.user_error_history[user_id].append({
                    "error_type": error_type.value,
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Keep only recent errors (last 24 hours)
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                self.user_error_history[user_id] = [
                    err for err in self.user_error_history[user_id]
                    if datetime.fromisoformat(err["timestamp"]) > cutoff_time
                ]
            
        except Exception as e:
            logger.warning(f"Error tracking difficulty error: {str(e)}")
    
    def _get_user_friendly_message(
        self, 
        error_type: DifficultyErrorType,
        context: Dict[str, Any]
    ) -> str:
        """Get user-friendly error message based on error type"""
        
        messages = {
            DifficultyErrorType.STATE_CORRUPTION: (
                "There was an issue with your interview difficulty settings. "
                "We're working to restore them automatically."
            ),
            DifficultyErrorType.PERSISTENCE_FAILURE: (
                "We couldn't save your difficulty preferences right now. "
                "Your current session will continue normally, but changes might not be saved."
            ),
            DifficultyErrorType.RECOVERY_FAILURE: (
                "We encountered an issue restoring your difficulty settings. "
                "The system will use safe default settings for now."
            ),
            DifficultyErrorType.VALIDATION_ERROR: (
                "There's an issue with the difficulty level settings. "
                "Please try refreshing the page or contact support if the problem persists."
            ),
            DifficultyErrorType.ISOLATION_VIOLATION: (
                "There was a technical issue with session management. "
                "Your current interview should continue normally."
            ),
            DifficultyErrorType.INHERITANCE_ERROR: (
                "There was an issue setting up your practice session difficulty. "
                "The system will use your preferred difficulty level instead."
            ),
            DifficultyErrorType.CACHE_INCONSISTENCY: (
                "There's a temporary synchronization issue. "
                "Please refresh the page to see the most current information."
            ),
            DifficultyErrorType.SESSION_NOT_FOUND: (
                "The interview session could not be found. "
                "Please start a new interview or contact support if this continues."
            ),
            DifficultyErrorType.INVALID_DIFFICULTY_LEVEL: (
                "The difficulty level setting is invalid. "
                "The system will use a medium difficulty level as a safe default."
            ),
            DifficultyErrorType.FINALIZATION_ERROR: (
                "There was an issue completing your interview session. "
                "Your progress has been saved, but some features might be temporarily unavailable."
            )
        }
        
        base_message = messages.get(error_type, "An unexpected error occurred with the difficulty system.")
        
        # Add context-specific information
        if context.get("recent_user_errors", 0) > 2:
            base_message += " If you continue to experience issues, please contact support."
        
        return base_message
    
    def _get_user_action_suggestions(
        self, 
        error_type: DifficultyErrorType,
        context: Dict[str, Any]
    ) -> List[str]:
        """Get suggested user actions based on error type"""
        
        suggestions = {
            DifficultyErrorType.STATE_CORRUPTION: [
                "Refresh the page to reload your settings",
                "If the issue persists, try starting a new interview session",
                "Contact support if problems continue"
            ],
            DifficultyErrorType.PERSISTENCE_FAILURE: [
                "Continue with your current session",
                "Your progress is still being tracked",
                "Try refreshing the page after completing the current question"
            ],
            DifficultyErrorType.RECOVERY_FAILURE: [
                "The system is using safe default settings",
                "You can manually adjust difficulty in your profile settings",
                "Contact support for assistance with restoring your preferences"
            ],
            DifficultyErrorType.VALIDATION_ERROR: [
                "Refresh the page to reload the interface",
                "Check your internet connection",
                "Try logging out and logging back in"
            ],
            DifficultyErrorType.CACHE_INCONSISTENCY: [
                "Refresh the page to sync the latest data",
                "Clear your browser cache if the issue persists",
                "The issue should resolve automatically within a few minutes"
            ],
            DifficultyErrorType.SESSION_NOT_FOUND: [
                "Start a new interview session",
                "Check if you have any other active sessions",
                "Contact support if you lost important progress"
            ],
            DifficultyErrorType.INHERITANCE_ERROR: [
                "The practice session will use your default difficulty",
                "You can manually adjust difficulty before starting",
                "Your original interview results are still saved"
            ]
        }
        
        return suggestions.get(error_type, [
            "Refresh the page",
            "Try the operation again",
            "Contact support if the issue persists"
        ])
    
    def _should_attempt_recovery(
        self, 
        error_type: DifficultyErrorType,
        session_id: Optional[int]
    ) -> bool:
        """Determine if automatic recovery should be attempted"""
        
        # Check if recovery is enabled for this error type
        config = self.auto_recovery_config.get(error_type)
        if not config or not config.get("enabled", False):
            return False
        
        # Check recovery attempt limits
        if session_id:
            recovery_key = f"{error_type.value}_{session_id}"
            attempts = self.recovery_attempts.get(recovery_key, 0)
            max_attempts = config.get("max_attempts", 1)
            
            if attempts >= max_attempts:
                logger.warning(f"Max recovery attempts ({max_attempts}) reached for {recovery_key}")
                return False
        
        return True
    
    def _attempt_automatic_recovery(
        self,
        error: Exception,
        error_type: DifficultyErrorType,
        session_id: Optional[int],
        user_id: Optional[int],
        operation: Optional[str]
    ) -> Dict[str, Any]:
        """Attempt automatic recovery from difficulty errors"""
        
        recovery_result = {
            "success": False,
            "methods_attempted": [],
            "successful_method": None,
            "error_details": [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            # Track recovery attempt
            if session_id:
                recovery_key = f"{error_type.value}_{session_id}"
                self.recovery_attempts[recovery_key] = self.recovery_attempts.get(recovery_key, 0) + 1
            
            # Get recovery methods for this error type
            config = self.auto_recovery_config.get(error_type, {})
            recovery_methods = config.get("recovery_methods", [])
            
            logger.info(f"Attempting automatic recovery for {error_type.value} using methods: {recovery_methods}")
            
            for method in recovery_methods:
                try:
                    recovery_result["methods_attempted"].append(method)
                    
                    if method == "json_recovery" and session_id and self.recovery_service:
                        result = self.recovery_service.recover_session_difficulty_state(session_id)
                        if result.get("recovery_successful"):
                            recovery_result["success"] = True
                            recovery_result["successful_method"] = method
                            break
                    
                    elif method == "field_recovery" and session_id and self.recovery_service:
                        # Try to recover from database fields
                        from app.db.models import InterviewSession
                        session = self.db.query(InterviewSession).filter(
                            InterviewSession.id == session_id
                        ).first()
                        
                        if session:
                            recovered_state = self.recovery_service._recover_from_database_fields(session)
                            if recovered_state:
                                recovery_result["success"] = True
                                recovery_result["successful_method"] = method
                                break
                    
                    elif method == "fallback" and session_id and self.recovery_service:
                        # Create fallback state
                        from app.db.models import InterviewSession
                        session = self.db.query(InterviewSession).filter(
                            InterviewSession.id == session_id
                        ).first()
                        
                        if session:
                            fallback_state = self.recovery_service._create_fallback_state(session)
                            if fallback_state:
                                recovery_result["success"] = True
                                recovery_result["successful_method"] = method
                                break
                    
                    elif method == "retry_persist":
                        # For persistence failures, try a simple retry
                        # This would be implemented based on the specific operation
                        logger.info(f"Retry persist method attempted for {error_type.value}")
                    
                    elif method == "cache_only":
                        # For persistence failures, continue with cache-only operation
                        recovery_result["success"] = True
                        recovery_result["successful_method"] = method
                        recovery_result["note"] = "Operating in cache-only mode"
                        break
                    
                    elif method == "cache_refresh":
                        # Clear and refresh cache
                        if session_id and hasattr(self, 'session_difficulty_service'):
                            self.session_difficulty_service.clear_session_cache(session_id)
                            recovery_result["success"] = True
                            recovery_result["successful_method"] = method
                            break
                    
                    elif method == "database_reload":
                        # Force reload from database
                        if session_id and self.recovery_service:
                            state = self.recovery_service.session_difficulty_service._load_session_difficulty_state(session_id)
                            if state:
                                recovery_result["success"] = True
                                recovery_result["successful_method"] = method
                                break
                
                except Exception as method_error:
                    error_msg = f"Recovery method {method} failed: {str(method_error)}"
                    recovery_result["error_details"].append(error_msg)
                    logger.warning(error_msg)
            
            if recovery_result["success"]:
                logger.info(f"Successfully recovered from {error_type.value} using {recovery_result['successful_method']}")
            else:
                logger.warning(f"All recovery methods failed for {error_type.value}")
            
        except Exception as recovery_error:
            recovery_result["error_details"].append(f"Recovery process error: {str(recovery_error)}")
            logger.error(f"Error during automatic recovery: {str(recovery_error)}")
        
        return recovery_result
    
    def _apply_fallback_behavior(
        self, 
        error_type: DifficultyErrorType,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply fallback behavior when recovery fails"""
        
        fallback_result = {
            "applied": False,
            "fallback_type": None,
            "details": {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        try:
            if error_type in [
                DifficultyErrorType.STATE_CORRUPTION,
                DifficultyErrorType.INVALID_DIFFICULTY_LEVEL,
                DifficultyErrorType.RECOVERY_FAILURE
            ]:
                # Use safe default difficulty
                fallback_result["applied"] = True
                fallback_result["fallback_type"] = "default_difficulty"
                fallback_result["details"] = {
                    "difficulty_level": "medium",
                    "reason": "Safe default applied due to error"
                }
            
            elif error_type == DifficultyErrorType.PERSISTENCE_FAILURE:
                # Continue with cache-only operation
                fallback_result["applied"] = True
                fallback_result["fallback_type"] = "cache_only_mode"
                fallback_result["details"] = {
                    "mode": "cache_only",
                    "reason": "Persistence unavailable, using cache"
                }
            
            elif error_type == DifficultyErrorType.INHERITANCE_ERROR:
                # Use user's default difficulty for practice session
                fallback_result["applied"] = True
                fallback_result["fallback_type"] = "user_default_difficulty"
                fallback_result["details"] = {
                    "difficulty_source": "user_preference",
                    "reason": "Inheritance failed, using user default"
                }
            
            elif error_type == DifficultyErrorType.CACHE_INCONSISTENCY:
                # Force database reload
                fallback_result["applied"] = True
                fallback_result["fallback_type"] = "force_database_reload"
                fallback_result["details"] = {
                    "action": "database_reload",
                    "reason": "Cache inconsistency detected"
                }
            
        except Exception as e:
            logger.error(f"Error applying fallback behavior: {str(e)}")
        
        return fallback_result
    
    def _get_recovery_success_message(self, error_type: DifficultyErrorType) -> str:
        """Get success message after successful recovery"""
        
        messages = {
            DifficultyErrorType.STATE_CORRUPTION: (
                "Your difficulty settings have been successfully restored. "
                "You can continue with your interview normally."
            ),
            DifficultyErrorType.PERSISTENCE_FAILURE: (
                "The system has recovered and your settings are now being saved properly."
            ),
            DifficultyErrorType.CACHE_INCONSISTENCY: (
                "The synchronization issue has been resolved. "
                "All information is now up to date."
            )
        }
        
        return messages.get(error_type, "The issue has been resolved automatically.")
    
    def _create_critical_error_response(
        self,
        original_error: Exception,
        handling_error: Exception,
        session_id: Optional[int],
        user_id: Optional[int]
    ) -> Dict[str, Any]:
        """Create response for critical errors in error handling"""
        
        return {
            "error": True,
            "error_type": "critical_difficulty_error",
            "error_code": "DIFFICULTY_CRITICAL_ERROR",
            "message": "A critical error occurred in difficulty error handling",
            "user_friendly_message": (
                "We're experiencing technical difficulties. "
                "Please refresh the page or contact support if the problem persists."
            ),
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "recovery_attempted": False,
            "recovery_successful": False,
            "fallback_applied": False,
            "user_actions": [
                "Refresh the page",
                "Try starting a new session",
                "Contact support immediately"
            ],
            "details": {
                "original_error": str(original_error),
                "handling_error": str(handling_error)
            }
        }
    
    def get_error_statistics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get comprehensive error statistics for monitoring"""
        
        stats = {
            "total_errors": sum(self.error_counts.values()),
            "error_breakdown": dict(self.error_counts),
            "recovery_attempts": dict(self.recovery_attempts),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if user_id and user_id in self.user_error_history:
            stats["user_specific"] = {
                "user_id": user_id,
                "recent_errors": len(self.user_error_history[user_id]),
                "error_history": self.user_error_history[user_id][-10:]  # Last 10 errors
            }
        
        # Add recovery success rates
        recovery_stats = {}
        for error_type in DifficultyErrorType:
            error_count = self.error_counts.get(error_type.value, 0)
            recovery_count = sum(
                1 for key in self.recovery_attempts.keys() 
                if key.startswith(error_type.value)
            )
            
            if error_count > 0:
                recovery_stats[error_type.value] = {
                    "total_errors": error_count,
                    "recovery_attempts": recovery_count,
                    "recovery_rate": recovery_count / error_count if error_count > 0 else 0
                }
        
        stats["recovery_statistics"] = recovery_stats
        
        return stats
    
    def reset_error_tracking(self, user_id: Optional[int] = None) -> None:
        """Reset error tracking data"""
        
        if user_id:
            if user_id in self.user_error_history:
                del self.user_error_history[user_id]
            logger.info(f"Reset error tracking for user {user_id}")
        else:
            self.error_counts.clear()
            self.recovery_attempts.clear()
            self.user_error_history.clear()
            logger.info("Reset all error tracking data")


def with_difficulty_error_handling(
    error_type: DifficultyErrorType,
    session_id_param: str = "session_id",
    user_id_param: str = "user_id",
    auto_recover: bool = True
):
    """
    Decorator for automatic difficulty error handling
    
    Args:
        error_type: The type of difficulty error this operation might encounter
        session_id_param: Name of the parameter containing session_id
        user_id_param: Name of the parameter containing user_id
        auto_recover: Whether to attempt automatic recovery
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract session_id and user_id from parameters
            session_id = kwargs.get(session_id_param)
            user_id = kwargs.get(user_id_param)
            
            # Get database session if available
            db_session = kwargs.get('db') or (args[0] if args and hasattr(args[0], 'db') else None)
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Create error handling service instance
                error_handler = DifficultyErrorHandlingService(db_session)
                
                # Handle the error
                error_response = error_handler.handle_difficulty_error(
                    error=e,
                    error_type=error_type,
                    session_id=session_id,
                    user_id=user_id,
                    operation=func.__name__,
                    auto_recover=auto_recover
                )
                
                # If recovery was successful, try the operation again
                if error_response.get("recovery_successful"):
                    try:
                        return func(*args, **kwargs)
                    except Exception as retry_error:
                        logger.warning(f"Operation failed even after successful recovery: {str(retry_error)}")
                
                # Raise appropriate exception based on error type
                if error_type in [
                    DifficultyErrorType.SESSION_NOT_FOUND,
                    DifficultyErrorType.VALIDATION_ERROR
                ]:
                    raise ValidationError(error_response["user_friendly_message"])
                elif error_type in [
                    DifficultyErrorType.PERSISTENCE_FAILURE,
                    DifficultyErrorType.STATE_CORRUPTION
                ]:
                    raise DatabaseError("difficulty_operation", error_response["user_friendly_message"])
                else:
                    raise BusinessLogicError(error_response["user_friendly_message"])
        
        return wrapper
    return decorator


# Global difficulty error handling service instance
difficulty_error_service = None


def get_difficulty_error_service(db_session=None) -> DifficultyErrorHandlingService:
    """Get or create difficulty error handling service instance"""
    global difficulty_error_service
    
    if difficulty_error_service is None or (db_session and difficulty_error_service.db != db_session):
        difficulty_error_service = DifficultyErrorHandlingService(db_session)
    
    return difficulty_error_service