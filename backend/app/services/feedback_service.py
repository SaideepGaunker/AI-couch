"""
Feedback Service for answer analysis and personalized feedback generation
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.db.models import Question, User, InterviewSession, PerformanceMetrics
from app.services.gemini_service import GeminiService
from app.crud.question import get_question


class FeedbackService:
    """Service for generating and managing feedback"""
    
    def __init__(self, db: Session):
        self.db = db
        self.gemini_service = GeminiService(db)
    
    def analyze_answer(
        self, 
        question_id: int, 
        answer_text: str, 
        user_id: int, 
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Analyze user's answer and provide detailed feedback"""
        
        # Get question
        question = get_question(self.db, question_id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found"
            )
        
        # Get user context
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Prepare context for analysis
        analysis_context = {
            'role': user.role,
            'experience_level': user.experience_level,
            'target_roles': user.target_roles,
            'question_type': question.question_type,
            'difficulty_level': question.difficulty_level,
            **(context or {})
        }
        
        # Use Gemini API for analysis
        evaluation = self.gemini_service.evaluate_answer(
            question=question.content,
            answer=answer_text,
            context=analysis_context
        )
        
        return evaluation
    
    def get_session_feedback(self, session_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get comprehensive feedback for an interview session"""
        
        # Verify session ownership
        session = self.db.query(InterviewSession).filter(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id
        ).first()
        
        if not session:
            return None
        
        # Get performance metrics
        metrics = self.db.query(PerformanceMetrics).filter(
            PerformanceMetrics.session_id == session_id
        ).all()
        
        if not metrics:
            return {
                'session_id': session_id,
                'message': 'No performance data available',
                'overall_score': 0,
                'feedback': 'Complete the session to receive feedback'
            }
        
        # Calculate aggregate scores
        avg_content_score = sum(m.content_quality_score for m in metrics) / len(metrics)
        avg_body_language = sum(m.body_language_score or 0 for m in metrics) / len(metrics)
        avg_tone_score = sum(m.tone_confidence_score or 0 for m in metrics) / len(metrics)
        
        # Collect all improvement suggestions
        all_suggestions = []
        for metric in metrics:
            if metric.improvement_suggestions:
                all_suggestions.extend(metric.improvement_suggestions)
        
        # Get unique suggestions
        unique_suggestions = list(set(all_suggestions))
        
        return {
            'session_id': session_id,
            'overall_score': session.overall_score,
            'detailed_scores': {
                'content_quality': avg_content_score,
                'body_language': avg_body_language,
                'tone_confidence': avg_tone_score
            },
            'questions_answered': len(metrics),
            'improvement_suggestions': unique_suggestions[:10],  # Top 10
            'session_summary': {
                'duration': session.duration,
                'session_type': session.session_type,
                'target_role': session.target_role,
                'completed_at': session.completed_at.isoformat() if session.completed_at else None
            }
        }
    
    def generate_personalized_feedback(
        self, 
        session_id: int, 
        user_id: int, 
        performance_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate personalized feedback using AI"""
        
        # Verify session ownership
        session = self.db.query(InterviewSession).filter(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        # Get user information
        user = self.db.query(User).filter(User.id == user_id).first()
        
        # Enhance performance data with user context
        enhanced_data = {
            **performance_data,
            'user_context': {
                'role': user.role,
                'experience_level': user.experience_level,
                'target_roles': user.target_roles,
                'session_type': session.session_type,
                'target_role': session.target_role
            }
        }
        
        # Generate feedback using Gemini API
        feedback = self.gemini_service.generate_feedback(enhanced_data)
        
        return feedback