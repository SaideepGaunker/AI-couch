"""
Gemini AI Service for question generation and answer evaluation
"""
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import google.generativeai as genai
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Question, User
from app.schemas.question import QuestionCreate

logger = logging.getLogger(__name__)

# Configure Gemini API only if an API key is provided
if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your-gemini-api-key-here":
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        logger.info("Gemini API configured successfully")
    except Exception as e:
        logger.error(f"Failed to configure Gemini API: {str(e)}")
        # Fallback: leave unconfigured to force offline behavior
        pass
else:
    logger.warning("No valid Gemini API key provided, using fallback mode")


class GeminiService:
    """Service for interacting with Google Gemini API"""
    
    def __init__(self, db: Session):
        self.db = db
        try:
            # Create model only when API is available
            if settings.GEMINI_API_KEY:
                # Use the working model first, fallback to others
                model_names = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.0-pro', 'gemini-pro']
                self.model = None
                
                for model_name in model_names:
                    try:
                        self.model = genai.GenerativeModel(model_name)
                        logger.info(f"Gemini model '{model_name}' initialized successfully")
                        break
                    except Exception as model_error:
                        logger.warning(f"Failed to initialize model '{model_name}': {str(model_error)}")
                        continue
                
                if not self.model:
                    logger.error("All Gemini model attempts failed, using fallback mode")
            else:
                self.model = None
                logger.info("Gemini model not available, using fallback mode")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {str(e)}")
            self.model = None
        
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = timedelta(hours=1)
    
    def generate_questions(
        self, 
        role: str, 
        difficulty: str = "intermediate", 
        question_type: str = "mixed",
        count: int = 5,
        context: Dict[str, Any] = None,
        previous_answers: List[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate interview questions using Gemini API with context awareness"""
        
        # Build cache key including context for better caching
        context_key = ""
        if context or previous_answers:
            context_key = f"_ctx_{hash(str(context or {}))}_ans_{hash(str(previous_answers or []))}"
        cache_key = f"{role}_{difficulty}_{question_type}_{count}{context_key}"
        
        # Skip cache for contextual questions to ensure freshness
        if not context and not previous_answers and self._is_cached(cache_key):
            logger.info(f"Returning cached questions for {cache_key}")
            return self.cache[cache_key]["data"]
        
        # Force Gemini API usage - only fallback if API completely fails
        if not self.model or not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your-gemini-api-key-here":
            logger.error("Gemini API not configured properly")
            raise RuntimeError("Gemini API is required for question generation")
        
        try:
            logger.info(f"Generating questions using Gemini API for {role} with context: {bool(context or previous_answers)}")
            
            # Build contextual prompt
            prompt = self._build_contextual_question_prompt(
                role, difficulty, question_type, count, context, previous_answers
            )
            
            # Enhanced generation config for better contextual responses
            generation_config = {
                "temperature": 0.8,  # Higher for more creative contextual questions
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 3072,
            }
            
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            response_text = ""
            if hasattr(response, 'text') and response.text:
                response_text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                if hasattr(response.candidates[0], 'content'):
                    response_text = response.candidates[0].content.parts[0].text
            
            questions_data = self._parse_questions_response(response_text)
            
            if questions_data and len(questions_data) > 0:
                logger.info(f"Successfully generated {len(questions_data)} contextual questions via Gemini API")
                
                # Only cache non-contextual questions
                if not context and not previous_answers:
                    self._cache_data(cache_key, questions_data)
                
                # Store questions in database (with duplicate prevention)
                self._store_questions(questions_data, role, difficulty, question_type)
                
                return questions_data
            else:
                logger.error("Gemini API returned empty questions")
                raise RuntimeError("Failed to generate questions from Gemini API")
                
        except Exception as e:
            logger.error(f"Error generating questions with Gemini API: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            if hasattr(e, 'response'):
                logger.error(f"API Response: {e.response}")
            
            # Only use fallback for non-contextual questions as last resort
            if not context and not previous_answers:
                logger.warning("Using fallback questions as last resort")
                fallback_questions = self._get_fallback_questions(role, difficulty, question_type, count)
                self._cache_data(cache_key, fallback_questions)
                return fallback_questions
            else:
                # For contextual questions, we must have AI generation
                raise RuntimeError(f"Failed to generate contextual questions: {str(e)}")
    
    def generate_contextual_questions(
        self,
        role: str,
        previous_question: str,
        user_answer: str,
        difficulty: str = "intermediate",
        count: int = 2
    ) -> List[Dict[str, Any]]:
        """Generate follow-up questions based on user's previous answer"""
        
        try:
            logger.info(f"Generating contextual follow-up questions for {role}")
            
            prompt = self._build_followup_question_prompt(
                role, previous_question, user_answer, difficulty, count
            )
            
            generation_config = {
                "temperature": 0.9,  # High creativity for follow-ups
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
            
            response = self.model.generate_content(prompt, generation_config=generation_config)
            
            response_text = ""
            if hasattr(response, 'text') and response.text:
                response_text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                if hasattr(response.candidates[0], 'content'):
                    response_text = response.candidates[0].content.parts[0].text
            
            questions_data = self._parse_questions_response(response_text)
            
            if questions_data and len(questions_data) > 0:
                logger.info(f"Generated {len(questions_data)} contextual follow-up questions")
                return questions_data
            else:
                logger.warning("No contextual questions generated, creating generic follow-up")
                return self._create_generic_followup(previous_question, user_answer, role)
                
        except Exception as e:
            logger.error(f"Error generating contextual questions: {str(e)}")
            return self._create_generic_followup(previous_question, user_answer, role)
    
    def evaluate_answer(
        self, 
        question: str, 
        answer: str, 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate user's answer using Gemini API"""
        
        try:
            prompt = self._build_evaluation_prompt(question, answer, context)
            
            if not self.model:
                raise RuntimeError("Gemini model not available")
            
            generation_config = {
                "temperature": 0.3,
                "top_p": 0.8,
                "max_output_tokens": 1024,
            }
            
            response = self.model.generate_content(prompt, generation_config=generation_config)
            
            response_text = ""
            if hasattr(response, 'text') and response.text:
                response_text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                if hasattr(response.candidates[0], 'content'):
                    response_text = response.candidates[0].content.parts[0].text
            
            evaluation = self._parse_evaluation_response(response_text)
            
            return evaluation
            
        except Exception as e:
            logger.error(f"Error evaluating answer: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            return self._get_fallback_evaluation()
    
    def generate_feedback(
        self, 
        performance_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate personalized feedback based on performance data"""
        
        try:
            prompt = self._build_feedback_prompt(performance_data)
            
            if not self.model:
                raise RuntimeError("Gemini model not available")
            response = self.model.generate_content(prompt)
            feedback = self._parse_feedback_response(getattr(response, 'text', '') or '')
            
            return feedback
            
        except Exception as e:
            logger.error(f"Error generating feedback: {str(e)}")
            return self._get_fallback_feedback()
    
    def generate_follow_up_questions(
        self, 
        original_question: str, 
        user_answer: str, 
        context: Dict[str, Any]
    ) -> List[str]:
        """Generate follow-up questions based on user's answer"""
        
        try:
            prompt = self._build_followup_prompt(original_question, user_answer, context)
            
            if not self.model:
                raise RuntimeError("Gemini model not available")
            response = self.model.generate_content(prompt)
            follow_ups = self._parse_followup_response(getattr(response, 'text', '') or '')
            
            return follow_ups
            
        except Exception as e:
            logger.error(f"Error generating follow-up questions: {str(e)}")
            return []
    
    def _build_question_prompt(
        self, 
        role: str, 
        difficulty: str, 
        question_type: str, 
        count: int
    ) -> str:
        """Build prompt for question generation"""
        
        type_instructions = {
            "behavioral": "behavioral and situational questions that assess soft skills, teamwork, and problem-solving approach",
            "technical": "technical questions that test domain-specific knowledge and skills",
            "mixed": "a mix of behavioral, technical, and situational questions"
        }
        
        difficulty_instructions = {
            "beginner": "entry-level questions suitable for candidates with 0-2 years of experience",
            "intermediate": "mid-level questions for candidates with 2-5 years of experience", 
            "advanced": "senior-level questions for experienced candidates with 5+ years"
        }
        
        prompt = f"""
        You are an expert interview coach and recruiter. Generate {count} realistic interview questions for a {role} position.

        Requirements:
        - Difficulty level: {difficulty_instructions.get(difficulty, 'intermediate')}
        - Question type: {type_instructions.get(question_type, 'mixed')}
        - Questions should be realistic and commonly asked in actual interviews
        - Include a mix of open-ended and specific questions
        - Questions should be relevant to current industry standards and practices

        For each question, provide:
        1. The question text
        2. Question category (behavioral, technical, situational, etc.)
        3. Expected answer duration in minutes
        4. Key points that a good answer should cover

        Format your response as a JSON array with this structure:
        [
            {{
                "question": "Question text here",
                "category": "behavioral|technical|situational",
                "duration": 3,
                "key_points": ["point 1", "point 2", "point 3"]
            }}
        ]

        Role: {role}
        Generate questions now:
        """
        
        return prompt
    
    def _build_contextual_question_prompt(
        self,
        role: str,
        difficulty: str,
        question_type: str,
        count: int,
        context: Dict[str, Any] = None,
        previous_answers: List[Dict[str, Any]] = None
    ) -> str:
        """Build contextual prompt for question generation based on previous answers"""
        
        type_instructions = {
            "behavioral": "behavioral and situational questions that assess soft skills, teamwork, and problem-solving approach",
            "technical": "technical questions that test domain-specific knowledge and skills",
            "mixed": "a mix of behavioral, technical, and situational questions"
        }
        
        difficulty_instructions = {
            "beginner": "entry-level questions suitable for candidates with 0-2 years of experience",
            "intermediate": "mid-level questions for candidates with 2-5 years of experience", 
            "advanced": "senior-level questions for experienced candidates with 5+ years"
        }
        
        # Build context section
        context_section = ""
        if previous_answers:
            context_section = "\n\nPREVIOUS INTERVIEW CONTEXT:\n"
            for i, qa in enumerate(previous_answers[-3:], 1):  # Use last 3 Q&As for context
                context_section += f"Q{i}: {qa.get('question', '')}\n"
                context_section += f"A{i}: {qa.get('answer', '')}\n\n"
            
            context_section += """
            Based on the candidate's previous answers, generate follow-up questions that:
            - Dive deeper into topics they mentioned
            - Explore specific examples or projects they referenced
            - Ask for clarification or more details about their experience
            - Build upon their stated skills and interests
            - Create a natural conversation flow
            """
        
        if context:
            context_section += f"\n\nADDITIONAL CONTEXT:\n{context}\n"
        
        prompt = f"""
        You are an expert interview coach conducting a dynamic interview for a {role} position.
        
        Requirements:
        - Difficulty level: {difficulty_instructions.get(difficulty, 'intermediate')}
        - Question type: {type_instructions.get(question_type, 'mixed')}
        - Generate {count} questions that feel natural and conversational
        - Questions should be unique and avoid repetition
        - Focus on creating engaging, insightful questions
        
        {context_section}
        
        For each question, provide:
        1. The question text (make it conversational and specific)
        2. Question category (behavioral, technical, situational, etc.)
        3. Expected answer duration in minutes
        4. Key points that a good answer should cover
        
        Format your response as a JSON array:
        [
            {{
                "question": "Question text here",
                "category": "behavioral|technical|situational",
                "duration": 3,
                "key_points": ["point 1", "point 2", "point 3"]
            }}
        ]
        
        Generate contextual questions now:
        """
        
        return prompt
    
    def _build_followup_question_prompt(
        self,
        role: str,
        previous_question: str,
        user_answer: str,
        difficulty: str,
        count: int
    ) -> str:
        """Build prompt for generating follow-up questions based on specific answer"""
        
        prompt = f"""
        You are an expert interviewer conducting a {role} interview. Based on the candidate's answer, generate {count} natural follow-up questions.
        
        PREVIOUS QUESTION: {previous_question}
        
        CANDIDATE'S ANSWER: {user_answer}
        
        Generate follow-up questions that:
        - Dive deeper into specific points they mentioned
        - Ask for concrete examples or details
        - Explore the technical or behavioral aspects further
        - Feel like a natural conversation progression
        - Are appropriate for {difficulty} level candidates
        
        Examples of good follow-ups:
        - If they mention "projects" → "Tell me about one specific project you're most proud of"
        - If they mention "database work" → "What database technologies have you worked with?"
        - If they mention "team collaboration" → "Can you give me an example of how you handled a team conflict?"
        
        Format your response as a JSON array:
        [
            {{
                "question": "Follow-up question text here",
                "category": "behavioral|technical|situational",
                "duration": 3,
                "key_points": ["point 1", "point 2", "point 3"]
            }}
        ]
        
        Generate follow-up questions now:
        """
        
        return prompt
    
    def _build_evaluation_prompt(
        self, 
        question: str, 
        answer: str, 
        context: Dict[str, Any]
    ) -> str:
        """Build prompt for answer evaluation"""
        
        user_role = context.get('role', 'job_seeker')
        experience_level = context.get('experience_level', 'intermediate')
        target_role = context.get('target_role', 'general')
        
        prompt = f"""
        You are an expert interview evaluator. Evaluate the following interview answer.

        Question: {question}
        
        Candidate's Answer: {answer}
        
        Context:
        - Candidate Role: {user_role}
        - Experience Level: {experience_level}
        - Target Position: {target_role}

        Evaluate the answer on these criteria:
        1. Content Quality (0-100): Relevance, completeness, accuracy
        2. Communication (0-100): Clarity, structure, professionalism
        3. Depth (0-100): Level of detail and insight
        4. Relevance (0-100): How well it addresses the question

        Provide:
        - Overall score (0-100)
        - Scores for each criterion
        - Specific strengths (2-3 points)
        - Areas for improvement (2-3 points)
        - Actionable suggestions for better answers

        Format as JSON:
        {{
            "overall_score": 85,
            "scores": {{
                "content_quality": 80,
                "communication": 90,
                "depth": 85,
                "relevance": 85
            }},
            "strengths": ["strength 1", "strength 2"],
            "improvements": ["improvement 1", "improvement 2"],
            "suggestions": ["suggestion 1", "suggestion 2"]
        }}
        """
        
        return prompt
    
    def _build_feedback_prompt(self, performance_data: Dict[str, Any]) -> str:
        """Build prompt for personalized feedback generation"""
        
        prompt = f"""
        You are an expert interview coach. Generate personalized feedback based on the candidate's overall performance.

        Performance Data:
        {json.dumps(performance_data, indent=2)}

        Generate comprehensive feedback including:
        1. Overall performance summary
        2. Key strengths to leverage
        3. Priority areas for improvement
        4. Specific action items and practice recommendations
        5. Motivational closing message

        Format as JSON:
        {{
            "summary": "Overall performance summary",
            "strengths": ["strength 1", "strength 2"],
            "improvements": ["area 1", "area 2"],
            "action_items": ["action 1", "action 2"],
            "motivation": "Encouraging message"
        }}
        """
        
        return prompt
    
    def _build_followup_prompt(
        self, 
        original_question: str, 
        user_answer: str, 
        context: Dict[str, Any]
    ) -> str:
        """Build prompt for follow-up question generation"""
        
        prompt = f"""
        You are an experienced interviewer. Based on the candidate's answer, generate 2-3 relevant follow-up questions.

        Original Question: {original_question}
        Candidate's Answer: {user_answer}
        
        Generate follow-up questions that:
        - Dig deeper into the candidate's response
        - Clarify any ambiguous points
        - Explore related scenarios or experiences
        - Test the depth of their knowledge/experience

        Format as JSON array:
        ["follow-up question 1", "follow-up question 2", "follow-up question 3"]
        """
        
        return prompt
    
    def _parse_questions_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse Gemini response for questions"""
        try:
            # Clean the response text
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            
            questions = json.loads(cleaned_text)
            
            # Validate and clean questions
            validated_questions = []
            for q in questions:
                if isinstance(q, dict) and 'question' in q:
                    validated_questions.append({
                        'question': q.get('question', ''),
                        'category': q.get('category', 'general'),
                        'duration': q.get('duration', 3),
                        'key_points': q.get('key_points', [])
                    })
            
            return validated_questions
            
        except Exception as e:
            logger.error(f"Error parsing questions response: {str(e)}")
            return []
    
    def _parse_evaluation_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini response for answer evaluation"""
        try:
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            
            evaluation = json.loads(cleaned_text)
            return evaluation
            
        except Exception as e:
            logger.error(f"Error parsing evaluation response: {str(e)}")
            return self._get_fallback_evaluation()
    
    def _parse_feedback_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini response for feedback"""
        try:
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            
            feedback = json.loads(cleaned_text)
            return feedback
            
        except Exception as e:
            logger.error(f"Error parsing feedback response: {str(e)}")
            return self._get_fallback_feedback()
    
    def _parse_followup_response(self, response_text: str) -> List[str]:
        """Parse Gemini response for follow-up questions"""
        try:
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            
            follow_ups = json.loads(cleaned_text)
            return follow_ups if isinstance(follow_ups, list) else []
            
        except Exception as e:
            logger.error(f"Error parsing follow-up response: {str(e)}")
            return []
    
    def _store_questions(
        self, 
        questions_data: List[Dict[str, Any]], 
        role: str, 
        difficulty: str, 
        question_type: str
    ):
        """Store generated questions in database (avoiding duplicates)"""
        try:
            stored_count = 0
            duplicate_count = 0
            
            for q_data in questions_data:
                question_content = q_data['question'].strip()
                
                # Skip empty questions
                if not question_content:
                    continue
                
                # Normalize question content for better duplicate detection
                normalized_content = self._normalize_question_content(question_content)
                
                # Check for exact duplicates (case-insensitive)
                existing_question = self.db.query(Question).filter(
                    Question.content.ilike(question_content)
                ).first()
                
                if existing_question:
                    duplicate_count += 1
                    logger.debug(f"Exact duplicate found, skipping: {question_content[:50]}...")
                    continue
                
                # Check for similar questions using normalized content
                # Look for questions that start with similar text (first 80 characters)
                similar_prefix = normalized_content[:80] if len(normalized_content) > 80 else normalized_content
                similar_question = self.db.query(Question).filter(
                    Question.content.ilike(f"{similar_prefix}%")
                ).first()
                
                if similar_question:
                    # Additional check: calculate similarity ratio
                    similarity_ratio = self._calculate_similarity(
                        normalized_content, 
                        similar_question.content.lower().strip()
                    )
                    
                    # If similarity is above 70%, consider it a duplicate
                    if similarity_ratio > 0.7:
                        duplicate_count += 1
                        logger.debug(f"Similar question found (similarity: {similarity_ratio:.2f}), skipping: {question_content[:50]}...")
                        continue
                
                # Check for questions with same role, type, and very similar content
                role_type_questions = self.db.query(Question).filter(
                    Question.role_category == role,
                    Question.question_type == q_data['category']
                ).all()
                
                is_duplicate = False
                for existing in role_type_questions:
                    existing_normalized = self._normalize_question_content(existing.content)
                    similarity = self._calculate_similarity(normalized_content, existing_normalized)
                    
                    if similarity > 0.75:  # High similarity threshold for same role/type
                        duplicate_count += 1
                        logger.debug(f"Role-specific duplicate found (similarity: {similarity:.2f}), skipping: {question_content[:50]}...")
                        is_duplicate = True
                        break
                
                if is_duplicate:
                    continue
                
                # Store new question
                question = Question(
                    content=question_content,
                    question_type=q_data['category'],
                    role_category=role,
                    difficulty_level=difficulty,
                    expected_duration=q_data['duration'],
                    generated_by='gemini_api'
                )
                self.db.add(question)
                stored_count += 1
                logger.debug(f"Storing new question: {question_content[:50]}...")
            
            if stored_count > 0:
                self.db.commit()
                logger.info(f"Stored {stored_count} new questions in database")
            
            if duplicate_count > 0:
                logger.info(f"Skipped {duplicate_count} duplicate/similar questions")
            
        except Exception as e:
            logger.error(f"Error storing questions: {str(e)}")
            self.db.rollback()
    
    def _normalize_question_content(self, content: str) -> str:
        """Normalize question content for better duplicate detection"""
        import re
        
        # Convert to lowercase
        normalized = content.lower().strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove common punctuation that doesn't affect meaning
        normalized = re.sub(r'[.!?;,]', '', normalized)
        
        # Remove common question starters that might vary
        starters = [
            'can you ', 'could you ', 'would you ', 'will you ',
            'please ', 'tell me ', 'describe ', 'explain ',
            'what is ', 'what are ', 'how do ', 'how would ',
            'why do ', 'why would ', 'when do ', 'where do '
        ]
        
        for starter in starters:
            if normalized.startswith(starter):
                normalized = normalized[len(starter):]
                break
        
        return normalized.strip()
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity ratio between two texts using multiple methods"""
        if not text1 or not text2:
            return 0.0
        
        # Method 1: Word-based Jaccard similarity
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        jaccard_similarity = len(words1.intersection(words2)) / len(words1.union(words2))
        
        # Method 2: Character-based similarity (for catching minor variations)
        chars1 = set(text1.replace(' ', ''))
        chars2 = set(text2.replace(' ', ''))
        char_similarity = len(chars1.intersection(chars2)) / len(chars1.union(chars2)) if chars1.union(chars2) else 0
        
        # Method 3: Length-based similarity check
        len1, len2 = len(text1), len(text2)
        length_ratio = min(len1, len2) / max(len1, len2) if max(len1, len2) > 0 else 0
        
        # Method 4: Common substring check for question variations
        shorter, longer = (text1, text2) if len1 < len2 else (text2, text1)
        substring_ratio = 0
        if len(shorter) > 10:
            shorter_words = shorter.split()
            longer_words = longer.split()
            common_words = sum(1 for word in shorter_words if word in longer_words)
            substring_ratio = common_words / len(shorter_words) if shorter_words else 0
        
        # Combine similarities with weights optimized for question detection
        combined_similarity = (
            jaccard_similarity * 0.4 +
            substring_ratio * 0.3 +
            char_similarity * 0.2 +
            length_ratio * 0.1
        )
        
        return combined_similarity
    
    def _create_generic_followup(
        self, 
        previous_question: str, 
        user_answer: str, 
        role: str
    ) -> List[Dict[str, Any]]:
        """Create generic follow-up questions when AI generation fails"""
        
        # Analyze the answer for keywords to create relevant follow-ups
        answer_lower = user_answer.lower()
        
        followups = []
        
        # Check for common topics and create relevant follow-ups
        if any(word in answer_lower for word in ['project', 'projects', 'worked on', 'built', 'developed']):
            followups.append({
                "question": "Can you tell me more about one specific project you mentioned?",
                "category": "behavioral",
                "duration": 4,
                "key_points": ["Project details", "Your role", "Challenges faced", "Results achieved"]
            })
        
        if any(word in answer_lower for word in ['team', 'collaborate', 'worked with', 'colleagues']):
            followups.append({
                "question": "How do you typically handle collaboration and communication in team settings?",
                "category": "behavioral", 
                "duration": 3,
                "key_points": ["Communication style", "Conflict resolution", "Team dynamics"]
            })
        
        if any(word in answer_lower for word in ['challenge', 'difficult', 'problem', 'issue']):
            followups.append({
                "question": "Walk me through how you approach problem-solving when facing technical challenges.",
                "category": "behavioral",
                "duration": 4,
                "key_points": ["Problem analysis", "Solution approach", "Learning outcomes"]
            })
        
        if any(word in answer_lower for word in ['technology', 'tech', 'programming', 'coding', 'development']):
            followups.append({
                "question": f"What specific technologies or tools do you prefer working with in {role} roles?",
                "category": "technical",
                "duration": 3,
                "key_points": ["Technology preferences", "Experience level", "Learning approach"]
            })
        
        # If no specific topics found, use generic follow-ups
        if not followups:
            followups = [
                {
                    "question": "Can you elaborate on that with a specific example?",
                    "category": "behavioral",
                    "duration": 3,
                    "key_points": ["Specific example", "Context", "Your actions", "Results"]
                },
                {
                    "question": "What did you learn from that experience?",
                    "category": "behavioral",
                    "duration": 2,
                    "key_points": ["Key learnings", "Personal growth", "Application to future"]
                }
            ]
        
        return followups[:2]  # Return max 2 follow-ups
    
    def generate_comprehensive_feedback(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive feedback with specific recommendations and areas for improvement"""
        
        try:
            logger.info("Generating comprehensive feedback using Gemini API")
            
            prompt = self._build_comprehensive_feedback_prompt(performance_data)
            
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 3072,
            }
            
            response = self.model.generate_content(prompt, generation_config=generation_config)
            
            response_text = ""
            if hasattr(response, 'text') and response.text:
                response_text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                if hasattr(response.candidates[0], 'content'):
                    response_text = response.candidates[0].content.parts[0].text
            
            feedback = self._parse_comprehensive_feedback_response(response_text)
            
            if feedback:
                logger.info("Successfully generated comprehensive feedback")
                return feedback
            else:
                logger.warning("Failed to parse comprehensive feedback, using fallback")
                return self._get_fallback_comprehensive_feedback(performance_data)
                
        except Exception as e:
            logger.error(f"Error generating comprehensive feedback: {str(e)}")
            return self._get_fallback_comprehensive_feedback(performance_data)
    
    def _build_comprehensive_feedback_prompt(self, performance_data: Dict[str, Any]) -> str:
        """Build prompt for comprehensive feedback generation"""
        
        session_info = performance_data.get('session_info', {})
        user_info = performance_data.get('user_info', {})
        scores = performance_data.get('performance_scores', {})
        qa_data = performance_data.get('questions_and_answers', [])
        
        # Build questions and answers section
        qa_section = ""
        for i, qa in enumerate(qa_data, 1):
            qa_section += f"""
Question {i}: {qa['question']}
Answer: {qa['answer']}
Content Score: {qa['content_score']}/100
Body Language Score: {qa['body_language_score']}/100
Tone Score: {qa['tone_score']}/100
"""
        
        prompt = f"""
You are an expert interview coach and career advisor. Analyze this interview performance and provide comprehensive, actionable feedback.

INTERVIEW SESSION DETAILS:
- Target Role: {session_info.get('target_role', 'Unknown')}
- Session Type: {session_info.get('session_type', 'mixed')}
- Duration: {session_info.get('duration', 30)} minutes
- Questions Answered: {session_info.get('questions_answered', 0)}

CANDIDATE PROFILE:
- Current Role: {user_info.get('role', 'Unknown')}
- Experience Level: {user_info.get('experience_level', 'intermediate')}

PERFORMANCE SCORES:
- Overall Score: {scores.get('overall_score', 0):.1f}/100
- Content Quality: {scores.get('content_quality', 0):.1f}/100
- Body Language: {scores.get('body_language', 0):.1f}/100
- Voice & Tone: {scores.get('voice_tone', 0):.1f}/100

QUESTIONS AND ANSWERS:
{qa_section}

Please provide detailed feedback in the following JSON format:
{{
    "areas_for_improvement": [
        "Specific area 1 with actionable advice",
        "Specific area 2 with actionable advice",
        "Specific area 3 with actionable advice"
    ],
    "recommendations": [
        "Specific recommendation 1 with clear action steps",
        "Specific recommendation 2 with clear action steps",
        "Specific recommendation 3 with clear action steps"
    ],
    "detailed_analysis": "A comprehensive paragraph analyzing the overall performance, highlighting strengths and weaknesses with specific examples from the answers provided.",
    "question_feedback": [
        {{
            "question": "Question text",
            "feedback": "Specific feedback on this answer",
            "improvement_tip": "How to improve this type of answer"
        }}
    ]
}}

GUIDELINES:
1. Be specific and actionable in your feedback
2. Reference actual answers when possible
3. Provide concrete steps for improvement
4. Consider the target role and session type
5. Balance constructive criticism with encouragement
6. Focus on skills like technical knowledge, communication, STAR method, confidence, etc.
7. For areas of improvement, be specific about what skills need work (e.g., "database optimization knowledge", "behavioral storytelling", "technical explanation clarity")
8. For recommendations, provide specific actions (e.g., "Practice explaining technical concepts to non-technical audiences", "Prepare 3-5 STAR method examples for behavioral questions")

Generate comprehensive feedback now:
"""
        
        return prompt
    
    def _parse_comprehensive_feedback_response(self, response_text: str) -> Dict[str, Any]:
        """Parse comprehensive feedback response from Gemini"""
        try:
            # Clean the response text
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            
            feedback = json.loads(cleaned_text)
            
            # Validate required fields
            required_fields = ['areas_for_improvement', 'recommendations', 'detailed_analysis']
            for field in required_fields:
                if field not in feedback:
                    feedback[field] = []
            
            return feedback
            
        except Exception as e:
            logger.error(f"Error parsing comprehensive feedback response: {str(e)}")
            return None
    
    def _get_fallback_comprehensive_feedback(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fallback comprehensive feedback when AI fails"""
        
        scores = performance_data.get('performance_scores', {})
        session_info = performance_data.get('session_info', {})
        
        # Generate basic feedback based on scores
        areas_for_improvement = []
        recommendations = []
        
        content_score = scores.get('content_quality', 0)
        body_language_score = scores.get('body_language', 0)
        tone_score = scores.get('voice_tone', 0)
        
        if content_score < 70:
            areas_for_improvement.append("Content quality and depth of answers need improvement")
            recommendations.append("Practice answering questions with more specific examples and details")
        
        if body_language_score < 70:
            areas_for_improvement.append("Body language and non-verbal communication")
            recommendations.append("Practice maintaining good posture and eye contact during interviews")
        
        if tone_score < 70:
            areas_for_improvement.append("Voice tone and confidence level")
            recommendations.append("Work on speaking clearly and confidently, practice vocal exercises")
        
        # Add session-specific recommendations
        session_type = session_info.get('session_type', 'mixed')
        if session_type == 'technical':
            recommendations.append("Focus on practicing technical problem-solving and explanation skills")
        elif session_type == 'behavioral':
            recommendations.append("Prepare more STAR method examples for behavioral questions")
        elif session_type == 'hr':
            recommendations.append("Research common HR questions and practice professional responses")
        
        return {
            'areas_for_improvement': areas_for_improvement or ['Continue practicing to improve overall interview performance'],
            'recommendations': recommendations or ['Keep practicing regularly to build confidence and skills'],
            'detailed_analysis': f"Based on your {session_info.get('session_type', 'interview')} session for {session_info.get('target_role', 'the target role')}, you scored {scores.get('overall_score', 0):.1f}/100 overall. Focus on the specific areas mentioned above to improve your performance.",
            'question_feedback': []
        }
    
    def _is_cached(self, cache_key: str) -> bool:
        """Check if data is cached and not expired"""
        if cache_key not in self.cache:
            return False
        
        cached_time = self.cache[cache_key]["timestamp"]
        return datetime.now() - cached_time < self.cache_ttl
    
    def _cache_data(self, cache_key: str, data: Any):
        """Cache data with timestamp"""
        self.cache[cache_key] = {
            "data": data,
            "timestamp": datetime.now()
        }
    
    def _get_fallback_questions(
        self, 
        role: str, 
        difficulty: str, 
        question_type: str, 
        count: int
    ) -> List[Dict[str, Any]]:
        """Return comprehensive fallback questions when API fails"""
        
        # Role-specific question templates
        role_questions = {
            'Software Developer': [
                {
                    "question": "Can you walk me through your experience with object-oriented programming?",
                    "category": "technical",
                    "duration": 4,
                    "key_points": ["OOP concepts", "Design patterns", "Real examples"]
                },
                {
                    "question": "Describe a challenging bug you encountered and how you solved it.",
                    "category": "behavioral",
                    "duration": 5,
                    "key_points": ["Problem description", "Debugging process", "Solution approach"]
                },
                {
                    "question": "How do you handle code reviews and feedback from team members?",
                    "category": "behavioral",
                    "duration": 3,
                    "key_points": ["Openness to feedback", "Collaboration skills", "Learning mindset"]
                },
                {
                    "question": "What's your experience with version control systems like Git?",
                    "category": "technical",
                    "duration": 3,
                    "key_points": ["Git workflows", "Branching strategies", "Conflict resolution"]
                },
                {
                    "question": "How do you stay updated with the latest technologies and best practices?",
                    "category": "behavioral",
                    "duration": 3,
                    "key_points": ["Learning methods", "Industry awareness", "Continuous improvement"]
                }
            ],
            'Data Scientist': [
                {
                    "question": "Explain the difference between supervised and unsupervised learning.",
                    "category": "technical",
                    "duration": 4,
                    "key_points": ["Definitions", "Examples", "Use cases"]
                },
                {
                    "question": "Describe a data analysis project you worked on from start to finish.",
                    "category": "behavioral",
                    "duration": 5,
                    "key_points": ["Problem definition", "Data collection", "Analysis process", "Results"]
                },
                {
                    "question": "How do you handle missing or inconsistent data in your analysis?",
                    "category": "technical",
                    "duration": 4,
                    "key_points": ["Data cleaning", "Imputation methods", "Validation"]
                },
                {
                    "question": "What's your experience with statistical testing and hypothesis validation?",
                    "category": "technical",
                    "duration": 4,
                    "key_points": ["Test selection", "P-values", "Interpretation"]
                },
                {
                    "question": "How do you communicate complex technical findings to non-technical stakeholders?",
                    "category": "behavioral",
                    "duration": 3,
                    "key_points": ["Simplification", "Visualization", "Storytelling"]
                }
            ],
            'Product Manager': [
                {
                    "question": "Walk me through how you prioritize features in a product roadmap.",
                    "category": "behavioral",
                    "duration": 4,
                    "key_points": ["Prioritization framework", "Stakeholder input", "Data-driven decisions"]
                },
                {
                    "question": "Describe a time when you had to make a difficult product decision with limited data.",
                    "category": "situational",
                    "duration": 5,
                    "key_points": ["Decision process", "Risk assessment", "Outcome"]
                },
                {
                    "question": "How do you gather and analyze user feedback to inform product decisions?",
                    "category": "behavioral",
                    "duration": 4,
                    "key_points": ["Feedback channels", "Analysis methods", "Action items"]
                },
                {
                    "question": "What's your approach to working with engineering teams and managing technical constraints?",
                    "category": "behavioral",
                    "duration": 4,
                    "key_points": ["Communication", "Understanding constraints", "Collaboration"]
                },
                {
                    "question": "How do you measure the success of a product feature?",
                    "category": "technical",
                    "duration": 4,
                    "key_points": ["KPIs", "Metrics", "Analysis"]
                }
            ]
        }
        
        # General fallback questions for any role
        general_questions = [
            {
                "question": "Tell me about yourself and your professional background.",
                "category": "behavioral",
                "duration": 3,
                "key_points": ["Professional background", "Key skills", "Career goals"]
            },
            {
                "question": "Why are you interested in this position and our company?",
                "category": "behavioral", 
                "duration": 3,
                "key_points": ["Company research", "Role alignment", "Career growth"]
            },
            {
                "question": "Describe a challenging project or problem you worked on. How did you approach it?",
                "category": "behavioral",
                "duration": 4,
                "key_points": ["Problem description", "Solution approach", "Results achieved"]
            },
            {
                "question": "What are your greatest strengths and how would they benefit this role?",
                "category": "behavioral",
                "duration": 3,
                "key_points": ["Relevant strengths", "Specific examples", "Value to employer"]
            },
            {
                "question": "Where do you see yourself in 5 years, and how does this role fit into your career plan?",
                "category": "behavioral",
                "duration": 3,
                "key_points": ["Career progression", "Skill development", "Long-term goals"]
            },
            {
                "question": "Describe a time when you had to work with a difficult team member. How did you handle it?",
                "category": "behavioral",
                "duration": 4,
                "key_points": ["Situation description", "Approach taken", "Resolution outcome"]
            },
            {
                "question": "What do you do to stay motivated and productive when working on long-term projects?",
                "category": "behavioral",
                "duration": 3,
                "key_points": ["Motivation strategies", "Productivity methods", "Results"]
            },
            {
                "question": "How do you handle feedback and criticism in your work?",
                "category": "behavioral",
                "duration": 3,
                "key_points": ["Reception of feedback", "Implementation", "Growth"]
            }
        ]
        
        # Get role-specific questions if available
        questions = role_questions.get(role, [])
        
        # Add general questions to fill the count
        questions.extend(general_questions)
        
        # Filter by question type if specified
        if question_type != "mixed":
            questions = [q for q in questions if q["category"] == question_type]
        
        # Adjust difficulty by modifying questions
        if difficulty == "beginner":
            # Use simpler questions and reduce duration
            for q in questions:
                q["duration"] = max(2, q["duration"] - 1)
        elif difficulty == "advanced":
            # Increase duration for more complex answers
            for q in questions:
                q["duration"] = min(6, q["duration"] + 1)
        
        # Return requested number of questions
        return questions[:count]
    
    def _get_fallback_evaluation(self) -> Dict[str, Any]:
        """Return fallback evaluation when API fails"""
        return {
            "overall_score": 70,
            "scores": {
                "content_quality": 70,
                "communication": 70,
                "depth": 70,
                "relevance": 70
            },
            "strengths": ["Clear communication", "Relevant examples"],
            "improvements": ["Add more specific details", "Structure your answer better"],
            "suggestions": ["Practice the STAR method", "Prepare more concrete examples"]
        }
    
    def _get_fallback_feedback(self) -> Dict[str, Any]:
        """Return fallback feedback when API fails"""
        return {
            "summary": "You demonstrated good communication skills and provided relevant examples.",
            "strengths": ["Clear speaking", "Professional demeanor"],
            "improvements": ["Add more specific details", "Practice storytelling"],
            "action_items": ["Practice common questions", "Prepare STAR format examples"],
            "motivation": "Keep practicing and you'll continue to improve!"
        }