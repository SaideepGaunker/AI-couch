"""
Unit tests for Gemini Service
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from app.services.gemini_service import GeminiService
from app.db.models import Question


class TestGeminiService:
    """Test cases for GeminiService"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def gemini_service(self, mock_db):
        """Create GeminiService instance with mocked dependencies"""
        with patch('app.services.gemini_service.genai'):
            service = GeminiService(mock_db)
            service.model = Mock()
            return service
    
    def test_generate_questions_success(self, gemini_service, mock_db):
        """Test successful question generation"""
        # Mock Gemini API response
        mock_response = Mock()
        mock_response.text = '''[
            {
                "question": "Tell me about yourself",
                "category": "behavioral",
                "duration": 3,
                "key_points": ["Background", "Skills", "Goals"]
            }
        ]'''
        
        gemini_service.model.generate_content.return_value = mock_response
        
        # Test
        questions = gemini_service.generate_questions(
            role="Software Developer",
            difficulty="intermediate",
            question_type="behavioral",
            count=1
        )
        
        # Assertions
        assert len(questions) == 1
        assert questions[0]['question'] == "Tell me about yourself"
        assert questions[0]['category'] == "behavioral"
        assert questions[0]['duration'] == 3
    
    def test_generate_questions_api_failure(self, gemini_service, mock_db):
        """Test question generation when API fails"""
        # Mock API failure
        gemini_service.model.generate_content.side_effect = Exception("API Error")
        
        # Test
        questions = gemini_service.generate_questions(
            role="Software Developer",
            difficulty="intermediate",
            question_type="behavioral",
            count=3
        )
        
        # Should return fallback questions
        assert len(questions) == 3
        assert all('question' in q for q in questions)
    
    def test_evaluate_answer_success(self, gemini_service, mock_db):
        """Test successful answer evaluation"""
        # Mock Gemini API response
        mock_response = Mock()
        mock_response.text = '''{
            "overall_score": 85,
            "scores": {
                "content_quality": 80,
                "communication": 90,
                "depth": 85,
                "relevance": 85
            },
            "strengths": ["Clear communication", "Good examples"],
            "improvements": ["Add more details", "Structure better"],
            "suggestions": ["Use STAR method", "Practice more"]
        }'''
        
        gemini_service.model.generate_content.return_value = mock_response
        
        # Test
        evaluation = gemini_service.evaluate_answer(
            question="Tell me about yourself",
            answer="I am a software developer with 5 years of experience...",
            context={"role": "job_seeker", "experience_level": "intermediate"}
        )
        
        # Assertions
        assert evaluation['overall_score'] == 85
        assert 'scores' in evaluation
        assert 'strengths' in evaluation
        assert 'improvements' in evaluation
    
    def test_evaluate_answer_api_failure(self, gemini_service, mock_db):
        """Test answer evaluation when API fails"""
        # Mock API failure
        gemini_service.model.generate_content.side_effect = Exception("API Error")
        
        # Test
        evaluation = gemini_service.evaluate_answer(
            question="Tell me about yourself",
            answer="I am a software developer...",
            context={}
        )
        
        # Should return fallback evaluation
        assert 'overall_score' in evaluation
        assert evaluation['overall_score'] == 70  # Fallback score
    
    def test_cache_functionality(self, gemini_service, mock_db):
        """Test caching mechanism"""
        # Mock successful response
        mock_response = Mock()
        mock_response.text = '''[{"question": "Test", "category": "behavioral", "duration": 3, "key_points": []}]'''
        gemini_service.model.generate_content.return_value = mock_response
        
        # First call
        questions1 = gemini_service.generate_questions("Developer", "intermediate", "behavioral", 1)
        
        # Second call with same parameters
        questions2 = gemini_service.generate_questions("Developer", "intermediate", "behavioral", 1)
        
        # Should use cache for second call
        assert questions1 == questions2
        assert gemini_service.model.generate_content.call_count == 1
    
    def test_parse_questions_response_invalid_json(self, gemini_service, mock_db):
        """Test parsing invalid JSON response"""
        invalid_json = "This is not valid JSON"
        
        questions = gemini_service._parse_questions_response(invalid_json)
        
        assert questions == []
    
    def test_build_question_prompt(self, gemini_service, mock_db):
        """Test question prompt building"""
        prompt = gemini_service._build_question_prompt(
            role="Software Developer",
            difficulty="intermediate",
            question_type="technical",
            count=5
        )
        
        assert "Software Developer" in prompt
        assert "intermediate" in prompt
        assert "technical" in prompt
        assert "5" in prompt
    
    def test_store_questions_in_database(self, gemini_service, mock_db):
        """Test storing questions in database"""
        questions_data = [
            {
                'question': 'Test question',
                'category': 'behavioral',
                'duration': 3,
                'key_points': ['point1', 'point2']
            }
        ]
        
        gemini_service._store_questions(questions_data, "Developer", "intermediate", "behavioral")
        
        # Verify database operations
        assert mock_db.add.called
        assert mock_db.commit.called