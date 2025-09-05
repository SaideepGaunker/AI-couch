"""
Error Monitoring and Management Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from app.db.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.services.error_handling_service import error_service
from app.core.exceptions import error_tracker, graceful_degradation
from app.db.models import User

router = APIRouter()


@router.get("/stats")
async def get_error_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get error statistics for monitoring"""
    try:
        stats = error_service.get_error_statistics()
        return {
            "status": "success",
            "data": stats,
            "message": "Error statistics retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve error statistics"
        )


@router.get("/recent")
async def get_recent_errors(
    limit: int = 10,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get recent errors (admin only)"""
    try:
        stats = error_tracker.get_error_stats()
        recent_errors = stats.get("recent_errors", [])[:limit]
        
        return {
            "status": "success",
            "data": {
                "errors": recent_errors,
                "total_count": len(recent_errors)
            },
            "message": f"Retrieved {len(recent_errors)} recent errors"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recent errors"
        )


@router.get("/patterns")
async def get_error_patterns(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get error patterns for analysis (admin only)"""
    try:
        stats = error_tracker.get_error_stats()
        patterns = stats.get("error_patterns", {})
        
        return {
            "status": "success",
            "data": {
                "patterns": patterns,
                "pattern_count": len(patterns)
            },
            "message": "Error patterns retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve error patterns"
        )


@router.post("/circuit-breaker/{service_name}/reset")
async def reset_circuit_breaker(
    service_name: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Reset a circuit breaker (admin only)"""
    try:
        error_service.reset_circuit_breaker(service_name)
        return {
            "status": "success",
            "message": f"Circuit breaker for {service_name} has been reset"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset circuit breaker for {service_name}"
        )


@router.post("/features/{feature_name}/enable")
async def enable_feature(
    feature_name: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Re-enable a gracefully degraded feature (admin only)"""
    try:
        error_service.enable_feature(feature_name)
        return {
            "status": "success",
            "message": f"Feature {feature_name} has been enabled"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable feature {feature_name}"
        )


@router.post("/features/{feature_name}/disable")
async def disable_feature(
    feature_name: str,
    reason: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Manually disable a feature (admin only)"""
    try:
        graceful_degradation.disable_feature(feature_name, reason)
        return {
            "status": "success",
            "message": f"Feature {feature_name} has been disabled: {reason}"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable feature {feature_name}"
        )


@router.get("/features/status")
async def get_feature_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get status of all features"""
    try:
        stats = error_service.get_error_statistics()
        disabled_features = stats.get("disabled_features", [])
        
        # Define all features
        all_features = [
            "gemini_service",
            "posture_analysis",
            "voice_analysis",
            "feedback_generation",
            "role_hierarchy",
            "session_management",
            "user_progress",
            "recommendations"
        ]
        
        feature_status = {}
        for feature in all_features:
            feature_status[feature] = {
                "enabled": feature not in disabled_features,
                "status": "disabled" if feature in disabled_features else "enabled"
            }
        
        return {
            "status": "success",
            "data": {
                "features": feature_status,
                "total_features": len(all_features),
                "disabled_count": len(disabled_features)
            },
            "message": "Feature status retrieved successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feature status"
        )


@router.post("/test-error")
async def test_error_handling(
    error_type: str = "generic",
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Test error handling system (admin only)"""
    try:
        if error_type == "validation":
            from app.core.exceptions import ValidationError
            raise ValidationError("Test validation error", "test_field")
        elif error_type == "not_found":
            from app.core.exceptions import NotFoundError
            raise NotFoundError("TestResource", "test_id")
        elif error_type == "database":
            from app.core.exceptions import DatabaseError
            raise DatabaseError("test_operation", "Test database error")
        elif error_type == "external_service":
            from app.core.exceptions import ExternalServiceError
            raise ExternalServiceError("test_service", "Test external service error")
        else:
            raise Exception("Test generic error")
            
    except Exception as e:
        # This will be caught by the global error handler
        raise e


@router.get("/health-check")
async def error_system_health_check():
    """Check health of error handling system"""
    try:
        health_status = {
            "status": "healthy",
            "components": {}
        }
        
        # Check error tracker
        try:
            stats = error_tracker.get_error_stats()
            health_status["components"]["error_tracker"] = {
                "status": "healthy",
                "total_errors": stats["total_errors"],
                "unique_errors": stats["unique_errors"]
            }
        except Exception as e:
            health_status["components"]["error_tracker"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Check graceful degradation
        try:
            disabled_features = list(graceful_degradation.disabled_features)
            health_status["components"]["graceful_degradation"] = {
                "status": "healthy",
                "disabled_features": disabled_features,
                "disabled_count": len(disabled_features)
            }
        except Exception as e:
            health_status["components"]["graceful_degradation"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Check circuit breakers
        try:
            circuit_breaker_stats = {}
            for service, breaker in error_service.circuit_breakers.items():
                circuit_breaker_stats[service] = {
                    "state": breaker["state"],
                    "failures": breaker["failures"]
                }
            
            health_status["components"]["circuit_breakers"] = {
                "status": "healthy",
                "breakers": circuit_breaker_stats,
                "total_breakers": len(circuit_breaker_stats)
            }
        except Exception as e:
            health_status["components"]["circuit_breakers"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        return {
            "status": "success",
            "data": health_status,
            "message": "Error system health check completed"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error system health check failed"
        )


@router.post("/clear-stats")
async def clear_error_statistics(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Clear error statistics (admin only)"""
    try:
        # Reset error tracker
        error_tracker.error_counts.clear()
        error_tracker.recent_errors.clear()
        error_tracker.error_patterns.clear()
        
        return {
            "status": "success",
            "message": "Error statistics cleared successfully"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear error statistics"
        )