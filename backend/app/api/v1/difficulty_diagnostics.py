"""
Difficulty Diagnostics API Endpoints

This module provides API endpoints for difficulty state validation, diagnostics,
and health checks to support troubleshooting and system monitoring.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import logging

from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.db.models import User
from app.services.difficulty_validation_service import DifficultyValidationService
from app.services.difficulty_state_recovery_service import DifficultyStateRecoveryService
from app.services.difficulty_error_handling_service import get_difficulty_error_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/difficulty-diagnostics", tags=["difficulty-diagnostics"])


@router.get("/health-check")
async def get_difficulty_system_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Perform comprehensive health check of the difficulty state system
    
    Returns overall system health status and component-level diagnostics.
    """
    try:
        validation_service = DifficultyValidationService(db)
        health_check = validation_service.perform_health_check()
        
        return {
            "success": True,
            "data": health_check
        }
        
    except Exception as e:
        logger.error(f"Error in difficulty system health check: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "health_check_failed",
                "message": "Failed to perform difficulty system health check",
                "details": str(e)
            }
        )


@router.get("/validate")
async def validate_difficulty_state_consistency(
    session_id: Optional[int] = Query(None, description="Specific session ID to validate"),
    user_id: Optional[int] = Query(None, description="Specific user ID to validate"),
    include_cache: bool = Query(True, description="Include cache consistency validation"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Validate difficulty state consistency across the system
    
    Can validate a specific session, all sessions for a user, or system-wide validation.
    """
    try:
        # Authorization check - users can only validate their own sessions
        if user_id and current_user.id != user_id and not current_user.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to validate other users' sessions"
            )
        
        # If session_id is provided, verify user owns the session
        if session_id:
            from app.db.models import InterviewSession
            session = db.query(InterviewSession).filter(
                InterviewSession.id == session_id
            ).first()
            
            if not session:
                raise HTTPException(
                    status_code=404,
                    detail="Session not found"
                )
            
            if session.user_id != current_user.id and not current_user.is_admin:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to validate this session"
                )
        
        # Default to current user if no specific scope provided
        if not session_id and not user_id:
            user_id = current_user.id
        
        validation_service = DifficultyValidationService(db)
        validation_result = validation_service.validate_difficulty_state_consistency(
            session_id=session_id,
            user_id=user_id,
            include_cache_validation=include_cache
        )
        
        return {
            "success": True,
            "data": validation_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in difficulty state validation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "validation_failed",
                "message": "Failed to validate difficulty state consistency",
                "details": str(e)
            }
        )


@router.get("/diagnose/{session_id}")
async def diagnose_session_issues(
    session_id: int = Path(..., description="Session ID to diagnose"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Perform comprehensive diagnosis of issues for a specific session
    
    Provides detailed analysis of difficulty state, cache, and database consistency.
    """
    try:
        # Verify user owns the session or is admin
        from app.db.models import InterviewSession
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Session not found"
            )
        
        if session.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to diagnose this session"
            )
        
        validation_service = DifficultyValidationService(db)
        diagnostic_result = validation_service.diagnose_session_issues(session_id)
        
        return {
            "success": True,
            "data": diagnostic_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in session diagnosis for session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "diagnosis_failed",
                "message": f"Failed to diagnose session {session_id}",
                "details": str(e)
            }
        )


@router.post("/recover/{session_id}")
async def recover_session_difficulty_state(
    session_id: int = Path(..., description="Session ID to recover"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Attempt to recover difficulty state for a specific session
    
    Uses multiple recovery strategies to restore corrupted or missing difficulty state.
    """
    try:
        # Verify user owns the session or is admin
        from app.db.models import InterviewSession
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Session not found"
            )
        
        if session.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to recover this session"
            )
        
        recovery_service = DifficultyStateRecoveryService(db)
        recovery_result = recovery_service.recover_session_difficulty_state(session_id)
        
        return {
            "success": recovery_result.get("recovery_successful", False),
            "data": recovery_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in session recovery for session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "recovery_failed",
                "message": f"Failed to recover session {session_id}",
                "details": str(e)
            }
        )


@router.post("/recover/user/{user_id}")
async def recover_user_difficulty_consistency(
    user_id: int = Path(..., description="User ID to recover"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Validate and fix difficulty consistency for all sessions of a user
    
    Performs user-wide validation and applies fixes for identified issues.
    """
    try:
        # Authorization check - users can only recover their own sessions
        if current_user.id != user_id and not current_user.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to recover other users' sessions"
            )
        
        recovery_service = DifficultyStateRecoveryService(db)
        recovery_result = recovery_service.validate_and_fix_difficulty_consistency(user_id)
        
        return {
            "success": recovery_result.get("validation_successful", False),
            "data": recovery_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in user recovery for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "user_recovery_failed",
                "message": f"Failed to recover user {user_id} difficulty consistency",
                "details": str(e)
            }
        )


