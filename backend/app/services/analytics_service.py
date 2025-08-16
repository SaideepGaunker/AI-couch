"""
Analytics Service for user progress tracking and system analytics
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from app.db.models import (
    User, InterviewSession, PerformanceMetrics, UserProgress, 
    Question, Institution
)


class AnalyticsService:
    """Service for analytics and progress tracking"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_progress(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user progress data"""
        
        # Basic session statistics
        total_sessions = self.db.query(InterviewSession).filter(
            InterviewSession.user_id == user_id
        ).count()
        
        completed_sessions = self.db.query(InterviewSession).filter(
            and_(
                InterviewSession.user_id == user_id,
                InterviewSession.status == "completed"
            )
        ).count()
        
        # Average scores
        avg_scores = self.db.query(
            func.avg(PerformanceMetrics.content_quality_score).label('content'),
            func.avg(PerformanceMetrics.body_language_score).label('body_language'),
            func.avg(PerformanceMetrics.tone_confidence_score).label('tone')
        ).join(InterviewSession).filter(
            InterviewSession.user_id == user_id
        ).first()
        
        # Overall score from sessions
        overall_score = self.db.query(
            func.avg(InterviewSession.overall_score)
        ).filter(
            and_(
                InterviewSession.user_id == user_id,
                InterviewSession.status == "completed"
            )
        ).scalar() or 0
        
        # Improvement rate (last 5 sessions vs previous 5)
        improvement_rate = self._calculate_improvement_rate(user_id)
        
        # Recent recommendations
        recommendations = self.get_personalized_recommendations(user_id)
        
        return {
            "overall_score": round(float(overall_score), 1),
            "sessions_completed": completed_sessions,
            "total_sessions": total_sessions,
            "completion_rate": (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0,
            "improvement_rate": improvement_rate,
            "skill_breakdown": {
                "content_quality": round(float(avg_scores.content or 0), 1),
                "body_language": round(float(avg_scores.body_language or 0), 1),
                "tone_confidence": round(float(avg_scores.tone or 0), 1)
            },
            "recommendations": recommendations[:5],  # Top 5 recommendations
            "days_active": self._get_days_active(user_id)
        }
    
    def get_user_session_analytics(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's session history with analytics"""
        
        sessions = self.db.query(InterviewSession).filter(
            InterviewSession.user_id == user_id
        ).order_by(desc(InterviewSession.created_at)).limit(limit).all()
        
        session_analytics = []
        for session in sessions:
            # Get performance metrics for this session
            metrics = self.db.query(PerformanceMetrics).filter(
                PerformanceMetrics.session_id == session.id
            ).all()
            
            questions_answered = len(metrics)
            avg_response_time = sum(m.response_time for m in metrics) / len(metrics) if metrics else 0
            
            session_analytics.append({
                "id": session.id,
                "created_at": session.created_at.isoformat(),
                "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                "session_type": session.session_type,
                "target_role": session.target_role,
                "duration": session.duration,
                "status": session.status,
                "overall_score": session.overall_score,
                "questions_answered": questions_answered,
                "avg_response_time": round(avg_response_time, 1)
            })
        
        return session_analytics
    
    def get_user_trends(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get user's performance trends over time"""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Daily session data
        daily_sessions = self.db.query(
            func.date(InterviewSession.created_at).label('date'),
            func.count(InterviewSession.id).label('session_count'),
            func.avg(InterviewSession.overall_score).label('avg_score')
        ).filter(
            and_(
                InterviewSession.user_id == user_id,
                InterviewSession.created_at >= start_date,
                InterviewSession.status == "completed"
            )
        ).group_by(
            func.date(InterviewSession.created_at)
        ).order_by('date').all()
        
        # Skill progression
        skill_progression = self.db.query(
            func.date(PerformanceMetrics.created_at).label('date'),
            func.avg(PerformanceMetrics.content_quality_score).label('content'),
            func.avg(PerformanceMetrics.body_language_score).label('body_language'),
            func.avg(PerformanceMetrics.tone_confidence_score).label('tone')
        ).join(InterviewSession).filter(
            and_(
                InterviewSession.user_id == user_id,
                PerformanceMetrics.created_at >= start_date
            )
        ).group_by(
            func.date(PerformanceMetrics.created_at)
        ).order_by('date').all()
        
        return {
            "daily_sessions": [
                {
                    "date": session.date.isoformat(),
                    "session_count": session.session_count,
                    "avg_score": round(float(session.avg_score or 0), 1)
                }
                for session in daily_sessions
            ],
            "skill_progression": [
                {
                    "date": skill.date.isoformat(),
                    "content_quality": round(float(skill.content or 0), 1),
                    "body_language": round(float(skill.body_language or 0), 1),
                    "tone_confidence": round(float(skill.tone or 0), 1)
                }
                for skill in skill_progression
            ]
        }
    
    def get_dashboard_data(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        
        progress_data = self.get_user_progress(user_id)
        recent_sessions = self.get_user_session_analytics(user_id, 5)
        
        # Recent achievements
        achievements = self._get_user_achievements(user_id)
        
        # Next recommended actions
        next_actions = self._get_next_actions(user_id)
        
        return {
            "progress": progress_data,
            "recent_sessions": recent_sessions,
            "achievements": achievements,
            "next_actions": next_actions
        }
    
    def get_personalized_recommendations(self, user_id: int) -> List[str]:
        """Generate personalized recommendations for user improvement"""
        
        recommendations = []
        
        # Get user's recent performance
        recent_metrics = self.db.query(PerformanceMetrics).join(InterviewSession).filter(
            InterviewSession.user_id == user_id
        ).order_by(desc(PerformanceMetrics.created_at)).limit(10).all()
        
        if not recent_metrics:
            return ["Complete your first interview session to get personalized recommendations"]
        
        # Analyze weak areas
        avg_content = sum(m.content_quality_score for m in recent_metrics) / len(recent_metrics)
        avg_body_language = sum(m.body_language_score or 0 for m in recent_metrics) / len(recent_metrics)
        avg_tone = sum(m.tone_confidence_score or 0 for m in recent_metrics) / len(recent_metrics)
        
        if avg_content < 70:
            recommendations.append("Focus on improving answer quality with specific examples and structured responses")
        
        if avg_body_language < 70:
            recommendations.append("Practice maintaining good posture and eye contact during interviews")
        
        if avg_tone < 70:
            recommendations.append("Work on speaking with more confidence and clarity")
        
        # Session frequency recommendations
        recent_session_count = self.db.query(InterviewSession).filter(
            and_(
                InterviewSession.user_id == user_id,
                InterviewSession.created_at >= datetime.utcnow() - timedelta(days=7)
            )
        ).count()
        
        if recent_session_count < 2:
            recommendations.append("Try to practice at least 2-3 times per week for consistent improvement")
        
        # Question type recommendations
        question_type_performance = self.db.query(
            Question.question_type,
            func.avg(PerformanceMetrics.content_quality_score).label('avg_score')
        ).join(PerformanceMetrics).join(InterviewSession).filter(
            InterviewSession.user_id == user_id
        ).group_by(Question.question_type).all()
        
        for qtype, avg_score in question_type_performance:
            if avg_score < 65:
                recommendations.append(f"Practice more {qtype} questions to improve in this area")
        
        return recommendations[:10]  # Return top 10 recommendations
    
    def get_system_overview(self) -> Dict[str, Any]:
        """Get system-wide analytics overview (admin only)"""
        
        # Total users and sessions
        total_users = self.db.query(User).count()
        total_sessions = self.db.query(InterviewSession).count()
        completed_sessions = self.db.query(InterviewSession).filter(
            InterviewSession.status == "completed"
        ).count()
        
        # Active users (last 30 days)
        active_users = self.db.query(User).join(InterviewSession).filter(
            InterviewSession.created_at >= datetime.utcnow() - timedelta(days=30)
        ).distinct().count()
        
        # Average system performance
        system_avg_score = self.db.query(
            func.avg(InterviewSession.overall_score)
        ).filter(InterviewSession.status == "completed").scalar() or 0
        
        # Popular question types
        popular_questions = self.db.query(
            Question.question_type,
            func.count(PerformanceMetrics.id).label('usage_count')
        ).join(PerformanceMetrics).group_by(
            Question.question_type
        ).order_by(desc('usage_count')).limit(5).all()
        
        return {
            "total_users": total_users,
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "completion_rate": (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0,
            "active_users_30d": active_users,
            "system_avg_score": round(float(system_avg_score), 1),
            "popular_question_types": [
                {"type": q.question_type, "usage_count": q.usage_count}
                for q in popular_questions
            ]
        }
    
    def _calculate_improvement_rate(self, user_id: int) -> float:
        """Calculate user's improvement rate"""
        
        # Get last 10 completed sessions
        recent_sessions = self.db.query(InterviewSession).filter(
            and_(
                InterviewSession.user_id == user_id,
                InterviewSession.status == "completed"
            )
        ).order_by(desc(InterviewSession.created_at)).limit(10).all()
        
        if len(recent_sessions) < 4:
            return 0.0
        
        # Compare first half vs second half
        mid_point = len(recent_sessions) // 2
        recent_half = recent_sessions[:mid_point]
        older_half = recent_sessions[mid_point:]
        
        recent_avg = sum(s.overall_score for s in recent_half) / len(recent_half)
        older_avg = sum(s.overall_score for s in older_half) / len(older_half)
        
        if older_avg == 0:
            return 0.0
        
        improvement_rate = ((recent_avg - older_avg) / older_avg) * 100
        return round(improvement_rate, 1)
    
    def _get_days_active(self, user_id: int) -> int:
        """Get number of days user has been active"""
        
        first_session = self.db.query(InterviewSession).filter(
            InterviewSession.user_id == user_id
        ).order_by(InterviewSession.created_at).first()
        
        if not first_session:
            return 0
        
        days_active = (datetime.utcnow() - first_session.created_at).days
        return max(1, days_active)  # At least 1 day
    
    def _get_user_achievements(self, user_id: int) -> List[Dict[str, Any]]:
        """Get user achievements and milestones"""
        
        achievements = []
        
        # Session count achievements
        session_count = self.db.query(InterviewSession).filter(
            InterviewSession.user_id == user_id
        ).count()
        
        if session_count >= 1:
            achievements.append({"title": "First Steps", "description": "Completed your first interview session"})
        if session_count >= 10:
            achievements.append({"title": "Dedicated Learner", "description": "Completed 10 interview sessions"})
        if session_count >= 50:
            achievements.append({"title": "Interview Master", "description": "Completed 50 interview sessions"})
        
        # Score achievements
        best_score = self.db.query(
            func.max(InterviewSession.overall_score)
        ).filter(
            and_(
                InterviewSession.user_id == user_id,
                InterviewSession.status == "completed"
            )
        ).scalar() or 0
        
        if best_score >= 80:
            achievements.append({"title": "High Achiever", "description": "Scored 80+ in an interview session"})
        if best_score >= 90:
            achievements.append({"title": "Excellence", "description": "Scored 90+ in an interview session"})
        
        return achievements[-5:]  # Return last 5 achievements
    
    def _get_next_actions(self, user_id: int) -> List[str]:
        """Get recommended next actions for user"""
        
        actions = []
        
        # Check last session date
        last_session = self.db.query(InterviewSession).filter(
            InterviewSession.user_id == user_id
        ).order_by(desc(InterviewSession.created_at)).first()
        
        if not last_session:
            actions.append("Start your first interview practice session")
        elif (datetime.utcnow() - last_session.created_at).days > 7:
            actions.append("It's been a while - start a new practice session")
        else:
            actions.append("Continue your regular practice routine")
        
        # Check for incomplete sessions
        incomplete_sessions = self.db.query(InterviewSession).filter(
            and_(
                InterviewSession.user_id == user_id,
                InterviewSession.status.in_(["active", "paused"])
            )
        ).count()
        
        if incomplete_sessions > 0:
            actions.append("Complete your paused interview session")
        
        return actions[:3]  # Return top 3 actions