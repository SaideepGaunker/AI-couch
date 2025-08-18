# Frontend Voice Analysis Integration Guide

## 🎯 Overview

This implementation provides **real-time voice tone and confidence analysis** on the frontend using the Web Audio API, then sends only the **average results** to the backend for storage in the `performance_metrics` table.

## 🏗️ Architecture

```
Frontend (JavaScript)          Backend (FastAPI)
┌─────────────────────┐       ┌──────────────────────┐
│ Web Audio API       │       │                      │
│ ↓                   │       │                      │
│ Real-time Analysis  │       │                      │
│ ↓                   │       │                      │
│ Calculate Metrics   │  →    │ Store Average Score  │
│ ↓                   │       │ ↓                    │
│ Average Score       │       │ performance_metrics  │
│ ↓                   │       │ .tone_confidence_    │
│ Send to Backend     │       │  score               │
└─────────────────────┘       └──────────────────────┘
```

## 📁 Files Created

### Frontend Files:

- `frontend_voice_analysis.js` - Main voice analysis engine
- `interview_page_integration.html` - Example integration

### Backend Files:

- `backend/app/api/v1/endpoints/voice_analysis.py` - API endpoint
- Updated `backend/app/api/v1/api.py` - Added router

## 🚀 Quick Integration

### 1. Include the JavaScript Module

```html
<script src="frontend_voice_analysis.js"></script>
```

### 2. Initialize Voice Analysis

```javascript
// Initialize voice analysis
const voiceAnalysis = new InterviewVoiceAnalysis(
  "http://localhost:8000/api/v1"
);

// Start analysis for a question
await voiceAnalysis.startInterviewAnalysis(sessionId, questionId);

// Stop analysis and send results to backend
await voiceAnalysis.stopInterviewAnalysis(authToken);
```

### 3. Backend API Endpoints

- `POST /api/v1/interviews/voice-confidence` - Submit voice analysis results
- `GET /api/v1/interviews/voice-confidence/{session_id}` - Get session voice analysis

## 🎤 How It Works

### Frontend Analysis Process:

1. **Microphone Access**: Requests user permission for microphone
2. **Real-time Processing**: Uses Web Audio API to analyze audio in real-time
3. **Metric Calculation**:
   - **Volume**: Voice strength and energy
   - **Pitch Stability**: Consistency of fundamental frequency
   - **Clarity**: Spectral centroid analysis
   - **Consistency**: Overall voice steadiness
4. **Confidence Score**: Weighted combination of all metrics (0-100)
5. **Average Calculation**: Calculates session average when stopped
6. **Backend Submission**: Sends only the final average score

### Backend Storage:

- Stores in existing `performance_metrics` table
- Uses `tone_confidence_score` column
- Associates with `session_id` and `question_id`
- Includes improvement suggestions

## 📊 Real-time UI Updates

The system provides real-time feedback:

```javascript
// Override the update callback for custom UI
voiceAnalysis.voiceAnalyzer.onAnalysisUpdate = function (metrics) {
  // Update your UI with current metrics
  updateConfidenceDisplay(metrics.confidenceScore);
  updateVolumeIndicator(metrics.volume);
  updatePitchStability(metrics.pitch);
};
```

## 🎯 Integration with Your Interview Flow

### Basic Integration:

```javascript
class InterviewManager {
  constructor() {
    this.voiceAnalysis = new InterviewVoiceAnalysis();
    this.currentSession = null;
    this.currentQuestion = null;
  }

  async startQuestion(sessionId, questionId) {
    this.currentSession = sessionId;
    this.currentQuestion = questionId;

    // Start voice analysis
    await this.voiceAnalysis.startInterviewAnalysis(sessionId, questionId);
  }

  async endQuestion() {
    // Stop analysis and save results
    const result = await this.voiceAnalysis.stopInterviewAnalysis(
      this.authToken
    );

    if (result.success) {
      console.log("Voice analysis saved:", result.summary);
    }
  }

  async nextQuestion(newQuestionId) {
    // End current question analysis
    await this.endQuestion();

    // Start new question analysis
    await this.startQuestion(this.currentSession, newQuestionId);
  }
}
```

