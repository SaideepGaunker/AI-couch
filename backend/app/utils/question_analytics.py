"""
Question analytics and usage tracking utilities
"""
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
import logging

from app.db.models import Question, PerformanceMetrics, InterviewSession

logger = logging.getLogger(__name__)


class QuestionAnalytics:
    """Analytics for question usage and effectiveness"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_question_usage_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get question usage statistics"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Most used questions
        most_used = self.db.query(
            Question.id,
            Question.content,
            func.count(PerformanceMetrics.id).label('usage_count')
        ).join(
            PerformanceMetrics
        ).join(
            InterviewSession
        ).filter(
            InterviewSession.created_at >= start_date
        ).group_by(
            Question.id, Question.content
        ).order_by(
            func.count(PerformanceMetrics.id).desc()
        ).limit(10).all()
        
        # Question effectiveness (average scores)
        effectiveness = self.db.query(
            Question.id,
            Question.content,
            func.avg(PerformanceMetrics.content_quality_score).label('avg_score'),
            func.count(PerformanceMetrics.id).label('usage_count')
        ).join(
            PerformanceMetrics
        ).join(
            InterviewSession
        ).filter(
            InterviewSession.created_at >= start_date
        ).group_by(
            Question.id, Question.content
        ).having(
            func.count(PerformanceMetrics.id) >= 5  # Minimum usage threshold
        ).order_by(
            func.avg(PerformanceMetrics.content_quality_score).desc()
        ).limit(10).all()
        
        return {
            'most_used_questions': [
                {
                    'question_id': q.id,
                    'content': q.content[:100] + '...' if len(q.content) > 100 else q.content,
                    'usage_count': q.usage_count
                }
                for q in most_used
            ],
            'most_effective_questions': [
                {
                    'question_id': q.id,
                    'content': q.content[:100] + '...' if len(q.content) > 100 else q.content,
                    'avg_score': round(float(q.avg_score), 2),
                    'usage_count': q.usage_count
                }
                for q in effectiveness
            ]
        }
    
    def get_difficulty_distribution(self) -> Dict[str, Any]:
        """Get distribution of questions by difficulty"""
        distribution = self.db.query(
            Question.difficulty_level,
            func.count(Question.id).label('count')
        ).group_by(Question.difficulty_level).all()
        
        total_questions = sum(item.count for item in distribution)
        
        return {
            'distribution': {
                item.difficulty_level: {
                    'count': item.count,
                    'percentage': round((item.count / total_questions) * 100, 2) if total_questions > 0 else 0
                }
                for item in distribution
            },
            'total_questions': total_questions
        }
    
    def get_role_category_stats(self) -> Dict[str, Any]:
        """Get statistics by role category"""
        stats = self.db.query(
            Question.role_category,
            func.count(Question.id).label('question_count'),
            func.avg(func.coalesce(PerformanceMetrics.content_quality_score, 0)).label('avg_performance')
        ).outerjoin(
            PerformanceMetrics
        ).group_by(
            Question.role_category
        ).all()
        
        return {
            'role_stats': [
                {
                    'role_category': stat.role_category,
                    'question_count': stat.question_count,
                    'avg_performance': round(float(stat.avg_performance or 0), 2)
                }
                for stat in stats
            ]
        }
    
    def get_question_performance_trends(self, question_id: int, days: int = 90) -> Dict[str, Any]:
        """Get performance trends for a specific question"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Daily performance averages
        daily_performance = self.db.query(
            func.date(InterviewSession.created_at).label('date'),
            func.avg(PerformanceMetrics.content_quality_score).label('avg_score'),
            func.count(PerformanceMetrics.id).label('usage_count')
        ).join(
            InterviewSession
        ).filter(
            and_(
                PerformanceMetrics.question_id == question_id,
                InterviewSession.created_at >= start_date
            )
        ).group_by(
            func.date(InterviewSession.created_at)
        ).order_by(
            func.date(InterviewSession.created_at)
        ).all()
        
        return {
            'question_id': question_id,
            'daily_trends': [
                {
                    'date': trend.date.isoformat(),
                    'avg_score': round(float(trend.avg_score), 2),
                    'usage_count': trend.usage_count
                }
                for trend in daily_performance
            ]
        }
    
    def identify_problematic_questions(self, min_usage: int = 10) -> List[Dict[str, Any]]:
        """Identify questions with consistently low performance"""
        problematic = self.db.query(
            Question.id,
            Question.content,
            func.avg(PerformanceMetrics.content_quality_score).label('avg_score'),
            func.count(PerformanceMetrics.id).label('usage_count')
        ).join(
            PerformanceMetrics
        ).group_by(
            Question.id, Question.content
        ).having(
            and_(
                func.count(PerformanceMetrics.id) >= min_usage,
                func.avg(PerformanceMetrics.content_quality_score) < 60  # Low performance threshold
            )
        ).order_by(
            func.avg(PerformanceMetrics.content_quality_score)
        ).all()
        
        return [
            {
                'question_id': q.id,
                'content': q.content[:150] + '...' if len(q.content) > 150 else q.content,
                'avg_score': round(float(q.avg_score), 2),
                'usage_count': q.usage_count,
                'recommendation': 'Consider revising or removing this question'
            }
            for q in problematic
        ]
    
    def get_question_diversity_score(self) -> Dict[str, Any]:
        """Calculate diversity score of question database"""
        # Count unique question types, difficulties, and roles
        type_count = self.db.query(Question.question_type).distinct().count()
        difficulty_count = self.db.query(Question.difficulty_level).distinct().count()
        role_count = self.db.query(Question.role_category).distinct().count()
        
        # Calculate distribution evenness
        type_distribution = self.db.query(
            Question.question_type,
            func.count(Question.id).label('count')
        ).group_by(Question.question_type).all()
        
        total_questions = sum(item.count for item in type_distribution)
        if total_questions == 0:
            return {'diversity_score': 0, 'recommendations': ['Add more questions to the database']}
        
        # Calculate Shannon diversity index for question types
        shannon_index = 0
        for item in type_distribution:
            proportion = item.count / total_questions
            if proportion > 0:
                shannon_index -= proportion * (proportion ** 0.5)  # Simplified calculation
        
        diversity_score = min(100, shannon_index * 50)  # Normalize to 0-100
        
        recommendations = []
        if diversity_score < 50:
            recommendations.append("Increase variety in question types")
        if type_count < 3:
            recommendations.append("Add more question types (behavioral, technical, situational)")
        if difficulty_count < 3:
            recommendations.append("Ensure questions cover all difficulty levels")
        if role_count < 5:
            recommendations.append("Add questions for more role categories")
        
        return {
            'diversity_score': round(diversity_score, 2),
            'type_count': type_count,
            'difficulty_count': difficulty_count,
            'role_count': role_count,
            'recommendations': recommendations
        }