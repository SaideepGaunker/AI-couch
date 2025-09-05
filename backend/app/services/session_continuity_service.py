"""
Session Continuity Service - Business logic for session cloning and practice-again functionality
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.models import InterviewSession, Question, PerformanceMetrics, User
from app.schemas.interview import (
    InterviewSessionCreate, SessionType, PracticeAgainRequest
)
from app.services.question_service import QuestionService
from app.crud.interview import create_interview_session, get_interview_session

logger = logging.getLogger(__name__)


class SessionContinuityService:
    """Service for managing session continuity, cloning, and practice-again functionality"""
    
    def __init__(self, db: Session):
        self.db = db
        self.question_service = QuestionService(db)
    
    def clone_session_for_practice(
        self,
        original_session_id: int,
        user_id: int,
        request_data: Optional[PracticeAgainRequest] = None
    ) -> Optional[InterviewSession]:
        """
        Clone a session for practice-again functionality
        Preserves settings but generates fresh questions
        """
        try:
            logger.info(f"Cloning session {original_session_id} for practice by user {user_id}")
            
            # Get original session
            original_session = get_interview_session(self.db, original_session_id)
            if not original_session:
                logger.error(f"Original session {original_session_id} not found")
                return None
            
            # Verify ownership
            if original_session.user_id != user_id:
                logger.error(f"User {user_id} does not own session {original_session_id}")
                return None
            
            # Determine difficulty for new session
            new_difficulty = original_session.difficulty_level
            if request_data and not request_data.keep_difficulty:
                # Use adaptive difficulty if not keeping original
                from app.services.difficulty_service import DifficultyService
                difficulty_service = DifficultyService(self.db)
                new_difficulty = difficulty_service.get_next_difficulty(user_id)
                logger.info(f"Using adaptive difficulty: {new_difficulty}")
            
            # Create session data based on original
            session_data = InterviewSessionCreate(
                session_type=SessionType(original_session.session_type),
                target_role=original_session.target_role,
                duration=original_session.duration,
                difficulty=new_difficulty,
                question_count=self._get_original_question_count(original_session_id),
                enable_video=True,  # Default values
                enable_audio=True
            )
            
            # Create new session with practice-again mode
            new_session = create_interview_session(
                self.db,
                user_id,
                session_data,
                difficulty_level=new_difficulty
            )
            
            # Set session continuity fields
            new_session.parent_session_id = original_session_id
            new_session.session_mode = "practice_again"
            new_session.resume_state = {
                "original_session_id": original_session_id,
                "cloned_at": datetime.utcnow().isoformat(),
                "generate_new_questions": request_data.generate_new_questions if request_data else True,
                "keep_difficulty": request_data.keep_difficulty if request_data else False
            }
            
            self.db.commit()
            self.db.refresh(new_session)
            
            logger.info(f"Successfully cloned session {original_session_id} to new session {new_session.id}")
            return new_session
            
        except Exception as e:
            logger.error(f"Error cloning session for practice: {str(e)}")
            self.db.rollback()
            return None
    
    def get_session_family(self, session_id: int, user_id: int) -> Dict[str, Any]:
        """
        Get complete session family tree (parent and all children)
        """
        try:
            logger.info(f"Getting session family for session {session_id}")
            
            # Get the session
            session = get_interview_session(self.db, session_id)
            if not session or session.user_id != user_id:
                logger.error(f"Session {session_id} not found or access denied")
                return {}
            
            # Find root session (original)
            root_session = session
            if session.parent_session_id:
                root_session = get_interview_session(self.db, session.parent_session_id)
                if not root_session:
                    root_session = session  # Fallback if parent not found
            
            # Get all child sessions
            child_sessions = self.db.query(InterviewSession).filter(
                and_(
                    InterviewSession.parent_session_id == root_session.id,
                    InterviewSession.user_id == user_id
                )
            ).order_by(InterviewSession.created_at).all()
            
            # Build family tree
            family_tree = {
                "root_session": {
                    "id": root_session.id,
                    "target_role": root_session.target_role,
                    "session_type": root_session.session_type,
                    "difficulty_level": root_session.difficulty_level,
                    "status": root_session.status,
                    "overall_score": root_session.overall_score,
                    "performance_score": root_session.performance_score,
                    "created_at": root_session.created_at.isoformat() if root_session.created_at else None,
                    "completed_at": root_session.completed_at.isoformat() if root_session.completed_at else None,
                    "session_mode": root_session.session_mode or "new"
                },
                "practice_sessions": [],
                "total_sessions": 1 + len(child_sessions),
                "total_practice_attempts": len(child_sessions)
            }
            
            # Add child sessions
            for child in child_sessions:
                family_tree["practice_sessions"].append({
                    "id": child.id,
                    "difficulty_level": child.difficulty_level,
                    "status": child.status,
                    "overall_score": child.overall_score,
                    "performance_score": child.performance_score,
                    "created_at": child.created_at.isoformat() if child.created_at else None,
                    "completed_at": child.completed_at.isoformat() if child.completed_at else None,
                    "session_mode": child.session_mode or "practice_again",
                    "resume_state": child.resume_state
                })
            
            logger.info(f"Retrieved session family with {family_tree['total_sessions']} sessions")
            return family_tree
            
        except Exception as e:
            logger.error(f"Error getting session family: {str(e)}")
            return {}
    
    def resume_session(
        self,
        session_id: int,
        user_id: int,
        resume_data: Dict[str, Any]
    ) -> bool:
        """
        Resume a paused session with state management
        """
        try:
            logger.info(f"Resuming session {session_id} for user {user_id}")
            
            # Get session
            session = get_interview_session(self.db, session_id)
            if not session or session.user_id != user_id:
                logger.error(f"Session {session_id} not found or access denied")
                return False
            
            if session.status != "paused":
                logger.error(f"Session {session_id} is not in paused state (current: {session.status})")
                return False
            
            # Update resume state
            current_resume_state = session.resume_state or {}
            current_resume_state.update({
                "resumed_at": datetime.utcnow().isoformat(),
                "resume_data": resume_data
            })
            
            session.resume_state = current_resume_state
            session.status = "active"
            
            self.db.commit()
            
            logger.info(f"Successfully resumed session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error resuming session: {str(e)}")
            self.db.rollback()
            return False
    
    def get_practice_history(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get user's practice history with session relationships
        """
        try:
            logger.info(f"Getting practice history for user {user_id}")
            
            # Get all sessions for user
            sessions = self.db.query(InterviewSession).filter(
                InterviewSession.user_id == user_id
            ).order_by(InterviewSession.created_at.desc()).limit(limit).all()
            
            practice_history = []
            
            for session in sessions:
                session_data = {
                    "id": session.id,
                    "target_role": session.target_role,
                    "session_type": session.session_type,
                    "difficulty_level": session.difficulty_level,
                    "status": session.status,
                    "overall_score": session.overall_score,
                    "performance_score": session.performance_score,
                    "created_at": session.created_at.isoformat() if session.created_at else None,
                    "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                    "session_mode": session.session_mode or "new",
                    "parent_session_id": session.parent_session_id,
                    "is_practice_session": session.parent_session_id is not None,
                    "can_practice_again": session.status == "completed"
                }
                
                # Add family information
                if session.parent_session_id:
                    session_data["original_session"] = session.parent_session_id
                else:
                    # Count practice attempts for this session
                    practice_count = self.db.query(InterviewSession).filter(
                        InterviewSession.parent_session_id == session.id
                    ).count()
                    session_data["practice_attempts"] = practice_count
                
                practice_history.append(session_data)
            
            logger.info(f"Retrieved {len(practice_history)} sessions in practice history")
            return practice_history
            
        except Exception as e:
            logger.error(f"Error getting practice history: {str(e)}")
            return []
    
    def get_session_performance_comparison(
        self,
        session_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Compare performance between original session and practice attempts
        """
        try:
            logger.info(f"Getting performance comparison for session {session_id}")
            
            # Get session family
            family = self.get_session_family(session_id, user_id)
            if not family:
                return {}
            
            root_session = family["root_session"]
            practice_sessions = family["practice_sessions"]
            
            # Calculate performance trends
            performance_data = {
                "original_performance": {
                    "overall_score": root_session["overall_score"] or 0,
                    "performance_score": root_session["performance_score"] or 0,
                    "difficulty_level": root_session["difficulty_level"]
                },
                "practice_attempts": [],
                "improvement_metrics": {
                    "best_overall_score": root_session["overall_score"] or 0,
                    "best_performance_score": root_session["performance_score"] or 0,
                    "average_improvement": 0,
                    "consistency_score": 0
                }
            }
            
            # Add practice session data
            practice_scores = []
            for practice in practice_sessions:
                if practice["status"] == "completed":
                    practice_data = {
                        "session_id": practice["id"],
                        "overall_score": practice["overall_score"] or 0,
                        "performance_score": practice["performance_score"] or 0,
                        "difficulty_level": practice["difficulty_level"],
                        "completed_at": practice["completed_at"]
                    }
                    performance_data["practice_attempts"].append(practice_data)
                    practice_scores.append(practice["performance_score"] or 0)
                    
                    # Update best scores
                    if practice["overall_score"] and practice["overall_score"] > performance_data["improvement_metrics"]["best_overall_score"]:
                        performance_data["improvement_metrics"]["best_overall_score"] = practice["overall_score"]
                    
                    if practice["performance_score"] and practice["performance_score"] > performance_data["improvement_metrics"]["best_performance_score"]:
                        performance_data["improvement_metrics"]["best_performance_score"] = practice["performance_score"]
            
            # Calculate improvement metrics
            if practice_scores:
                original_score = root_session["performance_score"] or 0
                avg_practice_score = sum(practice_scores) / len(practice_scores)
                performance_data["improvement_metrics"]["average_improvement"] = avg_practice_score - original_score
                
                # Calculate consistency (lower standard deviation = higher consistency)
                if len(practice_scores) > 1:
                    variance = sum((score - avg_practice_score) ** 2 for score in practice_scores) / len(practice_scores)
                    std_dev = variance ** 0.5
                    performance_data["improvement_metrics"]["consistency_score"] = max(0, 100 - std_dev)
                else:
                    performance_data["improvement_metrics"]["consistency_score"] = 100
            
            logger.info(f"Generated performance comparison for session family")
            return performance_data
            
        except Exception as e:
            logger.error(f"Error getting performance comparison: {str(e)}")
            return {}
    
    def _get_original_question_count(self, session_id: int) -> int:
        """Get the number of questions from the original session"""
        try:
            question_count = self.db.query(PerformanceMetrics).filter(
                PerformanceMetrics.session_id == session_id
            ).count()
            
            return max(question_count, 5)  # Default to 5 if no metrics found
            
        except Exception as e:
            logger.error(f"Error getting original question count: {str(e)}")
            return 5  # Default fallback
    
    def delete_session_family(self, session_id: int, user_id: int) -> bool:
        """
        Delete entire session family (original + all practice sessions)
        """
        try:
            logger.info(f"Deleting session family for session {session_id}")
            
            # Get session family
            family = self.get_session_family(session_id, user_id)
            if not family:
                return False
            
            root_session_id = family["root_session"]["id"]
            
            # Delete all child sessions first
            child_sessions = self.db.query(InterviewSession).filter(
                and_(
                    InterviewSession.parent_session_id == root_session_id,
                    InterviewSession.user_id == user_id
                )
            ).all()
            
            for child in child_sessions:
                # Delete performance metrics for child session
                self.db.query(PerformanceMetrics).filter(
                    PerformanceMetrics.session_id == child.id
                ).delete()
                
                # Delete child session
                self.db.delete(child)
            
            # Delete performance metrics for root session
            self.db.query(PerformanceMetrics).filter(
                PerformanceMetrics.session_id == root_session_id
            ).delete()
            
            # Delete root session
            root_session = get_interview_session(self.db, root_session_id)
            if root_session and root_session.user_id == user_id:
                self.db.delete(root_session)
            
            self.db.commit()
            
            logger.info(f"Successfully deleted session family for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting session family: {str(e)}")
            self.db.rollback()
            return False