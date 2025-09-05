"""
Recommendations API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.schemas.recommendation import (
    RecommendationRequest, RecommendationsResponse, LearningResourceResponse,
    LearningResourceCreate, FeedbackRequest, UserRecommendationResponse
)
from app.core.dependencies import get_current_user, rate_limit
from app.services.recommendation_service import RecommendationService
from app.crud.recommendation import (
    create_learning_resource, get_learning_resources, get_learning_resource,
    update_learning_resource, delete_learning_resource, seed_learning_resources
)
from app.db.models import User

router = APIRouter()


@router.post("/recommendations", response_model=RecommendationsResponse)
async def get_recommendations(
    scores: RecommendationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(max_calls=10, window_seconds=300))
):
    """Get personalized recommendations based on performance scores"""
    try:
        recommendation_service = RecommendationService(db)
        recommendations = recommendation_service.get_recommendations(current_user.id, scores)
        return recommendations
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate recommendations"
        )


@router.post("/recommendations/{resource_id}/track")
async def track_recommendation_click(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Track when user clicks on a recommendation"""
    try:
        recommendation_service = RecommendationService(db)
        success = recommendation_service.track_click(current_user.id, resource_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recommendation not found"
            )
        
        return {"message": "Click tracked successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to track click"
        )


@router.post("/recommendations/{resource_id}/feedback")
async def submit_recommendation_feedback(
    resource_id: int,
    feedback_data: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit user feedback for a recommendation"""
    try:
        recommendation_service = RecommendationService(db)
        success = recommendation_service.submit_feedback(
            current_user.id, 
            resource_id, 
            feedback_data.feedback
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recommendation not found"
            )
        
        return {"message": "Feedback submitted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback"
        )


@router.get("/recommendations/history")
async def get_recommendation_history(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's recommendation history"""
    try:
        recommendation_service = RecommendationService(db)
        history = recommendation_service.get_user_recommendation_history(current_user.id, limit)
        return {"history": history}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recommendation history"
        )


# Admin endpoints for managing learning resources
@router.post("/admin/resources", response_model=LearningResourceResponse)
async def create_resource(
    resource_data: LearningResourceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new learning resource (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        resource = create_learning_resource(db, resource_data)
        return LearningResourceResponse.model_validate(resource)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create learning resource"
        )


@router.get("/admin/resources", response_model=List[LearningResourceResponse])
async def list_resources(
    category: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List learning resources with optional filtering (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        resources = get_learning_resources(db, category, resource_type, level, skip, limit)
        return [LearningResourceResponse.model_validate(r) for r in resources]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve learning resources"
        )


@router.get("/admin/resources/{resource_id}", response_model=LearningResourceResponse)
async def get_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get learning resource by ID (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    resource = get_learning_resource(db, resource_id)
    if not resource:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learning resource not found"
        )
    
    return LearningResourceResponse.model_validate(resource)


@router.put("/admin/resources/{resource_id}", response_model=LearningResourceResponse)
async def update_resource(
    resource_id: int,
    update_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update learning resource (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        resource = update_learning_resource(db, resource_id, update_data)
        if not resource:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning resource not found"
            )
        
        return LearningResourceResponse.model_validate(resource)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update learning resource"
        )


@router.delete("/admin/resources/{resource_id}")
async def delete_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete learning resource (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        success = delete_learning_resource(db, resource_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Learning resource not found"
            )
        
        return {"message": "Learning resource deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete learning resource"
        )


@router.post("/admin/seed-resources")
async def seed_resources(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Seed database with initial learning resources (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        count = seed_learning_resources(db)
        return {
            "message": f"Successfully seeded {count} learning resources",
            "count": count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to seed learning resources"
        )