### Advanced Integration with React/Vue:

```javascript
// React Hook Example
function useVoiceAnalysis() {
  const [voiceAnalysis] = useState(new InterviewVoiceAnalysis());
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [currentScore, setCurrentScore] = useState(0);

  useEffect(() => {
    voiceAnalysis.voiceAnalyzer.onAnalysisUpdate = (metrics) => {
      setCurrentScore(metrics.confidenceScore);
    };
  }, []);

  const startAnalysis = async (sessionId, questionId) => {
    const result = await voiceAnalysis.startInterviewAnalysis(
      sessionId,
      questionId
    );
    setIsAnalyzing(result.success);
  };

  const stopAnalysis = async (authToken) => {
    const result = await voiceAnalysis.stopInterviewAnalysis(authToken);
    setIsAnalyzing(false);
    return result;
  };

  return { startAnalysis, stopAnalysis, isAnalyzing, currentScore };
}
```

## 🔧 Customization Options

### Adjust Analysis Sensitivity:

```javascript
const voiceAnalyzer = new VoiceAnalyzer();

// Customize analysis parameters
voiceAnalyzer.fftSize = 4096; // Higher = more detailed analysis
voiceAnalyzer.smoothingTimeConstant = 0.9; // Higher = smoother
voiceAnalyzer.maxHistoryLength = 200; // More history for stability
```

### Custom Scoring Weights:

```javascript
// Modify the calculateConfidenceScore method
calculateConfidenceScore(volume, pitch, clarity, consistency) {
    const weights = {
        volume: 0.20,      // Reduce volume importance
        pitch: 0.40,       // Increase pitch stability importance
        clarity: 0.30,     // Increase clarity importance
        consistency: 0.10  // Reduce consistency importance
    };

    return Math.round(
        (volume * weights.volume) +
        (pitch * weights.pitch) +
        (clarity * weights.clarity) +
        (consistency * weights.consistency)
    );
}
```

## 🧪 Testing

### Test the Backend Endpoint:

```bash
curl -X POST "http://localhost:8000/api/v1/interviews/voice-confidence" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 1,
    "question_id": 1,
    "tone_confidence_score": 85.5,
    "analysis_duration": 30,
    "total_samples": 1800,
    "improvement_suggestions": "Excellent voice confidence! Keep up the great work."
  }'
```

### Test Frontend Analysis:

1. Open `interview_page_integration.html` in browser
2. Click "Start Analysis" and speak
3. Watch real-time metrics update
4. Click "Stop Analysis" to see results

## 📈 Performance Considerations

- **CPU Usage**: Minimal - uses efficient Web Audio API
- **Memory**: Keeps only recent analysis history (configurable)
- **Network**: Only sends final average, not real-time data
- **Battery**: Optimized for mobile devices

## 🔒 Privacy & Security

- **No Audio Storage**: Audio is processed in real-time, never stored
- **Local Processing**: All analysis happens on user's device
- **Minimal Data**: Only confidence scores sent to server
- **User Consent**: Requires explicit microphone permission

## 🎉 Benefits

✅ **Real-time Feedback**: Users see confidence scores as they speak
✅ **Reduced Server Load**: Processing happens on frontend
✅ **Privacy Friendly**: No audio data leaves the device
✅ **Responsive UI**: Immediate visual feedback
✅ **Scalable**: No server-side audio processing needed
✅ **Cross-platform**: Works on all modern browsers

## 🚀 Next Steps

1. **Integrate** the JavaScript module into your interview page
2. **Customize** the UI to match your design
3. **Test** with real users and adjust sensitivity
4. **Monitor** the backend endpoint for successful data storage
5. **Enhance** with additional metrics if needed

Your voice analysis feature is now ready to provide real-time feedback while efficiently storing results in your database!
