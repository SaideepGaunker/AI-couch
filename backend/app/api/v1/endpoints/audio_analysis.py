"""
Audio Analysis API endpoints
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from sqlalchemy.orm import Session
import tempfile
import os
from pathlib import Path
import logging

from app.db.database import get_db
from app.services.tone_analysis_service import ToneAnalyzer
from app.crud import performance_metrics as crud_performance
from app.schemas.audio_analysis import AudioAnalysisResponse, AudioAnalysisRequest
from app.core.dependencies import get_current_user
from app.db.models import User

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize tone analyzer
tone_analyzer = ToneAnalyzer()

# Supported audio formats
SUPPORTED_FORMATS = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.aac'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/analyze", response_model=AudioAnalysisResponse)
async def analyze_audio(
    audio_file: UploadFile = File(...),
    session_id: int = None,
    question_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze audio file for tone and confidence metrics
    
    Args:
        audio_file: Uploaded audio file
        session_id: Optional interview session ID to save results
        question_id: Optional question ID to associate with results
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        AudioAnalysisResponse with tone confidence score and suggestions
    """
    try:
        # Validate file format
        file_extension = Path(audio_file.filename).suffix.lower()
        if file_extension not in SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported audio format. Supported formats: {', '.join(SUPPORTED_FORMATS)}"
            )
        
        # Check file size
        if audio_file.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
            )
        
        # Create temporary file to store uploaded audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            # Read and write audio content
            content = await audio_file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Process audio file
            logger.info(f"Processing audio file: {audio_file.filename}")
            
            # Read audio file content
            with open(temp_file_path, 'rb') as f:
                audio_bytes = f.read()
            
            # Analyze audio using tone analyzer
            analysis_result = tone_analyzer.analyze_complete_audio(audio_bytes)
            
            # If session_id and question_id are provided, save to database
            if session_id and question_id:
                # Check if performance metric already exists
                existing_metric = crud_performance.get_by_session_and_question(
                    db, session_id=session_id, question_id=question_id
                )
                
                if existing_metric:
                    # Update existing record
                    crud_performance.update_tone_confidence(
                        db, 
                        performance_id=existing_metric.id,
                        tone_score=analysis_result["tone_confidence_score"],
                        suggestions=analysis_result["improvement_suggestions"]
                    )
                    logger.info(f"Updated existing performance metric {existing_metric.id}")
                else:
                    # Create new performance metric record
                    new_metric = crud_performance.create_with_tone_analysis(
                        db,
                        session_id=session_id,
                        question_id=question_id,
                        tone_confidence_score=analysis_result["tone_confidence_score"],
                        improvement_suggestions=analysis_result["improvement_suggestions"]
                    )
                    logger.info(f"Created new performance metric {new_metric.id}")
                
                logger.info(f"Saved tone analysis results for session {session_id}, question {question_id}")
            
            return AudioAnalysisResponse(
                tone_confidence_score=int(analysis_result["tone_confidence_score"]),
                improvement_suggestions=analysis_result["improvement_suggestions"],
                success=True,
                message="Audio analysis completed successfully"
            )
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except OSError:
                logger.warning(f"Could not delete temporary file: {temp_file_path}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing audio: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during audio analysis"
        )


@router.post("/analyze-features", response_model=AudioAnalysisResponse)
async def analyze_audio_features(
    request: AudioAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze pre-extracted audio features for tone and confidence
    
    Args:
        request: AudioAnalysisRequest with extracted features
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        AudioAnalysisResponse with tone confidence score and suggestions
    """
    try:
        # For now, return a simple response since we're focusing on file upload analysis
        # This endpoint can be enhanced later for pre-extracted features
        return AudioAnalysisResponse(
            tone_confidence_score=75,
            improvement_suggestions="Feature-based analysis not yet implemented. Please use file upload.",
            success=True,
            message="Feature analysis endpoint available"
        )
        
    except Exception as e:
        logger.error(f"Error analyzing audio features: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during audio feature analysis"
        )


@router.get("/supported-formats")
async def get_supported_formats():
    """Get list of supported audio formats"""
    return {
        "supported_formats": list(SUPPORTED_FORMATS),
        "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024)
    }