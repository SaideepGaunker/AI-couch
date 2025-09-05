"""
User Context Builder Service for collecting comprehensive user data for Gemini prompts
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.db.models import (
    User, InterviewSession, PerformanceMetrics, UserProgress, 
    RoleHierarchy, Question
)
from app.services.role_hierarchy_service import RoleHierarchyService

logger = logging.getLogger(__name__)


class UserContextBuilder:
    """Build comprehensive user context for Gemini prompts"""
    
    def __init__(self, db: Session):
        self.db = db
        self.role_hierarchy_service = RoleHierarchyService(db)
    
    def _get_role_attribute(self, role_obj, attr_name: str, default_value=''):
        """Helper method to get attribute from either dictionary or Pydantic model"""
        if role_obj is None:
            return default_value
        if hasattr(role_obj, attr_name):
            # Pydantic model case
            return getattr(role_obj, attr_name, default_value)
        else:
            # Dictionary case
            return role_obj.get(attr_name, default_value)
    
    def build_complete_context(
        self, 
        user_id: int, 
        session_data: Dict[str, Any],
        role_hierarchy: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build rich context including all available user and session data
        
        Args:
            user_id: ID of the user
            session_data: Current session information
            role_hierarchy: Optional hierarchical role data
            
        Returns:
            Comprehensive context dictionary for Gemini prompts
        """
        
        try:
            logger.info(f"Building complete context for user {user_id}")
            
            # Get user data
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Build user profile context
            user_profile = self._build_user_profile_context(user, role_hierarchy)
            
            # Build session context
            session_context = self._build_session_context(user_id, session_data)
            
            # Build performance history context
            performance_history = self._build_performance_history_context(user_id)
            
            # Build question requirements context
            question_requirements = self._build_question_requirements_context(
                role_hierarchy, session_data
            )
            
            # Combine all contexts
            complete_context = {
                'user_profile': user_profile,
                'session_context': session_context,
                'performance_history': performance_history,
                'question_requirements': question_requirements,
                'context_metadata': {
                    'built_at': datetime.utcnow().isoformat(),
                    'user_id': user_id,
                    'context_version': '1.0'
                }
            }
            
            logger.info(f"Successfully built complete context for user {user_id}")
            return complete_context
            
        except Exception as e:
            logger.error(f"Error building complete context for user {user_id}: {str(e)}")
            raise
    
    def _build_user_profile_context(
        self, 
        user: User, 
        role_hierarchy: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build comprehensive user profile context"""
        
        try:
            # Build role hierarchy context
            role_hierarchy_context = {}
            tech_stacks = []
            question_tags = []
            
            if role_hierarchy:
                # Use provided role hierarchy
                main_role = self._get_role_attribute(role_hierarchy, 'main_role', user.main_role)
                sub_role = self._get_role_attribute(role_hierarchy, 'sub_role', user.sub_role)
                specialization = self._get_role_attribute(role_hierarchy, 'specialization', user.specialization)
                
                role_hierarchy_context = {
                    'main_role': main_role,
                    'sub_role': sub_role,
                    'specialization': specialization
                }
                
                # Get tech stacks and question tags from role hierarchy service
                if main_role:
                    try:
                        tech_stacks = self.role_hierarchy_service.get_tech_stacks_for_role(
                            main_role, sub_role
                        )
                        question_tags = self.role_hierarchy_service.get_question_tags_for_role(
                            main_role, sub_role, specialization
                        )
                    except Exception as e:
                        logger.warning(f"Error getting role hierarchy data: {str(e)}")
                        tech_stacks = []
                        question_tags = []
            else:
                # Use user's stored role data
                role_hierarchy_context = {
                    'main_role': user.main_role,
                    'sub_role': user.sub_role,
                    'specialization': user.specialization
                }
                
                if user.main_role:
                    try:
                        tech_stacks = self.role_hierarchy_service.get_tech_stacks_for_role(
                            user.main_role, user.sub_role
                        )
                        question_tags = self.role_hierarchy_service.get_question_tags_for_role(
                            user.main_role, user.sub_role, user.specialization
                        )
                    except Exception as e:
                        logger.warning(f"Error getting role hierarchy data: {str(e)}")
                        tech_stacks = []
                        question_tags = []
            
            # Build preferences context
            preferences = {
                'target_roles': user.target_roles or [],
                'experience_level': user.experience_level,
                'preferred_difficulty': self._get_user_preferred_difficulty(user.id),
                'preferred_question_types': self._get_user_preferred_question_types(user.id)
            }
            
            # Build tech stack proficiency context
            tech_stack_proficiency = self._build_tech_stack_proficiency(user.id, tech_stacks)
            
            user_profile = {
                'user_id': user.id,
                'role_hierarchy': role_hierarchy_context,
                'tech_stacks': tech_stacks,
                'question_tags': question_tags,
                'experience_level': user.experience_level,
                'preferences': preferences,
                'tech_stack_proficiency': tech_stack_proficiency,
                'account_info': {
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'last_login': user.last_login.isoformat() if user.last_login else None,
                    'is_verified': user.is_verified
                }
            }
            
            return user_profile
            
        except Exception as e:
            logger.error(f"Error building user profile context: {str(e)}")
            raise
    
    def _build_session_context(
        self, 
        user_id: int, 
        session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build comprehensive session context"""
        
        try:
            # Extract session data
            session_type = session_data.get('session_type', 'main')
            question_count = session_data.get('question_count', 5)
            current_difficulty = session_data.get('difficulty', 'medium')
            time_limit = session_data.get('duration', 30)
            
            # Get previous answers from current session if available
            previous_answers = session_data.get('previous_answers', [])
            
            # Get current performance in session
            current_performance = self._get_current_session_performance(
                session_data.get('session_id'), user_id
            )
            
            # Get recent session history for context
            recent_sessions = self._get_recent_session_history(user_id, limit=3)
            
            session_context = {
                'session_type': session_type,
                'question_count': question_count,
                'current_difficulty': current_difficulty,
                'time_limit': time_limit,
                'previous_answers': previous_answers,
                'current_performance': current_performance,
                'recent_sessions': recent_sessions,
                'session_metadata': {
                    'session_id': session_data.get('session_id'),
                    'target_role': session_data.get('target_role'),
                    'created_at': session_data.get('created_at'),
                    'parent_session_id': session_data.get('parent_session_id')
                }
            }
            
            return session_context
            
        except Exception as e:
            logger.error(f"Error building session context: {str(e)}")
            raise
    
    def _build_performance_history_context(self, user_id: int) -> Dict[str, Any]:
        """Build comprehensive performance history context"""
        
        try:
            # Get overall performance statistics
            overall_stats = self._get_overall_performance_stats(user_id)
            
            # Get recent performance trends
            recent_trends = self._get_recent_performance_trends(user_id, days=30)
            
            # Get difficulty progression history
            difficulty_progression = self._get_difficulty_progression(user_id)
            
            # Get question type performance
            question_type_performance = self._get_question_type_performance(user_id)
            
            # Get improvement areas
            improvement_areas = self._get_improvement_areas(user_id)
            
            performance_history = {
                'overall_stats': overall_stats,
                'recent_trends': recent_trends,
                'difficulty_progression': difficulty_progression,
                'question_type_performance': question_type_performance,
                'improvement_areas': improvement_areas,
                'performance_metadata': {
                    'total_sessions': overall_stats.get('total_sessions', 0),
                    'avg_score': overall_stats.get('avg_overall_score', 0),
                    'last_session_date': overall_stats.get('last_session_date')
                }
            }
            
            return performance_history
            
        except Exception as e:
            logger.error(f"Error building performance history context: {str(e)}")
            raise
    
    def _build_question_requirements_context(
        self, 
        role_hierarchy: Optional[Dict[str, Any]], 
        session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build question requirements and distribution context"""
        
        try:
            # Define question distribution requirements
            distribution = {
                'theory_percentage': 20,
                'coding_percentage': 40,
                'aptitude_percentage': 40
            }
            
            # Build difficulty mapping based on role and experience
            difficulty_mapping = {
                'easy': 'simple coding (loops, arrays), basic aptitude, simple theory',
                'medium': 'problem-solving, data structures/algorithms, applied theory',
                'hard': 'advanced coding, optimization, system/architecture theory',
                'expert': 'complex system design, advanced algorithms, architectural decisions, leadership scenarios'
            }
            
            # Build role-specific competencies
            role_competencies = []
            if role_hierarchy:
                main_role = self._get_role_attribute(role_hierarchy, 'main_role')
                sub_role = self._get_role_attribute(role_hierarchy, 'sub_role')
                specialization = self._get_role_attribute(role_hierarchy, 'specialization')
                
                role_competencies = self._get_role_specific_competencies(
                    main_role, sub_role, specialization
                )
            
            # Build question examples based on role and difficulty
            question_examples = self._get_question_examples_for_role(
                role_hierarchy, session_data.get('difficulty', 'medium')
            )
            
            question_requirements = {
                'distribution': distribution,
                'difficulty_mapping': difficulty_mapping,
                'role_competencies': role_competencies,
                'question_examples': question_examples,
                'validation_criteria': {
                    'role_relevance': True,
                    'difficulty_appropriateness': True,
                    'tech_stack_alignment': True,
                    'experience_level_match': True
                }
            }
            
            return question_requirements
            
        except Exception as e:
            logger.error(f"Error building question requirements context: {str(e)}")
            raise
    
    def _get_user_preferred_difficulty(self, user_id: int) -> str:
        """Get user's preferred difficulty based on recent sessions"""
        
        try:
            # Get most common difficulty from recent sessions
            recent_sessions = self.db.query(InterviewSession.difficulty_level).filter(
                InterviewSession.user_id == user_id,
                InterviewSession.difficulty_level.isnot(None)
            ).order_by(desc(InterviewSession.created_at)).limit(5).all()
            
            if recent_sessions:
                difficulties = [session.difficulty_level for session in recent_sessions]
                # Return most common difficulty
                return max(set(difficulties), key=difficulties.count)
            
            return 'medium'  # Default
            
        except Exception as e:
            logger.error(f"Error getting user preferred difficulty: {str(e)}")
            return 'medium'
    
    def _get_user_preferred_question_types(self, user_id: int) -> List[str]:
        """Get user's preferred question types based on performance"""
        
        try:
            # Get question types where user performs well
            good_performance_types = self.db.query(
                Question.question_type,
                func.avg(PerformanceMetrics.content_quality_score).label('avg_score')
            ).join(
                PerformanceMetrics, Question.id == PerformanceMetrics.question_id
            ).join(
                InterviewSession, PerformanceMetrics.session_id == InterviewSession.id
            ).filter(
                InterviewSession.user_id == user_id
            ).group_by(
                Question.question_type
            ).having(
                func.avg(PerformanceMetrics.content_quality_score) > 70
            ).all()
            
            return [qtype.question_type for qtype in good_performance_types]
            
        except Exception as e:
            logger.error(f"Error getting user preferred question types: {str(e)}")
            return ['behavioral', 'technical', 'situational']
    
    def _build_tech_stack_proficiency(
        self, 
        user_id: int, 
        tech_stacks: List[str]
    ) -> Dict[str, str]:
        """Build tech stack proficiency mapping"""
        
        try:
            proficiency = {}
            
            # For each tech stack, determine proficiency based on performance
            for tech in tech_stacks:
                # Get performance on questions related to this tech stack
                tech_performance = self._get_tech_stack_performance(user_id, tech)
                
                if tech_performance >= 80:
                    proficiency[tech] = 'expert'
                elif tech_performance >= 60:
                    proficiency[tech] = 'intermediate'
                elif tech_performance >= 40:
                    proficiency[tech] = 'beginner'
                else:
                    proficiency[tech] = 'learning'
            
            return proficiency
            
        except Exception as e:
            logger.error(f"Error building tech stack proficiency: {str(e)}")
            return {}
    
    def _get_tech_stack_performance(self, user_id: int, tech_stack: str) -> float:
        """Get user's performance on questions related to specific tech stack"""
        
        try:
            # Query performance on questions that mention this tech stack
            performance = self.db.query(
                func.avg(PerformanceMetrics.content_quality_score)
            ).join(
                Question, PerformanceMetrics.question_id == Question.id
            ).join(
                InterviewSession, PerformanceMetrics.session_id == InterviewSession.id
            ).filter(
                InterviewSession.user_id == user_id,
                Question.content.ilike(f'%{tech_stack}%')
            ).scalar()
            
            return float(performance or 50.0)  # Default to 50 if no data
            
        except Exception as e:
            logger.error(f"Error getting tech stack performance: {str(e)}")
            return 50.0
    
    def _get_current_session_performance(
        self, 
        session_id: Optional[int], 
        user_id: int
    ) -> Dict[str, Any]:
        """Get current session performance metrics"""
        
        try:
            if not session_id:
                return {}
            
            # Get performance metrics for current session
            metrics = self.db.query(PerformanceMetrics).filter(
                PerformanceMetrics.session_id == session_id
            ).all()
            
            if not metrics:
                return {}
            
            # Calculate averages
            avg_body_language = sum(m.body_language_score for m in metrics) / len(metrics)
            avg_tone = sum(m.tone_confidence_score for m in metrics) / len(metrics)
            avg_content = sum(m.content_quality_score for m in metrics) / len(metrics)
            
            return {
                'questions_answered': len(metrics),
                'avg_body_language_score': avg_body_language,
                'avg_tone_confidence_score': avg_tone,
                'avg_content_quality_score': avg_content,
                'overall_trend': 'improving' if avg_content > 70 else 'needs_improvement'
            }
            
        except Exception as e:
            logger.error(f"Error getting current session performance: {str(e)}")
            return {}
    
    def _get_recent_session_history(self, user_id: int, limit: int = 3) -> List[Dict[str, Any]]:
        """Get recent session history for context"""
        
        try:
            recent_sessions = self.db.query(InterviewSession).filter(
                InterviewSession.user_id == user_id,
                InterviewSession.status == 'completed'
            ).order_by(desc(InterviewSession.completed_at)).limit(limit).all()
            
            session_history = []
            for session in recent_sessions:
                session_history.append({
                    'session_id': session.id,
                    'session_type': session.session_type,
                    'target_role': session.target_role,
                    'difficulty_level': session.difficulty_level,
                    'overall_score': session.overall_score,
                    'performance_score': session.performance_score,
                    'completed_at': session.completed_at.isoformat() if session.completed_at else None
                })
            
            return session_history
            
        except Exception as e:
            logger.error(f"Error getting recent session history: {str(e)}")
            return []
    
    def _get_overall_performance_stats(self, user_id: int) -> Dict[str, Any]:
        """Get overall performance statistics"""
        
        try:
            # Get session statistics
            session_stats = self.db.query(
                func.count(InterviewSession.id).label('total_sessions'),
                func.avg(InterviewSession.overall_score).label('avg_overall_score'),
                func.avg(InterviewSession.performance_score).label('avg_performance_score'),
                func.max(InterviewSession.completed_at).label('last_session_date')
            ).filter(
                InterviewSession.user_id == user_id,
                InterviewSession.status == 'completed'
            ).first()
            
            # Get performance metrics statistics
            metrics_stats = self.db.query(
                func.avg(PerformanceMetrics.body_language_score).label('avg_body_language'),
                func.avg(PerformanceMetrics.tone_confidence_score).label('avg_tone'),
                func.avg(PerformanceMetrics.content_quality_score).label('avg_content')
            ).join(
                InterviewSession, PerformanceMetrics.session_id == InterviewSession.id
            ).filter(
                InterviewSession.user_id == user_id
            ).first()
            
            return {
                'total_sessions': session_stats.total_sessions or 0,
                'avg_overall_score': float(session_stats.avg_overall_score or 0),
                'avg_performance_score': float(session_stats.avg_performance_score or 0),
                'last_session_date': session_stats.last_session_date.isoformat() if session_stats.last_session_date else None,
                'avg_body_language_score': float(metrics_stats.avg_body_language or 0),
                'avg_tone_confidence_score': float(metrics_stats.avg_tone or 0),
                'avg_content_quality_score': float(metrics_stats.avg_content or 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting overall performance stats: {str(e)}")
            return {}
    
    def _get_recent_performance_trends(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get recent performance trends"""
        
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get recent sessions with performance data
            recent_sessions = self.db.query(InterviewSession).filter(
                InterviewSession.user_id == user_id,
                InterviewSession.completed_at >= start_date,
                InterviewSession.status == 'completed'
            ).order_by(InterviewSession.completed_at).all()
            
            if len(recent_sessions) < 2:
                return {'trend': 'insufficient_data'}
            
            # Calculate trend
            scores = [session.performance_score for session in recent_sessions if session.performance_score]
            if len(scores) >= 2:
                trend = 'improving' if scores[-1] > scores[0] else 'declining'
                improvement_rate = (scores[-1] - scores[0]) / len(scores)
            else:
                trend = 'stable'
                improvement_rate = 0
            
            return {
                'trend': trend,
                'improvement_rate': improvement_rate,
                'recent_sessions_count': len(recent_sessions),
                'avg_recent_score': sum(scores) / len(scores) if scores else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting recent performance trends: {str(e)}")
            return {}
    
    def _get_difficulty_progression(self, user_id: int) -> List[Dict[str, Any]]:
        """Get difficulty progression history"""
        
        try:
            sessions = self.db.query(InterviewSession).filter(
                InterviewSession.user_id == user_id,
                InterviewSession.difficulty_level.isnot(None)
            ).order_by(InterviewSession.created_at).limit(10).all()
            
            progression = []
            for session in sessions:
                progression.append({
                    'session_id': session.id,
                    'difficulty_level': session.difficulty_level,
                    'performance_score': session.performance_score,
                    'date': session.created_at.isoformat() if session.created_at else None
                })
            
            return progression
            
        except Exception as e:
            logger.error(f"Error getting difficulty progression: {str(e)}")
            return []
    
    def _get_question_type_performance(self, user_id: int) -> Dict[str, float]:
        """Get performance by question type"""
        
        try:
            performance_by_type = self.db.query(
                Question.question_type,
                func.avg(PerformanceMetrics.content_quality_score).label('avg_score')
            ).join(
                PerformanceMetrics, Question.id == PerformanceMetrics.question_id
            ).join(
                InterviewSession, PerformanceMetrics.session_id == InterviewSession.id
            ).filter(
                InterviewSession.user_id == user_id
            ).group_by(Question.question_type).all()
            
            return {
                perf.question_type: float(perf.avg_score) 
                for perf in performance_by_type
            }
            
        except Exception as e:
            logger.error(f"Error getting question type performance: {str(e)}")
            return {}
    
    def _get_improvement_areas(self, user_id: int) -> List[str]:
        """Get areas needing improvement based on performance"""
        
        try:
            # Get question types with low performance
            low_performance_types = self.db.query(
                Question.question_type
            ).join(
                PerformanceMetrics, Question.id == PerformanceMetrics.question_id
            ).join(
                InterviewSession, PerformanceMetrics.session_id == InterviewSession.id
            ).filter(
                InterviewSession.user_id == user_id
            ).group_by(
                Question.question_type
            ).having(
                func.avg(PerformanceMetrics.content_quality_score) < 60
            ).all()
            
            return [qtype.question_type for qtype in low_performance_types]
            
        except Exception as e:
            logger.error(f"Error getting improvement areas: {str(e)}")
            return []
    
    def _get_role_specific_competencies(
        self, 
        main_role: Optional[str], 
        sub_role: Optional[str], 
        specialization: Optional[str]
    ) -> List[str]:
        """Get role-specific competencies to assess"""
        
        try:
            if not main_role:
                return []
            
            # Define competency mappings for different roles
            competency_mappings = {
                'Software Developer': {
                    'Frontend Developer': ['UI/UX Design', 'JavaScript Frameworks', 'Responsive Design', 'Browser Compatibility'],
                    'Backend Developer': ['API Design', 'Database Management', 'Server Architecture', 'Security'],
                    'Mobile Developer': ['Mobile UI/UX', 'Platform-specific APIs', 'Performance Optimization', 'App Store Guidelines'],
                    'Full Stack Developer': ['End-to-end Development', 'System Integration', 'DevOps', 'Architecture Design']
                },
                'Data Scientist': {
                    'ML Engineer': ['Machine Learning Algorithms', 'Model Deployment', 'Data Pipeline', 'MLOps'],
                    'Data Analyst': ['Statistical Analysis', 'Data Visualization', 'Business Intelligence', 'Reporting'],
                    'Research Scientist': ['Research Methodology', 'Experimental Design', 'Publication', 'Innovation']
                },
                'Product Manager': {
                    'Technical Product Manager': ['Technical Requirements', 'API Strategy', 'Engineering Collaboration', 'Technical Roadmapping'],
                    'Growth Product Manager': ['Growth Metrics', 'A/B Testing', 'User Acquisition', 'Conversion Optimization'],
                    'Platform Product Manager': ['Platform Strategy', 'Developer Experience', 'Ecosystem Management', 'Partnerships']
                }
            }
            
            # Get competencies for the role
            role_competencies = competency_mappings.get(main_role, {})
            if sub_role and sub_role in role_competencies:
                return role_competencies[sub_role]
            else:
                # Return general competencies for the main role
                all_competencies = []
                for sub_competencies in role_competencies.values():
                    all_competencies.extend(sub_competencies)
                return list(set(all_competencies))[:5]  # Return top 5 unique competencies
            
        except Exception as e:
            logger.error(f"Error getting role specific competencies: {str(e)}")
            return []
    
    def _get_question_examples_for_role(
        self, 
        role_hierarchy: Optional[Dict[str, Any]], 
        difficulty: str
    ) -> Dict[str, List[str]]:
        """Get question examples based on role and difficulty"""
        
        try:
            examples = {
                'coding': [],
                'aptitude': [],
                'theory': []
            }
            
            if difficulty == 'easy':
                examples['coding'] = [
                    'Write a program to check if a string is a palindrome',
                    'Implement a function to find the maximum element in an array',
                    'Create a simple calculator with basic operations'
                ]
                examples['aptitude'] = [
                    'Find the missing number in a sequence from 1 to 10',
                    'Calculate the time complexity of a simple loop',
                    'Identify the pattern in a given sequence'
                ]
                examples['theory'] = [
                    'Explain the difference between a compiler and an interpreter',
                    'What is the difference between HTTP and HTTPS?',
                    'Define what an API is and give an example'
                ]
            elif difficulty == 'medium':
                examples['coding'] = [
                    'Implement a binary search algorithm',
                    'Design a simple caching mechanism',
                    'Write a function to merge two sorted arrays'
                ]
                examples['aptitude'] = [
                    'Optimize a database query for better performance',
                    'Design a simple load balancing strategy',
                    'Calculate space complexity for a recursive algorithm'
                ]
                examples['theory'] = [
                    'Explain the CAP theorem and its implications',
                    'Describe different types of database indexes',
                    'What are the principles of RESTful API design?'
                ]
            elif difficulty in ['hard', 'expert']:
                examples['coding'] = [
                    'Design and implement a distributed caching system',
                    'Implement a thread-safe singleton pattern',
                    'Design a rate limiting algorithm'
                ]
                examples['aptitude'] = [
                    'Design a system to handle 1 million concurrent users',
                    'Optimize a system for high availability and fault tolerance',
                    'Design a data pipeline for real-time analytics'
                ]
                examples['theory'] = [
                    'Explain microservices architecture and its trade-offs',
                    'Describe event-driven architecture patterns',
                    'What are the challenges in distributed system design?'
                ]
            
            return examples
            
        except Exception as e:
            logger.error(f"Error getting question examples: {str(e)}")
            return {'coding': [], 'aptitude': [], 'theory': []}