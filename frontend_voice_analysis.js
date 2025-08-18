/**
 * Frontend Voice Tone and Confidence Analysis
 * Real-time analysis using Web Audio API
 */

class VoiceAnalyzer {
  constructor() {
    this.audioContext = null;
    this.analyser = null;
    this.microphone = null;
    this.dataArray = null;
    this.isAnalyzing = false;

    // Analysis results storage
    this.analysisResults = [];
    this.currentSessionScores = [];

    // Analysis parameters
    this.sampleRate = 44100;
    this.fftSize = 2048;
    this.smoothingTimeConstant = 0.8;

    // Confidence metrics tracking
    this.volumeHistory = [];
    this.pitchHistory = [];
    this.clarityHistory = [];
    this.consistencyHistory = [];

    this.maxHistoryLength = 100; // Keep last 100 measurements
  }

  /**
   * Initialize audio context and start analysis
   */
  async startAnalysis() {
    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      // Create audio context
      this.audioContext = new (window.AudioContext ||
        window.webkitAudioContext)();
      this.analyser = this.audioContext.createAnalyser();
      this.microphone = this.audioContext.createMediaStreamSource(stream);

      // Configure analyser
      this.analyser.fftSize = this.fftSize;
      this.analyser.smoothingTimeConstant = this.smoothingTimeConstant;

      // Connect microphone to analyser
      this.microphone.connect(this.analyser);

      // Create data array for frequency data
      this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);

      this.isAnalyzing = true;
      this.analyzeAudio();

