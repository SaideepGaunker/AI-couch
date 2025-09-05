"""
Recommendation system related Pydantic schemas
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, field_validator, ConfigDict
from enum import Enum


class ResourceCategory(str, Enum):
    BODY_LANGUAGE = "body_language"
    VOICE_ANALYSIS = "voice_analysis"
    CONTENT_QUALITY = "content_quality"
    OVERALL = "overall"


class ResourceType(str, Enum):
    VIDEO = "video"
    COURSE = "course"


class ResourceLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class FeedbackType(str, Enum):
    LIKED = "liked"
    DISLIKED = "disliked"
    NEUTRAL = "neutral"


class RecommendationRequest(BaseModel):
    body_language: float
    voice_analysis: float
    content_quality: float
    overall: float
    
    @field_validator('body_language', 'voice_analysis', 'content_quality', 'overall')
    @classmethod
    def validate_scores(cls, v):
        if v < 0 or v > 100:
            raise ValueError('Scores must be between 0 and 100')
        return v


class LearningResourceCreate(BaseModel):
    category: ResourceCategory
    type: ResourceType
    level: ResourceLevel
    title: str
    url: str
    provider: Optional[str] = None
    tags: Optional[List[str]] = []
    ranking_weight: Optional[float] = 1.0
    
    @field_validator('ranking_weight')
    @classmethod
    def validate_ranking_weight(cls, v):
        if v and (v < 0 or v > 10):
            raise ValueError('Ranking weight must be between 0 and 10')
        return v


class LearningResourceResponse(BaseModel):
    id: int
    category: str
    type: str
    level: str
    title: str
    url: str
    provider: Optional[str] = None
    tags: List[str] = []
    ranking_weight: float
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserRecommendationCreate(BaseModel):
    resource_id: int
    clicked: Optional[bool] = False
    user_feedback: Optional[FeedbackType] = FeedbackType.NEUTRAL


class UserRecommendationResponse(BaseModel):
    id: int
    user_id: int
    resource_id: int
    recommended_at: datetime
    clicked: bool
    user_feedback: str
    feedback_at: Optional[datetime] = None
    resource: LearningResourceResponse
    
    model_config = ConfigDict(from_attributes=True)


class RecommendationResponse(BaseModel):
    category: str
    level: str
    video: Optional[LearningResourceResponse] = None
    course: Optional[LearningResourceResponse] = None


class RecommendationsResponse(BaseModel):
    body_language: RecommendationResponse
    voice_analysis: RecommendationResponse
    content_quality: RecommendationResponse
    overall: RecommendationResponse
    generated_at: datetime


class FeedbackRequest(BaseModel):
    feedback: FeedbackType