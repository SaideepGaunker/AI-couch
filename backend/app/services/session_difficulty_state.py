"""
Session-Specific Difficulty State Management Classes

This module provides classes for managing difficulty state on a per-session basis,
ensuring proper isolation between different interview sessions.
"""
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
import json

logger = logging.getLogger(__name__)


@dataclass
class DifficultyChange:
    """
    Records individual difficulty adjustments within a session
    
    This class tracks each time the difficulty is changed during an interview session,
    providing a complete audit trail of adaptive difficulty adjustments.
    """
    from_difficulty: str
    to_difficulty: str
    reason: str
    timestamp: datetime
    question_index: Optional[int] = None
    change_number: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "from_difficulty": self.from_difficulty,
            "to_difficulty": self.to_difficulty,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
            "question_index": self.question_index,
            "change_number": self.change_number
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DifficultyChange':
        """Create from dictionary (JSON deserialization)"""
        return cls(
            from_difficulty=data["from_difficulty"],
            to_difficulty=data["to_difficulty"],
            reason=data["reason"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            question_index=data.get("question_index"),
            change_number=data.get("change_number")
        )


class SessionDifficultyState:
    """
    Session-specific difficulty state management
    
    This class manages the difficulty state for a single interview session,
    providing isolation from other sessions and proper tracking of difficulty changes.
    """
    
    def __init__(self, session_id: int, initial_difficulty: str):
        """
        Initialize session difficulty state
        
        Args:
            session_id: The ID of the interview session
            initial_difficulty: The starting difficulty level for this session
        """
        self.session_id = session_id
        self.initial_difficulty = initial_difficulty
        self.current_difficulty = initial_difficulty
        self.final_difficulty: Optional[str] = None
        self.difficulty_changes: List[DifficultyChange] = []
        self.adaptive_adjustments: List[Dict[str, Any]] = []
        self.last_updated = datetime.utcnow()
        self.is_finalized = False
        
        logger.info(f"Initialized difficulty state for session {session_id} with initial difficulty: {initial_difficulty}")
    
    def update_difficulty(self, new_difficulty: str, reason: str, question_index: Optional[int] = None) -> bool:
        """
        Update difficulty for this specific session
        
        Args:
            new_difficulty: The new difficulty level to set
            reason: Reason for the difficulty change (e.g., "poor_performance", "excellent_performance")
            question_index: Optional index of the question that triggered the change
            
        Returns:
            bool: True if difficulty was updated, False if no change was needed
        """
        try:
            # Don't update if already finalized
            if self.is_finalized:
                logger.warning(f"Session {self.session_id}: Cannot update difficulty - session is finalized")
                return False
            
            # Don't update if difficulty is the same
            if new_difficulty == self.current_difficulty:
                logger.info(f"Session {self.session_id}: No difficulty change needed (already at {new_difficulty})")
                return False
            
            # Create difficulty change record
            change = DifficultyChange(
                from_difficulty=self.current_difficulty,
                to_difficulty=new_difficulty,
                reason=reason,
                question_index=question_index,
                timestamp=datetime.utcnow(),
                change_number=len(self.difficulty_changes) + 1
            )
            
            # Update state
            old_difficulty = self.current_difficulty
            self.current_difficulty = new_difficulty
            self.difficulty_changes.append(change)
            self.last_updated = datetime.utcnow()
            
            # Add to adaptive adjustments for compatibility
            self.adaptive_adjustments.append({
                "from": old_difficulty,
                "to": new_difficulty,
                "reason": reason,
                "timestamp": change.timestamp.isoformat(),
                "question_index": question_index
            })
            
            logger.info(f"Session {self.session_id}: Difficulty updated from {old_difficulty} to {new_difficulty} - {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Session {self.session_id}: Error updating difficulty - {str(e)}")
            return False
    
    def finalize_difficulty(self) -> str:
        """
        Mark the final difficulty when session completes
        
        Returns:
            str: The final difficulty level
        """
        try:
            self.final_difficulty = self.current_difficulty
            self.is_finalized = True
            self.last_updated = datetime.utcnow()
            
            logger.info(f"Session {self.session_id}: Final difficulty set to {self.final_difficulty}")
            return self.final_difficulty
            
        except Exception as e:
            logger.error(f"Session {self.session_id}: Error finalizing difficulty - {str(e)}")
            return self.current_difficulty
    
    def get_difficulty_for_practice(self) -> str:
        """
        Get the appropriate difficulty for practice sessions
        
        Returns:
            str: The difficulty level to use for practice sessions (final if available, otherwise current)
        """
        practice_difficulty = self.final_difficulty or self.current_difficulty
        logger.info(f"Session {self.session_id}: Practice difficulty is {practice_difficulty}")
        return practice_difficulty
    
    def get_changes_count(self) -> int:
        """Get the number of difficulty changes in this session"""
        return len(self.difficulty_changes)
    
    def has_difficulty_changed(self) -> bool:
        """Check if difficulty has changed from initial level"""
        return self.current_difficulty != self.initial_difficulty
    
    def get_difficulty_progression(self) -> List[str]:
        """Get the progression of difficulty levels throughout the session"""
        progression = [self.initial_difficulty]
        for change in self.difficulty_changes:
            progression.append(change.to_difficulty)
        return progression
    
    def get_latest_change(self) -> Optional[DifficultyChange]:
        """Get the most recent difficulty change"""
        return self.difficulty_changes[-1] if self.difficulty_changes else None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization
        
        Returns:
            Dict containing all state information
        """
        return {
            "session_id": self.session_id,
            "initial_difficulty": self.initial_difficulty,
            "current_difficulty": self.current_difficulty,
            "final_difficulty": self.final_difficulty,
            "difficulty_changes": [change.to_dict() for change in self.difficulty_changes],
            "adaptive_adjustments": self.adaptive_adjustments,
            "last_updated": self.last_updated.isoformat(),
            "is_finalized": self.is_finalized,
            "changes_count": len(self.difficulty_changes),
            "has_changed": self.has_difficulty_changed()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionDifficultyState':
        """
        Create from dictionary (JSON deserialization)
        
        Args:
            data: Dictionary containing state information
            
        Returns:
            SessionDifficultyState instance
        """
        try:
            # Create instance with basic info
            instance = cls(
                session_id=data["session_id"],
                initial_difficulty=data["initial_difficulty"]
            )
            
            # Restore state
            instance.current_difficulty = data["current_difficulty"]
            instance.final_difficulty = data.get("final_difficulty")
            instance.last_updated = datetime.fromisoformat(data["last_updated"])
            instance.is_finalized = data.get("is_finalized", False)
            instance.adaptive_adjustments = data.get("adaptive_adjustments", [])
            
            # Restore difficulty changes
            changes_data = data.get("difficulty_changes", [])
            instance.difficulty_changes = [
                DifficultyChange.from_dict(change_data) 
                for change_data in changes_data
            ]
            
            logger.info(f"Restored difficulty state for session {instance.session_id}")
            return instance
            
        except Exception as e:
            logger.error(f"Error creating SessionDifficultyState from dict: {str(e)}")
            # Return a basic instance if restoration fails
            return cls(
                session_id=data.get("session_id", 0),
                initial_difficulty=data.get("initial_difficulty", "medium")
            )
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the difficulty state for logging/debugging
        
        Returns:
            Dict with summary information
        """
        return {
            "session_id": self.session_id,
            "initial": self.initial_difficulty,
            "current": self.current_difficulty,
            "final": self.final_difficulty,
            "changes": len(self.difficulty_changes),
            "finalized": self.is_finalized,
            "progression": self.get_difficulty_progression()
        }
    
    def validate_state(self) -> List[str]:
        """
        Validate the current state and return any issues found
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        try:
            # Check basic state consistency
            if not self.session_id or self.session_id <= 0:
                errors.append("Invalid session_id")
            
            if not self.initial_difficulty:
                errors.append("Missing initial_difficulty")
            
            if not self.current_difficulty:
                errors.append("Missing current_difficulty")
            
            # Check difficulty change consistency
            expected_difficulty = self.initial_difficulty
            for i, change in enumerate(self.difficulty_changes):
                if change.from_difficulty != expected_difficulty:
                    errors.append(f"Change {i+1}: from_difficulty mismatch (expected {expected_difficulty}, got {change.from_difficulty})")
                expected_difficulty = change.to_difficulty
            
            if expected_difficulty != self.current_difficulty:
                errors.append(f"Current difficulty mismatch (expected {expected_difficulty}, got {self.current_difficulty})")
            
            # Check finalization state
            if self.is_finalized and not self.final_difficulty:
                errors.append("Session is finalized but final_difficulty is not set")
            
            if self.final_difficulty and not self.is_finalized:
                errors.append("final_difficulty is set but session is not finalized")
            
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return errors