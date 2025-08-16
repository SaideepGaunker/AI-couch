"""
Feedback-related Pydantic schemas
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, field_validator


class AnswerEvaluation(BaseModel):
    question: str
    answer: str
    role: str
    user_experience: str = "intermediate"
    
    @field_validator('user_experience')
    @classmethod
    def validate_user_experience(cls, v):
        allowed_levels = ['beginner', 'intermediate', 'advanced']
        if v not in allowed_levels:
            raise ValueError(f'User experience must be one of: {", ".join(allowed_levels)}')
        return v


class FeedbackResponse(BaseModel):
    content_quality_score: float
    strengths: List[str]
    weaknesses: List[str]
    improvement_suggestions: List[str]
    overall_feedback: str
    score_breakdown: Dict[str, float]
    generated_at: datetime


class PerformanceData(BaseModel):
    overall_score: float
    body_language_score: float
    tone_confidence_score: float
    content_quality_score: float
    session_type: str
    response_time: Optional[int] = None


class UserContext(BaseModel):
    role: str
    experience_level: str
    target_roles: List[str]
    institution_id: Optional[int] = None


class PersonalizedFeedback(BaseModel):
    overall_assessment: str
    key_strengths: List[str]
    areas_for_improvement: List[str]
    specific_recommendations: List[Dict[str, Any]]
    next_steps: List[str]
    motivational_message: str
    generated_at: datetime


class FeedbackRequest(BaseModel):
    session_id: int
    include_ai_feedback: bool = True
    include_recommendations: bool = True