"""
Interview session endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db
from app.schemas.interview import (
    InterviewSessionCreate, InterviewSessionResponse, InterviewSessionUpdate,
    SessionProgressResponse, SessionSummaryResponse, AnswerSubmission
)
from app.core.dependencies import get_current_user, rate_limit
from app.services.interview_service import InterviewService
from app.db.models import User

router = APIRouter()


@router.post("/start")
async def start_interview(
    session_data: InterviewSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(max_calls=5, window_seconds=300))
):
    """Start a new interview session"""
    interview_service = InterviewService(db)
    
    try:
        result = interview_service.start_interview_session(current_user, session_data)
        return {
            "message": "Interview session started successfully",
            "session_id": result['session'].id,
            "session": result['session'],
            "questions": result['questions'],
            "configuration": result['configuration']
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start interview session"
        )


@router.post("/start-test")
async def start_test_session(
    session_data: InterviewSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(max_calls=5, window_seconds=300))
):
    """Start a new test session"""
    interview_service = InterviewService(db)
    
    try:
        result = interview_service.start_test_session(current_user, session_data)
        return {
            "message": "Test session started successfully",
            "session_id": result['session'].id,
            "session": result['session'],
            "questions": result['questions'],
            "configuration": result['configuration']
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start test session"
        )


@router.get("/", response_model=List[InterviewSessionResponse])
async def get_user_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's interview sessions"""
    interview_service = InterviewService(db)
    
    try:
        sessions = interview_service.get_user_sessions(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            status=status
        )
        return sessions
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sessions"
        )


@router.get("/statistics")
async def get_user_session_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's session statistics"""
    interview_service = InterviewService(db)
    
    try:
        stats = interview_service.get_user_statistics(current_user.id)
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )


@router.get("/{session_id}")
async def get_interview_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get interview session details"""
    interview_service = InterviewService(db)
    
    try:
        session_data = interview_service.get_session_details(session_id, current_user.id)
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        return session_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session"
        )


@router.get("/{session_id}/progress")
async def get_session_progress(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current session progress"""
    interview_service = InterviewService(db)
    
    try:
        progress = interview_service.get_session_progress(session_id, current_user.id)
        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        return progress
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session progress"
        )


@router.put("/{session_id}/pause")
async def pause_interview(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Pause interview session"""
    interview_service = InterviewService(db)
    
    try:
        session = interview_service.pause_interview_session(session_id, current_user.id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or cannot be paused"
            )
        
        return {
            "message": "Interview session paused successfully",
            "session": session
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pause session"
        )


@router.put("/{session_id}/resume")
async def resume_interview(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resume paused interview session"""
    interview_service = InterviewService(db)
    
    try:
        session = interview_service.resume_interview_session(session_id, current_user.id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or cannot be resumed"
            )
        
        return {
            "message": "Interview session resumed successfully",
            "session": session
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resume session"
        )


@router.put("/{session_id}/complete")
async def complete_interview(
    session_id: int,
    final_score: Optional[float] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Complete interview session"""
    interview_service = InterviewService(db)
    
    try:
        result = interview_service.complete_interview_session(
            session_id, 
            current_user.id, 
            final_score
        )
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        return {
            "message": "Interview session completed successfully",
            "session": result['session'],
            "summary": result['summary']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete session"
        )


@router.post("/{session_id}/submit-answer")
async def submit_answer(
    session_id: int,
    answer_data: AnswerSubmission,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit answer for current question"""
    interview_service = InterviewService(db)
    
    try:
        result = interview_service.submit_answer(session_id, current_user.id, answer_data)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit answer"
        )


@router.get("/{session_id}/next-question")
async def get_next_question_contextual(
    session_id: int,
    previous_answer: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get next question with contextual awareness based on previous answer"""
    interview_service = InterviewService(db)
    
    try:
        result = interview_service.get_next_question_contextual(
            session_id, 
            current_user, 
            previous_answer
        )
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get next question"
        )


@router.get("/{session_id}/feedback")
async def get_session_feedback(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed feedback for completed interview session"""
    interview_service = InterviewService(db)
    
    try:
        feedback = interview_service.get_session_feedback(session_id, current_user.id)
        if not feedback:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or feedback not available"
            )
        
        return feedback
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session feedback"
        )


@router.get("/statistics")
async def get_user_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's interview statistics and progress data"""
    interview_service = InterviewService(db)
    
    try:
        statistics = interview_service.get_user_statistics(current_user.id)
        return statistics
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user statistics"
        )


@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify API is working"""
    return {
        "message": "Interview API is working",
        "timestamp": datetime.now().isoformat(),
        "status": "ok"
    }


@router.delete("/{session_id}")
async def delete_interview_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete interview session"""
    interview_service = InterviewService(db)
    
    try:
        # Only allow deletion of user's own sessions
        session_data = interview_service.get_session_details(session_id, current_user.id)
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Note: In a real application, you might want to soft delete or archive sessions
        # instead of hard deletion for data integrity and analytics
        
        return {"message": "Session deletion not implemented - sessions are archived for analytics"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete session"
        )