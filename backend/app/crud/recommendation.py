"""
CRUD operations for Learning Resources and User Recommendations
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime

from app.db.models import LearningResource, UserRecommendation
from app.schemas.recommendation import (
    LearningResourceCreate, ResourceCategory, ResourceType, ResourceLevel
)


def create_learning_resource(
    db: Session, 
    resource_data: LearningResourceCreate
) -> LearningResource:
    """Create new learning resource"""
    db_resource = LearningResource(
        category=resource_data.category.value,
        type=resource_data.type.value,
        level=resource_data.level.value,
        title=resource_data.title,
        url=resource_data.url,
        provider=resource_data.provider,
        tags=resource_data.tags or [],
        ranking_weight=resource_data.ranking_weight or 1.0
    )
    db.add(db_resource)
    db.commit()
    db.refresh(db_resource)
    return db_resource


def get_learning_resource(db: Session, resource_id: int) -> Optional[LearningResource]:
    """Get learning resource by ID"""
    return db.query(LearningResource).filter(LearningResource.id == resource_id).first()


def get_learning_resources(
    db: Session,
    category: Optional[str] = None,
    resource_type: Optional[str] = None,
    level: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[LearningResource]:
    """Get learning resources with optional filtering"""
    query = db.query(LearningResource)
    
    if category:
        query = query.filter(LearningResource.category == category)
    if resource_type:
        query = query.filter(LearningResource.type == resource_type)
    if level:
        query = query.filter(LearningResource.level == level)
    
    return query.offset(skip).limit(limit).all()


def update_learning_resource(
    db: Session,
    resource_id: int,
    update_data: Dict[str, Any]
) -> Optional[LearningResource]:
    """Update learning resource"""
    resource = get_learning_resource(db, resource_id)
    if not resource:
        return None
    
    for field, value in update_data.items():
        if hasattr(resource, field):
            setattr(resource, field, value)
    
    db.commit()
    db.refresh(resource)
    return resource


def delete_learning_resource(db: Session, resource_id: int) -> bool:
    """Delete learning resource"""
    resource = get_learning_resource(db, resource_id)
    if not resource:
        return False
    
    # Delete associated user recommendations first
    db.query(UserRecommendation).filter(
        UserRecommendation.resource_id == resource_id
    ).delete()
    
    db.delete(resource)
    db.commit()
    return True


def create_user_recommendation(
    db: Session,
    user_id: int,
    resource_id: int,
    clicked: bool = False,
    user_feedback: str = "neutral"
) -> UserRecommendation:
    """Create user recommendation record"""
    db_recommendation = UserRecommendation(
        user_id=user_id,
        resource_id=resource_id,
        recommended_at=datetime.utcnow(),
        clicked=clicked,
        user_feedback=user_feedback
    )
    db.add(db_recommendation)
    db.commit()
    db.refresh(db_recommendation)
    return db_recommendation


def get_user_recommendations(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 50
) -> List[UserRecommendation]:
    """Get user's recommendation history"""
    return db.query(UserRecommendation).filter(
        UserRecommendation.user_id == user_id
    ).order_by(
        UserRecommendation.recommended_at.desc()
    ).offset(skip).limit(limit).all()


def update_user_recommendation(
    db: Session,
    user_id: int,
    resource_id: int,
    clicked: Optional[bool] = None,
    user_feedback: Optional[str] = None
) -> Optional[UserRecommendation]:
    """Update user recommendation (for click tracking and feedback)"""
    recommendation = db.query(UserRecommendation).filter(
        and_(
            UserRecommendation.user_id == user_id,
            UserRecommendation.resource_id == resource_id
        )
    ).order_by(UserRecommendation.recommended_at.desc()).first()
    
    if not recommendation:
        return None
    
    if clicked is not None:
        recommendation.clicked = clicked
    if user_feedback is not None:
        recommendation.user_feedback = user_feedback
        recommendation.feedback_at = datetime.utcnow()
    
    db.commit()
    db.refresh(recommendation)
    return recommendation


