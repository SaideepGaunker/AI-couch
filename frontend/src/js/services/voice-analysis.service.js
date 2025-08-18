(function () {
  "use strict";

  angular
    .module("interviewPrepApp")
    .service("VoiceAnalysisService", VoiceAnalysisService);

  VoiceAnalysisService.$inject = ["$q", "$timeout"];

  function VoiceAnalysisService($q, $timeout) {
    var service = {
      startAnalysis: startAnalysis,
      stopAnalysis: stopAnalysis,
      getCurrentScore: getCurrentScore,
      getSessionSummary: getSessionSummary,
      resetSession: resetSession,
      isAnalyzing: isAnalyzing,
    };

    // Voice analysis state
    var audioContext = null;
    var analyser = null;
    var microphone = null;
    var dataArray = null;
    var analyzing = false;

    // Analysis results storage
    var analysisResults = [];
    var currentSessionScores = [];

    // Analysis parameters
    var sampleRate = 44100;
    var fftSize = 2048;
    var smoothingTimeConstant = 0.8;
    var recentWindowSizeSeconds = 5; // sliding window for UI score
    var recentScores = [];

    // Confidence metrics tracking
    var volumeHistory = [];
    var pitchHistory = [];
    var clarityHistory = [];
    var consistencyHistory = [];
    var maxHistoryLength = 100;

    return service;

    function startAnalysis() {
      var deferred = $q.defer();

      if (analyzing) {
        deferred.resolve({
          success: true,
          message: "Analysis already running",
        });
        return deferred.promise;
      }

      // Request microphone access
      navigator.mediaDevices
        .getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        })
        .then(function (stream) {
          try {
            // Create audio context
            audioContext = new (window.AudioContext ||
              window.webkitAudioContext)();
            analyser = audioContext.createAnalyser();
            microphone = audioContext.createMediaStreamSource(stream);

            // Configure analyser
            analyser.fftSize = fftSize;
            analyser.smoothingTimeConstant = smoothingTimeConstant;

            // Connect microphone to analyser
            microphone.connect(analyser);

            // Create data array for frequency data
            dataArray = new Uint8Array(analyser.frequencyBinCount);

            analyzing = true;
            analyzeAudio();

            console.log("✅ Voice analysis started");
            deferred.resolve({
              success: true,
              message: "Voice analysis started successfully",
            });
          } catch (error) {
            console.error("❌ Failed to initialize audio context:", error);
            deferred.reject({
              success: false,
              message: "Failed to initialize audio: " + error.message,
            });
          }
        })
        .catch(function (error) {
          console.error("❌ Failed to access microphone:", error);
          deferred.reject({
            success: false,
            message: "Failed to access microphone: " + error.message,
          });
        });

      return deferred.promise;
    }

    function stopAnalysis() {
      analyzing = false;

      if (microphone) {
        microphone.disconnect();
      }

      if (audioContext) {
        audioContext.close();
      }

      console.log("🛑 Voice analysis stopped");
      return getSessionSummary();
    }

    function analyzeAudio() {
      if (!analyzing) return;

      // Get frequency data
      analyser.getByteFrequencyData(dataArray);

      // Analyze voice characteristics
      var metrics = calculateVoiceMetrics(dataArray);

      // Store results
      storeAnalysisResult(metrics);

      // Maintain recent sliding window for responsive UI score
      var nowTs = metrics.timestamp;
      recentScores.push({ t: nowTs, s: metrics.confidenceScore });
      var cutoff = nowTs - recentWindowSizeSeconds * 1000;
      while (recentScores.length && recentScores[0].t < cutoff) {
        recentScores.shift();
      }

      // Continue analysis
      requestAnimationFrame(analyzeAudio);
    }

    function calculateVoiceMetrics(frequencyData) {
      var now = Date.now();

      // 1. Volume Analysis (Voice Strength)
      var volume = calculateVolume(frequencyData);

      // 2. Pitch Analysis (Voice Stability)
      var pitch = calculatePitch(frequencyData);

      // 3. Clarity Analysis (Spectral Clarity)
      var clarity = calculateClarity(frequencyData);

      // 4. Consistency Analysis (Voice Steadiness)
      var consistency = calculateConsistency(volume, pitch);

      // Calculate confidence score (0-100)
      var confidenceScore = calculateConfidenceScore(
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

    function calculateVolume(frequencyData) {
      var sum = 0;
      for (var i = 0; i < frequencyData.length; i++) {
        sum += frequencyData[i];
      }
      var average = sum / frequencyData.length;

      // Normalize to 0-100 scale
      var volumeScore = Math.min(100, (average / 255) * 100);

      // Treat near silence as zero to avoid mid-range bias when not speaking
      if (average < 2) {
        volumeScore = 0;
      }

      // Store in history
      volumeHistory.push(volumeScore);
      if (volumeHistory.length > maxHistoryLength) {
        volumeHistory.shift();
      }

      return volumeScore;
    }

    function calculatePitch(frequencyData) {
      // Find dominant frequency (simplified pitch detection)
      var maxIndex = 0;
      var maxValue = 0;

      // Focus on human voice range (80Hz - 1000Hz)
      var startBin = Math.floor((80 * fftSize) / sampleRate);
      var endBin = Math.floor((1000 * fftSize) / sampleRate);

      for (var i = startBin; i < endBin && i < frequencyData.length; i++) {
        if (frequencyData[i] > maxValue) {
          maxValue = frequencyData[i];
          maxIndex = i;
        }
      }

      // Convert bin to frequency
      var dominantFreq = (maxIndex * sampleRate) / fftSize;

      // If energy is extremely low, treat as no pitch (silence)
      if (maxValue < 2) {
        dominantFreq = 0;
      }

      // Store in history
      pitchHistory.push(dominantFreq);
      if (pitchHistory.length > maxHistoryLength) {
        pitchHistory.shift();
      }

      // Calculate pitch stability (lower variation = higher score)
      if (pitchHistory.length < 10) return dominantFreq === 0 ? 0 : 50;

      var pitchVariation = calculateVariation(pitchHistory);
      var stabilityScore = Math.max(0, 100 - pitchVariation);

      return Math.min(100, stabilityScore);
    }

    function calculateClarity(frequencyData) {
      // Calculate spectral centroid (brightness/clarity indicator)
      var weightedSum = 0;
      var magnitudeSum = 0;

      for (var i = 0; i < frequencyData.length; i++) {
        var frequency = (i * sampleRate) / fftSize;
        var magnitude = frequencyData[i];

        weightedSum += frequency * magnitude;
        magnitudeSum += magnitude;
      }

      var spectralCentroid = magnitudeSum > 0 ? weightedSum / magnitudeSum : 0;

      // If almost no energy, clarity should be 0
      if (magnitudeSum < 1) {
        return 0;
      }

      // Optimal range for voice clarity (1000-3000 Hz)
      var clarityScore;
      if (spectralCentroid >= 1000 && spectralCentroid <= 3000) {
        clarityScore = 100;
      } else if (spectralCentroid >= 500 && spectralCentroid <= 4000) {
        clarityScore = 80;
      } else {
        clarityScore = 60;
      }

      // Store in history
      clarityHistory.push(clarityScore);
      if (clarityHistory.length > maxHistoryLength) {
        clarityHistory.shift();
      }

      return clarityScore;
    }

    function calculateConsistency(currentVolume, currentPitch) {
      if (volumeHistory.length < 10) return currentVolume === 0 ? 0 : 50;

      // Calculate consistency based on volume and pitch stability
      var volumeConsistency =
        100 - calculateVariation(volumeHistory.slice(-20));
      var pitchConsistency = 100 - calculateVariation(pitchHistory.slice(-20));

      var consistencyScore = (volumeConsistency + pitchConsistency) / 2;

      // Store in history
      consistencyHistory.push(consistencyScore);
      if (consistencyHistory.length > maxHistoryLength) {
        consistencyHistory.shift();
      }

      return Math.max(0, Math.min(100, consistencyScore));
    }

    function calculateConfidenceScore(volume, pitch, clarity, consistency) {
      // Weighted combination of metrics
      var weights = {
        volume: 0.25, // Voice strength
        pitch: 0.3, // Pitch stability
        clarity: 0.25, // Voice clarity
        consistency: 0.2, // Overall consistency
      };

      var confidenceScore =
        volume * weights.volume +
        pitch * weights.pitch +
        clarity * weights.clarity +
        consistency * weights.consistency;

      // If all key components indicate silence, force 0
      var isSilentFrame = volume === 0 && pitch === 0 && clarity === 0;
      if (isSilentFrame) {
        return 0;
      }

      return Math.round(Math.max(0, Math.min(100, confidenceScore)));
    }

    function calculateVariation(data) {
      if (data.length < 2) return 0;

      var mean =
        data.reduce(function (sum, val) {
          return sum + val;
        }, 0) / data.length;
      var variance =
        data.reduce(function (sum, val) {
          return sum + Math.pow(val - mean, 2);
        }, 0) / data.length;
      var stdDev = Math.sqrt(variance);

      return mean > 0 ? (stdDev / mean) * 100 : 0;
    }

    function storeAnalysisResult(metrics) {
      analysisResults.push(metrics);
      currentSessionScores.push(metrics.confidenceScore);

      // Keep only recent results (last 5 minutes at 60fps = 18000 samples)
      var maxResults = 18000;
      if (analysisResults.length > maxResults) {
        analysisResults.shift();
        currentSessionScores.shift();
      }
    }

    function getCurrentScore() {
      // Use recent sliding window to make UI more responsive
      if (recentScores.length > 0) {
        var sumRecent = 0;
        for (var i = 0; i < recentScores.length; i++) {
          sumRecent += recentScores[i].s;
        }
        return Math.round(sumRecent / recentScores.length);
      }

      if (currentSessionScores.length === 0) return 0;

      var sum = currentSessionScores.reduce(function (acc, score) {
        return acc + score;
      }, 0);
      return Math.round(sum / currentSessionScores.length);
    }

    function getSessionSummary() {
      if (currentSessionScores.length === 0) {
        return {
          averageScore: 0,
          totalSamples: 0,
          duration: 0,
          suggestions: "No voice data recorded",
        };
      }

      var averageScore = getCurrentScore();
      var totalSamples = currentSessionScores.length;
      var duration =
        totalSamples > 0
          ? (analysisResults[analysisResults.length - 1].timestamp -
              analysisResults[0].timestamp) /
            1000
          : 0;

      // Generate suggestions based on average score
      var suggestions = "";
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

    function resetSession() {
      analysisResults = [];
      currentSessionScores = [];
      volumeHistory = [];
      pitchHistory = [];
      clarityHistory = [];
      consistencyHistory = [];
      recentScores = [];
    }

    function isAnalyzing() {
      return analyzing;
    }
  }
})();
