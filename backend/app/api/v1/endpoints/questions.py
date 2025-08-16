"""
Question generation and management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.schemas.question import (
    QuestionGenerate, QuestionResponse, QuestionSearch, QuestionCreate
)
from app.core.dependencies import get_current_user, require_admin, rate_limit
from app.services.gemini_service import GeminiService
from app.services.question_service import QuestionService
from app.db.models import User

router = APIRouter()


@router.post("/generate", response_model=List[QuestionResponse])
async def generate_questions(
    question_request: QuestionGenerate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(max_calls=10, window_seconds=300))
):
    """Generate AI-powered interview questions"""
    question_service = QuestionService(db)
    
    try:
        questions = question_service.generate_and_store_questions(
            role=question_request.role,
            difficulty=question_request.difficulty,
            question_type=question_request.question_type,
            count=question_request.count
        )
        
        return questions
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate questions"
        )


@router.get("/", response_model=List[QuestionResponse])
async def get_questions(
    role_category: Optional[str] = Query(None),
    question_type: Optional[str] = Query(None),
    difficulty_level: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get questions with filtering options"""
    question_service = QuestionService(db)
    
    search_params = QuestionSearch(
        role_category=role_category,
        question_type=question_type,
        difficulty_level=difficulty_level,
        limit=limit,
        offset=offset
    )
    
    try:
        questions = question_service.get_questions(search_params)
        return questions
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve questions"
        )


@router.get("/random", response_model=List[QuestionResponse])
async def get_random_questions(
    role_category: Optional[str] = Query(None),
    question_type: Optional[str] = Query(None),
    difficulty_level: Optional[str] = Query(None),
    count: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get random questions for practice"""
    question_service = QuestionService(db)
    
    try:
        questions = question_service.get_random_questions(
            role_category=role_category,
            question_type=question_type,
            difficulty_level=difficulty_level,
            count=count
        )
        
        return questions
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve random questions"
        )


@router.get("/search", response_model=List[QuestionResponse])
async def search_questions(
    q: str = Query(..., min_length=3),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search questions by content"""
    question_service = QuestionService(db)
    
    try:
        questions = question_service.search_questions(q, limit)
        return questions
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search questions"
        )


@router.get("/statistics")
async def get_question_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get question database statistics"""
    question_service = QuestionService(db)
    
    try:
        stats = question_service.get_statistics()
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific question by ID"""
    question_service = QuestionService(db)
    
    try:
        question = question_service.get_question_by_id(question_id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found"
            )
        
        return question
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve question"
        )


# Admin endpoints
@router.post("/", response_model=QuestionResponse)
async def create_question(
    question: QuestionCreate,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create new question (admin only)"""
    question_service = QuestionService(db)
    
    try:
        created_question = question_service.create_question(question)
        return created_question
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create question"
        )


@router.put("/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: int,
    question_data: dict,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update question (admin only)"""
    question_service = QuestionService(db)
    
    try:
        updated_question = question_service.update_question(question_id, question_data)
        if not updated_question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found"
            )
        
        return updated_question
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update question"
        )


@router.delete("/{question_id}")
async def delete_question(
    question_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete question (admin only)"""
    question_service = QuestionService(db)
    
    try:
        success = question_service.delete_question(question_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found"
            )
        
        return {"message": "Question deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete question"
        )