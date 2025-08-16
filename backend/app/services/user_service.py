"""
User Service - Business logic for user profile management
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.crud.user import (
    get_user, get_users, update_user, delete_user,
    authenticate_user, change_user_password
)
from app.schemas.user import UserUpdate
from app.db.models import User, InterviewSession, PerformanceMetrics, UserProgress
from app.core.security import verify_password


class UserService:
    """User management service with GDPR compliance"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return get_user(self.db, user_id)
    
    def update_user_profile(self, user_id: int, profile_update: UserUpdate) -> Optional[User]:
        """Update user profile information"""
        return update_user(self.db, user_id, profile_update)
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """Change user password with verification"""
        user = get_user(self.db, user_id)
        if not user:
            return False
        
        # Verify old password
        if not verify_password(old_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        return change_user_password(self.db, user_id, new_password)
    
    def delete_user_data(self, user_id: int) -> bool:
        """Delete user data (GDPR compliance - soft delete)"""
        user = get_user(self.db, user_id)
        if not user:
            return False
        
        # Anonymize user data instead of hard delete
        user.email = f"deleted_user_{user_id}@deleted.com"
        user.name = "Deleted User"
        user.is_active = False
        user.target_roles = []
        user.experience_level = None
        
        # Keep interview data for analytics but anonymize
        sessions = self.db.query(InterviewSession).filter(
            InterviewSession.user_id == user_id
        ).all()
        
        for session in sessions:
            # Keep session data but mark as anonymized
            session.target_role = "anonymized"
        
        self.db.commit()
        return True
    
    def export_user_data(self, user_id: int) -> Dict[str, Any]:
        """Export all user data (GDPR compliance)"""
        user = get_user(self.db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get all user-related data
        sessions = self.db.query(InterviewSession).filter(
            InterviewSession.user_id == user_id
        ).all()
        
        performance_data = self.db.query(PerformanceMetrics).join(
            InterviewSession
        ).filter(InterviewSession.user_id == user_id).all()
        
        progress_data = self.db.query(UserProgress).filter(
            UserProgress.user_id == user_id
        ).all()
        
        return {
            "user_profile": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "target_roles": user.target_roles,
                "experience_level": user.experience_level,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None
            },
            "interview_sessions": [
                {
                    "id": session.id,
                    "session_type": session.session_type,
                    "target_role": session.target_role,
                    "duration": session.duration,
                    "overall_score": session.overall_score,
                    "created_at": session.created_at.isoformat(),
                    "completed_at": session.completed_at.isoformat() if session.completed_at else None
                }
                for session in sessions
            ],
            "performance_metrics": [
                {
                    "session_id": metric.session_id,
                    "question_id": metric.question_id,
                    "body_language_score": metric.body_language_score,
                    "tone_confidence_score": metric.tone_confidence_score,
                    "content_quality_score": metric.content_quality_score,
                    "response_time": metric.response_time,
                    "created_at": metric.created_at.isoformat()
                }
                for metric in performance_data
            ],
            "progress_tracking": [
                {
                    "metric_type": progress.metric_type,
                    "score": progress.score,
                    "session_date": progress.session_date.isoformat(),
                    "improvement_trend": progress.improvement_trend
                }
                for progress in progress_data
            ]
        }
    
    def update_user_settings(self, user_id: int, settings_data: Dict[str, Any]) -> bool:
        """Update user settings and preferences"""
        user = get_user(self.db, user_id)
        if not user:
            return False
        
        # Update allowed settings
        if "target_roles" in settings_data:
            user.target_roles = settings_data["target_roles"]
        
        if "experience_level" in settings_data:
            user.experience_level = settings_data["experience_level"]
        
        # Store additional settings in a separate table or JSON field
        # For now, we'll just update the basic user fields
        
        self.db.commit()
        return True
    
    def get_users_list(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[str] = None,
        institution_id: Optional[int] = None
    ) -> List[User]:
        """Get list of users with filtering (admin only)"""
        query = self.db.query(User)
        
        if role:
            query = query.filter(User.role == role)
        
        if institution_id:
            query = query.filter(User.institution_id == institution_id)
        
        return query.offset(skip).limit(limit).all()
    
    def activate_user(self, user_id: int) -> bool:
        """Activate user account (admin only)"""
        user = get_user(self.db, user_id)
        if not user:
            return False
        
        user.is_active = True
        self.db.commit()
        return True
    
    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate user account (admin only)"""
        user = get_user(self.db, user_id)
        if not user:
            return False
        
        user.is_active = False
        self.db.commit()
        return True
    
    def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get user statistics and analytics"""
        user = get_user(self.db, user_id)
        if not user:
            return {}
        
        # Count sessions
        total_sessions = self.db.query(InterviewSession).filter(
            InterviewSession.user_id == user_id
        ).count()
        
        completed_sessions = self.db.query(InterviewSession).filter(
            InterviewSession.user_id == user_id,
            InterviewSession.status == "completed"
        ).count()
        
        # Average scores
        avg_scores = self.db.query(
            self.db.func.avg(PerformanceMetrics.body_language_score).label('avg_body_language'),
            self.db.func.avg(PerformanceMetrics.tone_confidence_score).label('avg_tone'),
            self.db.func.avg(PerformanceMetrics.content_quality_score).label('avg_content')
        ).join(InterviewSession).filter(
            InterviewSession.user_id == user_id
        ).first()
        
        return {
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "completion_rate": (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0,
            "average_scores": {
                "body_language": float(avg_scores.avg_body_language or 0),
                "tone_confidence": float(avg_scores.avg_tone or 0),
                "content_quality": float(avg_scores.avg_content or 0)
            }
        }
    
    def get_user_progress_trends(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get user progress trends over time"""
        from datetime import datetime, timedelta
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        progress_data = self.db.query(UserProgress).filter(
            UserProgress.user_id == user_id,
            UserProgress.session_date >= start_date
        ).order_by(UserProgress.session_date).all()
        
        # Group by metric type
        trends = {}
        for progress in progress_data:
            if progress.metric_type not in trends:
                trends[progress.metric_type] = []
            
            trends[progress.metric_type].append({
                "date": progress.session_date.isoformat(),
                "score": progress.score,
                "trend": progress.improvement_trend
            })
        
        return trends