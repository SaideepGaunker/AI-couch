"""
Interview Service - Business logic for interview session management
"""
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from fastapi import HTTPException, status

from app.db.models import InterviewSession, Question, PerformanceMetrics, User
from app.schemas.interview import (
    InterviewSessionCreate, InterviewSessionUpdate, SessionConfigRequest,
    AnswerSubmission, SessionType, SessionStatus
)
from app.services.question_service import QuestionService
from app.services.gemini_service import GeminiService
from app.services.difficulty_service import DifficultyService
from app.services.difficulty_mapping_service import DifficultyMappingService
from app.services.recommendation_service import RecommendationService
from app.services.session_settings_manager import SessionSettingsManager
from app.services.session_specific_difficulty_service import SessionSpecificDifficultyService
from app.schemas.recommendation import RecommendationRequest
from app.crud.interview import (
    create_interview_session, get_interview_session, update_interview_session,
    get_user_sessions, create_performance_metric
)
from app.crud.question import get_question

logger = logging.getLogger(__name__)


from app.core.cache import session_manager, cache_service
from app.core.exceptions import (
    SessionError, NotFoundError, ValidationError, 
    BusinessLogicError, AuthorizationError, handle_database_error
)

class InterviewService:
    """Service for managing interview sessions"""
    
    def __init__(self, db: Session):
        self.db = db
        self.question_service = QuestionService(db)
        self.gemini_service = GeminiService(db)
        self.difficulty_service = DifficultyService(db)
        self.difficulty_mapping = DifficultyMappingService
        self.recommendation_service = RecommendationService(db)
        self.session_manager = session_manager
        self.cache = cache_service
        self.session_settings_manager = SessionSettingsManager(db)
        self.session_difficulty_service = SessionSpecificDifficultyService(db)
    
    def start_interview_session(
        self, 
        user: User, 
        session_data: InterviewSessionCreate
    ) -> Dict[str, Any]:
        """Start a new interview session with comprehensive error handling and validation"""
        
        try:
            logger.info(f"Starting interview session for user {user.id} with role {session_data.target_role}")
            
            # Validate session data
            if not self._validate_session_data(session_data):
                raise ValidationError("Invalid session configuration provided")
            
            # Complete any incomplete sessions before starting new one
            self._complete_incomplete_sessions(user.id)
            
            # Check for existing active sessions and handle appropriately
            active_sessions = self.session_manager.get_user_sessions(user.id)
            if len(active_sessions) > 3:  # Limit concurrent sessions
                logger.warning(f"User {user.id} has {len(active_sessions)} active sessions, cleaning up old ones")
                self._cleanup_old_user_sessions(user.id)
            
            # Always use user's selected difficulty for the current session
            current_session_difficulty = session_data.difficulty or "medium"
            logger.info(f"Using user-selected difficulty for current session: {current_session_difficulty}")
            
            # Calculate adaptive difficulty for NEXT session only (don't use it now)
            adaptive_difficulty_for_next = self.difficulty_service.get_next_difficulty(user.id)
            logger.info(f"Calculated adaptive difficulty for next session: {adaptive_difficulty_for_next}")
            
            # Create session with user-selected difficulty and comprehensive error handling
            try:
                session = create_interview_session(
                    self.db, 
                    user.id, 
                    session_data, 
                    difficulty_level=current_session_difficulty
                )
                logger.info(f"Created interview session {session.id} with difficulty {current_session_difficulty}")
                
                # Initialize session-specific difficulty state
                try:
                    difficulty_state = self.session_difficulty_service.initialize_session_difficulty(
                        session.id, 
                        current_session_difficulty
                    )
                    logger.info(f"Initialized session-specific difficulty state for session {session.id}")
                except Exception as difficulty_error:
                    logger.error(f"Failed to initialize session difficulty state: {str(difficulty_error)}")
                    # Don't fail the entire session creation, but log the error
                    # The session can still function with fallback difficulty handling
                    
            except Exception as e:
                logger.error(f"Failed to create session in database: {str(e)}")
                raise SessionError(f"Failed to create interview session: {str(e)}")
            
            # Get questions for the session with user context and validation
            try:
                questions = self._get_validated_questions(user, session_data, current_session_difficulty, session.id)
                logger.info(f"Retrieved {len(questions)} validated questions for session")
            except Exception as e:
                logger.error(f"Failed to get questions: {str(e)}")
                # Clean up the created session if question retrieval fails
                try:
                    self.db.delete(session)
                    self.db.commit()
                except:
                    pass
                raise SessionError(f"Failed to retrieve questions: {str(e)}")
            
            # Initialize session state with comprehensive validation
            try:
                session_state = self._create_session_state(user.id, questions, session.id)
                if not self.session_manager.create_session(session.id, session_state):
                    raise SessionError("Failed to initialize session state")
                logger.info(f"Session state initialized successfully for session {session.id}")
            except Exception as e:
                logger.error(f"Failed to initialize session state: {str(e)}")
                # Clean up database session
                try:
                    self.db.delete(session)
                    self.db.commit()
                except:
                    pass
                raise SessionError(f"Failed to initialize session state: {str(e)}")
            
            # Convert questions to dictionaries for JSON serialization
            questions_data = self._serialize_questions(questions)
            
            # Validate final response before returning
            response = {
                "session": session,
                "questions": questions_data,
                "configuration": {
                    "total_questions": len(questions),
                    "estimated_duration": sum(q.expected_duration for q in questions),
                    "session_id": session.id,
                    "difficulty_level": current_session_difficulty,
                    "created_at": session.created_at.isoformat() if session.created_at else None
                }
            }
            
            if not self._validate_session_response(response):
                raise SessionError("Invalid session response generated")
            
            logger.info(f"Interview session {session.id} started successfully")
            return response
            
        except (ValidationError, SessionError, BusinessLogicError):
            # Re-raise known exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error starting interview session: {str(e)}")
            raise SessionError(f"Failed to start interview session: {str(e)}")
    
    def get_next_question_contextual(
        self,
        session_id: int,
        user: User,
        previous_answer: str = None
    ) -> Dict[str, Any]:
        """Get next question with contextual awareness"""
        
        try:
            session_state = self.session_manager.get_session(session_id)
            if not session_state:
                raise ValueError("Session not found or not active")
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
            session_state = {
                "user_id": user.id,
                "questions": [q.id for q in questions],
                "current_question_index": 0,
                "start_time": datetime.utcnow().isoformat(),
                "answers": {},
                "paused_time": 0,
                "is_test_mode": True
            }
            self.session_manager.create_session(session.id, session_state)
            
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
    
    def _validate_session_data(self, session_data: InterviewSessionCreate) -> bool:
        """Validate session configuration data"""
        try:
            # Check required fields
            if not session_data.target_role or not session_data.session_type:
                logger.error("Missing required session data: target_role or session_type")
                return False
            
            # Validate duration
            if session_data.duration and (session_data.duration < 5 or session_data.duration > 120):
                logger.error(f"Invalid session duration: {session_data.duration}")
                return False
            
            # Validate question count
            if session_data.question_count and (session_data.question_count < 1 or session_data.question_count > 20):
                logger.error(f"Invalid question count: {session_data.question_count}")
                return False
            
            # Validate difficulty
            valid_difficulties = ['easy', 'medium', 'hard', 'expert']
            if session_data.difficulty and session_data.difficulty not in valid_difficulties:
                logger.error(f"Invalid difficulty: {session_data.difficulty}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating session data: {str(e)}")
            return False
    
    def _complete_incomplete_sessions(self, user_id: int):
        """Complete any incomplete sessions for a user before starting a new one"""
        try:
            # Get incomplete sessions from database
            incomplete_sessions = self.db.query(InterviewSession).filter(
                and_(
                    InterviewSession.user_id == user_id,
                    InterviewSession.status.in_(["active", "in_progress"])
                )
            ).all()
            
            for session in incomplete_sessions:
                logger.info(f"Auto-completing incomplete session {session.id} for user {user_id}")
                try:
                    self._complete_session(session.id, user_id)
                except Exception as e:
                    logger.error(f"Error completing session {session.id}: {str(e)}")
                    # Mark as completed even if there's an error to prevent blocking
                    session.status = SessionStatus.COMPLETED
                    session.completed_at = datetime.utcnow()
                    session.performance_score = 25.0  # Low score for incomplete session
                    self.db.commit()
                    
        except Exception as e:
            logger.error(f"Error completing incomplete sessions for user {user_id}: {str(e)}")
    
    def _cleanup_old_user_sessions(self, user_id: int):
        """Clean up old active sessions for a user"""
        try:
            active_sessions = self.session_manager.get_user_sessions(user_id)
            
            # Sort by last activity and keep only the 2 most recent
            session_activities = []
            for session_id in active_sessions:
                session_state = self.session_manager.get_session(session_id)
                if session_state:
                    last_activity = session_state.get("last_activity", session_state.get("start_time", ""))
                    session_activities.append((session_id, last_activity))
            
            # Sort by activity time (most recent first)
            session_activities.sort(key=lambda x: x[1], reverse=True)
            
            # Remove old sessions (keep only 2 most recent)
            for session_id, _ in session_activities[2:]:
                logger.info(f"Cleaning up old session {session_id} for user {user_id}")
                self.session_manager.delete_session(session_id)
                
        except Exception as e:
            logger.error(f"Error cleaning up old sessions for user {user_id}: {str(e)}")
    
    def _get_validated_questions(self, user: User, session_data: InterviewSessionCreate, 
                               difficulty_level: str, session_id: int) -> List:
        """Get and validate questions for the session"""
        try:
            # Get user's previous sessions for context
            previous_sessions = get_user_sessions(self.db, user.id, limit=3)
            previous_sessions_data = []
            for prev_session in previous_sessions:
                if prev_session.id != session_id:  # Exclude current session
                    session_data_dict = {
                        "role": prev_session.target_role,
                        "session_type": prev_session.session_type,
                        "completed_at": prev_session.completed_at.isoformat() if prev_session.completed_at else None
                    }
                    previous_sessions_data.append(session_data_dict)
            
            # Check if hierarchical role data is provided
            hierarchical_role = getattr(session_data, 'hierarchical_role', None)
            if hierarchical_role:
                logger.info(f"Using hierarchical role data: {hierarchical_role}")
                from app.schemas.role_hierarchy import HierarchicalRole
                
                role_data = HierarchicalRole(
                    main_role=getattr(hierarchical_role, 'main_role', session_data.target_role),
                    sub_role=getattr(hierarchical_role, 'sub_role', None),
                    specialization=getattr(hierarchical_role, 'specialization', None),
                    tech_stack=getattr(hierarchical_role, 'tech_stack', [])
                )
                
                questions = self.question_service.get_questions_for_hierarchical_role(
                    role_data=role_data,
                    difficulty=difficulty_level,
                    session_type=session_data.session_type.value,
                    count=session_data.question_count or 5,
                    user_id=user.id,
                    previous_sessions=previous_sessions_data
                )
            else:
                # Fallback to traditional role-based question generation
                questions = self.question_service.get_questions_for_session(
                    role=session_data.target_role,
                    difficulty=difficulty_level,
                    session_type=session_data.session_type.value,
                    count=session_data.question_count or 5,
                    user_id=user.id,
                    previous_sessions=previous_sessions_data
                )
            
            # Validate questions
            if not questions or len(questions) == 0:
                logger.error("No questions retrieved for interview session")
                raise ValueError("No questions available for this role and session type")
            
            # Validate each question has required fields
            for i, question in enumerate(questions):
                if not hasattr(question, 'id') or not hasattr(question, 'content'):
                    logger.error(f"Question {i} missing required fields")
                    raise ValueError(f"Invalid question data at index {i}")
                
                if not question.content or question.content.strip() == "":
                    logger.error(f"Question {i} has empty content")
                    raise ValueError(f"Empty question content at index {i}")
            
            return questions
            
        except Exception as e:
            logger.error(f"Error getting validated questions: {str(e)}")
            raise
    
    def _create_session_state(self, user_id: int, questions: List, session_id: int) -> Dict[str, Any]:
        """Create comprehensive session state"""
        try:
            session_state = {
                "user_id": user_id,
                "session_id": session_id,
                "questions": [q.id for q in questions],
                "current_question_index": 0,
                "start_time": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat(),
                "answers": {},
                "paused_time": 0,
                "status": "active",
                "total_questions": len(questions),
                "questions_answered": 0,
                "session_metadata": {
                    "created_at": datetime.utcnow().isoformat(),
                    "version": "1.0",
                    "question_ids": [q.id for q in questions]
                }
            }
            
            # Validate session state
            if not self._validate_session_state(session_state):
                raise ValueError("Invalid session state created")
            
            return session_state
            
        except Exception as e:
            logger.error(f"Error creating session state: {str(e)}")
            raise
    
    def _validate_session_state(self, session_state: Dict[str, Any]) -> bool:
        """Validate session state structure"""
        try:
            required_fields = [
                "user_id", "session_id", "questions", "current_question_index",
                "start_time", "answers", "status", "total_questions"
            ]
            
            for field in required_fields:
                if field not in session_state:
                    logger.error(f"Missing required field in session state: {field}")
                    return False
            
            # Validate data types
            if not isinstance(session_state["questions"], list):
                logger.error("Questions field must be a list")
                return False
            
            if not isinstance(session_state["current_question_index"], int):
                logger.error("Current question index must be an integer")
                return False
            
            if not isinstance(session_state["answers"], dict):
                logger.error("Answers field must be a dictionary")
                return False
            
            # Validate ranges
            if session_state["current_question_index"] < 0:
                logger.error("Current question index cannot be negative")
                return False
            
            if session_state["total_questions"] != len(session_state["questions"]):
                logger.error("Total questions count mismatch")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating session state: {str(e)}")
            return False
    
    def _serialize_questions(self, questions: List) -> List[Dict[str, Any]]:
        """Serialize questions for JSON response"""
        try:
            questions_data = []
            for q in questions:
                question_dict = {
                    "id": q.id,
                    "content": q.content,
                    "question_type": getattr(q, 'question_type', 'behavioral'),
                    "role_category": getattr(q, 'role_category', 'general'),
                    "difficulty_level": getattr(q, 'difficulty_level', 'intermediate'),
                    "expected_duration": getattr(q, 'expected_duration', 3),
                    "generated_by": getattr(q, 'generated_by', 'system'),
                    "created_at": q.created_at.isoformat() if hasattr(q, 'created_at') and q.created_at else None
                }
                questions_data.append(question_dict)
            
            return questions_data
            
        except Exception as e:
            logger.error(f"Error serializing questions: {str(e)}")
            raise
    
    def _validate_session_response(self, response: Dict[str, Any]) -> bool:
        """Validate session response structure"""
        try:
            # Check required top-level fields
            required_fields = ["session", "questions", "configuration"]
            for field in required_fields:
                if field not in response:
                    logger.error(f"Missing required field in response: {field}")
                    return False
            
            # Validate session object
            if not hasattr(response["session"], 'id'):
                logger.error("Session object missing id")
                return False
            
            # Validate questions array
            if not isinstance(response["questions"], list) or len(response["questions"]) == 0:
                logger.error("Questions must be a non-empty list")
                return False
            
            # Validate configuration
            config = response["configuration"]
            if not isinstance(config.get("total_questions"), int) or config["total_questions"] <= 0:
                logger.error("Invalid total_questions in configuration")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating session response: {str(e)}")
            return False
    
    def get_session_details(self, session_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get comprehensive session details including questions and state"""
        try:
            # Get session from database
            session = self.get_session_by_id(session_id, user_id)
            if not session:
                return None
            
            # Get session state from cache
            session_state = self.session_manager.get_session(session_id)
            
            # Get questions if session state exists
            questions_data = []
            if session_state and "questions" in session_state:
                for question_id in session_state["questions"]:
                    question = get_question(self.db, question_id)
                    if question:
                        questions_data.append({
                            "id": question.id,
                            "content": question.content,
                            "question_type": question.question_type,
                            "role_category": question.role_category,
                            "difficulty_level": question.difficulty_level,
                            "expected_duration": question.expected_duration,
                            "generated_by": question.generated_by,
                            "created_at": question.created_at.isoformat() if question.created_at else None
                        })
            
            return {
                "session": session,
                "questions": questions_data,
                "session_state": session_state,
                "configuration": {
                    "total_questions": len(questions_data),
                    "estimated_duration": sum(q.get("expected_duration", 3) for q in questions_data)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting session details for {session_id}: {str(e)}")
            return None
    
    def get_session_progress(self, session_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get current session progress"""
        try:
            session = self.get_session_by_id(session_id, user_id)
            if not session:
                return None
            
            session_state = self.session_manager.get_session(session_id)
            if not session_state:
                return None
            
            current_index = session_state.get("current_question_index", 0)
            total_questions = len(session_state.get("questions", []))
            questions_answered = len(session_state.get("answers", {}))
            
            # Calculate elapsed time
            start_time_str = session_state.get("start_time")
            elapsed_time = 0
            if start_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str)
                    elapsed_time = int((datetime.utcnow() - start_time).total_seconds())
                except:
                    pass
            
            # Calculate remaining time
            session_duration = session.duration * 60  # Convert to seconds
            remaining_time = max(0, session_duration - elapsed_time)
            
            # Calculate completion percentage
            completion_percentage = (questions_answered / total_questions * 100) if total_questions > 0 else 0
            
            return {
                "session_id": session_id,
                "current_question": current_index + 1,
                "total_questions": total_questions,
                "questions_answered": questions_answered,
                "elapsed_time": elapsed_time,
                "remaining_time": remaining_time,
                "completion_percentage": round(completion_percentage, 2),
                "status": session_state.get("status", "active")
            }
            
        except Exception as e:
            logger.error(f"Error getting session progress for {session_id}: {str(e)}")
            return None
    
    def get_user_sessions(self, user_id: int, skip: int = 0, limit: int = 100, 
                         status: Optional[str] = None, include_family_info: bool = False) -> List:
        """Get user sessions with optional filtering and family info"""
        try:
            sessions = get_user_sessions(self.db, user_id, skip=skip, limit=limit)
            
            if status:
                sessions = [s for s in sessions if s.status == status]
            
            if include_family_info:
                # Add family information for each session
                for session in sessions:
                    if hasattr(session, 'parent_session_id') and session.parent_session_id:
                        # This is a practice session
                        session.family_info = {
                            "is_practice_session": True,
                            "original_session_id": session.parent_session_id
                        }
                    else:
                        # Check for child sessions
                        child_count = self.db.query(InterviewSession).filter(
                            InterviewSession.parent_session_id == session.id
                        ).count()
                        session.family_info = {
                            "is_practice_session": False,
                            "practice_attempts": child_count
                        }
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error getting user sessions: {str(e)}")
            return []
    
    def pause_interview_session(self, session_id: int, user_id: int) -> Optional[InterviewSession]:
        """Pause interview session with state management"""
        try:
            session = self.get_session_by_id(session_id, user_id)
            if not session or session.status != SessionStatus.ACTIVE:
                return None
            
            # Update database
            update_data = InterviewSessionUpdate(status=SessionStatus.PAUSED)
            updated_session = update_interview_session(self.db, session_id, update_data)
            
            # Update session state
            session_state = self.session_manager.get_session(session_id)
            if session_state:
                session_state.update({
                    "status": "paused",
                    "paused_at": datetime.utcnow().isoformat(),
                    "last_activity": datetime.utcnow().isoformat()
                })
                self.session_manager.update_session(session_id, session_state)
            
            logger.info(f"Session {session_id} paused successfully")
            return updated_session
            
        except Exception as e:
            logger.error(f"Error pausing session {session_id}: {str(e)}")
            return None
    
    def resume_interview_session(self, session_id: int, user_id: int) -> Optional[InterviewSession]:
        """Resume paused interview session with state management"""
        try:
            session = self.get_session_by_id(session_id, user_id)
            if not session or session.status != SessionStatus.PAUSED:
                return None
            
            # Update database
            update_data = InterviewSessionUpdate(status=SessionStatus.ACTIVE)
            updated_session = update_interview_session(self.db, session_id, update_data)
            
            # Update session state
            session_state = self.session_manager.get_session(session_id)
            if session_state:
                # Calculate pause duration
                paused_at_str = session_state.get("paused_at")
                if paused_at_str:
                    try:
                        paused_at = datetime.fromisoformat(paused_at_str)
                        pause_duration = (datetime.utcnow() - paused_at).total_seconds()
                        session_state["paused_time"] = session_state.get("paused_time", 0) + pause_duration
                    except:
                        pass
                
                session_state.update({
                    "status": "active",
                    "resumed_at": datetime.utcnow().isoformat(),
                    "last_activity": datetime.utcnow().isoformat()
                })
                session_state.pop("paused_at", None)  # Remove pause timestamp
                self.session_manager.update_session(session_id, session_state)
            
            logger.info(f"Session {session_id} resumed successfully")
            return updated_session
            
        except Exception as e:
            logger.error(f"Error resuming session {session_id}: {str(e)}")
            return None
    
    def complete_interview_session(self, session_id: int, user_id: int, 
                                 final_score: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Complete interview session with comprehensive cleanup"""
        try:
            session = self.get_session_by_id(session_id, user_id)
            if not session:
                return None
            
            # Calculate final scores if not provided
            if final_score is None:
                final_score = self._calculate_session_score(session_id)
            
            # Update database
            update_data = InterviewSessionUpdate(
                status=SessionStatus.COMPLETED,
                overall_score=final_score,
                completed_at=datetime.utcnow()
            )
            updated_session = update_interview_session(self.db, session_id, update_data)
            
            # Update session state
            session_state = self.session_manager.get_session(session_id)
            if session_state:
                session_state.update({
                    "status": "completed",
                    "completed_at": datetime.utcnow().isoformat(),
                    "final_score": final_score,
                    "last_activity": datetime.utcnow().isoformat()
                })
                self.session_manager.update_session(session_id, session_state)
            
            # Finalize session difficulty state
            try:
                final_difficulty = self.session_difficulty_service.finalize_session_difficulty(session_id)
                if final_difficulty:
                    logger.info(f"Finalized difficulty for session {session_id}: {final_difficulty}")
                else:
                    logger.warning(f"Could not finalize difficulty for session {session_id}")
            except Exception as difficulty_error:
                logger.error(f"Error finalizing session difficulty for session {session_id}: {str(difficulty_error)}")
                # Don't fail the entire completion process
            
            # Generate session summary
            summary = self._generate_session_summary(session_id, session_state)
            
            # Clean up session difficulty cache
            try:
                self.session_difficulty_service.clear_session_cache(session_id)
                logger.debug(f"Cleared difficulty cache for completed session {session_id}")
            except Exception as cache_error:
                logger.warning(f"Error clearing difficulty cache for session {session_id}: {str(cache_error)}")
            
            logger.info(f"Session {session_id} completed successfully with score {final_score}")
            return {
                "session": updated_session,
                "summary": summary
            }
            
        except Exception as e:
            logger.error(f"Error completing session {session_id}: {str(e)}")
            return None
    
    def create_practice_session(self, original_session: InterviewSession, user: User) -> Dict[str, Any]:
        """Create a practice session based on an existing session"""
        try:
            from app.services.session_continuity_service import SessionContinuityService
            
            continuity_service = SessionContinuityService(self.db)
            
            # Clone the session for practice
            new_session = continuity_service.clone_session_for_practice(
                original_session.id, 
                user.id
            )
            
            if not new_session:
                raise ValueError("Failed to create practice session")
            
            # Get questions for the new session (fresh questions)
            session_data = InterviewSessionCreate(
                session_type=SessionType(original_session.session_type),
                target_role=original_session.target_role,
                duration=original_session.duration,
                difficulty=new_session.difficulty_level,
                question_count=5  # Default question count
            )
            
            questions = self._get_validated_questions(user, session_data, new_session.difficulty_level, new_session.id)
            
            # Initialize session state
            session_state = self._create_session_state(user.id, questions, new_session.id)
            session_state["is_practice_session"] = True
            session_state["original_session_id"] = original_session.id
            
            if not self.session_manager.create_session(new_session.id, session_state):
                raise SessionError("Failed to initialize practice session state")
            
            # Serialize questions
            questions_data = self._serialize_questions(questions)
            
            return {
                "session": new_session,
                "questions": questions_data,
                "configuration": {
                    "total_questions": len(questions),
                    "estimated_duration": sum(q.get("expected_duration", 3) for q in questions_data),
                    "is_practice_session": True,
                    "original_session_id": original_session.id
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating practice session: {str(e)}")
            raise
    
    def _calculate_session_score(self, session_id: int) -> float:
        """Calculate overall session score from performance metrics"""
        try:
            from app.db.models import PerformanceMetrics
            
            metrics = self.db.query(PerformanceMetrics).filter(
                PerformanceMetrics.session_id == session_id
            ).all()
            
            if not metrics:
                return 0.0
            
            # Calculate weighted average of all metrics
            total_score = 0.0
            total_weight = 0.0
            
            for metric in metrics:
                # Weight different aspects
                content_weight = 0.4
                body_language_weight = 0.3
                tone_weight = 0.3
                
                score = (
                    (metric.content_quality_score or 0) * content_weight +
                    (metric.body_language_score or 0) * body_language_weight +
                    (metric.tone_confidence_score or 0) * tone_weight
                )
                
                total_score += score
                total_weight += 1.0
            
            return round(total_score / total_weight, 2) if total_weight > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating session score: {str(e)}")
            return 0.0
    
    def _generate_session_summary(self, session_id: int, session_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive session summary"""
        try:
            summary = {
                "session_id": session_id,
                "total_questions": 0,
                "questions_answered": 0,
                "average_scores": {},
                "time_breakdown": {},
                "completion_rate": 0.0
            }
            
            if session_state:
                summary["total_questions"] = len(session_state.get("questions", []))
                summary["questions_answered"] = len(session_state.get("answers", {}))
                
                if summary["total_questions"] > 0:
                    summary["completion_rate"] = round(
                        (summary["questions_answered"] / summary["total_questions"]) * 100, 2
                    )
                
                # Calculate time breakdown
                start_time_str = session_state.get("start_time")
                completed_at_str = session_state.get("completed_at")
                
                if start_time_str and completed_at_str:
                    try:
                        start_time = datetime.fromisoformat(start_time_str)
                        completed_at = datetime.fromisoformat(completed_at_str)
                        total_duration = int((completed_at - start_time).total_seconds())
                        
                        summary["time_breakdown"] = {
                            "total_duration": total_duration,
                            "paused_time": session_state.get("paused_time", 0),
                            "active_time": total_duration - session_state.get("paused_time", 0)
                        }
                    except:
                        pass
            
            # Get performance metrics for average scores
            from app.db.models import PerformanceMetrics
            metrics = self.db.query(PerformanceMetrics).filter(
                PerformanceMetrics.session_id == session_id
            ).all()
            
            if metrics:
                content_scores = [m.content_quality_score for m in metrics if m.content_quality_score]
                body_scores = [m.body_language_score for m in metrics if m.body_language_score]
                tone_scores = [m.tone_confidence_score for m in metrics if m.tone_confidence_score]
                
                summary["average_scores"] = {
                    "content_quality": round(sum(content_scores) / len(content_scores), 2) if content_scores else 0,
                    "body_language": round(sum(body_scores) / len(body_scores), 2) if body_scores else 0,
                    "voice_tone": round(sum(tone_scores) / len(tone_scores), 2) if tone_scores else 0
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating session summary: {str(e)}")
            return {"session_id": session_id, "error": "Failed to generate summary"}
    
    def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user statistics"""
        try:
            # Get all user sessions
            sessions = get_user_sessions(self.db, user_id)
            
            # Calculate basic statistics
            total_sessions = len(sessions)
            completed_sessions = len([s for s in sessions if s.status == 'completed'])
            
            # Calculate average scores
            completed_with_scores = [s for s in sessions if s.status == 'completed' and s.overall_score]
            avg_score = sum(s.overall_score for s in completed_with_scores) / len(completed_with_scores) if completed_with_scores else 0
            
            # Get skill breakdown from performance metrics
            from app.db.models import PerformanceMetrics
            all_metrics = []
            for session in sessions:
                metrics = self.db.query(PerformanceMetrics).filter(
                    PerformanceMetrics.session_id == session.id
                ).all()
                all_metrics.extend(metrics)
            
            skill_breakdown = {}
            if all_metrics:
                content_scores = [m.content_quality_score for m in all_metrics if m.content_quality_score]
                body_scores = [m.body_language_score for m in all_metrics if m.body_language_score]
                tone_scores = [m.tone_confidence_score for m in all_metrics if m.tone_confidence_score]
                
                skill_breakdown = {
                    "content_quality": round(sum(content_scores) / len(content_scores), 2) if content_scores else 0,
                    "body_language": round(sum(body_scores) / len(body_scores), 2) if body_scores else 0,
                    "voice_tone": round(sum(tone_scores) / len(tone_scores), 2) if tone_scores else 0
                }
            
            return {
                "total_sessions": total_sessions,
                "completed_sessions": completed_sessions,
                "completion_rate": round((completed_sessions / total_sessions) * 100, 2) if total_sessions > 0 else 0,
                "average_score": round(avg_score, 2),
                "skill_breakdown": skill_breakdown,
                "recent_activity": {
                    "last_session": sessions[0].created_at.isoformat() if sessions else None,
                    "sessions_this_week": len([s for s in sessions if 
                        s.created_at >= datetime.utcnow() - timedelta(days=7)])
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting user statistics: {str(e)}")
            return {
                "total_sessions": 0,
                "completed_sessions": 0,
                "completion_rate": 0,
                "average_score": 0,
                "skill_breakdown": {},
                "recent_activity": {}
            }
    
    def _complete_session(self, session_id: int, user_id: int):
        """Internal method to complete a session"""
        try:
            result = self.complete_interview_session(session_id, user_id)
            if result:
                logger.info(f"Session {session_id} completed automatically")
            else:
                logger.warning(f"Failed to complete session {session_id}")
        except Exception as e:
            logger.error(f"Error in _complete_session: {str(e)}")
            raise
    
    def get_session_feedback(self, session_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get comprehensive session feedback with error handling"""
        try:
            # Get session
            session = self.get_session_by_id(session_id, user_id)
            if not session:
                logger.error(f"Session {session_id} not found for feedback")
                return None
            
            # Only provide feedback for completed sessions
            if session.status != SessionStatus.COMPLETED:
                logger.warning(f"Session {session_id} is not completed, status: {session.status}")
                return self._create_partial_feedback(session)
            
            # Get performance metrics
            from app.db.models import PerformanceMetrics
            metrics = self.db.query(PerformanceMetrics).filter(
                PerformanceMetrics.session_id == session_id
            ).all()
            
            if not metrics:
                logger.warning(f"No performance metrics found for session {session_id}")
                return self._create_basic_feedback(session)
            
            # Calculate comprehensive feedback
            feedback = self._calculate_comprehensive_feedback(session, metrics)
            
            # Get learning recommendations with error handling
            try:
                learning_recommendations = self._get_learning_recommendations(session, metrics)
            except Exception as e:
                logger.error(f"Error getting learning recommendations: {str(e)}")
                learning_recommendations = self._get_basic_learning_recommendations(session.target_role)
            
            # Get difficulty information for the user
            current_difficulty = session.difficulty_level or 'medium'
            
            # Calculate recommended difficulty for NEXT session based on current session performance
            # Use performance-based difficulty adjustment logic
            overall_score = session.overall_score or 0
            
            logger.info(f"=== DIFFICULTY CALCULATION DEBUG ===")
            logger.info(f"Session {session_id}: Score {overall_score}, Current Difficulty: {current_difficulty}")
            
            next_difficulty = self._calculate_recommended_difficulty(current_difficulty, overall_score)
            
            logger.info(f"Calculated next difficulty: {next_difficulty}")
            logger.info(f"=== END DIFFICULTY CALCULATION DEBUG ===")
            
            # Build complete feedback response
            response = {
                "feedback": feedback,
                "session": {
                    "id": session.id,
                    "target_role": session.target_role,
                    "session_type": session.session_type,
                    "duration": session.duration,
                    "status": session.status,
                    "overall_score": session.overall_score,
                    "difficulty_level": current_difficulty,
                    "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                    "created_at": session.created_at.isoformat() if session.created_at else None
                },
                "difficulty_info": {
                    "current_difficulty": current_difficulty,
                    "next_difficulty": next_difficulty,
                    "difficulty_change_reason": self._get_difficulty_change_reason(current_difficulty, next_difficulty, overall_score),
                    "performance_based_recommendation": True,
                    "current_session_score": overall_score
                },
                "learning_recommendations": learning_recommendations,
                "performance_metrics_count": len(metrics),
                "generated_at": datetime.utcnow().isoformat()
            }
            
            # Store the recommended difficulty for next session in user preferences
            self._store_recommended_difficulty_for_next_session(user_id, next_difficulty)
            
            logger.info(f"Generated comprehensive feedback for session {session_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error getting session feedback: {str(e)}")
            return self._create_fallback_feedback(session_id)
    
    def _store_recommended_difficulty_for_next_session(self, user_id: int, recommended_difficulty: str):
        """Store the recommended difficulty for the user's next session"""
        try:
            from app.db.models import User
            user = self.db.query(User).filter(User.id == user_id).first()
            if user:
                # Store in user's metadata or create a separate table for recommendations
                # For now, we'll just log it - you can extend this to store in database
                logger.info(f"Recommended difficulty for user {user_id} next session: {recommended_difficulty}")
        except Exception as e:
            logger.error(f"Error storing recommended difficulty: {str(e)}")
    
    def _create_partial_feedback(self, session) -> Dict[str, Any]:
        """Create partial feedback for incomplete sessions"""
        try:
            current_difficulty = session.difficulty_level or 'medium'
            next_difficulty = self.difficulty_service.get_next_difficulty(session.user_id)
            
            return {
                "feedback": {
                    "overall_score": 0,
                    "content_quality": 0,
                    "body_language": 0,
                    "voice_tone": 0,
                    "areas_for_improvement": ["Complete the session to receive detailed feedback"],
                    "recommendations": "Please complete your interview session to receive comprehensive feedback.",
                    "session_incomplete": True
                },
                "session": {
                    "id": session.id,
                    "target_role": session.target_role,
                    "session_type": session.session_type,
                    "status": session.status,
                    "difficulty_level": current_difficulty
                },
                "difficulty_info": {
                    "current_difficulty": current_difficulty,
                    "next_difficulty": next_difficulty,
                    "difficulty_change_reason": "Complete the session for difficulty adjustment"
                },
                "learning_recommendations": None
            }
        except Exception as e:
            logger.error(f"Error creating partial feedback: {str(e)}")
            return self._create_fallback_feedback(session.id if session else 0)
    
    def _create_basic_feedback(self, session) -> Dict[str, Any]:
        """Create basic feedback when no metrics are available"""
        try:
            current_difficulty = session.difficulty_level or 'medium'
            next_difficulty = self.difficulty_service.get_next_difficulty(session.user_id)
            
            return {
                "feedback": {
                    "overall_score": session.overall_score or 0,
                    "content_quality": session.overall_score or 0,
                    "body_language": 50,  # Default score
                    "voice_tone": 50,     # Default score
                    "areas_for_improvement": [
                        "Continue practicing to improve your interview skills",
                        "Focus on providing detailed, specific examples",
                        "Practice maintaining good posture and eye contact"
                    ],
                    "recommendations": "Keep practicing interviews to build confidence and improve your responses.",
                    "limited_data": True
                },
                "session": {
                    "id": session.id,
                    "target_role": session.target_role,
                    "session_type": session.session_type,
                    "status": session.status,
                    "overall_score": session.overall_score,
                    "difficulty_level": current_difficulty
                },
                "difficulty_info": {
                    "current_difficulty": current_difficulty,
                    "next_difficulty": next_difficulty,
                    "difficulty_change_reason": self._get_difficulty_change_reason(current_difficulty, next_difficulty)
                },
                "learning_recommendations": self._get_basic_learning_recommendations(session.target_role)
            }
        except Exception as e:
            logger.error(f"Error creating basic feedback: {str(e)}")
            return self._create_fallback_feedback(session.id if session else 0)
    
    def _calculate_comprehensive_feedback(self, session, metrics: List) -> Dict[str, Any]:
        """Calculate comprehensive feedback from performance metrics"""
        try:
            # Calculate average scores
            content_scores = [m.content_quality_score for m in metrics if m.content_quality_score is not None]
            body_scores = [m.body_language_score for m in metrics if m.body_language_score is not None]
            tone_scores = [m.tone_confidence_score for m in metrics if m.tone_confidence_score is not None]
            
            avg_content = sum(content_scores) / len(content_scores) if content_scores else 0
            avg_body = sum(body_scores) / len(body_scores) if body_scores else 0
            avg_tone = sum(tone_scores) / len(tone_scores) if tone_scores else 0
            
            # Calculate overall score
            overall_score = session.overall_score or ((avg_content + avg_body + avg_tone) / 3)
            
            # Collect improvement suggestions
            all_suggestions = []
            for metric in metrics:
                if metric.improvement_suggestions:
                    if isinstance(metric.improvement_suggestions, list):
                        all_suggestions.extend(metric.improvement_suggestions)
                    else:
                        all_suggestions.append(str(metric.improvement_suggestions))
            
            # Remove duplicates and limit suggestions
            unique_suggestions = list(set(all_suggestions))[:5]
            
            # Generate areas for improvement based on scores
            areas_for_improvement = []
            if avg_content < 60:
                areas_for_improvement.append("Content quality - provide more detailed and relevant responses")
            if avg_body < 60:
                areas_for_improvement.append("Body language - maintain good posture and eye contact")
            if avg_tone < 60:
                areas_for_improvement.append("Voice confidence - speak clearly and with confidence")
            
            if not areas_for_improvement:
                areas_for_improvement.append("Continue practicing to maintain your strong performance")
            
            # Generate recommendations
            recommendations = self._generate_recommendations(avg_content, avg_body, avg_tone, session.target_role)
            
            return {
                "overall_score": round(overall_score, 2),
                "content_quality": round(avg_content, 2),
                "body_language": round(avg_body, 2),
                "voice_tone": round(avg_tone, 2),
                "areas_for_improvement": areas_for_improvement,
                "recommendations": recommendations,
                "improvement_suggestions": unique_suggestions,
                "questions_answered": len(metrics),
                "score_breakdown": {
                    "content_scores": content_scores,
                    "body_language_scores": body_scores,
                    "voice_tone_scores": tone_scores
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating comprehensive feedback: {str(e)}")
            return {
                "overall_score": 0,
                "content_quality": 0,
                "body_language": 0,
                "voice_tone": 0,
                "areas_for_improvement": ["Error calculating feedback"],
                "recommendations": "Please try again or contact support.",
                "error": True
            }
    
    def _generate_recommendations(self, content_score: float, body_score: float, 
                                tone_score: float, target_role: str) -> List[str]:
        """Generate personalized recommendations based on scores"""
        try:
            recommendations = []
            
            # Content recommendations
            if content_score < 50:
                recommendations.append("Practice the STAR method (Situation, Task, Action, Result) for structured responses")
            elif content_score < 70:
                recommendations.append("Add more specific examples and quantifiable results to your answers")
            else:
                recommendations.append("Excellent content quality - continue providing detailed, relevant examples")
            
            # Body language recommendations
            if body_score < 50:
                recommendations.append("Practice maintaining good posture and making eye contact during interviews")
            elif body_score < 70:
                recommendations.append("Work on consistent body language throughout the interview")
            else:
                recommendations.append("Great body language - you project confidence and professionalism")
            
            # Voice recommendations
            if tone_score < 50:
                recommendations.append("Practice speaking clearly and with confidence")
            elif tone_score < 70:
                recommendations.append("Work on varying your tone to show enthusiasm and engagement")
            else:
                recommendations.append("Excellent voice confidence - you communicate effectively")
            
            # Role-specific recommendations
            role_specific = self._get_role_specific_recommendations(target_role, content_score)
            if role_specific:
                recommendations.append(role_specific)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return ["Continue practicing to improve your interview skills."]
    
    def _get_role_specific_recommendations(self, target_role: str, content_score: float) -> str:
        """Get role-specific recommendations"""
        try:
            role_recommendations = {
                "software_developer": "Focus on explaining technical concepts clearly and discussing your problem-solving approach",
                "data_scientist": "Emphasize your analytical thinking and ability to derive insights from data",
                "product_manager": "Highlight your strategic thinking and stakeholder management skills",
                "devops_engineer": "Discuss your experience with automation and system reliability",
                "designer": "Showcase your design process and user-centered thinking"
            }
            
            # Normalize role name
            normalized_role = target_role.lower().replace(" ", "_").replace("-", "_")
            
            return role_recommendations.get(normalized_role, "")
            
        except Exception as e:
            logger.error(f"Error getting role-specific recommendations: {str(e)}")
            return ""
    
    def _get_learning_recommendations(self, session, metrics: List) -> Optional[Dict[str, Any]]:
        """Get learning recommendations based on performance using Gemini AI"""
        try:
            if not metrics:
                return self._get_basic_learning_recommendations(session.target_role)
            
            # Analyze performance patterns
            content_scores = [m.content_quality_score for m in metrics if m.content_quality_score is not None]
            body_scores = [m.body_language_score for m in metrics if m.body_language_score is not None]
            tone_scores = [m.tone_confidence_score for m in metrics if m.tone_confidence_score is not None]
            
            avg_content = sum(content_scores) / len(content_scores) if content_scores else 0
            avg_body = sum(body_scores) / len(body_scores) if body_scores else 0
            avg_tone = sum(tone_scores) / len(tone_scores) if tone_scores else 0
            
            # Try to generate AI-powered learning recommendations using Gemini
            try:
                performance_data = {
                    "content_quality_score": avg_content,
                    "body_language_score": avg_body,
                    "voice_tone_score": avg_tone,
                    "target_role": session.target_role,
                    "session_type": session.session_type,
                    "overall_score": session.overall_score or ((avg_content + avg_body + avg_tone) / 3)
                }
                
                # Use Gemini to generate comprehensive learning recommendations
                ai_recommendations = self.gemini_service.generate_comprehensive_feedback(performance_data)
                
                if ai_recommendations and "learning_recommendations" in ai_recommendations:
                    logger.info("Successfully generated AI-powered learning recommendations")
                    return ai_recommendations["learning_recommendations"]
                    
            except Exception as ai_error:
                logger.warning(f"AI recommendation generation failed, using fallback: {str(ai_error)}")
            
            # Fallback to rule-based recommendations
            # Determine focus areas
            focus_areas = []
            if avg_content < 60:
                focus_areas.append("content_development")
            if avg_body < 60:
                focus_areas.append("body_language")
            if avg_tone < 60:
                focus_areas.append("voice_confidence")
            
            # Generate learning resources
            resources = []
            
            if "content_development" in focus_areas:
                resources.extend([
                    {
                        "type": "article",
                        "title": "STAR Method for Interview Responses",
                        "description": "Learn to structure your answers effectively",
                        "priority": "high"
                    },
                    {
                        "type": "practice",
                        "title": "Behavioral Interview Practice",
                        "description": "Practice common behavioral questions",
                        "priority": "high"
                    }
                ])
            
            if "body_language" in focus_areas:
                resources.extend([
                    {
                        "type": "video",
                        "title": "Professional Body Language Tips",
                        "description": "Improve your non-verbal communication",
                        "priority": "medium"
                    }
                ])
            
            # Add role-specific resources
            role_resources = self._get_role_specific_learning_resources(session.target_role)
            resources.extend(role_resources)
            
            return {
                "focus_areas": focus_areas,
                "resources": resources[:5],  # Limit to 5 resources
                "next_steps": self._get_next_steps_recommendations(avg_content, avg_body),
                "estimated_improvement_time": "2-4 weeks with regular practice"
            }
            
        except Exception as e:
            logger.error(f"Error getting learning recommendations: {str(e)}")
            return self._get_basic_learning_recommendations(session.target_role)
    
    def _get_basic_learning_recommendations(self, target_role: str) -> Dict[str, Any]:
        """Get basic learning recommendations"""
        return {
            "focus_areas": ["general_interview_skills"],
            "resources": [
                {
                    "type": "practice",
                    "title": "General Interview Practice",
                    "description": f"Practice common {target_role} interview questions",
                    "priority": "high"
                },
                {
                    "type": "article",
                    "title": "Interview Preparation Guide",
                    "description": "Comprehensive guide to interview preparation",
                    "priority": "medium"
                }
            ],
            "next_steps": ["Complete more practice sessions", "Focus on providing specific examples"],
            "estimated_improvement_time": "2-3 weeks with regular practice"
        }
    
    def _get_role_specific_learning_resources(self, target_role: str) -> List[Dict[str, Any]]:
        """Get role-specific learning resources"""
        try:
            role_resources = {
                "software_developer": [
                    {
                        "type": "practice",
                        "title": "Technical Interview Coding Practice",
                        "description": "Practice coding problems and system design",
                        "priority": "high"
                    }
                ],
                "data_scientist": [
                    {
                        "type": "practice",
                        "title": "Data Science Case Studies",
                        "description": "Practice analyzing data scenarios",
                        "priority": "high"
                    }
                ],
                "product_manager": [
                    {
                        "type": "article",
                        "title": "Product Management Frameworks",
                        "description": "Learn key PM frameworks and methodologies",
                        "priority": "high"
                    }
                ]
            }
            
            normalized_role = target_role.lower().replace(" ", "_").replace("-", "_")
            return role_resources.get(normalized_role, [])
            
        except Exception as e:
            logger.error(f"Error getting role-specific resources: {str(e)}")
            return []
    
    def _get_next_steps_recommendations(self, content_score: float, body_score: float) -> List[str]:
        """Get next steps recommendations based on scores"""
        try:
            next_steps = []
            
            if content_score < 60:
                next_steps.append("Focus on developing more detailed, specific responses")
                next_steps.append("Practice the STAR method for behavioral questions")
            
            if body_score < 60:
                next_steps.append("Practice maintaining good posture during interviews")
                next_steps.append("Work on making consistent eye contact")
            
            if content_score >= 70 and body_score >= 70:
                next_steps.append("Continue practicing to maintain your strong performance")
                next_steps.append("Consider practicing more challenging interview scenarios")
            
            if not next_steps:
                next_steps.append("Continue regular practice sessions")
                next_steps.append("Focus on consistency across all interview areas")
            
            return next_steps[:3]  # Limit to 3 next steps
            
        except Exception as e:
            logger.error(f"Error getting next steps: {str(e)}")
            return ["Continue practicing interview skills"]
    
    def _get_difficulty_change_reason(self, current_difficulty: str, next_difficulty: str, performance_score: float = None) -> str:
        """Get reason for difficulty change"""
        try:
            if performance_score is not None:
                if current_difficulty == next_difficulty:
                    if performance_score < 20:
                        return f"Maintaining {current_difficulty} difficulty - consider practicing more to improve (Score: {performance_score:.0f}/100)"
                    elif performance_score > 80:
                        return f"Excellent performance at {current_difficulty} level - ready for next challenge (Score: {performance_score:.0f}/100)"
                    else:
                        return f"Consistent performance at {current_difficulty} level (Score: {performance_score:.0f}/100)"
                else:
                    if performance_score < 20:
                        return f"Adjusting to {next_difficulty} to better match your current skill level (Score: {performance_score:.0f}/100)"
                    elif performance_score > 80:
                        return f"Increasing to {next_difficulty} due to strong performance (Score: {performance_score:.0f}/100)"
                    else:
                        return f"Adjusting to {next_difficulty} based on your performance (Score: {performance_score:.0f}/100)"
            else:
                # Fallback to original logic
                current_index = self.difficulty_service.difficulty_levels.index(current_difficulty)
                next_index = self.difficulty_service.difficulty_levels.index(next_difficulty)
                
                if current_index == next_index:
                    return "Based on your consistent performance"
                elif next_index > current_index:
                    return "You're ready for a challenge!"
                else:
                    return "Let's build your confidence"
        except (ValueError, AttributeError):
            return "Based on your performance in this session"

    def _create_fallback_feedback(self, session_id: int) -> Dict[str, Any]:
        """Create fallback feedback when all else fails"""
        return {
            "feedback": {
                "overall_score": 0,
                "content_quality": 0,
                "body_language": 0,
                "voice_tone": 0,
                "areas_for_improvement": ["Unable to generate feedback at this time"],
                "recommendations": "Please try again later or contact support if the issue persists.",
                "error": True
            },
            "session": {
                "id": session_id,
                "target_role": "Unknown",
                "session_type": "mixed",
                "status": "unknown",
                "difficulty_level": "medium"
            },
            "difficulty_info": {
                "current_difficulty": "medium",
                "next_difficulty": "medium",
                "difficulty_change_reason": "Complete more sessions for difficulty adjustment"
            },
            "learning_recommendations": None,
            "error": "Failed to generate feedback"
        }
    
    def get_session_by_id(self, session_id: int, user_id: int) -> Optional[InterviewSession]:
        """Get interview session by ID"""
        try:
            session = get_interview_session(self.db, session_id)
            
            if not session:
                raise NotFoundError("Interview session", session_id)
            
            # Verify ownership
            if session.user_id != user_id:
                raise AuthorizationError(
                    "Access denied to this session",
                    details={"session_id": session_id, "user_id": user_id}
                )
            
            return session
            
        except (NotFoundError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            raise handle_database_error(e, "get_session")
    
    def get_session(self, session_id: int, user_id: int) -> Optional[InterviewSession]:
        """Get interview session by ID (alias for get_session_by_id)"""
        return self.get_session_by_id(session_id, user_id)
    
    def get_current_question(self, session_id: int, user_id: int) -> Optional[Question]:
        """Get current question for the session"""
        session = self.get_session_by_id(session_id, user_id)
        if not session or session.status != SessionStatus.ACTIVE:
            return None
        
        session_state = self.session_manager.get_session(session_id)
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
        """Submit answer for current question with comprehensive error handling and validation"""
        logger.info(f"Submitting answer for session {session_id}, question {answer_data.question_id}")
        
        try:
            # Validate answer data
            if not self._validate_answer_data(answer_data):
                raise ValidationError("Invalid answer data provided")
            
            # Get and validate session
            session = self.get_session_by_id(session_id, user_id)
            if not session:
                logger.error(f"Session {session_id} not found for user {user_id}")
                raise NotFoundError("Interview session", session_id)
            
            if session.status != SessionStatus.ACTIVE:
                logger.error(f"Session {session_id} is not active, status: {session.status}")
                raise BusinessLogicError(f"Session is not active (status: {session.status})")
            
            # Get or recover session state
            session_state = self._get_or_recover_session_state(session_id, user_id, session)
            
            # Validate question and get question object
            question = self._validate_and_get_question(answer_data.question_id, session_state)
            
            # Process answer with retry mechanism
            evaluation = self._process_answer_with_retry(question, answer_data, session, user_id)
            
            # Store performance metrics with comprehensive error handling
            performance_metric = self._store_performance_metrics_safely(
                session_id, answer_data, evaluation
            )
            
            # Check for adaptive difficulty adjustment during session
            try:
                self._check_and_apply_adaptive_difficulty_adjustment(
                    session_id, evaluation, session_state, user_id
                )
            except Exception as difficulty_error:
                logger.error(f"Error in adaptive difficulty adjustment: {str(difficulty_error)}")
                # Don't fail the answer submission if difficulty adjustment fails
            
            # Update session state with validation
            self._update_session_state_safely(session_id, session_state, answer_data, evaluation)
            
            # Determine next steps
            next_steps = self._determine_next_steps(session_id, session_state, user_id)
            
            # Build response
            response = self._build_answer_response(
                answer_data.question_id, evaluation, next_steps, performance_metric
            )
            
            logger.info(f"Answer submitted successfully for session {session_id}")
            return response
            
        except (ValidationError, NotFoundError, BusinessLogicError, AuthorizationError):
            # Re-raise known exceptions
            raise
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error in submit_answer: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise SessionError(f"Failed to submit answer: {str(e)}")
    
    def _validate_answer_data(self, answer_data: AnswerSubmission) -> bool:
        """Validate answer submission data"""
        try:
            # Check required fields
            if not answer_data.question_id or not isinstance(answer_data.question_id, int):
                logger.error("Invalid or missing question_id")
                return False
            
            if not answer_data.answer_text or not answer_data.answer_text.strip():
                logger.error("Empty or missing answer text")
                return False
            
            # Validate response time
            if answer_data.response_time is None or answer_data.response_time < 0:
                logger.error("Invalid response time")
                return False
            
            # Validate posture data if provided
            if answer_data.posture_data:
                if not isinstance(answer_data.posture_data, dict):
                    logger.error("Posture data must be a dictionary")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating answer data: {str(e)}")
            return False
    
    def _get_or_recover_session_state(self, session_id: int, user_id: int, session) -> Dict[str, Any]:
        """Get session state or attempt recovery"""
        try:
            session_state = self.session_manager.get_session(session_id)
            
            if not session_state:
                logger.warning(f"Session state not found for {session_id}, attempting recovery")
                session_state = self._recover_session_state(session_id, user_id, session)
                
                if not session_state:
                    raise SessionError("Unable to recover session state")
                
                # Create the recovered state in session manager
                if not self.session_manager.create_session(session_id, session_state):
                    raise SessionError("Failed to restore session state")
            
            # Validate session state
            if not self._validate_session_state(session_state):
                logger.warning(f"Invalid session state for {session_id}, attempting repair")
                session_state = self._repair_session_state(session_state, session_id, user_id)
            
            return session_state
            
        except Exception as e:
            logger.error(f"Error getting session state: {str(e)}")
            raise
    
    def _recover_session_state(self, session_id: int, user_id: int, session) -> Optional[Dict[str, Any]]:
        """Attempt to recover session state from database"""
        try:
            # Get performance metrics to determine progress
            from app.db.models import PerformanceMetrics
            metrics = self.db.query(PerformanceMetrics).filter(
                PerformanceMetrics.session_id == session_id
            ).order_by(PerformanceMetrics.created_at).all()
            
            # Get questions from the original session (if available)
            questions = []
            answered_questions = set()
            
            if metrics:
                for metric in metrics:
                    answered_questions.add(metric.question_id)
                    question = get_question(self.db, metric.question_id)
                    if question and question not in questions:
                        questions.append(question)
            
            # If no questions found, create fallback questions
            if not questions:
                logger.warning(f"No questions found for session {session_id}, creating fallback")
                questions = self._create_fallback_questions(session.target_role)
            
            # Build recovered session state
            recovered_state = {
                "user_id": user_id,
                "session_id": session_id,
                "questions": [q.id for q in questions],
                "current_question_index": len(answered_questions),
                "start_time": session.created_at.isoformat(),
                "last_activity": datetime.utcnow().isoformat(),
                "answers": {},
                "paused_time": 0,
                "status": "active",
                "total_questions": len(questions),
                "questions_answered": len(answered_questions),
                "recovered": True,
                "recovery_timestamp": datetime.utcnow().isoformat()
            }
            
            # Add answered questions to state
            for metric in metrics:
                recovered_state["answers"][str(metric.question_id)] = {
                    "answer": metric.answer_text or "Recovered answer",
                    "evaluation": {"overall_score": metric.content_quality_score or 0},
                    "timestamp": metric.created_at.isoformat() if metric.created_at else datetime.utcnow().isoformat()
                }
            
            logger.info(f"Successfully recovered session state for {session_id}")
            return recovered_state
            
        except Exception as e:
            logger.error(f"Error recovering session state: {str(e)}")
            return None
    
    def _create_fallback_questions(self, target_role: str) -> List:
        """Create fallback questions when recovery fails"""
        try:
            # Try to get questions from question service
            questions = self.question_service.get_questions_for_session(
                role=target_role,
                difficulty="intermediate",
                session_type="mixed",
                count=3
            )
            
            if questions:
                return questions
            
            # Create minimal fallback questions
            class FallbackQuestion:
                def __init__(self, question_id, content):
                    self.id = question_id
                    self.content = content
                    self.question_type = "behavioral"
                    self.expected_duration = 3
                    self.role_category = target_role
                    self.difficulty_level = "intermediate"
                    self.generated_by = "fallback"
                    self.created_at = datetime.utcnow()
            
            fallback_questions = [
                FallbackQuestion(1, f"Tell me about your experience in {target_role}."),
                FallbackQuestion(2, "Describe a challenging situation you've faced and how you handled it."),
                FallbackQuestion(3, "What are your strengths and how do they apply to this role?")
            ]
            
            logger.info(f"Created {len(fallback_questions)} fallback questions")
            return fallback_questions
            
        except Exception as e:
            logger.error(f"Error creating fallback questions: {str(e)}")
            return []
    
    def _repair_session_state(self, session_state: Dict[str, Any], session_id: int, user_id: int) -> Dict[str, Any]:
        """Repair corrupted session state"""
        try:
            # Ensure required fields exist
            required_fields = {
                "user_id": user_id,
                "session_id": session_id,
                "questions": session_state.get("questions", [1, 2, 3]),
                "current_question_index": session_state.get("current_question_index", 0),
                "start_time": session_state.get("start_time", datetime.utcnow().isoformat()),
                "last_activity": datetime.utcnow().isoformat(),
                "answers": session_state.get("answers", {}),
                "paused_time": session_state.get("paused_time", 0),
                "status": session_state.get("status", "active"),
                "total_questions": len(session_state.get("questions", [1, 2, 3])),
                "questions_answered": len(session_state.get("answers", {})),
                "repaired": True,
                "repair_timestamp": datetime.utcnow().isoformat()
            }
            
            # Update session state with repaired values
            session_state.update(required_fields)
            
            # Validate ranges
            if session_state["current_question_index"] < 0:
                session_state["current_question_index"] = 0
            
            if session_state["current_question_index"] > len(session_state["questions"]):
                session_state["current_question_index"] = len(session_state["questions"])
            
            logger.info(f"Successfully repaired session state for {session_id}")
            return session_state
            
        except Exception as e:
            logger.error(f"Error repairing session state: {str(e)}")
            raise
    
    def _validate_and_get_question(self, question_id: int, session_state: Dict[str, Any]):
        """Validate question ID and get question object"""
        try:
            # Check if question is in session
            if question_id not in session_state.get("questions", []):
                logger.warning(f"Question {question_id} not in session questions")
                # Allow it but log the issue
            
            # Get question from database
            question = get_question(self.db, question_id)
            if not question:
                logger.warning(f"Question {question_id} not found in database, creating fallback")
                
                # Create fallback question
                class FallbackQuestion:
                    def __init__(self):
                        self.id = question_id
                        self.content = "Please share your thoughts on this topic."
                        self.question_type = "behavioral"
                        self.expected_duration = 3
                        self.role_category = "general"
                        self.difficulty_level = "intermediate"
                        self.generated_by = "fallback"
                        self.created_at = datetime.utcnow()
                
                question = FallbackQuestion()
            
            return question
            
        except Exception as e:
            logger.error(f"Error validating question: {str(e)}")
            raise
    
    def _process_answer_with_retry(self, question, answer_data: AnswerSubmission, session, user_id: int) -> Dict[str, Any]:
        """Process answer evaluation with retry mechanism"""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Get user context
                user = self.db.query(User).filter(User.id == user_id).first()
                context = {
                    "role": getattr(user, 'role', 'job_seeker'),
                    "experience_level": getattr(user, 'experience_level', 'intermediate'),
                    "target_role": session.target_role
                }
                
                # Evaluate answer
                evaluation = self.gemini_service.evaluate_answer(
                    question=question.content,
                    answer=answer_data.answer_text,
                    context=context
                )
                
                logger.info(f"Answer evaluation completed for question {answer_data.question_id}")
                return evaluation
                
            except Exception as e:
                retry_count += 1
                logger.warning(f"Answer evaluation attempt {retry_count} failed: {str(e)}")
                
                if retry_count >= max_retries:
                    logger.error(f"All evaluation attempts failed, using fallback")
                    return self._create_fallback_evaluation(answer_data.answer_text)
                
                # Wait before retry
                import time
                time.sleep(1)
        
        return self._create_fallback_evaluation(answer_data.answer_text)
    
    def _create_fallback_evaluation(self, answer_text: str) -> Dict[str, Any]:
        """Create fallback evaluation when Gemini service fails"""
        try:
            # Simple heuristic-based evaluation
            answer_length = len(answer_text.strip())
            word_count = len(answer_text.split())
            
            # Basic scoring based on length and content
            if word_count < 10:
                score = 40
                feedback = "Try to provide more detailed responses"
            elif word_count < 50:
                score = 65
                feedback = "Good response, consider adding more specific examples"
            else:
                score = 80
                feedback = "Comprehensive response with good detail"
            
            return {
                "overall_score": score,
                "scores": {
                    "content_quality": score,
                    "communication": score,
                    "depth": max(30, min(90, word_count * 2)),
                    "relevance": score
                },
                "strengths": ["Clear communication"],
                "improvements": ["Add more specific examples"],
                "suggestions": [feedback],
                "fallback_evaluation": True
            }
            
        except Exception as e:
            logger.error(f"Error creating fallback evaluation: {str(e)}")
            return {
                "overall_score": 50,
                "scores": {"content_quality": 50, "communication": 50, "depth": 50, "relevance": 50},
                "strengths": ["Response provided"],
                "improvements": ["Continue practicing"],
                "suggestions": ["Keep practicing to improve your interview skills"],
                "fallback_evaluation": True
            }
    
    def _store_performance_metrics_safely(self, session_id: int, answer_data: AnswerSubmission, 
                                        evaluation: Dict[str, Any]) -> Optional:
        """Store performance metrics with comprehensive error handling"""
        try:
            # Process posture data
            body_language_score = self._extract_body_language_score(answer_data.posture_data, evaluation)
            
            # Store performance metric with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
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
                    
                    # Verify storage
                    if performance_metric and performance_metric.id:
                        logger.info(f"Performance metric stored successfully with ID {performance_metric.id}")
                        return performance_metric
                    else:
                        raise ValueError("Performance metric creation returned None or invalid ID")
                        
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to store performance metrics after {max_retries} attempts: {str(e)}")
                        return None
                    else:
                        logger.warning(f"Performance metric storage attempt {attempt + 1} failed, retrying: {str(e)}")
                        import time
                        time.sleep(0.5)
            
            return None
            
        except Exception as e:
            logger.error(f"Error in _store_performance_metrics_safely: {str(e)}")
            return None
    
    def _extract_body_language_score(self, posture_data: Optional[Dict[str, Any]], 
                                   evaluation: Dict[str, Any]) -> float:
        """Extract body language score from posture data"""
        try:
            if not posture_data:
                # Use content-based fallback
                content_score = evaluation.get('overall_score', 0)
                return min(85.0, content_score * 0.8) if content_score > 0 else 50.0
            
            # Try different posture score fields
            score_fields = ['score', 'posture_score', 'overall_score']
            for field in score_fields:
                if field in posture_data and posture_data[field] is not None:
                    try:
                        score = float(posture_data[field])
                        if 0 <= score <= 100:
                            return score
                    except (ValueError, TypeError):
                        continue
            
            # Try individual posture component scores
            individual_scores = []
            component_fields = ['head_tilt_score', 'back_straightness_score', 'shoulder_alignment_score']
            
            for field in component_fields:
                if field in posture_data and posture_data[field] is not None:
                    try:
                        score = float(posture_data[field])
                        if 0 <= score <= 100:
                            individual_scores.append(score)
                    except (ValueError, TypeError):
                        continue
            
            if individual_scores:
                return sum(individual_scores) / len(individual_scores)
            
            # Final fallback
            content_score = evaluation.get('overall_score', 0)
            return min(85.0, content_score * 0.8) if content_score > 0 else 50.0
            
        except Exception as e:
            logger.error(f"Error extracting body language score: {str(e)}")
            return 50.0
    
    def _update_session_state_safely(self, session_id: int, session_state: Dict[str, Any], 
                                   answer_data: AnswerSubmission, evaluation: Dict[str, Any]):
        """Update session state with validation and error handling"""
        try:
            # Prepare updates
            answer_record = {
                "answer": answer_data.answer_text,
                "evaluation": evaluation,
                "timestamp": datetime.utcnow().isoformat(),
                "response_time": answer_data.response_time
            }
            
            # Update answers
            session_state["answers"][str(answer_data.question_id)] = answer_record
            
            # Update progress
            session_state["current_question_index"] = session_state.get("current_question_index", 0) + 1
            session_state["questions_answered"] = len(session_state["answers"])
            session_state["last_activity"] = datetime.utcnow().isoformat()
            
            # Validate updated state
            if not self._validate_session_state(session_state):
                logger.error("Session state validation failed after update")
                raise SessionError("Invalid session state after update")
            
            # Update in session manager
            if not self.session_manager.update_session(session_id, session_state):
                logger.error("Failed to update session state in session manager")
                raise SessionError("Failed to update session state")
            
            logger.info(f"Session state updated successfully for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error updating session state: {str(e)}")
            raise
    
    def _determine_next_steps(self, session_id: int, session_state: Dict[str, Any], user_id: int) -> Dict[str, Any]:
        """Determine next steps after answer submission"""
        try:
            current_index = session_state.get("current_question_index", 0)
            total_questions = len(session_state.get("questions", []))
            
            is_complete = current_index >= total_questions
            next_question_id = None
            
            if not is_complete and current_index < len(session_state["questions"]):
                next_question_id = session_state["questions"][current_index]
            
            if is_complete:
                # Complete the session
                try:
                    self._complete_session(session_id, user_id)
                    logger.info(f"Session {session_id} completed automatically")
                except Exception as e:
                    logger.error(f"Error completing session: {str(e)}")
                    # Don't fail the answer submission if completion fails
            
            return {
                "is_complete": is_complete,
                "next_question_id": next_question_id,
                "progress": {
                    "current_question": current_index,
                    "total_questions": total_questions,
                    "completion_percentage": (current_index / total_questions * 100) if total_questions > 0 else 100
                }
            }
            
        except Exception as e:
            logger.error(f"Error determining next steps: {str(e)}")
            return {
                "is_complete": False,
                "next_question_id": None,
                "progress": {"current_question": 0, "total_questions": 0, "completion_percentage": 0}
            }
    
    def _build_answer_response(self, question_id: int, evaluation: Dict[str, Any], 
                             next_steps: Dict[str, Any], performance_metric) -> Dict[str, Any]:
        """Build comprehensive answer submission response"""
        try:
            response = {
                "question_id": question_id,
                "submitted": True,
                "next_question_id": next_steps.get("next_question_id"),
                "session_completed": next_steps.get("is_complete", False),
                "progress": next_steps.get("progress", {}),
                "real_time_feedback": {
                    "score": evaluation.get('overall_score', 0),
                    "quick_tip": evaluation.get('suggestions', [''])[0] if evaluation.get('suggestions') else None,
                    "strengths": evaluation.get('strengths', []),
                    "fallback_used": evaluation.get('fallback_evaluation', False)
                },
                "performance_metric_stored": performance_metric is not None,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Add performance metric ID if available
            if performance_metric and hasattr(performance_metric, 'id'):
                response["performance_metric_id"] = performance_metric.id
            
            return response
            
        except Exception as e:
            logger.error(f"Error building answer response: {str(e)}")
            return {
                "question_id": question_id,
                "submitted": True,
                "error": "Response building failed",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def pause_session(self, session_id: int, user_id: int) -> bool:
        """Pause interview session"""
        session = self.get_session_by_id(session_id, user_id)
        if not session or session.status != SessionStatus.ACTIVE:
            return False
        
        # Update session status
        update_data = InterviewSessionUpdate(status=SessionStatus.PAUSED)
        update_interview_session(self.db, session_id, update_data)
        
        # Update session state
        session_state = self.session_manager.get_session(session_id)
        if session_state:
            session_state["paused_at"] = datetime.utcnow().isoformat()
            self.session_manager.update_session(session_id, session_state)
        
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
        session_state = self.session_manager.get_session(session_id)
        if session_state:
            paused_at_str = session_state.get("paused_at")
            if paused_at_str:
                try:
                    paused_at = datetime.fromisoformat(paused_at_str)
                    pause_duration = (datetime.utcnow() - paused_at).total_seconds()
                    session_state["paused_time"] = session_state.get("paused_time", 0) + pause_duration
                    del session_state["paused_at"]
                    self.session_manager.update_session(session_id, session_state)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid paused_at timestamp for session {session_id}")
        
        return True
    
    def complete_session(self, session_id: int, user_id: int) -> Dict[str, Any]:
        """Manually complete interview session"""
        return self._complete_session(session_id, user_id)
    
    def _complete_session(self, session_id: int, user_id: int) -> Dict[str, Any]:
        """Internal method to complete session with proper scoring"""
        session = self.get_session_by_id(session_id, user_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Skip if already completed
        if session.status == SessionStatus.COMPLETED:
            logger.info(f"Session {session_id} already completed")
            return {"message": "Session already completed", "session_id": session_id}
        
        # Calculate overall score and performance score
        performance_metrics = self.db.query(PerformanceMetrics).filter(
            PerformanceMetrics.session_id == session_id
        ).all()
        
        # Calculate comprehensive performance score using difficulty service
        performance_score = self.difficulty_service.calculate_performance_score(session_id)
        logger.info(f"Calculated performance score for session {session_id}: {performance_score}")
        
        # Use the same comprehensive score for overall_score to maintain consistency
        # Both overall_score and performance_score should represent the same weighted calculation
        overall_score = performance_score
        
        # Ensure we have a reasonable score even if calculation fails
        if overall_score == 0 and performance_metrics:
            # Fallback: use content quality average if comprehensive calculation fails
            valid_content_scores = [m.content_quality_score for m in performance_metrics if m.content_quality_score is not None]
            overall_score = sum(valid_content_scores) / len(valid_content_scores) if valid_content_scores else 50.0
            logger.warning(f"Using content quality fallback for session {session_id}: {overall_score}")
        elif overall_score == 0:
            # If no metrics at all, assign neutral score for completion
            overall_score = 50.0
            logger.warning(f"No performance metrics found for session {session_id}, assigning neutral score")
        
        # Calculate next difficulty based on current session performance (70% weight)
        next_difficulty = self.difficulty_service.get_next_difficulty(
            user_id=user_id, 
            target_role=session.target_role,
            current_session_score=performance_score
        )
        logger.info(f"Calculated next difficulty for user {user_id}: {next_difficulty}")
        
        # Update session with both scores and next difficulty
        update_data = InterviewSessionUpdate(
            status=SessionStatus.COMPLETED,
            overall_score=overall_score,
            completed_at=datetime.utcnow()
        )
        updated_session = update_interview_session(self.db, session_id, update_data)
        
        # Update performance score and next difficulty separately (not in schema yet)
        if updated_session:
            updated_session.performance_score = performance_score
            updated_session.next_difficulty = next_difficulty
            self.db.commit()
            logger.info(f"Session {session_id} completed with overall_score: {overall_score}, performance_score: {performance_score}, next_difficulty: {next_difficulty}")
        
        # Finalize session difficulty state
        try:
            final_difficulty = self.session_difficulty_service.finalize_session_difficulty(session_id)
            if final_difficulty:
                logger.info(f"Finalized difficulty for session {session_id}: {final_difficulty}")
            else:
                logger.warning(f"Could not finalize difficulty for session {session_id}")
        except Exception as difficulty_error:
            logger.error(f"Error finalizing session difficulty for session {session_id}: {str(difficulty_error)}")
            # Don't fail the entire completion process
        
        # Clean up session state and difficulty cache
        self.session_manager.delete_session(session_id)
        
        # Clean up session difficulty cache
        try:
            self.session_difficulty_service.clear_session_cache(session_id)
            logger.debug(f"Cleared difficulty cache for completed session {session_id}")
        except Exception as cache_error:
            logger.warning(f"Error clearing difficulty cache for session {session_id}: {str(cache_error)}")
        
        # Generate comprehensive feedback
        session_state = self.session_manager.get_session(session_id) or {}
        performance_data = {
            "session_id": session_id,
            "answers": session_state.get("answers", {}),
            "overall_score": overall_score,
            "performance_score": performance_score,
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
        
        # Generate learning resource recommendations based on performance
        recommendations = None
        try:
            if performance_metrics:
                # Calculate average scores for each category
                valid_content_scores = [m.content_quality_score for m in performance_metrics if m.content_quality_score is not None]
                valid_body_scores = [m.body_language_score for m in performance_metrics if m.body_language_score is not None]
                valid_tone_scores = [m.tone_confidence_score for m in performance_metrics if m.tone_confidence_score is not None]
                
                avg_content = sum(valid_content_scores) / len(valid_content_scores) if valid_content_scores else 50.0
                avg_body_language = sum(valid_body_scores) / len(valid_body_scores) if valid_body_scores else 50.0
                avg_tone = sum(valid_tone_scores) / len(valid_tone_scores) if valid_tone_scores else 50.0
                
                # Create recommendation request
                recommendation_request = RecommendationRequest(
                    body_language=avg_body_language,
                    voice_analysis=avg_tone,
                    content_quality=avg_content,
                    overall=overall_score
                )
                
                # Get personalized learning resource recommendations
                recommendations = self.recommendation_service.get_recommendations(user_id, recommendation_request)
                logger.info(f"Generated learning resource recommendations for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error generating learning resource recommendations: {str(e)}")
            recommendations = None
        
        # Clean up session state
        self.session_manager.delete_session(session_id)
        
        return {
            "session_id": session_id,
            "overall_score": overall_score,
            "feedback": feedback,
            "learning_recommendations": recommendations.model_dump() if recommendations else None,
            "completed_at": datetime.utcnow().isoformat()
        }
    
    def create_practice_session(self, original_session: InterviewSession, user: User, adaptive_difficulty: str = None) -> Dict[str, Any]:
        """Create a new practice session based on an existing session using SessionSettingsManager with adaptive difficulty"""
        
        try:
            logger.info(f"Creating practice session based on session {original_session.id} for user {user.id} with adaptive difficulty: {adaptive_difficulty}")
            
            # Use SessionSettingsManager to create practice session with proper inheritance
            result = self.session_settings_manager.create_practice_session(original_session.id, user)
            practice_session = result['session']
            inherited_settings = result['inherited_settings']
            
            # Override difficulty with adaptive difficulty if provided
            if adaptive_difficulty:
                practice_session.difficulty_level = adaptive_difficulty
                inherited_settings['difficulty_level'] = adaptive_difficulty
                self.db.commit()
                logger.info(f"Updated practice session {practice_session.id} with adaptive difficulty: {adaptive_difficulty}")
            
            logger.info(f"Created practice session {practice_session.id} with inherited question count: {inherited_settings['question_count']}")
            
            # Generate fresh questions using inherited count and adaptive difficulty
            original_questions = self.db.query(PerformanceMetrics.question_id).filter(
                PerformanceMetrics.session_id == original_session.id
            ).all()
            original_question_ids = [q.question_id for q in original_questions]
            
            # Get questions for the session using inherited count and adaptive difficulty
            questions = self.question_service.get_random_questions(
                role_category=practice_session.target_role,
                difficulty_level=adaptive_difficulty or practice_session.difficulty_level,
                count=inherited_settings['question_count']  # Use inherited count instead of hardcoded 5
            )
            
            # Filter out questions from original session if possible
            if original_question_ids and len(questions) > len(original_question_ids):
                questions = [q for q in questions if q.id not in original_question_ids][:inherited_settings['question_count']]
            
            # Initialize session state with inherited settings
            session_state = {
                "user_id": user.id,
                "session_id": practice_session.id,
                "questions": [q.id for q in questions],
                "current_question_index": 0,
                "answers": {},
                "start_time": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat(),
                "session_type": practice_session.session_type,
                "target_role": practice_session.target_role,
                "difficulty_level": practice_session.difficulty_level,
                "total_questions": len(questions),
                "questions_answered": 0,
                "is_practice": True,
                "parent_session_id": original_session.id,
                "inherited_question_count": inherited_settings['question_count'],
                "session_metadata": {
                    "created_at": datetime.utcnow().isoformat(),
                    "version": "1.0",
                    "question_ids": [q.id for q in questions],
                    "inherited_from": original_session.id
                }
            }
            
            if not self.session_manager.create_session(practice_session.id, session_state):
                raise ValueError("Failed to initialize practice session state")
            
            # Convert questions to dictionaries for JSON serialization
            questions_data = self._serialize_questions(questions)
            
            # Prepare configuration with inherited settings
            configuration = {
                "session_id": practice_session.id,
                "total_questions": len(questions),
                "time_limit": practice_session.duration,
                "difficulty_level": practice_session.difficulty_level,
                "session_mode": "practice_again",
                "parent_session_id": original_session.id,
                "inherited_question_count": inherited_settings['question_count'],
                "validation_passed": result['validation']['is_valid']
            }
            
            logger.info(f"Practice session {practice_session.id} initialized with {len(questions)} questions (inherited count: {inherited_settings['question_count']})")
            
            return {
                "session": practice_session,
                "questions": questions_data,
                "configuration": configuration,
                "inherited_settings": inherited_settings
            }
            
        except Exception as e:
            logger.error(f"Error creating practice session: {str(e)}")
            self.db.rollback()
            raise ValueError(f"Failed to create practice session: {str(e)}")
    
    def get_session_progress(self, session_id: int, user_id: int) -> Dict[str, Any]:
        """Get current session progress"""
        session = self.get_session_by_id(session_id, user_id)
        if not session:
            return {}
        
        session_state = self.session_manager.get_session(session_id)
        if not session_state:
            return {}
        
        start_time_str = session_state.get("start_time")
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                start_time = datetime.utcnow()
        else:
            start_time = datetime.utcnow()
        
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
            
            # Calculate aggregate scores with proper handling of zero values
            avg_content = sum(q['content_score'] for q in questions_data) / len(questions_data)
            avg_body_language = sum(q['body_language_score'] for q in questions_data) / len(questions_data)
            avg_tone = sum(q['tone_score'] for q in questions_data) / len(questions_data)
            
            # Use the difficulty service to calculate the proper performance score
            calculated_performance_score = self.difficulty_service.calculate_performance_score(session_id)
            
            # If we have a calculated performance score, use it; otherwise use the average
            if calculated_performance_score > 0:
                overall_score = calculated_performance_score
            else:
                overall_score = (avg_content + avg_body_language + avg_tone) / 3
                # Ensure minimum score for completed sessions
                if overall_score == 0 and len(questions_data) > 0:
                    overall_score = 45.0  # Give some credit for completing the session
            
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
            
            # Generate learning resource recommendations
            learning_recommendations = None
            try:
                recommendation_request = RecommendationRequest(
                    body_language=avg_body_language,
                    voice_analysis=avg_tone,
                    content_quality=avg_content,
                    overall=overall_score
                )
                learning_recommendations = self.recommendation_service.get_recommendations(user_id, recommendation_request)
                logger.info(f"Generated learning resource recommendations for session feedback")
            except Exception as e:
                logger.error(f"Error generating learning recommendations for feedback: {str(e)}")
            
            # Get difficulty information for the user with consistent labels
            difficulty_stats = self.difficulty_service.get_difficulty_statistics(user_id)
            current_difficulty = difficulty_stats.get('current_difficulty', 'medium')
            next_difficulty = difficulty_stats.get('next_difficulty', 'medium')
            
            # Get consistent difficulty labels
            current_difficulty_label = self.difficulty_mapping.get_difficulty_label(
                self.difficulty_mapping.normalize_difficulty_input(current_difficulty)
            )
            next_difficulty_label = self.difficulty_mapping.get_difficulty_label(
                self.difficulty_mapping.normalize_difficulty_input(next_difficulty)
            )
            
            # Update session performance score in database if it's not set
            if session.performance_score is None or session.performance_score == 0:
                session.performance_score = overall_score
                self.db.commit()
                logger.info(f"Updated session {session_id} performance score to {overall_score}")
            
            # Update user's difficulty level if there's a recommended change
            if current_difficulty != next_difficulty and session.status == 'completed':
                try:
                    # Update the most recent session's difficulty level to reflect the new level
                    # This ensures future sessions will use the new difficulty
                    session.difficulty_level = next_difficulty
                    self.db.commit()
                    logger.info(f"Updated user {user_id} difficulty level from {current_difficulty} to {next_difficulty} based on performance")
                except Exception as e:
                    logger.error(f"Error updating difficulty level: {str(e)}")
                    # Don't fail the entire feedback generation if difficulty update fails
                    pass
            
            # Structure the response
            feedback_response = {
                'session': {
                    'id': session.id,
                    'target_role': session.target_role,
                    'session_type': session.session_type,
                    'overall_score': int(overall_score),
                    'current_difficulty': current_difficulty_label,
                    'next_difficulty': next_difficulty_label
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
                },
                'difficulty_info': {
                    'current_difficulty': current_difficulty_label,
                    'next_difficulty': next_difficulty_label,
                    'difficulty_change_reason': self._get_difficulty_change_reason(current_difficulty_label, next_difficulty_label, overall_score)
                },
                'learning_recommendations': learning_recommendations.model_dump() if learning_recommendations else None
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
                    'overall_score': 0,
                    'current_difficulty': self.difficulty_mapping.get_difficulty_label(2),  # Medium
                    'next_difficulty': self.difficulty_mapping.get_difficulty_label(2)  # Medium
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
                },
                'difficulty_info': {
                    'current_difficulty': self.difficulty_mapping.get_difficulty_label(2),  # Medium
                    'next_difficulty': self.difficulty_mapping.get_difficulty_label(2),  # Medium
                    'difficulty_change_reason': 'Complete more sessions for difficulty adjustment'
                }
            }
    
    def _get_difficulty_change_reason(self, current_difficulty: str, next_difficulty: str, performance_score: float) -> str:
        """Generate explanation for difficulty level changes using consistent labels"""
        if current_difficulty == next_difficulty:
            return f"Maintaining {current_difficulty} difficulty based on current performance"
        else:
            # Compare internal levels to determine direction
            current_level = self.difficulty_mapping.normalize_difficulty_input(current_difficulty)
            next_level = self.difficulty_mapping.normalize_difficulty_input(next_difficulty)
            
            if next_level > current_level:
                return f"Increasing to {next_difficulty} due to strong performance ({performance_score:.0f}/100)"
            else:
                return f"Adjusting to {next_difficulty} to better match your current skill level"
    
    def get_user_sessions(
        self, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 100, 
        status: Optional[str] = None,
        include_family_info: bool = False
    ) -> List[InterviewSession]:
        """Get user's interview sessions with filtering and optional family information"""
        query = self.db.query(InterviewSession).filter(InterviewSession.user_id == user_id)
        
        if status:
            query = query.filter(InterviewSession.status == status)
        
        sessions = query.order_by(InterviewSession.created_at.desc()).offset(skip).limit(limit).all()
        
        if include_family_info:
            # Add family information to each session
            for session in sessions:
                session.family_info = self._get_session_family_info(session, user_id)
        
        return sessions
    
    def _get_session_family_info(self, session: InterviewSession, user_id: int) -> Dict[str, Any]:
        """Get family information for a session"""
        try:
            # Determine if this is an original session or practice session
            is_original = session.parent_session_id is None
            
            if is_original:
                # Count practice sessions
                practice_count = self.db.query(InterviewSession).filter(
                    InterviewSession.parent_session_id == session.id,
                    InterviewSession.user_id == user_id
                ).count()
                
                return {
                    "is_original": True,
                    "practice_count": practice_count,
                    "has_practices": practice_count > 0,
                    "original_session_id": session.id,
                    "session_family_size": practice_count + 1
                }
            else:
                # Get original session info
                original_session = self.db.query(InterviewSession).filter(
                    InterviewSession.id == session.parent_session_id,
                    InterviewSession.user_id == user_id
                ).first()
                
                # Count total practice sessions in family
                total_practices = self.db.query(InterviewSession).filter(
                    InterviewSession.parent_session_id == session.parent_session_id,
                    InterviewSession.user_id == user_id
                ).count()
                
                return {
                    "is_original": False,
                    "is_practice": True,
                    "original_session_id": session.parent_session_id,
                    "original_session_role": original_session.target_role if original_session else None,
                    "original_session_date": original_session.created_at.isoformat() if original_session else None,
                    "practice_number": self._get_practice_number(session, user_id),
                    "session_family_size": total_practices + 1
                }
        except Exception as e:
            logger.error(f"Error getting family info for session {session.id}: {str(e)}")
            return {"is_original": True, "practice_count": 0, "has_practices": False}
    
    def _get_practice_number(self, session: InterviewSession, user_id: int) -> int:
        """Get the practice number for a practice session (1st practice, 2nd practice, etc.)"""
        try:
            # Get all practice sessions for the same parent, ordered by creation date
            practice_sessions = self.db.query(InterviewSession).filter(
                InterviewSession.parent_session_id == session.parent_session_id,
                InterviewSession.user_id == user_id,
                InterviewSession.created_at <= session.created_at
            ).order_by(InterviewSession.created_at.asc()).all()
            
            # Find the position of this session
            for i, practice_session in enumerate(practice_sessions):
                if practice_session.id == session.id:
                    return i + 1
            
            return 1  # Default to 1 if not found
        except Exception as e:
            logger.error(f"Error getting practice number for session {session.id}: {str(e)}")
            return 1
    
    def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user statistics with difficulty and performance data"""
        
        try:
            # Get user's sessions
            sessions = get_user_sessions(self.db, user_id, limit=50)
            
            # Get difficulty statistics
            difficulty_stats = self.difficulty_service.get_difficulty_statistics(user_id)
            performance_trend = self.difficulty_service.get_performance_trend(user_id)
            
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
                    },
                    "difficulty_info": difficulty_stats,
                    "performance_trend": performance_trend
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
                },
                "difficulty_info": difficulty_stats,
                "performance_trend": performance_trend
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
        logger.info(f"=== GET SESSION DETAILS DEBUG ===")
        logger.info(f"Getting session details for session_id: {session_id}, user_id: {user_id}")
        
        session = self.get_session_by_id(session_id, user_id)
        if not session:
            logger.error(f"Session {session_id} not found for user {user_id}")
            return None
        
        logger.info(f"Session found: {session.id}, target_role: {session.target_role}, status: {session.status}")
        
        # Get performance metrics
        metrics = self.db.query(PerformanceMetrics).filter(
            PerformanceMetrics.session_id == session_id
        ).all()
        
        # Get questions for the session
        questions = []
        session_state = self.session_manager.get_session(session_id)
        
        if session_state and "questions" in session_state:
            # Get question objects from question IDs in active session
            question_ids = session_state["questions"]
            questions = self.db.query(Question).filter(Question.id.in_(question_ids)).all()
            logger.info(f"Found {len(questions)} questions from active session state")
        else:
            # If session is not active, generate questions based on session configuration
            logger.info(f"Session {session_id} not in active state, generating questions")
            try:
                # Get user for context
                user = self.db.query(User).filter(User.id == user_id).first()
                if user:
                    # Generate questions based on session parameters
                    questions = self.question_service.get_questions_for_session(
                        role=session.target_role,
                        difficulty=session.difficulty_level or "intermediate",
                        session_type=session.session_type.value if session.session_type else "behavioral",
                        count=5,  # Default question count
                        user_id=user_id
                    )
                    logger.info(f"Generated {len(questions)} questions for session {session_id}")
                    
                    # Recreate session state if questions were generated
                    if questions:
                        new_session_state = {
                            "user_id": user_id,
                            "questions": [q.id for q in questions],
                            "current_question_index": 0,
                            "start_time": datetime.utcnow().isoformat(),
                            "answers": {},
                            "paused_time": 0
                        }
                        self.session_manager.create_session(session_id, new_session_state)
                        logger.info(f"Recreated session state for session {session_id}")
                else:
                    logger.error(f"User {user_id} not found")
            except Exception as e:
                logger.error(f"Error generating questions for session {session_id}: {str(e)}")
                questions = []
        
        # Convert questions to dictionaries for JSON serialization
        questions_data = []
        for q in questions:
            questions_data.append({
                "id": q.id,
                "content": q.content,
                "question_text": q.content,  # Add alias for frontend compatibility
                "question_type": q.question_type,
                "role_category": q.role_category,
                "difficulty_level": q.difficulty_level,
                "expected_duration": q.expected_duration,
                "generated_by": q.generated_by,
                "created_at": q.created_at.isoformat() if q.created_at else None
            })
        
        logger.info(f"=== FINAL SESSION DETAILS ===")
        logger.info(f"Session ID: {session.id}")
        logger.info(f"Questions count: {len(questions_data)}")
        logger.info(f"Metrics count: {len(metrics)}")
        logger.info(f"Questions data: {[q['content'][:50] + '...' for q in questions_data]}")
        logger.info(f"=== END SESSION DETAILS DEBUG ===")
        
        return {
            "session": session,
            "questions": questions_data,
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
        self.session_manager.delete_session(session_id)
        
        return {
            "session": updated_session,
            "summary": summary
        }
    
    def _check_and_apply_adaptive_difficulty_adjustment(
        self, 
        session_id: int, 
        evaluation: Dict[str, Any], 
        session_state: Dict[str, Any], 
        user_id: int
    ) -> None:
        """
        Check if adaptive difficulty adjustment is needed during the session
        
        This method analyzes the current answer evaluation and session progress
        to determine if the difficulty should be adjusted in real-time.
        """
        try:
            logger.info(f"Checking adaptive difficulty adjustment for session {session_id}")
            
            # Get current session difficulty state
            difficulty_state = self.session_difficulty_service.get_session_difficulty_state(session_id)
            if not difficulty_state:
                logger.warning(f"No difficulty state found for session {session_id}")
                return
            
            # Don't adjust if session is already finalized
            if difficulty_state.is_finalized:
                logger.info(f"Session {session_id} difficulty is already finalized")
                return
            
            # Get current question index to determine if we should adjust
            current_question_index = session_state.get("current_question_index", 0)
            total_questions = session_state.get("total_questions", 5)
            
            # Only consider adjustments after at least 2 questions and before the last question
            if current_question_index < 2 or current_question_index >= total_questions - 1:
                logger.info(f"Not adjusting difficulty at question {current_question_index} of {total_questions}")
                return
            
            # Analyze recent performance for adjustment decision
            adjustment_needed, new_difficulty, reason = self._analyze_performance_for_adjustment(
                session_id, evaluation, difficulty_state, current_question_index
            )
            
            if adjustment_needed and new_difficulty != difficulty_state.current_difficulty:
                # Apply the difficulty adjustment
                success = self.session_difficulty_service.update_session_difficulty(
                    session_id, 
                    new_difficulty, 
                    reason, 
                    current_question_index
                )
                
                if success:
                    logger.info(f"Applied adaptive difficulty adjustment for session {session_id}: "
                              f"{difficulty_state.current_difficulty} -> {new_difficulty} ({reason})")
                    
                    # Notify about the difficulty change (could be used for UI updates)
                    self._notify_difficulty_change(session_id, difficulty_state.current_difficulty, 
                                                 new_difficulty, reason, user_id)
                else:
                    logger.warning(f"Failed to apply difficulty adjustment for session {session_id}")
            else:
                logger.debug(f"No difficulty adjustment needed for session {session_id}")
                
        except Exception as e:
            logger.error(f"Error in adaptive difficulty adjustment for session {session_id}: {str(e)}")
    
    def _analyze_performance_for_adjustment(
        self, 
        session_id: int, 
        current_evaluation: Dict[str, Any], 
        difficulty_state, 
        question_index: int
    ) -> Tuple[bool, str, str]:
        """
        Analyze performance to determine if difficulty adjustment is needed
        
        Returns:
            Tuple of (adjustment_needed, new_difficulty, reason)
        """
        try:
            # Get recent performance metrics for this session
            from app.db.models import PerformanceMetrics
            
            recent_metrics = self.db.query(PerformanceMetrics).filter(
                PerformanceMetrics.session_id == session_id
            ).order_by(PerformanceMetrics.id.desc()).limit(3).all()
            
            if len(recent_metrics) < 2:
                # Not enough data for adjustment
                return False, difficulty_state.current_difficulty, "insufficient_data"
            
            # Calculate average performance from recent answers
            content_scores = [m.content_quality_score for m in recent_metrics if m.content_quality_score is not None]
            avg_content_score = sum(content_scores) / len(content_scores) if content_scores else 50.0
            
            current_difficulty = difficulty_state.current_difficulty
            
            # Determine if adjustment is needed based on performance thresholds
            if avg_content_score >= 85 and current_difficulty != "expert":
                # Excellent performance - increase difficulty
                new_difficulty = self._get_next_higher_difficulty(current_difficulty)
                return True, new_difficulty, f"excellent_performance_avg_{avg_content_score:.0f}"
                
            elif avg_content_score <= 25 and current_difficulty != "easy":
                # Poor performance - decrease difficulty
                new_difficulty = self._get_next_lower_difficulty(current_difficulty)
                return True, new_difficulty, f"poor_performance_avg_{avg_content_score:.0f}"
                
            elif avg_content_score >= 75 and current_difficulty == "easy":
                # Good performance on easy - move to medium
                return True, "medium", f"good_performance_on_easy_{avg_content_score:.0f}"
                
            elif avg_content_score <= 35 and current_difficulty == "expert":
                # Struggling on expert - move to hard
                return True, "hard", f"struggling_on_expert_{avg_content_score:.0f}"
            
            # No adjustment needed
            return False, current_difficulty, "performance_within_range"
            
        except Exception as e:
            logger.error(f"Error analyzing performance for adjustment: {str(e)}")
            return False, difficulty_state.current_difficulty, "analysis_error"
    
    def _get_next_higher_difficulty(self, current_difficulty: str) -> str:
        """Get the next higher difficulty level"""
        difficulty_order = ["easy", "medium", "hard", "expert"]
        try:
            current_index = difficulty_order.index(current_difficulty)
            if current_index < len(difficulty_order) - 1:
                return difficulty_order[current_index + 1]
        except ValueError:
            pass
        return current_difficulty
    
    def _get_next_lower_difficulty(self, current_difficulty: str) -> str:
        """Get the next lower difficulty level"""
        difficulty_order = ["easy", "medium", "hard", "expert"]
        try:
            current_index = difficulty_order.index(current_difficulty)
            if current_index > 0:
                return difficulty_order[current_index - 1]
        except ValueError:
            pass
        return current_difficulty
    
    def _notify_difficulty_change(
        self, 
        session_id: int, 
        old_difficulty: str, 
        new_difficulty: str, 
        reason: str, 
        user_id: int
    ) -> None:
        """
        Notify about difficulty changes for potential UI updates
        
        This method can be extended to send real-time notifications to the frontend
        """
        try:
            logger.info(f"Difficulty change notification for session {session_id}: "
                       f"{old_difficulty} -> {new_difficulty} (reason: {reason})")
            
            # Store the notification in session state for potential retrieval
            session_state = self.session_manager.get_session(session_id)
            if session_state:
                if "difficulty_notifications" not in session_state:
                    session_state["difficulty_notifications"] = []
                
                session_state["difficulty_notifications"].append({
                    "old_difficulty": old_difficulty,
                    "new_difficulty": new_difficulty,
                    "reason": reason,
                    "timestamp": datetime.utcnow().isoformat(),
                    "question_index": session_state.get("current_question_index", 0)
                })
                
                self.session_manager.update_session(session_id, session_state)
                
        except Exception as e:
            logger.error(f"Error sending difficulty change notification: {str(e)}")
    
    def _calculate_recommended_difficulty(self, current_difficulty: str, overall_score: float) -> str:
        """
        Calculate recommended difficulty for next session based on current session performance
        
        Args:
            current_difficulty: Current session difficulty level
            overall_score: Overall performance score (0-100)
            
        Returns:
            Recommended difficulty level for next session
        """
        try:
            logger.info(f"=== RECOMMENDED DIFFICULTY CALCULATION ===")
            logger.info(f"Input: current_difficulty={current_difficulty}, overall_score={overall_score}")
            
            # Performance-based difficulty adjustment logic
            if overall_score < 20:  # Very poor performance
                if current_difficulty in ['hard', 'expert']:
                    result = 'easy'
                elif current_difficulty == 'medium':
                    result = 'easy'
                else:
                    result = 'easy'  # Stay at easy if already at easy
                logger.info(f"Very poor performance (<20): {current_difficulty} -> {result}")
                return result
            elif overall_score < 40:  # Poor performance
                if current_difficulty in ['hard', 'expert']:
                    result = 'medium'
                elif current_difficulty == 'medium':
                    result = 'easy'
                else:
                    result = current_difficulty  # Stay at easy if already at easy
                logger.info(f"Poor performance (<40): {current_difficulty} -> {result}")
                return result
            elif overall_score > 80:  # Excellent performance
                if current_difficulty == 'easy':
                    result = 'medium'
                elif current_difficulty == 'medium':
                    result = 'hard'
                elif current_difficulty == 'hard':
                    result = 'expert'
                else:
                    result = current_difficulty  # Stay at expert if already at expert
                logger.info(f"Excellent performance (>80): {current_difficulty} -> {result}")
                return result
            else:  # Good performance, maintain current level
                logger.info(f"Good performance (40-80): {current_difficulty} -> {current_difficulty} (maintained)")
                return current_difficulty
                
        except Exception as e:
            logger.error(f"Error calculating recommended difficulty: {str(e)}")
            return current_difficulty  # Fallback to current difficulty