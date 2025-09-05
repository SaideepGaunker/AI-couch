"""
Session-Specific Difficulty Management Service
Provides session-isolated difficulty state management with proper inheritance
"""
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
import json

from app.db.models import InterviewSession, User, PerformanceMetrics
from app.services.difficulty_mapping_service import DifficultyMappingService

logger = logging.getLogger(__name__)


class DifficultyChange:
    """Represents a single difficulty adjustment within a session"""
    
    def __init__(self, from_difficulty: str, to_difficulty: str, reason: str, 
                 question_index: int = None, timestamp: datetime = None):
        self.from_difficulty = from_difficulty
        self.to_difficulty = to_difficulty
        self.reason = reason
        self.question_index = question_index
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "from_difficulty": self.from_difficulty,
            "to_difficulty": self.to_difficulty,
            "reason": self.reason,
            "question_index": self.question_index,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DifficultyChange':
        """Create from dictionary for JSON deserialization"""
        return cls(
            from_difficulty=data["from_difficulty"],
            to_difficulty=data["to_difficulty"],
            reason=data["reason"],
            question_index=data.get("question_index"),
            timestamp=datetime.fromisoformat(data["timestamp"])
        )


class SessionDifficultyState:
    """Session-specific difficulty state management"""
    
    def __init__(self, session_id: int, initial_difficulty: str):
        self.session_id = session_id
        self.initial_difficulty = initial_difficulty
        self.current_difficulty = initial_difficulty
        self.final_difficulty = None
        self.difficulty_changes: List[DifficultyChange] = []
        self.adaptive_adjustments = []
        self.last_updated = datetime.utcnow()
        self.is_finalized = False
    
    def update_difficulty(self, new_difficulty: str, reason: str, question_index: int = None):
        """Update difficulty for this specific session"""
        if self.is_finalized:
            logger.warning(f"Session {self.session_id}: Attempted to update finalized difficulty state")
            return
        
        change = DifficultyChange(
            from_difficulty=self.current_difficulty,
            to_difficulty=new_difficulty,
            reason=reason,
            question_index=question_index,
            timestamp=datetime.utcnow()
        )
        
        self.difficulty_changes.append(change)
        self.current_difficulty = new_difficulty
        self.last_updated = datetime.utcnow()
        
        logger.info(f"Session {self.session_id}: Difficulty updated from {change.from_difficulty} to {new_difficulty} - {reason}")
    
    def finalize_difficulty(self):
        """Mark the final difficulty when session completes"""
        self.final_difficulty = self.current_difficulty
        self.is_finalized = True
        self.last_updated = datetime.utcnow()
        logger.info(f"Session {self.session_id}: Final difficulty set to {self.final_difficulty}")
    
    def get_difficulty_for_practice(self) -> str:
        """Get the appropriate difficulty for practice sessions"""
        # Use final difficulty if session is completed, otherwise current
        return self.final_difficulty or self.current_difficulty
    
    def get_changes_count(self) -> int:
        """Get the number of difficulty changes in this session"""
        return len(self.difficulty_changes)
    
    def has_difficulty_changed(self) -> bool:
        """Check if difficulty has changed from initial"""
        return self.current_difficulty != self.initial_difficulty
    
    def get_difficulty_progression(self) -> List[str]:
        """Get the progression of difficulties throughout the session"""
        progression = [self.initial_difficulty]
        for change in self.difficulty_changes:
            progression.append(change.to_difficulty)
        return progression
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "session_id": self.session_id,
            "initial_difficulty": self.initial_difficulty,
            "current_difficulty": self.current_difficulty,
            "final_difficulty": self.final_difficulty,
            "difficulty_changes": [change.to_dict() for change in self.difficulty_changes],
            "last_updated": self.last_updated.isoformat(),
            "is_finalized": self.is_finalized
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionDifficultyState':
        """Create from dictionary for JSON deserialization"""
        state = cls(data["session_id"], data["initial_difficulty"])
        state.current_difficulty = data["current_difficulty"]
        state.final_difficulty = data.get("final_difficulty")
        state.last_updated = datetime.fromisoformat(data["last_updated"])
        state.is_finalized = data.get("is_finalized", False)
        
        # Restore difficulty changes
        for change_data in data.get("difficulty_changes", []):
            state.difficulty_changes.append(DifficultyChange.from_dict(change_data))
        
        return state


