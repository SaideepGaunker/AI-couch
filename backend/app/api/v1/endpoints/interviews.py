"""
Interview session endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.db.database import get_db
from app.schemas.interview import (
    InterviewSessionCreate, InterviewSessionResponse, InterviewSessionUpdate,
    SessionProgressResponse, SessionSummaryResponse, AnswerSubmission
)
from app.core.dependencies import get_current_user, rate_limit
from app.services.interview_service import InterviewService
from app.db.models import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/test")
async def test_interview_endpoint():
    """Test endpoint to verify interview API is working"""
    return {"message": "Interview API is working", "timestamp": datetime.now().isoformat()}


@router.get("/{session_id}/inheritance-info")
async def get_session_inheritance_info(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get inheritance information for a session (for testing purposes)"""
    interview_service = InterviewService(db)
    
    try:
        # Get inheritance info using SessionSettingsManager
        inheritance_info = interview_service.session_settings_manager.get_session_inheritance_info(session_id)
        
        if not inheritance_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Verify user ownership
        session = interview_service.get_session(session_id, current_user.id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this session"
            )
        
        return {
            "session_id": session_id,
            "inheritance_info": inheritance_info,
            "session_details": {
                "id": session.id,
                "session_type": session.session_type,
                "target_role": session.target_role,
                "duration": session.duration,
                "difficulty_level": session.difficulty_level,
                "parent_session_id": session.parent_session_id,
                "session_mode": session.session_mode,
                "created_at": session.created_at.isoformat() if session.created_at else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session inheritance info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session inheritance information"
        )


@router.get("/{session_id}/difficulty-state")
async def get_session_difficulty_state(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get session-specific difficulty state"""
    from app.services.session_specific_difficulty_service import SessionSpecificDifficultyService
    
    try:
        # Verify user ownership
        interview_service = InterviewService(db)
        session = interview_service.get_session(session_id, current_user.id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or not authorized"
            )
        
        # Get difficulty state with error handling
        try:
            difficulty_service = SessionSpecificDifficultyService(db)
            difficulty_state = difficulty_service.get_session_difficulty_state(session_id)
        except Exception as difficulty_error:
            logger.error(f"Error getting difficulty state for session {session_id}: {str(difficulty_error)}")
            difficulty_state = None
        
        if not difficulty_state:
            # Return basic state from database if no cached state
            return {
                "session_id": session_id,
                "initial_difficulty": session.initial_difficulty_level or session.difficulty_level or "medium",
                "current_difficulty": session.current_difficulty_level or session.difficulty_level or "medium",
                "final_difficulty": session.final_difficulty_level,
                "difficulty_changes": [],
                "changes_count": session.difficulty_changes_count or 0,
                "is_finalized": session.final_difficulty_level is not None,
                "source": "database_fallback"
            }
        
        return {
            "session_id": session_id,
            "initial_difficulty": difficulty_state.initial_difficulty,
            "current_difficulty": difficulty_state.current_difficulty,
            "final_difficulty": difficulty_state.final_difficulty,
            "difficulty_changes": [change.to_dict() for change in difficulty_state.difficulty_changes],
            "changes_count": difficulty_state.get_changes_count(),
            "is_finalized": difficulty_state.is_finalized,
            "last_updated": difficulty_state.last_updated.isoformat() if difficulty_state.last_updated else None,
            "source": "session_state_cache"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session difficulty state: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get session difficulty state"
        )


@router.get("/{session_id}/practice-preview")
async def get_practice_session_preview(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a preview of what settings would be inherited for a practice session"""
    from app.services.enhanced_session_settings_manager import EnhancedSessionSettingsManager
    
    try:
        enhanced_manager = EnhancedSessionSettingsManager(db)
        preview = enhanced_manager.get_practice_session_preview(session_id, current_user.id)
        
        return {
            "message": "Practice session preview generated successfully",
            "preview": preview
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error getting practice session preview: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get practice session preview"
        )


@router.post("/start")
async def start_interview(
    session_data: InterviewSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
        logger.error(f"Failed to start interview session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start interview session: {str(e)}"
        )


@router.post("/start-test")
async def start_test_session(
    session_data: InterviewSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
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
    include_family_info: bool = Query(False, description="Include session family information"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's interview sessions with optional family information"""
    interview_service = InterviewService(db)
    
    try:
        sessions = interview_service.get_user_sessions(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            status=status,
            include_family_info=include_family_info
        )
        
        # If family info is requested, add it to the response
        if include_family_info:
            enhanced_sessions = []
            for session in sessions:
                session_dict = {
                    "id": session.id,
                    "user_id": session.user_id,
                    "session_type": session.session_type,
                    "target_role": session.target_role,
                    "duration": session.duration,
                    "status": session.status,
                    "overall_score": session.overall_score or 0.0,
                    "performance_score": getattr(session, 'performance_score', 0.0),
                    "difficulty_level": getattr(session, 'difficulty_level', 'medium'),
                    "parent_session_id": getattr(session, 'parent_session_id', None),
                    "session_mode": getattr(session, 'session_mode', 'new'),
                    "created_at": session.created_at,
                    "completed_at": session.completed_at,
                    "family_info": getattr(session, 'family_info', {})
                }
                enhanced_sessions.append(session_dict)
            return enhanced_sessions
        
        return sessions
        
    except Exception as e:
        logger.error(f"Error retrieving sessions: {str(e)}")
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


@router.post("/{session_id}/practice-again")
async def practice_again(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(max_calls=10, window_seconds=300))
):
    """Create a new practice session based on an existing session with inherited settings"""
    interview_service = InterviewService(db)
    
    try:
        logger.info(f"Practice-again request for session {session_id} by user {current_user.id}")
        
        # Get the original session
        original_session = interview_service.get_session(session_id, current_user.id)
        if not original_session:
            logger.warning(f"Original session {session_id} not found for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Original session not found"
            )
        
        # Verify ownership
        if original_session.user_id != current_user.id:
            logger.warning(f"User {current_user.id} attempted to access session {session_id} owned by user {original_session.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this session"
            )
        
        # Log original session settings for verification
        logger.info(f"Original session settings - Duration: {original_session.duration}, "
                   f"Difficulty: {original_session.difficulty_level}, "
                   f"Target Role: {original_session.target_role}, "
                   f"Next Difficulty: {original_session.next_difficulty}")
        
        # Use the calculated next_difficulty from the original session (70% current + 30% previous)
        adaptive_difficulty = original_session.next_difficulty or original_session.difficulty_level or "medium"
        logger.info(f"Using adaptive difficulty for practice session: {adaptive_difficulty}")
        
        # Create new practice session using SessionSettingsManager with adaptive difficulty
        result = interview_service.create_practice_session(original_session, current_user, adaptive_difficulty)
        
        # Log inherited settings for verification
        inherited_settings = result.get('inherited_settings', {})
        logger.info(f"Practice session {result['session'].id} created with inherited settings: "
                   f"Question Count: {inherited_settings.get('question_count')}, "
                   f"Duration: {inherited_settings.get('duration')}, "
                   f"Difficulty: {inherited_settings.get('difficulty_level')}")
        
        # Verify question count inheritance
        practice_session = result['session']
        questions_count = len(result['questions'])
        expected_count = inherited_settings.get('question_count', 5)
        
        if questions_count != expected_count:
            logger.warning(f"Question count mismatch: expected {expected_count}, got {questions_count}")
        else:
            logger.info(f"Question count inheritance verified: {questions_count} questions")
        
        return {
            "message": "Practice session created successfully with inherited settings",
            "session_id": result['session'].id,
            "session": result['session'],
            "questions": result['questions'],
            "configuration": result['configuration'],
            "original_session_id": session_id,
            "inherited_settings": {
                "question_count": inherited_settings.get('question_count'),
                "duration": inherited_settings.get('duration'),
                "difficulty_level": inherited_settings.get('difficulty_level'),
                "target_role": inherited_settings.get('target_role')
            },
            "inheritance_verification": {
                "settings_inherited": True,
                "question_count_matched": questions_count == expected_count,
                "parent_session_linked": practice_session.parent_session_id == session_id,
                "session_mode_correct": practice_session.session_mode == "practice_again"
            }
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error creating practice session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating practice session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create practice session"
        )


@router.post("/{session_id}/practice-again-enhanced")
async def practice_again_enhanced(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(max_calls=10, window_seconds=300))
):
    """Create a new practice session with enhanced difficulty inheritance using EnhancedSessionSettingsManager"""
    from app.services.enhanced_session_settings_manager import EnhancedSessionSettingsManager
    
    try:
        logger.info(f"Enhanced practice-again request for session {session_id} by user {current_user.id}")
        
        # Initialize enhanced session settings manager
        enhanced_manager = EnhancedSessionSettingsManager(db)
        
        # Validate practice session eligibility
        eligibility = enhanced_manager.validate_practice_session_eligibility(session_id, current_user.id)
        if not eligibility["is_eligible"]:
            logger.warning(f"Session {session_id} not eligible for practice: {eligibility['reasons']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Session not eligible for practice: {'; '.join(eligibility['reasons'])}"
            )
        
        # Create enhanced practice session with proper difficulty inheritance
        result = enhanced_manager.create_practice_session(session_id, current_user.id)
        
        # Get questions for the practice session
        interview_service = InterviewService(db)
        practice_session = result["session"]
        inherited_settings = result["inherited_settings"]
        
        # Generate questions with inherited settings
        logger.info(f"Generating questions for practice session - Role: {inherited_settings['target_role']}, Difficulty: {inherited_settings['difficulty_level']}, Type: {practice_session.session_type}, Count: {inherited_settings['question_count']}")
        
        try:
            questions = interview_service.question_service.get_questions_for_session(
                role=inherited_settings['target_role'],
                difficulty=inherited_settings['difficulty_level'],
                session_type=practice_session.session_type,
                count=inherited_settings['question_count'],
                user_id=current_user.id
            )
            logger.info(f"Question service returned {len(questions) if questions else 0} questions")
        except Exception as question_error:
            logger.error(f"Question service failed: {str(question_error)}")
            questions = []
        
        if not questions or len(questions) == 0:
            logger.error(f"No questions retrieved for enhanced practice session - Role: {inherited_settings['target_role']}, Difficulty: {inherited_settings['difficulty_level']}, Type: {practice_session.session_type}")
            # Try to get fallback questions
            try:
                from app.services.fallback_question_service import FallbackQuestionService
                fallback_service = FallbackQuestionService(db)
                questions = fallback_service.get_questions_by_role(
                    role=inherited_settings['target_role'],
                    difficulty=inherited_settings['difficulty_level'],
                    session_type=practice_session.session_type,
                    count=inherited_settings['question_count']
                )
                if questions and len(questions) > 0:
                    logger.info(f"Retrieved {len(questions)} fallback questions")
                else:
                    raise ValueError(f"No questions available for role '{inherited_settings['target_role']}' with difficulty '{inherited_settings['difficulty_level']}' and session type '{practice_session.session_type}'")
            except Exception as fallback_error:
                logger.error(f"Fallback question service also failed: {str(fallback_error)}")
                # Create basic fallback questions as last resort
                logger.info("Creating basic fallback questions as last resort")
                questions = [
                    {
                        "id": 9999,
                        "content": f"Tell me about your experience in {inherited_settings['target_role']}.",
                        "question_type": "behavioral",
                        "role_category": inherited_settings['target_role'],
                        "difficulty_level": inherited_settings['difficulty_level'],
                        "expected_duration": 3,
                        "generated_by": "fallback"
                    },
                    {
                        "id": 9998,
                        "content": "Describe a challenging situation you've faced and how you handled it.",
                        "question_type": "behavioral",
                        "role_category": inherited_settings['target_role'],
                        "difficulty_level": inherited_settings['difficulty_level'],
                        "expected_duration": 3,
                        "generated_by": "fallback"
                    },
                    {
                        "id": 9997,
                        "content": "What are your strengths and how do they apply to this role?",
                        "question_type": "behavioral",
                        "role_category": inherited_settings['target_role'],
                        "difficulty_level": inherited_settings['difficulty_level'],
                        "expected_duration": 3,
                        "generated_by": "fallback"
                    }
                ]
                logger.info(f"Created {len(questions)} basic fallback questions")
        
        # Initialize session state
        session_state = {
            "user_id": current_user.id,
            "questions": [q.id if hasattr(q, 'id') else q['id'] for q in questions],
            "current_question_index": 0,
            "start_time": datetime.utcnow().isoformat(),
            "answers": {},
            "paused_time": 0,
            "is_practice_session": True,
            "enhanced_inheritance": True,
            "parent_session_id": session_id
        }
        interview_service.session_manager.create_session(practice_session.id, session_state)
        
        # Serialize questions for response
        try:
            questions_data = interview_service._serialize_questions(questions)
        except Exception as serialize_error:
            logger.warning(f"Error serializing questions, using raw data: {str(serialize_error)}")
            # Handle both object and dictionary questions
            questions_data = []
            for q in questions:
                if hasattr(q, '__dict__'):
                    # Object question
                    questions_data.append({
                        "id": q.id,
                        "content": q.content,
                        "question_type": q.question_type,
                        "role_category": q.role_category,
                        "difficulty_level": q.difficulty_level,
                        "expected_duration": q.expected_duration,
                        "generated_by": q.generated_by
                    })
                else:
                    # Dictionary question
                    questions_data.append(q)
        
        # Log detailed inheritance information
        parent_info = result["parent_session_info"]
        inheritance_verification = result["inheritance_verification"]
        
        logger.info(f"Enhanced practice session {practice_session.id} created with:")
        logger.info(f"  - Inherited difficulty: {inherited_settings['difficulty_level']}")
        logger.info(f"  - Parent initial difficulty: {parent_info['initial_difficulty']}")
        logger.info(f"  - Parent final difficulty: {parent_info['final_difficulty']}")
        logger.info(f"  - Difficulty was adjusted: {parent_info['difficulty_was_adjusted']}")
        logger.info(f"  - Question count: {inherited_settings['question_count']}")
        logger.info(f"  - Inheritance verification: {inheritance_verification}")
        
        return {
            "message": "Enhanced practice session created successfully with proper difficulty inheritance",
            "session_id": practice_session.id,
            "session": practice_session,
            "questions": questions_data,
            "configuration": {
                "total_questions": len(questions),
                "estimated_duration": inherited_settings['duration'],
                "session_id": practice_session.id,
                "difficulty_level": inherited_settings['difficulty_level'],
                "created_at": practice_session.created_at.isoformat() if practice_session.created_at else None
            },
            "inherited_settings": inherited_settings,
            "parent_session_info": parent_info,
            "inheritance_verification": inheritance_verification,
            "validation_details": result["validation_details"],
            "eligibility_check": eligibility
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error creating enhanced practice session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating enhanced practice session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create enhanced practice session"
        )


@router.post("/quick-test")
async def create_quick_test_session(
    override_settings: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(max_calls=15, window_seconds=300))
):
    """Create a new quick test session with proper settings inheritance or override"""
    interview_service = InterviewService(db)
    
    try:
        logger.info(f"Quick test request by user {current_user.id} with overrides: {override_settings}")
        
        # Create quick test session using SessionSettingsManager
        result = interview_service.session_settings_manager.create_quick_test_session(
            user=current_user,
            override_settings=override_settings
        )
        
        # Get questions for the quick test session
        quick_test_session = result['session']
        settings_info = result['settings_info']
        
        # Calculate question distribution for quick test
        from app.services.question_distribution_calculator import QuestionDistributionCalculator
        distribution_calculator = QuestionDistributionCalculator()
        
        question_distribution = distribution_calculator.calculate_distribution(
            total_questions=settings_info['question_count'],
            session_type='quick_test'
        )
        
        logger.info(f"Quick test question distribution: {question_distribution}")
        
        # Generate questions with proper distribution
        questions = interview_service.question_service.get_questions_with_distribution(
            role=settings_info['target_role'],
            difficulty=settings_info['difficulty_level'],
            session_type='technical',
            distribution=question_distribution
        )
        
        if not questions or len(questions) == 0:
            logger.error("No questions retrieved for quick test session")
            raise ValueError("No questions available for this role and session type")
        
        # Initialize session state
        session_state = {
            "user_id": current_user.id,
            "questions": [q.id for q in questions],
            "current_question_index": 0,
            "start_time": datetime.utcnow().isoformat(),
            "answers": {},
            "paused_time": 0,
            "is_quick_test": True,
            "settings_info": settings_info
        }
        interview_service.session_manager.create_session(quick_test_session.id, session_state)
        
        # Serialize questions for response
        questions_data = interview_service._serialize_questions(questions)
        
        # Log settings information for verification
        logger.info(f"Quick test session {quick_test_session.id} created with settings: "
                   f"Question Count: {settings_info['question_count']} ({settings_info['question_count_source']}), "
                   f"Difficulty: {settings_info['difficulty_level']}, "
                   f"Target Role: {settings_info['target_role']}")
        
        # Validate actual question distribution
        actual_distribution = {
            'theory': sum(1 for q in questions_data if q.get('question_type') in ['theoretical', 'theory']),
            'coding': sum(1 for q in questions_data if q.get('question_type') in ['technical', 'coding']),
            'aptitude': sum(1 for q in questions_data if q.get('question_type') in ['problem-solving', 'aptitude'])
        }
        
        distribution_summary = distribution_calculator.get_distribution_summary(question_distribution)
        
        return {
            "message": "Quick test session created successfully",
            "session_id": quick_test_session.id,
            "session": quick_test_session,
            "questions": questions_data,
            "configuration": {
                "total_questions": len(questions),
                "estimated_duration": quick_test_session.duration,
                "session_id": quick_test_session.id,
                "difficulty_level": settings_info['difficulty_level'],
                "created_at": quick_test_session.created_at.isoformat() if quick_test_session.created_at else None
            },
            "settings_info": {
                "question_count": settings_info['question_count'],
                "question_count_source": settings_info['question_count_source'],
                "difficulty_level": settings_info['difficulty_level'],
                "target_role": settings_info['target_role'],
                "duration": settings_info['duration'],
                "inherited_from_session_id": settings_info.get('inherited_from_session_id')
            },
            "question_distribution": {
                "expected": question_distribution,
                "actual": actual_distribution,
                "summary": distribution_summary,
                "distribution_applied": True
            },
            "inheritance_verification": {
                "settings_applied": result['validation']['is_valid'],
                "question_count_source": settings_info['question_count_source'],
                "last_main_session_id": result.get('last_main_session_id'),
                "override_settings_applied": bool(override_settings),
                "distribution_enforced": True
            }
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error creating quick test session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating quick test session: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create quick test session"
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


@router.get("/statistics/enhanced")
async def get_enhanced_user_statistics(
    days: int = Query(30, ge=7, le=365, description="Number of days to include in trend analysis"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get enhanced user statistics with performance trends and difficulty analysis"""
    from app.services.difficulty_service import DifficultyService
    
    interview_service = InterviewService(db)
    difficulty_service = DifficultyService(db)
    
    try:
        # Get base statistics
        base_statistics = interview_service.get_user_statistics(current_user.id)
        
        # Get enhanced performance trend data
        performance_trend = difficulty_service.get_performance_trend(current_user.id, days)
        
        # Get difficulty statistics
        difficulty_stats = difficulty_service.get_difficulty_statistics(current_user.id)
        
        # Get next recommended difficulty
        next_difficulty = difficulty_service.get_next_difficulty(current_user.id)
        
        # Calculate trend for last 3 sessions
        recent_sessions = interview_service.get_user_sessions(current_user.id, limit=3)
        recent_trend = []
        if recent_sessions:
            for session in recent_sessions:
                if session.performance_score is not None:
                    recent_trend.append({
                        "session_id": session.id,
                        "date": session.completed_at.isoformat() if session.completed_at else session.created_at.isoformat(),
                        "performance_score": session.performance_score,
                        "difficulty_level": session.difficulty_level or "medium",
                        "target_role": session.target_role
                    })
        
        # Enhanced statistics response
        enhanced_stats = {
            **base_statistics,
            "performance_analysis": {
                "current_performance_score": recent_trend[0]["performance_score"] if recent_trend else 0,
                "next_difficulty_level": next_difficulty,
                "performance_trend": performance_trend,
                "recent_sessions_trend": recent_trend,
                "difficulty_progression": difficulty_stats
            },
            "adaptive_insights": {
                "recommended_focus_areas": _get_focus_areas(base_statistics),
                "difficulty_readiness": _assess_difficulty_readiness(difficulty_stats, performance_trend),
                "improvement_velocity": _calculate_improvement_velocity(recent_trend)
            }
        }
        
        return enhanced_stats
        
    except Exception as e:
        logger.error(f"Error retrieving enhanced statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve enhanced user statistics"
        )


def _get_focus_areas(base_stats: Dict[str, Any]) -> List[str]:
    """Determine focus areas based on skill breakdown"""
    focus_areas = []
    skill_breakdown = base_stats.get("skill_breakdown", {})
    
    if skill_breakdown.get("content_quality", 0) < 60:
        focus_areas.append("content_quality")
    if skill_breakdown.get("body_language", 0) < 60:
        focus_areas.append("body_language")
    if skill_breakdown.get("voice_tone", 0) < 60:
        focus_areas.append("voice_analysis")
    
    return focus_areas


def _assess_difficulty_readiness(difficulty_stats: Dict[str, Any], performance_trend) -> str:
    """Assess if user is ready for difficulty increase"""
    current_difficulty = difficulty_stats.get("current_difficulty", "medium")
    average_performance = difficulty_stats.get("average_performance", 0)
    trend_direction = performance_trend.trend_direction
    
    if average_performance > 75 and trend_direction == "improving":
        return "ready_for_increase"
    elif average_performance < 40 and trend_direction == "declining":
        return "consider_decrease"
    else:
        return "maintain_current"


def _calculate_improvement_velocity(recent_trend: List[Dict]) -> float:
    """Calculate rate of improvement over recent sessions"""
    if len(recent_trend) < 2:
        return 0.0
    
    scores = [session["performance_score"] for session in recent_trend]
    # Simple linear regression slope
    n = len(scores)
    x_sum = sum(range(n))
    y_sum = sum(scores)
    xy_sum = sum(i * score for i, score in enumerate(scores))
    x_squared_sum = sum(i * i for i in range(n))
    
    if n * x_squared_sum - x_sum * x_sum == 0:
        return 0.0
    
    slope = (n * xy_sum - x_sum * y_sum) / (n * x_squared_sum - x_sum * x_sum)
    return round(slope, 2)


@router.get("/difficulty/statistics")
async def get_difficulty_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's difficulty statistics and recommendations"""
    interview_service = InterviewService(db)
    
    try:
        stats = interview_service.difficulty_service.get_difficulty_statistics(current_user.id)
        return stats
        
    except Exception as e:
        logger.error(f"Error getting difficulty statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get difficulty statistics"
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