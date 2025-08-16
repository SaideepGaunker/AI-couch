"""
Body Language Analysis Service using Hugging Face model
"""
import os
import logging
from typing import Dict, Any, List
import numpy as np

logger = logging.getLogger(__name__)

class BodyLanguageAnalyzer:
    """Analyzes body language using pre-trained model"""
    
    def __init__(self):
        self.model = None
        self.is_loaded = False
        self._load_model()
    
    def _load_model(self):
        """Load the body language detection model"""
        try:
            # Set Keras backend
            os.environ["KERAS_BACKEND"] = "jax"
            
            import keras
            
            # Load model from Hugging Face
            model_path = "hf://ThisIs-Developer/Body-Language-Detection-with-MediaPipe-and-OpenCV"
            self.model = keras.saving.load_model(model_path)
            self.is_loaded = True
            logger.info("Body language model loaded successfully")
            
        except ImportError as e:
            logger.error(f"Failed to import keras: {e}")
            logger.info("Install with: pip install keras jax jaxlib huggingface-hub")
        except Exception as e:
            logger.error(f"Failed to load body language model: {e}")
            self.is_loaded = False
    
    def analyze_frame(self, frame_data: np.ndarray) -> Dict[str, Any]:
        """Analyze a single frame for body language"""
        if not self.is_loaded or self.model is None:
            return {
                "confidence": 0.0,
                "body_language": "unknown",
                "error": "Model not loaded"
            }
        
        try:
            # Preprocess frame (adjust based on your model's input requirements)
            processed_frame = self._preprocess_frame(frame_data)
            
            # Make prediction
            prediction = self.model.predict(processed_frame, verbose=0)
            
            # Process results (adjust based on your model's output format)
            result = self._process_prediction(prediction)
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing frame: {e}")
            return {
                "confidence": 0.0,
                "body_language": "error",
                "error": str(e)
            }
    
    def _preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """Preprocess frame for model input"""
        # Add your preprocessing logic here
        # This depends on what your model expects
        # Example: resize, normalize, reshape, etc.
        return frame
    
    def _process_prediction(self, prediction: np.ndarray) -> Dict[str, Any]:
        """Process model prediction into readable format"""
        # Add your post-processing logic here
        # This depends on your model's output format
        # Example: convert probabilities to labels, etc.
        return {
            "confidence": float(np.max(prediction)),
            "body_language": "analyzed",
            "raw_prediction": prediction.tolist()
        }
    
    def analyze_session(self, frames: List[np.ndarray]) -> Dict[str, Any]:
        """Analyze multiple frames for session-level insights"""
        if not frames:
            return {"error": "No frames provided"}
        
        results = []
        for frame in frames:
            result = self.analyze_frame(frame)
            results.append(result)
        
        # Aggregate results
        avg_confidence = np.mean([r.get("confidence", 0) for r in results])
        
        return {
            "frame_count": len(frames),
            "average_confidence": float(avg_confidence),
            "frame_analyses": results,
            "session_summary": "Body language analysis completed"
        }