"""
Body Language Detection Service using MediaPipe
Real-time posture analysis for interview sessions
"""
import logging
import math
import base64
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import cv2
import mediapipe as mp
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.database import get_db

logger = logging.getLogger(__name__)

class PostureAnalyzer:
    """Analyzes posture using MediaPipe pose detection"""
    
    def __init__(self):
        """Initialize MediaPipe pose detection with optimized configuration"""
        try:
            self.mp_pose = mp.solutions.pose
            self.mp_drawing = mp.solutions.drawing_utils
            
            # Initialize with optimized settings to reduce warnings
            self.pose = self.mp_pose.Pose(
                static_image_mode=True,  # Better for single frame analysis
                model_complexity=1,      # Good balance of accuracy and performance
                enable_segmentation=False,
                min_detection_confidence=0.7,  # Higher confidence for better reliability
                min_tracking_confidence=0.5
            )
            
            self.is_initialized = True
            logger.info("MediaPipe posture analyzer initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize MediaPipe posture analyzer: {e}")
            self.is_initialized = False
            self.pose = None
    
    def analyze_frame(self, frame_data: np.ndarray) -> Dict[str, Any]:
        """
        Analyze a single frame for posture with enhanced validation
        
        Args:
            frame_data: RGB image array from webcam
            
        Returns:
            Dict containing posture analysis results
        """
        if not self.is_initialized or self.pose is None:
            logger.error("MediaPipe analyzer not properly initialized")
            return self._error_response("Analyzer not initialized")
        
        try:
            # Validate input frame
            if frame_data is None:
                logger.warning("Received None frame data")
                return self._error_response("Invalid frame data")
            
            if not isinstance(frame_data, np.ndarray):
                logger.warning(f"Invalid frame data type: {type(frame_data)}")
                return self._error_response("Invalid frame data type")
            
            if len(frame_data.shape) != 3 or frame_data.shape[2] != 3:
                logger.warning(f"Invalid frame shape: {frame_data.shape}")
                return self._error_response("Invalid frame dimensions")
            
            # Convert BGR to RGB if needed (OpenCV uses BGR by default)
            try:
                rgb_frame = cv2.cvtColor(frame_data, cv2.COLOR_BGR2RGB)
            except Exception as convert_error:
                logger.warning(f"Failed to convert frame color space: {convert_error}")
                rgb_frame = frame_data  # Use original if conversion fails
            
            # Process the frame with MediaPipe
            try:
                results = self.pose.process(rgb_frame)
            except Exception as process_error:
                logger.error(f"MediaPipe processing failed: {process_error}")
                return self._error_response("Pose detection failed")
            
            # Check if pose landmarks were detected
            if not results or not results.pose_landmarks:
                return self._no_pose_response()
            
            # Extract landmarks
            landmarks = results.pose_landmarks.landmark
            if not landmarks:
                return self._no_pose_response()
            
            # Analyze posture components with error handling
            head_tilt = self._analyze_head_tilt(landmarks)
            back_straightness = self._analyze_back_straightness(landmarks)
            shoulder_alignment = self._analyze_shoulder_alignment(landmarks)
            
            # Validate analysis results
            if not all(isinstance(result, dict) for result in [head_tilt, back_straightness, shoulder_alignment]):
                logger.error("Invalid analysis component results")
                return self._error_response("Analysis component failure")
            
            # Calculate overall posture score
            posture_score = self._calculate_posture_score(head_tilt, back_straightness, shoulder_alignment)
            
            # Determine posture status
            posture_status = self._get_posture_status(posture_score)
            
            # Generate feedback message
            feedback_message = self._generate_feedback(head_tilt, back_straightness, shoulder_alignment)
            
            return {
                "success": True,
                "posture_score": round(float(posture_score), 1),
                "posture_status": posture_status,
                "feedback_message": feedback_message,
                "details": {
                    "head_tilt": {
                        "angle": round(float(head_tilt.get("angle", 0)), 1),
                        "status": head_tilt.get("status", "unknown"),
                        "score": round(float(head_tilt.get("score", 0)), 1)
                    },
                    "back_straightness": {
                        "angle": round(float(back_straightness.get("angle", 0)), 1),
                        "status": back_straightness.get("status", "unknown"),
                        "score": round(float(back_straightness.get("score", 0)), 1)
                    },
                    "shoulder_alignment": {
                        "difference": round(float(shoulder_alignment.get("difference", 0)), 3),
                        "status": shoulder_alignment.get("status", "unknown"),
                        "score": round(float(shoulder_alignment.get("score", 0)), 1)
                    }
                },
                "landmarks_detected": True,
                "timestamp": self._get_timestamp()
            }
            
        except Exception as e:
            logger.error(f"Unexpected error analyzing posture: {e}")
            return self._error_response(f"Analysis failed: {str(e)}")
    
    def _analyze_head_tilt(self, landmarks) -> Dict[str, Any]:
        """Analyze head tilt (forward/backward) with improved error handling"""
        try:
            # Validate landmarks exist
            if not landmarks:
                logger.warning("No landmarks provided for head tilt analysis")
                return {"angle": 0, "status": "unknown", "score": 50}
            
            # Get nose and ear landmarks with validation
            try:
                nose = landmarks[self.mp_pose.PoseLandmark.NOSE]
                left_ear = landmarks[self.mp_pose.PoseLandmark.LEFT_EAR]
                right_ear = landmarks[self.mp_pose.PoseLandmark.RIGHT_EAR]
            except (IndexError, KeyError) as e:
                logger.warning(f"Required landmarks not found for head tilt analysis: {e}")
                return {"angle": 0, "status": "unknown", "score": 50}
            
            # Validate landmark coordinates
            if not all(hasattr(lm, 'y') for lm in [nose, left_ear, right_ear]):
                logger.warning("Invalid landmark coordinates for head tilt analysis")
                return {"angle": 0, "status": "unknown", "score": 50}
            
            # Calculate average ear position
            avg_ear_y = (left_ear.y + right_ear.y) / 2
            
            # Calculate head tilt angle
            head_tilt_angle = math.degrees(math.atan2(nose.y - avg_ear_y, 0.1))
            
            # Ensure angle is a valid number
            if not isinstance(head_tilt_angle, (int, float)) or math.isnan(head_tilt_angle):
                logger.warning("Invalid head tilt angle calculated")
                return {"angle": 0, "status": "unknown", "score": 50}
            
            # Determine status and score
            abs_angle = abs(head_tilt_angle)
            if abs_angle <= 10:
                status = "good"
                score = 100
            elif abs_angle <= 20:
                status = "needs_improvement"
                score = 70
            else:
                status = "bad"
                score = 40
            
            return {
                "angle": float(head_tilt_angle),
                "status": status,
                "score": float(score)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing head tilt: {e}")
            return {"angle": 0.0, "status": "unknown", "score": 50.0}
    
    def _analyze_back_straightness(self, landmarks) -> Dict[str, Any]:
        """Analyze back straightness (slouching detection) with improved error handling"""
        try:
            # Validate landmarks exist
            if not landmarks:
                logger.warning("No landmarks provided for back straightness analysis")
                return {"angle": 0, "status": "unknown", "score": 50}
            
            # Get shoulder and hip landmarks with validation
            try:
                left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
                right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
                left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP]
                right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP]
            except (IndexError, KeyError) as e:
                logger.warning(f"Required landmarks not found for back straightness analysis: {e}")
                return {"angle": 0, "status": "unknown", "score": 50}
            
            # Validate landmark coordinates
            required_landmarks = [left_shoulder, right_shoulder, left_hip, right_hip]
            if not all(hasattr(lm, 'x') and hasattr(lm, 'y') for lm in required_landmarks):
                logger.warning("Invalid landmark coordinates for back straightness analysis")
                return {"angle": 0, "status": "unknown", "score": 50}
            
            # Calculate average positions
            avg_shoulder_y = (left_shoulder.y + right_shoulder.y) / 2
            avg_hip_y = (left_hip.y + right_hip.y) / 2
            avg_shoulder_x = (left_shoulder.x + right_shoulder.x) / 2
            avg_hip_x = (left_hip.x + right_hip.x) / 2
            
            # Calculate back angle
            back_angle = math.degrees(math.atan2(avg_shoulder_y - avg_hip_y, avg_shoulder_x - avg_hip_x))
            
            # Validate calculated angle
            if not isinstance(back_angle, (int, float)) or math.isnan(back_angle):
                logger.warning("Invalid back angle calculated")
                return {"angle": 0, "status": "unknown", "score": 50}
            
            # Normalize angle (we want vertical alignment)
            normalized_angle = abs(90 - abs(back_angle))
            
            # Determine status and score
            if normalized_angle <= 15:
                status = "good"
                score = 100
            elif normalized_angle <= 30:
                status = "needs_improvement"
                score = 70
            else:
                status = "bad"
                score = 40
            
            return {
                "angle": float(normalized_angle),
                "status": status,
                "score": float(score)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing back straightness: {e}")
            return {"angle": 0.0, "status": "unknown", "score": 50.0}
    
    def _analyze_shoulder_alignment(self, landmarks) -> Dict[str, Any]:
        """Analyze shoulder alignment (level shoulders) with improved error handling"""
        try:
            # Validate landmarks exist
            if not landmarks:
                logger.warning("No landmarks provided for shoulder alignment analysis")
                return {"difference": 0, "status": "unknown", "score": 50}
            
            # Get shoulder landmarks with validation
            try:
                left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER]
                right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER]
            except (IndexError, KeyError) as e:
                logger.warning(f"Required landmarks not found for shoulder alignment analysis: {e}")
                return {"difference": 0, "status": "unknown", "score": 50}
            
            # Validate landmark coordinates
            if not all(hasattr(lm, 'y') for lm in [left_shoulder, right_shoulder]):
                logger.warning("Invalid landmark coordinates for shoulder alignment analysis")
                return {"difference": 0, "status": "unknown", "score": 50}
            
            # Calculate shoulder height difference
            shoulder_diff = abs(left_shoulder.y - right_shoulder.y)
            
            # Validate calculated difference
            if not isinstance(shoulder_diff, (int, float)) or math.isnan(shoulder_diff):
                logger.warning("Invalid shoulder difference calculated")
                return {"difference": 0, "status": "unknown", "score": 50}
            
            # Determine status and score
            if shoulder_diff <= 0.02:
                status = "good"
                score = 100
            elif shoulder_diff <= 0.05:
                status = "needs_improvement"
                score = 70
            else:
                status = "bad"
                score = 40
            
            return {
                "difference": float(shoulder_diff),
                "status": status,
                "score": float(score)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing shoulder alignment: {e}")
            return {"difference": 0.0, "status": "unknown", "score": 50.0}
    
    def _calculate_posture_score(self, head_tilt: Dict, back_straightness: Dict, shoulder_alignment: Dict) -> float:
        """Calculate overall posture score (0-100)"""
        # Weighted average of all components
        weights = {
            "head_tilt": 0.3,
            "back_straightness": 0.5,
            "shoulder_alignment": 0.2
        }
        
        total_score = (
            head_tilt["score"] * weights["head_tilt"] +
            back_straightness["score"] * weights["back_straightness"] +
            shoulder_alignment["score"] * weights["shoulder_alignment"]
        )
        
        return max(0, min(100, total_score))
    
    def _get_posture_status(self, score: float) -> str:
        """Get posture status based on score"""
        if score >= 80:
            return "good"
        elif score >= 60:
            return "needs_improvement"
        else:
            return "bad"
    
    def _generate_feedback(self, head_tilt: Dict, back_straightness: Dict, shoulder_alignment: Dict) -> str:
        """Generate feedback message based on posture analysis"""
        issues = []
        
        if head_tilt["status"] != "good":
            if head_tilt["angle"] > 0:
                issues.append("Keep your head up - avoid looking down")
            else:
                issues.append("Relax your head position - avoid tilting back")
        
        if back_straightness["status"] != "good":
            issues.append("Sit up straight - avoid slouching")
        
        if shoulder_alignment["status"] != "good":
            issues.append("Level your shoulders - keep them aligned")
        
        if not issues:
            return "Excellent posture! Keep it up."
        elif len(issues) == 1:
            return issues[0] + "."
        else:
            return "Focus on: " + ", ".join(issues) + "."
    
    def _error_response(self, error_msg: str) -> Dict[str, Any]:
        """Return error response"""
        return {
            "success": False,
            "error": error_msg,
            "posture_score": 0,
            "posture_status": "error",
            "feedback_message": "Unable to analyze posture",
            "landmarks_detected": False,
            "timestamp": self._get_timestamp()
        }
    
    def _no_pose_response(self) -> Dict[str, Any]:
        """Return response when no pose is detected"""
        return {
            "success": True,
            "posture_score": 0,
            "posture_status": "no_pose",
            "feedback_message": "Please ensure you're visible in the camera",
            "landmarks_detected": False,
            "timestamp": self._get_timestamp()
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def analyze_session(self, frame_analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze multiple frames for session-level insights
        
        Args:
            frame_analyses: List of frame analysis results
            
        Returns:
            Dict containing session-level posture analysis
        """
        if not frame_analyses:
            return {"error": "No frame analyses provided"}
        
        # Filter successful analyses
        successful_analyses = [analysis for analysis in frame_analyses if analysis.get("success", False)]
        
        if not successful_analyses:
            return {
                "session_score": 0,
                "session_status": "insufficient_data",
                "frame_count": len(frame_analyses),
                "successful_frames": 0,
                "average_scores": {},
                "recommendations": ["Ensure you're visible in the camera throughout the session"]
            }
        
        # Calculate averages
        avg_score = sum(analysis["posture_score"] for analysis in successful_analyses) / len(successful_analyses)
        
        # Calculate component averages
        avg_head_tilt = sum(analysis["details"]["head_tilt"]["score"] for analysis in successful_analyses) / len(successful_analyses)
        avg_back_straightness = sum(analysis["details"]["back_straightness"]["score"] for analysis in successful_analyses) / len(successful_analyses)
        avg_shoulder_alignment = sum(analysis["details"]["shoulder_alignment"]["score"] for analysis in successful_analyses) / len(successful_analyses)
        
        # Generate session recommendations
        recommendations = self._generate_session_recommendations(avg_head_tilt, avg_back_straightness, avg_shoulder_alignment)
        
        return {
            "session_score": round(avg_score, 1),
            "session_status": self._get_posture_status(avg_score),
            "frame_count": len(frame_analyses),
            "successful_frames": len(successful_analyses),
            "success_rate": round(len(successful_analyses) / len(frame_analyses) * 100, 1),
            "average_scores": {
                "head_tilt": round(avg_head_tilt, 1),
                "back_straightness": round(avg_back_straightness, 1),
                "shoulder_alignment": round(avg_shoulder_alignment, 1)
            },
            "recommendations": recommendations
        }
    
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


class BodyLanguageService:
    """Service for handling body language detection and storage"""
    
    def __init__(self):
        self.analyzer = PostureAnalyzer()
        logger.info("Body language service initialized")
    
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
            logger.info(f"Posture analysis completed for interview {interview_id}")
            
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

    async def get_session_posture_summary(self, interview_id: int) -> Dict[str, Any]:
        """Get posture summary for an interview session"""
        logger.info(f"Posture summary requested for interview {interview_id}")
        
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


# Alias for backward compatibility
BodyLanguageAnalyzer = PostureAnalyzer

# Global instance
body_language_service = BodyLanguageService()