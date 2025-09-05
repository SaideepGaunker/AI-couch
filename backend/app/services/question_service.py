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
from app.services.role_hierarchy_service import RoleHierarchyService
from app.schemas.role_hierarchy import HierarchicalRole
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
        self.role_hierarchy_service = RoleHierarchyService(db)
    
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
    
    def get_questions_by_tech_stack(
        self,
        tech_stack: str,
        difficulty: str = None,
        count: int = 10
    ) -> List[Question]:
        """Get questions filtered by technology stack"""
        
        try:
            logger.info(f"Getting questions for tech stack: {tech_stack}")
            
            # Query questions that have this tech stack in their difficulty tags
            query = self.db.query(Question).filter(
                Question.question_difficulty_tags.contains([tech_stack.lower().replace(" ", "-")])
            )
            
            if difficulty:
                query = query.filter(Question.difficulty_level == difficulty)
            
            questions = query.limit(count).all()
            
            logger.info(f"Found {len(questions)} questions for tech stack {tech_stack}")
            return questions
            
        except Exception as e:
            logger.error(f"Error getting questions by tech stack: {str(e)}")
            return []
    
    def update_question_tags_from_hierarchy(self) -> int:
        """Update existing questions with hierarchical tags based on role hierarchy"""
        
        try:
            logger.info("Updating question tags from role hierarchy")
            
            # Get all questions without hierarchical tags
            questions = self.db.query(Question).filter(
                or_(
                    Question.question_difficulty_tags.is_(None),
                    Question.question_difficulty_tags == []
                )
            ).all()
            
            updated_count = 0
            
            for question in questions:
                try:
                    # Try to match question role with hierarchy
                    role_parts = question.role_category.split(" - ")
                    main_role = role_parts[0] if role_parts else question.role_category
                    sub_role = role_parts[1] if len(role_parts) > 1 else None
                    
                    # Get tags from role hierarchy
                    question_tags = self.role_hierarchy_service.get_question_tags_for_role(
                        main_role, sub_role
                    )
                    tech_stacks = self.role_hierarchy_service.get_tech_stacks_for_role(
                        main_role, sub_role
                    )
                    
                    # Build tags list
                    tags = []
                    if sub_role:
                        tags.append(sub_role.lower().replace(" ", "-"))
                    if question_tags:
                        tags.extend(question_tags[:3])
                    if tech_stacks:
                        tags.extend([tech.lower().replace(" ", "-") for tech in tech_stacks[:2]])
                    
                    if tags:
                        question.question_difficulty_tags = list(set(tags))
                        updated_count += 1
                        
                except Exception as e:
                    logger.error(f"Error updating tags for question {question.id}: {str(e)}")
                    continue
            
            if updated_count > 0:
                self.db.commit()
                logger.info(f"Updated {updated_count} questions with hierarchical tags")
            
            return updated_count
            
        except Exception as e:
            logger.error(f"Error updating question tags from hierarchy: {str(e)}")
            self.db.rollback()
            return 0
    
    def get_questions_for_hierarchical_role(
        self,
        role_data: HierarchicalRole,
        difficulty: str,
        session_type: str,
        count: int = 5,
        user_id: int = None,
        previous_sessions: List[Dict] = None
    ) -> List[Question]:
        """Get questions optimized for hierarchical role structure"""
        
        try:
            logger.info(f"Getting questions for hierarchical role: {role_data.main_role}/{role_data.sub_role}/{role_data.specialization}")
            
            # Validate role combination
            if not self.role_hierarchy_service.validate_role_combination(
                role_data.main_role, role_data.sub_role, role_data.specialization
            ):
                logger.warning(f"Invalid role combination, falling back to main role: {role_data.main_role}")
                # Fall back to main role only
                role_data = HierarchicalRole(main_role=role_data.main_role)
            
            # Use role hierarchy service to get filtered questions
            questions = self.role_hierarchy_service.filter_questions_by_role(
                role_data, difficulty, session_type, count * 2  # Get more to have options
            )
            
            # If we have enough questions, return them
            if len(questions) >= count:
                logger.info(f"Found {len(questions)} existing questions for hierarchical role")
                return questions[:count]
            
            # Generate additional questions with hierarchical context
            needed = count - len(questions)
            logger.info(f"Need {needed} more questions, generating with hierarchical context")
            
            # Get tech stacks and question tags for this role
            tech_stacks = self.role_hierarchy_service.get_tech_stacks_for_role(
                role_data.main_role, role_data.sub_role
            )
            question_tags = self.role_hierarchy_service.get_question_tags_for_role(
                role_data.main_role, role_data.sub_role, role_data.specialization
            )
            
            # Build enhanced context for generation
            context = {
                "main_role": role_data.main_role,
                "sub_role": role_data.sub_role,
                "specialization": role_data.specialization,
                "tech_stacks": tech_stacks,
                "question_tags": question_tags,
                "session_type": session_type
            }
            
            if previous_sessions:
                context["previous_sessions"] = previous_sessions[-2:]
            
            # Generate questions with hierarchical context
            role_string = f"{role_data.main_role}"
            if role_data.sub_role:
                role_string += f" - {role_data.sub_role}"
            if role_data.specialization:
                role_string += f" ({role_data.specialization})"
            
            generated_questions = self.gemini_service.generate_questions(
                role=role_string,
                difficulty=difficulty,
                question_type=session_type,
                count=needed,
                context=context
            )
            
            # Convert and store generated questions with enhanced tags
            for q_data in generated_questions:
                question_create = QuestionCreate(
                    content=q_data['question'].strip(),
                    question_type=q_data['category'],
                    role_category=role_string,
                    difficulty_level=difficulty,
                    expected_duration=q_data['duration'],
                    generated_by='gemini_hierarchical'
                )
                
                try:
                    question = create_question(self.db, question_create)
                    
                    # Add hierarchical tags to question_difficulty_tags
                    tags = []
                    if role_data.sub_role:
                        tags.append(role_data.sub_role.lower().replace(" ", "-"))
                    if role_data.specialization:
                        tags.append(role_data.specialization.lower().replace(" ", "-"))
                    if tech_stacks:
                        tags.extend([tech.lower().replace(" ", "-") for tech in tech_stacks[:3]])  # Limit to 3 tech stacks
                    if question_tags:
                        tags.extend(question_tags[:3])  # Add role-specific question tags
                    
                    if tags:
                        question.question_difficulty_tags = list(set(tags))  # Remove duplicates
                        self.db.commit()
                    
                    questions.append(question)
                    logger.debug(f"Created hierarchical question with tags {tags}: {q_data['question'][:50]}...")
                    
                except Exception as e:
                    logger.error(f"Error creating hierarchical question: {str(e)}")
                    continue
            
            logger.info(f"Returning {len(questions)} questions for hierarchical role")
            return questions[:count]
            
        except Exception as e:
            logger.error(f"Error getting questions for hierarchical role: {str(e)}")
            # Fallback to basic role-based questions
            return self.get_questions_for_session(
                role=role_data.main_role,
                difficulty=difficulty,
                session_type=session_type,
                count=count,
                user_id=user_id,
                previous_sessions=previous_sessions
            )

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
    
    def get_questions_by_tech_stack(
        self,
        tech_stack: List[str],
        difficulty: str = "intermediate",
        count: int = 5
    ) -> List[Question]:
        """Get questions filtered by technology stack"""
        
        try:
            logger.info(f"Getting questions for tech stack: {tech_stack}")
            
            # Build query to find questions with matching tech stack tags
            query = self.db.query(Question).filter(
                Question.difficulty_level == difficulty
            )
            
            # Filter by tech stack in question_difficulty_tags
            tech_filters = []
            for tech in tech_stack:
                tech_tag = tech.lower().replace(" ", "_")
                tech_filters.append(Question.question_difficulty_tags.contains(tech_tag))
                # Also check role_category for broader matches
                tech_filters.append(Question.role_category.ilike(f"%{tech}%"))
            
            if tech_filters:
                query = query.filter(or_(*tech_filters))
            
            questions = query.limit(count).all()
            
            logger.info(f"Found {len(questions)} questions for tech stack {tech_stack}")
            return questions
            
        except Exception as e:
            logger.error(f"Error getting questions by tech stack: {str(e)}")
            return []
    
    def get_questions_by_specialization(
        self,
        specialization: str,
        difficulty: str = "intermediate",
        count: int = 5
    ) -> List[Question]:
        """Get questions filtered by specialization"""
        
        try:
            logger.info(f"Getting questions for specialization: {specialization}")
            
            specialization_tag = specialization.lower().replace(" ", "_")
            
            # Query for questions with matching specialization
            questions = self.db.query(Question).filter(
                and_(
                    Question.difficulty_level == difficulty,
                    or_(
                        Question.question_difficulty_tags.contains(specialization_tag),
                        Question.role_category.ilike(f"%{specialization}%")
                    )
                )
            ).limit(count).all()
            
            logger.info(f"Found {len(questions)} questions for specialization {specialization}")
            return questions
            
        except Exception as e:
            logger.error(f"Error getting questions by specialization: {str(e)}")
            return []
    
    def update_question_tags(
        self,
        question_id: int,
        tags: List[str]
    ) -> bool:
        """Update question difficulty tags for better hierarchical filtering"""
        
        try:
            question = self.get_question_by_id(question_id)
            if not question:
                logger.error(f"Question {question_id} not found")
                return False
            
            # Normalize tags
            normalized_tags = [tag.lower().replace(" ", "_") for tag in tags]
            
            # Update tags
            question.question_difficulty_tags = normalized_tags
            self.db.commit()
            
            logger.info(f"Updated question {question_id} tags: {normalized_tags}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating question tags: {str(e)}")
            self.db.rollback()
            return False
    
    def get_questions_with_distribution(
        self,
        role: str,
        difficulty: str,
        session_type: str,
        distribution: Dict[str, int]
    ) -> List[Question]:
        """
        Get questions with proper type distribution for quick tests
        
        Args:
            role: Target role for questions
            difficulty: Difficulty level
            session_type: Type of session
            distribution: Required distribution (theory, coding, aptitude counts)
            
        Returns:
            List of questions matching the distribution requirements
        """
        try:
            logger.info(f"Getting questions with distribution: {distribution} for {role}")
            
            questions = []
            
            # Generate questions for each type based on distribution
            for question_type, count in distribution.items():
                if count > 0:
                    logger.info(f"Generating {count} {question_type} questions")
                    
                    # Map distribution types to question categories
                    if question_type == 'theory':
                        category = 'theoretical'
                    elif question_type == 'coding':
                        category = 'technical'
                    elif question_type == 'aptitude':
                        category = 'problem-solving'
                    else:
                        category = 'mixed'
                    
                    # Try to get existing questions first
                    existing_questions = self.get_random_questions(
                        role_category=role,
                        question_type=category,
                        difficulty_level=difficulty,
                        count=count
                    )
                    
                    if len(existing_questions) >= count:
                        questions.extend(existing_questions[:count])
                        logger.info(f"Used {count} existing {question_type} questions")
                    else:
                        # Use existing questions and generate the rest
                        questions.extend(existing_questions)
                        needed = count - len(existing_questions)
                        
                        logger.info(f"Need to generate {needed} more {question_type} questions")
                        
                        # Generate additional questions with specific type
                        generated_questions = self.gemini_service.generate_questions(
                            role=role,
                            difficulty=difficulty,
                            question_type=category,
                            count=needed
                        )
                        
                        # Convert and store generated questions
                        for q_data in generated_questions:
                            question_create = QuestionCreate(
                                content=q_data['question'].strip(),
                                question_type=category,
                                role_category=role,
                                difficulty_level=difficulty,
                                expected_duration=q_data['duration'],
                                generated_by='gemini_distributed'
                            )
                            
                            try:
                                question = create_question(self.db, question_create)
                                questions.append(question)
                                logger.debug(f"Created {question_type} question: {q_data['question'][:50]}...")
                            except Exception as e:
                                logger.error(f"Error creating {question_type} question: {str(e)}")
                                continue
            
            # Validate the distribution
            from app.services.question_distribution_calculator import QuestionDistributionCalculator
            distribution_calculator = QuestionDistributionCalculator()
            
            # Convert questions to format expected by validator
            questions_for_validation = []
            for q in questions:
                questions_for_validation.append({
                    'category': q.question_type,
                    'question': q.content
                })
            
            validation_result = distribution_calculator.validate_distribution(
                questions_for_validation, distribution
            )
            
            if not validation_result['is_valid']:
                logger.warning(f"Distribution validation failed: {validation_result['deviations']}")
                # Try to adjust by regenerating some questions
                # For now, just log the issue and return what we have
            else:
                logger.info(f"Distribution validation passed with score: {validation_result['validation_score']}%")
            
            logger.info(f"Returning {len(questions)} questions with distribution: "
                       f"Theory: {sum(1 for q in questions if q.question_type in ['theoretical', 'theory'])}, "
                       f"Coding: {sum(1 for q in questions if q.question_type in ['technical', 'coding'])}, "
                       f"Aptitude: {sum(1 for q in questions if q.question_type in ['problem-solving', 'aptitude'])}")
            
            return questions
            
        except Exception as e:
            logger.error(f"Error getting questions with distribution: {str(e)}")
            # Fallback to regular question generation
            total_count = sum(distribution.values())
            return self.get_questions_for_session(
                role=role,
                difficulty=difficulty,
                session_type=session_type,
                count=total_count
            )

    def enhance_existing_questions_with_hierarchy(self) -> int:
        """Enhance existing questions with hierarchical tags based on role categories"""
        
        try:
            logger.info("Enhancing existing questions with hierarchical tags")
            
            # Get all questions without tags
            questions = self.db.query(Question).filter(
                or_(
                    Question.question_difficulty_tags.is_(None),
                    Question.question_difficulty_tags == []
                )
            ).all()
            
            enhanced_count = 0
            
            for question in questions:
                tags = []
                
                # Extract tags from role_category
                if question.role_category:
                    role_parts = question.role_category.lower().split()
                    tags.extend([part.replace(" ", "_") for part in role_parts])
                
                # Add common tech stack tags based on role category
                role_category_lower = (question.role_category or "").lower()
                
                if "frontend" in role_category_lower or "react" in role_category_lower:
                    tags.extend(["react", "javascript", "html", "css"])
                elif "backend" in role_category_lower or "python" in role_category_lower:
                    tags.extend(["python", "api", "database"])
                elif "data" in role_category_lower or "ml" in role_category_lower:
                    tags.extend(["python", "machine_learning", "data_analysis"])
                elif "marketing" in role_category_lower:
                    tags.extend(["digital_marketing", "analytics"])
                
                # Remove duplicates and update
                if tags:
                    unique_tags = list(set(tags))
                    question.question_difficulty_tags = unique_tags
                    enhanced_count += 1
            
            self.db.commit()
            logger.info(f"Enhanced {enhanced_count} questions with hierarchical tags")
            return enhanced_count
            
        except Exception as e:
            logger.error(f"Error enhancing questions with hierarchy: {str(e)}")
            self.db.rollback()
            return 0