"""
Main API router for v1 endpoints
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, interviews, questions, feedback, analytics, admin, voice_analysis

api_router = APIRouter()

# Include core endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(interviews.router, prefix="/interviews", tags=["interviews"])
api_router.include_router(questions.router, prefix="/questions", tags=["questions"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(voice_analysis.router, prefix="/interviews", tags=["voice-analysis"])

# Try to include posture router (optional due to MediaPipe dependency)
try:
    from app.api.v1.endpoints import posture
    api_router.include_router(posture.router, prefix="/posture", tags=["posture"])
    print("✅ Posture analysis module loaded successfully")
except ImportError as e:
    print(f"⚠️  Posture analysis module not available: {e}")
    print("   Install MediaPipe: pip install mediapipe")
except Exception as e:
    print(f"⚠️  Posture analysis module failed to load: {e}")
    print("   Check protobuf version: pip install protobuf==3.20.3")

# Try to include audio analysis router (optional due to dependency issues)
try:
    from app.api.v1.endpoints import audio_analysis
    api_router.include_router(audio_analysis.router, prefix="/audio", tags=["audio-analysis"])
    print("✅ Audio analysis module loaded successfully")
except ImportError as e:
    print(f"⚠️  Audio analysis module not available: {e}")
    print("   Install audio dependencies: pip install librosa soundfile")
except Exception as e:
    print(f"⚠️  Audio analysis module failed to load: {e}")
    print("   Check protobuf version: pip install protobuf==3.20.3")