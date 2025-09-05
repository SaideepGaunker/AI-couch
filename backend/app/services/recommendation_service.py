"""
Recommendation Service - Business logic for learning resource recommendations
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from random import shuffle

from app.db.models import LearningResource, UserRecommendation, User
from app.schemas.recommendation import (
    RecommendationRequest, RecommendationResponse, RecommendationsResponse,
    LearningResourceResponse, ResourceCategory, ResourceType, ResourceLevel,
    FeedbackType
)

logger = logging.getLogger(__name__)


class RecommendationService:
    """Service for managing learning resource recommendations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def map_score_to_level(self, score: float) -> str:
        """Map performance score to learning level"""
        if score < 40:
            return ResourceLevel.BEGINNER.value
        elif score < 70:
            return ResourceLevel.INTERMEDIATE.value
        else:
            return ResourceLevel.ADVANCED.value
    
    def get_recommendations(self, user_id: int, scores: RecommendationRequest) -> RecommendationsResponse:
        """
        Get personalized recommendations based on performance scores
        Returns 1 video + 1 course per category, avoiding recent repetitions
        """
        try:
            logger.info(f"Generating recommendations for user {user_id}")
            
            # Map scores to levels
            score_mapping = {
                ResourceCategory.BODY_LANGUAGE.value: self.map_score_to_level(scores.body_language),
                ResourceCategory.VOICE_ANALYSIS.value: self.map_score_to_level(scores.voice_analysis),
                ResourceCategory.CONTENT_QUALITY.value: self.map_score_to_level(scores.content_quality),
                ResourceCategory.OVERALL.value: self.map_score_to_level(scores.overall)
            }
            
            logger.info(f"Score mapping: {score_mapping}")
            
            # Get recently recommended resources to avoid repetition
            recent_cutoff = datetime.utcnow() - timedelta(days=7)
            recent_recommendations = self.db.query(UserRecommendation.resource_id).filter(
                and_(
                    UserRecommendation.user_id == user_id,
                    UserRecommendation.recommended_at >= recent_cutoff
                )
            ).subquery()
            
            recommendations = {}
            
            for category, level in score_mapping.items():
                logger.info(f"Getting recommendations for {category} at {level} level")
                
                # Get video recommendation
                video = self._get_resource_recommendation(
                    category=category,
                    level=level,
                    resource_type=ResourceType.VIDEO.value,
                    exclude_ids=recent_recommendations,
                    user_id=user_id
                )
                
                # Get course recommendation
                course = self._get_resource_recommendation(
                    category=category,
                    level=level,
                    resource_type=ResourceType.COURSE.value,
                    exclude_ids=recent_recommendations,
                    user_id=user_id
                )
                
                recommendations[category] = RecommendationResponse(
                    category=category,
                    level=level,
                    video=video,
                    course=course
                )
                
                # Track these recommendations
                if video:
                    self._track_recommendation(user_id, video.id)
                if course:
                    self._track_recommendation(user_id, course.id)
            
            return RecommendationsResponse(
                body_language=recommendations[ResourceCategory.BODY_LANGUAGE.value],
                voice_analysis=recommendations[ResourceCategory.VOICE_ANALYSIS.value],
                content_quality=recommendations[ResourceCategory.CONTENT_QUALITY.value],
                overall=recommendations[ResourceCategory.OVERALL.value],
                generated_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            # Return fallback recommendations instead of raising
            return self._get_fallback_recommendations()
    
    def _get_resource_recommendation(
        self, 
        category: str, 
        level: str, 
        resource_type: str,
        exclude_ids,
        user_id: int
    ) -> Optional[LearningResourceResponse]:
        """Get a single resource recommendation with ranking and anti-repetition logic"""
        
        try:
            # Query for resources, excluding recently recommended ones
            query = self.db.query(LearningResource).filter(
                and_(
                    LearningResource.category == category,
                    LearningResource.level == level,
                    LearningResource.type == resource_type,
                    ~LearningResource.id.in_(exclude_ids)
                )
            ).order_by(LearningResource.ranking_weight.desc())
            
            resources = query.all()
            
            if not resources:
                # Fallback: get any resource of this type/category if no non-recent ones available
                logger.warning(f"No non-recent resources found for {category}/{level}/{resource_type}, using fallback")
                resources = self.db.query(LearningResource).filter(
                    and_(
                        LearningResource.category == category,
                        LearningResource.level == level,
                        LearningResource.type == resource_type
                    )
                ).order_by(LearningResource.ranking_weight.desc()).limit(5).all()
            
            if not resources:
                logger.warning(f"No resources found for {category}/{level}/{resource_type}")
                return None
            
            # Apply weighted random selection based on ranking_weight
            # Higher weight = higher probability of selection
            weights = [r.ranking_weight for r in resources]
            total_weight = sum(weights)
            
            if total_weight == 0:
                # If all weights are 0, use uniform selection
                selected_resource = resources[0]
            else:
                # Weighted random selection
                import random
                rand_val = random.uniform(0, total_weight)
                cumulative_weight = 0
                selected_resource = resources[0]  # fallback
                
                for resource in resources:
                    cumulative_weight += resource.ranking_weight
                    if rand_val <= cumulative_weight:
                        selected_resource = resource
                        break
            
            return LearningResourceResponse.model_validate(selected_resource)
            
        except Exception as e:
            logger.error(f"Error getting resource recommendation: {str(e)}")
            return None
    
    def _track_recommendation(self, user_id: int, resource_id: int):
        """Track that a recommendation was made to avoid repetition"""
        try:
            recommendation = UserRecommendation(
                user_id=user_id,
                resource_id=resource_id,
                clicked=False,
                user_feedback="neutral"
            )
            
            self.db.add(recommendation)
            self.db.commit()
            
            logger.info(f"Tracked recommendation: user {user_id}, resource {resource_id}")
            
        except Exception as e:
            logger.error(f"Error tracking recommendation: {str(e)}")
            self.db.rollback()
    
    def track_click(self, user_id: int, resource_id: int) -> bool:
        """Track when user clicks on a recommendation"""
        try:
            # Find the most recent recommendation for this user/resource
            recommendation = self.db.query(UserRecommendation).filter(
                and_(
                    UserRecommendation.user_id == user_id,
                    UserRecommendation.resource_id == resource_id
                )
            ).order_by(UserRecommendation.recommended_at.desc()).first()
            
            if recommendation:
                recommendation.clicked = True
                self.db.commit()
                logger.info(f"Tracked click: user {user_id}, resource {resource_id}")
                return True
            else:
                logger.warning(f"No recommendation found to track click: user {user_id}, resource {resource_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error tracking click: {str(e)}")
            self.db.rollback()
            return False
    
    def submit_feedback(self, user_id: int, resource_id: int, feedback: FeedbackType) -> bool:
        """Submit user feedback for a recommendation"""
        try:
            # Find the most recent recommendation for this user/resource
            recommendation = self.db.query(UserRecommendation).filter(
                and_(
                    UserRecommendation.user_id == user_id,
                    UserRecommendation.resource_id == resource_id
                )
            ).order_by(UserRecommendation.recommended_at.desc()).first()
            
            if recommendation:
                recommendation.user_feedback = feedback.value
                recommendation.feedback_at = datetime.utcnow()
                self.db.commit()
                logger.info(f"Submitted feedback: user {user_id}, resource {resource_id}, feedback {feedback.value}")
                return True
            else:
                logger.warning(f"No recommendation found for feedback: user {user_id}, resource {resource_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error submitting feedback: {str(e)}")
            self.db.rollback()
            return False
    
    def get_user_recommendation_history(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's recommendation history with feedback"""
        try:
            recommendations = self.db.query(UserRecommendation).filter(
                UserRecommendation.user_id == user_id
            ).order_by(UserRecommendation.recommended_at.desc()).limit(limit).all()
            
            history = []
            for rec in recommendations:
                history.append({
                    "resource_id": rec.resource_id,
                    "resource_title": rec.resource.title if rec.resource else "Unknown",
                    "category": rec.resource.category if rec.resource else "Unknown",
                    "recommended_at": rec.recommended_at,
                    "clicked": rec.clicked,
                    "user_feedback": rec.user_feedback,
                    "feedback_at": rec.feedback_at
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting recommendation history: {str(e)}")
            return []
    
    def _get_fallback_recommendations(self) -> RecommendationsResponse:
        """Get fallback recommendations when database resources are not available"""
        from app.schemas.recommendation import RecommendationResponse, LearningResourceResponse
        
        # Create fallback learning resources
        fallback_video = LearningResourceResponse(
            id=999,
            title="Interview Skills Masterclass",
            description="Comprehensive guide to interview preparation and techniques",
            url="https://example.com/interview-skills",
            provider="Internal",
            type="video",
            duration=30,
            difficulty="intermediate",
            category="overall",
            level="intermediate",
            ranking_weight=100
        )
        
        fallback_course = LearningResourceResponse(
            id=998,
            title="Behavioral Interview Preparation",
            description="Learn the STAR method and practice common behavioral questions",
            url="https://example.com/behavioral-interviews",
            provider="Internal", 
            type="course",
            duration=60,
            difficulty="beginner",
            category="content_quality",
            level="beginner",
            ranking_weight=90
        )
        
        # Create fallback recommendations
        body_language_rec = RecommendationResponse(
            category="body_language",
            level="intermediate",
            video=fallback_video,
            course=fallback_course
        )
        
        voice_analysis_rec = RecommendationResponse(
            category="voice_analysis", 
            level="intermediate",
            video=fallback_video,
            course=fallback_course
        )
        
        content_quality_rec = RecommendationResponse(
            category="content_quality",
            level="beginner", 
            video=fallback_video,
            course=fallback_course
        )
        
        overall_rec = RecommendationResponse(
            category="overall",
            level="intermediate",
            video=fallback_video,
            course=fallback_course
        )
        
        return RecommendationsResponse(
            body_language=body_language_rec,
            voice_analysis=voice_analysis_rec,
            content_quality=content_quality_rec,
            overall=overall_rec,
            generated_at=datetime.utcnow()
        )