"""
Audio Analysis Schemas
"""
from pydantic import BaseModel
from typing import Dict, Any, Optional


class AudioAnalysisRequest(BaseModel):
    """Request schema for audio feature analysis"""
    features: Dict[str, Any]
    session_id: Optional[int] = None
    question_id: Optional[int] = None


class AudioAnalysisResponse(BaseModel):
    """Response schema for audio analysis"""
    tone_confidence_score: int
    improvement_suggestions: str
    success: bool = True
    message: str = "Analysis completed successfully"


class AudioFeatures(BaseModel):
    """Schema for extracted audio features"""
    mfcc_mean: list
    mfcc_std: list
    pitch_mean: float
    pitch_std: float
    energy_mean: float
    energy_std: float
    tempo: float
    spectral_centroid_mean: float
    spectral_rolloff_mean: float
    zero_crossing_rate_mean: float
    speech_rate: float
    pause_ratio: float
    duration: float