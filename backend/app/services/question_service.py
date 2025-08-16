"""
Question Service - Business logic for question management
"""
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.db.models import Question
from app.schemas.question import QuestionCreate, QuestionSearch
from app.services.gemini_service import GeminiService
from app.crud.question import (
    create_question, get_question, get_questions_filtered,
    update_question, delete_question, search_questions_by_content
)

logger = logging.getLogger(__name__)


class QuestionService:
    """Service for question management and generation"""
    
    def __init__(self, db: Session):
        self.db = db
        self.gemini_service = GeminiService(db)
    
    def generate_and_store_questions(
        self,
        role: str,
        difficulty: str = "intermediate",
        question_type: str = "mixed",
        count: int = 5
    ) -> List[Question]:
        """Generate questions using Gemini API and store them"""
        
        # Generate questions using Gemini
        generated_questions = self.gemini_service.generate_questions(
            role=role,
            difficulty=difficulty,
            question_type=question_type,
            count=count
        )
        
        # Convert to database objects (avoiding duplicates)
        stored_questions = []
        for q_data in generated_questions:
            question_content = q_data['question'].strip()
            
            # Check if question already exists
            existing_question = self.db.query(Question).filter(
                Question.content == question_content
            ).first()
            
            if existing_question:
                logger.debug(f"Question already exists, using existing: {question_content[:50]}...")
                stored_questions.append(existing_question)
                continue
            
            # Create new question
            question_create = QuestionCreate(
                content=question_content,
                question_type=q_data['category'],
                role_category=role,
                difficulty_level=difficulty,
                expected_duration=q_data['duration'],
                generated_by='gemini_api'
            )
            
            question = create_question(self.db, question_create)
            stored_questions.append(question)
            logger.debug(f"Created new question: {question_content[:50]}...")
        
        return stored_questions
    
    def get_questions(self, search_params: QuestionSearch) -> List[Question]:
        """Get questions with filtering"""
        return get_questions_filtered(
            self.db,
            role_category=search_params.role_category,
            question_type=search_params.question_type,
            difficulty_level=search_params.difficulty_level,
            limit=search_params.limit,
            offset=search_params.offset
        )
    
    def get_question_by_id(self, question_id: int) -> Optional[Question]:
        """Get question by ID"""
        return get_question(self.db, question_id)
    
    def get_random_questions(
        self,
        role_category: Optional[str] = None,
        question_type: Optional[str] = None,
        difficulty_level: Optional[str] = None,
        count: int = 5
    ) -> List[Question]:
        """Get random questions for practice"""
        query = self.db.query(Question)
        
        # Apply filters
        if role_category:
            query = query.filter(Question.role_category == role_category)
        if question_type:
            query = query.filter(Question.question_type == question_type)
        if difficulty_level:
            query = query.filter(Question.difficulty_level == difficulty_level)
        
        # Get random questions (handle MySQL vs others)
        dialect_name = getattr(getattr(self.db, 'bind', None), 'dialect', None)
        dialect_name = getattr(dialect_name, 'name', '').lower() if dialect_name else ''
        random_func = func.rand() if dialect_name == 'mysql' else func.random()
        questions = query.order_by(random_func).limit(count).all()
        
        # If not enough questions found, generate new ones
        if len(questions) < count and role_category:
            needed = count - len(questions)
            new_questions = self.generate_and_store_questions(
                role=role_category,
                difficulty=difficulty_level or "intermediate",
                question_type=question_type or "mixed",
                count=needed
            )
            questions.extend(new_questions)
        
        return questions[:count]
    
    def search_questions(self, query: str, limit: int = 20) -> List[Question]:
        """Search questions by content"""
        return search_questions_by_content(self.db, query, limit)
    
    def create_question(self, question_data: QuestionCreate) -> Question:
        """Create new question"""
        return create_question(self.db, question_data)
    
    def update_question(self, question_id: int, update_data: Dict[str, Any]) -> Optional[Question]:
        """Update question"""
        return update_question(self.db, question_id, update_data)
    
    def delete_question(self, question_id: int) -> bool:
        """Delete question"""
        return delete_question(self.db, question_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get question database statistics"""
        total_questions = self.db.query(Question).count()
        
        # Count by role category
        role_stats = self.db.query(
            Question.role_category,
            func.count(Question.id).label('count')
        ).group_by(Question.role_category).all()
        
        # Count by question type
        type_stats = self.db.query(
            Question.question_type,
            func.count(Question.id).label('count')
        ).group_by(Question.question_type).all()
        
        # Count by difficulty
        difficulty_stats = self.db.query(
            Question.difficulty_level,
            func.count(Question.id).label('count')
        ).group_by(Question.difficulty_level).all()
        
        return {
            "total_questions": total_questions,
            "by_role": {role: count for role, count in role_stats},
            "by_type": {qtype: count for qtype, count in type_stats},
            "by_difficulty": {diff: count for diff, count in difficulty_stats}
        }
    
    def get_available_roles(self) -> List[str]:
        """Get available role categories"""
        roles = self.db.query(Question.role_category).distinct().all()
        return [role[0] for role in roles if role[0]]
    
    def get_questions_for_session(
        self,
        role: str,
        difficulty: str,
        session_type: str,
        count: int = 5,
        user_id: int = None,
        previous_sessions: List[Dict] = None
    ) -> List[Question]:
        """Get questions optimized for interview session with AI generation priority"""
        
        try:
            logger.info(f"Getting questions for {role} session (difficulty: {difficulty}, type: {session_type})")
            
            # Always try to generate fresh questions using Gemini API first for better user experience
            try:
                logger.info("Attempting to generate fresh questions using Gemini API")
                
                # Build context from previous sessions to avoid repetition
                context = {}
                if previous_sessions:
                    context["previous_sessions"] = previous_sessions[-2:]  # Last 2 sessions for context
                
                generated_questions = self.gemini_service.generate_questions(
                    role=role,
                    difficulty=difficulty,
                    question_type="mixed",
                    count=count,
                    context=context
                )
                
                if generated_questions and len(generated_questions) > 0:
                    logger.info(f"Successfully generated {len(generated_questions)} fresh questions")
                    
                    # Convert to Question objects and store in database
                    questions = []
                    for q_data in generated_questions:
                        # Try to find existing question first
                        existing_question = self.db.query(Question).filter(
                            Question.content.ilike(q_data['question'].strip())
                        ).first()
                        
                        if existing_question:
                            questions.append(existing_question)
                        else:
                            # Create new question
                            question_create = QuestionCreate(
                                content=q_data['question'].strip(),
                                question_type=q_data['category'],
                                role_category=role,
                                difficulty_level=difficulty,
                                expected_duration=q_data['duration'],
                                generated_by='gemini_api'
                            )
                            
                            try:
                                question = create_question(self.db, question_create)
                                questions.append(question)
                                logger.debug(f"Created new question: {q_data['question'][:50]}...")
                            except ValueError as e:
                                if "already exists" in str(e):
                                    # Find the existing question
                                    existing = self.db.query(Question).filter(
                                        Question.content.ilike(q_data['question'].strip())
                                    ).first()
                                    if existing:
                                        questions.append(existing)
                                else:
                                    raise e
                    
                    logger.info(f"Prepared {len(questions)} AI-generated questions for session")
                    return questions[:count]
                
            except Exception as e:
                logger.error(f"Failed to generate fresh questions: {str(e)}")
                logger.info("Falling back to existing database questions")
            
            # Fallback: Get existing questions from database
            logger.info("Using existing questions from database as fallback")
            existing_questions = self.get_random_questions(
                role_category=role,
                difficulty_level=difficulty,
                count=count
            )
            
            # Fallback: Get existing questions from database
            questions = self.get_random_questions(
                role_category=role,
                difficulty_level=difficulty,
                count=count
            )
            
            if len(questions) >= count:
                logger.info(f"Using {len(questions)} existing questions from database")
                return questions[:count]
            
            # If still not enough questions, generate more
            if len(questions) < count:
                logger.info(f"Only {len(questions)} questions in database, generating {count - len(questions)} more")
                needed = count - len(questions)
                
                try:
                    new_questions = self.generate_and_store_questions(
                        role=role,
                        difficulty=difficulty,
                        question_type="mixed",
                        count=needed
                    )
                    questions.extend(new_questions)
                    logger.info(f"Generated and added {len(new_questions)} new questions")
                except Exception as e:
                    logger.error(f"Failed to generate additional questions: {str(e)}")
            
            # Ensure we have the right number of questions
            questions = questions[:count]
            
            if len(questions) == 0:
                raise ValueError("No questions could be generated or retrieved")
            
            logger.info(f"Returning {len(questions)} questions for {role} session")
            return questions
            
        except Exception as e:
            logger.error(f"Error getting questions for session: {str(e)}")
            raise ValueError(f"Failed to get questions for session: {str(e)}")
    
    def get_contextual_followup_questions(
        self,
        role: str,
        previous_question: str,
        user_answer: str,
        difficulty: str = "intermediate",
        count: int = 2
    ) -> List[Question]:
        """Generate contextual follow-up questions based on user's answer"""
        
        try:
            logger.info(f"Generating contextual follow-up questions for {role}")
            
            # Generate contextual questions using Gemini
            generated_questions = self.gemini_service.generate_contextual_questions(
                role=role,
                previous_question=previous_question,
                user_answer=user_answer,
                difficulty=difficulty,
                count=count
            )
            
            # Convert to Question objects
            questions = []
            for q_data in generated_questions:
                # Create temporary Question object (don't store follow-ups in DB)
                question = Question(
                    content=q_data['question'].strip(),
                    question_type=q_data['category'],
                    role_category=role,
                    difficulty_level=difficulty,
                    expected_duration=q_data['duration'],
                    generated_by='gemini_contextual'
                )
                questions.append(question)
            
            logger.info(f"Generated {len(questions)} contextual follow-up questions")
            return questions
            
        except Exception as e:
            logger.error(f"Error generating contextual follow-up questions: {str(e)}")
            # Return empty list if contextual generation fails
            return []
    
    def _get_fallback_questions(self, role: str, difficulty: str, count: int) -> List[Question]:
        """Get fallback questions when database is empty"""
        try:
            # Create fallback questions
            fallback_data = [
                {
                    "content": "Tell me about yourself and your professional background.",
                    "question_type": "behavioral",
                    "role_category": role,
                    "difficulty_level": difficulty,
                    "expected_duration": 3,
                    "generated_by": "fallback"
                },
                {
                    "content": "Why are you interested in this position and our company?",
                    "question_type": "behavioral",
                    "role_category": role,
                    "difficulty_level": difficulty,
                    "expected_duration": 3,
                    "generated_by": "fallback"
                },
                {
                    "content": "Describe a challenging project or problem you worked on. How did you approach it?",
                    "question_type": "behavioral",
                    "role_category": role,
                    "difficulty_level": difficulty,
                    "expected_duration": 4,
                    "generated_by": "fallback"
                },
                {
                    "content": "What are your greatest strengths and how would they benefit this role?",
                    "question_type": "behavioral",
                    "role_category": role,
                    "difficulty_level": difficulty,
                    "expected_duration": 3,
                    "generated_by": "fallback"
                },
                {
                    "content": "Where do you see yourself in 5 years, and how does this role fit into your career plan?",
                    "question_type": "behavioral",
                    "role_category": role,
                    "difficulty_level": difficulty,
                    "expected_duration": 3,
                    "generated_by": "fallback"
                }
            ]
            
            # Create Question objects
            fallback_questions = []
            for q_data in fallback_data[:count]:
                question = Question(
                    content=q_data["content"],
                    question_type=q_data["question_type"],
                    role_category=q_data["role_category"],
                    difficulty_level=q_data["difficulty_level"],
                    expected_duration=q_data["expected_duration"],
                    generated_by=q_data["generated_by"]
                )
                fallback_questions.append(question)
            
            logger.info(f"Created {len(fallback_questions)} fallback questions for {role}")
            return fallback_questions
            
        except Exception as e:
            logger.error(f"Error creating fallback questions: {str(e)}")
            # Return a minimal set of questions
            return [
                Question(
                    content="Tell me about yourself and your background.",
                    question_type="behavioral",
                    role_category=role,
                    difficulty_level=difficulty,
                    expected_duration=3,
                    generated_by="emergency_fallback"
                )
            ]