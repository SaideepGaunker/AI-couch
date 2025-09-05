"""
Unified Difficulty Mapping Service - Single source of truth for difficulty level labels
"""
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DifficultyMappingService:
    """Single source of truth for difficulty level labels across all components"""
    
    # Unified difficulty mapping - internal levels to display labels
    DIFFICULTY_LABELS: Dict[int, str] = {
        1: "Easy",
        2: "Medium", 
        3: "Hard",
        4: "Expert"
    }
    
    # String-based mapping for backward compatibility
    STRING_TO_LEVEL: Dict[str, int] = {
        "easy": 1,
        "medium": 2,
        "hard": 3,
        "expert": 4
    }
    
    # Level to string mapping for backward compatibility
    LEVEL_TO_STRING: Dict[int, str] = {
        1: "easy",
        2: "medium",
        3: "hard",
        4: "expert"
    }
    
    @classmethod
    def get_difficulty_label(cls, internal_level: int) -> str:
        """
        Convert internal difficulty level to consistent display label
        
        Args:
            internal_level: Internal difficulty level (1-4)
            
        Returns:
            Display label (Easy, Medium, Hard, Expert)
        """
        try:
            if not isinstance(internal_level, int):
                logger.warning(f"Invalid internal_level type: {type(internal_level)}, converting to int")
                internal_level = int(internal_level)
                
            label = cls.DIFFICULTY_LABELS.get(internal_level, "Unknown")
            
            if label == "Unknown":
                logger.warning(f"Unknown internal difficulty level: {internal_level}, defaulting to Easy")
                return "Easy"
                
            return label
            
        except (ValueError, TypeError) as e:
            logger.error(f"Error converting internal_level to label: {e}, defaulting to Easy")
            return "Easy"
    
    @classmethod
    def get_internal_level(cls, label: str) -> int:
        """
        Convert display label back to internal level
        
        Args:
            label: Display label (Easy, Medium, Hard, Expert) or string level (easy, medium, hard, expert)
            
        Returns:
            Internal difficulty level (1-4)
        """
        try:
            if not isinstance(label, str):
                logger.warning(f"Invalid label type: {type(label)}, converting to string")
                label = str(label)
            
            # Normalize the label
            normalized_label = label.lower().strip()
            
            # Check string-based mapping first (for backward compatibility)
            if normalized_label in cls.STRING_TO_LEVEL:
                return cls.STRING_TO_LEVEL[normalized_label]
            
            # Check display label mapping
            for level, display_label in cls.DIFFICULTY_LABELS.items():
                if display_label.lower() == normalized_label:
                    return level
            
            logger.warning(f"Unknown difficulty label: {label}, defaulting to Medium (level 2)")
            return 2  # Default to Medium
            
        except Exception as e:
            logger.error(f"Error converting label to internal_level: {e}, defaulting to Medium (level 2)")
            return 2
    
    @classmethod
    def get_string_level(cls, internal_level: int) -> str:
        """
        Convert internal level to string level for backward compatibility
        
        Args:
            internal_level: Internal difficulty level (1-4)
            
        Returns:
            String level (easy, medium, hard, expert)
        """
        try:
            if not isinstance(internal_level, int):
                internal_level = int(internal_level)
                
            string_level = cls.LEVEL_TO_STRING.get(internal_level, "medium")
            
            if string_level == "medium" and internal_level not in cls.LEVEL_TO_STRING:
                logger.warning(f"Unknown internal difficulty level: {internal_level}, defaulting to medium")
                
            return string_level
            
        except (ValueError, TypeError) as e:
            logger.error(f"Error converting internal_level to string: {e}, defaulting to medium")
            return "medium"
    
    @classmethod
    def normalize_difficulty_input(cls, difficulty_input) -> int:
        """
        Normalize any difficulty input (int, string label, display label) to internal level
        
        Args:
            difficulty_input: Any difficulty representation
            
        Returns:
            Internal difficulty level (1-4)
        """
        try:
            # If it's already an integer, validate and return
            if isinstance(difficulty_input, int):
                if difficulty_input in cls.DIFFICULTY_LABELS:
                    return difficulty_input
                else:
                    logger.warning(f"Invalid integer difficulty level: {difficulty_input}, defaulting to 2")
                    return 2
            
            # If it's a string, convert using get_internal_level
            if isinstance(difficulty_input, str):
                return cls.get_internal_level(difficulty_input)
            
            # For any other type, try to convert to string first
            logger.warning(f"Unexpected difficulty input type: {type(difficulty_input)}, converting to string")
            return cls.get_internal_level(str(difficulty_input))
            
        except Exception as e:
            logger.error(f"Error normalizing difficulty input: {e}, defaulting to 2")
            return 2
    
    @classmethod
    def get_all_levels(cls) -> Dict[int, Dict[str, str]]:
        """
        Get all difficulty levels with their mappings
        
        Returns:
            Dictionary with internal level as key and mappings as value
        """
        return {
            level: {
                "display_label": cls.get_difficulty_label(level),
                "string_level": cls.get_string_level(level)
            }
            for level in cls.DIFFICULTY_LABELS.keys()
        }
    
    @classmethod
    def validate_difficulty_consistency(cls, internal_level: int, expected_label: str) -> bool:
        """
        Validate that an internal level matches the expected label
        
        Args:
            internal_level: Internal difficulty level
            expected_label: Expected display label
            
        Returns:
            True if consistent, False otherwise
        """
        try:
            actual_label = cls.get_difficulty_label(internal_level)
            return actual_label.lower() == expected_label.lower()
        except Exception as e:
            logger.error(f"Error validating difficulty consistency: {e}")
            return False