/**
 * Interview Chat Controller - Handles chatbot-style interview with audio
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .controller('InterviewChatController', InterviewChatController);

    InterviewChatController.$inject = ['$location', '$routeParams', '$timeout', '$interval', 'AuthService', 'InterviewService'];

    function InterviewChatController($location, $routeParams, $timeout, $interval, AuthService, InterviewService) {
        var vm = this;

        // Properties
        vm.sessionId = $routeParams.sessionId;
        vm.session = null;
        vm.questions = [];
        vm.currentQuestionIndex = 0;
        vm.currentQuestion = null;
        vm.chatMessages = [];
        vm.loading = false;
        vm.error = '';
        
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
        vm.cameraError = '';
        
        // Timer properties
        vm.sessionTimeRemaining = 0;
        vm.questionTimeRemaining = 0;
        vm.sessionTimer = null;
        vm.questionTimer = null;
        
        // Current answer
        vm.currentAnswer = '';
        vm.transcribedText = '';

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

        // Initialize
        activate();

        function activate() {
            console.log('Interview Chat activated with session ID:', vm.sessionId);
            
            if (!vm.sessionId) {
                vm.error = 'No session ID provided';
                return;
            }

            // Initialize session data from URL params
            var sessionData = $routeParams.sessionData;
            if (sessionData) {
                try {
                    var data = JSON.parse(sessionData);
                    vm.session = data.session;
                    vm.questions = data.questions || [];
                    initializeInterview();
                } catch (e) {
                    console.error('Error parsing session data:', e);
                    loadSessionData();
                }
            } else {
                loadSessionData();
            }

            // Initialize audio services and camera
            initializeAudioServices();
            
            // Start camera
            $timeout(function() {
                startCamera();
            }, 1000);
        }

        function loadSessionData() {
            vm.loading = true;
            InterviewService.getSession(vm.sessionId)
                .then(function(response) {
                    vm.session = response.session;
                    vm.questions = response.questions || [];
                    initializeInterview();
                })
                .catch(function(error) {
                    console.error('Error loading session:', error);
                    vm.error = 'Failed to load interview session';
                })
                .finally(function() {
                    vm.loading = false;
                });
        }

        function initializeInterview() {
            console.log('Initializing interview with questions:', vm.questions);
            
            // Check if we have questions from backend
            if (!vm.questions || vm.questions.length === 0) {
                console.error('No questions received from backend!');
                vm.error = 'No questions available for this interview. Please try starting a new session.';
                return;
            }
            
            console.log('Questions received from backend:', vm.questions);
            
            if (vm.questions.length > 0) {
                vm.currentQuestion = vm.questions[0];
                vm.currentQuestionIndex = 0;
                
                console.log('Current question:', vm.currentQuestion);
                console.log('Question content field:', vm.currentQuestion.content);
                console.log('Question text field:', vm.currentQuestion.question_text);
                
                // Initialize timers
                vm.sessionTimeRemaining = (vm.session.duration || 30) * 60;
                vm.questionTimeRemaining = (vm.currentQuestion.expected_duration || 3) * 60;
                
                // Add welcome message
                addChatMessage('ai', 'Welcome to your interview! I\'ll be asking you questions and you can respond using voice or text. Let\'s begin!');
                
                // Start with first question
                $timeout(function() {
                    askCurrentQuestion();
                    startTimers();
                }, 1000);
            } else {
                vm.error = 'No questions available for this interview';
            }
        }

        function initializeAudioServices() {
            // Initialize Speech Recognition
            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                vm.recognition = new SpeechRecognition();
                vm.recognition.continuous = true;
                vm.recognition.interimResults = true;
                vm.recognition.lang = 'en-US';

                vm.recognition.onstart = function() {
                    console.log('Speech recognition started');
                    vm.isListening = true;
                    $timeout(function() {}, 0);
                };

                vm.recognition.onresult = function(event) {
                    var transcript = '';
                    for (var i = event.resultIndex; i < event.results.length; i++) {
                        if (event.results[i].isFinal) {
                            transcript += event.results[i][0].transcript;
                        }
                    }
                    if (transcript) {
                        vm.transcribedText = transcript;
                        vm.currentAnswer = transcript;
                        $timeout(function() {}, 0);
                    }
                };

                vm.recognition.onerror = function(event) {
                    console.error('Speech recognition error:', event.error);
                    vm.isListening = false;
                    $timeout(function() {}, 0);
                };

                vm.recognition.onend = function() {
                    console.log('Speech recognition ended');
                    vm.isListening = false;
                    $timeout(function() {}, 0);
                };
            }

            // Initialize Speech Synthesis
            if ('speechSynthesis' in window) {
                vm.synthesis = window.speechSynthesis;
            }

            // Initialize Media Recorder for audio analysis
            initializeMediaRecorder();
        }

        function initializeMediaRecorder() {
            navigator.mediaDevices.getUserMedia({ audio: true })
                .then(function(stream) {
                    vm.mediaStream = stream;
                    vm.mediaRecorder = new MediaRecorder(stream);
                    
                    vm.mediaRecorder.ondataavailable = function(event) {
                        if (event.data.size > 0) {
                            vm.audioChunks.push(event.data);
                        }
                    };

                    vm.mediaRecorder.onstop = function() {
                        // Process audio for tone analysis
                        var audioBlob = new Blob(vm.audioChunks, { type: 'audio/wav' });
                        vm.audioChunks = [];
                        // Send to backend for tone analysis
                        analyzeAudioTone(audioBlob);
                    };
                })
                .catch(function(error) {
                    console.error('Error accessing microphone:', error);
                });
        }

        function askCurrentQuestion() {
            if (!vm.currentQuestion) return;

            var questionText = vm.currentQuestion.content || vm.currentQuestion.question_text || 'Question text not available';
            console.log('Asking question:', questionText);
            console.log('Question object:', vm.currentQuestion);
            
            addChatMessage('ai', questionText);
            
            // Speak the question
            speakQuestion(questionText);
            
            // Reset answer
            vm.currentAnswer = '';
            vm.transcribedText = '';
        }

        function speakQuestion(text) {
            if (!vm.synthesis) return;

            vm.isSpeaking = true;
            var utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.9;
            utterance.pitch = 1;
            utterance.volume = 0.8;

            utterance.onend = function() {
                vm.isSpeaking = false;
                $timeout(function() {}, 0);
            };

            vm.synthesis.speak(utterance);
        }

        function startListening() {
            if (!vm.recognition) {
                vm.error = 'Speech recognition not supported in this browser';
                return;
            }

            vm.currentAnswer = '';
            vm.transcribedText = '';
            
            // Start audio recording for tone analysis
            if (vm.mediaRecorder && vm.mediaRecorder.state === 'inactive') {
                vm.mediaRecorder.start();
                vm.isRecording = true;
            }

            vm.recognition.start();
        }

        function stopListening() {
            if (vm.recognition && vm.isListening) {
                vm.recognition.stop();
            }

            // Stop audio recording
            if (vm.mediaRecorder && vm.mediaRecorder.state === 'recording') {
                vm.mediaRecorder.stop();
                vm.isRecording = false;
            }
        }

        function submitAnswer() {
            if (!vm.currentAnswer.trim()) {
                vm.error = 'Please provide an answer before submitting.';
                return;
            }

            vm.loading = true;
            vm.error = '';

            // Add user message to chat
            addChatMessage('user', vm.currentAnswer);

            // Calculate response time
            var responseTime = Math.max(1, (vm.currentQuestion.expected_duration * 60) - (vm.questionTimeRemaining || 0));
            
            var answerData = {
                question_id: parseInt(vm.currentQuestion.id || vm.currentQuestion.question_id || 1),
                answer_text: vm.currentAnswer.trim(),
                response_time: Math.floor(responseTime)
            };
            
            console.log('Answer data being sent:', answerData);

            console.log('Submitting answer:', answerData);

            InterviewService.submitAnswer(vm.sessionId, answerData)
                .then(function(response) {
                    console.log('Answer submitted successfully:', response);
                    
                    // Show AI feedback
                    if (response.real_time_feedback) {
                        var feedbackMsg = 'Thank you for your answer!';
                        if (response.real_time_feedback.quick_tip) {
                            feedbackMsg += ' Tip: ' + response.real_time_feedback.quick_tip;
                        }
                        addChatMessage('ai', feedbackMsg);
                    } else {
                        addChatMessage('ai', 'Thank you for your answer!');
                    }
                    
                    // Move to next question
                    nextQuestion();
                })
                .catch(function(error) {
                    console.error('Answer submission error:', error);
                    console.error('Error details:', error);
                    
                    var errorMsg = 'Failed to submit answer.';
                    if (error.status === 404) {
                        errorMsg = 'Session not found. Please start a new interview.';
                    } else if (error.status === 400) {
                        errorMsg = error.data?.detail || 'Invalid answer data. Please try again.';
                    } else if (error.status === 500) {
                        errorMsg = 'Server error. Please try again.';
                    }
                    
                    vm.error = errorMsg;
                    addChatMessage('ai', 'Sorry, there was an error processing your answer. Please try again.');
                })
                .finally(function() {
                    vm.loading = false;
                });
        }

        function skipQuestion() {
            addChatMessage('user', '[Skipped]');
            nextQuestion();
        }

        function nextQuestion() {
            if (vm.currentQuestionIndex < vm.questions.length - 1) {
                vm.currentQuestionIndex++;
                vm.currentQuestion = vm.questions[vm.currentQuestionIndex];
                vm.questionTimeRemaining = (vm.currentQuestion.expected_duration || 3) * 60;
                
                $timeout(function() {
                    askCurrentQuestion();
                }, 1000);
            } else {
                // All questions completed
                addChatMessage('ai', 'Congratulations! You have completed all the interview questions. Let me process your results...');
                $timeout(function() {
                    endSession();
                }, 2000);
            }
        }

        function endSession() {
            console.log('Ending interview session');
            stopTimers();
            
            if (vm.mediaStream) {
                vm.mediaStream.getTracks().forEach(function(track) {
                    track.stop();
                });
            }

            if (vm.sessionId) {
                InterviewService.completeSession(vm.sessionId)
                    .then(function(response) {
                        console.log('Session completed:', response);
                        $timeout(function() {
                            $location.path('/feedback/' + vm.sessionId);
                        }, 0);
                    })
                    .catch(function(error) {
                        console.error('Error ending session:', error);
                        $timeout(function() {
                            $location.path('/feedback/' + vm.sessionId);
                        }, 0);
                    });
            } else {
                $location.path('/dashboard');
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
                    volume_consistency: Math.random() * 100
                }
            };
        }

        function addChatMessage(sender, message) {
            vm.chatMessages.push({
                sender: sender, // 'ai' or 'user'
                message: message,
                timestamp: new Date()
            });
            
            // Scroll to bottom
            $timeout(function() {
                var chatContainer = document.getElementById('chatContainer');
                if (chatContainer) {
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                }
            }, 100);
        }

        function startTimers() {
            // Session timer
            vm.sessionTimer = $interval(function() {
                if (vm.sessionTimeRemaining > 0) {
                    vm.sessionTimeRemaining--;
                } else {
                    endSession();
                }
            }, 1000);

            // Question timer
            vm.questionTimer = $interval(function() {
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
                vm.cameraError = 'Camera not supported in this browser.';
                return;
            }

            vm.cameraError = '';
            console.log('Starting interview camera...');

            navigator.mediaDevices.getUserMedia({ 
                video: { 
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user'
                }, 
                audio: true 
            })
                .then(function(stream) {
                    console.log('Interview camera stream obtained:', stream);
                    vm.mediaStream = stream;
                    vm.cameraActive = true;
                    vm.cameraError = '';
                    
                    $timeout(function() {
                        var videoElement = document.getElementById('interviewVideo');
                        if (videoElement) {
                            videoElement.srcObject = stream;
                            videoElement.onloadedmetadata = function() {
                                videoElement.play().catch(function(e) {
                                    console.error('Error playing interview video:', e);
                                });
                            };
                        }
                    }, 100);
                })
                .catch(function(error) {
                    console.error('Error accessing interview camera:', error);
                    vm.cameraActive = false;
                    
                    if (error.name === 'NotAllowedError') {
                        vm.cameraError = 'Camera access denied. Please enable camera permissions.';
                    } else if (error.name === 'NotFoundError') {
                        vm.cameraError = 'No camera found. Please connect a camera.';
                    } else {
                        vm.cameraError = 'Unable to access camera: ' + error.message;
                    }
                    
                    $timeout(function() {}, 0);
                });
        }

        function stopCamera() {
            try {
                if (vm.mediaStream) {
                    vm.mediaStream.getTracks().forEach(function(track) {
                        track.stop();
                    });
                    vm.mediaStream = null;
                }
                vm.cameraActive = false;
                vm.cameraError = '';
                
                var videoElement = document.getElementById('interviewVideo');
                if (videoElement) {
                    videoElement.srcObject = null;
                }
            } catch (error) {
                console.error('Error stopping interview camera:', error);
            }
        }

        function formatTime(seconds) {
            var minutes = Math.floor(seconds / 60);
            var remainingSeconds = seconds % 60;
            return minutes + ':' + (remainingSeconds < 10 ? '0' : '') + remainingSeconds;
        }

        // Cleanup on destroy
        this.$onDestroy = function() {
            stopTimers();
            stopCamera();
            if (vm.recognition && vm.isListening) {
                vm.recognition.stop();
            }
        };
    }
})();