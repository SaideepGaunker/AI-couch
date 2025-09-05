"""
Enhanced Session Settings Manager - Handle session settings inheritance with proper difficulty inheritance

This service provides enhanced session settings management with proper difficulty inheritance
from parent sessions, ensuring practice sessions use the final adjusted difficulty level.
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime

from app.db.models import InterviewSession, User
from app.schemas.interview import InterviewSessionCreate, SessionType
from app.crud.interview import create_interview_session, get_interview_session
from app.services.session_specific_difficulty_service import SessionSpecificDifficultyService

logger = logging.getLogger(__name__)


class EnhancedSessionSettingsManager:
    """
    Enhanced session settings manager with proper difficulty inheritance
    
    This service ensures that practice sessions inherit the final difficulty from their
    parent session, not the initial difficulty, providing proper continuity for users.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the enhanced session settings manager
        
        Args:
            db: Database session for persistence operations
        """
        self.db = db
        self.session_difficulty_service = SessionSpecificDifficultyService(db)
        
        logger.info("EnhancedSessionSettingsManager initialized")
    
    def create_practice_session(self, parent_session_id: int, user_id: int) -> Dict[str, Any]:
        """
        Create practice session with proper difficulty inheritance
        
        This method creates a practice session that inherits the final difficulty from
        the parent session, ensuring that adaptive difficulty adjustments are preserved.
        
        Args:
            parent_session_id: ID of the parent session to inherit from
            user_id: ID of the user creating the practice session
            
        Returns:
            Dict containing session data, inheritance info, and validation results
            
        Raises:
            ValueError: If parent session not found or invalid
            Exception: If session creation fails
        """
        try:
            logger.info(f"Creating enhanced practice session from parent {parent_session_id} for user {user_id}")
            
            # Validate parent session exists and belongs to user
            parent_session = self.db.query(InterviewSession).filter(
                and_(
                    InterviewSession.id == parent_session_id,
                    InterviewSession.user_id == user_id
                )
            ).first()
            
            if not parent_session:
                raise ValueError(f"Parent session {parent_session_id} not found for user {user_id}")
            
            # Get the final difficulty from parent session using session-specific service
            practice_difficulty = self.session_difficulty_service.get_difficulty_for_practice_session(parent_session_id)
            
            logger.info(f"Practice session will inherit difficulty: {practice_difficulty}")
            
            # Extract other settings from parent session
            inherited_settings = self._extract_session_settings(parent_session)
            
            # Update inherited settings with the proper difficulty
            inherited_settings['difficulty_level'] = practice_difficulty
            inherited_settings['original_difficulty'] = parent_session.difficulty_level or "medium"
            inherited_settings['initial_difficulty'] = parent_session.initial_difficulty_level or parent_session.difficulty_level or "medium"
            inherited_settings['final_difficulty'] = practice_difficulty
            
            # Create session data for practice session
            practice_session_data = InterviewSessionCreate(
                target_role=inherited_settings['target_role'],
                session_type=SessionType.TECHNICAL,  # Practice sessions are always technical
                difficulty=practice_difficulty,  # Use final difficulty from parent
                duration=inherited_settings['duration'],
                question_count=inherited_settings['question_count'],
                enable_video=True,
                enable_audio=True
            )
            
            # Create the practice session
            practice_session = create_interview_session(
                self.db, 
                user_id, 
                practice_session_data,
                difficulty_level=practice_difficulty
            )
            
            # Set parent relationship and session mode
            practice_session.parent_session_id = parent_session_id
            practice_session.session_mode = "practice_again"
            
            # Initialize session-specific difficulty state for practice session
            self.session_difficulty_service.initialize_session_difficulty(
                practice_session.id, 
                practice_difficulty
            )
            
            # Commit all changes
            self.db.commit()
            
            logger.info(f"Created enhanced practice session {practice_session.id} with inherited difficulty {practice_difficulty}")
            
            # Comprehensive validation of inherited settings
            validation_result = self._validate_inherited_settings(practice_session, inherited_settings, parent_session)
            
            # Prepare detailed response
            response = {
                "session": practice_session,
                "inherited_settings": inherited_settings,
                "parent_session_info": {
                    "id": parent_session_id,
                    "initial_difficulty": inherited_settings['initial_difficulty'],
                    "final_difficulty": practice_difficulty,
                    "difficulty_was_adjusted": practice_difficulty != inherited_settings['initial_difficulty']
                },
                "inheritance_verification": {
                    "settings_inherited": validation_result['is_valid'],
                    "question_count_matched": validation_result.get('question_count_matched', False),
                    "parent_session_linked": practice_session.parent_session_id == parent_session_id,
                    "session_mode_correct": practice_session.session_mode == "practice_again",
                    "difficulty_inherited_from_final": practice_difficulty == parent_session.get_difficulty_for_practice()
                },
                "validation_details": validation_result
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error creating enhanced practice session: {str(e)}")
            self.db.rollback()
            raise
    
    def _extract_session_settings(self, session: InterviewSession) -> Dict[str, Any]:
        """
        Extract settings from a session for inheritance
        
        Args:
            session: The session to extract settings from
            
        Returns:
            Dict containing the extracted settings
        """
        try:
            # Calculate question count from session data or use reasonable defaults
            question_count = getattr(session, 'question_count', None)
            if not question_count:
                # Infer from duration if not explicitly set
                if session.duration <= 15:
                    question_count = 3
                elif session.duration <= 30:
                    question_count = 5
                elif session.duration <= 45:
                    question_count = 8
                else:
                    question_count = 10
            
            settings = {
                'session_type': session.session_type,
                'target_role': session.target_role,
                'duration': session.duration,
                'difficulty_level': session.difficulty_level or 'medium',
                'question_count': question_count,
                'performance_score': session.performance_score or 0.0,
                'overall_score': session.overall_score or 0.0,
                'created_at': session.created_at.isoformat() if session.created_at else None,
                'completed_at': session.completed_at.isoformat() if session.completed_at else None
            }
            
            logger.info(f"Extracted settings from session {session.id}: {settings}")
            return settings
            
        except Exception as e:
            logger.error(f"Error extracting session settings: {str(e)}")
            raise
    
    def _validate_inherited_settings(self, new_session: InterviewSession, 
                                   expected_settings: Dict[str, Any], 
                                   parent_session: InterviewSession) -> Dict[str, Any]:
        """
        Validate that inherited settings are properly applied with comprehensive checks
        
        Args:
            new_session: The newly created practice session
            expected_settings: The settings that should have been inherited
            parent_session: The original parent session
            
        Returns:
            Dict containing detailed validation results
        """
        try:
            errors = []
            warnings = []
            validation_flags = {}
            
            # Validate target role inheritance
            if new_session.target_role != expected_settings['target_role']:
                errors.append(f"Target role mismatch: expected {expected_settings['target_role']}, got {new_session.target_role}")
                validation_flags['target_role_matched'] = False
            else:
                validation_flags['target_role_matched'] = True
            
            # Validate duration inheritance
            if new_session.duration != expected_settings['duration']:
                errors.append(f"Duration mismatch: expected {expected_settings['duration']}, got {new_session.duration}")
                validation_flags['duration_matched'] = False
            else:
                validation_flags['duration_matched'] = True
            
            # Validate difficulty inheritance (should use final difficulty from parent)
            parent_final_difficulty = parent_session.get_difficulty_for_practice()
            if new_session.difficulty_level != parent_final_difficulty:
                errors.append(f"Difficulty should inherit final difficulty {parent_final_difficulty}, got {new_session.difficulty_level}")
                validation_flags['difficulty_inherited_correctly'] = False
            else:
                validation_flags['difficulty_inherited_correctly'] = True
            
            # Validate that practice session doesn't use initial difficulty
            parent_initial_difficulty = parent_session.initial_difficulty_level or parent_session.difficulty_level
            if new_session.difficulty_level == parent_initial_difficulty and parent_final_difficulty != parent_initial_difficulty:
                warnings.append(f"Practice session may be using initial difficulty {parent_initial_difficulty} instead of final {parent_final_difficulty}")
                validation_flags['avoided_initial_difficulty'] = False
            else:
                validation_flags['avoided_initial_difficulty'] = True
            
            # Validate parent session relationship
            if new_session.parent_session_id != parent_session.id:
                errors.append(f"Parent session ID mismatch: expected {parent_session.id}, got {new_session.parent_session_id}")
                validation_flags['parent_relationship_set'] = False
            else:
                validation_flags['parent_relationship_set'] = True
            
            # Validate session mode
            if new_session.session_mode != "practice_again":
                errors.append(f"Session mode should be 'practice_again', got {new_session.session_mode}")
                validation_flags['session_mode_correct'] = False
            else:
                validation_flags['session_mode_correct'] = True
            
            # Validate session type (practice sessions should be technical)
            if new_session.session_type != SessionType.TECHNICAL.value:
                warnings.append(f"Practice sessions should typically be technical, got {new_session.session_type}")
                validation_flags['session_type_appropriate'] = False
            else:
                validation_flags['session_type_appropriate'] = True
            
            # Validate question count inheritance
            expected_question_count = expected_settings.get('question_count')
            actual_question_count = getattr(new_session, 'question_count', None)
            if expected_question_count and actual_question_count != expected_question_count:
                warnings.append(f"Question count may not match: expected {expected_question_count}, got {actual_question_count}")
                validation_flags['question_count_matched'] = False
            else:
                validation_flags['question_count_matched'] = True
            
            # Check for difficulty adjustment history
            parent_difficulty_state = self.session_difficulty_service.get_session_difficulty_state(parent_session.id)
            if parent_difficulty_state and parent_difficulty_state.get_changes_count() > 0:
                validation_flags['parent_had_difficulty_adjustments'] = True
                if validation_flags['difficulty_inherited_correctly']:
                    validation_flags['adjustments_properly_inherited'] = True
                else:
                    validation_flags['adjustments_properly_inherited'] = False
                    errors.append("Practice session did not properly inherit difficulty adjustments from parent")
            else:
                validation_flags['parent_had_difficulty_adjustments'] = False
                validation_flags['adjustments_properly_inherited'] = True  # No adjustments to inherit
            
            validation_result = {
                'is_valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'validation_flags': validation_flags,
                'validated_settings': {
                    'session_type': new_session.session_type,
                    'target_role': new_session.target_role,
                    'duration': new_session.duration,
                    'difficulty_level': new_session.difficulty_level,
                    'parent_session_id': new_session.parent_session_id,
                    'session_mode': new_session.session_mode
                },
                'difficulty_inheritance_details': {
                    'parent_initial_difficulty': parent_initial_difficulty,
                    'parent_final_difficulty': parent_final_difficulty,
                    'inherited_difficulty': new_session.difficulty_level,
                    'difficulty_was_adjusted_in_parent': parent_final_difficulty != parent_initial_difficulty,
                    'inheritance_source': 'final_difficulty' if validation_flags['difficulty_inherited_correctly'] else 'unknown'
                }
            }
            
            if validation_result['is_valid']:
                logger.info(f"Enhanced settings inheritance validation passed for session {new_session.id}")
            else:
                logger.warning(f"Enhanced settings inheritance validation failed for session {new_session.id}: {errors}")
            
            if warnings:
                logger.warning(f"Enhanced settings inheritance warnings for session {new_session.id}: {warnings}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating enhanced inherited settings: {str(e)}")
            return {
                'is_valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': [],
                'validation_flags': {},
                'validated_settings': {},
                'difficulty_inheritance_details': {}
            }
    
    def get_practice_session_preview(self, parent_session_id: int, user_id: int) -> Dict[str, Any]:
        """
        Get a preview of what settings would be inherited for a practice session
        
        This method allows users to see what settings would be inherited before
        actually creating the practice session.
        
        Args:
            parent_session_id: ID of the parent session
            user_id: ID of the user
            
        Returns:
            Dict containing preview information
        """
        try:
            logger.info(f"Getting practice session preview for parent {parent_session_id}")
            
            # Validate parent session exists and belongs to user
            parent_session = self.db.query(InterviewSession).filter(
                and_(
                    InterviewSession.id == parent_session_id,
                    InterviewSession.user_id == user_id
                )
            ).first()
            
            if not parent_session:
                raise ValueError(f"Parent session {parent_session_id} not found for user {user_id}")
            
            # Get the difficulty that would be inherited
            practice_difficulty = self.session_difficulty_service.get_difficulty_for_practice_session(parent_session_id)
            
            # Extract settings that would be inherited
            inherited_settings = self._extract_session_settings(parent_session)
            inherited_settings['difficulty_level'] = practice_difficulty
            
            # Get difficulty change history if available
            parent_difficulty_state = self.session_difficulty_service.get_session_difficulty_state(parent_session_id)
            difficulty_history = []
            if parent_difficulty_state:
                difficulty_history = [change.to_dict() for change in parent_difficulty_state.difficulty_changes]
            
            preview = {
                "parent_session_info": {
                    "id": parent_session_id,
                    "target_role": parent_session.target_role,
                    "session_type": parent_session.session_type,
                    "duration": parent_session.duration,
                    "initial_difficulty": parent_session.initial_difficulty_level or parent_session.difficulty_level,
                    "final_difficulty": practice_difficulty,
                    "difficulty_was_adjusted": practice_difficulty != (parent_session.initial_difficulty_level or parent_session.difficulty_level),
                    "created_at": parent_session.created_at.isoformat() if parent_session.created_at else None,
                    "completed_at": parent_session.completed_at.isoformat() if parent_session.completed_at else None
                },
                "inherited_settings": inherited_settings,
                "difficulty_inheritance": {
                    "will_inherit_from": "final_difficulty",
                    "inherited_difficulty": practice_difficulty,
                    "difficulty_change_history": difficulty_history,
                    "changes_count": len(difficulty_history)
                },
                "practice_session_config": {
                    "session_type": "technical",
                    "session_mode": "practice_again",
                    "will_link_to_parent": True,
                    "estimated_question_count": inherited_settings['question_count']
                }
            }
            
            return preview
            
        except Exception as e:
            logger.error(f"Error getting practice session preview: {str(e)}")
            raise
    
    def validate_practice_session_eligibility(self, parent_session_id: int, user_id: int) -> Dict[str, Any]:
        """
        Validate that a session is eligible for practice session creation
        
        Args:
            parent_session_id: ID of the potential parent session
            user_id: ID of the user
            
        Returns:
            Dict containing eligibility information
        """
        try:
            eligibility = {
                "is_eligible": False,
                "reasons": [],
                "warnings": [],
                "session_info": {}
            }
            
            # Check if parent session exists
            parent_session = self.db.query(InterviewSession).filter(
                and_(
                    InterviewSession.id == parent_session_id,
                    InterviewSession.user_id == user_id
                )
            ).first()
            
            if not parent_session:
                eligibility["reasons"].append("Parent session not found or does not belong to user")
                return eligibility
            
            eligibility["session_info"] = {
                "id": parent_session.id,
                "status": parent_session.status,
                "session_mode": parent_session.session_mode,
                "target_role": parent_session.target_role,
                "created_at": parent_session.created_at.isoformat() if parent_session.created_at else None
            }
            
            # Check session status
            if parent_session.status not in ["completed", "active"]:
                eligibility["reasons"].append(f"Parent session status is {parent_session.status}, should be completed or active")
            
            # Check if it's already a practice session
            if parent_session.session_mode == "practice_again":
                eligibility["warnings"].append("Creating practice session from another practice session")
            
            # Check if session has target role
            if not parent_session.target_role:
                eligibility["reasons"].append("Parent session has no target role specified")
            
            # Check difficulty state availability
            try:
                practice_difficulty = self.session_difficulty_service.get_difficulty_for_practice_session(parent_session_id)
                eligibility["session_info"]["available_difficulty"] = practice_difficulty
            except Exception as e:
                eligibility["warnings"].append(f"Could not determine practice difficulty: {str(e)}")
            
            # Determine eligibility
            eligibility["is_eligible"] = len(eligibility["reasons"]) == 0
            
            return eligibility
            
        except Exception as e:
            logger.error(f"Error validating practice session eligibility: {str(e)}")
            return {
                "is_eligible": False,
                "reasons": [f"Validation error: {str(e)}"],
                "warnings": [],
                "session_info": {}
            }