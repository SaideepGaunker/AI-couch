
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.gemini_service import GeminiService
from app.core.dependencies import get_current_user
from app.db.models import User

router = APIRouter()

@router.get("/debug/gemini")
async def debug_gemini_api(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Debug endpoint to test Gemini API functionality"""
    
    try:
        gemini_service = GeminiService(db)
        
        # Test 1: Check if API is configured
        if not gemini_service.model:
            return {
                "status": "error",
                "message": "Gemini API not configured or model not initialized",
                "api_key_configured": bool(gemini_service.model)
            }
        
        # Test 2: Simple API call
        try:
            response = gemini_service.model.generate_content(
                "Generate 1 simple technical interview question for a Python developer. Format as JSON: {'question': 'text', 'category': 'technical', 'duration': 3}",
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 500,
                }
            )
            
            response_text = ""
            if hasattr(response, 'text') and response.text:
                response_text = response.text
            elif hasattr(response, 'candidates') and response.candidates:
                if hasattr(response.candidates[0], 'content'):
                    response_text = response.candidates[0].content.parts[0].text
            
            return {
                "status": "success",
                "message": "Gemini API is working correctly",
                "api_response": response_text[:200] + "..." if len(response_text) > 200 else response_text,
                "response_length": len(response_text)
            }
            
        except Exception as api_error:
            return {
                "status": "error", 
                "message": f"Gemini API call failed: {str(api_error)}",
                "error_type": type(api_error).__name__
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Service initialization failed: {str(e)}",
            "error_type": type(e).__name__
        }
