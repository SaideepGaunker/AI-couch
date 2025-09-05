"""
CRUD operations for Interview Session model
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.models import InterviewSession, PerformanceMetrics
from app.schemas.interview import InterviewSessionCreate, InterviewSessionUpdate


def create_interview_session(
    db: Session, 
    user_id: int, 
    session_data: InterviewSessionCreate,
    difficulty_level: str = "medium",
    parent_session_id: Optional[int] = None,
    session_mode: str = "new"
) -> InterviewSession:
    """
    Create new interview session with proper relationship tracking
    
    Args:
        db: Database session
        user_id: ID of the user creating the session
        session_data: Session creation data
        difficulty_level: Difficulty level for the session
        parent_session_id: ID of parent session (for practice sessions)
        session_mode: Mode of the session (new, practice_again, quick_test)
        
    Returns:
        InterviewSession: The created session
        
    Raises:
        ValueError: If parent session validation fails
    """
    # Validate parent session relationship for practice sessions
    if session_mode == "practice_again" and parent_session_id:
        parent_session = get_interview_session(db, parent_session_id)
        
        if not parent_session:
            raise ValueError(f"Parent session {parent_session_id} not found")
        
        if parent_session.user_id != user_id:
            raise ValueError(f"Parent session {parent_session_id} does not belong to user {user_id}")
        
        # Validate that parent session is eligible for practice
        if parent_session.status not in ["completed", "active"]:
            raise ValueError(f"Parent session {parent_session_id} has invalid status for practice: {parent_session.status}")
    
    # Create the session with proper relationship tracking
    db_session = InterviewSession(
        user_id=user_id,
        session_type=session_data.session_type.value,
        target_role=session_data.target_role,
        duration=session_data.duration,
        status="active",
        overall_score=0.0,
        performance_score=0.0,
        difficulty_level=difficulty_level,
        parent_session_id=parent_session_id,
        session_mode=session_mode
    )
    
    # Initialize difficulty tracking fields for session-specific difficulty management
    if session_mode == "practice_again" and parent_session_id:
        # For practice sessions, initialize with inherited difficulty
        db_session.initial_difficulty_level = difficulty_level
        db_session.current_difficulty_level = difficulty_level
    else:
        # For new sessions, initialize with user-selected difficulty
        db_session.initial_difficulty_level = difficulty_level
        db_session.current_difficulty_level = difficulty_level
    
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


def get_interview_session(db: Session, session_id: int) -> Optional[InterviewSession]:
    """Get interview session by ID"""
    return db.query(InterviewSession).filter(InterviewSession.id == session_id).first()


def update_interview_session(
    db: Session, 
    session_id: int, 
    update_data: InterviewSessionUpdate
) -> Optional[InterviewSession]:
    """Update interview session"""
    session = get_interview_session(db, session_id)
    if not session:
        return None
    
    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        if hasattr(session, field):
            if field == "status" and hasattr(value, "value"):
                setattr(session, field, value.value)
            else:
                setattr(session, field, value)
    
    db.commit()
    db.refresh(session)
    return session


def get_user_sessions(
    db: Session, 
    user_id: int, 
    limit: int = 10, 
    offset: int = 0
) -> List[InterviewSession]:
    """Get user's interview sessions"""
    return db.query(InterviewSession).filter(
        InterviewSession.user_id == user_id
    ).order_by(
        InterviewSession.created_at.desc()
    ).offset(offset).limit(limit).all()


def get_active_sessions(db: Session, user_id: int) -> List[InterviewSession]:
    """Get user's active sessions"""
    return db.query(InterviewSession).filter(
        InterviewSession.user_id == user_id,
        InterviewSession.status.in_(["active", "paused"])
    ).all()


def delete_interview_session(db: Session, session_id: int) -> bool:
    """Delete interview session"""
    session = get_interview_session(db, session_id)
    if not session:
        return False
    
    # Delete associated performance metrics first
    db.query(PerformanceMetrics).filter(
        PerformanceMetrics.session_id == session_id
    ).delete()
    
    db.delete(session)
    db.commit()
    return True


def get_practice_sessions(db: Session, parent_session_id: int) -> List[InterviewSession]:
    """Get all practice sessions for a given parent session"""
    return db.query(InterviewSession).filter(
        InterviewSession.parent_session_id == parent_session_id,
        InterviewSession.session_mode == "practice_again"
    ).order_by(InterviewSession.created_at.desc()).all()