def get_resource_statistics(db: Session, resource_id: int) -> Dict[str, Any]:
    """Get statistics for a learning resource"""
    total_recommendations = db.query(func.count(UserRecommendation.id)).filter(
        UserRecommendation.resource_id == resource_id
    ).scalar()
    
    total_clicks = db.query(func.count(UserRecommendation.id)).filter(
        and_(
            UserRecommendation.resource_id == resource_id,
            UserRecommendation.clicked == True
        )
    ).scalar()
    
    feedback_stats = db.query(
        UserRecommendation.user_feedback,
        func.count(UserRecommendation.id)
    ).filter(
        UserRecommendation.resource_id == resource_id
    ).group_by(UserRecommendation.user_feedback).all()
    
    click_rate = (total_clicks / total_recommendations * 100) if total_recommendations > 0 else 0
    
    feedback_breakdown = {feedback: count for feedback, count in feedback_stats}
    
    return {
        "total_recommendations": total_recommendations,
        "total_clicks": total_clicks,
        "click_rate": round(click_rate, 2),
        "feedback_breakdown": feedback_breakdown
    }


def seed_learning_resources(db: Session) -> int:
    """Seed the database with initial learning resources"""
    
    resources_data = [
        # Body Language - Beginner
        {
            "category": "body_language",
            "type": "video",
            "level": "beginner",
            "title": "Body Language Basics for Interviews",
            "url": "https://www.youtube.com/watch?v=example1",
            "provider": "YouTube",
            "tags": ["posture", "eye-contact", "gestures"],
            "ranking_weight": 1.5
        },
        {
            "category": "body_language",
            "type": "course",
            "level": "beginner",
            "title": "Introduction to Professional Body Language",
            "url": "https://www.coursera.org/learn/body-language-basics",
            "provider": "Coursera",
            "tags": ["professional", "workplace", "communication"],
            "ranking_weight": 1.8
        },
        {
            "category": "body_language",
            "type": "video",
            "level": "beginner",
            "title": "How to Sit Properly in an Interview",
            "url": "https://www.youtube.com/watch?v=example2",
            "provider": "YouTube",
            "tags": ["posture", "sitting", "confidence"],
            "ranking_weight": 1.2
        },
        {
            "category": "body_language",
            "type": "course",
            "level": "beginner",
            "title": "Confident Body Language for Job Seekers",
            "url": "https://www.udemy.com/course/body-language-confidence",
            "provider": "Udemy",
            "tags": ["confidence", "job-interview", "first-impression"],
            "ranking_weight": 1.4
        },
        {
            "category": "body_language",
            "type": "video",
            "level": "beginner",
            "title": "Eye Contact Techniques for Interviews",
            "url": "https://www.youtube.com/watch?v=example3",
            "provider": "YouTube",
            "tags": ["eye-contact", "engagement", "connection"],
            "ranking_weight": 1.3
        },
        
        # Body Language - Intermediate
        {
            "category": "body_language",
            "type": "video",
            "level": "intermediate",
            "title": "Advanced Body Language for Leadership Roles",
            "url": "https://www.youtube.com/watch?v=example4",
            "provider": "YouTube",
            "tags": ["leadership", "executive", "presence"],
            "ranking_weight": 1.6
        },
        {
            "category": "body_language",
            "type": "course",
            "level": "intermediate",
            "title": "Mastering Non-Verbal Communication",
            "url": "https://www.linkedin.com/learning/nonverbal-communication",
            "provider": "LinkedIn Learning",
            "tags": ["non-verbal", "advanced", "professional"],
            "ranking_weight": 1.9
        },
        {
            "category": "body_language",
            "type": "video",
            "level": "intermediate",
            "title": "Reading and Projecting Confidence",
            "url": "https://www.youtube.com/watch?v=example5",
            "provider": "YouTube",
            "tags": ["confidence", "projection", "reading-others"],
            "ranking_weight": 1.4
        },
        {
            "category": "body_language",
            "type": "course",
            "level": "intermediate",
            "title": "Body Language in Virtual Interviews",
            "url": "https://www.skillshare.com/classes/virtual-interview-body-language",
            "provider": "Skillshare",
            "tags": ["virtual", "remote", "video-calls"],
            "ranking_weight": 1.7
        },
        {
            "category": "body_language",
            "type": "video",
            "level": "intermediate",
            "title": "Cultural Awareness in Body Language",
            "url": "https://www.youtube.com/watch?v=example6",
            "provider": "YouTube",
            "tags": ["cultural", "diversity", "international"],
            "ranking_weight": 1.3
        },
        
        # Body Language - Advanced
        {
            "category": "body_language",
            "type": "video",
            "level": "advanced",
            "title": "Executive Presence and Body Language",
            "url": "https://www.youtube.com/watch?v=example7",
            "provider": "YouTube",
            "tags": ["executive", "leadership", "presence"],
            "ranking_weight": 1.8
        },
        {
            "category": "body_language",
            "type": "course",
            "level": "advanced",
            "title": "Psychology of Body Language in Business",
            "url": "https://www.masterclass.com/classes/body-language-psychology",
            "provider": "MasterClass",
            "tags": ["psychology", "business", "advanced"],
            "ranking_weight": 2.0
        },
        {
            "category": "body_language",
            "type": "video",
            "level": "advanced",
            "title": "Micro-expressions in Professional Settings",
            "url": "https://www.youtube.com/watch?v=example8",
            "provider": "YouTube",
            "tags": ["micro-expressions", "psychology", "advanced"],
            "ranking_weight": 1.7
        },
        {
            "category": "body_language",
            "type": "course",
            "level": "advanced",
            "title": "Advanced Non-Verbal Leadership Communication",
            "url": "https://www.edx.org/course/advanced-nonverbal-leadership",
            "provider": "edX",
            "tags": ["leadership", "advanced", "communication"],
            "ranking_weight": 1.9
        },
        {
            "category": "body_language",
            "type": "video",
            "level": "advanced",
            "title": "Body Language for C-Suite Executives",
            "url": "https://www.youtube.com/watch?v=example9",
            "provider": "YouTube",
            "tags": ["c-suite", "executive", "high-level"],
            "ranking_weight": 1.6
        },
        
        # Voice Analysis - Beginner
        {
            "category": "voice_analysis",
            "type": "video",
            "level": "beginner",
            "title": "Voice Training for Interviews",
            "url": "https://www.youtube.com/watch?v=voice1",
            "provider": "YouTube",
            "tags": ["voice", "training", "clarity"],
            "ranking_weight": 1.4
        },
        {
            "category": "voice_analysis",
            "type": "course",
            "level": "beginner",
            "title": "Speaking with Confidence",
            "url": "https://www.coursera.org/learn/confident-speaking",
            "provider": "Coursera",
            "tags": ["confidence", "speaking", "public-speaking"],
            "ranking_weight": 1.7
        },
        {
            "category": "voice_analysis",
            "type": "video",
            "level": "beginner",
            "title": "Breathing Techniques for Better Speech",
            "url": "https://www.youtube.com/watch?v=voice2",
            "provider": "YouTube",
            "tags": ["breathing", "speech", "techniques"],
            "ranking_weight": 1.3
        },
        {
            "category": "voice_analysis",
            "type": "course",
            "level": "beginner",
            "title": "Clear Communication Fundamentals",
            "url": "https://www.udemy.com/course/clear-communication",
            "provider": "Udemy",
            "tags": ["communication", "clarity", "fundamentals"],
            "ranking_weight": 1.5
        },
        {
            "category": "voice_analysis",
            "type": "video",
            "level": "beginner",
            "title": "Overcoming Interview Nervousness",
            "url": "https://www.youtube.com/watch?v=voice3",
            "provider": "YouTube",
            "tags": ["nervousness", "anxiety", "calm"],
            "ranking_weight": 1.6
        }
        # Continue with more categories and levels...
    ]
    
    # Add more resources for voice_analysis intermediate/advanced and content_quality, overall categories
    # This is a sample - in production you'd have the full 60+ resources
    
    created_count = 0
    for resource_data in resources_data:
        try:
            # Check if resource already exists
            existing = db.query(LearningResource).filter(
                and_(
                    LearningResource.title == resource_data["title"],
                    LearningResource.url == resource_data["url"]
                )
            ).first()
            
            if not existing:
                db_resource = LearningResource(**resource_data)
                db.add(db_resource)
                created_count += 1
        except Exception as e:
            print(f"Error creating resource {resource_data['title']}: {str(e)}")
            continue
    
    try:
        db.commit()
        print(f"Successfully seeded {created_count} learning resources")
        return created_count
    except Exception as e:
        db.rollback()
        print(f"Error committing seeded resources: {str(e)}")
        return 0