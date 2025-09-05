"""
Question Validation Service with User Context
"""
import logging
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class QuestionValidationService:
    """Service for validating questions against user context and requirements"""
    
    def __init__(self):
        self.validation_version = "1.0"
        self.validation_criteria = [
            'role_relevance', 'difficulty_appropriateness', 'tech_stack_alignment',
            'experience_level_match', 'uniqueness', 'practical_application'
        ]
    
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
    
    def validate_questions_against_context(
        self,
        questions: List[Dict[str, Any]],
        context: Dict[str, Any],
        use_ai_validation: bool = True,
        gemini_service = None
    ) -> Dict[str, Any]:
        """
        Validate questions against user context with comprehensive criteria
        
        Args:
            questions: List of questions to validate
            context: Complete user context from UserContextBuilder
            use_ai_validation: Whether to use AI-powered validation
            gemini_service: Optional Gemini service for AI validation
            
        Returns:
            Validation results with passed/failed questions and feedback
        """
        
        try:
            logger.info(f"Validating {len(questions)} questions against user context")
            
            # Perform rule-based validation first
            rule_based_results = self._rule_based_validation(questions, context)
            
            # Perform AI-powered validation if available and requested
            ai_validation_results = None
            if use_ai_validation and gemini_service:
                try:
                    ai_validation_results = self._ai_powered_validation(
                        questions, context, gemini_service
                    )
                except Exception as e:
                    logger.warning(f"AI validation failed, using rule-based only: {str(e)}")
            
            # Combine validation results
            final_results = self._combine_validation_results(
                rule_based_results, ai_validation_results
            )
            
            logger.info(f"Validation completed: {len(final_results['validated_questions'])} questions passed")
            
            return final_results
            
        except Exception as e:
            logger.error(f"Error in question validation: {str(e)}")
            # Return all questions as valid if validation fails
            return {
                'validated_questions': questions,
                'rejected_questions': [],
                'validation_summary': {
                    'total_questions': len(questions),
                    'passed_validation': len(questions),
                    'rejected_count': 0,
                    'overall_quality': 'unknown',
                    'validation_method': 'fallback'
                },
                'validation_details': {
                    'error': str(e),
                    'fallback_used': True
                }
            }
    
    def validate_single_question(
        self,
        question: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate a single question against user context
        
        Args:
            question: Question to validate
            context: User context
            
        Returns:
            Validation result for the question
        """
        
        try:
            validation_result = {
                'is_valid': True,
                'validation_score': 0,
                'criteria_scores': {},
                'issues': [],
                'suggestions': []
            }
            
            # Check each validation criterion
            for criterion in self.validation_criteria:
                score, issues, suggestions = self._evaluate_criterion(
                    question, context, criterion
                )
                validation_result['criteria_scores'][criterion] = score
                validation_result['issues'].extend(issues)
                validation_result['suggestions'].extend(suggestions)
            
            # Calculate overall validation score
            validation_result['validation_score'] = sum(
                validation_result['criteria_scores'].values()
            ) / len(self.validation_criteria)
            
            # Determine if question is valid (threshold: 60%)
            validation_result['is_valid'] = validation_result['validation_score'] >= 60
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating single question: {str(e)}")
            return {
                'is_valid': True,  # Default to valid if validation fails
                'validation_score': 50,
                'criteria_scores': {},
                'issues': [f"Validation error: {str(e)}"],
                'suggestions': []
            }
    
    def filter_irrelevant_questions(
        self,
        questions: List[Dict[str, Any]],
        context: Dict[str, Any],
        strict_mode: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Filter out irrelevant questions based on context
        
        Args:
            questions: List of questions to filter
            context: User context
            strict_mode: Whether to use strict filtering criteria
            
        Returns:
            List of relevant questions
        """
        
        try:
            relevant_questions = []
            user_profile = context.get('user_profile', {})
            role_hierarchy = user_profile.get('role_hierarchy', {})
            tech_stacks = user_profile.get('tech_stacks', [])
            
            for question in questions:
                relevance_score = self._calculate_relevance_score(
                    question, role_hierarchy, tech_stacks
                )
                
                threshold = 70 if strict_mode else 40
                if relevance_score >= threshold:
                    relevant_questions.append(question)
                else:
                    logger.debug(f"Filtered question with relevance score {relevance_score}: {question.get('question', '')[:50]}...")
            
            logger.info(f"Filtered {len(questions) - len(relevant_questions)} irrelevant questions")
            return relevant_questions
            
        except Exception as e:
            logger.error(f"Error filtering questions: {str(e)}")
            return questions  # Return all questions if filtering fails
    
    def regenerate_failed_questions(
        self,
        failed_questions: List[Dict[str, Any]],
        context: Dict[str, Any],
        gemini_service = None
    ) -> List[Dict[str, Any]]:
        """
        Generate improved questions to replace failed ones
        
        Args:
            failed_questions: Questions that failed validation
            context: User context
            gemini_service: Gemini service for regeneration
            
        Returns:
            List of regenerated questions
        """
        
        try:
            if not gemini_service:
                logger.warning("No Gemini service available for regeneration")
                return []
            
            # Analyze failure patterns
            failure_analysis = self._analyze_failure_patterns(failed_questions, context)
            
            # Generate improvement suggestions
            improvement_suggestions = self._generate_improvement_suggestions(
                failure_analysis, context
            )
            
            # Use Gemini service to regenerate questions
            regenerated_questions = gemini_service._regenerate_questions_with_feedback(
                context, failed_questions
            )
            
            logger.info(f"Regenerated {len(regenerated_questions)} questions")
            return regenerated_questions
            
        except Exception as e:
            logger.error(f"Error regenerating questions: {str(e)}")
            return []
    
    def _rule_based_validation(
        self,
        questions: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform rule-based validation of questions"""
        
        validated_questions = []
        rejected_questions = []
        
        user_profile = context.get('user_profile', {})
        session_context = context.get('session_context', {})
        
        for question in questions:
            validation_result = self.validate_single_question(question, context)
            
            if validation_result['is_valid']:
                validated_questions.append(question)
            else:
                rejected_questions.append({
                    'question': question,
                    'rejection_reason': '; '.join(validation_result['issues']),
                    'suggested_improvement': '; '.join(validation_result['suggestions']),
                    'validation_score': validation_result['validation_score']
                })
        
        return {
            'validated_questions': validated_questions,
            'rejected_questions': rejected_questions,
            'validation_method': 'rule_based',
            'validation_timestamp': datetime.utcnow().isoformat()
        }
    
    def _ai_powered_validation(
        self,
        questions: List[Dict[str, Any]],
        context: Dict[str, Any],
        gemini_service
    ) -> Dict[str, Any]:
        """Perform AI-powered validation using Gemini service"""
        
        try:
            # Use the integrated prompts for validation
            validation_prompt = gemini_service.build_validation_prompt(
                questions, context
            )
            
            # Generate validation response
            generation_config = {
                "temperature": 0.2,
                "top_p": 0.8,
                "max_output_tokens": 3072,
            }
            
            response = gemini_service.model.generate_content(
                validation_prompt, 
                generation_config=generation_config
            )
            
            # Extract response text
            response_text = ""
            if hasattr(response, 'text') and response.text:
                response_text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                if hasattr(response.candidates[0], 'content'):
                    response_text = response.candidates[0].content.parts[0].text
            
            # Parse validation results
            ai_results = self._parse_ai_validation_response(response_text)
            
            if ai_results:
                ai_results['validation_method'] = 'ai_powered'
                ai_results['validation_timestamp'] = datetime.utcnow().isoformat()
                return ai_results
            else:
                logger.warning("Failed to parse AI validation response")
                return None
                
        except Exception as e:
            logger.error(f"Error in AI-powered validation: {str(e)}")
            return None
    
    def _combine_validation_results(
        self,
        rule_based_results: Dict[str, Any],
        ai_validation_results: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Combine rule-based and AI validation results"""
        
        if not ai_validation_results:
            # Use only rule-based results
            return {
                **rule_based_results,
                'validation_summary': {
                    'total_questions': len(rule_based_results['validated_questions']) + len(rule_based_results['rejected_questions']),
                    'passed_validation': len(rule_based_results['validated_questions']),
                    'rejected_count': len(rule_based_results['rejected_questions']),
                    'overall_quality': self._assess_overall_quality(rule_based_results),
                    'validation_method': 'rule_based_only'
                }
            }
        
        # Combine both validation methods
        # Use intersection of validated questions (both methods must approve)
        rule_validated_ids = {self._get_question_id(q) for q in rule_based_results['validated_questions']}
        ai_validated_ids = {self._get_question_id(q) for q in ai_validation_results['validated_questions']}
        
        combined_validated_ids = rule_validated_ids.intersection(ai_validated_ids)
        
        combined_validated = [
            q for q in rule_based_results['validated_questions']
            if self._get_question_id(q) in combined_validated_ids
        ]
        
        # Combine rejected questions
        combined_rejected = []
        combined_rejected.extend(rule_based_results['rejected_questions'])
        combined_rejected.extend([
            r for r in ai_validation_results['rejected_questions']
            if self._get_question_id(r.get('question', {})) not in combined_validated_ids
        ])
        
        return {
            'validated_questions': combined_validated,
            'rejected_questions': combined_rejected,
            'validation_summary': {
                'total_questions': len(combined_validated) + len(combined_rejected),
                'passed_validation': len(combined_validated),
                'rejected_count': len(combined_rejected),
                'overall_quality': self._assess_overall_quality({'validated_questions': combined_validated, 'rejected_questions': combined_rejected}),
                'validation_method': 'combined'
            },
            'validation_details': {
                'rule_based_passed': len(rule_based_results['validated_questions']),
                'ai_validation_passed': len(ai_validation_results['validated_questions']),
                'consensus_passed': len(combined_validated)
            }
        }
    
    def _evaluate_criterion(
        self,
        question: Dict[str, Any],
        context: Dict[str, Any],
        criterion: str
    ) -> Tuple[float, List[str], List[str]]:
        """Evaluate a specific validation criterion"""
        
        user_profile = context.get('user_profile', {})
        session_context = context.get('session_context', {})
        role_hierarchy = user_profile.get('role_hierarchy', {})
        
        question_text = question.get('question', '').lower()
        question_category = question.get('category', '')
        
        if criterion == 'role_relevance':
            return self._evaluate_role_relevance(question_text, role_hierarchy)
        elif criterion == 'difficulty_appropriateness':
            return self._evaluate_difficulty_appropriateness(
                question, session_context.get('current_difficulty', 'medium')
            )
        elif criterion == 'tech_stack_alignment':
            return self._evaluate_tech_stack_alignment(
                question_text, user_profile.get('tech_stacks', [])
            )
        elif criterion == 'experience_level_match':
            return self._evaluate_experience_level_match(
                question, user_profile.get('experience_level', 'intermediate')
            )
        elif criterion == 'uniqueness':
            return self._evaluate_uniqueness(question, context)
        elif criterion == 'practical_application':
            return self._evaluate_practical_application(question, role_hierarchy)
        else:
            return 50.0, [], []  # Default score for unknown criteria
    
    def _evaluate_role_relevance(
        self,
        question_text: str,
        role_hierarchy: Dict[str, Any]
    ) -> Tuple[float, List[str], List[str]]:
        """Evaluate role relevance of a question"""
        
        main_role = self._get_role_attribute(role_hierarchy, 'main_role', '').lower()
        sub_role = self._get_role_attribute(role_hierarchy, 'sub_role', '').lower()
        specialization = self._get_role_attribute(role_hierarchy, 'specialization', '').lower()
        
        score = 0
        issues = []
        suggestions = []
        
        # Check main role relevance
        if main_role and any(word in question_text for word in main_role.split()):
            score += 40
        else:
            issues.append(f"Question doesn't mention {main_role} responsibilities")
            suggestions.append(f"Include {main_role}-specific scenarios or tasks")
        
        # Check sub role relevance
        if sub_role and any(word in question_text for word in sub_role.split()):
            score += 30
        elif sub_role:
            issues.append(f"Question doesn't address {sub_role} specific skills")
            suggestions.append(f"Focus on {sub_role} competencies")
        
        # Check specialization relevance
        if specialization and any(word in question_text for word in specialization.split()):
            score += 30
        elif specialization:
            issues.append(f"Question doesn't test {specialization} expertise")
            suggestions.append(f"Include {specialization} specific knowledge areas")
        
        # Check for generic programming terms as fallback
        generic_terms = ['code', 'program', 'develop', 'implement', 'design', 'system']
        if any(term in question_text for term in generic_terms):
            score = max(score, 60)  # Minimum score for technical relevance
        
        return min(score, 100), issues, suggestions
    
    def _evaluate_difficulty_appropriateness(
        self,
        question: Dict[str, Any],
        target_difficulty: str
    ) -> Tuple[float, List[str], List[str]]:
        """Evaluate if question matches target difficulty"""
        
        question_text = question.get('question', '').lower()
        duration = question.get('duration', 3)
        
        difficulty_indicators = {
            'easy': ['basic', 'simple', 'what is', 'define', 'list', 'name'],
            'medium': ['how', 'explain', 'implement', 'design', 'compare', 'analyze'],
            'hard': ['optimize', 'scale', 'architecture', 'complex', 'advanced', 'integrate'],
            'expert': ['strategic', 'lead', 'architect', 'enterprise', 'governance', 'innovation']
        }
        
        target_indicators = difficulty_indicators.get(target_difficulty.lower(), [])
        
        score = 50  # Base score
        issues = []
        suggestions = []
        
        # Check for appropriate difficulty indicators
        matching_indicators = [ind for ind in target_indicators if ind in question_text]
        if matching_indicators:
            score += 30
        else:
            # More lenient - check for general technical terms
            technical_terms = ['implement', 'design', 'explain', 'how', 'what', 'why', 'create', 'build']
            if any(term in question_text for term in technical_terms):
                score += 20  # Partial credit for technical content
            else:
                issues.append(f"Question doesn't match {target_difficulty} difficulty indicators")
                suggestions.append(f"Use {target_difficulty}-appropriate language: {', '.join(target_indicators[:3])}")
        
        # Check duration appropriateness (more lenient)
        expected_duration = {'easy': 2, 'medium': 3, 'hard': 4, 'expert': 5}
        expected = expected_duration.get(target_difficulty.lower(), 3)
        
        if abs(duration - expected) <= 2:  # Allow 2-minute variance
            score += 20
        else:
            issues.append(f"Duration {duration}min doesn't match {target_difficulty} expectation (~{expected}min)")
            suggestions.append(f"Adjust question complexity for {expected}-minute duration")
        
        return min(score, 100), issues, suggestions
    
    def _evaluate_tech_stack_alignment(
        self,
        question_text: str,
        tech_stacks: List[str]
    ) -> Tuple[float, List[str], List[str]]:
        """Evaluate tech stack alignment"""
        
        if not tech_stacks:
            return 70, [], []  # Neutral score if no tech stack specified
        
        score = 0
        issues = []
        suggestions = []
        
        # Check for tech stack mentions
        mentioned_techs = [tech for tech in tech_stacks if tech.lower() in question_text]
        
        if mentioned_techs:
            score = 90
        else:
            # Check for related technologies or concepts
            tech_concepts = self._get_related_tech_concepts(tech_stacks)
            if any(concept in question_text for concept in tech_concepts):
                score = 75
            else:
                # More lenient - check for general programming concepts
                programming_terms = ['component', 'function', 'method', 'class', 'variable', 'array', 'object']
                if any(term in question_text for term in programming_terms):
                    score = 65  # Acceptable for general programming questions
                else:
                    score = 40
                    issues.append("Question doesn't relate to candidate's tech stack")
                    suggestions.append(f"Include technologies from: {', '.join(tech_stacks[:3])}")
        
        return score, issues, suggestions
    
    def _evaluate_experience_level_match(
        self,
        question: Dict[str, Any],
        experience_level: str
    ) -> Tuple[float, List[str], List[str]]:
        """Evaluate experience level appropriateness"""
        
        question_text = question.get('question', '').lower()
        
        experience_indicators = {
            'entry': ['learn', 'basic', 'introduction', 'getting started'],
            'junior': ['implement', 'use', 'apply', 'work with'],
            'intermediate': ['design', 'optimize', 'troubleshoot', 'integrate'],
            'senior': ['architect', 'lead', 'mentor', 'strategy', 'best practices'],
            'expert': ['innovate', 'research', 'pioneer', 'industry standards']
        }
        
        # Map common experience levels
        level_mapping = {
            'beginner': 'entry',
            'intermediate': 'intermediate',
            'advanced': 'senior',
            'expert': 'expert'
        }
        
        mapped_level = level_mapping.get(experience_level.lower(), experience_level.lower())
        expected_indicators = experience_indicators.get(mapped_level, [])
        
        score = 50
        issues = []
        suggestions = []
        
        if any(indicator in question_text for indicator in expected_indicators):
            score = 85
        else:
            issues.append(f"Question complexity doesn't match {experience_level} level")
            suggestions.append(f"Use {experience_level}-appropriate complexity and terminology")
        
        return score, issues, suggestions
    
    def _evaluate_uniqueness(
        self,
        question: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Tuple[float, List[str], List[str]]:
        """Evaluate question uniqueness (placeholder - would need question history)"""
        
        # This is a simplified implementation
        # In a real system, you'd check against previously asked questions
        
        question_text = question.get('question', '')
        
        # Check for overly generic questions
        generic_phrases = [
            'tell me about yourself',
            'what are your strengths',
            'where do you see yourself',
            'why do you want this job'
        ]
        
        if any(phrase in question_text.lower() for phrase in generic_phrases):
            return 30, ['Question is too generic'], ['Make question more role-specific']
        
        return 80, [], []  # Default to good uniqueness
    
    def _evaluate_practical_application(
        self,
        question: Dict[str, Any],
        role_hierarchy: Dict[str, Any]
    ) -> Tuple[float, List[str], List[str]]:
        """Evaluate practical application relevance"""
        
        question_text = question.get('question', '').lower()
        
        practical_indicators = [
            'real-world', 'project', 'experience', 'example', 'scenario',
            'situation', 'challenge', 'problem', 'solution', 'implement'
        ]
        
        score = 50
        issues = []
        suggestions = []
        
        if any(indicator in question_text for indicator in practical_indicators):
            score = 85
        else:
            issues.append("Question lacks practical application context")
            suggestions.append("Add real-world scenarios or practical examples")
        
        return score, issues, suggestions
    
    def _calculate_relevance_score(
        self,
        question: Dict[str, Any],
        role_hierarchy: Dict[str, Any],
        tech_stacks: List[str]
    ) -> float:
        """Calculate overall relevance score for a question"""
        
        question_text = question.get('question', '').lower()
        
        # Role relevance (40% weight)
        role_score, _, _ = self._evaluate_role_relevance(question_text, role_hierarchy)
        
        # Tech stack alignment (30% weight)
        tech_score, _, _ = self._evaluate_tech_stack_alignment(question_text, tech_stacks)
        
        # Practical application (30% weight)
        practical_score, _, _ = self._evaluate_practical_application(question, role_hierarchy)
        
        # Weighted average
        relevance_score = (role_score * 0.4) + (tech_score * 0.3) + (practical_score * 0.3)
        
        return relevance_score
    
    def _get_related_tech_concepts(self, tech_stacks: List[str]) -> List[str]:
        """Get related technology concepts for broader matching"""
        
        concept_mapping = {
            'react': ['component', 'jsx', 'hooks', 'state', 'props'],
            'javascript': ['js', 'node', 'npm', 'async', 'promise'],
            'python': ['django', 'flask', 'pandas', 'numpy', 'pip'],
            'java': ['spring', 'maven', 'gradle', 'jvm', 'servlet'],
            'docker': ['container', 'image', 'dockerfile', 'compose'],
            'kubernetes': ['k8s', 'pod', 'deployment', 'service', 'ingress']
        }
        
        concepts = []
        for tech in tech_stacks:
            tech_lower = tech.lower()
            if tech_lower in concept_mapping:
                concepts.extend(concept_mapping[tech_lower])
        
        return concepts
    
    def _parse_ai_validation_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse AI validation response"""
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing AI validation response: {str(e)}")
            return None
    
    def _assess_overall_quality(self, validation_results: Dict[str, Any]) -> str:
        """Assess overall quality of validation results"""
        
        total = len(validation_results['validated_questions']) + len(validation_results['rejected_questions'])
        if total == 0:
            return 'unknown'
        
        pass_rate = len(validation_results['validated_questions']) / total
        
        if pass_rate >= 0.9:
            return 'excellent'
        elif pass_rate >= 0.7:
            return 'good'
        elif pass_rate >= 0.5:
            return 'needs_improvement'
        else:
            return 'poor'
    
    def _get_question_id(self, question: Dict[str, Any]) -> str:
        """Get unique identifier for a question"""
        
        # Use question text hash as ID
        question_text = question.get('question', '')
        return str(hash(question_text))
    
    def _analyze_failure_patterns(
        self,
        failed_questions: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze patterns in failed questions"""
        
        failure_patterns = {
            'common_issues': [],
            'missing_elements': [],
            'improvement_areas': []
        }
        
        # Analyze common failure reasons
        rejection_reasons = []
        for failed in failed_questions:
            if isinstance(failed, dict) and 'rejection_reason' in failed:
                rejection_reasons.append(failed['rejection_reason'])
        
        # Identify common patterns
        if any('generic' in reason.lower() for reason in rejection_reasons):
            failure_patterns['common_issues'].append('Questions too generic')
            failure_patterns['improvement_areas'].append('Add role-specific context')
        
        if any('tech stack' in reason.lower() for reason in rejection_reasons):
            failure_patterns['common_issues'].append('Poor tech stack alignment')
            failure_patterns['improvement_areas'].append('Include relevant technologies')
        
        return failure_patterns
    
    def _generate_improvement_suggestions(
        self,
        failure_analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[str]:
        """Generate improvement suggestions based on failure analysis"""
        
        suggestions = []
        user_profile = context.get('user_profile', {})
        role_hierarchy = user_profile.get('role_hierarchy', {})
        
        for issue in failure_analysis.get('common_issues', []):
            if 'generic' in issue.lower():
                suggestions.append(f"Focus on {self._get_role_attribute(role_hierarchy, 'specialization', 'role-specific')} scenarios")
            elif 'tech stack' in issue.lower():
                tech_stacks = user_profile.get('tech_stacks', [])
                if tech_stacks:
                    suggestions.append(f"Include questions about {', '.join(tech_stacks[:3])}")
        
        return suggestions