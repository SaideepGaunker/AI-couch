"""
CRUD operations for Performance Metrics
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models import PerformanceMetrics


def get_by_session_and_question(
    db: Session, 
    session_id: int, 
    question_id: int
) -> Optional[PerformanceMetrics]:
    """Get performance metric by session and question ID"""
    return db.query(PerformanceMetrics).filter(
        PerformanceMetrics.session_id == session_id,
        PerformanceMetrics.question_id == question_id
    ).first()


def create_with_tone_analysis(
    db: Session,
    session_id: int,
    question_id: int,
    tone_confidence_score: float,
    improvement_suggestions: str,
    answer_text: str = "",
    response_time: int = 0
) -> PerformanceMetrics:
    """Create new performance metric with tone analysis"""
    metric = PerformanceMetrics(
        session_id=session_id,
        question_id=question_id,
        answer_text=answer_text,
        response_time=response_time,
        tone_confidence_score=tone_confidence_score,
        improvement_suggestions=[improvement_suggestions] if improvement_suggestions else []
    )
    
    db.add(metric)
    db.commit()
    db.refresh(metric)
    return metric


def update_tone_confidence(
    db: Session,
    performance_id: int,
    tone_score: float,
    suggestions: str
) -> Optional[PerformanceMetrics]:
    """Update existing performance metric with tone confidence data"""
    metric = db.query(PerformanceMetrics).filter(
        PerformanceMetrics.id == performance_id
    ).first()
    
    if not metric:
        return None
    
    metric.tone_confidence_score = tone_score
    
    # Update improvement suggestions
    current_suggestions = metric.improvement_suggestions or []
    if suggestions and suggestions not in current_suggestions:
        current_suggestions.append(suggestions)
        metric.improvement_suggestions = current_suggestions
    
    db.commit()
    db.refresh(metric)
    return metric


def update_performance_metric(
    db: Session,
    session_id: int,
    question_id: int,
    **kwargs
) -> Optional[PerformanceMetrics]:
    """Update or create performance metric with provided data"""
    metric = get_by_session_and_question(db, session_id, question_id)
    
    if metric:
        # Update existing metric
        for key, value in kwargs.items():
            if hasattr(metric, key) and value is not None:
                setattr(metric, key, value)
        db.commit()
        db.refresh(metric)
        return metric
    else:
        # Create new metric
        metric = PerformanceMetrics(
            session_id=session_id,
            question_id=question_id,
            **kwargs
        )
        db.add(metric)
        db.commit()
        db.refresh(metric)
        return metric


def get_session_metrics(db: Session, session_id: int) -> List[PerformanceMetrics]:
    """Get all performance metrics for a session"""
    return db.query(PerformanceMetrics).filter(
        PerformanceMetrics.session_id == session_id
    ).all()