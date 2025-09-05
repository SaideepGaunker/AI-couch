/**
 * Interview Chat Controller - Handles chatbot-style interview with audio
 */
(function () {
  "use strict";

  angular
    .module("interviewPrepApp")
    .controller("InterviewChatController", InterviewChatController);

  InterviewChatController.$inject = [
    "$location",
    "$routeParams",
    "$timeout",
    "$interval",
    "$scope",
    "AuthService",
    "InterviewService",
    "PostureService",
    "VoiceAnalysisService",
    "ApiService",
    "SessionDataService",
    "DifficultyDisplayService",
    "UnifiedDifficultyStateService",
  ];

  function InterviewChatController(
    $location,
    $routeParams,
    $timeout,
    $interval,
    $scope,
    AuthService,
    InterviewService,
    PostureService,
    VoiceAnalysisService,
    ApiService,
    SessionDataService,
    DifficultyDisplayService,
    UnifiedDifficultyStateService
  ) {
    var vm = this;

    // Properties
    vm.sessionId = $routeParams.sessionId;
    vm.session = null;
    vm.questions = [];
    vm.currentQuestionIndex = 0;
    vm.currentQuestion = null;
    vm.chatMessages = [];
    vm.loading = false;
    vm.error = "";

    // Audio properties
    vm.isListening = false;
    vm.isRecording = false;
    vm.isSpeaking = false;
    vm.mediaRecorder = null;
    vm.mediaStream = null;
    vm.audioChunks = [];
    vm.recognition = null;
    vm.synthesis = null;

    // Camera properties
    vm.cameraActive = false;
    vm.cameraError = "";

    // Voice analysis properties
    vm.voiceAnalysisEnabled = true;
    vm.voiceAnalysisActive = false;
    vm.currentVoiceScore = 0;
    vm.voiceAnalysisError = "";
    vm.voiceAnalysisResults = null;

    // Posture detection properties
    vm.postureEnabled = false;
    vm.postureFeedback = null;
    vm.showPostureFeedback = false;
    vm.postureAnalysisActive = false;

    // Posture data collection for feedback
    vm.postureScores = [];
    vm.averagePostureScore = 0;

    // Timer properties
    vm.sessionTimeRemaining = 0;
    vm.questionTimeRemaining = 0;
    vm.sessionTimer = null;
    vm.questionTimer = null;

    // Current answer
    vm.currentAnswer = "";
    vm.transcribedText = "";

    // Difficulty state management
    vm.currentDifficultyState = null;
    vm.difficultyDisplay = null;
    vm.difficultyChangeSubscription = null;

    // Methods
    vm.startListening = startListening;
    vm.stopListening = stopListening;
    vm.submitAnswer = submitAnswer;
    vm.skipQuestion = skipQuestion;
    vm.endSession = endSession;
    vm.speakQuestion = speakQuestion;
    vm.startCamera = startCamera;
    vm.stopCamera = stopCamera;
    vm.formatTime = formatTime;
    vm.recoverSession = recoverSession;
    vm.validateSession = validateSession;
    vm.togglePostureDetection = togglePostureDetection;
    vm.startPostureAnalysis = startPostureAnalysis;
    vm.stopPostureAnalysis = stopPostureAnalysis;
    vm.getPostureStatusText = getPostureStatusText;
    
    // Difficulty state management methods
    vm.initializeDifficultyState = initializeDifficultyState;
    vm.updateDifficultyDisplay = updateDifficultyDisplay;
    vm.onDifficultyChange = onDifficultyChange;
    vm.getConsistentDifficultyLabel = getConsistentDifficultyLabel;

    // Debug method for testing
    vm.testFunction = function () {
      console.log("Test function called - controller is working!");
      vm.error = "Test function called - controller is working!";
      $scope.$apply();
    };

    // Make controller available globally for debugging
    window.debugController = vm;

    // Initialize
    activate();

    function activate() {
      console.log("=== INTERVIEW CHAT CONTROLLER ACTIVATION ===");
      console.log("Interview Chat activated with session ID:", vm.sessionId);
      console.log("Controller instance:", vm);
      console.log("Available methods:", Object.keys(vm));

      if (!vm.sessionId) {
        console.error("No session ID provided");
        vm.error = "No session ID provided";
        return;
      }

      // Test if basic functions are working
      try {
        console.log("Testing basic controller functionality...");
        console.log("formatTime function:", typeof vm.formatTime);
        console.log("submitAnswer function:", typeof vm.submitAnswer);
        console.log("endSession function:", typeof vm.endSession);
        console.log("All functions appear to be defined correctly");
      } catch (e) {
        console.error("Error testing controller functions:", e);
      }

      // Check for session data from SessionDataService first
      console.log('Interview Chat Controller - Checking for stored session data...');
      
      if (SessionDataService.hasValidSessionData()) {
        var storedSessionData = SessionDataService.getSessionData();
        console.log('Interview Chat Controller - Found valid stored session data!');
        console.log('- Session object:', storedSessionData.session);
        console.log('- Session ID:', storedSessionData.session ? storedSessionData.session.id : 'No session');
        console.log('- Questions array:', storedSessionData.questions);
        console.log('- Questions count:', storedSessionData.questions ? storedSessionData.questions.length : 0);

        // Validate that the session ID matches the route parameter
        if (storedSessionData.session.id.toString() === vm.sessionId) {
          vm.session = storedSessionData.session;
          vm.questions = storedSessionData.questions || [];

          console.log('- vm.session set to:', vm.session);
          console.log('- vm.questions set to:', vm.questions);
          console.log('About to call initializeInterview()...');

          // Clear the stored data since we've used it
          SessionDataService.clearSessionData();

          // Set initial session state
          SessionDataService.setSessionState(vm.sessionId, {
            status: 'initializing',
            currentQuestionIndex: 0,
            startTime: Date.now()
          });

          initializeInterview();
        } else {
          console.warn('Stored session ID does not match route parameter, clearing and loading from API');
          SessionDataService.clearSessionData();
          loadSessionData();
        }
      } else {
        // Fallback to URL params or API call
        console.log('Interview Chat Controller - No stored session data, checking URL params...');
        console.log('Interview Chat Controller - Route params:', $routeParams);
        console.log('Interview Chat Controller - Search params:', $location.search());

        var sessionData = $routeParams.sessionData || $location.search().sessionData;
        console.log('Interview Chat Controller - Session data found in URL:', !!sessionData);

        if (sessionData) {
          try {
            console.log('Interview Chat Controller - Parsing URL session data...');
            var data = JSON.parse(sessionData);
            vm.session = data.session;
            vm.questions = data.questions || [];
            console.log('About to call initializeInterview()...');
            initializeInterview();
          } catch (e) {
            console.error("Error parsing session data:", e);
            console.log('Interview Chat Controller - Falling back to loadSessionData');
            loadSessionData();
          }
        } else {
          console.log('Interview Chat Controller - No session data found, loading from API');
          loadSessionData();
        }
      }

      // Initialize audio services and camera
      initializeAudioServices();

      // Initialize posture detection service
      initializePostureDetection();

      // Start camera
      $timeout(function () {
        startCamera();
      }, 1000);

      // Cleanup on scope destroy
      $scope.$on('$destroy', function() {
        if (vm.difficultyChangeSubscription) {
          vm.difficultyChangeSubscription();
          vm.difficultyChangeSubscription = null;
        }
      });
    }

    function loadSessionData() {
      console.log("=== LOADING SESSION DATA FROM API ===");
      vm.loading = true;
      InterviewService.getSession(vm.sessionId)
        .then(function (response) {
          console.log("=== API RESPONSE RECEIVED ===");
          console.log("Full response:", response);
          console.log("Response keys:", Object.keys(response));
          console.log("Session object:", response.session);
          console.log("Questions array:", response.questions);
          console.log("Questions type:", typeof response.questions);
          console.log("Questions length:", response.questions ? response.questions.length : 'undefined');

          vm.session = response.session;
          vm.questions = response.questions || [];

          console.log("=== AFTER ASSIGNMENT ===");
          console.log("vm.session:", vm.session);
          console.log("vm.questions:", vm.questions);
          console.log("vm.questions length:", vm.questions.length);

          initializeInterview();
        })
        .catch(function (error) {
          console.error("=== API ERROR ===");
          console.error("Error loading session:", error);
          console.error("Error status:", error.status);
          console.error("Error data:", error.data);
          vm.error = "Failed to load interview session";
        })
        .finally(function () {
          vm.loading = false;
        });
    }

    function initializeInterview() {
      console.log("=== INITIALIZING INTERVIEW ===");
      console.log("Questions array:", vm.questions);
      console.log("Questions length:", vm.questions ? vm.questions.length : 'undefined');
      console.log("Questions type:", typeof vm.questions);
      console.log("Session object:", vm.session);

      // Validate session before proceeding
      if (!validateSession()) {
        vm.error = "Invalid session data. Please try starting a new session.";
        return;
      }

      console.log("Session validation passed, proceeding with initialization...");

      // Try to recover session state if available
      var recovered = recoverSession();
      
      if (!recovered) {
        // Start from the beginning
        vm.currentQuestion = vm.questions[0];
        vm.currentQuestionIndex = 0;
      }

      console.log("=== SETTING UP CURRENT QUESTION ===");
      console.log("Current question index:", vm.currentQuestionIndex);
      console.log("Current question:", vm.currentQuestion);
      console.log("Question content field:", vm.currentQuestion.content);
      console.log("Question text field:", vm.currentQuestion.question_text);
      console.log("Question keys:", Object.keys(vm.currentQuestion));

      // Initialize timers
      vm.sessionTimeRemaining = (vm.session.duration || 30) * 60;
      vm.questionTimeRemaining =
        (vm.currentQuestion.expected_duration || 3) * 60;

      console.log("=== ADDING WELCOME MESSAGE ===");
      // Add welcome message (only if starting from beginning)
      if (vm.currentQuestionIndex === 0) {
        var difficultyLevel = vm.session.difficulty_level || 'medium';
        var difficultyLabel = DifficultyDisplayService.getDifficultyLabel(
          DifficultyDisplayService.normalizeDifficultyInput(difficultyLevel)
        );
        var difficultyMessage = getDifficultyWelcomeMessage(difficultyLabel);
        
        addChatMessage(
          "ai",
          "Welcome to your interview! I'll be asking you questions and you can respond using voice or text. " + difficultyMessage + " Let's begin!"
        );
      } else {
        addChatMessage(
          "ai",
          "Welcome back! Continuing from where you left off..."
        );
      }
      console.log("Welcome message added, chat messages count:", vm.chatMessages.length);

      // Update session state
      SessionDataService.setSessionState(vm.sessionId, {
        status: 'active',
        currentQuestionIndex: vm.currentQuestionIndex,
        startTime: Date.now()
      });

      // Initialize difficulty state management
      initializeDifficultyState();

      // Start with current question
      console.log("=== STARTING CURRENT QUESTION IN 1 SECOND ===");
      $timeout(function () {
        console.log("Timeout executed, calling askCurrentQuestion()");
        askCurrentQuestion();
        startTimers();
      }, 1000);
    }

    function initializeAudioServices() {
      // Initialize Speech Recognition
      if (
        "webkitSpeechRecognition" in window ||
        "SpeechRecognition" in window
      ) {
        var SpeechRecognition =
          window.SpeechRecognition || window.webkitSpeechRecognition;
        vm.recognition = new SpeechRecognition();
        vm.recognition.continuous = true;
        vm.recognition.interimResults = true;
        vm.recognition.lang = "en-US";

        vm.recognition.onstart = function () {
          console.log("Speech recognition started");
          vm.isListening = true;
          $scope.$apply();
        };

        vm.recognition.onresult = function (event) {
          var transcript = "";
          for (var i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
              transcript += event.results[i][0].transcript;
            }
          }
          if (transcript) {
            vm.transcribedText = transcript;
            vm.currentAnswer = transcript;
            $scope.$apply();
          }
        };

        vm.recognition.onerror = function (event) {
          console.error("Speech recognition error:", event.error);
          vm.isListening = false;
          $scope.$apply();
        };

        vm.recognition.onend = function () {
          console.log("Speech recognition ended");
          vm.isListening = false;
          // Ensure voice analysis is not running when speak is inactive
          try {
            if (vm.voiceAnalysisActive) {
              stopVoiceAnalysis();
            }
          } catch (e) {
            console.warn("Error stopping voice analysis on recognition end:", e);
          }
          $scope.$apply();
        };
      }

      // Initialize Speech Synthesis
      if ("speechSynthesis" in window) {
        vm.synthesis = window.speechSynthesis;
      }

      // Initialize Media Recorder for audio analysis
      initializeMediaRecorder();
    }

    function initializeMediaRecorder() {
      navigator.mediaDevices
        .getUserMedia({ audio: true })
        .then(function (stream) {
          vm.mediaStream = stream;
          vm.mediaRecorder = new MediaRecorder(stream);

          vm.mediaRecorder.ondataavailable = function (event) {
            if (event.data.size > 0) {
              vm.audioChunks.push(event.data);
            }
          };

          vm.mediaRecorder.onstop = function () {
            // Process audio for tone analysis
            var audioBlob = new Blob(vm.audioChunks, { type: "audio/wav" });
            vm.audioChunks = [];
            // Send to backend for tone analysis
            analyzeAudioTone(audioBlob);
          };
        })
        .catch(function (error) {
          console.error("Error accessing microphone:", error);
        });
    }

    function askCurrentQuestion() {
      console.log("=== ASK CURRENT QUESTION CALLED ===");
      console.log("Current question exists:", !!vm.currentQuestion);

      if (!vm.currentQuestion) {
        console.error("No current question available!");
        return;
      }

      var questionText =
        vm.currentQuestion.content ||
        vm.currentQuestion.question_text ||
        "Question text not available";
      console.log("=== ASKING QUESTION ===");
      console.log("Question text:", questionText);
      console.log("Question object:", vm.currentQuestion);

      console.log("Adding question to chat messages...");
      
      // Add question number and difficulty info
      var questionNumber = vm.currentQuestionIndex + 1;
      var totalQuestions = vm.questions.length;
      var questionDifficulty = vm.currentQuestion.difficulty_level || vm.session.difficulty_level || 'medium';
      var questionDifficultyLabel = DifficultyDisplayService.getDifficultyLabel(
        DifficultyDisplayService.normalizeDifficultyInput(questionDifficulty)
      );
      
      var questionPrefix = `Question ${questionNumber}/${totalQuestions} (${questionDifficultyLabel}): `;
      var fullQuestionText = questionPrefix + questionText;
      
      addChatMessage("ai", fullQuestionText);
      console.log("Question added, total messages:", vm.chatMessages.length);

      // Speak the question
      speakQuestion(questionText);

      // Reset answer
      vm.currentAnswer = "";
      vm.transcribedText = "";
    }

    function speakQuestion(text) {
      if (!vm.synthesis) return;

      vm.isSpeaking = true;
      var utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.9;
      utterance.pitch = 1;
      utterance.volume = 0.8;

      utterance.onend = function () {
        vm.isSpeaking = false;
        $timeout(function () { }, 0);
      };

      vm.synthesis.speak(utterance);
    }

    function startListening() {
      console.log("=== START LISTENING CALLED ===");
      console.log("Recognition available:", !!vm.recognition);
      console.log("Current listening state:", vm.isListening);

      if (!vm.recognition) {
        console.error("Speech recognition not supported");
        vm.error = "Speech recognition not supported in this browser";
        return;
      }

      vm.currentAnswer = "";
      vm.transcribedText = "";

      // Start voice analysis when user starts speaking
      startVoiceAnalysis();

      // Start audio recording for tone analysis
      if (vm.mediaRecorder && vm.mediaRecorder.state === "inactive") {
        vm.mediaRecorder.start();
        vm.isRecording = true;
      }

      vm.recognition.start();
    }

    function stopListening() {
      console.log("=== STOP LISTENING CALLED ===");
      console.log("Recognition available:", !!vm.recognition);
      console.log("Current listening state:", vm.isListening);

      if (vm.recognition && vm.isListening) {
        vm.recognition.stop();
      }

      // Stop audio recording
      if (vm.mediaRecorder && vm.mediaRecorder.state === "recording") {
        vm.mediaRecorder.stop();
        vm.isRecording = false;
      }

      // Pause/stop voice analysis when speak button becomes inactive
      if (vm.voiceAnalysisActive) {
        stopVoiceAnalysis();
      }
    }

    function submitAnswer() {
      console.log("=== SUBMIT ANSWER CALLED ===");
      console.log("Current answer:", vm.currentAnswer);
      console.log("Loading state:", vm.loading);

      if (!vm.currentAnswer.trim()) {
        console.log("No answer provided, showing error");
        vm.error = "Please provide an answer before submitting.";
        return;
      }

      vm.loading = true;
      vm.error = "";

      // Add user message to chat
      addChatMessage("user", vm.currentAnswer);

      // Calculate response time
      var responseTime = Math.max(
        1,
        vm.currentQuestion.expected_duration * 60 -
        (vm.questionTimeRemaining || 0)
      );

      var answerData = {
        question_id: parseInt(
          vm.currentQuestion.id || vm.currentQuestion.question_id || 1
        ),
        answer_text: vm.currentAnswer.trim(),
        response_time: Math.floor(responseTime),
      };

      // Add posture analysis data if available
      console.log("=== POSTURE DATA DEBUG ===");
      console.log("postureEnabled:", vm.postureEnabled);
      console.log("postureScores length:", vm.postureScores.length);
      console.log("postureScores array:", vm.postureScores);

      if (vm.postureEnabled && vm.postureScores.length > 0) {
        // Get the most recent posture score for this answer
        var recentPostureScore = vm.postureScores[vm.postureScores.length - 1];
        answerData.posture_data = {
          score: recentPostureScore.score,
          status: recentPostureScore.status,
        };

        console.log(
          "Including posture data in answer submission:",
          answerData.posture_data
        );
        console.log("Posture score type:", typeof recentPostureScore.score);
        console.log("Posture score value:", recentPostureScore.score);
      } else if (vm.postureEnabled && vm.postureFeedback) {
        // Use current posture feedback if no scores collected yet
        answerData.posture_data = {
          score: vm.postureFeedback.posture_score || 0,
          status: vm.postureFeedback.posture_status || "unknown",
        };

        console.log("Using current posture feedback:", answerData.posture_data);
      } else {
        console.log(
          "No posture data available - postureEnabled:",
          vm.postureEnabled,
          "postureScores length:",
          vm.postureScores.length
        );
      }
      console.log("=== END POSTURE DATA DEBUG ===");

      // Stop voice analysis and get results
      console.log("=== VOICE ANALYSIS DATA DEBUG ===");
      console.log("voiceAnalysisEnabled:", vm.voiceAnalysisEnabled);
      console.log("voiceAnalysisActive:", vm.voiceAnalysisActive);

      var voiceAnalysisResults = null;
      if (vm.voiceAnalysisActive) {
        voiceAnalysisResults = stopVoiceAnalysis();
        console.log("Voice analysis results:", voiceAnalysisResults);
        console.log(
          "Voice confidence score:",
          voiceAnalysisResults.averageScore
        );
      } else if (
        vm.voiceAnalysisResults &&
        vm.voiceAnalysisResults.averageScore &&
        vm.voiceAnalysisResults.averageScore > 0
      ) {
        // Use the most recent stored results if analysis already stopped
        voiceAnalysisResults = vm.voiceAnalysisResults;
        console.log(
          "Using stored voice analysis results:",
          voiceAnalysisResults
        );
      } else {
        console.log("Voice analysis not active and no stored results available");
      }
      console.log("=== END VOICE ANALYSIS DATA DEBUG ===");

      console.log("Answer data being sent:", answerData);

      // Submit answer first, then submit voice analysis separately
      InterviewService.submitAnswer(vm.sessionId, answerData)
        .then(function (response) {
          // Submit voice analysis results if available
          if (voiceAnalysisResults && voiceAnalysisResults.averageScore > 0) {
            var questionId = parseInt(
              vm.currentQuestion.id || vm.currentQuestion.question_id || 1
            );
            submitVoiceAnalysisToBackend(
              vm.sessionId,
              questionId,
              voiceAnalysisResults
            )
              .then(function (voiceResponse) {
                console.log("✅ Voice analysis submitted successfully");
              })
              .catch(function (voiceError) {
                console.error(
                  "❌ Failed to submit voice analysis, but continuing:",
                  voiceError
                );
              });
          }

          // Show AI feedback
          if (response.real_time_feedback) {
            var feedbackMsg = "Thank you for your answer!";
            if (response.real_time_feedback.quick_tip) {
              feedbackMsg += " Tip: " + response.real_time_feedback.quick_tip;
            }
            addChatMessage("ai", feedbackMsg);
          } else {
            addChatMessage("ai", "Thank you for your answer!");
          }

          // Move to next question
          nextQuestion();
        })
        .catch(function (error) {
          console.error("Answer submission error:", error);
          console.error("Error details:", error);

          var errorMsg = "Failed to submit answer.";
          if (error.status === 404) {
            errorMsg = "Session not found. Please start a new interview.";
          } else if (error.status === 400) {
            errorMsg =
              error.data?.detail || "Invalid answer data. Please try again.";
          } else if (error.status === 500) {
            errorMsg = "Server error. Please try again.";
          }

          vm.error = errorMsg;
          addChatMessage(
            "ai",
            "Sorry, there was an error processing your answer. Please try again."
          );
        })
        .finally(function () {
          vm.loading = false;
        });
    }

    function skipQuestion() {
      console.log("=== SKIP QUESTION CALLED ===");
      console.log("Current question index:", vm.currentQuestionIndex);
      console.log("Total questions:", vm.questions.length);

      addChatMessage("user", "[Skipped]");
      nextQuestion();
    }

    function nextQuestion() {
      if (vm.currentQuestionIndex < vm.questions.length - 1) {
        vm.currentQuestionIndex++;
        vm.currentQuestion = vm.questions[vm.currentQuestionIndex];
        vm.questionTimeRemaining =
          (vm.currentQuestion.expected_duration || 3) * 60;

        // Update session state with current progress
        SessionDataService.setSessionState(vm.sessionId, {
          status: 'active',
          currentQuestionIndex: vm.currentQuestionIndex,
          lastUpdateTime: Date.now()
        });

        $timeout(function () {
          askCurrentQuestion();
        }, 1000);
      } else {
        // All questions completed
        addChatMessage(
          "ai",
          "Congratulations! You have completed all the interview questions. Let me process your results..."
        );
        
        // Update session state to completed
        SessionDataService.setSessionState(vm.sessionId, {
          status: 'completed',
          currentQuestionIndex: vm.currentQuestionIndex,
          completionTime: Date.now()
        });
        
        $timeout(function () {
          endSession();
        }, 2000);
      }
    }

    function endSession() {
      console.log("=== END SESSION CALLED ===");
      console.log("Session ID:", vm.sessionId);

      // Prevent multiple calls
      if (vm.sessionEnding) {
        console.log("Session already ending, ignoring duplicate call");
        return;
      }
      vm.sessionEnding = true;

      // Stop all timers and media
      stopTimers();
      stopAllMedia();

      // Update session state to completing
      SessionDataService.setSessionState(vm.sessionId, {
        status: 'completing',
        completionStarted: Date.now()
      });

      if (vm.sessionId) {
        // Show completion message
        addChatMessage("ai", "Processing your interview results...");
        vm.loading = true;

        // Prepare comprehensive session completion data
        var sessionData = {
          session_id: vm.sessionId,
          completion_timestamp: new Date().toISOString(),
          questions_answered: vm.chatMessages.filter(function(msg) { 
            return msg.sender === 'user' && msg.message !== '[Skipped]'; 
          }).length,
          total_questions: vm.questions ? vm.questions.length : 0
        };

        console.log("Completing session with data:", sessionData);

        InterviewService.completeSession(vm.sessionId, sessionData)
          .then(function (response) {
            console.log("Session completion successful:", response);
            
            // Clear session state since session is completed
            SessionDataService.clearSessionState();
            
            // Add success message
            addChatMessage("ai", "Interview completed successfully! Redirecting to your feedback...");
            
            // Navigate to feedback with delay for user to see message
            $timeout(function () {
              navigateToFeedback();
            }, 2000);
          })
          .catch(function (error) {
            console.error("Error completing session:", error);
            
            // Still try to navigate to feedback even if completion API failed
            SessionDataService.clearSessionState();
            
            // Show error but still proceed
            addChatMessage("ai", "Interview completed. Generating your feedback...");
            
            $timeout(function () {
              navigateToFeedback();
            }, 1500);
          })
          .finally(function() {
            vm.loading = false;
            vm.sessionEnding = false;
          });
      } else {
        console.error("No session ID available for completion");
        vm.sessionEnding = false;
        navigateToDashboard();
      }
    }

    function stopAllMedia() {
      try {
        // Stop camera stream
        if (vm.mediaStream) {
          vm.mediaStream.getTracks().forEach(function (track) {
            track.stop();
          });
          vm.mediaStream = null;
        }

        // Stop voice recognition
        if (vm.recognition && vm.isListening) {
          vm.recognition.stop();
        }

        // Stop speech synthesis
        if (vm.synthesis) {
          vm.synthesis.cancel();
        }

        // Stop posture analysis
        if (vm.postureAnalysisActive) {
          stopPostureAnalysis();
        }

        // Stop voice analysis
        if (vm.voiceAnalysisActive) {
          stopVoiceAnalysis();
        }

        console.log("All media streams stopped successfully");
      } catch (error) {
        console.error("Error stopping media streams:", error);
      }
    }

    function navigateToFeedback() {
      try {
        console.log("Navigating to feedback page for session:", vm.sessionId);
        
        // Ensure we have a valid session ID
        if (!vm.sessionId) {
          console.error("No session ID for feedback navigation");
          navigateToDashboard();
          return;
        }

        // Use $timeout to ensure Angular digest cycle completes
        $timeout(function () {
          $location.path("/feedback/" + vm.sessionId);
        }, 0);
        
      } catch (error) {
        console.error("Error navigating to feedback:", error);
        navigateToDashboard();
      }
    }

    function navigateToDashboard() {
      try {
        console.log("Navigating to dashboard");
        $timeout(function () {
          $location.path("/dashboard");
        }, 0);
      } catch (error) {
        console.error("Error navigating to dashboard:", error);
        // Force navigation as last resort
        window.location.href = "#/dashboard";
      }
    }

    function analyzeAudioTone(audioBlob) {
      // This would send audio to backend for tone analysis
      // For now, we'll simulate the analysis
      vm.lastAudioAnalysis = {
        confidence_score: Math.random() * 100,
        tone_analysis: {
          pitch_variation: Math.random() * 100,
          speaking_pace: Math.random() * 100,
          volume_consistency: Math.random() * 100,
        },
      };
    }

    function addChatMessage(sender, message) {
      vm.chatMessages.push({
        sender: sender, // 'ai' or 'user'
        message: message,
        timestamp: new Date(),
      });

      // Scroll to bottom
      $timeout(function () {
        var chatContainer = document.getElementById("chatContainer");
        if (chatContainer) {
          chatContainer.scrollTop = chatContainer.scrollHeight;
        }
      }, 100);
    }

    function startTimers() {
      // Session timer
      vm.sessionTimer = $interval(function () {
        if (vm.sessionTimeRemaining > 0) {
          vm.sessionTimeRemaining--;
        } else {
          endSession();
        }
      }, 1000);

      // Question timer
      vm.questionTimer = $interval(function () {
        if (vm.questionTimeRemaining > 0) {
          vm.questionTimeRemaining--;
        } else {
          // Auto-submit or move to next question
          if (vm.currentAnswer.trim()) {
            submitAnswer();
          } else {
            skipQuestion();
          }
        }
      }, 1000);
    }

    function stopTimers() {
      if (vm.sessionTimer) {
        $interval.cancel(vm.sessionTimer);
        vm.sessionTimer = null;
      }
      if (vm.questionTimer) {
        $interval.cancel(vm.questionTimer);
        vm.questionTimer = null;
      }
    }

    function startCamera() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        vm.cameraError = "Camera not supported in this browser.";
        return;
      }

      vm.cameraError = "";
      console.log("Starting interview camera...");

      navigator.mediaDevices
        .getUserMedia({
          video: {
            width: { ideal: 640 },
            height: { ideal: 480 },
            facingMode: "user",
          },
          audio: true,
        })
        .then(function (stream) {
          console.log("Interview camera stream obtained:", stream);
          vm.mediaStream = stream;
          vm.cameraActive = true;
          vm.cameraError = "";

          $timeout(function () {
            var videoElement = document.getElementById("interviewVideo");
            if (videoElement) {
              videoElement.srcObject = stream;
              videoElement.onloadedmetadata = function () {
                videoElement.play().catch(function (e) {
                  console.error("Error playing interview video:", e);
                });

                // Automatically enable posture detection after camera is ready
                $timeout(function () {
                  if (!vm.postureEnabled) {
                    console.log("Automatically enabling posture detection...");
                    vm.postureEnabled = true;
                    startPostureAnalysis();
                  }
                }, 2000); // Wait 2 seconds for camera to stabilize
              };
            }
          }, 100);
        })
        .catch(function (error) {
          console.error("Error accessing interview camera:", error);
          vm.cameraActive = false;

          if (error.name === "NotAllowedError") {
            vm.cameraError =
              "Camera access denied. Please enable camera permissions.";
          } else if (error.name === "NotFoundError") {
            vm.cameraError = "No camera found. Please connect a camera.";
          } else {
            vm.cameraError = "Unable to access camera: " + error.message;
          }

          $timeout(function () { }, 0);
        });
    }

    function stopCamera() {
      try {
        if (vm.mediaStream) {
          vm.mediaStream.getTracks().forEach(function (track) {
            track.stop();
          });
          vm.mediaStream = null;
        }
        vm.cameraActive = false;
        vm.cameraError = "";

        var videoElement = document.getElementById("interviewVideo");
        if (videoElement) {
          videoElement.srcObject = null;
        }
      } catch (error) {
        console.error("Error stopping interview camera:", error);
      }
    }

    function formatTime(seconds) {
      var minutes = Math.floor(seconds / 60);
      var remainingSeconds = seconds % 60;
      return (
        minutes + ":" + (remainingSeconds < 10 ? "0" : "") + remainingSeconds
      );
    }

    function initializePostureDetection() {
      if (!PostureService) {
        console.warn("PostureService not available");
        return;
      }

      console.log(
        "Initializing posture detection service for chat interview..."
      );

      // Set up posture feedback callback
      PostureService.onPostureFeedback = function (feedback) {
        console.log("Received posture feedback in chat:", feedback);

        // Use $timeout to safely update the scope without digest cycle conflicts
        $timeout(function () {
          vm.postureFeedback = feedback;
          vm.showPostureFeedback = true;

          // Store posture score for feedback system
          if (feedback.posture_score && feedback.posture_score > 0) {
            console.log("=== POSTURE SCORE COLLECTION DEBUG ===");
            console.log("Raw feedback received:", feedback);
            console.log("Posture score type:", typeof feedback.posture_score);
            console.log("Posture score value:", feedback.posture_score);

            vm.postureScores.push({
              score: feedback.posture_score,
              status: feedback.posture_status,
              timestamp: new Date().toISOString(),
              feedback_message: feedback.feedback_message || "",
            });

            // Calculate average posture score
            if (vm.postureScores.length > 0) {
              vm.averagePostureScore = Math.round(
                vm.postureScores.reduce((sum, item) => sum + item.score, 0) /
                vm.postureScores.length
              );
            }

            console.log("Updated posture scores array:", vm.postureScores);
            console.log(
              "Current average posture score:",
              vm.averagePostureScore
            );
            console.log("Total scores collected:", vm.postureScores.length);
            console.log("========================================");
          } else if (feedback.score && feedback.score > 0) {
            // Alternative field name
            console.log("=== POSTURE SCORE COLLECTION DEBUG (alternative) ===");
            console.log("Using feedback.score:", feedback.score);

            vm.postureScores.push({
              score: feedback.score,
              status: feedback.status || feedback.posture_status || "unknown",
              timestamp: new Date().toISOString(),
              feedback_message: feedback.feedback_message || "",
            });

            // Calculate average posture score
            if (vm.postureScores.length > 0) {
              vm.averagePostureScore = Math.round(
                vm.postureScores.reduce((sum, item) => sum + item.score, 0) /
                vm.postureScores.length
              );
            }

            console.log("Updated posture scores array:", vm.postureScores);
            console.log(
              "Current average posture score:",
              vm.averagePostureScore
            );
            console.log("Total scores collected:", vm.postureScores.length);
            console.log("========================================");
          } else {
            console.log(
              "Posture score not stored - invalid data:",
              feedback.posture_score || feedback.score
            );
            console.log("Full feedback object:", feedback);
          }

          // Auto-hide feedback after 5 seconds if status is good
          if (feedback.posture_status === "good") {
            $timeout(function () {
              vm.showPostureFeedback = false;
            }, 5000);
          }
        }, 0);
      };

      PostureService.onError = function (error) {
        console.error("Posture detection error in chat:", error);

        // Use $timeout to safely update the scope without digest cycle conflicts
        $timeout(function () {
          vm.postureFeedback = null;
          vm.showPostureFeedback = false;
        }, 0);
      };

      console.log(
        "Posture detection service initialized successfully for chat interview"
      );
    }

    function togglePostureDetection() {
      if (!vm.cameraActive) {
        vm.error = "Please enable camera first";
        return;
      }

      vm.postureEnabled = !vm.postureEnabled;
      if (vm.postureEnabled) {
        startPostureAnalysis();
        console.log("Posture detection enabled");
      } else {
        stopPostureAnalysis();
        console.log("Posture detection disabled");
      }
    }

    function startPostureAnalysis() {
      if (!PostureService || !vm.cameraActive || !vm.sessionId) {
        console.warn(
          "Cannot start posture analysis - service, camera, or session not available"
        );
        return;
      }

      var videoElement = document.getElementById("interviewVideo");
      if (!videoElement) {
        console.error("Video element not found for posture analysis");
        vm.error = "Video element not found for posture analysis";
        return;
      }

      try {
        console.log("Starting posture analysis...");
        PostureService.startPostureAnalysis(videoElement, vm.sessionId, 3000); // Analyze every 3 seconds
        vm.postureAnalysisActive = true;
        console.log("Posture analysis started successfully");
      } catch (error) {
        console.error("Error starting posture analysis:", error);
        vm.error = "Failed to start posture detection: " + error.message;
      }
    }

    function stopPostureAnalysis() {
      if (PostureService) {
        PostureService.stopPostureAnalysis();
        vm.postureAnalysisActive = false;
        vm.postureFeedback = null;
        console.log("Posture analysis stopped");
      }
    }

    function getPostureStatusText(status) {
      switch (status) {
        case "good":
          return "Good Posture!";
        case "needs_improvement":
          return "Needs Improvement";
        case "bad":
          return "Poor Posture";
        case "no_pose":
          return "No Pose Detected";
        case "error":
          return "Analysis Error";
        default:
          return "Unknown Status";
      }
    }

    // Voice Analysis Functions
    function startVoiceAnalysis() {
      if (!vm.voiceAnalysisEnabled) {
        console.log("Voice analysis disabled");
        return;
      }

      console.log("=== STARTING VOICE ANALYSIS ===");
      console.log(
        "Question ID:",
        vm.currentQuestion.id || vm.currentQuestion.question_id
      );

      VoiceAnalysisService.startAnalysis()
        .then(function (result) {
          if (result.success) {
            vm.voiceAnalysisActive = true;
            vm.voiceAnalysisError = "";
            console.log("✅ Voice analysis started successfully");

            // Start monitoring voice score
            startVoiceScoreMonitoring();
          } else {
            vm.voiceAnalysisError = result.message;
            console.error("❌ Failed to start voice analysis:", result.message);
          }
        })
        .catch(function (error) {
          vm.voiceAnalysisError =
            error.message || "Failed to start voice analysis";
          console.error("❌ Voice analysis error:", error);
        });
    }

    function stopVoiceAnalysis() {
      if (!vm.voiceAnalysisActive) {
        return null;
      }

      console.log("=== STOPPING VOICE ANALYSIS ===");

      var results = VoiceAnalysisService.stopAnalysis();
      vm.voiceAnalysisActive = false;
      vm.voiceAnalysisResults = results;
      // Reset live score display when analysis stops
      vm.currentVoiceScore = 0;

      // Clear voice score monitoring interval if running
      if (vm.voiceScoreInterval) {
        $interval.cancel(vm.voiceScoreInterval);
        vm.voiceScoreInterval = null;
      }

      console.log("Voice analysis results:", results);
      console.log("Average score:", results.averageScore);
      console.log("Duration:", results.duration + "s");
      console.log("Suggestions:", results.suggestions);

      return results;
    }

    function startVoiceScoreMonitoring() {
      // Update current voice score every second
      var voiceScoreInterval = $interval(function () {
        if (vm.voiceAnalysisActive) {
          vm.currentVoiceScore = VoiceAnalysisService.getCurrentScore();
        }
      }, 1000);

      // Store interval for cleanup
      vm.voiceScoreInterval = voiceScoreInterval;
    }

    function submitVoiceAnalysisToBackend(sessionId, questionId, voiceResults) {
      if (!voiceResults || voiceResults.averageScore === 0) {
        console.log("No voice analysis results to submit");
        return Promise.resolve();
      }

      console.log("=== SUBMITTING VOICE ANALYSIS TO BACKEND ===");
      console.log("Session ID:", sessionId);
      console.log("Question ID:", questionId);
      console.log("Voice Score:", voiceResults.averageScore);

      var voiceData = {
        session_id: parseInt(sessionId),
        question_id: parseInt(questionId),
        tone_confidence_score: voiceResults.averageScore,
        analysis_duration: voiceResults.duration,
        total_samples: voiceResults.totalSamples,
        improvement_suggestions: voiceResults.suggestions,
      };

      return ApiService.post("/interviews/voice-confidence", voiceData)
        .then(function (response) {
          console.log("✅ Voice analysis submitted successfully:", response);
          return response;
        })
        .catch(function (error) {
          console.error("❌ Failed to submit voice analysis:", error);
          throw error;
        });
    }

    // Cleanup on destroy
    this.$onDestroy = function () {
      stopTimers();
      stopCamera();
      if (vm.recognition && vm.isListening) {
        vm.recognition.stop();
      }
      stopPostureAnalysis(); // Ensure posture analysis is stopped on destroy

      // Stop voice analysis
      if (vm.voiceAnalysisActive) {
        stopVoiceAnalysis();
      }

      // Clear voice score monitoring interval
      if (vm.voiceScoreInterval) {
        $interval.cancel(vm.voiceScoreInterval);
      }
    };

    function validateSession() {
      console.log("=== VALIDATING SESSION ===");
      
      try {
        // Check if we have a valid session
        if (!vm.session || !vm.session.id) {
          console.error("Invalid session object - missing session or session.id");
          vm.error = "Invalid session data. Please start a new interview.";
          return false;
        }
        
        // Check if we have questions
        if (!vm.questions || !Array.isArray(vm.questions) || vm.questions.length === 0) {
          console.error("Invalid or empty questions array");
          vm.error = "No questions available for this interview. Please try again.";
          return false;
        }
        
        // Validate each question has required fields
        var validQuestions = 0;
        for (var i = 0; i < vm.questions.length; i++) {
          var question = vm.questions[i];
          
          // Check for question ID
          if (!question.id && !question.question_id) {
            console.warn("Question missing ID at index", i, "- attempting to fix");
            question.id = question.question_id || (i + 1);
          }
          
          // Check for question content
          if (!question.content && !question.question_text) {
            console.warn("Question missing content at index", i, "- attempting to fix");
            question.content = question.question_text || "Please share your thoughts on this topic.";
          }
          
          // Ensure other required fields exist
          question.question_type = question.question_type || "behavioral";
          question.expected_duration = question.expected_duration || 3;
          
          validQuestions++;
        }
        
        if (validQuestions === 0) {
          console.error("No valid questions found after validation");
          vm.error = "Unable to load interview questions. Please try again.";
          return false;
        }
        
        // Validate session status
        if (vm.session.status && vm.session.status === 'completed') {
          console.warn("Session is already completed");
          vm.error = "This interview session has already been completed.";
          return false;
        }
        
        console.log("Session validation passed - found", validQuestions, "valid questions");
        return true;
        
      } catch (error) {
        console.error("Error during session validation:", error);
        vm.error = "Session validation failed. Please try starting a new interview.";
        return false;
      }
    }

    function recoverSession() {
      try {
        console.log("=== ATTEMPTING SESSION RECOVERY ===");
        
        // Try to recover session state if available
        var sessionState = SessionDataService.getSessionState();
        console.log("Retrieved session state:", sessionState);
        
        if (sessionState && sessionState.sessionId === vm.sessionId) {
          console.log("Session state matches current session ID");
          
          // Restore session progress
          if (sessionState.state && sessionState.state.currentQuestionIndex !== undefined) {
            var recoveredIndex = sessionState.state.currentQuestionIndex;
            console.log("Attempting to recover to question index:", recoveredIndex);
            
            // Validate recovered index
            if (recoveredIndex >= 0 && recoveredIndex < vm.questions.length) {
              vm.currentQuestionIndex = recoveredIndex;
              vm.currentQuestion = vm.questions[vm.currentQuestionIndex];
              
              console.log("Session recovered successfully - current question index:", vm.currentQuestionIndex);
              console.log("Current question:", vm.currentQuestion);
              
              // Update session state with recovery info
              SessionDataService.setSessionState(vm.sessionId, {
                status: 'recovered',
                currentQuestionIndex: vm.currentQuestionIndex,
                recoveryTime: Date.now(),
                lastActivity: Date.now()
              });
              
              return true;
            } else {
              console.warn("Recovered index out of bounds, starting from beginning");
              return false;
            }
          } else {
            console.log("No valid state data found in session state");
            return false;
          }
        } else {
          console.log("No matching session state found for recovery");
          return false;
        }
      } catch (error) {
        console.error("Error during session recovery:", error);
        return false;
      }
    }

    function getDifficultyWelcomeMessage(difficultyLabel) {
      switch (difficultyLabel) {
        case 'Easy':
          return "This session is set to EASY difficulty - perfect for getting comfortable with the interview format.";
        case 'Medium':
          return "This session is set to MEDIUM difficulty - a balanced mix of questions to test your skills.";
        case 'Hard':
          return "This session is set to HARD difficulty - challenging questions to push your abilities.";
        case 'Expert':
          return "This session is set to EXPERT difficulty - advanced questions for experienced professionals.";
        default:
          return "This session is set to " + difficultyLabel.toUpperCase() + " difficulty.";
      }
    }

    // Add methods to controller for template access
    vm.getConsistentDifficultyLabel = function(difficulty) {
      return DifficultyDisplayService.getDifficultyLabel(
        DifficultyDisplayService.normalizeDifficultyInput(difficulty)
      );
    };

    vm.getDifficultyColor = function(difficulty) {
      var difficultyLabel = DifficultyDisplayService.getDifficultyLabel(
        DifficultyDisplayService.normalizeDifficultyInput(difficulty)
      );
      switch (difficultyLabel) {
        case 'Easy': return 'success';
        case 'Medium': return 'warning';
        case 'Hard': return 'danger';
        case 'Expert': return 'dark';
        default: return 'secondary';
      }
    };
    // ==================== Difficulty State Management ====================

    function initializeDifficultyState() {
      if (!vm.session || !vm.session.id) {
        console.warn('Cannot initialize difficulty state without session');
        return;
      }

      console.log('Initializing difficulty state for session:', vm.session.id);

      // Subscribe to difficulty changes for real-time updates
      vm.difficultyChangeSubscription = UnifiedDifficultyStateService.subscribeToChanges(vm.onDifficultyChange);

      // Load initial difficulty state
      UnifiedDifficultyStateService.getSessionDifficultyState(vm.session.id)
        .then(function(difficultyState) {
          vm.currentDifficultyState = difficultyState;
          vm.updateDifficultyDisplay();
          console.log('Difficulty state loaded for session:', vm.session.id, difficultyState);
        })
        .catch(function(error) {
          console.error('Error loading difficulty state:', error);
          // Use fallback from session data
          vm.currentDifficultyState = {
            session_id: vm.session.id,
            initial_difficulty: vm.session.difficulty_level || 'medium',
            current_difficulty: vm.session.difficulty_level || 'medium',
            final_difficulty: null,
            difficulty_changes: [],
            is_fallback: true
          };
          vm.updateDifficultyDisplay();
        });
    }

    function updateDifficultyDisplay() {
      if (!vm.currentDifficultyState) {
        return;
      }

      UnifiedDifficultyStateService.getDifficultyForDisplay(vm.session.id)
        .then(function(displayInfo) {
          vm.difficultyDisplay = displayInfo;
          
          // Sync difficulty across all components for this session
          UnifiedDifficultyStateService.syncDifficultyAcrossComponents(
            vm.session.id, 
            displayInfo.current.string
          );
          
          console.log('Difficulty display updated:', displayInfo);
        })
        .catch(function(error) {
          console.error('Error updating difficulty display:', error);
          // Create fallback display
          vm.difficultyDisplay = createFallbackDifficultyDisplay();
        });
    }

    function onDifficultyChange(changeData) {
      if (changeData.sessionId !== vm.session.id) {
        return; // Not for this session
      }

      console.log('Difficulty change received for session:', changeData);

      // Update current state
      if (vm.currentDifficultyState) {
        vm.currentDifficultyState.current_difficulty = changeData.newDifficulty;
        vm.currentDifficultyState.last_updated = changeData.timestamp;
      }

      // Update display
      vm.updateDifficultyDisplay();

      // Add chat message about difficulty change
      addChatMessage("ai", 
        "I've adjusted the difficulty to " + changeData.newDifficulty.charAt(0).toUpperCase() + 
        changeData.newDifficulty.slice(1) + " based on your performance. " + 
        (changeData.reason || "Let's continue with the next question.")
      );
    }

    function getConsistentDifficultyLabel(difficultyString) {
      if (!difficultyString) {
        return 'Medium';
      }
      
      var normalizedLevel = DifficultyDisplayService.normalizeDifficultyInput(difficultyString);
      return DifficultyDisplayService.getDifficultyLabel(normalizedLevel);
    }

    function createFallbackDifficultyDisplay() {
      var fallbackDifficulty = vm.session.difficulty_level || 'medium';
      var normalizedLevel = DifficultyDisplayService.normalizeDifficultyInput(fallbackDifficulty);
      var difficultyInfo = DifficultyDisplayService.getDifficultyInfo(normalizedLevel);

      return {
        current: {
          level: normalizedLevel,
          string: fallbackDifficulty,
          label: difficultyInfo.label,
          color: difficultyInfo.color,
          icon: difficultyInfo.icon,
          badgeClass: difficultyInfo.badgeClass
        },
        initial: {
          level: normalizedLevel,
          string: fallbackDifficulty,
          label: difficultyInfo.label
        },
        final: null,
        hasChanged: false,
        isCompleted: false,
        changeCount: 0,
        error: 'Using fallback difficulty display'
      };
    }

  }
})();