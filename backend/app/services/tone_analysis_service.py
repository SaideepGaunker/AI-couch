"""
Tone and Confidence Analysis Service using pyAudioAnalysis
"""
import numpy as np
import librosa
import soundfile as sf
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import io

logger = logging.getLogger(__name__)


class ToneAnalyzer:
    """Tone and confidence analysis using audio processing"""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.confidence_history = []
        self.tone_history = []
        self.pace_history = []
        self.volume_history = []
    
    def analyze_audio_chunk(self, audio_data: bytes) -> Dict[str, Any]:
        """Analyze audio chunk for tone and confidence metrics"""
        try:
            # Convert bytes to numpy array
            audio_array = self._bytes_to_audio_array(audio_data)
            
            if len(audio_array) == 0:
                return self._get_default_metrics()
            
            # Extract audio features
            confidence_score = self._analyze_confidence(audio_array)
            tone_score = self._analyze_tone_quality(audio_array)
            pace_score = self._analyze_speaking_pace(audio_array)
            volume_score = self._analyze_volume_consistency(audio_array)
            
            # Calculate overall score
            overall_score = (
                confidence_score * 0.4 +
                tone_score * 0.3 +
                pace_score * 0.2 +
                volume_score * 0.1
            )
            
            # Store in history
            self.confidence_history.append(confidence_score)
            self.tone_history.append(tone_score)
            self.pace_history.append(pace_score)
            self.volume_history.append(volume_score)
            
            # Keep only recent history
            max_history = 100
            if len(self.confidence_history) > max_history:
                self.confidence_history.pop(0)
                self.tone_history.pop(0)
                self.pace_history.pop(0)
                self.volume_history.pop(0)
            
            return {
                'overall_score': round(overall_score, 2),
                'confidence_score': round(confidence_score, 2),
                'tone_score': round(tone_score, 2),
                'pace_score': round(pace_score, 2),
                'volume_score': round(volume_score, 2),
                'timestamp': datetime.utcnow().isoformat(),
                'audio_analyzed': True
            }
            
        except Exception as e:
            logger.error(f"Error analyzing audio chunk: {e}")
            return self._get_default_metrics()
    
    def _bytes_to_audio_array(self, audio_data: bytes) -> np.ndarray:
        """Convert audio bytes to numpy array"""
        try:
            # Try to load as WAV format
            audio_io = io.BytesIO(audio_data)
            audio_array, sr = sf.read(audio_io)
            
            # Resample if necessary
            if sr != self.sample_rate:
                audio_array = librosa.resample(audio_array, orig_sr=sr, target_sr=self.sample_rate)
            
            # Convert to mono if stereo
            if len(audio_array.shape) > 1:
                audio_array = np.mean(audio_array, axis=1)
            
            return audio_array
            
        except Exception as e:
            logger.error(f"Error converting audio bytes: {e}")
            return np.array([])
    
    def _analyze_confidence(self, audio_array: np.ndarray) -> float:
        """Analyze confidence based on voice characteristics"""
        try:
            if len(audio_array) == 0:
                return 50.0
            
            # Extract features that indicate confidence
            
            # 1. Voice stability (low jitter)
            f0 = librosa.yin(audio_array, fmin=50, fmax=400, sr=self.sample_rate)
            f0_clean = f0[f0 > 0]  # Remove unvoiced frames
            
            if len(f0_clean) > 10:
                f0_stability = 100 - (np.std(f0_clean) / np.mean(f0_clean) * 100)
                f0_stability = max(0, min(100, f0_stability))
            else:
                f0_stability = 50.0
            
            # 2. Voice strength (RMS energy)
            rms = librosa.feature.rms(y=audio_array)[0]
            avg_rms = np.mean(rms)
            voice_strength = min(100, avg_rms * 1000)  # Scale to 0-100
            
            # 3. Spectral centroid (voice clarity)
            spectral_centroids = librosa.feature.spectral_centroid(y=audio_array, sr=self.sample_rate)[0]
            avg_centroid = np.mean(spectral_centroids)
            clarity_score = min(100, (avg_centroid - 1000) / 20)  # Normalize
            clarity_score = max(0, clarity_score)
            
            # Combine metrics
            confidence_score = (
                f0_stability * 0.4 +
                voice_strength * 0.4 +
                clarity_score * 0.2
            )
            
            return max(0, min(100, confidence_score))
            
        except Exception as e:
            logger.error(f"Error analyzing confidence: {e}")
            return 50.0
    
    def _analyze_tone_quality(self, audio_array: np.ndarray) -> float:
        """Analyze tone quality and pleasantness"""
        try:
            if len(audio_array) == 0:
                return 50.0
            
            # 1. Spectral rolloff (voice warmth)
            rolloff = librosa.feature.spectral_rolloff(y=audio_array, sr=self.sample_rate)[0]
            avg_rolloff = np.mean(rolloff)
            warmth_score = 100 - abs(avg_rolloff - 3000) / 50  # Optimal around 3kHz
            warmth_score = max(0, min(100, warmth_score))
            
            # 2. Zero crossing rate (voice smoothness)
            zcr = librosa.feature.zero_crossing_rate(audio_array)[0]
            avg_zcr = np.mean(zcr)
            smoothness_score = 100 - (avg_zcr * 1000)  # Lower ZCR = smoother
            smoothness_score = max(0, min(100, smoothness_score))
            
            # 3. Spectral bandwidth (voice richness)
            bandwidth = librosa.feature.spectral_bandwidth(y=audio_array, sr=self.sample_rate)[0]
            avg_bandwidth = np.mean(bandwidth)
            richness_score = min(100, avg_bandwidth / 30)  # Scale to 0-100
            
            # Combine metrics
            tone_score = (
                warmth_score * 0.4 +
                smoothness_score * 0.3 +
                richness_score * 0.3
            )
            
            return max(0, min(100, tone_score))
            
        except Exception as e:
            logger.error(f"Error analyzing tone quality: {e}")
            return 50.0
    
    def _analyze_speaking_pace(self, audio_array: np.ndarray) -> float:
        """Analyze speaking pace and rhythm"""
        try:
            if len(audio_array) == 0:
                return 50.0
            
            # Detect speech segments using energy-based VAD
            frame_length = int(0.025 * self.sample_rate)  # 25ms frames
            hop_length = int(0.01 * self.sample_rate)     # 10ms hop
            
            # Calculate RMS energy for each frame
            rms = librosa.feature.rms(
                y=audio_array, 
                frame_length=frame_length, 
                hop_length=hop_length
            )[0]
            
            # Simple voice activity detection
            threshold = np.mean(rms) * 0.3
            speech_frames = rms > threshold
            
            # Calculate speech rate
            total_frames = len(speech_frames)
            speech_ratio = np.sum(speech_frames) / total_frames if total_frames > 0 else 0
            
            # Optimal speech ratio is around 0.4-0.7 (40-70% of time speaking)
            if 0.4 <= speech_ratio <= 0.7:
                pace_score = 100
            elif speech_ratio < 0.4:
                pace_score = 100 - (0.4 - speech_ratio) * 200  # Too slow
            else:
                pace_score = 100 - (speech_ratio - 0.7) * 200  # Too fast
            
            return max(0, min(100, pace_score))
            
        except Exception as e:
            logger.error(f"Error analyzing speaking pace: {e}")
            return 50.0
    
    def _analyze_volume_consistency(self, audio_array: np.ndarray) -> float:
        """Analyze volume consistency and control"""
        try:
            if len(audio_array) == 0:
                return 50.0
            
            # Calculate RMS energy over time
            rms = librosa.feature.rms(y=audio_array)[0]
            
            # Remove silent parts
            rms_voiced = rms[rms > np.mean(rms) * 0.1]
            
            if len(rms_voiced) < 5:
                return 50.0
            
            # Calculate volume consistency (lower std = more consistent)
            volume_std = np.std(rms_voiced)
            volume_mean = np.mean(rms_voiced)
            
            # Coefficient of variation
            cv = volume_std / volume_mean if volume_mean > 0 else 1
            
            # Convert to score (lower CV = higher score)
            consistency_score = max(0, 100 - (cv * 200))
            
            return min(100, consistency_score)
            
        except Exception as e:
            logger.error(f"Error analyzing volume consistency: {e}")
            return 50.0
    
    def get_confidence_score(self, audio_session: List[bytes]) -> float:
        """Calculate overall confidence score for entire audio session"""
        try:
            if not audio_session:
                return 50.0
            
            # Analyze each chunk and get average
            chunk_scores = []
            for chunk in audio_session:
                metrics = self.analyze_audio_chunk(chunk)
                chunk_scores.append(metrics['confidence_score'])
            
            if not chunk_scores:
                return 50.0
            
            # Calculate weighted average (recent chunks have more weight)
            weights = np.li