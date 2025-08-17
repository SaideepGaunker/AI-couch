"""
Posture Detection Service
Handles posture analysis and storage for interview sessions
"""
import logging
from typing import Dict, Any, List, Optional
import base64
import numpy as np
import cv2
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.body_language_service import PostureAnalyzer
from app.db.database import get_db

logger = logging.getLogger(__name__)

class PostureService:
    """Service for handling posture detection and storage"""
    
    def __init__(self):
        self.analyzer = PostureAnalyzer()
        logger.info("Posture service initialized")
    
    async def analyze_frame_from_base64(self, image_data: str, interview_id: int) -> Dict[str, Any]:
        """
        Analyze posture from base64 encoded image with enhanced error handling
        
        Args:
            image_data: Base64 encoded image string
            interview_id: ID of the interview session
            
        Returns:
            Dict containing posture analysis results
        """
        try:
            # Validate input parameters
            if not image_data or not isinstance(image_data, str):
                logger.warning("Invalid or empty image data provided")
                return {
                    "success": False,
                    "error": "Invalid image data",
                    "posture_score": 0,
                    "posture_status": "error",
                    "feedback_message": "Unable to process image data",
                    "landmarks_detected": False
                }
            
            if not isinstance(interview_id, int) or interview_id <= 0:
                logger.warning(f"Invalid interview_id provided: {interview_id}")
                return {
                    "success": False,
                    "error": "Invalid interview ID",
                    "posture_score": 0,
                    "posture_status": "error",
                    "feedback_message": "Invalid session identifier",
                    "landmarks_detected": False
                }
            
            # Decode base64 image
            frame = self._decode_base64_image(image_data)
            if frame is None:
                logger.warning("Failed to decode base64 image data")
                return {
                    "success": False,
                    "error": "Failed to decode image",
                    "posture_score": 0,
                    "posture_status": "error",
                    "feedback_message": "Unable to process image format",
                    "landmarks_detected": False
                }
            
            # Analyze posture
            result = self.analyzer.analyze_frame(frame)
            
            # Validate analysis result structure
            if not isinstance(result, dict):
                logger.error("Analyzer returned invalid result type")
                return {
                    "success": False,
                    "error": "Invalid analysis result",
                    "posture_score": 0,
                    "posture_status": "error",
                    "feedback_message": "Analysis failed",
                    "landmarks_detected": False
                }
            
            # Posture data is now calculated in real-time and stored in PerformanceMetrics
            # No need to store in PostureEvaluation table
            logger.info(f"Posture analysis completed for interview {interview_id} - result returned without database storage")
            
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error analyzing frame for interview {interview_id}: {e}")
            return {
                "success": False,
                "error": "Internal analysis error",
                "posture_score": 0,
                "posture_status": "error",
                "feedback_message": "Unable to analyze posture at this time",
                "landmarks_detected": False
            }
    
    def _decode_base64_image(self, image_data: str) -> Optional[np.ndarray]:
        """Decode base64 image to numpy array with enhanced validation"""
        try:
            # Validate input
            if not image_data or not isinstance(image_data, str):
                logger.warning("Invalid image data type or empty string")
                return None
            
            # Remove data URL prefix if present
            if image_data.startswith('data:image'):
                parts = image_data.split(',')
                if len(parts) < 2:
                    logger.warning("Invalid data URL format")
                    return None
                image_data = parts[1]
            
            # Validate base64 string length
            if len(image_data) < 100:  # Minimum reasonable size for an image
                logger.warning("Base64 string too short to be a valid image")
                return None
            
            # Decode base64
            try:
                image_bytes = base64.b64decode(image_data, validate=True)
            except Exception as decode_error:
                logger.warning(f"Invalid base64 encoding: {decode_error}")
                return None
            
            # Validate decoded data size
            if len(image_bytes) < 100:
                logger.warning("Decoded image data too small")
                return None
            
            # Convert to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            
            # Decode image
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Validate decoded frame
            if frame is None:
                logger.warning("OpenCV failed to decode image data")
                return None
            
            # Validate frame dimensions
            if frame.shape[0] < 50 or frame.shape[1] < 50:
                logger.warning(f"Image too small for analysis: {frame.shape}")
                return None
            
            return frame
            
        except Exception as e:
            logger.error(f"Error decoding base64 image: {e}")
            return None
    
    def _safe_get_nested(self, data: Dict[str, Any], keys: List[str], default: Any = 0.0) -> Any:
        """Safely get nested dictionary values with fallback defaults"""
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    async def get_session_posture_summary(self, interview_id: int) -> Dict[str, Any]:
        """Get posture summary for an interview session - placeholder since database storage removed"""
        logger.info(f"Posture summary requested for interview {interview_id} - database storage removed")
        
        return {
            "session_score": 0,
            "session_status": "no_data",
            "evaluation_count": 0,
            "recommendations": ["Posture data is now calculated in real-time and stored in PerformanceMetrics"],
            "average_scores": {
                "head_tilt": 0,
                "back_straightness": 0,
                "shoulder_alignment": 0
            },
            "timeline": []
        }
    
    def _get_posture_status(self, score: float) -> str:
        """Get posture status based on score"""
        if score >= 80:
            return "good"
        elif score >= 60:
            return "needs_improvement"
        else:
            return "bad"
    
    def _generate_session_recommendations(self, head_tilt_score: float, back_score: float, shoulder_score: float) -> List[str]:
        """Generate recommendations based on session averages"""
        recommendations = []
        
        if head_tilt_score < 70:
            recommendations.append("Practice maintaining proper head position - keep your chin parallel to the ground")
        
        if back_score < 70:
            recommendations.append("Work on your sitting posture - keep your back straight and shoulders back")
        
        if shoulder_score < 70:
            recommendations.append("Focus on keeping your shoulders level and relaxed")
        
        if not recommendations:
            recommendations.append("Great posture throughout the session! Keep up the excellent work.")
        
        return recommendations

# Global instance
posture_service = PostureService()