@router.post("/reset")
async def reset_difficulty_state(
    session_id: Optional[int] = Query(None, description="Specific session ID to reset"),
    user_id: Optional[int] = Query(None, description="Specific user ID to reset"),
    reset_type: str = Query("soft", description="Type of reset: soft, hard, cache_only"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reset difficulty state for sessions when needed
    
    Provides different reset options:
    - soft: Clear cache, keep database data
    - hard: Clear cache and reset database fields
    - cache_only: Only clear cache
    """
    try:
        # Authorization checks
        if user_id and current_user.id != user_id and not current_user.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to reset other users' sessions"
            )
        
        if session_id:
            from app.db.models import InterviewSession
            session = db.query(InterviewSession).filter(
                InterviewSession.id == session_id
            ).first()
            
            if not session:
                raise HTTPException(
                    status_code=404,
                    detail="Session not found"
                )
            
            if session.user_id != current_user.id and not current_user.is_admin:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to reset this session"
                )
        
        # Default to current user if no specific scope provided
        if not session_id and not user_id:
            user_id = current_user.id
        
        # Validate reset type
        if reset_type not in ["soft", "hard", "cache_only"]:
            raise HTTPException(
                status_code=400,
                detail="Invalid reset type. Must be 'soft', 'hard', or 'cache_only'"
            )
        
        validation_service = DifficultyValidationService(db)
        reset_result = validation_service.reset_difficulty_state(
            session_id=session_id,
            user_id=user_id,
            reset_type=reset_type
        )
        
        return {
            "success": reset_result.get("success", False),
            "data": reset_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in difficulty state reset: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "reset_failed",
                "message": "Failed to reset difficulty state",
                "details": str(e)
            }
        )


@router.get("/statistics")
async def get_difficulty_error_statistics(
    user_id: Optional[int] = Query(None, description="Specific user ID for statistics"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive error statistics for difficulty operations
    
    Provides monitoring data for system health and error patterns.
    """
    try:
        # Authorization check for user-specific statistics
        if user_id and current_user.id != user_id and not current_user.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view other users' statistics"
            )
        
        # Get error handling service statistics
        error_service = get_difficulty_error_service(db)
        error_stats = error_service.get_error_statistics(user_id)
        
        # Get recovery service statistics
        recovery_service = DifficultyStateRecoveryService(db)
        recovery_stats = recovery_service.get_recovery_statistics(user_id)
        
        return {
            "success": True,
            "data": {
                "error_statistics": error_stats,
                "recovery_statistics": recovery_stats,
                "timestamp": error_stats.get("timestamp")
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting difficulty statistics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "statistics_failed",
                "message": "Failed to retrieve difficulty error statistics",
                "details": str(e)
            }
        )


@router.get("/session/{session_id}/state")
async def get_session_difficulty_state_info(
    session_id: int = Path(..., description="Session ID to get state info for"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed difficulty state information for a specific session
    
    Provides comprehensive view of session difficulty state for debugging.
    """
    try:
        # Verify user owns the session or is admin
        from app.db.models import InterviewSession
        session = db.query(InterviewSession).filter(
            InterviewSession.id == session_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Session not found"
            )
        
        if session.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to view this session's state"
            )
        
        # Get state information from service
        from app.services.session_specific_difficulty_service import SessionSpecificDifficultyService
        difficulty_service = SessionSpecificDifficultyService(db)
        
        state_summary = difficulty_service.get_session_difficulty_summary(session_id)
        
        # Add database information
        state_info = {
            "session_id": session_id,
            "database_info": {
                "difficulty_level": session.difficulty_level,
                "initial_difficulty_level": getattr(session, 'initial_difficulty_level', None),
                "current_difficulty_level": getattr(session, 'current_difficulty_level', None),
                "final_difficulty_level": getattr(session, 'final_difficulty_level', None),
                "difficulty_changes_count": getattr(session, 'difficulty_changes_count', 0),
                "has_json_state": session.difficulty_state_json is not None,
                "session_status": session.status,
                "session_mode": getattr(session, 'session_mode', None),
                "parent_session_id": getattr(session, 'parent_session_id', None)
            },
            "state_summary": state_summary,
            "timestamp": state_summary.get("timestamp")
        }
        
        return {
            "success": True,
            "data": state_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session state info for session {session_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "state_info_failed",
                "message": f"Failed to get state info for session {session_id}",
                "details": str(e)
            }
        )


@router.post("/clear-cache")
async def clear_difficulty_cache(
    session_id: Optional[int] = Query(None, description="Specific session ID to clear from cache"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Clear difficulty state from cache
    
    Useful for resolving cache inconsistency issues.
    """
    try:
        if session_id:
            # Verify user owns the session or is admin
            from app.db.models import InterviewSession
            session = db.query(InterviewSession).filter(
                InterviewSession.id == session_id
            ).first()
            
            if not session:
                raise HTTPException(
                    status_code=404,
                    detail="Session not found"
                )
            
            if session.user_id != current_user.id and not current_user.is_admin:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to clear cache for this session"
                )
        
        # Clear cache
        from app.services.session_specific_difficulty_service import SessionSpecificDifficultyService
        difficulty_service = SessionSpecificDifficultyService(db)
        difficulty_service.clear_session_cache(session_id)
        
        return {
            "success": True,
            "data": {
                "message": f"Cache cleared for {'session ' + str(session_id) if session_id else 'all sessions'}",
                "session_id": session_id,
                "timestamp": difficulty_service._get_current_timestamp()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing difficulty cache: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "cache_clear_failed",
                "message": "Failed to clear difficulty cache",
                "details": str(e)
            }
        )