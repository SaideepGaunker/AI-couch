"""
Difficulty State Recovery Service

This service handles corrupted or missing difficulty state, providing recovery mechanisms
and validation for difficulty state consistency across the system.
"""
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.db.models import InterviewSession, User
from app.services.session_difficulty_state import SessionDifficultyState, DifficultyChange
from app.services.session_specific_difficulty_service import SessionSpecificDifficultyService
from app.services.difficulty_mapping_service import DifficultyMappingService

logger = logging.getLogger(__name__)


class DifficultyStateRecoveryService:
    """
    Service to handle corrupted or missing difficulty state
    
    This service provides comprehensive recovery mechanisms for difficulty state issues,
    including individual session recovery, user-wide validation, and fallback mechanisms.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the difficulty state recovery service
        
        Args:
            db: Database session for persistence operations
        """
        self.db = db
        self.session_difficulty_service = SessionSpecificDifficultyService(db)
        self.difficulty_mapping = DifficultyMappingService
        
        logger.info("DifficultyStateRecoveryService initialized")
    
    def recover_session_difficulty_state(self, session_id: int) -> Dict[str, Any]:
        """
        Recover difficulty state for a session with corrupted or missing data
        
        This method attempts multiple recovery strategies to restore a valid difficulty state
        for a session, falling back to safe defaults if necessary.
        
        Args:
            session_id: The ID of the session to recover
            
        Returns:
            Dict containing recovery results and the recovered state
        """
        try:
            logger.info(f"Starting difficulty state recovery for session {session_id}")
            
            recovery_result = {
                "session_id": session_id,
                "recovery_attempted": True,
                "recovery_successful": False,
                "recovery_method": None,
                "recovered_state": None,
                "issues_found": [],
                "actions_taken": [],
                "fallback_used": False,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Get the session from database
            session = self.db.query(InterviewSession).filter(
                InterviewSession.id == session_id
            ).first()
            
            if not session:
                recovery_result["issues_found"].append("Session not found in database")
                logger.error(f"Session {session_id} not found for recovery")
                return recovery_result
            
            # Try recovery strategies in order of preference
            recovered_state = None
            
            # Strategy 1: Try to recover from existing JSON state
            if session.difficulty_state_json:
                try:
                    recovered_state = self._recover_from_json_state(session)
                    if recovered_state:
                        recovery_result["recovery_method"] = "json_state_recovery"
                        recovery_result["actions_taken"].append("Recovered from existing JSON state")
                        logger.info(f"Session {session_id}: Recovered from JSON state")
                except Exception as e:
                    recovery_result["issues_found"].append(f"JSON state recovery failed: {str(e)}")
                    logger.warning(f"Session {session_id}: JSON recovery failed - {str(e)}")
            
            # Strategy 2: Try to recover from individual database fields
            if not recovered_state:
                try:
                    recovered_state = self._recover_from_database_fields(session)
                    if recovered_state:
                        recovery_result["recovery_method"] = "database_fields_recovery"
                        recovery_result["actions_taken"].append("Recovered from database fields")
                        logger.info(f"Session {session_id}: Recovered from database fields")
                except Exception as e:
                    recovery_result["issues_found"].append(f"Database fields recovery failed: {str(e)}")
                    logger.warning(f"Session {session_id}: Database fields recovery failed - {str(e)}")
            
            # Strategy 3: Try to infer from session history and user preferences
            if not recovered_state:
                try:
                    recovered_state = self._recover_from_session_context(session)
                    if recovered_state:
                        recovery_result["recovery_method"] = "context_inference"
                        recovery_result["actions_taken"].append("Inferred from session context")
                        logger.info(f"Session {session_id}: Recovered from context inference")
                except Exception as e:
                    recovery_result["issues_found"].append(f"Context inference failed: {str(e)}")
                    logger.warning(f"Session {session_id}: Context inference failed - {str(e)}")
            
            # Strategy 4: Create fallback state with safe defaults
            if not recovered_state:
                try:
                    recovered_state = self._create_fallback_state(session)
                    recovery_result["recovery_method"] = "fallback_creation"
                    recovery_result["actions_taken"].append("Created fallback state with safe defaults")
                    recovery_result["fallback_used"] = True
                    logger.info(f"Session {session_id}: Created fallback state")
                except Exception as e:
                    recovery_result["issues_found"].append(f"Fallback creation failed: {str(e)}")
                    logger.error(f"Session {session_id}: Fallback creation failed - {str(e)}")
            
            if recovered_state:
                # Validate the recovered state
                validation_errors = recovered_state.validate_state()
                if validation_errors:
                    recovery_result["issues_found"].extend([f"Validation: {error}" for error in validation_errors])
                    logger.warning(f"Session {session_id}: Recovered state has validation issues: {validation_errors}")
                
                # Store the recovered state
                try:
                    # Update cache
                    self.session_difficulty_service.session_states[session_id] = recovered_state
                    
                    # Persist to database
                    success = self.session_difficulty_service._persist_session_difficulty_state(recovered_state)
                    if success:
                        recovery_result["recovery_successful"] = True
                        recovery_result["recovered_state"] = recovered_state.get_summary()
                        recovery_result["actions_taken"].append("Persisted recovered state to database")
                        logger.info(f"Session {session_id}: Successfully recovered and persisted difficulty state")
                    else:
                        recovery_result["issues_found"].append("Failed to persist recovered state")
                        logger.error(f"Session {session_id}: Failed to persist recovered state")
                        
                except Exception as e:
                    recovery_result["issues_found"].append(f"Persistence error: {str(e)}")
                    logger.error(f"Session {session_id}: Error persisting recovered state - {str(e)}")
            else:
                recovery_result["issues_found"].append("All recovery strategies failed")
                logger.error(f"Session {session_id}: All recovery strategies failed")
            
            return recovery_result
            
        except Exception as e:
            logger.error(f"Error during difficulty state recovery for session {session_id}: {str(e)}")
            return {
                "session_id": session_id,
                "recovery_attempted": True,
                "recovery_successful": False,
                "recovery_method": None,
                "recovered_state": None,
                "issues_found": [f"Recovery process error: {str(e)}"],
                "actions_taken": [],
                "fallback_used": False,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def validate_and_fix_difficulty_consistency(self, user_id: int) -> Dict[str, Any]:
        """
        Validate and fix difficulty consistency for all sessions of a user
        
        This method performs user-wide validation of difficulty state consistency,
        identifying and fixing issues across all sessions.
        
        Args:
            user_id: The ID of the user to validate
            
        Returns:
            Dict containing validation results and fixes applied
        """
        try:
            logger.info(f"Starting user-wide difficulty consistency validation for user {user_id}")
            
            validation_result = {
                "user_id": user_id,
                "validation_attempted": True,
                "validation_successful": False,
                "sessions_checked": 0,
                "sessions_with_issues": 0,
                "sessions_fixed": 0,
                "issues_found": [],
                "fixes_applied": [],
                "session_details": {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Get all sessions for the user
            user_sessions = self.db.query(InterviewSession).filter(
                InterviewSession.user_id == user_id
            ).order_by(InterviewSession.created_at.desc()).all()
            
            validation_result["sessions_checked"] = len(user_sessions)
            
            if not user_sessions:
                validation_result["validation_successful"] = True
                validation_result["issues_found"].append("No sessions found for user")
                logger.info(f"User {user_id}: No sessions found")
                return validation_result
            
            # Validate each session
            for session in user_sessions:
                session_validation = self._validate_session_difficulty_consistency(session)
                validation_result["session_details"][session.id] = session_validation
                
                if session_validation["has_issues"]:
                    validation_result["sessions_with_issues"] += 1
                    validation_result["issues_found"].extend([
                        f"Session {session.id}: {issue}" for issue in session_validation["issues"]
                    ])
                    
                    # Attempt to fix issues
                    if session_validation["can_be_fixed"]:
                        fix_result = self._fix_session_difficulty_issues(session, session_validation["issues"])
                        if fix_result["fixed"]:
                            validation_result["sessions_fixed"] += 1
                            validation_result["fixes_applied"].extend([
                                f"Session {session.id}: {fix}" for fix in fix_result["fixes_applied"]
                            ])
            
            # Check for cross-session consistency issues
            cross_session_issues = self._validate_cross_session_consistency(user_sessions)
            if cross_session_issues:
                validation_result["issues_found"].extend([
                    f"Cross-session: {issue}" for issue in cross_session_issues
                ])
            
            # Check practice session inheritance
            inheritance_issues = self._validate_practice_session_inheritance(user_sessions)
            if inheritance_issues:
                validation_result["issues_found"].extend([
                    f"Inheritance: {issue}" for issue in inheritance_issues
                ])
            
            # Determine overall success
            validation_result["validation_successful"] = (
                validation_result["sessions_with_issues"] == validation_result["sessions_fixed"]
            )
            
            logger.info(f"User {user_id}: Validation complete - {validation_result['sessions_checked']} sessions checked, "
                       f"{validation_result['sessions_with_issues']} with issues, {validation_result['sessions_fixed']} fixed")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error during user-wide difficulty validation for user {user_id}: {str(e)}")
            return {
                "user_id": user_id,
                "validation_attempted": True,
                "validation_successful": False,
                "sessions_checked": 0,
                "sessions_with_issues": 0,
                "sessions_fixed": 0,
                "issues_found": [f"Validation process error: {str(e)}"],
                "fixes_applied": [],
                "session_details": {},
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _recover_from_json_state(self, session: InterviewSession) -> Optional[SessionDifficultyState]:
        """
        Attempt to recover difficulty state from JSON data
        
        Args:
            session: The InterviewSession to recover
            
        Returns:
            Optional[SessionDifficultyState]: Recovered state if successful
        """
        try:
            if not session.difficulty_state_json:
                return None
            
            # Try to create state from JSON
            recovered_state = SessionDifficultyState.from_dict(session.difficulty_state_json)
            
            # Validate the recovered state
            validation_errors = recovered_state.validate_state()
            if validation_errors:
                logger.warning(f"Session {session.id}: JSON state has validation errors: {validation_errors}")
                # Try to fix common issues
                self._fix_state_validation_issues(recovered_state, validation_errors)
            
            return recovered_state
            
        except Exception as e:
            logger.error(f"Session {session.id}: Error recovering from JSON state - {str(e)}")
            return None
    
    def _recover_from_database_fields(self, session: InterviewSession) -> Optional[SessionDifficultyState]:
        """
        Attempt to recover difficulty state from individual database fields
        
        Args:
            session: The InterviewSession to recover
            
        Returns:
            Optional[SessionDifficultyState]: Recovered state if successful
        """
        try:
            # Determine initial difficulty
            initial_difficulty = (
                session.initial_difficulty_level or 
                session.difficulty_level or 
                "medium"
            )
            
            # Create basic state
            recovered_state = SessionDifficultyState(session.id, initial_difficulty)
            
            # Restore current difficulty
            if session.current_difficulty_level:
                recovered_state.current_difficulty = session.current_difficulty_level
            elif session.difficulty_level:
                recovered_state.current_difficulty = session.difficulty_level
            
            # Restore final difficulty
            if session.final_difficulty_level:
                recovered_state.final_difficulty = session.final_difficulty_level
                recovered_state.is_finalized = True
            
            # Try to reconstruct changes if we have count information
            if session.difficulty_changes_count and session.difficulty_changes_count > 0:
                # Create synthetic changes based on available information
                if recovered_state.current_difficulty != recovered_state.initial_difficulty:
                    change = DifficultyChange(
                        from_difficulty=recovered_state.initial_difficulty,
                        to_difficulty=recovered_state.current_difficulty,
                        reason="recovered_from_database",
                        timestamp=session.created_at or datetime.utcnow(),
                        change_number=1
                    )
                    recovered_state.difficulty_changes.append(change)
            
            logger.info(f"Session {session.id}: Recovered state from database fields")
            return recovered_state
            
        except Exception as e:
            logger.error(f"Session {session.id}: Error recovering from database fields - {str(e)}")
            return None
    
    def _recover_from_session_context(self, session: InterviewSession) -> Optional[SessionDifficultyState]:
        """
        Attempt to recover difficulty state from session context and user history
        
        Args:
            session: The InterviewSession to recover
            
        Returns:
            Optional[SessionDifficultyState]: Recovered state if successful
        """
        try:
            # Get user's typical difficulty preference
            user_sessions = self.db.query(InterviewSession).filter(
                and_(
                    InterviewSession.user_id == session.user_id,
                    InterviewSession.id != session.id,
                    InterviewSession.difficulty_level.isnot(None)
                )
            ).order_by(InterviewSession.created_at.desc()).limit(5).all()
            
            # Determine most common difficulty
            difficulty_counts = {}
            for user_session in user_sessions:
                diff = user_session.difficulty_level
                difficulty_counts[diff] = difficulty_counts.get(diff, 0) + 1
            
            if difficulty_counts:
                most_common_difficulty = max(difficulty_counts.keys(), key=lambda k: difficulty_counts[k])
            else:
                most_common_difficulty = "medium"
            
            # Use session's difficulty if available, otherwise use user's common difficulty
            initial_difficulty = session.difficulty_level or most_common_difficulty
            
            # Create state with inferred values
            recovered_state = SessionDifficultyState(session.id, initial_difficulty)
            
            # If session is completed, mark as finalized
            if session.status == "completed" and session.completed_at:
                recovered_state.finalize_difficulty()
            
            logger.info(f"Session {session.id}: Recovered state from context inference")
            return recovered_state
            
        except Exception as e:
            logger.error(f"Session {session.id}: Error recovering from context - {str(e)}")
            return None
    
    def _create_fallback_state(self, session: InterviewSession) -> SessionDifficultyState:
        """
        Create a fallback difficulty state with safe defaults
        
        Args:
            session: The InterviewSession to create fallback for
            
        Returns:
            SessionDifficultyState: Fallback state with safe defaults
        """
        try:
            # Use safe default difficulty
            fallback_difficulty = "medium"
            
            # Create basic state
            fallback_state = SessionDifficultyState(session.id, fallback_difficulty)
            
            # If session is completed, mark as finalized
            if session.status == "completed" and session.completed_at:
                fallback_state.finalize_difficulty()
            
            logger.info(f"Session {session.id}: Created fallback state with difficulty {fallback_difficulty}")
            return fallback_state
            
        except Exception as e:
            logger.error(f"Session {session.id}: Error creating fallback state - {str(e)}")
            # Return absolute minimum state
            return SessionDifficultyState(session.id or 0, "medium")
    
    def _validate_session_difficulty_consistency(self, session: InterviewSession) -> Dict[str, Any]:
        """
        Validate difficulty consistency for a single session
        
        Args:
            session: The InterviewSession to validate
            
        Returns:
            Dict containing validation results for the session
        """
        validation = {
            "session_id": session.id,
            "has_issues": False,
            "can_be_fixed": True,
            "issues": [],
            "severity": "none"  # none, low, medium, high, critical
        }
        
        try:
            # Check for missing difficulty information
            if not session.difficulty_level:
                validation["issues"].append("Missing difficulty_level")
                validation["severity"] = "high"
            
            # Check for inconsistent difficulty fields
            if (session.initial_difficulty_level and 
                session.current_difficulty_level and 
                session.difficulty_level):
                if session.current_difficulty_level != session.difficulty_level:
                    validation["issues"].append("current_difficulty_level != difficulty_level")
                    validation["severity"] = "medium"
            
            # Check for finalized sessions without final difficulty
            if (session.status == "completed" and 
                session.completed_at and 
                not session.final_difficulty_level):
                validation["issues"].append("Completed session missing final_difficulty_level")
                validation["severity"] = "medium"
            
            # Check for practice sessions without parent reference
            if (session.session_mode == "practice_again" and 
                not session.parent_session_id):
                validation["issues"].append("Practice session missing parent_session_id")
                validation["severity"] = "high"
            
            # Check JSON state consistency
            if session.difficulty_state_json:
                try:
                    json_state = session.difficulty_state_json
                    if isinstance(json_state, dict):
                        if json_state.get("session_id") != session.id:
                            validation["issues"].append("JSON state session_id mismatch")
                            validation["severity"] = "medium"
                except Exception:
                    validation["issues"].append("Corrupted JSON state")
                    validation["severity"] = "high"
            
            # Check difficulty changes count consistency
            if (session.difficulty_changes_count and 
                session.difficulty_changes_count > 0 and 
                not session.difficulty_state_json):
                validation["issues"].append("Has difficulty_changes_count but no JSON state")
                validation["severity"] = "medium"
            
            validation["has_issues"] = len(validation["issues"]) > 0
            
        except Exception as e:
            validation["issues"].append(f"Validation error: {str(e)}")
            validation["has_issues"] = True
            validation["severity"] = "critical"
            validation["can_be_fixed"] = False
        
        return validation
    
    def _fix_session_difficulty_issues(self, session: InterviewSession, issues: List[str]) -> Dict[str, Any]:
        """
        Attempt to fix identified difficulty issues for a session
        
        Args:
            session: The InterviewSession to fix
            issues: List of issues to fix
            
        Returns:
            Dict containing fix results
        """
        fix_result = {
            "session_id": session.id,
            "fixed": False,
            "fixes_applied": [],
            "fixes_failed": []
        }
        
        try:
            for issue in issues:
                if "Missing difficulty_level" in issue:
                    # Set default difficulty
                    session.difficulty_level = "medium"
                    fix_result["fixes_applied"].append("Set default difficulty_level")
                
                elif "current_difficulty_level != difficulty_level" in issue:
                    # Sync current with main difficulty field
                    session.current_difficulty_level = session.difficulty_level
                    fix_result["fixes_applied"].append("Synced current_difficulty_level with difficulty_level")
                
                elif "Completed session missing final_difficulty_level" in issue:
                    # Set final difficulty from current
                    session.final_difficulty_level = session.difficulty_level or session.current_difficulty_level or "medium"
                    fix_result["fixes_applied"].append("Set final_difficulty_level for completed session")
                
                elif "JSON state session_id mismatch" in issue:
                    # Fix JSON state session_id
                    if session.difficulty_state_json and isinstance(session.difficulty_state_json, dict):
                        session.difficulty_state_json["session_id"] = session.id
                        fix_result["fixes_applied"].append("Fixed JSON state session_id")
                
                elif "Corrupted JSON state" in issue:
                    # Clear corrupted JSON state
                    session.difficulty_state_json = None
                    fix_result["fixes_applied"].append("Cleared corrupted JSON state")
                
                elif "Has difficulty_changes_count but no JSON state" in issue:
                    # Create basic JSON state
                    basic_state = {
                        "session_id": session.id,
                        "initial_difficulty": session.initial_difficulty_level or session.difficulty_level or "medium",
                        "current_difficulty": session.current_difficulty_level or session.difficulty_level or "medium",
                        "final_difficulty": session.final_difficulty_level,
                        "changes_count": session.difficulty_changes_count or 0,
                        "difficulty_changes": [],
                        "last_updated": datetime.utcnow().isoformat()
                    }
                    session.difficulty_state_json = basic_state
                    fix_result["fixes_applied"].append("Created basic JSON state")
            
            # Commit fixes if any were applied
            if fix_result["fixes_applied"]:
                self.db.commit()
                fix_result["fixed"] = True
                logger.info(f"Session {session.id}: Applied fixes - {fix_result['fixes_applied']}")
            
        except Exception as e:
            fix_result["fixes_failed"].append(f"Fix error: {str(e)}")
            logger.error(f"Session {session.id}: Error applying fixes - {str(e)}")
            self.db.rollback()
        
        return fix_result
    
    def _validate_cross_session_consistency(self, sessions: List[InterviewSession]) -> List[str]:
        """
        Validate consistency across multiple sessions
        
        Args:
            sessions: List of InterviewSession objects to validate
            
        Returns:
            List of cross-session consistency issues
        """
        issues = []
        
        try:
            # Check for practice sessions with invalid parent references
            for session in sessions:
                if session.parent_session_id:
                    parent_exists = any(s.id == session.parent_session_id for s in sessions)
                    if not parent_exists:
                        issues.append(f"Session {session.id} references non-existent parent {session.parent_session_id}")
            
            # Check for circular parent references
            parent_child_map = {}
            for session in sessions:
                if session.parent_session_id:
                    parent_child_map[session.id] = session.parent_session_id
            
            for session_id, parent_id in parent_child_map.items():
                visited = set()
                current = parent_id
                while current and current not in visited:
                    visited.add(current)
                    current = parent_child_map.get(current)
                    if current == session_id:
                        issues.append(f"Circular parent reference detected involving session {session_id}")
                        break
            
        except Exception as e:
            issues.append(f"Cross-session validation error: {str(e)}")
        
        return issues
    
    def _validate_practice_session_inheritance(self, sessions: List[InterviewSession]) -> List[str]:
        """
        Validate that practice sessions properly inherit difficulty from parents
        
        Args:
            sessions: List of InterviewSession objects to validate
            
        Returns:
            List of inheritance issues
        """
        issues = []
        
        try:
            session_map = {s.id: s for s in sessions}
            
            for session in sessions:
                if session.session_mode == "practice_again" and session.parent_session_id:
                    parent = session_map.get(session.parent_session_id)
                    if parent:
                        # Check if practice session inherited appropriate difficulty
                        parent_final = parent.final_difficulty_level or parent.difficulty_level
                        practice_initial = session.initial_difficulty_level or session.difficulty_level
                        
                        if parent_final and practice_initial and parent_final != practice_initial:
                            issues.append(
                                f"Practice session {session.id} difficulty ({practice_initial}) "
                                f"doesn't match parent {parent.id} final difficulty ({parent_final})"
                            )
            
        except Exception as e:
            issues.append(f"Inheritance validation error: {str(e)}")
        
        return issues
    
    def _fix_state_validation_issues(self, state: SessionDifficultyState, validation_errors: List[str]) -> None:
        """
        Attempt to fix common validation issues in a difficulty state
        
        Args:
            state: The SessionDifficultyState to fix
            validation_errors: List of validation errors to address
        """
        try:
            for error in validation_errors:
                if "Invalid session_id" in error:
                    # Can't fix invalid session_id
                    continue
                
                elif "Missing initial_difficulty" in error:
                    state.initial_difficulty = "medium"
                
                elif "Missing current_difficulty" in error:
                    state.current_difficulty = state.initial_difficulty or "medium"
                
                elif "Current difficulty mismatch" in error:
                    # Rebuild difficulty progression
                    if state.difficulty_changes:
                        expected_difficulty = state.initial_difficulty
                        for change in state.difficulty_changes:
                            expected_difficulty = change.to_difficulty
                        state.current_difficulty = expected_difficulty
                
                elif "Session is finalized but final_difficulty is not set" in error:
                    state.final_difficulty = state.current_difficulty
                
                elif "final_difficulty is set but session is not finalized" in error:
                    if state.final_difficulty:
                        state.is_finalized = True
            
        except Exception as e:
            logger.error(f"Error fixing state validation issues: {str(e)}")
    
    def get_recovery_statistics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get statistics about difficulty state recovery operations
        
        Args:
            user_id: Optional user ID to filter statistics
            
        Returns:
            Dict containing recovery statistics
        """
        try:
            stats = {
                "total_sessions": 0,
                "sessions_with_issues": 0,
                "sessions_recovered": 0,
                "recovery_methods": {
                    "json_state_recovery": 0,
                    "database_fields_recovery": 0,
                    "context_inference": 0,
                    "fallback_creation": 0
                },
                "common_issues": {},
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Query sessions based on user filter
            query = self.db.query(InterviewSession)
            if user_id:
                query = query.filter(InterviewSession.user_id == user_id)
            
            sessions = query.all()
            stats["total_sessions"] = len(sessions)
            
            # Analyze each session for potential issues
            for session in sessions:
                validation = self._validate_session_difficulty_consistency(session)
                if validation["has_issues"]:
                    stats["sessions_with_issues"] += 1
                    
                    # Count common issues
                    for issue in validation["issues"]:
                        issue_type = issue.split(":")[0] if ":" in issue else issue
                        stats["common_issues"][issue_type] = stats["common_issues"].get(issue_type, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting recovery statistics: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }