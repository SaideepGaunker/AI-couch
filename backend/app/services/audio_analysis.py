"""
Audio Analysis Service for Interview Tone and Confidence Assessment
"""
import librosa
import numpy as np
from typing import Dict, Any, Tuple
import logging
from pathlib import Path
import tempfile
import os

logger = logging.getLogger(__name__)


class AudioAnalyzer:
    """
    Analyzes audio files to extract tone and confidence metrics
    """
    
    def __init__(self):
        self.sample_rate = 22050
        self.hop_length = 512
        self.n_mfcc = 13
        
    def extract_audio_features(self, audio_path: str) -> Dict[str, Any]:
        """
        Extract comprehensive audio features from the audio file
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Dictionary containing extracted features
        """
        try:
            # Load audio file
            y, sr = librosa.load(audio_path, sr=self.sample_rate)
            
            # Extract MFCC features
            mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=self.n_mfcc, hop_length=self.hop_length)
            mfcc_mean = np.mean(mfccs, axis=1)
            mfcc_std = np.std(mfccs, axis=1)
            
            # Extract pitch (fundamental frequency)
            pitches, magnitudes = librosa.piptrack(y=y, sr=sr, hop_length=self.hop_length)
            pitch_values = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_values.append(pitch)
            
            pitch_mean = np.mean(pitch_values) if pitch_values else 0
            pitch_std = np.std(pitch_values) if pitch_values else 0
            
            # Extract energy/power
            rms = librosa.feature.rms(y=y, hop_length=self.hop_length)[0]
            energy_mean = np.mean(rms)
            energy_std = np.std(rms)
            
            # Extract tempo
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            
            # Extract spectral features
            spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
            zero_crossing_rate = librosa.feature.zero_crossing_rate(y)[0]
            
            # Calculate speech rate (approximate)
            duration = len(y) / sr
            speech_rate = len(pitch_values) / duration if duration > 0 else 0
            
            # Detect pauses (silence detection)
            silence_threshold = np.percentile(rms, 20)
            silence_frames = np.sum(rms < silence_threshold)
            pause_ratio = silence_frames / len(rms) if len(rms) > 0 else 0
            
            features = {
                'mfcc_mean': mfcc_mean.tolist(),
                'mfcc_std': mfcc_std.tolist(),
                'pitch_mean': float(pitch_mean),
                'pitch_std': float(pitch_std),
                'energy_mean': float(energy_mean),
                'energy_std': float(energy_std),
                'tempo': float(tempo),
                'spectral_centroid_mean': float(np.mean(spectral_centroids)),
                'spectral_rolloff_mean': float(np.mean(spectral_rolloff)),
                'zero_crossing_rate_mean': float(np.mean(zero_crossing_rate)),
                'speech_rate': float(speech_rate),
                'pause_ratio': float(pause_ratio),
                'duration': float(duration)
            }
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting audio features: {str(e)}")
            raise
    
    def analyze_tone_confidence(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze tone and confidence based on extracted features
        
        Args:
            features: Dictionary of extracted audio features
            
        Returns:
            Dictionary containing tone confidence score and suggestions
        """
        try:
            # Initialize scoring components
            clarity_score = 0
            confidence_score = 0
            speech_rate_score = 0
            enunciation_score = 0
            
            # Analyze clarity (based on spectral features and energy)
            energy_mean = features['energy_mean']
            spectral_centroid = features['spectral_centroid_mean']
            
            # Higher energy and balanced spectral centroid indicate clearer speech
            if energy_mean > 0.02:  # Good energy level
                clarity_score += 30
            elif energy_mean > 0.01:
                clarity_score += 20
            else:
                clarity_score += 10
                
            # Spectral centroid in optimal range (1000-3000 Hz for clear speech)
            if 1000 <= spectral_centroid <= 3000:
                clarity_score += 20
            elif 800 <= spectral_centroid <= 4000:
                clarity_score += 15
            else:
                clarity_score += 5
            
            # Analyze confidence (based on pitch stability and energy consistency)
            pitch_std = features['pitch_std']
            energy_std = features['energy_std']
            
            # Lower pitch variation indicates more confident speech
            if pitch_std < 20:
                confidence_score += 25
            elif pitch_std < 40:
                confidence_score += 20
            else:
                confidence_score += 10
                
            # Consistent energy indicates confidence
            if energy_std < 0.01:
                confidence_score += 25
            elif energy_std < 0.02:
                confidence_score += 20
            else:
                confidence_score += 10
            
            # Analyze speech rate
            speech_rate = features['speech_rate']
            pause_ratio = features['pause_ratio']
            
            # Optimal speech rate (2-4 words per second approximately)
            if 2 <= speech_rate <= 4:
                speech_rate_score += 25
            elif 1.5 <= speech_rate <= 5:
                speech_rate_score += 20
            else:
                speech_rate_score += 10
                
            # Good pause ratio (10-30% pauses)
            if 0.1 <= pause_ratio <= 0.3:
                speech_rate_score += 15
            elif 0.05 <= pause_ratio <= 0.4:
                speech_rate_score += 10
            else:
                speech_rate_score += 5
            
            # Analyze enunciation (based on zero crossing rate and MFCC features)
            zcr_mean = features['zero_crossing_rate_mean']
            mfcc_std_avg = np.mean(features['mfcc_std'])
            
            # Optimal zero crossing rate for clear enunciation
            if 0.05 <= zcr_mean <= 0.15:
                enunciation_score += 20
            elif 0.03 <= zcr_mean <= 0.2:
                enunciation_score += 15
            else:
                enunciation_score += 10
                
            # MFCC variation indicates good articulation
            if mfcc_std_avg > 10:
                enunciation_score += 20
            elif mfcc_std_avg > 5:
                enunciation_score += 15
            else:
                enunciation_score += 10
            
            # Calculate overall score (weighted average)
            total_score = (clarity_score * 0.3 + confidence_score * 0.35 + 
                          speech_rate_score * 0.2 + enunciation_score * 0.15)
            
            # Normalize to 0-100 scale
            tone_confidence_score = min(100, max(0, int(total_score)))
            
            # Generate improvement suggestions
            suggestions = self._generate_suggestions(
                features, clarity_score, confidence_score, 
                speech_rate_score, enunciation_score
            )
            
            return {
                "tone_confidence_score": tone_confidence_score,
                "improvement_suggestions": suggestions
            }
            
        except Exception as e:
            logger.error(f"Error analyzing tone confidence: {str(e)}")
            raise
    
    def _generate_suggestions(self, features: Dict[str, Any], clarity: int, 
                            confidence: int, speech_rate: int, enunciation: int) -> str:
        """Generate personalized improvement suggestions"""
        suggestions = []
        
        # Clarity suggestions
        if clarity < 25:
            if features['energy_mean'] < 0.01:
                suggestions.append("Speak louder and project your voice more clearly")
            if features['spectral_centroid_mean'] < 1000:
                suggestions.append("Focus on clearer articulation of consonants")
        
        # Confidence suggestions
        if confidence < 25:
            if features['pitch_std'] > 40:
                suggestions.append("Try to maintain a steadier tone - avoid excessive pitch variations")
            if features['energy_std'] > 0.02:
                suggestions.append("Work on maintaining consistent volume throughout your response")
        
        # Speech rate suggestions
        if speech_rate < 20:
            if features['speech_rate'] > 4:
                suggestions.append("Slow down your speech pace - you're speaking too quickly")
            elif features['speech_rate'] < 2:
                suggestions.append("Increase your speech pace slightly - you're speaking too slowly")
            if features['pause_ratio'] < 0.1:
                suggestions.append("Add more strategic pauses for emphasis and clarity")
            elif features['pause_ratio'] > 0.3:
                suggestions.append("Reduce excessive pauses - maintain better flow")
        
        # Enunciation suggestions
        if enunciation < 15:
            suggestions.append("Focus on clearer pronunciation and word articulation")
            suggestions.append("Practice enunciating the endings of words more clearly")
        
        # General suggestions based on overall performance
        if all(score < 20 for score in [clarity, confidence, speech_rate, enunciation]):
            suggestions.append("Consider practicing with voice exercises and recording yourself")
        
        if not suggestions:
            suggestions.append("Great job! Your tone and confidence are strong. Keep practicing to maintain this level.")
        
        return " ".join(suggestions)
    
    def process_audio_file(self, audio_path: str) -> Dict[str, Any]:
        """
        Complete audio processing pipeline
        
        Args:
            audio_path: Path to the audio file
            
        Returns:
            Dictionary containing tone confidence score and suggestions
        """
        try:
            # Extract features
            features = self.extract_audio_features(audio_path)
            
            # Analyze tone and confidence
            result = self.analyze_tone_confidence(features)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing audio file: {str(e)}")
            return {
                "tone_confidence_score": 0,
                "improvement_suggestions": "Unable to analyze audio. Please ensure the audio file is clear and in a supported format."
            }