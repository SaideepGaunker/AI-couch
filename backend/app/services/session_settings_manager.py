"""
Session Settings Manager - Handle session settings inheritance and persistence
"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.models import InterviewSession, User
from app.schemas.interview import InterviewSessionCreate, SessionType
from app.crud.interview import create_interview_session, get_interview_session, get_user_sessions

logger = logging.getLogger(__name__)


class SessionSettingsManager:
    """Manage session settings inheritance and persistence"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_practice_session(self, original_session_id: int, user: User) -> Dict[str, Any]:
        """
        Create practice session inheriting settings from original session
        
        Args:
            original_session_id: ID of the original session to inherit from
            user: User creating the practice session
            
        Returns:
            Dict containing the new session data and inherited settings
            
        Raises:
            ValueError: If original session not found or invalid
        """
        try:
            logger.info(f"Creating practice session from original session {original_session_id} for user {user.id}")
            
            # Get the original session
            original_session = get_interview_session(self.db, original_session_id)
            if not original_session:
                raise ValueError(f"Original session {original_session_id} not found")
            
            # Verify ownership
            if original_session.user_id != user.id:
                raise ValueError(f"User {user.id} does not own session {original_session_id}")
            
            # Extract settings from original session
            inherited_settings = self._extract_session_settings(original_session)
            logger.info(f"Inherited settings: {inherited_settings}")
            
            # For practice sessions, use adaptive difficulty recommendation instead of original difficulty
            from app.services.difficulty_service import DifficultyService
            difficulty_service = DifficultyService(self.db)
            recommended_difficulty = difficulty_service.get_next_difficulty(user.id)
            
            logger.info(f"Practice session: Using adaptive difficulty '{recommended_difficulty}' instead of original '{inherited_settings['difficulty_level']}'")
            
            # Update inherited settings to show the adaptive difficulty
            inherited_settings['original_difficulty'] = inherited_settings['difficulty_level']
            inherited_settings['difficulty_level'] = recommended_difficulty
            
            # Create session data for practice session
            practice_session_data = InterviewSessionCreate(
                session_type=SessionType(inherited_settings['session_type']),
                target_role=inherited_settings['target_role'],
                duration=inherited_settings['duration'],
                difficulty=recommended_difficulty,  # Use adaptive difficulty for practice
                question_count=inherited_settings['question_count'],
                enable_video=True,  # Default values for practice
                enable_audio=True
            )
            
            # Create the practice session with inheritance
            practice_session = create_interview_session(
                db=self.db,
                user_id=user.id,
                session_data=practice_session_data,
                difficulty_level=inherited_settings['difficulty_level'],
                parent_session_id=original_session_id,
                session_mode="practice_again"
            )
            
            logger.info(f"Created practice session {practice_session.id} with inherited question count: {inherited_settings['question_count']}")
            
            # Validate that inherited settings are properly applied
            validation_result = self._validate_inherited_settings(practice_session, inherited_settings)
            if not validation_result['is_valid']:
                logger.error(f"Settings inheritance validation failed: {validation_result['errors']}")
                raise ValueError(f"Settings inheritance validation failed: {validation_result['errors']}")
            
            return {
                'session': practice_session,
                'inherited_settings': inherited_settings,
                'original_session_id': original_session_id,
                'validation': validation_result
            }
            
        except Exception as e:
            logger.error(f"Error creating practice session: {str(e)}")
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
            # Calculate question count from session data
            # For now, we'll use a default or try to infer from session metadata
            question_count = getattr(session, 'question_count', None)
            if not question_count:
                # Try to get from session metadata or use reasonable default based on duration
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
                'overall_score': session.overall_score or 0.0
            }
            
            logger.info(f"Extracted settings from session {session.id}: {settings}")
            return settings
            
        except Exception as e:
            logger.error(f"Error extracting session settings: {str(e)}")
            raise
    
    def _validate_inherited_settings(self, new_session: InterviewSession, expected_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that inherited settings are properly applied
        
        Args:
            new_session: The newly created session
            expected_settings: The settings that should have been inherited
            
        Returns:
            Dict containing validation results
        """
        try:
            errors = []
            
            # Validate session type
            if new_session.session_type != expected_settings['session_type']:
                errors.append(f"Session type mismatch: expected {expected_settings['session_type']}, got {new_session.session_type}")
            
            # Validate target role
            if new_session.target_role != expected_settings['target_role']:
                errors.append(f"Target role mismatch: expected {expected_settings['target_role']}, got {new_session.target_role}")
            
            # Validate duration
            if new_session.duration != expected_settings['duration']:
                errors.append(f"Duration mismatch: expected {expected_settings['duration']}, got {new_session.duration}")
            
            # Validate difficulty level
            if new_session.difficulty_level != expected_settings['difficulty_level']:
                errors.append(f"Difficulty level mismatch: expected {expected_settings['difficulty_level']}, got {new_session.difficulty_level}")
            
            # Validate parent session relationship
            if new_session.parent_session_id is None:
                errors.append("Parent session ID not set for practice session")
            
            # Validate session mode
            if new_session.session_mode != "practice_again":
                errors.append(f"Session mode should be 'practice_again', got {new_session.session_mode}")
            
            validation_result = {
                'is_valid': len(errors) == 0,
                'errors': errors,
                'validated_settings': {
                    'session_type': new_session.session_type,
                    'target_role': new_session.target_role,
                    'duration': new_session.duration,
                    'difficulty_level': new_session.difficulty_level,
                    'parent_session_id': new_session.parent_session_id,
                    'session_mode': new_session.session_mode
                }
            }
            
            if validation_result['is_valid']:
                logger.info(f"Settings inheritance validation passed for session {new_session.id}")
            else:
                logger.warning(f"Settings inheritance validation failed for session {new_session.id}: {errors}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating inherited settings: {str(e)}")
            return {
                'is_valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'validated_settings': {}
            }
    
    def get_session_inheritance_info(self, session_id: int) -> Optional[Dict[str, Any]]:
        """
        Get inheritance information for a session
        
        Args:
            session_id: ID of the session to get inheritance info for
            
        Returns:
            Dict containing inheritance information or None if not found
        """
        try:
            session = get_interview_session(self.db, session_id)
            if not session:
                return None
            
            inheritance_info = {
                'session_id': session.id,
                'session_mode': session.session_mode,
                'parent_session_id': session.parent_session_id,
                'is_practice_session': session.session_mode == "practice_again",
                'has_parent': session.parent_session_id is not None
            }
            
            # If this is a practice session, get parent session info
            if session.parent_session_id:
                parent_session = get_interview_session(self.db, session.parent_session_id)
                if parent_session:
                    inheritance_info['parent_session_info'] = {
                        'id': parent_session.id,
                        'session_type': parent_session.session_type,
                        'target_role': parent_session.target_role,
                        'duration': parent_session.duration,
                        'difficulty_level': parent_session.difficulty_level,
                        'created_at': parent_session.created_at.isoformat() if parent_session.created_at else None
                    }
            
            return inheritance_info
            
        except Exception as e:
            logger.error(f"Error getting session inheritance info: {str(e)}")
            return None
    
    def get_user_last_main_session(self, user_id: int) -> Optional[InterviewSession]:
        """
        Get user's last main (non-practice) session for settings inheritance
        
        Args:
            user_id: ID of the user
            
        Returns:
            Last main session or None if not found
        """
        try:
            # Get user sessions, excluding practice sessions
            sessions = self.db.query(InterviewSession).filter(
                InterviewSession.user_id == user_id,
                InterviewSession.session_mode != "practice_again"
            ).order_by(InterviewSession.created_at.desc()).limit(1).all()
            
            return sessions[0] if sessions else None
            
        except Exception as e:
            logger.error(f"Error getting user's last main session: {str(e)}")
            return None
    
    def create_quick_test_session(self, user: User, override_settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create quick test session with proper settings inheritance or override
        
        Args:
            user: User creating the quick test session
            override_settings: Optional settings to override inherited values
            
        Returns:
            Dict containing the new session data and settings information
            
        Raises:
            ValueError: If session creation fails
        """
        try:
            logger.info(f"Creating quick test session for user {user.id} with overrides: {override_settings}")
            
            # Get user's last main session for inheritance
            last_main_session = self.get_user_last_main_session(user.id)
            
            # Determine settings with inheritance logic
            if override_settings and 'question_count' in override_settings:
                # User explicitly overrode question count
                question_count = override_settings['question_count']
                question_count_source = 'user_override'
                logger.info(f"Using user override question count: {question_count}")
            elif last_main_session:
                # Inherit from last main session
                inherited_settings = self._extract_session_settings(last_main_session)
                question_count = inherited_settings['question_count']
                question_count_source = 'inherited'
                logger.info(f"Inheriting question count from session {last_main_session.id}: {question_count}")
            else:
                # Default for new users
                question_count = 3
                question_count_source = 'default'
                logger.info(f"Using default question count: {question_count}")
            
            # Determine other settings
            if last_main_session:
                difficulty = override_settings.get('difficulty') if override_settings else last_main_session.difficulty_level or 'medium'
                target_role = override_settings.get('target_role') if override_settings else last_main_session.target_role
            else:
                difficulty = override_settings.get('difficulty', 'medium') if override_settings else 'medium'
                target_role = override_settings.get('target_role', 'Software Developer') if override_settings else 'Software Developer'
            
            # Always use quick test defaults for duration and session type
            duration = 15  # Quick tests are always 15 minutes
            session_type = 'technical'  # Quick tests are always technical
            
            # Create session data for quick test
            quick_test_session_data = InterviewSessionCreate(
                session_type=SessionType(session_type),
                target_role=target_role,
                duration=duration,
                difficulty=difficulty,
                question_count=question_count,
                enable_video=True,
                enable_audio=True
            )
            
            # Create the quick test session
            quick_test_session = create_interview_session(
                db=self.db,
                user_id=user.id,
                session_data=quick_test_session_data,
                difficulty_level=difficulty,
                parent_session_id=last_main_session.id if last_main_session else None,
                session_mode="quick_test"
            )
            
            logger.info(f"Created quick test session {quick_test_session.id} with question count: {question_count}")
            
            # Prepare settings information
            settings_info = {
                'question_count': question_count,
                'question_count_source': question_count_source,
                'difficulty_level': difficulty,
                'target_role': target_role,
                'duration': duration,
                'session_type': session_type,
                'inherited_from_session_id': last_main_session.id if last_main_session and question_count_source == 'inherited' else None
            }
            
            # Validate settings
            validation_result = self._validate_quick_test_settings(quick_test_session, settings_info, override_settings)
            
            return {
                'session': quick_test_session,
                'settings_info': settings_info,
                'last_main_session_id': last_main_session.id if last_main_session else None,
                'validation': validation_result,
                'override_settings': override_settings or {}
            }
            
        except Exception as e:
            logger.error(f"Error creating quick test session: {str(e)}")
            raise
    
    def _validate_quick_test_settings(self, session: InterviewSession, settings_info: Dict[str, Any], 
                                    override_settings: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate that quick test settings are properly applied
        
        Args:
            session: The newly created quick test session
            settings_info: The settings information
            override_settings: Any override settings provided
            
        Returns:
            Dict containing validation results
        """
        try:
            errors = []
            warnings = []
            
            # Validate session mode
            if session.session_mode != "quick_test":
                errors.append(f"Session mode should be 'quick_test', got {session.session_mode}")
            
            # Validate question count
            expected_question_count = settings_info['question_count']
            if hasattr(session, 'question_count') and session.question_count != expected_question_count:
                errors.append(f"Question count mismatch: expected {expected_question_count}, got {session.question_count}")
            
            # Validate duration (should always be 15 for quick tests)
            if session.duration != 15:
                errors.append(f"Quick test duration should be 15 minutes, got {session.duration}")
            
            # Validate session type (should always be technical for quick tests)
            if session.session_type != 'technical':
                errors.append(f"Quick test session type should be 'technical', got {session.session_type}")
            
            # Validate difficulty
            if session.difficulty_level != settings_info['difficulty_level']:
                errors.append(f"Difficulty level mismatch: expected {settings_info['difficulty_level']}, got {session.difficulty_level}")
            
            # Validate target role
            if session.target_role != settings_info['target_role']:
                errors.append(f"Target role mismatch: expected {settings_info['target_role']}, got {session.target_role}")
            
            # Validate override handling
            if override_settings:
                for key, value in override_settings.items():
                    if key == 'question_count' and settings_info['question_count_source'] != 'user_override':
                        warnings.append(f"Question count override not properly applied")
            
            validation_result = {
                'is_valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'validated_settings': settings_info
            }
            
            if validation_result['is_valid']:
                logger.info(f"Quick test settings validation passed for session {session.id}")
            else:
                logger.warning(f"Quick test settings validation failed for session {session.id}: {errors}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating quick test settings: {str(e)}")
            return {
                'is_valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': [],
                'validated_settings': {}
            }