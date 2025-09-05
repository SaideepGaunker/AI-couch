"""
User Progress API endpoints for enhanced performance tracking
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.services.user_progress_service import UserProgressService
from app.core.dependencies import get_current_user
from app.schemas.user_progress import (
    UserProgressResponse, UserProgressSummaryResponse,
    PerformanceInsightsResponse, CreateProgressRequest
)

router = APIRouter()


@router.post("/", response_model=UserProgressResponse)
async def create_progress_record(
    progress_data: CreateProgressRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new user progress record"""
    
    progress_service = UserProgressService(db)
    
    try:
        progress = progress_service.create_progress_record(
            user_id=current_user.id,
            metric_type=progress_data.metric_type,
            score=progress_data.score,
            session_date=progress_data.session_date,
            improvement_trend=progress_data.improvement_trend
        )
        
        return UserProgressResponse.model_validate(progress)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create progress record: {str(e)}"
        )


@router.get("/summary", response_model=UserProgressSummaryResponse)
async def get_user_progress_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to include in summary"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive user progress summary with recommendations"""
    
    progress_service = UserProgressService(db)
    
    try:
        summary = progress_service.get_user_progress_summary(
            user_id=current_user.id,
            days=days
        )
        
        return UserProgressSummaryResponse(**summary)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get progress summary: {str(e)}"
        )


@router.get("/insights", response_model=PerformanceInsightsResponse)
async def get_performance_insights(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate performance insights and recommendations based on user data"""
    
    progress_service = UserProgressService(db)
    
    try:
        insights = progress_service.generate_performance_insights(
            user_id=current_user.id
        )
        
        return PerformanceInsightsResponse(**insights)
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate insights: {str(e)}"
        )


@router.post("/{progress_id}/recommendations")
async def add_recommendations(
    progress_id: int,
    recommendations: List[Dict[str, Any]],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add recommendations to a progress record"""
    
    progress_service = UserProgressService(db)
    
    try:
        progress = progress_service.add_recommendations_to_progress(
            progress_id=progress_id,
            recommendations=recommendations
        )
        
        return {"message": "Recommendations added successfully", "progress_id": progress.id}
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add recommendations: {str(e)}"
        )


@router.post("/{progress_id}/improvement-areas")
async def add_improvement_areas(
    progress_id: int,
    improvement_areas: List[Dict[str, Any]],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add improvement areas to a progress record"""
    
    progress_service = UserProgressService(db)
    
    try:
        progress = progress_service.add_improvement_areas_to_progress(
            progress_id=progress_id,
            improvement_areas=improvement_areas
        )
        
        return {"message": "Improvement areas added successfully", "progress_id": progress.id}
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add improvement areas: {str(e)}"
        )


@router.post("/{progress_id}/learning-suggestions")
async def add_learning_suggestions(
    progress_id: int,
    learning_suggestions: List[Dict[str, Any]],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add learning suggestions to a progress record"""
    
    progress_service = UserProgressService(db)
    
    try:
        progress = progress_service.add_learning_suggestions_to_progress(
            progress_id=progress_id,
            learning_suggestions=learning_suggestions
        )
        
        return {"message": "Learning suggestions added successfully", "progress_id": progress.id}
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add learning suggestions: {str(e)}"
        )