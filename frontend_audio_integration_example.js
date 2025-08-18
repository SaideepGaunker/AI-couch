/**
 * Frontend Audio Analysis Integration Example
 * This shows how to integrate the audio analysis API with your frontend
 */

class AudioAnalysisService {
  constructor(baseURL = "http://localhost:8000/api/v1") {
    this.baseURL = baseURL;
  }

  /**
   * Analyze audio file for tone and confidence
   * @param {File} audioFile - The audio file to analyze
   * @param {number} sessionId - Interview session ID
   * @param {number} questionId - Question ID
   * @param {string} token - Authentication token
   * @returns {Promise} Analysis results
   */
  async analyzeAudio(audioFile, sessionId = null, questionId = null, token) {
    const formData = new FormData();
    formData.append("audio_file", audioFile);

    if (sessionId) formData.append("session_id", sessionId);
    if (questionId) formData.append("question_id", questionId);

    try {
      const response = await fetch(`${this.baseURL}/audio/analyze`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      return result;
    } catch (error) {
      console.error("Audio analysis failed:", error);
      throw error;
    }
  }

  /**
   * Get supported audio formats
   * @returns {Promise} Supported formats and file size limits
   */
  async getSupportedFormats() {
    try {
      const response = await fetch(`${this.baseURL}/audio/supported-formats`);
      return await response.json();
    } catch (error) {
      console.error("Failed to get supported formats:", error);
      throw error;
    }
  }
}

// Example usage in your interview component
class InterviewComponent {
  constructor() {
    this.audioService = new AudioAnalysisService();
    this.mediaRecorder = null;
    this.audioChunks = [];
  }

  /**
   * Start recording audio
   */
  async startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaRecorder = new MediaRecorder(stream);
      this.audioChunks = [];

      this.mediaRecorder.ondataavailable = (event) => {
        this.audioChunks.push(event.data);
      };

      this.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(this.audioChunks, { type: "audio/wav" });
        this.analyzeRecordedAudio(audioBlob);
      };

      this.mediaRecorder.start();
      console.log("Recording started...");
    } catch (error) {
      console.error("Failed to start recording:", error);
    }
  }

  /**
   * Stop recording audio
   */
  stopRecording() {
    if (this.mediaRecorder && this.mediaRecorder.state === "recording") {
      this.mediaRecorder.stop();
      console.log("Recording stopped...");
    }
  }

  /**
   * Analyze recorded audio
   * @param {Blob} audioBlob - The recorded audio blob
   */
  async analyzeRecordedAudio(audioBlob) {
    try {
      // Convert blob to file
      const audioFile = new File([audioBlob], "recording.wav", {
        type: "audio/wav",
      });

      // Get session and question IDs from your app state
      const sessionId = this.getCurrentSessionId();
      const questionId = this.getCurrentQuestionId();
      const token = this.getAuthToken();

      // Analyze audio
      const result = await this.audioService.analyzeAudio(
        audioFile,
        sessionId,
        questionId,
        token
      );

      // Handle the results
      this.handleAnalysisResults(result);
    } catch (error) {
      console.error("Audio analysis failed:", error);
      this.showError("Failed to analyze audio. Please try again.");
    }
  }

  /**
   * Handle analysis results
   * @param {Object} result - Analysis results from API
   */
  handleAnalysisResults(result) {
    if (result.success) {
      // Update UI with tone confidence score
      this.updateToneConfidenceScore(result.tone_confidence_score);

      // Show improvement suggestions
      this.showImprovementSuggestions(result.improvement_suggestions);

      console.log("Audio analysis completed:", result);
    } else {
      this.showError("Audio analysis failed");
    }
  }

  /**
   * Update tone confidence score in UI
   * @param {number} score - Tone confidence score (0-100)
   */
  updateToneConfidenceScore(score) {
    const scoreElement = document.getElementById("tone-confidence-score");
    if (scoreElement) {
      scoreElement.textContent = `${score}/100`;

      // Add color coding based on score
      scoreElement.className =
        score >= 80
          ? "score-excellent"
          : score >= 60
          ? "score-good"
          : "score-needs-improvement";
    }
  }

  /**
   * Show improvement suggestions
   * @param {string} suggestions - Improvement suggestions text
   */
  showImprovementSuggestions(suggestions) {
    const suggestionsElement = document.getElementById(
      "improvement-suggestions"
    );
    if (suggestionsElement) {
      suggestionsElement.textContent = suggestions;
    }
  }

  /**
   * Show error message
   * @param {string} message - Error message
   */
  showError(message) {
    // Implement your error display logic
    console.error(message);
    alert(message); // Replace with your UI error display
  }

  // Helper methods (implement based on your app structure)
  getCurrentSessionId() {
    // Return current interview session ID
    return 1; // Replace with actual logic
  }

  getCurrentQuestionId() {
    // Return current question ID
    return 1; // Replace with actual logic
  }

  getAuthToken() {
    // Return authentication token
    return localStorage.getItem("auth_token"); // Replace with actual logic
  }
}

// Example HTML structure for your interview page
const exampleHTML = `
<div class="interview-audio-analysis">
    <div class="recording-controls">
        <button id="start-recording" onclick="interview.startRecording()">Start Recording</button>
        <button id="stop-recording" onclick="interview.stopRecording()">Stop Recording</button>
    </div>
    
    <div class="analysis-results">
        <div class="tone-confidence">
            <label>Tone Confidence Score:</label>
            <span id="tone-confidence-score">--/100</span>
        </div>
        
        <div class="improvement-suggestions">
            <label>Improvement Suggestions:</label>
            <p id="improvement-suggestions">Complete your answer to receive feedback.</p>
        </div>
    </div>
</div>

<style>
.score-excellent { color: #28a745; font-weight: bold; }
.score-good { color: #ffc107; font-weight: bold; }
.score-needs-improvement { color: #dc3545; font-weight: bold; }
</style>
`;

// Initialize the interview component
const interview = new InterviewComponent();

console.log("Audio analysis integration ready!");
console.log("Example HTML structure:", exampleHTML);
