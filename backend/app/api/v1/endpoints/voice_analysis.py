"""
Voice Analysis API endpoint - receives results from frontend
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging

from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.db.models import User, PerformanceMetrics
from app.crud.interview import get_interview_session

router = APIRouter()
logger = logging.getLogger(__name__)


class VoiceAnalysisRequest(BaseModel):
    """Request model for voice analysis results from frontend"""
    session_id: int
    question_id: int
    tone_confidence_score: float
    analysis_duration: Optional[int] = 0
    total_samples: Optional[int] = 0
    improvement_suggestions: Optional[str] = ""


class VoiceAnalysisResponse(BaseModel):
    """Response model for voice analysis submission"""
    success: bool
    message: str
    performance_metric_id: Optional[int] = None


@router.post("/voice-confidence", response_model=VoiceAnalysisResponse)
async def submit_voice_analysis(
    request: VoiceAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit voice analysis results from frontend
    
    Args:
        request: Voice analysis data from frontend
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        VoiceAnalysisResponse with success status
    """
    try:
        # Validate session belongs to current user
        session = get_interview_session(db, request.session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview session not found"
            )
        
        if session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this interview session"
            )
        
        # Validate score range
        if not (0 <= request.tone_confidence_score <= 100):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tone confidence score must be between 0 and 100"
            )
        
        # Check if performance metric already exists for this session/question
        existing_metric = db.query(PerformanceMetrics).filter(
            PerformanceMetrics.session_id == request.session_id,
            PerformanceMetrics.question_id == request.question_id
        ).first()
        
        if existing_metric:
            # Update existing metric
            existing_metric.tone_confidence_score = request.tone_confidence_score
            
            # Update improvement suggestions if provided
            if request.improvement_suggestions:
                current_suggestions = existing_metric.improvement_suggestions or []
                if request.improvement_suggestions not in current_suggestions:
                    current_suggestions.append(request.improvement_suggestions)
                    existing_metric.improvement_suggestions = current_suggestions
            
            db.commit()
            db.refresh(existing_metric)
            
            logger.info(f"Updated voice analysis for session {request.session_id}, question {request.question_id}: score={request.tone_confidence_score}")
            
            return VoiceAnalysisResponse(
                success=True,
                message="Voice analysis results updated successfully",
                performance_metric_id=existing_metric.id
            )
        
        else:
            # Create new performance metric
            new_metric = PerformanceMetrics(
                session_id=request.session_id,
                question_id=request.question_id,
                tone_confidence_score=request.tone_confidence_score,
                improvement_suggestions=[request.improvement_suggestions] if request.improvement_suggestions else [],
                answer_text="",  # Will be filled when answer is submitted
                response_time=request.analysis_duration or 0
            )
            
            db.add(new_metric)
            db.commit()
            db.refresh(new_metric)
            
            logger.info(f"Created voice analysis for session {request.session_id}, question {request.question_id}: score={request.tone_confidence_score}")
            
            return VoiceAnalysisResponse(
                success=True,
                message="Voice analysis results saved successfully",
                performance_metric_id=new_metric.id
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving voice analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while saving voice analysis"
        )


@router.get("/voice-confidence/{session_id}")
async def get_session_voice_analysis(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get voice analysis results for a session
    
    Args:
        session_id: Interview session ID
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Voice analysis summary for the session
    """
    try:
        # Validate session belongs to current user
        session = get_interview_session(db, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview session not found"
            )
        
        if session.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this interview session"
            )
        
        # Get all performance metrics with voice analysis for this session
        metrics = db.query(PerformanceMetrics).filter(
            PerformanceMetrics.session_id == session_id,
            PerformanceMetrics.tone_confidence_score.isnot(None),
            PerformanceMetrics.tone_confidence_score > 0
        ).all()
        
        if not metrics:
            return {
                "session_id": session_id,
                "total_questions": 0,
                "average_score": 0,
                "voice_analysis_available": False,
                "message": "No voice analysis data available for this session"
            }
        
        # Calculate statistics
        scores = [metric.tone_confidence_score for metric in metrics]
        average_score = sum(scores) / len(scores)
        
        # Collect all suggestions
        all_suggestions = []
        for metric in metrics:
            if metric.improvement_suggestions:
                all_suggestions.extend(metric.improvement_suggestions)
        
        # Remove duplicates while preserving order
        unique_suggestions = list(dict.fromkeys(all_suggestions))
        
        return {
            "session_id": session_id,
            "total_questions": len(metrics),
            "average_score": round(average_score, 1),
            "min_score": min(scores),
            "max_score": max(scores),
            "voice_analysis_available": True,
            "improvement_suggestions": unique_suggestions,
            "detailed_scores": [
                {
                    "question_id": metric.question_id,
                    "score": metric.tone_confidence_score,
                    "suggestions": metric.improvement_suggestions
                }
                for metric in metrics
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving voice analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving voice analysis"
        )