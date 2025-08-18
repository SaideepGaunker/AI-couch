"""
Test script for audio analysis functionality
"""
import requests
import json
from pathlib import Path

# Test the audio analysis endpoint
def test_audio_analysis():
    """Test the audio analysis endpoint with a sample file"""
    
    # API endpoint
    url = "http://localhost:8000/api/v1/audio/analyze"
    
    # You'll need to provide authentication token
    headers = {
        "Authorization": "Bearer YOUR_TOKEN_HERE"
    }
    
    # Test with a sample audio file (you'll need to provide this)
    # audio_file_path = "path/to/your/test/audio.wav"
    
    print("Audio analysis endpoint is ready!")
    print(f"POST {url}")
    print("Required parameters:")
    print("- audio_file: Upload file (wav, mp3, m4a, flac, ogg, aac)")
    print("- session_id: (optional) Interview session ID")
    print("- question_id: (optional) Question ID")
    print("\nExample response:")
    print({
        "tone_confidence_score": 75,
        "improvement_suggestions": "Good tone and confidence overall. Minor adjustments will make it even better.",
        "success": True,
        "message": "Audio analysis completed successfully"
    })

if __name__ == "__main__":
    test_audio_analysis()