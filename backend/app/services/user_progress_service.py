"""
Enhanced User Progress Service for performance tracking and recommendations
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from app.db.models import User, UserProgress, InterviewSession, PerformanceMetrics


class UserProgressService:
    """Service for enhanced user progress tracking and recommendations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_progress_record(
        self,
        user_id: int,
        metric_type: str,
        score: float,
        session_date: datetime = None,
        improvement_trend: float = 0.0
    ) -> UserProgress:
        """Create a new user progress record"""
        
        if session_date is None:
            session_date = datetime.utcnow()
        
        progress = UserProgress(
            user_id=user_id,
            metric_type=metric_type,
            score=score,
            session_date=session_date,
            improvement_trend=improvement_trend,
            recommendations=[],
            improvement_areas=[],
            learning_suggestions=[]
        )
        
        self.db.add(progress)
        self.db.commit()
        self.db.refresh(progress)
        
        return progress
    
    def add_recommendations_to_progress(
        self,
        progress_id: int,
        recommendations: List[Dict[str, Any]]
    ) -> UserProgress:
        """Add recommendations to a progress record"""
        
        progress = self.db.query(UserProgress).filter(
            UserProgress.id == progress_id
        ).first()
        
        if not progress:
            raise ValueError(f"Progress record with id {progress_id} not found")
        
        if not progress.recommendations:
            progress.recommendations = []
        
        for rec in recommendations:
            recommendation = {
                "category": rec.get("category"),
                "resource_type": rec.get("resource_type"),
                "title": rec.get("title"),
                "url": rec.get("url"),
                "priority": rec.get("priority", "medium"),
                "added_at": datetime.utcnow().isoformat()
            }
            progress.recommendations.append(recommendation)
        
        self.db.commit()
        return progress
    
    def add_improvement_areas_to_progress(
        self,
        progress_id: int,
        improvement_areas: List[Dict[str, Any]]
    ) -> UserProgress:
        """Add improvement areas to a progress record"""
        
        progress = self.db.query(UserProgress).filter(
            UserProgress.id == progress_id
        ).first()
        
        if not progress:
            raise ValueError(f"Progress record with id {progress_id} not found")
        
        if not progress.improvement_areas:
            progress.improvement_areas = []
        
        for area in improvement_areas:
            improvement_area = {
                "area": area.get("area"),
                "priority": area.get("priority"),
                "suggestions": area.get("suggestions", []),
                "added_at": datetime.utcnow().isoformat()
            }
            progress.improvement_areas.append(improvement_area)
        
        self.db.commit()
        return progress
    
    def add_learning_suggestions_to_progress(
        self,
        progress_id: int,
        learning_suggestions: List[Dict[str, Any]]
    ) -> UserProgress:
        """Add learning suggestions to a progress record"""
        
        progress = self.db.query(UserProgress).filter(
            UserProgress.id == progress_id
        ).first()
        
        if not progress:
            raise ValueError(f"Progress record with id {progress_id} not found")
        
        if not progress.learning_suggestions:
            progress.learning_suggestions = []
        
        for suggestion in learning_suggestions:
            learning_suggestion = {
                "suggestion": suggestion.get("suggestion"),
                "category": suggestion.get("category"),
                "difficulty": suggestion.get("difficulty", "intermediate"),
                "added_at": datetime.utcnow().isoformat()
            }
            progress.learning_suggestions.append(learning_suggestion)
        
        self.db.commit()
        return progress
    
    def get_user_progress_summary(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive user progress summary with recommendations"""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get progress records for the period
        progress_records = self.db.query(UserProgress).filter(
            and_(
                UserProgress.user_id == user_id,
                UserProgress.session_date >= start_date
            )
        ).order_by(desc(UserProgress.session_date)).all()
        
        if not progress_records:
            return {
                "user_id": user_id,
                "period_days": days,
                "total_records": 0,
                "average_scores": {},
                "improvement_trends": {},
                "recommendations": [],
                "improvement_areas": [],
                "learning_suggestions": []
            }
        
        # Calculate average scores by metric type
        metric_scores = {}
        metric_trends = {}
        
        for record in progress_records:
            if record.metric_type not in metric_scores:
                metric_scores[record.metric_type] = []
                metric_trends[record.metric_type] = []
            
            metric_scores[record.metric_type].append(record.score)
            metric_trends[record.metric_type].append(record.improvement_trend)
        
        average_scores = {
            metric: sum(scores) / len(scores)
            for metric, scores in metric_scores.items()
        }
        
        average_trends = {
            metric: sum(trends) / len(trends)
            for metric, trends in metric_trends.items()
        }
        
        # Aggregate recommendations, improvement areas, and learning suggestions
        all_recommendations = []
        all_improvement_areas = []
        all_learning_suggestions = []
        
        for record in progress_records:
            if record.recommendations:
                all_recommendations.extend(record.recommendations)
            if record.improvement_areas:
                all_improvement_areas.extend(record.improvement_areas)
            if record.learning_suggestions:
                all_learning_suggestions.extend(record.learning_suggestions)
        
        # Remove duplicates and sort by priority/date
        unique_recommendations = self._deduplicate_recommendations(all_recommendations)
        unique_improvement_areas = self._deduplicate_improvement_areas(all_improvement_areas)
        unique_learning_suggestions = self._deduplicate_learning_suggestions(all_learning_suggestions)
        
        return {
            "user_id": user_id,
            "period_days": days,
            "total_records": len(progress_records),
            "average_scores": average_scores,
            "improvement_trends": average_trends,
            "recommendations": unique_recommendations[:10],  # Top 10
            "improvement_areas": unique_improvement_areas[:5],  # Top 5
            "learning_suggestions": unique_learning_suggestions[:10]  # Top 10
        }
    
    def generate_performance_insights(self, user_id: int) -> Dict[str, Any]:
        """Generate performance insights and recommendations based on user data"""
        
        # Get recent performance metrics
        recent_sessions = self.db.query(InterviewSession).filter(
            and_(
                InterviewSession.user_id == user_id,
                InterviewSession.status == "completed"
            )
        ).order_by(desc(InterviewSession.created_at)).limit(10).all()
        
        if not recent_sessions:
            return {
                "insights": [],
                "recommendations": [],
                "improvement_areas": [],
                "learning_suggestions": []
            }
        
        # Analyze performance metrics
        all_metrics = []
        for session in recent_sessions:
            metrics = self.db.query(PerformanceMetrics).filter(
                PerformanceMetrics.session_id == session.id
            ).all()
            all_metrics.extend(metrics)
        
        if not all_metrics:
            return {
                "insights": [],
                "recommendations": [],
                "improvement_areas": [],
                "learning_suggestions": []
            }
        
        # Calculate averages
        avg_content = sum(m.content_quality_score for m in all_metrics) / len(all_metrics)
        avg_body_language = sum(m.body_language_score or 0 for m in all_metrics) / len(all_metrics)
        avg_tone = sum(m.tone_confidence_score or 0 for m in all_metrics) / len(all_metrics)
        
        insights = []
        recommendations = []
        improvement_areas = []
        learning_suggestions = []
        
        # Generate insights based on performance
        if avg_content < 70:
            insights.append("Content quality needs improvement")
            improvement_areas.append({
                "area": "Content Quality",
                "priority": "high",
                "suggestions": [
                    "Practice structuring answers using the STAR method",
                    "Prepare specific examples for common interview questions",
                    "Focus on providing concrete details and measurable results"
                ]
            })
            recommendations.append({
                "category": "content_quality",
                "resource_type": "course",
                "title": "Interview Answer Structuring Masterclass",
                "url": "https://example.com/content-quality-course",
                "priority": "high"
            })
            learning_suggestions.append({
                "suggestion": "Practice the STAR method for behavioral questions",
                "category": "content_quality",
                "difficulty": "beginner"
            })
        
        if avg_body_language < 70:
            insights.append("Body language and posture need attention")
            improvement_areas.append({
                "area": "Body Language",
                "priority": "medium",
                "suggestions": [
                    "Practice maintaining eye contact during responses",
                    "Work on confident posture and hand gestures",
                    "Record yourself to identify nervous habits"
                ]
            })
            recommendations.append({
                "category": "body_language",
                "resource_type": "video",
                "title": "Professional Body Language for Interviews",
                "url": "https://example.com/body-language-video",
                "priority": "medium"
            })
        
        if avg_tone < 70:
            insights.append("Voice confidence and tone could be stronger")
            improvement_areas.append({
                "area": "Voice Confidence",
                "priority": "medium",
                "suggestions": [
                    "Practice speaking with a clear, confident tone",
                    "Work on pacing and avoiding filler words",
                    "Record practice sessions to improve vocal delivery"
                ]
            })
            recommendations.append({
                "category": "voice_analysis",
                "resource_type": "tutorial",
                "title": "Voice Training for Professional Communication",
                "url": "https://example.com/voice-training",
                "priority": "medium"
            })
        
        # Add general learning suggestions
        learning_suggestions.extend([
            {
                "suggestion": "Practice mock interviews regularly",
                "category": "overall",
                "difficulty": "intermediate"
            },
            {
                "suggestion": "Research common questions for your target role",
                "category": "content_quality",
                "difficulty": "beginner"
            }
        ])
        
        return {
            "insights": insights,
            "recommendations": recommendations,
            "improvement_areas": improvement_areas,
            "learning_suggestions": learning_suggestions
        }
    
    def _deduplicate_recommendations(self, recommendations: List[Dict]) -> List[Dict]:
        """Remove duplicate recommendations and sort by priority"""
        seen = set()
        unique = []
        
        priority_order = {"high": 1, "medium": 2, "low": 3}
        
        # Sort by priority first
        sorted_recs = sorted(
            recommendations,
            key=lambda x: priority_order.get(x.get("priority", "medium"), 2)
        )
        
        for rec in sorted_recs:
            key = (rec.get("title"), rec.get("category"))
            if key not in seen:
                seen.add(key)
                unique.append(rec)
        
        return unique
    
    def _deduplicate_improvement_areas(self, areas: List[Dict]) -> List[Dict]:
        """Remove duplicate improvement areas and sort by priority"""
        seen = set()
        unique = []
        
        priority_order = {"high": 1, "medium": 2, "low": 3}
        
        # Sort by priority first
        sorted_areas = sorted(
            areas,
            key=lambda x: priority_order.get(x.get("priority", "medium"), 2)
        )
        
        for area in sorted_areas:
            key = area.get("area")
            if key not in seen:
                seen.add(key)
                unique.append(area)
        
        return unique
    
    def _deduplicate_learning_suggestions(self, suggestions: List[Dict]) -> List[Dict]:
        """Remove duplicate learning suggestions"""
        seen = set()
        unique = []
        
        for suggestion in suggestions:
            key = suggestion.get("suggestion")
            if key not in seen:
                seen.add(key)
                unique.append(suggestion)
        
        return unique