"""
Fallback Question Service for managing role-specific fallback questions
when AI generation fails or is unavailable.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.models import Question
from app.schemas.question import QuestionCreate

logger = logging.getLogger(__name__)


class FallbackQuestionService:
    """
    Service for managing intelligent fallback questions when AI generation fails.
    Provides role-specific, difficulty-appropriate questions with quality validation.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self._initialize_fallback_database()
    
    def get_fallback_questions(
        self,
        role: str,
        difficulty: str = "intermediate",
        question_type: str = "mixed",
        count: int = 5,
        context: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Get intelligent fallback questions based on role and difficulty.
        """
        logger.info(f"Generating {count} fallback questions for {role} ({difficulty}, {question_type})")
        
        # Get role-specific questions
        role_questions = self._get_role_specific_questions(role, difficulty, question_type)
        
        # If insufficient role-specific questions, add generic ones
        if len(role_questions) < count:
            generic_questions = self._get_generic_questions(difficulty, question_type)
            role_questions.extend(generic_questions)
        
        # Apply intelligent selection based on context
        if context:
            role_questions = self._apply_contextual_selection(role_questions, context)
        
        # Validate question quality
        validated_questions = self._validate_question_quality(role_questions, role, difficulty)
        
        # Ensure diversity and proper ordering
        final_questions = self._optimize_question_selection(validated_questions, count)
        
        logger.info(f"Selected {len(final_questions)} high-quality fallback questions")
        return final_questions[:count]
    
    def _initialize_fallback_database(self) -> None:
        """Initialize the fallback question database with high-quality questions"""
        try:
            # Check if fallback questions already exist
            existing_fallback = self.db.query(Question).filter(
                Question.generated_by == "fallback_system"
            ).first()
            
            if existing_fallback:
                logger.info("Fallback questions already initialized")
                return
            
            logger.info("Initializing fallback question database")
        except Exception as e:
            logger.error(f"Error checking existing fallback questions: {str(e)}")
    
    def _get_role_specific_questions(
        self, 
        role: str, 
        difficulty: str, 
        question_type: str
    ) -> List[Dict[str, Any]]:
        """Get role-specific questions from the comprehensive question bank"""
        
        role_key = self._normalize_role_name(role)
        
        # Get questions for the specific role
        if role_key == "software_developer":
            role_data = self._get_software_developer_questions()
        elif role_key == "data_scientist":
            role_data = self._get_data_scientist_questions()
        elif "marketing" in role_key:
            role_data = self._get_marketing_questions()
        else:
            role_data = {}
        
        difficulty_questions = role_data.get(difficulty, [])
        
        # Filter by question type
        if question_type != "mixed":
            difficulty_questions = [
                q for q in difficulty_questions 
                if q.get("category") == question_type
            ]
        
        return difficulty_questions
    
    def _get_software_developer_questions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Comprehensive software developer questions across all difficulty levels"""
        return {
            "beginner": [
                {
                    "question": "Tell me about a programming project you've worked on recently. What technologies did you use and what challenges did you face?",
                    "category": "behavioral",
                    "duration": 4,
                    "key_points": ["project description", "technology choices", "problem-solving", "learning outcomes"],
                    "role_relevance": "Assesses hands-on programming experience and technical decision-making",
                    "difficulty": "beginner"
                },
                {
                    "question": "How do you approach debugging when your code isn't working as expected? Walk me through your process.",
                    "category": "technical",
                    "duration": 3,
                    "key_points": ["systematic approach", "debugging tools", "problem isolation", "testing methods"],
                    "role_relevance": "Critical debugging skills for daily development work",
                    "difficulty": "beginner"
                }
            ],
            "intermediate": [
                {
                    "question": "Walk me through how you would design a REST API for a simple e-commerce application. What endpoints would you create?",
                    "category": "technical",
                    "duration": 5,
                    "key_points": ["API design principles", "HTTP methods", "resource modeling", "error handling", "authentication"],
                    "role_relevance": "Core backend development skill for web applications",
                    "difficulty": "intermediate"
                }
            ],
            "advanced": [
                {
                    "question": "Design a system that can handle 1 million concurrent users. Walk me through your architecture decisions and trade-offs.",
                    "category": "technical",
                    "duration": 8,
                    "key_points": ["scalability patterns", "load balancing", "database design", "caching strategies", "monitoring"],
                    "role_relevance": "Senior developers must understand large-scale system design",
                    "difficulty": "advanced"
                }
            ]
        }
    
    def _get_data_scientist_questions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Comprehensive data scientist questions across all difficulty levels"""
        return {
            "beginner": [
                {
                    "question": "Explain the difference between supervised and unsupervised learning. Can you give examples of when you'd use each?",
                    "category": "technical",
                    "duration": 4,
                    "key_points": ["learning paradigms", "use cases", "algorithm examples", "data requirements"],
                    "role_relevance": "Fundamental machine learning concepts",
                    "difficulty": "beginner"
                }
            ],
            "intermediate": [
                {
                    "question": "Describe a machine learning project you've worked on. What was the business problem, your approach, and the outcome?",
                    "category": "behavioral",
                    "duration": 6,
                    "key_points": ["problem definition", "methodology", "model selection", "evaluation metrics", "business impact"],
                    "role_relevance": "Demonstrates practical ML application and business understanding",
                    "difficulty": "intermediate"
                }
            ],
            "advanced": [
                {
                    "question": "Design an end-to-end machine learning pipeline for a real-time recommendation system. What components would you include and why?",
                    "category": "technical",
                    "duration": 8,
                    "key_points": ["system architecture", "data pipeline", "model serving", "monitoring", "A/B testing"],
                    "role_relevance": "Senior-level system design and MLOps knowledge",
                    "difficulty": "advanced"
                }
            ]
        }
    
    def _get_marketing_questions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Comprehensive marketing questions across all difficulty levels"""
        return {
            "easy": [
                {
                    "question": "Tell me about a marketing campaign you've worked on. What was the goal and how did you measure its success?",
                    "category": "behavioral",
                    "duration": 4,
                    "key_points": ["campaign planning", "goal setting", "metrics and KPIs", "results analysis"],
                    "role_relevance": "Basic marketing campaign experience and measurement understanding",
                    "difficulty": "easy"
                },
                {
                    "question": "What digital marketing channels are you most familiar with, and why do you think they're effective?",
                    "category": "technical",
                    "duration": 3,
                    "key_points": ["digital channels", "channel effectiveness", "marketing strategy", "audience targeting"],
                    "role_relevance": "Digital marketing fundamentals and channel knowledge",
                    "difficulty": "easy"
                }
            ],
            "medium": [
                {
                    "question": "How would you approach creating a content marketing strategy for a B2B SaaS product?",
                    "category": "technical",
                    "duration": 5,
                    "key_points": ["content strategy", "B2B marketing", "SaaS knowledge", "audience research", "content planning"],
                    "role_relevance": "Strategic content marketing planning for B2B products",
                    "difficulty": "medium"
                },
                {
                    "question": "Describe a time when you had to pivot a marketing strategy due to poor performance. What changes did you make?",
                    "category": "behavioral",
                    "duration": 4,
                    "key_points": ["strategy adaptation", "performance analysis", "decision making", "results improvement"],
                    "role_relevance": "Adaptability and strategic thinking in marketing",
                    "difficulty": "medium"
                }
            ],
            "hard": [
                {
                    "question": "Design a comprehensive go-to-market strategy for a new product launch. What would be your key considerations and timeline?",
                    "category": "technical",
                    "duration": 7,
                    "key_points": ["GTM strategy", "product launch", "market research", "competitive analysis", "budget allocation", "timeline planning"],
                    "role_relevance": "Senior-level strategic marketing planning and execution",
                    "difficulty": "hard"
                },
                {
                    "question": "How would you measure and optimize the customer acquisition cost (CAC) and lifetime value (LTV) for a subscription-based business?",
                    "category": "technical",
                    "duration": 6,
                    "key_points": ["CAC calculation", "LTV analysis", "optimization strategies", "attribution modeling", "ROI measurement"],
                    "role_relevance": "Advanced marketing analytics and business metrics",
                    "difficulty": "hard"
                }
            ],
            "expert": [
                {
                    "question": "Develop a multi-channel attribution model for a complex customer journey across digital and offline touchpoints. How would you handle data privacy regulations?",
                    "category": "technical",
                    "duration": 8,
                    "key_points": ["attribution modeling", "customer journey mapping", "data privacy", "GDPR compliance", "cross-channel analytics", "advanced modeling"],
                    "role_relevance": "Expert-level marketing analytics and compliance knowledge",
                    "difficulty": "expert"
                }
            ]
        }
    
    def _get_generic_questions(
        self, 
        difficulty: str, 
        question_type: str
    ) -> List[Dict[str, Any]]:
        """Get generic fallback questions when role-specific ones are insufficient"""
        
        generic_questions = {
            "behavioral": {
                "easy": [
                    {
                        "question": "Tell me about yourself and why you're interested in this role.",
                        "category": "behavioral",
                        "duration": 3,
                        "key_points": ["background summary", "career motivation", "role alignment", "communication skills"],
                        "role_relevance": "Universal opener to assess communication and self-awareness",
                        "difficulty": "beginner"
                    }
                ],
                "medium": [
                    {
                        "question": "Tell me about a time when you had to work with a difficult team member. How did you handle the situation?",
                        "category": "behavioral",
                        "duration": 4,
                        "key_points": ["conflict resolution", "communication skills", "teamwork", "professional maturity"],
                        "role_relevance": "Evaluates interpersonal skills and team collaboration",
                        "difficulty": "intermediate"
                    }
                ],
                "hard": [
                    {
                        "question": "Tell me about a time when you had to make a decision that was unpopular with your team. How did you handle it?",
                        "category": "behavioral",
                        "duration": 5,
                        "key_points": ["leadership", "decision-making", "stakeholder management", "communication"],
                        "role_relevance": "Evaluates leadership and decision-making under pressure",
                        "difficulty": "advanced"
                    }
                ]
            },
            "technical": {
                "beginner": [
                    {
                        "question": "What technologies or tools are you most comfortable with, and why did you choose to learn them?",
                        "category": "technical",
                        "duration": 3,
                        "key_points": ["technical skills", "learning preferences", "practical experience", "technology choices"],
                        "role_relevance": "Baseline technical competency assessment",
                        "difficulty": "beginner"
                    }
                ],
                "medium": [
                    {
                        "question": "How do you stay current with new technologies and industry trends in your field?",
                        "category": "technical",
                        "duration": 3,
                        "key_points": ["continuous learning", "industry awareness", "skill development", "professional growth"],
                        "role_relevance": "Assesses commitment to professional development",
                        "difficulty": "intermediate"
                    }
                ],
                "hard": [
                    {
                        "question": "Describe your approach to technical decision-making when there are multiple viable solutions with different trade-offs.",
                        "category": "technical",
                        "duration": 5,
                        "key_points": ["evaluation criteria", "trade-off analysis", "stakeholder consideration", "long-term thinking"],
                        "role_relevance": "Senior-level technical judgment and decision-making",
                        "difficulty": "advanced"
                    }
                ],
                "expert": [
                    {
                        "question": "Describe a complex technical challenge you've solved that required innovative thinking and cross-functional collaboration.",
                        "category": "behavioral",
                        "duration": 6,
                        "key_points": ["complex problem solving", "innovation", "cross-functional collaboration", "technical leadership"],
                        "role_relevance": "Evaluates advanced problem-solving and leadership capabilities",
                        "difficulty": "expert"
                    }
                ]
            },
            "technical": {
                "easy": [
                    {
                        "question": "What technologies or tools are you most comfortable with, and why did you choose to learn them?",
                        "category": "technical",
                        "duration": 3,
                        "key_points": ["technical skills", "learning preferences", "practical experience", "technology choices"],
                        "role_relevance": "Baseline technical competency assessment",
                        "difficulty": "easy"
                    }
                ],
                "medium": [
                    {
                        "question": "How do you stay current with new technologies and industry trends in your field?",
                        "category": "technical",
                        "duration": 3,
                        "key_points": ["continuous learning", "industry awareness", "skill development", "professional growth"],
                        "role_relevance": "Assesses commitment to professional development",
                        "difficulty": "medium"
                    }
                ],
                "hard": [
                    {
                        "question": "Describe your approach to technical decision-making when there are multiple viable solutions with different trade-offs.",
                        "category": "technical",
                        "duration": 5,
                        "key_points": ["evaluation criteria", "trade-off analysis", "stakeholder consideration", "long-term thinking"],
                        "role_relevance": "Senior-level technical judgment and decision-making",
                        "difficulty": "hard"
                    }
                ],
                "expert": [
                    {
                        "question": "Design a scalable architecture for a system that needs to handle 10x growth in the next year. What are your key considerations?",
                        "category": "technical",
                        "duration": 8,
                        "key_points": ["scalability design", "architecture planning", "performance optimization", "future-proofing", "technical leadership"],
                        "role_relevance": "Expert-level system design and technical leadership",
                        "difficulty": "expert"
                    }
                ]
            }
        }
        
        questions = []
        
        if question_type == "mixed" or question_type == "behavioral":
            questions.extend(generic_questions["behavioral"].get(difficulty, []))
        
        if question_type == "mixed" or question_type == "technical":
            questions.extend(generic_questions["technical"].get(difficulty, []))
        
        return questions
    
    def _normalize_role_name(self, role: str) -> str:
        """Normalize role name for consistent lookup"""
        return role.lower().replace(" ", "_").replace("-", "_")
    
    def _apply_contextual_selection(
        self, 
        questions: List[Dict[str, Any]], 
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply contextual selection based on user context"""
        
        # Extract context information
        tech_stacks = context.get("tech_stacks", [])
        specialization = context.get("specialization", "")
        previous_topics = context.get("previous_topics", [])
        
        # Score questions based on context relevance
        scored_questions = []
        for question in questions:
            score = self._calculate_context_score(question, tech_stacks, specialization, previous_topics)
            scored_questions.append((question, score))
        
        # Sort by relevance score
        scored_questions.sort(key=lambda x: x[1], reverse=True)
        
        return [q[0] for q in scored_questions]
    
    def _calculate_context_score(
        self, 
        question: Dict[str, Any], 
        tech_stacks: List[str], 
        specialization: str, 
        previous_topics: List[str]
    ) -> float:
        """Calculate relevance score for a question based on context"""
        
        score = 1.0  # Base score
        
        question_text = question.get("question", "").lower()
        key_points = [kp.lower() for kp in question.get("key_points", [])]
        
        # Tech stack relevance
        for tech in tech_stacks:
            if tech.lower() in question_text or any(tech.lower() in kp for kp in key_points):
                score += 0.5
        
        # Specialization relevance
        if specialization and specialization.lower() in question_text:
            score += 0.3
        
        # Avoid repetition of previous topics
        for topic in previous_topics:
            if topic.lower() in question_text:
                score -= 0.2
        
        return max(score, 0.1)  # Minimum score
    
    def _validate_question_quality(
        self, 
        questions: List[Dict[str, Any]], 
        role: str, 
        difficulty: str
    ) -> List[Dict[str, Any]]:
        """Validate and ensure quality of fallback questions"""
        
        validated_questions = []
        
        for question in questions:
            if self._is_high_quality_question(question, role, difficulty):
                validated_questions.append(question)
        
        return validated_questions
    
    def _is_high_quality_question(
        self, 
        question: Dict[str, Any], 
        role: str, 
        difficulty: str
    ) -> bool:
        """Check if a question meets quality standards"""
        
        # Basic structure validation
        required_fields = ["question", "category", "duration", "key_points"]
        if not all(field in question for field in required_fields):
            return False
        
        # Content quality checks
        question_text = question.get("question", "")
        
        # Minimum length check
        if len(question_text) < 20:
            return False
        
        # Duration validation
        duration = question.get("duration", 0)
        if duration < 2 or duration > 10:
            return False
        
        # Key points validation
        key_points = question.get("key_points", [])
        if len(key_points) < 2:
            return False
        
        return True
    
    def _optimize_question_selection(
        self, 
        questions: List[Dict[str, Any]], 
        count: int
    ) -> List[Dict[str, Any]]:
        """Optimize question selection for diversity and quality"""
        
        if len(questions) <= count:
            return questions
        
        # Ensure category diversity
        categories = {}
        for question in questions:
            category = question.get("category", "unknown")
            if category not in categories:
                categories[category] = []
            categories[category].append(question)
        
        # Select questions ensuring diversity
        selected = []
        remaining_count = count
        
        # First, select at least one from each category
        for category, category_questions in categories.items():
            if remaining_count > 0 and category_questions:
                selected.append(category_questions[0])
                remaining_count -= 1
        
        # Fill remaining slots with best questions
        remaining_questions = [q for q in questions if q not in selected]
        selected.extend(remaining_questions[:remaining_count])
        
        return selected 
   
    def store_fallback_questions_in_db(self, questions: List[Dict[str, Any]], role: str) -> None:
        """Store fallback questions in the database for future use"""
        try:
            for question_data in questions:
                # Check if question already exists to avoid duplicates
                existing = self.db.query(Question).filter(
                    Question.content == question_data["question"],
                    Question.role_category == role
                ).first()
                
                if not existing:
                    question = Question(
                        content=question_data["question"],
                        question_type=question_data.get("category", "behavioral"),
                        role_category=role,
                        difficulty_level=question_data.get("difficulty", "intermediate"),
                        expected_duration=question_data.get("duration", 3),
                        generated_by="fallback_system",
                        question_difficulty_tags=question_data.get("key_points", [])
                    )
                    self.db.add(question)
            
            self.db.commit()
            logger.info(f"Stored {len(questions)} fallback questions for {role}")
            
        except Exception as e:
            logger.error(f"Error storing fallback questions: {str(e)}")
            self.db.rollback()
    
    def _get_adjacent_difficulty_questions(
        self, 
        role_data: Dict[str, List[Dict[str, Any]]], 
        target_difficulty: str, 
        question_type: str
    ) -> List[Dict[str, Any]]:
        """Get questions from adjacent difficulty levels when target level is empty"""
        
        difficulty_order = ["easy", "medium", "hard", "expert"]
        target_index = difficulty_order.index(target_difficulty) if target_difficulty in difficulty_order else 1
        
        # Try adjacent difficulties
        for offset in [1, -1, 2, -2]:
            adj_index = target_index + offset
            if 0 <= adj_index < len(difficulty_order):
                adj_difficulty = difficulty_order[adj_index]
                adj_questions = role_data.get(adj_difficulty, [])
                
                if question_type != "mixed":
                    adj_questions = [q for q in adj_questions if q.get("category") == question_type]
                
                if adj_questions:
                    return adj_questions[:3]  # Limit to 3 questions from different difficulty
        
        return []
    
    def _get_comprehensive_role_questions(self, role: str) -> List[Dict[str, Any]]:
        """Get comprehensive questions for a role across all difficulties"""
        
        role_key = self._normalize_role_name(role)
        
        # Get role-specific questions
        if role_key == "software_developer":
            role_questions = self._get_software_developer_questions()
        elif role_key == "data_scientist":
            role_questions = self._get_data_scientist_questions()
        else:
            return []
        
        all_questions = []
        for difficulty, questions in role_questions.items():
            all_questions.extend(questions)
        
        return all_questions
    
    def get_questions_by_role(
        self,
        role: str,
        difficulty: str = "intermediate",
        session_type: str = "technical",
        count: int = 5
    ) -> List[Question]:
        """
        Get questions by role - required method for compatibility with QuestionService
        Returns Question objects from database or creates fallback questions
        """
        logger.info(f"FallbackQuestionService: Getting {count} questions for role {role}, difficulty {difficulty}")
        
        try:
            # First try to get existing questions from database
            existing_questions = self.db.query(Question).filter(
                Question.role_category == role,
                Question.difficulty_level == difficulty
            ).limit(count).all()
            
            if len(existing_questions) >= count:
                logger.info(f"Found {len(existing_questions)} existing questions in database")
                return existing_questions
            
            # If not enough existing questions, generate fallback questions
            logger.info(f"Only found {len(existing_questions)} existing questions, generating fallbacks")
            
            # Map session_type to question_type
            question_type = "mixed"
            if session_type in ["technical", "behavioral", "situational"]:
                question_type = session_type
            
            # Generate fallback questions
            fallback_data = self.get_fallback_questions(
                role=role,
                difficulty=difficulty,
                question_type=question_type,
                count=count - len(existing_questions)
            )
            
            # Convert fallback data to Question objects
            fallback_questions = []
            for question_data in fallback_data:
                question = Question(
                    content=question_data["question"],
                    question_type=question_data.get("category", "behavioral"),
                    role_category=role,
                    difficulty_level=difficulty,
                    expected_duration=question_data.get("duration", 3),
                    generated_by="fallback_system"
                )
                # Don't add to session yet, just create the object
                fallback_questions.append(question)
            
            # Combine existing and fallback questions
            all_questions = list(existing_questions) + fallback_questions
            
            logger.info(f"Returning {len(all_questions)} questions ({len(existing_questions)} from DB, {len(fallback_questions)} fallback)")
            return all_questions[:count]
            
        except Exception as e:
            logger.error(f"Error in get_questions_by_role: {str(e)}")
            # Return empty list to prevent further errors
            return []