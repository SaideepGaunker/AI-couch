"""
Posture Detection API Endpoints
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.services.posture_service import posture_service
from app.schemas.user import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter()

class PostureAnalysisRequest(BaseModel):
    """Request model for posture analysis"""
    image_data: str  # Base64 encoded image
    interview_id: int

class PostureAnalysisResponse(BaseModel):
    """Response model for posture analysis"""
    success: bool
    posture_score: float
    posture_status: str
    feedback_message: str
    details: Dict[str, Any]
    landmarks_detected: bool
    timestamp: str

@router.post("/analyze_posture", response_model=Dict[str, Any])
async def analyze_posture(
    request: PostureAnalysisRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze posture from webcam frame
    
    - **image_data**: Base64 encoded image from webcam
    - **interview_id**: ID of the current interview session
    
    Returns real-time posture feedback including:
    - Overall posture score (0-100)
    - Posture status (good/needs_improvement/bad)
    - Specific feedback message
    - Detailed analysis of head tilt, back straightness, and shoulder alignment
    """
    try:
        logger.info(f"Analyzing posture for user {current_user.id}, interview {request.interview_id}")
        
        # Verify interview belongs to current user
        from app.db.models import InterviewSession
        interview = db.query(InterviewSession).filter(
            InterviewSession.id == request.interview_id,
            InterviewSession.user_id == current_user.id
        ).first()
        
        if not interview:
            raise HTTPException(status_code=404, detail="Interview session not found")
        
        # Analyze posture
        result = await posture_service.analyze_frame_from_base64(
            request.image_data, 
            request.interview_id
        )
        
        # Don't raise HTTP exceptions for analysis failures - return the result as-is
        # This prevents posture detection issues from breaking the interview flow
        if "error" in result:
            logger.warning(f"Posture analysis returned error (non-critical): {result['error']}")
        else:
            logger.info(f"Posture analysis completed: score={result.get('posture_score', 0)}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in posture analysis: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during posture analysis")

@router.get("/posture_summary/{interview_id}")
async def get_posture_summary(
    interview_id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get posture summary for an interview session
    
    - **interview_id**: ID of the interview session
    
    Returns session-level posture analysis including:
    - Average posture score
    - Session status
    - Number of evaluations
    - Component scores (head tilt, back straightness, shoulder alignment)
    - Personalized recommendations
    - Timeline of posture scores
    """
    try:
        # Verify interview belongs to current user
        from app.db.models import InterviewSession
        interview = db.query(InterviewSession).filter(
            InterviewSession.id == interview_id,
            InterviewSession.user_id == current_user.id
        ).first()
        
        if not interview:
            raise HTTPException(status_code=404, detail="Interview session not found")
        
        # Get posture summary
        summary = await posture_service.get_session_posture_summary(interview_id)
        
        if "error" in summary:
            raise HTTPException(status_code=400, detail=summary["error"])
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting posture summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# WebSocket endpoint for real-time posture feedback
@router.websocket("/ws/posture/{interview_id}")
async def posture_websocket_endpoint(websocket: WebSocket, interview_id: int):
    """
    WebSocket endpoint for real-time posture analysis
    
    Accepts base64 encoded images and returns real-time posture feedback
    """
    await websocket.accept()
    logger.info(f"WebSocket connection established for interview {interview_id}")
    
    try:
        while True:
            # Receive image data
            data = await websocket.receive_json()
            
            if "image_data" not in data:
                await websocket.send_json({"error": "Missing image_data"})
                continue
            
            # Analyze posture
            result = await posture_service.analyze_frame_from_base64(
                data["image_data"], 
                interview_id
            )
            
            # Send result back to client
            await websocket.send_json(result)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for interview {interview_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass  # Connection might be closed