class SessionSpecificDifficultyService:
    """Manages difficulty state per session with proper isolation"""
    
    def __init__(self, db: Session):
        self.db = db
        self.session_states: Dict[int, SessionDifficultyState] = {}  # In-memory cache for active sessions
        self.difficulty_mapping = DifficultyMappingService
        self.difficulty_levels = ["easy", "medium", "hard", "expert"]
    
    def initialize_session_difficulty(self, session_id: int, user_selected_difficulty: str) -> SessionDifficultyState:
        """Initialize difficulty state for a new session"""
        
        # Always use user's selected difficulty for new sessions
        session_state = SessionDifficultyState(session_id, user_selected_difficulty)
        
        # Store in cache and database
        self.session_states[session_id] = session_state
        self._persist_session_difficulty_state(session_state)
        
        logger.info(f"Initialized session {session_id} with user-selected difficulty: {user_selected_difficulty}")
        return session_state
    
    def get_session_difficulty_state(self, session_id: int) -> Optional[SessionDifficultyState]:
        """Get difficulty state for a specific session"""
        
        # Check cache first
        if session_id in self.session_states:
            return self.session_states[session_id]
        
        # Load from database
        session_state = self._load_session_difficulty_state(session_id)
        if session_state:
            self.session_states[session_id] = session_state
        
        return session_state
    
    def update_session_difficulty(self, session_id: int, new_difficulty: str, reason: str, question_index: int = None) -> bool:
        """Update difficulty for a specific session only"""
        
        session_state = self.get_session_difficulty_state(session_id)
        if not session_state:
            logger.error(f"No difficulty state found for session {session_id}")
            return False
        
        # Update the session-specific state
        session_state.update_difficulty(new_difficulty, reason, question_index)
        
        # Persist the updated state
        self._persist_session_difficulty_state(session_state)
        
        logger.info(f"Updated difficulty for session {session_id}: {reason}")
        return True
    
    def finalize_session_difficulty(self, session_id: int) -> bool:
        """Finalize difficulty state when session completes"""
        
        session_state = self.get_session_difficulty_state(session_id)
        if not session_state:
            logger.error(f"No difficulty state found for session {session_id}")
            return False
        
        # Finalize the state
        session_state.finalize_difficulty()
        
        # Persist the finalized state
        self._persist_session_difficulty_state(session_state)
        
        # Update the database session record
        try:
            session = self.db.query(InterviewSession).filter(
                InterviewSession.id == session_id
            ).first()
            
            if session:
                session.final_difficulty_level = session_state.final_difficulty
                session.difficulty_changes_count = len(session_state.difficulty_changes)
                self.db.commit()
                logger.info(f"Finalized difficulty for session {session_id}: {session_state.final_difficulty}")
            
        except Exception as e:
            logger.error(f"Error updating session final difficulty: {str(e)}")
            self.db.rollback()
            return False
        
        return True
    
    def get_difficulty_for_practice_session(self, parent_session_id: int) -> str:
        """Get the appropriate difficulty for a practice session"""
        
        logger.info(f"=== PRACTICE SESSION DIFFICULTY INHERITANCE ===")
        logger.info(f"Getting difficulty for practice session from parent {parent_session_id}")
        
        parent_state = self.get_session_difficulty_state(parent_session_id)
        if not parent_state:
            logger.warning(f"No difficulty state found for parent session {parent_session_id}")
            # Fallback to database
            parent_session = self.db.query(InterviewSession).filter(
                InterviewSession.id == parent_session_id
            ).first()
            
            if parent_session:
                # Use final_difficulty_level if available, otherwise use difficulty_level
                if parent_session.final_difficulty_level:
                    practice_difficulty = parent_session.final_difficulty_level
                    logger.info(f"Using final_difficulty_level from database: {practice_difficulty}")
                else:
                    practice_difficulty = parent_session.difficulty_level or "medium"
                    logger.info(f"Using difficulty_level from database: {practice_difficulty}")
                return practice_difficulty
            else:
                logger.error(f"Parent session {parent_session_id} not found in database")
                return "medium"
        
        # Use the final difficulty from the parent session
        practice_difficulty = parent_state.get_difficulty_for_practice()
        logger.info(f"Using difficulty from session state: {practice_difficulty}")
        logger.info(f"Parent session state: initial={parent_state.initial_difficulty}, current={parent_state.current_difficulty}, final={parent_state.final_difficulty}")
        logger.info(f"=== END PRACTICE SESSION DIFFICULTY INHERITANCE ===")
        
        return practice_difficulty
    
    def clear_session_cache(self, session_id: int):
        """Clear session from cache when no longer needed"""
        if session_id in self.session_states:
            del self.session_states[session_id]
            logger.debug(f"Cleared session {session_id} from difficulty state cache")
    
    def _persist_session_difficulty_state(self, session_state: SessionDifficultyState):
        """Save session difficulty state to database"""
        try:
            session = self.db.query(InterviewSession).filter(
                InterviewSession.id == session_state.session_id
            ).first()
            
            if session:
                # Update session with current difficulty state
                session.current_difficulty_level = session_state.current_difficulty
                session.initial_difficulty_level = session_state.initial_difficulty
                if session_state.is_finalized:
                    session.final_difficulty_level = session_state.final_difficulty
                
                # Store difficulty changes as JSON
                session.difficulty_state_json = json.dumps(session_state.to_dict())
                session.difficulty_changes_count = len(session_state.difficulty_changes)
                
                self.db.commit()
                logger.debug(f"Persisted difficulty state for session {session_state.session_id}")
            
        except Exception as e:
            logger.error(f"Error persisting session difficulty state: {str(e)}")
            self.db.rollback()
    
    def _load_session_difficulty_state(self, session_id: int) -> Optional[SessionDifficultyState]:
        """Load session difficulty state from database"""
        try:
            session = self.db.query(InterviewSession).filter(
                InterviewSession.id == session_id
            ).first()
            
            if not session:
                return None
            
            # Try to load from JSON state first
            if session.difficulty_state_json:
                try:
                    state_data = json.loads(session.difficulty_state_json)
                    return SessionDifficultyState.from_dict(state_data)
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Error loading difficulty state JSON for session {session_id}: {str(e)}")
            
            # Fallback to basic session data
            initial_difficulty = session.initial_difficulty_level or session.difficulty_level or "medium"
            state = SessionDifficultyState(session_id, initial_difficulty)
            
            if session.current_difficulty_level:
                state.current_difficulty = session.current_difficulty_level
            
            if session.final_difficulty_level:
                state.final_difficulty = session.final_difficulty_level
                state.is_finalized = True
            
            logger.debug(f"Loaded difficulty state for session {session_id}")
            return state
            
        except Exception as e:
            logger.error(f"Error loading session difficulty state: {str(e)}")
            return None
    
    def get_session_difficulty_info(self, session_id: int) -> Dict[str, Any]:
        """Get comprehensive difficulty information for a session"""
        
        session_state = self.get_session_difficulty_state(session_id)
        if not session_state:
            return {
                "session_id": session_id,
                "initial_difficulty": "medium",
                "current_difficulty": "medium",
                "final_difficulty": None,
                "has_changed": False,
                "change_count": 0,
                "is_finalized": False
            }
        
        return {
            "session_id": session_id,
            "initial_difficulty": session_state.initial_difficulty,
            "current_difficulty": session_state.current_difficulty,
            "final_difficulty": session_state.final_difficulty,
            "has_changed": session_state.has_difficulty_changed(),
            "change_count": len(session_state.difficulty_changes),
            "is_finalized": session_state.is_finalized,
            "difficulty_progression": session_state.get_difficulty_progression(),
            "last_updated": session_state.last_updated.isoformat()
        }