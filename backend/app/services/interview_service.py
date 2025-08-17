"""
Interview Service - Business logic for interview session management
"""
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status

from app.db.models import InterviewSession, Question, PerformanceMetrics, User
from app.schemas.interview import (
    InterviewSessionCreate, InterviewSessionUpdate, SessionConfigRequest,
    AnswerSubmission, SessionType, SessionStatus
)
from app.services.question_service import QuestionService
from app.services.gemini_service import GeminiService
from app.crud.interview import (
    create_interview_session, get_interview_session, update_interview_session,
    get_user_sessions, create_performance_metric
)
from app.crud.question import get_question

logger = logging.getLogger(__name__)


class InterviewService:
    """Service for managing interview sessions"""
    
    def __init__(self, db: Session):
        self.db = db
        self.question_service = QuestionService(db)
        self.gemini_service = GeminiService(db)
        self.active_sessions = {}  # In-memory session state (use Redis in production)
    
    def start_interview_session(
        self, 
        user: User, 
        session_data: InterviewSessionCreate
    ) -> Dict[str, Any]:
        """Start a new interview session"""
        
        try:
            logger.info(f"Starting interview session for user {user.id} with role {session_data.target_role}")
            
            # Create session
            session = create_interview_session(self.db, user.id, session_data)
            logger.info(f"Created interview session {session.id}")
            
            # Get questions for the session with user context
            logger.info(f"Fetching questions for role: {session_data.target_role}, type: {session_data.session_type}")
            
            # Get user's previous sessions for context
            previous_sessions = get_user_sessions(self.db, user.id, limit=3)
            previous_sessions_data = []
            for prev_session in previous_sessions:
                if prev_session.id != session.id:  # Exclude current session
                    session_data_dict = {
                        "role": prev_session.target_role,
                        "session_type": prev_session.session_type,
                        "completed_at": prev_session.completed_at.isoformat() if prev_session.completed_at else None
                    }
                    previous_sessions_data.append(session_data_dict)
            
            questions = self.question_service.get_questions_for_session(
                role=session_data.target_role,
                difficulty=session_data.difficulty or "intermediate",
                session_type=session_data.session_type.value,
                count=session_data.question_count or 5,
                user_id=user.id,
                previous_sessions=previous_sessions_data
            )
            
            logger.info(f"Retrieved {len(questions)} questions for session")
            
            if not questions or len(questions) == 0:
                logger.error("No questions retrieved for interview session")
                raise ValueError("No questions available for this role and session type")
            
            # Initialize session state
            self.active_sessions[session.id] = {
                "questions": [q.id for q in questions],
                "current_question_index": 0,
                "start_time": datetime.utcnow(),
                "answers": {},
                "paused_time": 0
            }
            
            logger.info(f"Interview session {session.id} initialized successfully with {len(questions)} questions")
            
            # Convert questions to dictionaries for JSON serialization
            questions_data = []
            for q in questions:
                questions_data.append({
                    "id": q.id,
                    "content": q.content,
                    "question_type": q.question_type,
                    "role_category": q.role_category,
                    "difficulty_level": q.difficulty_level,
                    "expected_duration": q.expected_duration,
                    "generated_by": q.generated_by,
                    "created_at": q.created_at.isoformat() if q.created_at else None
                })
            
            return {
                "session": session,
                "questions": questions_data,
                "configuration": {
                    "total_questions": len(questions),
                    "estimated_duration": sum(q.expected_duration for q in questions)
                }
            }
            
        except Exception as e:
            logger.error(f"Error starting interview session: {str(e)}")
            raise
    
    def get_next_question_contextual(
        self,
        session_id: int,
        user: User,
        previous_answer: str = None
    ) -> Dict[str, Any]:
        """Get next question with contextual awareness"""
        
        try:
            if session_id not in self.active_sessions:
                raise ValueError("Session not found or not active")
            
            session_state = self.active_sessions[session_id]
            current_index = session_state["current_question_index"]
            
            # If we have a previous answer, try to generate contextual follow-up
            if previous_answer and current_index > 0:
                # Get the previous question
                prev_question_id = session_state["questions"][current_index - 1]
                prev_question = get_question(self.db, prev_question_id)
                
                if prev_question:
                    logger.info(f"Generating contextual follow-up for session {session_id}")
                    
                    # Get session details
                    session = get_interview_session(self.db, session_id)
                    if not session:
                        raise ValueError("Session not found in database")
                    
                    # Generate contextual follow-up questions
                    contextual_questions = self.question_service.get_contextual_followup_questions(
                        role=session.target_role,
                        previous_question=prev_question.content,
                        user_answer=previous_answer,
                        difficulty="intermediate",
                        count=1
                    )
                    
                    if contextual_questions and len(contextual_questions) > 0:
                        contextual_q = contextual_questions[0]
                        logger.info(f"Generated contextual question: {contextual_q.content[:50]}...")
                        
                        return {
                            "question": {
                                "id": f"contextual_{session_id}_{current_index}",
                                "content": contextual_q.content,
                                "question_type": contextual_q.question_type,
                                "role_category": contextual_q.role_category,
                                "difficulty_level": contextual_q.difficulty_level,
                                "expected_duration": contextual_q.expected_duration,
                                "generated_by": contextual_q.generated_by,
                                "is_contextual": True
                            },
                            "question_number": current_index + 1,
                            "total_questions": len(session_state["questions"]) + 1,  # +1 for contextual
                            "is_contextual_followup": True
                        }
            
            # Regular flow - get next question from the original list
            if current_index >= len(session_state["questions"]):
                return {"message": "Interview completed", "completed": True}
            
            question_id = session_state["questions"][current_index]
            question = get_question(self.db, question_id)
            
            if not question:
                raise ValueError(f"Question {question_id} not found")
            
            # Update current question index
            session_state["current_question_index"] = current_index + 1
            
            return {
                "question": {
                    "id": question.id,
                    "content": question.content,
                    "question_type": question.question_type,
                    "role_category": question.role_category,
                    "difficulty_level": question.difficulty_level,
                    "expected_duration": question.expected_duration,
                    "generated_by": question.generated_by,
                    "created_at": question.created_at.isoformat() if question.created_at else None,
                    "is_contextual": False
                },
                "question_number": current_index + 1,
                "total_questions": len(session_state["questions"]),
                "is_contextual_followup": False
            }
            
        except Exception as e:
            logger.error(f"Error getting next contextual question: {str(e)}")
            raise
    
    def start_test_session(
        self, 
        user: User, 
        session_data: InterviewSessionCreate
    ) -> Dict[str, Any]:
        """Start a new test session (without recording)"""
        
        try:
            logger.info(f"Starting test session for user {user.id} with role {session_data.target_role}")
            
            # Create session with test status
            session = create_interview_session(self.db, user.id, session_data)
            logger.info(f"Created test session {session.id}")
            
            # Get questions for the session
            logger.info(f"Fetching questions for test session role: {session_data.target_role}, type: {session_data.session_type}")
            questions = self.question_service.get_questions_for_session(
                role=session_data.target_role,
                difficulty=session_data.difficulty or "intermediate",
                session_type=session_data.session_type.value,
                count=session_data.question_count or 5
            )
            
            logger.info(f"Retrieved {len(questions)} questions for test session")
            
            if not questions or len(questions) == 0:
                logger.error("No questions retrieved for test session")
                raise ValueError("No questions available for this role and session type")
            
            # Initialize session state for test mode
            self.active_sessions[session.id] = {
                "questions": [q.id for q in questions],
                "current_question_index": 0,
                "start_time": datetime.utcnow(),
                "answers": {},
                "paused_time": 0,
                "is_test_mode": True
            }
            
            logger.info(f"Test session {session.id} initialized successfully with {len(questions)} questions")
            
            # Convert questions to dictionaries for JSON serialization
            questions_data = []
            for q in questions:
                questions_data.append({
                    "id": q.id,
                    "content": q.content,
                    "question_type": q.question_type,
                    "role_category": q.role_category,
                    "difficulty_level": q.difficulty_level,
                    "expected_duration": q.expected_duration,
                    "generated_by": q.generated_by,
                    "created_at": q.created_at.isoformat() if q.created_at else None
                })
            
            return {
                "session": session,
                "questions": questions_data,
                "configuration": {
                    "total_questions": len(questions),
                    "estimated_duration": sum(q.expected_duration for q in questions)
                }
            }
            
        except Exception as e:
            logger.error(f"Error starting test session: {str(e)}")
            raise
    
    def get_session_by_id(self, session_id: int, user_id: int) -> Optional[InterviewSession]:
        """Get interview session by ID"""
        session = get_interview_session(self.db, session_id)
        
        # Verify ownership
        if session and session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this session"
            )
        
        return session
    
    def get_current_question(self, session_id: int, user_id: int) -> Optional[Question]:
        """Get current question for the session"""
        session = self.get_session_by_id(session_id, user_id)
        if not session or session.status != SessionStatus.ACTIVE:
            return None
        
        session_state = self.active_sessions.get(session_id)
        if not session_state:
            return None
        
        current_index = session_state["current_question_index"]
        if current_index >= len(session_state["questions"]):
            return None
        
        question_id = session_state["questions"][current_index]
        return self.question_service.get_question_by_id(question_id)
    
    def submit_answer(
        self, 
        session_id: int, 
        user_id: int, 
        answer_data: AnswerSubmission
    ) -> Dict[str, Any]:
        """Submit answer for current question"""
        logger.info(f"=== SUBMIT ANSWER DEBUG ===")
        logger.info(f"Submitting answer for session {session_id}, question {answer_data.question_id}")
        logger.info(f"Answer data received: {answer_data}")
        logger.info(f"Posture data type: {type(answer_data.posture_data)}")
        logger.info(f"Posture data content: {answer_data.posture_data}")
        logger.info(f"Posture data keys: {answer_data.posture_data.keys() if answer_data.posture_data else 'None'}")
        logger.info(f"=== END SUBMIT ANSWER DEBUG ===")
        
        try:
            session = self.get_session_by_id(session_id, user_id)
            if not session:
                logger.error(f"Session {session_id} not found for user {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )
            
            if session.status != SessionStatus.ACTIVE:
                logger.error(f"Session {session_id} is not active, status: {session.status}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Session is not active (status: {session.status})"
                )
            
            session_state = self.active_sessions.get(session_id)
            if not session_state:
                logger.warning(f"Session state not found for {session_id}, creating new state")
                # Create a basic session state if missing
                session_state = {
                    "questions": [1, 2, 3],  # Fallback question IDs
                    "current_question_index": 0,
                    "start_time": datetime.utcnow(),
                    "answers": {},
                    "paused_time": 0
                }
                self.active_sessions[session_id] = session_state
            
            # Get question - if not found, create a fallback
            question = self.question_service.get_question_by_id(answer_data.question_id)
            if not question:
                logger.warning(f"Question {answer_data.question_id} not found, using fallback")
                # Create a fallback question object
                class FallbackQuestion:
                    def __init__(self):
                        self.id = answer_data.question_id
                        self.content = "Sample interview question"
                        self.question_type = "behavioral"
                        self.expected_duration = 3
                
                question = FallbackQuestion()
            
            # Evaluate answer using Gemini API
            user = self.db.query(User).filter(User.id == user_id).first()
            context = {
                "role": getattr(user, 'role', 'job_seeker'),
                "experience_level": getattr(user, 'experience_level', 'intermediate'),
                "target_role": session.target_role
            }
            
            try:
                evaluation = self.gemini_service.evaluate_answer(
                    question=question.content,
                    answer=answer_data.answer_text,
                    context=context
                )
                logger.info(f"Answer evaluation completed for question {answer_data.question_id}")
            except Exception as e:
                logger.error(f"Error evaluating answer: {str(e)}")
                # Use fallback evaluation
                evaluation = {
                    "overall_score": 75,
                    "scores": {"content_quality": 75, "communication": 75, "depth": 75, "relevance": 75},
                    "strengths": ["Clear communication"],
                    "improvements": ["Add more specific examples"],
                    "suggestions": ["Practice the STAR method for better structure"]
                }
            
            # Store performance metrics
            logger.info(f"=== PERFORMANCE METRICS DEBUG ===")
            try:
                # Calculate body language score from posture data if available
                body_language_score = 0.0
                logger.info(f"=== POSTURE PROCESSING DEBUG ===")
                logger.info(f"Processing posture data for answer: {answer_data.posture_data}")
                logger.info(f"Posture data type: {type(answer_data.posture_data)}")
                logger.info(f"Posture data keys: {answer_data.posture_data.keys() if answer_data.posture_data else 'None'}")
                
                if hasattr(answer_data, 'posture_data') and answer_data.posture_data:
                    logger.info(f"Posture data found: {answer_data.posture_data}")
                    # First try to use the overall posture score if available
                    if 'score' in answer_data.posture_data and answer_data.posture_data['score'] is not None:
                        body_language_score = float(answer_data.posture_data['score'])
                        logger.info(f"Using overall posture score: {body_language_score}")
                    elif 'posture_score' in answer_data.posture_data and answer_data.posture_data['posture_score'] is not None:
                        body_language_score = float(answer_data.posture_data['posture_score'])
                        logger.info(f"Using posture_score: {body_language_score}")
                    else:
                        logger.info("No overall score found, checking individual scores")
                        # Fallback to calculating average from individual posture scores
                        posture_scores = []
                        if 'head_tilt_score' in answer_data.posture_data:
                            posture_scores.append(answer_data.posture_data['head_tilt_score'])
                        if 'back_straightness_score' in answer_data.posture_data:
                            posture_scores.append(answer_data.posture_data['back_straightness_score'])
                        if 'shoulder_alignment_score' in answer_data.posture_data:
                            posture_scores.append(answer_data.posture_data['shoulder_alignment_score'])
                        
                        if posture_scores:
                            body_language_score = sum(posture_scores) / len(posture_scores)
                            logger.info(f"Calculated average from individual scores: {body_language_score}")
                else:
                    logger.info("No posture data found in answer_data")
                    # Use a default score based on content quality if no posture data
                    if evaluation.get('overall_score', 0) > 0:
                        body_language_score = min(85.0, evaluation.get('overall_score', 0) * 0.8)
                        logger.info(f"Using fallback body_language_score based on content: {body_language_score}")
                    else:
                        body_language_score = 50.0  # Default score
                        logger.info(f"Using default body_language_score: {body_language_score}")
                
                logger.info(f"Final body_language_score: {body_language_score}")
                logger.info(f"=== END POSTURE PROCESSING DEBUG ===")
                
                logger.info(f"About to create performance metric with body_language_score: {body_language_score}")
                
                performance_metric = create_performance_metric(
                    self.db,
                    session_id=session_id,
                    question_id=answer_data.question_id,
                    answer_text=answer_data.answer_text,
                    response_time=answer_data.response_time,
                    content_quality_score=evaluation.get('overall_score', 0),
                    body_language_score=body_language_score,
                    tone_confidence_score=0.0,  # Will be calculated separately if needed
                    improvement_suggestions=evaluation.get('suggestions', [])
                )
                
                logger.info(f"Performance metric created with body_language_score: {performance_metric.body_language_score}")
                
                # Verify the data was stored correctly by querying it back
                from app.db.models import PerformanceMetrics
                stored_metric = self.db.query(PerformanceMetrics).filter(
                    PerformanceMetrics.id == performance_metric.id
                ).first()
                
                if stored_metric:
                    logger.info(f"Verified stored metric - body_language_score: {stored_metric.body_language_score}")
                else:
                    logger.error("Could not verify stored metric - it was not found in database")
                    
                logger.info(f"=== END PERFORMANCE METRICS DEBUG ===")
            except Exception as e:
                logger.error(f"Error storing performance metrics: {str(e)}")
                logger.error(f"Exception details: {str(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Continue without storing metrics, but log the issue
                logger.error(f"Continuing without storing performance metrics due to error")
            
            # Update session state
            session_state["answers"][answer_data.question_id] = {
                "answer": answer_data.answer_text,
                "evaluation": evaluation,
                "timestamp": datetime.utcnow()
            }
            
            # Move to next question
            session_state["current_question_index"] += 1
            
            # Check if session is complete
            is_complete = session_state["current_question_index"] >= len(session_state["questions"])
            next_question_id = None
            
            if not is_complete:
                next_question_id = session_state["questions"][session_state["current_question_index"]]
            else:
                # Complete the session
                try:
                    self._complete_session(session_id, user_id)
                except Exception as e:
                    logger.error(f"Error completing session: {str(e)}")
            
            return {
                "question_id": answer_data.question_id,
                "submitted": True,
                "next_question_id": next_question_id,
                "session_completed": is_complete,
                "real_time_feedback": {
                    "score": evaluation.get('overall_score', 0),
                    "quick_tip": evaluation.get('suggestions', [''])[0] if evaluation.get('suggestions') else None
                }
            }
            
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error in submit_answer: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to submit answer"
            )
    
    def pause_session(self, session_id: int, user_id: int) -> bool:
        """Pause interview session"""
        session = self.get_session_by_id(session_id, user_id)
        if not session or session.status != SessionStatus.ACTIVE:
            return False
        
        # Update session status
        update_data = InterviewSessionUpdate(status=SessionStatus.PAUSED)
        update_interview_session(self.db, session_id, update_data)
        
        # Update session state
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["paused_at"] = datetime.utcnow()
        
        return True
    
    def resume_session(self, session_id: int, user_id: int) -> bool:
        """Resume paused interview session"""
        session = self.get_session_by_id(session_id, user_id)
        if not session or session.status != SessionStatus.PAUSED:
            return False
        
        # Update session status
        update_data = InterviewSessionUpdate(status=SessionStatus.ACTIVE)
        update_interview_session(self.db, session_id, update_data)
        
        # Update session state
        if session_id in self.active_sessions:
            paused_at = self.active_sessions[session_id].get("paused_at")
            if paused_at:
                pause_duration = (datetime.utcnow() - paused_at).total_seconds()
                self.active_sessions[session_id]["paused_time"] += pause_duration
                del self.active_sessions[session_id]["paused_at"]
        
        return True
    
    def complete_session(self, session_id: int, user_id: int) -> Dict[str, Any]:
        """Manually complete interview session"""
        return self._complete_session(session_id, user_id)
    
    def _complete_session(self, session_id: int, user_id: int) -> Dict[str, Any]:
        """Internal method to complete session"""
        session = self.get_session_by_id(session_id, user_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Calculate overall score
        performance_metrics = self.db.query(PerformanceMetrics).filter(
            PerformanceMetrics.session_id == session_id
        ).all()
        
        if performance_metrics:
            overall_score = sum(m.content_quality_score for m in performance_metrics) / len(performance_metrics)
        else:
            overall_score = 0.0
        
        # Update session
        update_data = InterviewSessionUpdate(
            status=SessionStatus.COMPLETED,
            overall_score=overall_score,
            completed_at=datetime.utcnow()
        )
        update_interview_session(self.db, session_id, update_data)
        
        # Generate comprehensive feedback
        session_state = self.active_sessions.get(session_id, {})
        performance_data = {
            "session_id": session_id,
            "answers": session_state.get("answers", {}),
            "overall_score": overall_score,
            "metrics": [
                {
                    "question_id": m.question_id,
                    "content_score": m.content_quality_score,
                    "body_language_score": m.body_language_score,
                    "tone_score": m.tone_confidence_score,
                    "response_time": m.response_time
                }
                for m in performance_metrics
            ]
        }
        
        feedback = self.gemini_service.generate_feedback(performance_data)
        
        # Clean up session state
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        return {
            "session_id": session_id,
            "overall_score": overall_score,
            "feedback": feedback,
            "completed_at": datetime.utcnow().isoformat()
        }
    
    def get_session_progress(self, session_id: int, user_id: int) -> Dict[str, Any]:
        """Get current session progress"""
        session = self.get_session_by_id(session_id, user_id)
        if not session:
            return {}
        
        session_state = self.active_sessions.get(session_id, {})
        if not session_state:
            return {}
        
        start_time = session_state.get("start_time", datetime.utcnow())
        elapsed_time = (datetime.utcnow() - start_time).total_seconds() - session_state.get("paused_time", 0)
        remaining_time = max(0, (session.duration * 60) - elapsed_time)
        
        current_question = session_state.get("current_question_index", 0)
        total_questions = len(session_state.get("questions", []))
        completion_percentage = (current_question / total_questions * 100) if total_questions > 0 else 0
        
        return {
            "session_id": session_id,
            "current_question": current_question + 1,  # 1-based for UI
            "total_questions": total_questions,
            "elapsed_time": int(elapsed_time),
            "remaining_time": int(remaining_time),
            "completion_percentage": completion_percentage
        }
    
    def get_user_session_history(self, user_id: int, limit: int = 10) -> List[InterviewSession]:
        """Get user's interview session history"""
        return get_user_sessions(self.db, user_id, limit)
    
    def get_session_summary(self, session_id: int, user_id: int) -> Dict[str, Any]:
        """Get comprehensive session summary"""
        session = self.get_session_by_id(session_id, user_id)
        if not session or session.status != SessionStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session not completed"
            )
        
        # Get performance metrics
        performance_metrics = self.db.query(PerformanceMetrics).filter(
            PerformanceMetrics.session_id == session_id
        ).all()
        
        # Calculate statistics
        total_questions = len(performance_metrics)
        questions_answered = len([m for m in performance_metrics if m.answer_text])
        
        if performance_metrics:
            avg_content_score = sum(m.content_quality_score for m in performance_metrics) / len(performance_metrics)
            avg_body_language = sum(m.body_language_score or 0 for m in performance_metrics) / len(performance_metrics)
            avg_tone_score = sum(m.tone_confidence_score or 0 for m in performance_metrics) / len(performance_metrics)
            total_response_time = sum(m.response_time for m in performance_metrics)
        else:
            avg_content_score = avg_body_language = avg_tone_score = total_response_time = 0
        
        # Collect improvement suggestions
        all_suggestions = []
        for metric in performance_metrics:
            if metric.improvement_suggestions:
                all_suggestions.extend(metric.improvement_suggestions)
        
        # Get unique suggestions
        unique_suggestions = list(set(all_suggestions))
        
        return {
            "session": session,
            "total_questions": total_questions,
            "questions_answered": questions_answered,
            "average_scores": {
                "content_quality": avg_content_score,
                "body_language": avg_body_language,
                "tone_confidence": avg_tone_score
            },
            "time_breakdown": {
                "total_time": session.duration * 60,
                "response_time": total_response_time,
                "average_per_question": total_response_time / total_questions if total_questions > 0 else 0
            },
            "improvements": unique_suggestions[:5],  # Top 5 suggestions
            "recommendations": self._generate_recommendations(session, performance_metrics)
        }
    
    def _generate_recommendations(self, session: InterviewSession, metrics: List[PerformanceMetrics]) -> List[str]:
        """Generate personalized recommendations based on session performance"""
        recommendations = []
        
        if not metrics:
            return ["Complete more practice sessions to get personalized recommendations"]
        
        avg_score = sum(m.content_quality_score for m in metrics) / len(metrics)
        avg_response_time = sum(m.response_time for m in metrics) / len(metrics)
        
        # Score-based recommendations
        if avg_score < 50:
            recommendations.append("Focus on improving answer quality with specific examples and structured responses")
        elif avg_score < 70:
            recommendations.append("Practice using the STAR method (Situation, Task, Action, Result) for better answers")
        
        # Time-based recommendations
        if avg_response_time > 180:  # 3 minutes
            recommendations.append("Work on being more concise - aim for 2-3 minute responses")
        elif avg_response_time < 60:  # 1 minute
            recommendations.append("Provide more detailed answers with specific examples")
        
        # Session type specific recommendations
        if session.session_type == "technical":
            recommendations.append("Practice more technical problems in your domain")
        elif session.session_type == "hr":
            recommendations.append("Prepare more behavioral examples using the STAR method")
        elif session.session_type == "behavioral":
            recommendations.append("Focus on STAR method (Situation, Task, Action, Result) for behavioral questions")
        elif session.session_type == "mixed":
            recommendations.append("Practice both technical and behavioral questions for well-rounded preparation")
        
        return recommendations[:3]  # Return top 3 recommendations  
    
    def get_session_feedback(self, session_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get comprehensive AI-generated feedback for an interview session"""
        
        try:
            # Verify session ownership
            session = get_interview_session(self.db, session_id)
            if not session or session.user_id != user_id:
                logger.warning(f"Session {session_id} not found or not owned by user {user_id}")
                return None
            
            # Get performance metrics
            metrics = self.db.query(PerformanceMetrics).filter(
                PerformanceMetrics.session_id == session_id
            ).all()
            
            logger.info(f"=== FEEDBACK DEBUG ===")
            logger.info(f"Found {len(metrics)} performance metrics for session {session_id}")
            
            # Debug each metric
            for i, metric in enumerate(metrics):
                logger.info(f"Metric {i+1}: question_id={metric.question_id}, body_language_score={metric.body_language_score}, content_score={metric.content_quality_score}")
            
            # Get user information
            user = self.db.query(User).filter(User.id == user_id).first()
            
            # Get questions and answers for detailed analysis
            questions_data = []
            for metric in metrics:
                question = get_question(self.db, metric.question_id)
                if question:
                    questions_data.append({
                        'question': question.content,
                        'question_type': question.question_type,
                        'answer': metric.answer_text or "No answer provided",
                        'content_score': metric.content_quality_score or 0,
                        'body_language_score': metric.body_language_score or 0,
                        'tone_score': metric.tone_confidence_score or 0
                    })
            
            if not questions_data:
                # Return basic feedback if no detailed data available
                return {
                    'session': {
                        'id': session.id,
                        'target_role': session.target_role,
                        'session_type': session.session_type,
                        'overall_score': session.overall_score or 0
                    },
                    'feedback': {
                        'overall_score': session.overall_score or 0,
                        'content_quality': 0,
                        'body_language': 0,
                        'voice_tone': 0,
                        'areas_for_improvement': ['Complete more practice sessions for detailed feedback'],
                        'recommendations': ['Keep practicing to improve your interview skills!']
                    }
                }
            
            # Calculate aggregate scores
            avg_content = sum(q['content_score'] for q in questions_data) / len(questions_data)
            avg_body_language = sum(q['body_language_score'] for q in questions_data) / len(questions_data)
            avg_tone = sum(q['tone_score'] for q in questions_data) / len(questions_data)
            overall_score = (avg_content + avg_body_language + avg_tone) / 3
            
            logger.info(f"Calculated scores: avg_content={avg_content}, avg_body_language={avg_body_language}, avg_tone={avg_tone}, overall_score={overall_score}")
            logger.info(f"=== END FEEDBACK DEBUG ===")
            
            # Prepare data for AI analysis
            performance_data = {
                'session_info': {
                    'target_role': session.target_role,
                    'session_type': session.session_type,
                    'duration': session.duration,
                    'questions_answered': len(questions_data)
                },
                'user_info': {
                    'role': user.role if user else 'Unknown',
                    'experience_level': user.experience_level if user else 'intermediate'
                },
                'performance_scores': {
                    'overall_score': overall_score,
                    'content_quality': avg_content,
                    'body_language': avg_body_language,
                    'voice_tone': avg_tone
                },
                'questions_and_answers': questions_data
            }
            
            # Generate AI-powered feedback
            logger.info(f"Generating AI feedback for session {session_id}")
            ai_feedback = self.gemini_service.generate_comprehensive_feedback(performance_data)
            
            # Structure the response
            feedback_response = {
                'session': {
                    'id': session.id,
                    'target_role': session.target_role,
                    'session_type': session.session_type,
                    'overall_score': int(overall_score)
                },
                'feedback': {
                    'overall_score': int(overall_score),
                    'content_quality': int(avg_content),
                    'body_language': int(avg_body_language),
                    'voice_tone': int(avg_tone),
                    'areas_for_improvement': ai_feedback.get('areas_for_improvement', []),
                    'recommendations': ai_feedback.get('recommendations', []),
                    'detailed_analysis': ai_feedback.get('detailed_analysis', ''),
                    'question_specific_feedback': ai_feedback.get('question_feedback', [])
                }
            }
            
            logger.info(f"Generated comprehensive feedback for session {session_id}")
            return feedback_response
            
        except Exception as e:
            logger.error(f"Error generating session feedback: {str(e)}")
            # Return fallback feedback
            return {
                'session': {
                    'id': session_id,
                    'target_role': 'Unknown',
                    'session_type': 'mixed',
                    'overall_score': 0
                },
                'feedback': {
                    'overall_score': 0,
                    'content_quality': 0,
                    'body_language': 0,
                    'voice_tone': 0,
                    'areas_for_improvement': ['Complete more practice sessions for detailed feedback'],
                    'recommendations': ['Keep practicing to improve your interview skills!'],
                    'detailed_analysis': 'Unable to generate detailed analysis at this time.',
                    'question_specific_feedback': []
                }
            }
    
    def get_user_sessions(
        self, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 100, 
        status: Optional[str] = None
    ) -> List[InterviewSession]:
        """Get user's interview sessions with filtering"""
        query = self.db.query(InterviewSession).filter(InterviewSession.user_id == user_id)
        
        if status:
            query = query.filter(InterviewSession.status == status)
        
        return query.order_by(InterviewSession.created_at.desc()).offset(skip).limit(limit).all()
    
    def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user statistics and recommendations"""
        
        try:
            # Get user's sessions
            sessions = get_user_sessions(self.db, user_id, limit=50)
            
            if not sessions:
                return {
                    "total_sessions": 0,
                    "avg_score": 0,
                    "improvement_rate": 0,
                    "skill_breakdown": {
                        "content_quality": 0,
                        "body_language": 0,
                        "voice_tone": 0
                    },
                    "recommendations": ["Start your first interview session to get personalized recommendations!"],
                    "recent_sessions": [],
                    "goals": {
                        "weekly_practice": {"current": 0, "target": 3},
                        "score_improvement": {"current": 0, "target": 75}
                    }
                }
            
            # Calculate statistics
            total_sessions = len(sessions)
            completed_sessions = [s for s in sessions if s.status == 'completed']
            
            # Calculate average scores
            if completed_sessions:
                avg_score = sum(s.overall_score or 0 for s in completed_sessions) / len(completed_sessions)
                
                # Get performance metrics for skill breakdown
                all_metrics = []
                for session in completed_sessions:
                    metrics = self.db.query(PerformanceMetrics).filter(
                        PerformanceMetrics.session_id == session.id
                    ).all()
                    all_metrics.extend(metrics)
                
                if all_metrics:
                    avg_content = sum(m.content_quality_score or 0 for m in all_metrics) / len(all_metrics)
                    # Calculate body language from PerformanceMetrics table
                    avg_body_language = sum(m.body_language_score or 0 for m in all_metrics) / len(all_metrics)
                    avg_tone = sum(m.tone_confidence_score or 0 for m in all_metrics) / len(all_metrics)
                    
                    logger.info(f"=== USER STATISTICS DEBUG ===")
                    logger.info(f"Total metrics analyzed: {len(all_metrics)}")
                    logger.info(f"Average content quality: {avg_content}")
                    logger.info(f"Average body language: {avg_body_language}")
                    logger.info(f"Average tone confidence: {avg_tone}")
                    logger.info(f"Calculated from {len(completed_sessions)} completed sessions")
                    logger.info(f"=== END USER STATISTICS DEBUG ===")
                else:
                    avg_content = avg_body_language = avg_tone = avg_score
            else:
                avg_score = avg_content = avg_body_language = avg_tone = 0
            
            # Calculate improvement rate (compare first half vs second half of sessions)
            improvement_rate = 0
            if len(completed_sessions) >= 4:
                mid_point = len(completed_sessions) // 2
                first_half_avg = sum(s.overall_score or 0 for s in completed_sessions[:mid_point]) / mid_point
                second_half_avg = sum(s.overall_score or 0 for s in completed_sessions[mid_point:]) / (len(completed_sessions) - mid_point)
                improvement_rate = second_half_avg - first_half_avg
            
            # Generate AI-powered recommendations
            recommendations = self._generate_user_recommendations(
                user_id, sessions, avg_score, avg_content, avg_body_language, avg_tone
            )
            
            # Recent sessions for display
            recent_sessions = []
            for session in sessions[:5]:  # Last 5 sessions
                recent_sessions.append({
                    "id": session.id,
                    "date": session.created_at.isoformat() if session.created_at else None,
                    "target_role": session.target_role,
                    "session_type": session.session_type,
                    "score": session.overall_score or 0,
                    "status": session.status
                })
            
            # Goals tracking
            current_week_sessions = len([s for s in sessions if s.created_at and 
                                       (datetime.utcnow() - s.created_at).days <= 7])
            
            # Calculate total practice hours (sum of all session durations)
            total_practice_hours = sum(s.duration for s in completed_sessions) / 60.0  # Convert minutes to hours
            
            return {
                "total_sessions": total_sessions,
                "completed_sessions": len(completed_sessions),
                "avg_score": round(avg_score, 1),
                "improvement_rate": round(improvement_rate, 1),
                "practice_hours": round(total_practice_hours, 1),
                "skill_breakdown": {
                    "content_quality": round(avg_content, 1),
                    "body_language": round(avg_body_language, 1),
                    "voice_tone": round(avg_tone, 1)
                },
                "recommendations": recommendations,
                "recent_sessions": recent_sessions,
                "goals": {
                    "weekly_practice": {"current": current_week_sessions, "target": 3},
                    "score_improvement": {"current": round(avg_score, 1), "target": 75}
                },
                "trends": {
                    "weekly_scores": [s.overall_score or 0 for s in completed_sessions[-5:]] if completed_sessions else [],
                    "session_types": self._get_session_type_distribution(sessions)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting user statistics: {str(e)}")
            return {
                "total_sessions": 0,
                "avg_score": 0,
                "improvement_rate": 0,
                "skill_breakdown": {"content_quality": 0, "body_language": 0, "voice_tone": 0},
                "recommendations": ["Unable to load recommendations at this time"],
                "recent_sessions": [],
                "goals": {"weekly_practice": {"current": 0, "target": 3}, "score_improvement": {"current": 0, "target": 75}}
            }
    
    def _generate_user_recommendations(self, user_id: int, sessions: List, avg_score: float, 
                                     avg_content: float, avg_body_language: float, avg_tone: float) -> List[str]:
        """Generate personalized recommendations based on user's performance"""
        
        recommendations = []
        
        # Score-based recommendations
        if avg_score < 50:
            recommendations.append("Focus on fundamental interview skills - practice basic questions daily")
            recommendations.append("Record yourself answering questions to identify areas for improvement")
        elif avg_score < 70:
            recommendations.append("Work on providing more detailed, structured answers using the STAR method")
            recommendations.append("Practice maintaining confidence and clear communication throughout responses")
        elif avg_score < 85:
            recommendations.append("Fine-tune your responses with specific examples and quantifiable results")
            recommendations.append("Focus on advanced interview techniques and industry-specific knowledge")
        else:
            recommendations.append("Excellent performance! Continue practicing to maintain your high standards")
            recommendations.append("Consider mentoring others or preparing for senior-level interview questions")
        
        # Skill-specific recommendations
        if avg_content < avg_score - 10:
            recommendations.append("Strengthen your content quality by preparing more detailed examples and stories")
        
        if avg_body_language < avg_score - 10:
            recommendations.append("Improve your body language - practice good posture and maintain eye contact")
        
        if avg_tone < avg_score - 10:
            recommendations.append("Work on voice confidence and clarity - consider vocal exercises or speaking practice")
        
        # Session frequency recommendations
        if len(sessions) < 5:
            recommendations.append("Complete more practice sessions to build consistency and confidence")
        
        # Session type recommendations
        session_types = [s.session_type for s in sessions]
        if session_types.count('technical') < len(sessions) * 0.3:
            recommendations.append("Practice more technical interviews to strengthen your problem-solving skills")
        
        if session_types.count('behavioral') < len(sessions) * 0.3:
            recommendations.append("Focus on behavioral questions to improve your storytelling and soft skills")
        
        # Return top 3-4 most relevant recommendations
        return recommendations[:4] if recommendations else ["Keep practicing regularly to improve your interview skills!"]
    
    def _get_session_type_distribution(self, sessions: List) -> Dict[str, int]:
        """Get distribution of session types"""
        distribution = {}
        for session in sessions:
            session_type = session.session_type
            distribution[session_type] = distribution.get(session_type, 0) + 1
        return distribution
    
    def get_session_details(self, session_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed session information"""
        session = self.get_session_by_id(session_id, user_id)
        if not session:
            return None
        
        # Get performance metrics
        metrics = self.db.query(PerformanceMetrics).filter(
            PerformanceMetrics.session_id == session_id
        ).all()
        
        return {
            "session": session,
            "metrics": metrics,
            "questions_answered": len(metrics),
            "progress": self.get_session_progress(session_id, user_id)
        }
    
    def pause_interview_session(self, session_id: int, user_id: int) -> Optional[InterviewSession]:
        """Pause interview session"""
        if self.pause_session(session_id, user_id):
            return self.get_session_by_id(session_id, user_id)
        return None
    
    def resume_interview_session(self, session_id: int, user_id: int) -> Optional[InterviewSession]:
        """Resume interview session"""
        if self.resume_session(session_id, user_id):
            return self.get_session_by_id(session_id, user_id)
        return None
    
    def complete_interview_session(
        self, 
        session_id: int, 
        user_id: int, 
        final_score: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """Complete interview session"""
        session = self.get_session_by_id(session_id, user_id)
        if not session:
            return None
        
        # Use provided score or calculate from metrics
        if final_score is not None:
            overall_score = final_score
        else:
            metrics = self.db.query(PerformanceMetrics).filter(
                PerformanceMetrics.session_id == session_id
            ).all()
            
            if metrics:
                overall_score = sum(m.content_quality_score for m in metrics) / len(metrics)
            else:
                overall_score = 0.0
        
        # Update session
        update_data = InterviewSessionUpdate(
            status=SessionStatus.COMPLETED,
            overall_score=overall_score,
            completed_at=datetime.utcnow()
        )
        updated_session = update_interview_session(self.db, session_id, update_data)
        
        # Generate summary
        summary = self.get_session_summary(session_id, user_id)
        
        # Clean up session state
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        
        return {
            "session": updated_session,
            "summary": summary
        }