"""
Interview session related Pydantic schemas
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, field_validator, ConfigDict
from enum import Enum


class SessionType(str, Enum):
    HR = "hr"
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    MIXED = "mixed"


class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class InterviewSessionCreate(BaseModel):
    session_type: SessionType
    target_role: str
    duration: int = 30  # in minutes
    difficulty: Optional[str] = "intermediate"  # beginner, intermediate, advanced
    question_count: Optional[int] = 5
    enable_video: Optional[bool] = True
    enable_audio: Optional[bool] = True
    
    @field_validator('duration')
    @classmethod
    def validate_duration(cls, v):
        if v < 5 or v > 120:
            raise ValueError('Duration must be between 5 and 120 minutes')
        return v
    
    @field_validator('difficulty')
    @classmethod
    def validate_difficulty(cls, v):
        if v and v not in ['beginner', 'intermediate', 'advanced']:
            raise ValueError('Difficulty must be one of: beginner, intermediate, advanced')
        return v
    
    @field_validator('question_count')
    @classmethod
    def validate_question_count(cls, v):
        if v and (v < 1 or v > 20):
            raise ValueError('Question count must be between 1 and 20')
        return v


class InterviewSessionUpdate(BaseModel):
    status: Optional[SessionStatus] = None
    overall_score: Optional[float] = None
    completed_at: Optional[datetime] = None


class InterviewSessionResponse(BaseModel):
    id: int
    user_id: int
    session_type: str
    target_role: str
    duration: int
    status: str
    overall_score: float
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class SessionQuestionResponse(BaseModel):
    question_id: int
    question_content: str
    question_type: str
    expected_duration: int
    order_index: int


class SessionStartResponse(BaseModel):
    session: InterviewSessionResponse
    questions: List[SessionQuestionResponse]
    total_questions: int
    estimated_duration: int


class SessionProgressResponse(BaseModel):
    session_id: int
    current_question: int
    total_questions: int
    elapsed_time: int
    remaining_time: int
    completion_percentage: float


class AnswerSubmission(BaseModel):
    question_id: int
    answer_text: str
    response_time: int  # in seconds
    audio_data: Optional[str] = None  # base64 encoded
    video_data: Optional[str] = None  # base64 encoded


class AnswerSubmissionResponse(BaseModel):
    question_id: int
    submitted: bool
    next_question_id: Optional[int] = None
    session_completed: bool = False
    real_time_feedback: Optional[Dict[str, Any]] = None


class SessionSummaryResponse(BaseModel):
    session: InterviewSessionResponse
    total_questions: int
    questions_answered: int
    average_scores: Dict[str, float]
    time_breakdown: Dict[str, int]
    strengths: List[str]
    improvements: List[str]
    recommendations: List[str]


class SessionConfigRequest(BaseModel):
    role: str
    difficulty: str = "intermediate"
    session_type: SessionType = SessionType.MIXED
    duration: int = 30
    question_count: int = 5
    
    @field_validator('question_count')
    @classmethod
    def validate_question_count(cls, v):
        if v < 1 or v > 20:
            raise ValueError('Question count must be between 1 and 20')
        return v