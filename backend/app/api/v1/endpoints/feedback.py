"""
Feedback and scoring endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.schemas.question import AnswerEvaluationRequest, AnswerEvaluationResponse, FeedbackRequest, FeedbackResponse
from app.core.dependencies import get_current_user, rate_limit
from app.services.gemini_service import GeminiService
from app.services.feedback_service import FeedbackService
from app.db.models import User

router = APIRouter()


@router.post("/analyze", response_model=AnswerEvaluationResponse)
async def analyze_answer(
    request: AnswerEvaluationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(max_calls=30, window_seconds=300))
):
    """Analyze and score user's answer"""
    feedback_service = FeedbackService(db)
    
    try:
        evaluation = feedback_service.analyze_answer(
            question_id=request.question_id,
            answer_text=request.answer_text,
            user_id=current_user.id,
            context=request.context
        )
        
        return AnswerEvaluationResponse(**evaluation)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze answer"
        )


@router.get("/session/{session_id}")
async def get_session_feedback(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive feedback for interview session"""
    feedback_service = FeedbackService(db)
    
    try:
        feedback = feedback_service.get_session_feedback(session_id, current_user.id)
        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session feedback not found"
            )
        
        return feedback
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session feedback"
        )


@router.post("/generate")
async def generate_personalized_feedback(
    request: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(max_calls=10, window_seconds=300))
):
    """Generate personalized feedback using AI"""
    feedback_service = FeedbackService(db)
    
    try:
        feedback = feedback_service.generate_personalized_feedback(
            session_id=request.session_id,
            user_id=current_user.id,
            performance_data=request.performance_data
        )
        
        return FeedbackResponse(**feedback)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate feedback"
        )