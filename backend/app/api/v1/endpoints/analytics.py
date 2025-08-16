"""
Analytics and progress tracking endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.services.analytics_service import AnalyticsService
from app.db.models import User

router = APIRouter()


@router.get("/progress")
async def get_user_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's progress and performance analytics"""
    analytics_service = AnalyticsService(db)
    
    try:
        progress_data = analytics_service.get_user_progress(current_user.id)
        return progress_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve progress data"
        )


@router.get("/sessions")
async def get_session_history(
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's session history with analytics"""
    analytics_service = AnalyticsService(db)
    
    try:
        sessions = analytics_service.get_user_session_analytics(current_user.id, limit)
        return {"sessions": sessions}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session history"
        )


@router.get("/trends")
async def get_improvement_trends(
    days: int = Query(30, ge=7, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's improvement trends over time"""
    analytics_service = AnalyticsService(db)
    
    try:
        trends = analytics_service.get_user_trends(current_user.id, days)
        return {"trends": trends, "period_days": days}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve trend data"
        )


@router.get("/dashboard")
async def get_dashboard_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive dashboard data"""
    analytics_service = AnalyticsService(db)
    
    try:
        dashboard_data = analytics_service.get_dashboard_data(current_user.id)
        return dashboard_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve dashboard data"
        )


@router.get("/recommendations")
async def get_personalized_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get personalized recommendations for improvement"""
    analytics_service = AnalyticsService(db)
    
    try:
        recommendations = analytics_service.get_personalized_recommendations(current_user.id)
        return {"recommendations": recommendations}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recommendations"
        )


# Admin endpoints
@router.get("/admin/overview")
async def get_admin_analytics_overview(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get system-wide analytics overview (admin only)"""
    analytics_service = AnalyticsService(db)
    
    try:
        overview = analytics_service.get_system_overview()
        return overview
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system analytics"
        )