def get_session_family(db: Session, session_id: int) -> dict:
    """
    Get the complete session family (parent and all practice sessions)
    
    Args:
        db: Database session
        session_id: ID of any session in the family
        
    Returns:
        dict: Contains parent session and all practice sessions
    """
    session = get_interview_session(db, session_id)
    if not session:
        return {"parent": None, "practice_sessions": []}
    
    # Find the root parent session
    parent_session = session
    if session.parent_session_id:
        parent_session = get_interview_session(db, session.parent_session_id)
        if not parent_session:
            parent_session = session  # Fallback if parent not found
    
    # Get all practice sessions for this parent
    practice_sessions = get_practice_sessions(db, parent_session.id)
    
    return {
        "parent": parent_session,
        "practice_sessions": practice_sessions,
        "total_practice_sessions": len(practice_sessions)
    }


def validate_practice_session_relationship(db: Session, parent_session_id: int, user_id: int) -> dict:
    """
    Validate that a practice session relationship is valid
    
    Args:
        db: Database session
        parent_session_id: ID of the proposed parent session
        user_id: ID of the user creating the practice session
        
    Returns:
        dict: Validation results with is_valid flag and details
    """
    validation_result = {
        "is_valid": False,
        "errors": [],
        "warnings": [],
        "parent_session_info": None
    }
    
    try:
        # Check if parent session exists
        parent_session = get_interview_session(db, parent_session_id)
        if not parent_session:
            validation_result["errors"].append(f"Parent session {parent_session_id} not found")
            return validation_result
        
        validation_result["parent_session_info"] = {
            "id": parent_session.id,
            "user_id": parent_session.user_id,
            "status": parent_session.status,
            "session_mode": parent_session.session_mode,
            "target_role": parent_session.target_role,
            "created_at": parent_session.created_at.isoformat() if parent_session.created_at else None
        }
        
        # Check ownership
        if parent_session.user_id != user_id:
            validation_result["errors"].append(f"Parent session {parent_session_id} belongs to user {parent_session.user_id}, not {user_id}")
            return validation_result
        
        # Check session status
        if parent_session.status not in ["completed", "active"]:
            validation_result["errors"].append(f"Parent session status '{parent_session.status}' is not valid for practice session creation")
        
        # Check if parent is already a practice session
        if parent_session.session_mode == "practice_again":
            validation_result["warnings"].append("Creating practice session from another practice session")
        
        # Check if parent has target role
        if not parent_session.target_role:
            validation_result["errors"].append("Parent session has no target role specified")
        
        # Get existing practice sessions count
        existing_practice_sessions = get_practice_sessions(db, parent_session_id)
        validation_result["existing_practice_sessions_count"] = len(existing_practice_sessions)
        
        if len(existing_practice_sessions) >= 10:  # Reasonable limit
            validation_result["warnings"].append(f"Parent session already has {len(existing_practice_sessions)} practice sessions")
        
        # Validation passes if no errors
        validation_result["is_valid"] = len(validation_result["errors"]) == 0
        
        return validation_result
        
    except Exception as e:
        validation_result["errors"].append(f"Validation error: {str(e)}")
        return validation_result


def get_user_sessions_with_family_info(
    db: Session, 
    user_id: int, 
    limit: int = 10, 
    offset: int = 0,
    include_practice_sessions: bool = True
) -> List[InterviewSession]:
    """
    Get user's interview sessions with family relationship information
    
    Args:
        db: Database session
        user_id: ID of the user
        limit: Maximum number of sessions to return
        offset: Number of sessions to skip
        include_practice_sessions: Whether to include practice sessions in results
        
    Returns:
        List of sessions with family_info attribute added
    """
    # Base query for user sessions
    query = db.query(InterviewSession).filter(InterviewSession.user_id == user_id)
    
    # Optionally exclude practice sessions from main list
    if not include_practice_sessions:
        query = query.filter(InterviewSession.session_mode != "practice_again")
    
    sessions = query.order_by(InterviewSession.created_at.desc()).offset(offset).limit(limit).all()
    
    # Add family information to each session
    for session in sessions:
        family_info = get_session_family(db, session.id)
        
        # Add family info as an attribute
        session.family_info = {
            "is_parent_session": session.parent_session_id is None,
            "is_practice_session": session.session_mode == "practice_again",
            "parent_session_id": session.parent_session_id,
            "practice_sessions_count": family_info["total_practice_sessions"] if session.parent_session_id is None else 0,
            "has_practice_sessions": family_info["total_practice_sessions"] > 0 if session.parent_session_id is None else False
        }
    
    return sessions


