"""
Question Distribution Calculator Service
"""
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class QuestionDistributionCalculator:
    """Service for calculating and enforcing proper question type ratios"""
    
    def __init__(self):
        self.distribution_version = "1.0"
        self.default_distribution = {
            'theory_percentage': 20,
            'coding_percentage': 40,
            'aptitude_percentage': 40
        }
    
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
        
        # Question type templates for different roles and difficulties
        self.question_templates = {
            'coding': {
                'easy': [
                    'Write a program to check if a string is a palindrome',
                    'Implement a function to find the maximum element in an array',
                    'Create a simple calculator with basic operations',
                    'Write a function to reverse a string',
                    'Implement a basic sorting algorithm'
                ],
                'medium': [
                    'Implement a binary search algorithm',
                    'Design a simple caching mechanism',
                    'Write a function to merge two sorted arrays',
                    'Create a function to find duplicate elements in an array',
                    'Implement a basic hash table'
                ],
                'hard': [
                    'Design and implement a distributed caching system',
                    'Implement a thread-safe singleton pattern',
                    'Design a rate limiting algorithm',
                    'Create an efficient algorithm for finding the shortest path',
                    'Implement a load balancer algorithm'
                ],
                'expert': [
                    'Design a scalable microservices architecture',
                    'Implement a consensus algorithm for distributed systems',
                    'Design a real-time data processing pipeline',
                    'Create a fault-tolerant distributed database',
                    'Implement a custom garbage collection algorithm'
                ]
            },
            'aptitude': {
                'easy': [
                    'Find the missing number in a sequence from 1 to 10',
                    'Calculate the time complexity of a simple loop',
                    'Identify the pattern in a given sequence',
                    'Solve a basic logic puzzle',
                    'Calculate simple probability problems'
                ],
                'medium': [
                    'Optimize a database query for better performance',
                    'Design a simple load balancing strategy',
                    'Calculate space complexity for a recursive algorithm',
                    'Solve complex logical reasoning problems',
                    'Analyze algorithm efficiency trade-offs'
                ],
                'hard': [
                    'Design a system to handle 1 million concurrent users',
                    'Optimize a system for high availability and fault tolerance',
                    'Design a data pipeline for real-time analytics',
                    'Solve complex optimization problems',
                    'Design efficient algorithms for large-scale data processing'
                ],
                'expert': [
                    'Design a globally distributed system architecture',
                    'Optimize performance for extreme scale requirements',
                    'Design fault-tolerant systems with complex failure modes',
                    'Create innovative solutions for unprecedented technical challenges',
                    'Design systems that can handle exponential growth'
                ]
            },
            'theory': {
                'easy': [
                    'Explain the difference between a compiler and an interpreter',
                    'What is the difference between HTTP and HTTPS?',
                    'Define what an API is and give an example',
                    'Explain basic object-oriented programming concepts',
                    'What are the main principles of software development?'
                ],
                'medium': [
                    'Explain the CAP theorem and its implications',
                    'Describe different types of database indexes',
                    'What are the principles of RESTful API design?',
                    'Explain different software design patterns',
                    'Describe the software development lifecycle'
                ],
                'hard': [
                    'Explain microservices architecture and its trade-offs',
                    'Describe event-driven architecture patterns',
                    'What are the challenges in distributed system design?',
                    'Explain advanced database concepts and optimization',
                    'Describe enterprise architecture patterns'
                ],
                'expert': [
                    'Explain cutting-edge architectural paradigms',
                    'Describe advanced distributed systems theory',
                    'What are the latest trends in software architecture?',
                    'Explain complex system design principles',
                    'Describe innovative approaches to scalability and performance'
                ]
            }
        }
    
    def calculate_distribution(
        self, 
        total_questions: int, 
        session_type: str = 'main',
        custom_distribution: Dict[str, int] = None
    ) -> Dict[str, int]:
        """
        Calculate question type distribution based on total count and session type
        
        Args:
            total_questions: Total number of questions needed
            session_type: Type of session (main, practice, quick_test)
            custom_distribution: Optional custom distribution percentages
            
        Returns:
            Dictionary with question counts for each type
        """
        
        try:
            logger.info(f"Calculating distribution for {total_questions} questions, session type: {session_type}")
            
            # Use custom distribution if provided, otherwise use default
            distribution = custom_distribution or self.default_distribution
            
            if session_type == 'quick_test' and total_questions <= 3:
                # For small quick tests, ensure at least one of each type
                return self._calculate_minimal_distribution(total_questions)
            
            # Standard distribution calculation
            theory_count = max(1, round(total_questions * distribution['theory_percentage'] / 100))
            coding_count = max(1, round(total_questions * distribution['coding_percentage'] / 100))
            
            # Ensure total doesn't exceed available questions
            if theory_count + coding_count >= total_questions:
                # Adjust if we're over the limit
                if total_questions >= 2:
                    theory_count = max(1, total_questions // 3)
                    coding_count = max(1, total_questions // 2)
                    if theory_count + coding_count >= total_questions:
                        theory_count = 1
                        coding_count = min(coding_count, total_questions - 1)
                else:
                    theory_count = 1 if total_questions >= 1 else 0
                    coding_count = 0
            
            aptitude_count = total_questions - theory_count - coding_count
            aptitude_count = max(0, aptitude_count)  # Ensure non-negative
            
            result = {
                'theory': theory_count,
                'coding': coding_count,
                'aptitude': aptitude_count
            }
            
            logger.info(f"Calculated distribution: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating distribution: {str(e)}")
            # Fallback to simple distribution
            return self._get_fallback_distribution(total_questions)
    
    def validate_distribution(
        self, 
        questions: List[Dict[str, Any]], 
        expected_distribution: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Validate that generated questions match expected distribution
        
        Args:
            questions: List of generated questions
            expected_distribution: Expected distribution counts
            
        Returns:
            Validation results with actual vs expected counts
        """
        
        try:
            # Count actual question types
            actual_distribution = {
                'theory': 0,
                'coding': 0,
                'aptitude': 0
            }
            
            for question in questions:
                question_type = question.get('category', '').lower()
                
                # Map question categories to distribution types
                if question_type in ['theory', 'theoretical']:
                    actual_distribution['theory'] += 1
                elif question_type in ['coding', 'technical', 'programming']:
                    actual_distribution['coding'] += 1
                elif question_type in ['aptitude', 'problem-solving', 'analytical']:
                    actual_distribution['aptitude'] += 1
                else:
                    # Default mapping based on question content
                    question_text = question.get('question', '').lower()
                    if any(word in question_text for word in ['explain', 'define', 'what is', 'describe']):
                        actual_distribution['theory'] += 1
                    elif any(word in question_text for word in ['implement', 'write', 'code', 'program']):
                        actual_distribution['coding'] += 1
                    else:
                        actual_distribution['aptitude'] += 1
            
            # Calculate validation results
            is_valid = actual_distribution == expected_distribution
            
            # Calculate deviation
            total_deviation = sum(
                abs(actual_distribution[key] - expected_distribution[key])
                for key in expected_distribution.keys()
            )
            
            validation_score = max(0, 100 - (total_deviation * 20))  # 20 points penalty per deviation
            
            result = {
                'is_valid': is_valid,
                'validation_score': validation_score,
                'actual_distribution': actual_distribution,
                'expected_distribution': expected_distribution,
                'deviations': {
                    key: actual_distribution[key] - expected_distribution[key]
                    for key in expected_distribution.keys()
                },
                'total_deviation': total_deviation
            }
            
            logger.info(f"Distribution validation: {validation_score}% score, valid: {is_valid}")
            return result
            
        except Exception as e:
            logger.error(f"Error validating distribution: {str(e)}")
            return {
                'is_valid': False,
                'validation_score': 0,
                'actual_distribution': {},
                'expected_distribution': expected_distribution,
                'deviations': {},
                'total_deviation': 0,
                'error': str(e)
            }
    
    def get_question_examples_for_role(
        self, 
        role_hierarchy: Dict[str, Any], 
        difficulty: str,
        question_type: str
    ) -> List[str]:
        """
        Get question examples based on role, difficulty, and type
        
        Args:
            role_hierarchy: Role hierarchy information
            difficulty: Difficulty level (easy, medium, hard, expert)
            question_type: Type of question (coding, aptitude, theory)
            
        Returns:
            List of example questions
        """
        
        try:
            # Get base examples for the difficulty and type
            base_examples = self.question_templates.get(question_type, {}).get(difficulty.lower(), [])
            
            if not base_examples:
                return []
            
            # Customize examples based on role
            main_role = self._get_role_attribute(role_hierarchy, 'main_role', '')
            sub_role = self._get_role_attribute(role_hierarchy, 'sub_role', '')
            specialization = self._get_role_attribute(role_hierarchy, 'specialization', '')
            
            customized_examples = []
            for example in base_examples[:3]:  # Limit to 3 examples
                customized_example = self._customize_example_for_role(
                    example, main_role, sub_role, specialization, question_type
                )
                customized_examples.append(customized_example)
            
            return customized_examples
            
        except Exception as e:
            logger.error(f"Error getting question examples: {str(e)}")
            return []
    
    def enforce_distribution_in_prompt(
        self, 
        distribution: Dict[str, int], 
        role_hierarchy: Dict[str, Any],
        difficulty: str
    ) -> str:
        """
        Generate prompt section for enforcing question distribution
        
        Args:
            distribution: Required distribution counts
            role_hierarchy: Role hierarchy information
            difficulty: Difficulty level
            
        Returns:
            Formatted prompt section for distribution enforcement
        """
        
        try:
            total_questions = sum(distribution.values())
            
            prompt_section = f"""
STRICT QUESTION DISTRIBUTION REQUIREMENTS:
- Total Questions: {total_questions}
- Theory Questions: {distribution['theory']} (conceptual knowledge, best practices, theoretical understanding)
- Coding Questions: {distribution['coding']} (programming problems, algorithm implementation, code review)
- Aptitude/Technical Logic: {distribution['aptitude']} (problem-solving, analytical thinking, technical reasoning)

DISTRIBUTION ENFORCEMENT RULES:
1. You MUST generate exactly {distribution['theory']} theory questions
2. You MUST generate exactly {distribution['coding']} coding questions  
3. You MUST generate exactly {distribution['aptitude']} aptitude questions
4. Each question type should test different aspects of competency
5. Maintain appropriate difficulty progression within each category
6. Ensure balanced coverage across the role requirements

QUESTION TYPE GUIDELINES:
"""
            
            # Add examples for each type
            for question_type, count in distribution.items():
                if count > 0:
                    examples = self.get_question_examples_for_role(
                        role_hierarchy, difficulty, question_type
                    )
                    if examples:
                        prompt_section += f"\n{question_type.upper()} QUESTION EXAMPLES ({count} required):\n"
                        for i, example in enumerate(examples, 1):
                            prompt_section += f"{i}. {example}\n"
            
            return prompt_section
            
        except Exception as e:
            logger.error(f"Error creating distribution prompt: {str(e)}")
            return f"Generate {sum(distribution.values())} questions with balanced distribution."
    
    def adjust_distribution_for_regeneration(
        self, 
        current_questions: List[Dict[str, Any]], 
        target_distribution: Dict[str, int]
    ) -> Dict[str, int]:
        """
        Calculate what types of questions need to be regenerated
        
        Args:
            current_questions: Currently generated questions
            target_distribution: Target distribution
            
        Returns:
            Dictionary with counts of questions needed for each type
        """
        
        try:
            # Count current distribution
            current_validation = self.validate_distribution(current_questions, target_distribution)
            current_counts = current_validation['actual_distribution']
            
            # Calculate what's needed
            needed_distribution = {}
            for question_type, target_count in target_distribution.items():
                current_count = current_counts.get(question_type, 0)
                needed_count = max(0, target_count - current_count)
                needed_distribution[question_type] = needed_count
            
            logger.info(f"Regeneration needed: {needed_distribution}")
            return needed_distribution
            
        except Exception as e:
            logger.error(f"Error calculating regeneration distribution: {str(e)}")
            return target_distribution
    
    def _calculate_minimal_distribution(self, total_questions: int) -> Dict[str, int]:
        """Calculate minimal distribution for small question sets"""
        
        if total_questions == 1:
            return {'theory': 0, 'coding': 1, 'aptitude': 0}
        elif total_questions == 2:
            return {'theory': 0, 'coding': 1, 'aptitude': 1}
        elif total_questions == 3:
            return {'theory': 1, 'coding': 1, 'aptitude': 1}
        else:
            # For 4+ questions, use proportional distribution
            theory_count = max(1, total_questions // 5)  # 20%
            coding_count = max(1, (total_questions * 2) // 5)  # 40%
            aptitude_count = total_questions - theory_count - coding_count
            return {'theory': theory_count, 'coding': coding_count, 'aptitude': aptitude_count}
    
    def _get_fallback_distribution(self, total_questions: int) -> Dict[str, int]:
        """Get fallback distribution if calculation fails"""
        
        if total_questions <= 3:
            return self._calculate_minimal_distribution(total_questions)
        
        # Simple even distribution as fallback
        per_type = total_questions // 3
        remainder = total_questions % 3
        
        return {
            'theory': per_type + (1 if remainder > 0 else 0),
            'coding': per_type + (1 if remainder > 1 else 0),
            'aptitude': per_type
        }
    
    def _customize_example_for_role(
        self, 
        example: str, 
        main_role: str, 
        sub_role: str, 
        specialization: str,
        question_type: str
    ) -> str:
        """Customize example question for specific role"""
        
        try:
            # Role-specific customizations
            role_customizations = {
                'Software Developer': {
                    'Frontend Developer': {
                        'React Developer': {
                            'coding': 'using React hooks and components',
                            'theory': 'in React and frontend development',
                            'aptitude': 'for React application optimization'
                        }
                    },
                    'Backend Developer': {
                        'API Developer': {
                            'coding': 'for RESTful API development',
                            'theory': 'in backend architecture and APIs',
                            'aptitude': 'for API performance optimization'
                        }
                    }
                },
                'Data Scientist': {
                    'ML Engineer': {
                        'Computer Vision Engineer': {
                            'coding': 'using machine learning libraries',
                            'theory': 'in machine learning and computer vision',
                            'aptitude': 'for ML model optimization'
                        }
                    }
                }
            }
            
            # Get customization text
            customization = ""
            if main_role in role_customizations:
                role_data = role_customizations[main_role]
                if sub_role in role_data:
                    sub_data = role_data[sub_role]
                    if specialization in sub_data:
                        spec_data = sub_data[specialization]
                        customization = spec_data.get(question_type, "")
            
            # Apply customization if available
            if customization:
                # Simple customization - append role-specific context
                if question_type == 'coding' and 'implement' in example.lower():
                    return f"{example} {customization}"
                elif question_type == 'theory' and 'explain' in example.lower():
                    return f"{example} {customization}"
                elif question_type == 'aptitude':
                    return f"{example} {customization}"
            
            return example
            
        except Exception as e:
            logger.error(f"Error customizing example: {str(e)}")
            return example
    
    def get_distribution_summary(self, distribution: Dict[str, int]) -> str:
        """Get a human-readable summary of the distribution"""
        
        total = sum(distribution.values())
        if total == 0:
            return "No questions specified"
        
        percentages = {
            key: round((count / total) * 100, 1)
            for key, count in distribution.items()
        }
        
        return f"Theory: {distribution['theory']} ({percentages['theory']}%), " \
               f"Coding: {distribution['coding']} ({percentages['coding']}%), " \
               f"Aptitude: {distribution['aptitude']} ({percentages['aptitude']}%)"