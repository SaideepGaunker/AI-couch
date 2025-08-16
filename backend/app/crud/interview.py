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
    session_data: InterviewSessionCreate
) -> InterviewSession:
    """Create new interview session"""
    db_session = InterviewSession(
        user_id=user_id,
        session_type=session_data.session_type.value,
        target_role=session_data.target_role,
        duration=session_data.duration,
        status="active",
        overall_score=0.0
    )
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
    db.add(metric)
    db.commit()
    db.refresh(metric)
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