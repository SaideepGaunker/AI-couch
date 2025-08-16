"""
Audio Analysis Service using pyAudioAnalysis for tone and confidence scoring
"""
import numpy as np
import librosa
import logging
from typing import Dict, Any, List, Optional
import base64
import io
import wave
from scipy import stats
from scipy.signal import find_peaks

logger = logging.getLogger(__name__)


class ToneAnalyzer:
    """Audio analysis for tone, pace, and confidence scoring"""
    
    def __init__(self):
        self.sample_rate = 16000  # Standard sample rate
        self.session_metrics = {
            'audio_chunks': [],
            'confidence_scores': [],
            'pace_scores': [],
            'tone_scores': [],
            'volume_levels': []
        }
    
    def analyze_audio_chunk(self, audio_data: bytes) -> Dict[str, Any]:
        """Analyze audio chunk for tone and confidence metrics"""
        try:
            # Decode audio data
            audio_array = self._decode_audio(audio_data)
            if audio_array is None or len(audio_array) == 0:
                return self._get_default_audio_metrics()
            
            # Extract audio features
            features = self._extract_audio_features(audio_array)
            
            # Calculate metrics
            confidence_score = self._calculate_confidence_score(features)
            tone_score = self._calculate_tone_score(features)
            pace_score = self._calculate_pace_score(features)
            volume_score = self._calculate_volume_score(features)
            
            # Generate feedback
            feedback = self._generate_audio_feedback(
                confidence_score, tone_score, pace_score, volume_score
            )
            
            # Update session metrics
            self._update_session_metrics({
                'confidence': confidence_score,
                'tone': tone_score,
                'pace': pace_score,
                'volume': volume_score
            })
            
            return {
                'confidence_score': confidence_score,
                'tone_score': tone_score,
                'pace_score': pace_score,
                'volume_score': volume_score,
                'overall_audio_score': (confidence_score + tone_score + pace_score) / 3,
                'feedback': feedback,
                'features': {
                    'pitch_mean': features.get('pitch_mean', 0),
                    'pitch_std': features.get('pitch_std', 0),
                    'energy_mean': features.get('energy_mean', 0),
                    'speaking_rate': features.get('speaking_rate', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing audio chunk: {str(e)}")
            return self._get_default_audio_metrics()
    
    def _decode_audio(self, audio_data: bytes) -> Optional[np.ndarray]:
        """Decode audio data to numpy array"""
        try:
            # Handle base64 encoded audio
            if isinstance(audio_data, str):
                if audio_data.startswith('data:audio'):
                    audio_data = audio_data.split(',')[1]
                audio_bytes = base64.b64decode(audio_data)
            else:
                audio_bytes = audio_data
            
            # Create BytesIO object
            audio_io = io.BytesIO(audio_bytes)
            
            # Try to load as WAV file
            try:
                with wave.open(audio_io, 'rb') as wav_file:
                    frames = wav_file.readframes(-1)
                    audio_array = np.frombuffer(frames, dtype=np.int16)
                    
                    # Convert to float and normalize
                    audio_array = audio_array.astype(np.float32) / 32768.0
                    
                    return audio_array
            except:
                # Try using librosa for other formats
                audio_array, sr = librosa.load(audio_io, sr=self.sample_rate)
                return audio_array
                
        except Exception as e:
            logger.error(f"Error decoding audio: {str(e)}")
            return None
    
    def _extract_audio_features(self, audio_array: np.ndarray) -> Dict[str, Any]:
        """Extract comprehensive audio features"""
        try:
            features = {}
            
            # Basic audio properties
            features['duration'] = len(audio_array) / self.sample_rate
            features['energy_mean'] = np.mean(audio_array ** 2)
            features['energy_std'] = np.std(audio_array ** 2)
            
            # Pitch analysis using librosa
            pitches, magnitudes = librosa.piptrack(
                y=audio_array, 
                sr=self.sample_rate,
                threshold=0.1
            )
            
            # Extract pitch values
            pitch_values = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_values.append(pitch)
            
            if pitch_values:
                features['pitch_mean'] = np.mean(pitch_values)
                features['pitch_std'] = np.std(pitch_values)
                features['pitch_range'] = np.max(pitch_values) - np.min(pitch_values)
            else:
                features['pitch_mean'] = 0
                features['pitch_std'] = 0
                features['pitch_range'] = 0
            
            # Spectral features
            spectral_centroids = librosa.feature.spectral_centroid(
                y=audio_array, sr=self.sample_rate
            )[0]
            features['spectral_centroid_mean'] = np.mean(spectral_centroids)
            features['spectral_centroid_std'] = np.std(spectral_centroids)
            
            # Zero crossing rate (indicator of speech vs silence)
            zcr = librosa.feature.zero_crossing_rate(audio_array)[0]
            features['zcr_mean'] = np.mean(zcr)
            
            # MFCC features (Mel-frequency cepstral coefficients)
            mfccs = librosa.feature.mfcc(y=audio_array, sr=self.sample_rate, n_mfcc=13)
            features['mfcc_mean'] = np.mean(mfccs, axis=1)
            features['mfcc_std'] = np.std(mfccs, axis=1)
            
            # Speaking rate estimation
            features['speaking_rate'] = self._estimate_speaking_rate(audio_array)
            
            # Voice activity detection
            features['voice_activity_ratio'] = self._calculate_voice_activity_ratio(audio_array)
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting audio features: {str(e)}")
            return {}
    
    def _estimate_speaking_rate(self, audio_array: np.ndarray) -> float:
        """Estimate speaking rate (words per minute)"""
        try:
            # Simple syllable counting based on energy peaks
            # This is a simplified approach - more sophisticated methods exist
            
            # Apply smoothing
            window_size = int(0.1 * self.sample_rate)  # 100ms window
            energy = np.convolve(audio_array ** 2, np.ones(window_size), mode='same')
            
            # Find peaks (potential syllables)
            peaks, _ = find_peaks(energy, height=np.mean(energy) * 0.5, distance=window_size//2)
            
            # Estimate syllables per second
            duration = len(audio_array) / self.sample_rate
            syllables_per_second = len(peaks) / duration if duration > 0 else 0
            
            # Convert to approximate words per minute (assuming ~1.5 syllables per word)
            words_per_minute = syllables_per_second * 60 / 1.5
            
            return min(300, max(0, words_per_minute))  # Cap at reasonable range
            
        except Exception as e:
            logger.error(f"Error estimating speaking rate: {str(e)}")
            return 120  # Default speaking rate
    
    def _calculate_voice_activity_ratio(self, audio_array: np.ndarray) -> float:
        """Calculate ratio of speech to silence"""
        try:
            # Simple voice activity detection based on energy threshold
            energy = audio_array ** 2
            threshold = np.mean(energy) * 0.1
            
            voice_frames = np.sum(energy > threshold)
            total_frames = len(energy)
            
            return voice_frames / total_frames if total_frames > 0 else 0
            
        except Exception as e:
            logger.error(f"Error calculating voice activity ratio: {str(e)}")
            return 0.5
    
    def _calculate_confidence_score(self, features: Dict[str, Any]) -> float:
        """Calculate confidence score based on audio features"""
        try:
            score = 50  # Base score
            
            # Volume/energy confidence
            energy_mean = features.get('energy_mean', 0)
            if 0.01 < energy_mean < 0.1:  # Good energy range
                score += 20
            elif energy_mean > 0.001:  # At least some energy
                score += 10
            
            # Pitch stability (less variation = more confident)
            pitch_std = features.get('pitch_std', 0)
            pitch_mean = features.get('pitch_mean', 0)
            if pitch_mean > 0:
                pitch_cv = pitch_std / pitch_mean  # Coefficient of variation
                if pitch_cv < 0.2:  # Stable pitch
                    score += 15
                elif pitch_cv < 0.4:
                    score += 10
            
            # Speaking rate (moderate pace = more confident)
            speaking_rate = features.get('speaking_rate', 120)
            if 100 <= speaking_rate <= 180:  # Optimal range
                score += 15
            elif 80 <= speaking_rate <= 220:  # Acceptable range
                score += 10
            
            # Voice activity (confident speakers have good voice activity)
            voice_activity = features.get('voice_activity_ratio', 0.5)
            if voice_activity > 0.7:
                score += 10
            elif voice_activity > 0.5:
                score += 5
            
            return min(100, max(0, score))
            
        except Exception as e:
            logger.error(f"Error calculating confidence score: {str(e)}")
            return 50.0
    
    def _calculate_tone_score(self, features: Dict[str, Any]) -> float:
        """Calculate tone quality score"""
        try:
            score = 50  # Base score
            
            # Pitch analysis for tone quality
            pitch_mean = features.get('pitch_mean', 0)
            if pitch_mean > 0:
                # Optimal pitch range varies by gender, but we'll use general ranges
                if 80 <= pitch_mean <= 300:  # Good pitch range
                    score += 20
                elif 60 <= pitch_mean <= 400:  # Acceptable range
                    score += 15
            
            # Spectral centroid (brightness/clarity of voice)
            spectral_centroid = features.get('spectral_centroid_mean', 0)
            if 1000 <= spectral_centroid <= 4000:  # Clear voice range
                score += 15
            elif 500 <= spectral_centroid <= 6000:  # Acceptable range
                score += 10
            
            # MFCC analysis for voice quality
            mfcc_mean = features.get('mfcc_mean', np.array([]))
            if len(mfcc_mean) > 0:
                # First MFCC coefficient relates to overall energy
                if -20 <= mfcc_mean[0] <= 0:  # Good energy balance
                    score += 15
            
            return min(100, max(0, score))
            
        except Exception as e:
            logger.error(f"Error calculating tone score: {str(e)}")
            return 50.0
    
    def _calculate_pace_score(self, features: Dict[str, Any]) -> float:
        """Calculate speaking pace score"""
        try:
            speaking_rate = features.get('speaking_rate', 120)
            
            # Optimal speaking rate for interviews is typically 140-180 WPM
            if 140 <= speaking_rate <= 180:
                return 100
            elif 120 <= speaking_rate <= 200:
                return 85
            elif 100 <= speaking_rate <= 220:
                return 70
            elif 80 <= speaking_rate <= 250:
                return 55
            else:
                return 40
                
        except Exception as e:
            logger.error(f"Error calculating pace score: {str(e)}")
            return 50.0
    
    def _calculate_volume_score(self, features: Dict[str, Any]) -> float:
        """Calculate volume appropriateness score"""
        try:
            energy_mean = features.get('energy_mean', 0)
            
            # Optimal energy range (these values may need calibration)
            if 0.01 <= energy_mean <= 0.1:
                return 100
            elif 0.005 <= energy_mean <= 0.2:
                return 85
            elif 0.001 <= energy_mean <= 0.3:
                return 70
            else:
                return 50
                
        except Exception as e:
            logger.error(f"Error calculating volume score: {str(e)}")
            return 50.0
    
    def _generate_audio_feedback(
        self, 
        confidence_score: float, 
        tone_score: float, 
        pace_score: float, 
        volume_score: float
    ) -> str:
        """Generate audio feedback based on scores"""
        feedback_parts = []
        
        if confidence_score < 60:
            feedback_parts.append("Speak with more confidence and conviction")
        elif confidence_score > 85:
            feedback_parts.append("Great confidence in your voice!")
        
        if tone_score < 60:
            feedback_parts.append("Work on voice clarity and tone quality")
        elif tone_score > 85:
            feedback_parts.append("Excellent voice tone and clarity!")
        
        if pace_score < 60:
            speaking_rate = self.session_metrics.get('pace_scores', [120])[-1] if self.session_metrics.get('pace_scores') else 120
            if speaking_rate < 100:
                feedback_parts.append("Speak a bit faster - your pace is too slow")
            else:
                feedback_parts.append("Slow down your speaking pace")
        elif pace_score > 85:
            feedback_parts.append("Perfect speaking pace!")
        
        if volume_score < 60:
            feedback_parts.append("Adjust your volume - speak clearly and audibly")
        elif volume_score > 85:
            feedback_parts.append("Good volume level!")
        
        return "; ".join(feedback_parts) if feedback_parts else "Good overall audio quality!"
    
    def _update_session_metrics(self, metrics: Dict[str, float]):
        """Update session-level audio metrics"""
        self.session_metrics['confidence_scores'].append(metrics['confidence'])
        self.session_metrics['tone_scores'].append(metrics['tone'])
        self.session_metrics['pace_scores'].append(metrics['pace'])
        self.session_metrics['volume_levels'].append(metrics['volume'])
    
    def get_confidence_score(self, audio_session: Dict[str, Any]) -> float:
        """Get overall confidence score for the session"""
        if not self.session_metrics['confidence_scores']:
            return 50.0
        
        return np.mean(self.session_metrics['confidence_scores'])
    
    def get_session_audio_report(self, session_id: str) -> Dict[str, Any]:
        """Generate comprehensive audio analysis report for the session"""
        if not self.session_metrics['confidence_scores']:
            return {
                'session_id': session_id,
                'error': 'No audio data analyzed',
                'recommendations': ['Ensure microphone is working and positioned correctly']
            }
        
        # Calculate averages
        avg_confidence = np.mean(self.session_metrics['confidence_scores'])
        avg_tone = np.mean(self.session_metrics['tone_scores'])
        avg_pace = np.mean(self.session_metrics['pace_scores'])
        avg_volume = np.mean(self.session_metrics['volume_levels'])
        
        # Calculate consistency (lower std = more consistent)
        confidence_consistency = 100 - min(50, np.std(self.session_metrics['confidence_scores']) * 2)
        
        # Generate recommendations
        recommendations = []
        if avg_confidence < 70:
            recommendations.append("Practice speaking with more confidence and conviction")
        if avg_tone < 70:
            recommendations.append("Work on voice clarity and tone quality")
        if avg_pace < 70:
            recommendations.append("Practice maintaining an optimal speaking pace")
        if confidence_consistency < 70:
            recommendations.append("Work on maintaining consistent confidence throughout")
        
        return {
            'session_id': session_id,
            'average_confidence_score': avg_confidence,
            'average_tone_score': avg_tone,
            'average_pace_score': avg_pace,
            'average_volume_score': avg_volume,
            'confidence_consistency': confidence_consistency,
            'total_audio_chunks': len(self.session_metrics['confidence_scores']),
            'overall_audio_score': (avg_confidence + avg_tone + avg_pace) / 3,
            'recommendations': recommendations
        }
    
    def _get_default_audio_metrics(self) -> Dict[str, Any]:
        """Return default metrics when audio analysis fails"""
        return {
            'confidence_score': 50,
            'tone_score': 50,
            'pace_score': 50,
            'volume_score': 50,
            'overall_audio_score': 50,
            'feedback': 'Audio analysis unavailable',
            'features': {
                'pitch_mean': 0,
                'pitch_std': 0,
                'energy_mean': 0,
                'speaking_rate': 120
            }
        }