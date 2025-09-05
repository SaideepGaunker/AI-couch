"""
User Progress Pydantic schemas for enhanced performance tracking
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class CreateProgressRequest(BaseModel):
    """Request schema for creating a progress record"""
    metric_type: str = Field(..., description="Type of metric (confidence, body_language, content_quality)")
    score: float = Field(..., ge=0, le=100, description="Score value between 0 and 100")
    session_date: Optional[datetime] = Field(None, description="Date of the session")
    improvement_trend: Optional[float] = Field(0.0, description="Improvement trend value")


class RecommendationSchema(BaseModel):
    """Schema for learning recommendations"""
    category: str
    resource_type: str
    title: str
    url: str
    priority: str = "medium"
    added_at: Optional[str] = None


class ImprovementAreaSchema(BaseModel):
    """Schema for improvement areas"""
    area: str
    priority: str
    suggestions: List[str]
    added_at: Optional[str] = None


class LearningSuggestionSchema(BaseModel):
    """Schema for learning suggestions"""
    suggestion: str
    category: str
    difficulty: str = "intermediate"
    added_at: Optional[str] = None


class UserProgressResponse(BaseModel):
    """Response schema for user progress records"""
    id: int
    user_id: int
    metric_type: str
    score: float
    session_date: datetime
    improvement_trend: float
    recommendations: Optional[List[Dict[str, Any]]] = []
    improvement_areas: Optional[List[Dict[str, Any]]] = []
    learning_suggestions: Optional[List[Dict[str, Any]]] = []
    
    model_config = ConfigDict(from_attributes=True)


class UserProgressSummaryResponse(BaseModel):
    """Response schema for user progress summary"""
    user_id: int
    period_days: int
    total_records: int
    average_scores: Dict[str, float]
    improvement_trends: Dict[str, float]
    recommendations: List[Dict[str, Any]]
    improvement_areas: List[Dict[str, Any]]
    learning_suggestions: List[Dict[str, Any]]


class PerformanceInsightsResponse(BaseModel):
    """Response schema for performance insights"""
    insights: List[str]
    recommendations: List[Dict[str, Any]]
    improvement_areas: List[Dict[str, Any]]
    learning_suggestions: List[Dict[str, Any]]


class ProgressMetricSummary(BaseModel):
    """Summary of progress metrics"""
    metric_type: str
    average_score: float
    improvement_trend: float
    total_records: int
    latest_score: Optional[float] = None
    latest_date: Optional[datetime] = None


class EnhancedProgressAnalytics(BaseModel):
    """Enhanced analytics for user progress"""
    user_id: int
    analysis_period_days: int
    overall_performance_score: float
    performance_trend: str  # improving, declining, stable
    metric_summaries: List[ProgressMetricSummary]
    top_strengths: List[str]
    priority_improvement_areas: List[Dict[str, Any]]
    recommended_actions: List[Dict[str, Any]]
    learning_path_suggestions: List[Dict[str, Any]]
    next_milestone: Optional[Dict[str, Any]] = None