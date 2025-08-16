"""
Question-related Pydantic schemas
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, field_validator, ConfigDict


class QuestionBase(BaseModel):
    content: str
    question_type: str
    role_category: str
    difficulty_level: str
    expected_duration: int


class QuestionCreate(QuestionBase):
    generated_by: str = "gemini_api"
    
    @field_validator('question_type')
    @classmethod
    def validate_question_type(cls, v):
        allowed_types = ['behavioral', 'technical', 'situational', 'general']
        if v not in allowed_types:
            raise ValueError(f'Question type must be one of: {", ".join(allowed_types)}')
        return v
    
    @field_validator('difficulty_level')
    @classmethod
    def validate_difficulty_level(cls, v):
        allowed_levels = ['beginner', 'intermediate', 'advanced']
        if v not in allowed_levels:
            raise ValueError(f'Difficulty level must be one of: {", ".join(allowed_levels)}')
        return v
    
    @field_validator('expected_duration')
    @classmethod
    def validate_duration(cls, v):
        if v < 1 or v > 15:
            raise ValueError('Expected duration must be between 1 and 15 minutes')
        return v


class QuestionResponse(QuestionBase):
    id: int
    generated_by: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class QuestionGenerate(BaseModel):
    role: str
    difficulty: str = "intermediate"
    question_type: str = "mixed"
    count: int = 5
    
    @field_validator('count')
    @classmethod
    def validate_count(cls, v):
        if v < 1 or v > 20:
            raise ValueError('Count must be between 1 and 20')
        return v


class QuestionSearch(BaseModel):
    role_category: Optional[str] = None
    question_type: Optional[str] = None
    difficulty_level: Optional[str] = None
    limit: int = 10
    offset: int = 0
    
    @field_validator('limit')
    @classmethod
    def validate_limit(cls, v):
        if v < 1 or v > 100:
            raise ValueError('Limit must be between 1 and 100')
        return v


class AnswerEvaluationRequest(BaseModel):
    question_id: int
    answer_text: str
    context: Optional[dict] = {}


class AnswerEvaluationResponse(BaseModel):
    overall_score: float
    scores: dict
    strengths: List[str]
    improvements: List[str]
    suggestions: List[str]


class FeedbackRequest(BaseModel):
    session_id: int
    performance_data: dict


class FeedbackResponse(BaseModel):
    summary: str
    strengths: List[str]
    improvements: List[str]
    action_items: List[str]
    motivation: str