      console.log("✅ Voice analysis started");
      return { success: true, message: "Voice analysis started successfully" };
    } catch (error) {
      console.error("❌ Failed to start voice analysis:", error);
      return {
        success: false,
        message: "Failed to access microphone: " + error.message,
      };
    }
  }

  /**
   * Stop voice analysis
   */
  stopAnalysis() {
    this.isAnalyzing = false;

    if (this.microphone) {
      this.microphone.disconnect();
    }

    if (this.audioContext) {
      this.audioContext.close();
    }

    console.log("🛑 Voice analysis stopped");
  }

  /**
   * Main analysis loop
   */
  analyzeAudio() {
    if (!this.isAnalyzing) return;

    // Get frequency data
    this.analyser.getByteFrequencyData(this.dataArray);

    // Analyze voice characteristics
    const metrics = this.calculateVoiceMetrics(this.dataArray);

    // Store results
    this.storeAnalysisResult(metrics);

    // Continue analysis
    requestAnimationFrame(() => this.analyzeAudio());
  }

  /**
   * Calculate voice metrics from frequency data
   */
  calculateVoiceMetrics(frequencyData) {
    const now = Date.now();

    // 1. Volume Analysis (Voice Strength)
    const volume = this.calculateVolume(frequencyData);

    // 2. Pitch Analysis (Voice Stability)
    const pitch = this.calculatePitch(frequencyData);

    // 3. Clarity Analysis (Spectral Clarity)
    const clarity = this.calculateClarity(frequencyData);

    // 4. Consistency Analysis (Voice Steadiness)
    const consistency = this.calculateConsistency(volume, pitch);

    // Calculate confidence score (0-100)
    const confidenceScore = this.calculateConfidenceScore(
      volume,
      pitch,
      clarity,
      consistency
    );

    return {
      timestamp: now,
      volume: volume,
      pitch: pitch,
      clarity: clarity,
      consistency: consistency,
      confidenceScore: confidenceScore,
    };
  }

  /**
   * Calculate volume/energy from frequency data
   */
  calculateVolume(frequencyData) {
    let sum = 0;
    for (let i = 0; i < frequencyData.length; i++) {
      sum += frequencyData[i];
    }
    const average = sum / frequencyData.length;

    // Normalize to 0-100 scale
    const volumeScore = Math.min(100, (average / 255) * 100);

    // Store in history
    this.volumeHistory.push(volumeScore);
    if (this.volumeHistory.length > this.maxHistoryLength) {
      this.volumeHistory.shift();
    }

    return volumeScore;
  }

  /**
   * Calculate pitch stability from frequency data
   */
  calculatePitch(frequencyData) {
    // Find dominant frequency (simplified pitch detection)
    let maxIndex = 0;
    let maxValue = 0;

    // Focus on human voice range (80Hz - 1000Hz)
    const startBin = Math.floor((80 * this.fftSize) / this.sampleRate);
    const endBin = Math.floor((1000 * this.fftSize) / this.sampleRate);

    for (let i = startBin; i < endBin && i < frequencyData.length; i++) {
      if (frequencyData[i] > maxValue) {
        maxValue = frequencyData[i];
        maxIndex = i;
      }
    }

    // Convert bin to frequency
    const dominantFreq = (maxIndex * this.sampleRate) / this.fftSize;

    // Store in history
    this.pitchHistory.push(dominantFreq);
    if (this.pitchHistory.length > this.maxHistoryLength) {
      this.pitchHistory.shift();
    }

    // Calculate pitch stability (lower variation = higher score)
    if (this.pitchHistory.length < 10) return 50;

    const pitchVariation = this.calculateVariation(this.pitchHistory);
    const stabilityScore = Math.max(0, 100 - pitchVariation);

    return Math.min(100, stabilityScore);
  }

  /**
   * Calculate voice clarity from spectral data
   */
  calculateClarity(frequencyData) {
    // Calculate spectral centroid (brightness/clarity indicator)
    let weightedSum = 0;
    let magnitudeSum = 0;

    for (let i = 0; i < frequencyData.length; i++) {
      const frequency = (i * this.sampleRate) / this.fftSize;
      const magnitude = frequencyData[i];

      weightedSum += frequency * magnitude;
      magnitudeSum += magnitude;
    }

    const spectralCentroid = magnitudeSum > 0 ? weightedSum / magnitudeSum : 0;

    // Optimal range for voice clarity (1000-3000 Hz)
    let clarityScore;
    if (spectralCentroid >= 1000 && spectralCentroid <= 3000) {
      clarityScore = 100;
    } else if (spectralCentroid >= 500 && spectralCentroid <= 4000) {
      clarityScore = 80;
    } else {
      clarityScore = 60;
    }

    // Store in history
    this.clarityHistory.push(clarityScore);
    if (this.clarityHistory.length > this.maxHistoryLength) {
      this.clarityHistory.shift();
    }

    return clarityScore;
  }

  /**
   * Calculate voice consistency
   */
  calculateConsistency(currentVolume, currentPitch) {
    if (this.volumeHistory.length < 10) return 50;

    // Calculate consistency based on volume and pitch stability
    const volumeConsistency =
      100 - this.calculateVariation(this.volumeHistory.slice(-20));
    const pitchConsistency =
      100 - this.calculateVariation(this.pitchHistory.slice(-20));

    const consistencyScore = (volumeConsistency + pitchConsistency) / 2;

    // Store in history
    this.consistencyHistory.push(consistencyScore);
    if (this.consistencyHistory.length > this.maxHistoryLength) {
      this.consistencyHistory.shift();
    }

    return Math.max(0, Math.min(100, consistencyScore));
  }

  /**
   * Calculate overall confidence score
   */
  calculateConfidenceScore(volume, pitch, clarity, consistency) {
    // Weighted combination of metrics
    const weights = {
      volume: 0.25, // Voice strength
      pitch: 0.3, // Pitch stability
      clarity: 0.25, // Voice clarity
      consistency: 0.2, // Overall consistency
    };

    const confidenceScore =
      volume * weights.volume +
      pitch * weights.pitch +
      clarity * weights.clarity +
      consistency * weights.consistency;

    return Math.round(Math.max(0, Math.min(100, confidenceScore)));
  }

  /**
   * Calculate variation (coefficient of variation)
   */
  calculateVariation(data) {
    if (data.length < 2) return 0;

    const mean = data.reduce((sum, val) => sum + val, 0) / data.length;
    const variance =
      data.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / data.length;
    const stdDev = Math.sqrt(variance);

    return mean > 0 ? (stdDev / mean) * 100 : 0;
  }

  /**
   * Store analysis result
   */
  storeAnalysisResult(metrics) {
    this.analysisResults.push(metrics);
    this.currentSessionScores.push(metrics.confidenceScore);

    // Keep only recent results (last 5 minutes at 60fps = 18000 samples)
    const maxResults = 18000;
    if (this.analysisResults.length > maxResults) {
      this.analysisResults.shift();
      this.currentSessionScores.shift();
    }

    // Trigger real-time UI update
    this.onAnalysisUpdate(metrics);
  }

  /**
   * Get current average confidence score
   */
  getCurrentAverageScore() {
    if (this.currentSessionScores.length === 0) return 0;

    const sum = this.currentSessionScores.reduce(
      (acc, score) => acc + score,
      0
    );
    return Math.round(sum / this.currentSessionScores.length);
  }

  /**
   * Get session summary
   */
  getSessionSummary() {
    if (this.currentSessionScores.length === 0) {
      return {
        averageScore: 0,
        totalSamples: 0,
        duration: 0,
        suggestions: "No voice data recorded",
      };
    }

    const averageScore = this.getCurrentAverageScore();
    const totalSamples = this.currentSessionScores.length;
    const duration =
      totalSamples > 0
        ? (this.analysisResults[this.analysisResults.length - 1].timestamp -
            this.analysisResults[0].timestamp) /
          1000
        : 0;

    // Generate suggestions based on average score
    let suggestions = "";
    if (averageScore >= 80) {
      suggestions =
        "Excellent voice confidence! Your tone is clear and steady.";
    } else if (averageScore >= 60) {
      suggestions =
        "Good voice confidence. Try to maintain consistent volume and pace.";
    } else if (averageScore >= 40) {
      suggestions =
        "Voice confidence needs improvement. Focus on speaking clearly and steadily.";
    } else {
      suggestions =
        "Work on voice confidence. Practice speaking with more conviction and clarity.";
    }

    return {
      averageScore: averageScore,
      totalSamples: totalSamples,
      duration: Math.round(duration),
      suggestions: suggestions,
    };
  }

  /**
   * Reset session data
   */
  resetSession() {
    this.analysisResults = [];
    this.currentSessionScores = [];
    this.volumeHistory = [];
    this.pitchHistory = [];
    this.clarityHistory = [];
    this.consistencyHistory = [];
  }

  /**
   * Callback for real-time updates (override in implementation)
   */
  onAnalysisUpdate(metrics) {
    // Override this method to handle real-time UI updates
    console.log("Voice Analysis Update:", {
      confidence: metrics.confidenceScore,
      volume: Math.round(metrics.volume),
      pitch: Math.round(metrics.pitch),
      clarity: Math.round(metrics.clarity),
      consistency: Math.round(metrics.consistency),
    });
  }
}