def update_session_relationship_tracking(
    db: Session, 
    session_id: int, 
    parent_session_id: Optional[int] = None,
    session_mode: Optional[str] = None
) -> Optional[InterviewSession]:
    """
    Update session relationship tracking fields
    
    Args:
        db: Database session
        session_id: ID of the session to update
        parent_session_id: New parent session ID (optional)
        session_mode: New session mode (optional)
        
    Returns:
        Updated session or None if not found
    """
    session = get_interview_session(db, session_id)
    if not session:
        return None
    
    # Validate parent session if provided
    if parent_session_id is not None:
        if parent_session_id != session.parent_session_id:
            # Validate the new parent session
            validation = validate_practice_session_relationship(db, parent_session_id, session.user_id)
            if not validation["is_valid"]:
                raise ValueError(f"Invalid parent session: {'; '.join(validation['errors'])}")
            
            session.parent_session_id = parent_session_id
    
    # Update session mode if provided
    if session_mode is not None:
        valid_modes = ["new", "practice_again", "quick_test", "continued"]
        if session_mode not in valid_modes:
            raise ValueError(f"Invalid session mode '{session_mode}'. Must be one of: {valid_modes}")
        
        session.session_mode = session_mode
    
    db.commit()
    db.refresh(session)
    return session
    db.commit()
    return True


def create_performance_metric(
    db: Session,
    session_id: int,
    question_id: int,
    answer_text: str,
    response_time: int,
    content_quality_score: float = 0.0,
    body_language_score: float = 0.0,
    tone_confidence_score: float = 0.0,
    improvement_suggestions: List[str] = None
) -> PerformanceMetrics:
    """Create performance metric for a question answer"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"=== CRUD DEBUG ===")
    logger.info(f"Creating performance metric with body_language_score: {body_language_score}")
    logger.info(f"All parameters: session_id={session_id}, question_id={question_id}, body_language_score={body_language_score}")
    
    metric = PerformanceMetrics(
        session_id=session_id,
        question_id=question_id,
        answer_text=answer_text,
        response_time=response_time,
        content_quality_score=content_quality_score,
        body_language_score=body_language_score,
        tone_confidence_score=tone_confidence_score,
        improvement_suggestions=improvement_suggestions or []
    )
    
    logger.info(f"Metric object created: {metric}")
    logger.info(f"Metric body_language_score before add: {metric.body_language_score}")
    
    logger.info(f"Adding metric to database session...")
    db.add(metric)
    
    # Check if the metric is in the session
    logger.info(f"Metric in session before commit: {metric in db}")
    
    try:
        logger.info(f"Committing to database...")
        db.commit()
        logger.info(f"Database commit successful")
    except Exception as e:
        logger.error(f"Database commit failed: {str(e)}")
        db.rollback()
        raise
    
    # Check if the metric is still in the session after commit
    logger.info(f"Metric in session after commit: {metric in db}")
    
    logger.info(f"Refreshing metric from database...")
    db.refresh(metric)
    
    logger.info(f"Metric body_language_score after commit: {metric.body_language_score}")
    logger.info(f"=== END CRUD DEBUG ===")
    
    return metric


def get_session_performance_metrics(
    db: Session, 
    session_id: int
) -> List[PerformanceMetrics]:
    """Get all performance metrics for a session"""
    return db.query(PerformanceMetrics).filter(
        PerformanceMetrics.session_id == session_id
    ).all()


def get_user_performance_history(
    db: Session, 
    user_id: int, 
    days: int = 30
) -> List[PerformanceMetrics]:
    """Get user's performance history"""
    from datetime import timedelta
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    return db.query(PerformanceMetrics).join(InterviewSession).filter(
        InterviewSession.user_id == user_id,
        PerformanceMetrics.created_at >= start_date
    ).order_by(PerformanceMetrics.created_at.desc()).all()