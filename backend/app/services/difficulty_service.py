"""
Difficulty Service - Business logic for adaptive difficulty tracking
"""
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from app.db.models import InterviewSession, PerformanceMetrics, User
from app.schemas.interview import PerformanceTrend
from app.services.difficulty_mapping_service import DifficultyMappingService

logger = logging.getLogger(__name__)


class DifficultyService:
    """Service for managing adaptive difficulty calculation"""
    
    def __init__(self, db: Session):
        self.db = db
        
        # Use unified difficulty mapping service
        self.difficulty_mapping = DifficultyMappingService
        
        # Difficulty levels in order (for backward compatibility)
        self.difficulty_levels = ["easy", "medium", "hard", "expert"]
        
        # Weights for performance score calculation
        self.score_weights = {
            "content_quality": 0.5,
            "body_language": 0.3,
            "voice_analysis": 0.2
        }
    
    def calculate_performance_score(self, session_id: int) -> float:
        """
        Calculate performance score from body_language, voice_analysis, content_quality
        Weighted average: content_quality (50%), body_language (30%), voice_analysis (20%)
        """
        try:
            logger.info(f"Calculating performance score for session {session_id}")
            
            # Get all performance metrics for this session
            metrics = self.db.query(PerformanceMetrics).filter(
                PerformanceMetrics.session_id == session_id
            ).all()
            
            if not metrics:
                logger.warning(f"No performance metrics found for session {session_id}")
                # Return a low score for sessions without metrics - they likely didn't complete properly
                return 25.0  # Low score to reflect incomplete session
            
            # Filter out None values and calculate averages
            valid_content_scores = [m.content_quality_score for m in metrics if m.content_quality_score is not None]
            valid_body_scores = [m.body_language_score for m in metrics if m.body_language_score is not None]
            valid_voice_scores = [m.tone_confidence_score for m in metrics if m.tone_confidence_score is not None]
            
            # Calculate averages with more realistic defaults for missing data
            if valid_content_scores:
                avg_content = sum(valid_content_scores) / len(valid_content_scores)
            else:
                # If no content scores, this indicates a problem - use low score
                avg_content = 30.0
                logger.warning(f"No valid content scores for session {session_id}")
            
            if valid_body_scores:
                avg_body_language = sum(valid_body_scores) / len(valid_body_scores)
            else:
                # Default body language score when not available
                avg_body_language = 40.0
            
            if valid_voice_scores:
                avg_voice = sum(valid_voice_scores) / len(valid_voice_scores)
            else:
                # Default voice score when not available
                avg_voice = 40.0
            
            # Calculate weighted performance score
            performance_score = (
                avg_content * self.score_weights["content_quality"] +
                avg_body_language * self.score_weights["body_language"] +
                avg_voice * self.score_weights["voice_analysis"]
            )
            
            # Apply quality penalties for very low content scores (indicates poor answers)
            if avg_content < 30:
                performance_score *= 0.8  # 20% penalty for very poor content
                logger.info(f"Applied quality penalty for low content score: {avg_content}")
            elif avg_content < 40:
                performance_score *= 0.9  # 10% penalty for poor content
                logger.info(f"Applied minor quality penalty for content score: {avg_content}")
            
            # Ensure score is within 0-100 range
            performance_score = max(0, min(100, performance_score))
            
            logger.info(f"Performance score calculated: {performance_score} (content: {avg_content}, body: {avg_body_language}, voice: {avg_voice})")
            logger.info(f"Valid scores found - Content: {len(valid_content_scores)}, Body: {len(valid_body_scores)}, Voice: {len(valid_voice_scores)}")
            
            return round(performance_score, 2)
            
        except Exception as e:
            logger.error(f"Error calculating performance score: {str(e)}")
            return 25.0  # Return low score instead of neutral on error
    
    def get_next_difficulty(self, user_id: int, target_role: str = None, current_session_score: float = None) -> str:
        """
        Intelligent difficulty adjustment with 70% weight on current session and 30% on previous interviews:
        - Current session score gets 70% priority in difficulty calculation
        - Previous interviews (last 3-5 sessions) get 30% weight
        - Immediate adjustments for exceptional performance (>80 or <30)
        - Gradual adjustments for moderate performance using weighted scoring
        
        Args:
            user_id: User ID
            target_role: Specific role to track difficulty for (e.g., "Frontend Developer React")
            current_session_score: Score from the current/latest session (gets 70% weight)
        """
        try:
            logger.info(f"Determining next difficulty for user {user_id}, role: {target_role}, current score: {current_session_score}")
            
            # Build query for recent sessions (excluding current session if it's the latest)
            query = self.db.query(InterviewSession).filter(
                and_(
                    InterviewSession.user_id == user_id,
                    InterviewSession.status == "completed",
                    InterviewSession.performance_score.isnot(None)
                )
            )
            
            # Add role-specific filtering if target_role is provided
            if target_role:
                query = query.filter(InterviewSession.target_role == target_role)
                logger.info(f"Filtering sessions for specific role: {target_role}")
            
            # Get recent completed sessions with performance scores
            recent_sessions = query.order_by(desc(InterviewSession.completed_at)).limit(6).all()
            
            # If no current session score provided, use the latest session score
            if current_session_score is None and recent_sessions:
                current_session_score = recent_sessions[0].performance_score
                logger.info(f"Using latest session score as current: {current_session_score}")
            
            # Get current difficulty from most recent session or default
            current_difficulty = "medium"
            if recent_sessions:
                current_difficulty = recent_sessions[0].difficulty_level or "medium"
            
            logger.info(f"Current session score: {current_session_score}, current difficulty: {current_difficulty}")
            
            # Handle case where no sessions exist
            if not recent_sessions and current_session_score is None:
                logger.info(f"No sessions found for user {user_id}, using default medium difficulty")
                return "medium"
            
            # If we only have current session score, use it directly
            if current_session_score is not None:
                # Immediate adjustment for exceptional performance (more responsive thresholds)
                if current_session_score >= 75:
                    new_difficulty = self._increase_difficulty(current_difficulty)
                    logger.info(f"Excellent performance ({current_session_score}), immediately increasing difficulty: {current_difficulty} -> {new_difficulty}")
                    return new_difficulty
                elif current_session_score <= 35:
                    new_difficulty = self._decrease_difficulty(current_difficulty)
                    logger.info(f"Poor performance ({current_session_score}), immediately decreasing difficulty: {current_difficulty} -> {new_difficulty}")
                    return new_difficulty
            
            # Calculate weighted difficulty using 70% current + 30% previous sessions
            if current_session_score is not None and recent_sessions:
                # Get previous sessions (excluding current if it's in the list)
                previous_sessions = recent_sessions[1:4] if len(recent_sessions) > 1 else []
                
                if previous_sessions:
                    # Calculate average of previous sessions (30% weight)
                    previous_scores = [s.performance_score for s in previous_sessions]
                    previous_average = sum(previous_scores) / len(previous_scores)
                    
                    # Calculate weighted score: 70% current + 30% previous
                    weighted_score = (current_session_score * 0.7) + (previous_average * 0.3)
                    
                    logger.info(f"Weighted calculation: current({current_session_score}) * 0.7 + previous_avg({previous_average:.1f}) * 0.3 = {weighted_score:.1f}")
                else:
                    # Only current session available, use it with full weight
                    weighted_score = current_session_score
                    logger.info(f"Only current session available, using full weight: {weighted_score}")
                
                # Determine difficulty based on weighted score
                new_difficulty = self._calculate_difficulty_from_weighted_score(weighted_score, current_difficulty)
                logger.info(f"Calculated difficulty based on weighted score ({weighted_score:.1f}): {current_difficulty} -> {new_difficulty}")
                return new_difficulty
            
            # Fallback: use only current session score if available
            elif current_session_score is not None:
                new_difficulty = self.map_score_to_difficulty(current_session_score)
                logger.info(f"Using current session score only ({current_session_score}): {new_difficulty}")
                return new_difficulty
            
            # Final fallback: use most recent session
            elif recent_sessions:
                latest_score = recent_sessions[0].performance_score
                new_difficulty = self.map_score_to_difficulty(latest_score)
                logger.info(f"Using latest session score ({latest_score}): {new_difficulty}")
                return new_difficulty
            
            # Ultimate fallback
            logger.info("No valid scores found, using medium difficulty")
            return "medium"
                
        except Exception as e:
            logger.error(f"Error determining next difficulty: {str(e)}")
            return "medium"  # Safe default
    
    def _calculate_difficulty_from_weighted_score(self, weighted_score: float, current_difficulty: str) -> str:
        """Calculate difficulty adjustment based on weighted performance score with improved thresholds"""
        try:
            logger.info(f"Calculating difficulty adjustment: score={weighted_score}, current={current_difficulty}")
            
            # More responsive thresholds for better difficulty progression
            if weighted_score >= 80:
                # Excellent performance - definitely increase difficulty
                new_difficulty = self._increase_difficulty(current_difficulty)
                logger.info(f"Excellent performance ({weighted_score}) - increasing difficulty: {current_difficulty} -> {new_difficulty}")
                return new_difficulty
            elif weighted_score <= 35:
                # Poor performance - definitely decrease difficulty
                new_difficulty = self._decrease_difficulty(current_difficulty)
                logger.info(f"Poor performance ({weighted_score}) - decreasing difficulty: {current_difficulty} -> {new_difficulty}")
                return new_difficulty
            elif weighted_score >= 70:
                # Good performance - increase if not at highest levels
                if current_difficulty in ["easy", "medium"]:
                    new_difficulty = self._increase_difficulty(current_difficulty)
                    logger.info(f"Good performance ({weighted_score}) - increasing from {current_difficulty} to {new_difficulty}")
                    return new_difficulty
                else:
                    logger.info(f"Good performance ({weighted_score}) but already at high difficulty ({current_difficulty}) - maintaining")
                    return current_difficulty
            elif weighted_score <= 45:
                # Below average performance - decrease if not at lowest levels
                if current_difficulty in ["hard", "expert"]:
                    new_difficulty = self._decrease_difficulty(current_difficulty)
                    logger.info(f"Below average performance ({weighted_score}) - decreasing from {current_difficulty} to {new_difficulty}")
                    return new_difficulty
                else:
                    logger.info(f"Below average performance ({weighted_score}) but already at low difficulty ({current_difficulty}) - maintaining")
                    return current_difficulty
            else:
                # Average performance (45-70) - maintain current difficulty
                logger.info(f"Average performance ({weighted_score}) - maintaining difficulty: {current_difficulty}")
                return current_difficulty
                
        except Exception as e:
            logger.error(f"Error calculating difficulty from weighted score: {str(e)}")
            return current_difficulty
    
    def map_score_to_difficulty(self, score: float) -> str:
        """Map performance score to difficulty level with realistic thresholds"""
        logger.info(f"Mapping score {score} to difficulty level")
        
        if score < 30:
            difficulty = "easy"
        elif score < 50:
            difficulty = "medium"  
        elif score < 70:
            difficulty = "hard"
        else:
            difficulty = "expert"
            
        logger.info(f"Score {score} mapped to difficulty: {difficulty}")
        return difficulty
    
    def should_adjust_difficulty(self, user_id: int, current_difficulty: str, rolling_average: float) -> bool:
        """Check cooldown rules to prevent oscillation"""
        try:
            # Get last 2 sessions to check for recent difficulty changes
            last_two_sessions = self.db.query(InterviewSession).filter(
                and_(
                    InterviewSession.user_id == user_id,
                    InterviewSession.status == "completed"
                )
            ).order_by(desc(InterviewSession.completed_at)).limit(2).all()
            
            if len(last_two_sessions) < 2:
                return True  # No cooldown if we don't have enough history
            
            # Check if difficulty was changed in the last session
            prev_difficulty = last_two_sessions[1].difficulty_level or "medium"
            current_session_difficulty = last_two_sessions[0].difficulty_level or "medium"
            
            # If difficulty was already changed in the last session, apply cooldown
            if prev_difficulty != current_session_difficulty:
                logger.info(f"Difficulty was recently changed ({prev_difficulty} -> {current_session_difficulty}), applying cooldown")
                return False
            
            # Additional check: don't change difficulty if the change would be too frequent
            # Look at last 3 sessions for pattern of changes
            last_three_sessions = self.db.query(InterviewSession).filter(
                and_(
                    InterviewSession.user_id == user_id,
                    InterviewSession.status == "completed"
                )
            ).order_by(desc(InterviewSession.completed_at)).limit(3).all()
            
            if len(last_three_sessions) >= 3:
                difficulties = [s.difficulty_level or "medium" for s in last_three_sessions]
                # If all three are different, we're oscillating too much
                if len(set(difficulties)) == 3:
                    logger.info(f"Detected oscillation in difficulties {difficulties}, applying cooldown")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking difficulty adjustment cooldown: {str(e)}")
            return True  # Default to allowing adjustment if there's an error
    
    def _increase_difficulty(self, current_difficulty: str) -> str:
        """Increase difficulty level by one step"""
        try:
            current_index = self.difficulty_levels.index(current_difficulty)
            if current_index < len(self.difficulty_levels) - 1:
                return self.difficulty_levels[current_index + 1]
            else:
                return current_difficulty  # Already at max
        except ValueError:
            return "medium"  # Default if current difficulty is invalid
    
    def _decrease_difficulty(self, current_difficulty: str) -> str:
        """Decrease difficulty level by one step"""
        try:
            current_index = self.difficulty_levels.index(current_difficulty)
            if current_index > 0:
                return self.difficulty_levels[current_index - 1]
            else:
                return current_difficulty  # Already at min
        except ValueError:
            return "medium"  # Default if current difficulty is invalid
    
    def get_performance_trend(self, user_id: int, days: int = 30) -> PerformanceTrend:
        """Get performance trend data for user statistics"""
        try:
            # Get sessions from the last N days
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            sessions = self.db.query(InterviewSession).filter(
                and_(
                    InterviewSession.user_id == user_id,
                    InterviewSession.status == "completed",
                    InterviewSession.completed_at >= cutoff_date,
                    InterviewSession.performance_score.isnot(None)
                )
            ).order_by(InterviewSession.completed_at).all()
            
            if not sessions:
                return PerformanceTrend(
                    session_dates=[],
                    performance_scores=[],
                    difficulty_levels=[],
                    trend_direction="stable",
                    average_score=0.0
                )
            
            # Extract data for trend analysis
            session_dates = [s.completed_at.strftime("%Y-%m-%d") for s in sessions]
            performance_scores = [s.performance_score for s in sessions]
            difficulty_levels = [s.difficulty_level or "medium" for s in sessions]
            
            # Calculate average score
            average_score = sum(performance_scores) / len(performance_scores)
            
            # Determine trend direction
            trend_direction = self._calculate_trend_direction(performance_scores)
            
            return PerformanceTrend(
                session_dates=session_dates,
                performance_scores=performance_scores,
                difficulty_levels=difficulty_levels,
                trend_direction=trend_direction,
                average_score=round(average_score, 2)
            )
            
        except Exception as e:
            logger.error(f"Error getting performance trend: {str(e)}")
            return PerformanceTrend(
                session_dates=[],
                performance_scores=[],
                difficulty_levels=[],
                trend_direction="stable",
                average_score=0.0
            )
    
    def _calculate_trend_direction(self, scores: List[float]) -> str:
        """Calculate trend direction from performance scores"""
        if len(scores) < 2:
            return "stable"
        
        # Simple linear trend calculation
        # Compare first half with second half
        mid_point = len(scores) // 2
        first_half_avg = sum(scores[:mid_point]) / mid_point if mid_point > 0 else 0
        second_half_avg = sum(scores[mid_point:]) / (len(scores) - mid_point)
        
        difference = second_half_avg - first_half_avg
        
        # Use a threshold to determine significant change
        threshold = 5.0  # 5 point difference is considered significant
        
        if difference > threshold:
            return "improving"
        elif difference < -threshold:
            return "declining"
        else:
            return "stable"
    
    def get_difficulty_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive difficulty and performance statistics for a user with consistent labels"""
        try:
            # Get all completed sessions
            sessions = self.db.query(InterviewSession).filter(
                and_(
                    InterviewSession.user_id == user_id,
                    InterviewSession.status == "completed"
                )
            ).order_by(desc(InterviewSession.completed_at)).all()
            
            if not sessions:
                return {
                    "total_sessions": 0,
                    "current_difficulty": "medium",
                    "current_difficulty_label": self.difficulty_mapping.get_difficulty_label(2),
                    "next_difficulty": "medium",
                    "next_difficulty_label": self.difficulty_mapping.get_difficulty_label(2),
                    "average_performance": 0.0,
                    "difficulty_distribution": {},
                    "difficulty_distribution_labels": {},
                    "recent_trend": "stable",
                    "session_history": []
                }
            
            # Calculate statistics with consistent labeling
            total_sessions = len(sessions)
            current_difficulty = sessions[0].difficulty_level or "medium"
            next_difficulty = self.get_next_difficulty(user_id)
            
            # Get consistent labels for current and next difficulty
            current_difficulty_label = self.get_consistent_difficulty_label(current_difficulty)
            next_difficulty_label = self.get_consistent_difficulty_label(next_difficulty)
            
            # Calculate average performance for sessions with scores
            sessions_with_scores = [s for s in sessions if s.performance_score is not None]
            average_performance = (
                sum(s.performance_score for s in sessions_with_scores) / len(sessions_with_scores)
                if sessions_with_scores else 0.0
            )
            
            # Difficulty distribution with consistent labels
            difficulty_counts = {}
            difficulty_counts_labels = {}
            for session in sessions:
                diff = session.difficulty_level or "medium"
                diff_label = self.get_consistent_difficulty_label(diff)
                
                difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1
                difficulty_counts_labels[diff_label] = difficulty_counts_labels.get(diff_label, 0) + 1
            
            # Recent trend (last 5 sessions)
            recent_scores = [s.performance_score for s in sessions[:5] if s.performance_score is not None]
            recent_trend = self._calculate_trend_direction(recent_scores) if recent_scores else "stable"
            
            # Session history for debugging (last 10 sessions) with consistent labels
            session_history = []
            for session in sessions[:10]:
                session_difficulty_label = self.get_consistent_difficulty_label(session.difficulty_level or "medium")
                session_history.append({
                    "session_id": session.id,
                    "difficulty_level": session.difficulty_level,
                    "difficulty_label": session_difficulty_label,
                    "performance_score": session.performance_score,
                    "overall_score": session.overall_score,
                    "completed_at": session.completed_at.isoformat() if session.completed_at else None
                })
            
            return {
                "total_sessions": total_sessions,
                "current_difficulty": current_difficulty,
                "current_difficulty_label": current_difficulty_label,
                "next_difficulty": next_difficulty,
                "next_difficulty_label": next_difficulty_label,
                "average_performance": round(average_performance, 2),
                "difficulty_distribution": difficulty_counts,
                "difficulty_distribution_labels": difficulty_counts_labels,
                "recent_trend": recent_trend,
                "sessions_with_scores": len(sessions_with_scores),
                "session_history": session_history
            }
            
        except Exception as e:
            logger.error(f"Error getting difficulty statistics: {str(e)}")
            return {
                "total_sessions": 0,
                "current_difficulty": "medium",
                "next_difficulty": "medium",
                "average_performance": 0.0,
                "difficulty_distribution": {},
                "recent_trend": "stable",
                "session_history": []
            }
    
    def get_consistent_difficulty_label(self, difficulty_input) -> str:
        """
        Get consistent difficulty label using unified mapping service
        
        Args:
            difficulty_input: Any difficulty representation (int, string, etc.)
            
        Returns:
            Consistent display label (Easy, Medium, Hard, Expert)
        """
        try:
            internal_level = self.difficulty_mapping.normalize_difficulty_input(difficulty_input)
            return self.difficulty_mapping.get_difficulty_label(internal_level)
        except Exception as e:
            logger.error(f"Error getting consistent difficulty label: {e}")
            return "Medium"
    
    def normalize_session_difficulty(self, session: InterviewSession) -> Dict[str, str]:
        """
        Get normalized difficulty information for a session
        
        Args:
            session: InterviewSession object
            
        Returns:
            Dictionary with consistent difficulty labels
        """
        try:
            current_difficulty = session.difficulty_level or "medium"
            
            return {
                "current_difficulty_label": self.get_consistent_difficulty_label(current_difficulty),
                "current_difficulty_string": self.difficulty_mapping.get_string_level(
                    self.difficulty_mapping.normalize_difficulty_input(current_difficulty)
                ),
                "internal_level": self.difficulty_mapping.normalize_difficulty_input(current_difficulty)
            }
        except Exception as e:
            logger.error(f"Error normalizing session difficulty: {e}")
            return {
                "current_difficulty_label": "Medium",
                "current_difficulty_string": "medium",
                "internal_level": 2
            }