/**
 * Interview Voice Analysis Integration
 */
class InterviewVoiceAnalysis {
  constructor(apiBaseUrl = "http://localhost:8000/api/v1") {
    this.voiceAnalyzer = new VoiceAnalyzer();
    this.apiBaseUrl = apiBaseUrl;
    this.currentSessionId = null;
    this.currentQuestionId = null;
    this.isRecording = false;

    // Bind the real-time update callback
    this.voiceAnalyzer.onAnalysisUpdate = this.handleRealTimeUpdate.bind(this);
  }

  /**
   * Start voice analysis for interview session
   */
  async startInterviewAnalysis(sessionId, questionId) {
    this.currentSessionId = sessionId;
    this.currentQuestionId = questionId;

    // Reset previous session data
    this.voiceAnalyzer.resetSession();

    // Start analysis
    const result = await this.voiceAnalyzer.startAnalysis();

    if (result.success) {
      this.isRecording = true;
      this.updateUI("recording", "Voice analysis started...");
    }

    return result;
  }

  /**
   * Stop voice analysis and send results to backend
   */
  async stopInterviewAnalysis(authToken) {
    if (!this.isRecording)
      return { success: false, message: "No active recording" };

    // Stop analysis
    this.voiceAnalyzer.stopAnalysis();
    this.isRecording = false;

    // Get session summary
    const summary = this.voiceAnalyzer.getSessionSummary();

    // Send results to backend
    if (
      this.currentSessionId &&
      this.currentQuestionId &&
      summary.averageScore > 0
    ) {
      try {
        const response = await fetch(
          `${this.apiBaseUrl}/interviews/voice-confidence`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${authToken}`,
            },
            body: JSON.stringify({
              session_id: this.currentSessionId,
              question_id: this.currentQuestionId,
              tone_confidence_score: summary.averageScore,
              analysis_duration: summary.duration,
              total_samples: summary.totalSamples,
              improvement_suggestions: summary.suggestions,
            }),
          }
        );

        if (response.ok) {
          const result = await response.json();
          console.log("✅ Voice analysis results saved:", result);

          this.updateUI(
            "completed",
            `Analysis complete! Score: ${summary.averageScore}/100`
          );

          return {
            success: true,
            message: "Voice analysis completed and saved",
            summary: summary,
          };
        } else {
          console.error("❌ Failed to save voice analysis results");
          return {
            success: false,
            message: "Failed to save results to server",
            summary: summary,
          };
        }
      } catch (error) {
        console.error("❌ Error saving voice analysis:", error);
        return {
          success: false,
          message: "Network error while saving results",
          summary: summary,
        };
      }
    }

    return {
      success: true,
      message: "Voice analysis completed",
      summary: summary,
    };
  }

  /**
   * Handle real-time analysis updates
   */
  handleRealTimeUpdate(metrics) {
    // Update UI with current confidence score
    this.updateUI("analyzing", `Confidence: ${metrics.confidenceScore}/100`);

    // You can also update individual metrics
    this.updateMetricsDisplay({
      confidence: metrics.confidenceScore,
      volume: Math.round(metrics.volume),
      pitch: Math.round(metrics.pitch),
      clarity: Math.round(metrics.clarity),
      consistency: Math.round(metrics.consistency),
    });
  }

  /**
   * Update UI elements (customize based on your UI)
   */
  updateUI(status, message) {
    // Update status indicator
    const statusElement = document.getElementById("voice-analysis-status");
    if (statusElement) {
      statusElement.textContent = message;
      statusElement.className = `voice-status ${status}`;
    }

    // Update confidence score display
    if (status === "analyzing") {
      const scoreElement = document.getElementById("current-confidence-score");
      if (scoreElement) {
        const score = message.match(/\d+/)?.[0] || "0";
        scoreElement.textContent = `${score}/100`;

        // Add color coding
        const scoreNum = parseInt(score);
        scoreElement.className =
          scoreNum >= 80
            ? "score-excellent"
            : scoreNum >= 60
            ? "score-good"
            : "score-needs-improvement";
      }
    }
  }

  /**
   * Update detailed metrics display
   */
  updateMetricsDisplay(metrics) {
    const elements = {
      "voice-volume": metrics.volume,
      "voice-pitch": metrics.pitch,
      "voice-clarity": metrics.clarity,
      "voice-consistency": metrics.consistency,
    };

    Object.entries(elements).forEach(([id, value]) => {
      const element = document.getElementById(id);
      if (element) {
        element.textContent = `${value}/100`;
      }
    });
  }

  /**
   * Get current session statistics
   */
  getCurrentStats() {
    return this.voiceAnalyzer.getSessionSummary();
  }
}

// Export for use in your application
window.InterviewVoiceAnalysis = InterviewVoiceAnalysis;
window.VoiceAnalyzer = VoiceAnalyzer;

console.log("🎤 Voice Analysis Module Loaded");
