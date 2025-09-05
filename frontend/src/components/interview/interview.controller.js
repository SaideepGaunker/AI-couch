/**
 * Interview Controller - Component-based Architecture
 */
(function () {
    'use strict';

    angular
        .module('interviewPrepApp')
        .controller('InterviewController', InterviewController);

    InterviewController.$inject = ['$location', '$timeout', '$interval', '$scope', 'AuthService', 'InterviewService', 'PostureService', 'UnifiedDifficultyStateService', 'DifficultyDisplayService'];

    function InterviewController($location, $timeout, $interval, $scope, AuthService, InterviewService, PostureService, UnifiedDifficultyStateService, DifficultyDisplayService) {
        var vm = this;

        // Properties
        vm.config = {
            target_role: null, // Will be set based on selectedRole
            selectedRole: null, // New hierarchical role data
            session_type: 'mixed',
            difficulty: 'intermediate',
            duration: 30,
            question_count: 5,
            enable_video: true,
            enable_audio: true
        };

        vm.session = null;
        vm.questions = [];
        vm.currentQuestion = null;
        vm.currentQuestionIndex = 0;
        vm.userAnswer = '';
        vm.loading = false;
        vm.error = '';
        vm.cameraError = '';
        vm.cameraReady = false;

        // Media properties
        vm.cameraActive = false;
        vm.microphoneActive = false;
        vm.isRecording = false;
        vm.mediaStream = null;
        vm.mediaRecorder = null;

        // Timer properties
        vm.sessionTimeRemaining = 0;
        vm.questionTimeRemaining = 0;
        vm.sessionTimer = null;
        vm.questionTimer = null;
        vm.isPaused = false;

        // Feedback properties
        vm.realTimeFeedback = null;
        
        // Posture detection properties
        vm.postureEnabled = false;
        vm.postureFeedback = null;
        vm.showPostureFeedback = false;
        vm.postureAnalysisActive = false;

        // Difficulty state management properties
        vm.currentDifficultyState = null;
        vm.difficultyDisplay = null;
        vm.difficultyChangeSubscription = null;

        // Methods
        vm.startInterview = startInterview;
        vm.startTest = startTest;
        vm.goToDashboard = goToDashboard;
        vm.submitAnswer = submitAnswer;
        vm.skipQuestion = skipQuestion;
        vm.nextQuestion = nextQuestion;
        vm.pauseSession = pauseSession;
        vm.resumeSession = resumeSession;
        vm.endSession = endSession;
        vm.startCamera = startCamera;
        vm.stopCamera = stopCamera;
        vm.toggleCamera = toggleCamera;
        vm.toggleMicrophone = toggleMicrophone;
        vm.toggleRecording = toggleRecording;
        vm.formatTime = formatTime;
        vm.debugSession = debugSession;
        vm.onRoleChange = onRoleChange;
        // Posture detection methods
        vm.togglePostureDetection = togglePostureDetection;
        vm.startPostureAnalysis = startPostureAnalysis;
        vm.stopPostureAnalysis = stopPostureAnalysis;
        vm.initializePostureDetection = initializePostureDetection;
        vm.triggerManualPostureAnalysis = triggerManualPostureAnalysis;

        // Difficulty state management methods
        vm.initializeDifficultyState = initializeDifficultyState;
        vm.updateDifficultyDisplay = updateDifficultyDisplay;
        vm.onDifficultyChange = onDifficultyChange;
        vm.getDifficultyDisplayInfo = getDifficultyDisplayInfo;

        // Debug function
        function debugSession() {
            console.log('=== Interview Session Debug ===');
            console.log('Session:', vm.session);
            console.log('Questions:', vm.questions);
            console.log('Current Question:', vm.currentQuestion);
            console.log('Current Question Index:', vm.currentQuestionIndex);
            console.log('Session Time Remaining:', vm.sessionTimeRemaining);
            console.log('Question Time Remaining:', vm.questionTimeRemaining);
            console.log('===============================');
        }

        // Initialize
        activate();

        function activate() {
            // Debug authentication state
            console.log('=== Interview Controller Auth Debug ===');
            console.log('Is authenticated:', AuthService.isAuthenticated());
            console.log('Access token:', localStorage.getItem('access_token'));
            console.log('User data:', localStorage.getItem('user'));
            console.log('Current user:', AuthService.getCurrentUser());
            console.log('=====================================');

            // Route-level authentication is now handled in app.js
            // So if we reach here, we should be authenticated
            console.log('Interview controller activated, initializing...');

            // Initialize media on load
            initializeMedia();

            // Auto-start camera preview
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

        function goToDashboard() {
            stopCamera();
            $location.path('/dashboard');
        }

        function startInterview() {
            if (!validateConfig()) {
                return;
            }

            vm.loading = true;
            vm.error = '';

            // Prepare config with hierarchical role data
            var sessionConfig = angular.copy(vm.config);
            
            // Add hierarchical role data if available
            if (vm.config.selectedRole && vm.config.selectedRole.mainRole) {
                sessionConfig.hierarchical_role = {
                    main_role: vm.config.selectedRole.mainRole,
                    sub_role: vm.config.selectedRole.subRole,
                    specialization: vm.config.selectedRole.specialization,
                    tech_stack: vm.config.selectedRole.techStack
                };
            }

            console.log('Starting interview with config:', sessionConfig);

            InterviewService.startSession(sessionConfig)
                .then(function (response) {
                    console.log('Interview session started:', response);
                    vm.session = response.session;
                    vm.questions = response.questions || [];

                    // Map backend field names to frontend expected names
                    if (vm.questions.length > 0) {
                        vm.questions = vm.questions.map(function (question) {
                            return {
                                id: question.question_id || question.id,
                                question_id: question.question_id || question.id,
                                question_text: question.content || question.question_text || 'Sample question text',
                                question_type: question.question_type || 'behavioral',
                                expected_duration: question.expected_duration || 2,
                                order_index: question.order_index || 0
                            };
                        });

                        vm.currentQuestion = vm.questions[0];
                        vm.currentQuestionIndex = 0;

                        console.log('Questions mapped:', vm.questions);
                        console.log('Current question set:', vm.currentQuestion);

                        // Initialize timers
                        vm.sessionTimeRemaining = vm.session.duration * 60; // Convert to seconds
                        vm.questionTimeRemaining = vm.currentQuestion.expected_duration * 60;

                        startTimers();
                        startCamera(); // Auto-start camera for interview
                        
                        // Initialize posture detection (optional)
                        initializePostureDetection();
                        
                        // Initialize difficulty state management
                        initializeDifficultyState();
                        
                        // Auto-enable posture detection after a short delay
                        $timeout(function() {
                            if (vm.cameraActive && vm.session && vm.session.id) {
                                console.log('Auto-enabling posture detection...');
                                startPostureAnalysis();
                            }
                        }, 2000); // Wait 2 seconds for camera to be fully ready
                    } else {
                        // Create a sample question if none received
                        console.warn('No questions received, creating sample question');
                        vm.questions = [{
                            id: 1,
                            question_id: 1,
                            question_text: 'Tell me about yourself and your experience.',
                            question_type: 'behavioral',
                            expected_duration: 3,
                            order_index: 0
                        }];
                        vm.currentQuestion = vm.questions[0];
                        vm.currentQuestionIndex = 0;

                        // Initialize timers
                        vm.sessionTimeRemaining = vm.session.duration * 60;
                        vm.questionTimeRemaining = vm.currentQuestion.expected_duration * 60;

                        startTimers();
                        startCamera();
                        
                        // Initialize difficulty state management
                        initializeDifficultyState();
                    }
                })
                .catch(function (error) {
                    console.error('Interview session error:', error);
                    vm.error = error.data?.detail || 'Failed to start interview session.';
                })
                .finally(function () {
                    vm.loading = false;
                });
        }

        function startTest() {
            vm.loading = true;
            vm.error = '';

            var testConfig = {
                target_role: vm.config.target_role || 'General',
                session_type: 'technical',
                difficulty: 'advanced',
                duration: 30,
                question_count: 5
            };
            
            // Add hierarchical role data if available
            if (vm.config.selectedRole && vm.config.selectedRole.mainRole) {
                testConfig.hierarchical_role = {
                    main_role: vm.config.selectedRole.mainRole,
                    sub_role: vm.config.selectedRole.subRole,
                    specialization: vm.config.selectedRole.specialization,
                    tech_stack: vm.config.selectedRole.techStack
                };
            }

            console.log('Starting test session with config:', testConfig);

            InterviewService.startTestSession(testConfig)
                .then(function (response) {
                    console.log('Test session response:', response);
                    vm.session = response.session;
                    vm.questions = response.questions || [];

                    if (vm.questions.length > 0) {
                        // Map backend field names to frontend expected names
                        vm.questions = vm.questions.map(function (question) {
                            return {
                                id: question.question_id || question.id,
                                question_id: question.question_id || question.id,
                                question_text: question.content || question.question_text || 'Sample test question',
                                question_type: question.question_type || 'technical',
                                expected_duration: question.expected_duration || 2,
                                order_index: question.order_index || 0
                            };
                        });

                        vm.currentQuestion = vm.questions[0];
                        vm.currentQuestionIndex = 0;

                        console.log('Test questions loaded:', vm.questions);
                        console.log('Current test question:', vm.currentQuestion);
                        console.log('Total test questions:', vm.questions.length);

                        // Initialize timers
                        vm.sessionTimeRemaining = testConfig.duration * 60;
                        vm.questionTimeRemaining = vm.currentQuestion.expected_duration * 60;

                        startTimers();
                        startCamera();
                        
                        // Initialize and auto-enable posture detection for test
                        initializePostureDetection();
                        
                        // Initialize difficulty state management
                        initializeDifficultyState();
                        $timeout(function() {
                            if (vm.cameraActive && vm.session && vm.session.id) {
                                console.log('Auto-enabling posture detection for test...');
                                startPostureAnalysis();
                            }
                        }, 2000);
                    } else {
                        // Create sample test questions if none received
                        console.warn('No test questions received, creating sample questions');
                        vm.questions = [
                            {
                                id: 1,
                                question_id: 1,
                                question_text: 'Describe a challenging technical problem you solved.',
                                question_type: 'technical',
                                expected_duration: 3,
                                order_index: 0
                            },
                            {
                                id: 2,
                                question_id: 2,
                                question_text: 'How do you approach debugging complex issues?',
                                question_type: 'technical',
                                expected_duration: 3,
                                order_index: 1
                            }
                        ];
                        vm.currentQuestion = vm.questions[0];
                        vm.currentQuestionIndex = 0;

                        // Initialize timers
                        vm.sessionTimeRemaining = testConfig.duration * 60;
                        vm.questionTimeRemaining = vm.currentQuestion.expected_duration * 60;

                        startTimers();
                        startCamera();
                    }
                })
                .catch(function (error) {
                    console.error('Test session error:', error);
                    vm.error = error.data?.detail || 'Failed to start test session.';
                })
                .finally(function () {
                    vm.loading = false;
                });
        }

        function submitAnswer() {
            if (!vm.userAnswer.trim()) {
                vm.error = 'Please provide an answer before submitting.';
                return;
            }

            vm.loading = true;
            vm.error = '';

            // Calculate response time properly (ensure it's positive)
            var responseTime = Math.max(1, (vm.currentQuestion.expected_duration * 60) - (vm.questionTimeRemaining || 0));

            var answerData = {
                question_id: parseInt(vm.currentQuestion.id || vm.currentQuestion.question_id || 1),
                answer_text: vm.userAnswer.trim(),
                response_time: Math.floor(responseTime) // Ensure it's an integer
            };
            
            console.log('Interview answer data being sent:', answerData);

            console.log('Submitting answer data:', answerData);

            InterviewService.submitAnswer(vm.session.id, answerData)
                .then(function (response) {
                    // Show real-time feedback
                    if (response.feedback) {
                        vm.realTimeFeedback = response.feedback;
                    }

                    // Clear answer and move to next question
                    vm.userAnswer = '';
                    nextQuestion();
                })
                .catch(function (error) {
                    console.error('Answer submission error:', error);
                    vm.error = error.data?.detail || 'Failed to submit answer.';
                })
                .finally(function () {
                    vm.loading = false;
                });
        }

        function skipQuestion() {
            vm.userAnswer = '';
            nextQuestion();
        }

        function nextQuestion() {
            if (vm.currentQuestionIndex < vm.questions.length - 1) {
                vm.currentQuestionIndex++;
                vm.currentQuestion = vm.questions[vm.currentQuestionIndex];
                vm.questionTimeRemaining = vm.currentQuestion.expected_duration * 60;
                vm.userAnswer = '';
            } else {
                // All questions completed
                endSession();
            }
        }

        function pauseSession() {
            vm.isPaused = true;
            stopTimers();
        }

        function resumeSession() {
            vm.isPaused = false;
            startTimers();
        }

        function endSession() {
            console.log('End session called');

            try {
                stopTimers();
                stopCamera();
            } catch (error) {
                console.error('Error during cleanup:', error);
            }

            if (vm.session && vm.session.id) {
                console.log('Completing session:', vm.session.id);
                vm.loading = true;

                InterviewService.completeSession(vm.session.id)
                    .then(function (response) {
                        console.log('Session completed successfully:', response);
                        // Use $timeout to ensure safe navigation
                        $timeout(function () {
                            $location.path('/feedback/' + vm.session.id);
                        }, 0);
                    })
                    .catch(function (error) {
                        console.error('Error ending session:', error);
                        // Still redirect to feedback page even if end session fails
                        $timeout(function () {
                            $location.path('/feedback/' + vm.session.id);
                        }, 0);
                    })
                    .finally(function () {
                        vm.loading = false;
                    });
            } else {
                console.log('No session found, redirecting to dashboard');
                $timeout(function () {
                    $location.path('/dashboard');
                }, 0);
            }
        }

        function onRoleChange(role) {
            console.log('Role changed:', role);
            vm.config.selectedRole = role;
            
            // Update target_role for backward compatibility
            if (role && role.displayName) {
                vm.config.target_role = role.displayName;
            } else if (role && role.mainRole) {
                vm.config.target_role = role.mainRole;
            }
            
            // Clear any previous errors
            if (vm.error && vm.error.includes('role')) {
                vm.error = '';
            }
        }

        function validateConfig() {
            // Check if we have either hierarchical role or legacy role
            var hasRole = (vm.config.selectedRole && vm.config.selectedRole.mainRole) || 
                         vm.config.target_role;
            
            if (!hasRole || !vm.config.session_type ||
                !vm.config.difficulty || !vm.config.duration || !vm.config.question_count) {
                vm.error = 'Please fill in all required fields.';
                return false;
            }
            return true;
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
                    if (vm.userAnswer.trim()) {
                        submitAnswer();
                    } else {
                        nextQuestion();
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

        function formatTime(seconds) {
            var minutes = Math.floor(seconds / 60);
            var remainingSeconds = seconds % 60;
            return minutes + ':' + (remainingSeconds < 10 ? '0' : '') + remainingSeconds;
        }

        function initializeMedia() {
            // Check for media device support
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                console.warn('Media devices not supported');
                return;
            }
        }

        function startCamera() {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                vm.cameraError = 'Camera not supported in this browser.';
                return;
            }

            vm.cameraError = '';
            vm.loading = true;
            console.log('Starting camera...');

            navigator.mediaDevices.getUserMedia({
                video: {
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user'
                },
                audio: true
            })
                .then(function (stream) {
                    console.log('Camera stream obtained:', stream);
                    vm.mediaStream = stream;
                    vm.cameraActive = true;
                    vm.microphoneActive = true;
                    vm.cameraReady = true;
                    vm.cameraError = '';

                    // Wait a bit for DOM to be ready, then set video source
                    $timeout(function () {
                        var videoElement = document.getElementById('previewVideo') || document.getElementById('userVideo');
                        console.log('Video element found:', videoElement);

                        if (videoElement) {
                            videoElement.srcObject = stream;
                            videoElement.onloadedmetadata = function () {
                                console.log('Video metadata loaded, playing...');
                                videoElement.play().catch(function (e) {
                                    console.error('Error playing video:', e);
                                });
                                
                                // Initialize posture detection after video is ready
                                if (vm.session && vm.session.id) {
                                    console.log('Video ready, initializing posture detection...');
                                    initializePostureDetection();
                                }
                            };
                        } else {
                            console.error('Video element not found!');
                            vm.cameraError = 'Video element not found in DOM';
                        }
                    }, 100);
                })
                .catch(function (error) {
                    console.error('Error accessing media devices:', error);
                    vm.cameraActive = false;
                    vm.cameraReady = false;

                    if (error.name === 'NotAllowedError') {
                        vm.cameraError = 'Camera access denied. Please enable camera permissions.';
                    } else if (error.name === 'NotFoundError') {
                        vm.cameraError = 'No camera found. Please connect a camera.';
                    } else if (error.name === 'NotReadableError') {
                        vm.cameraError = 'Camera is already in use by another application.';
                    } else {
                        vm.cameraError = 'Unable to access camera: ' + error.message;
                    }

                    // Use $timeout to safely trigger digest cycle
                    $timeout(function () {
                        // This will automatically trigger a digest cycle safely
                    }, 0);
                })
                .finally(function () {
                    vm.loading = false;
                    // No need for manual $apply - $timeout will handle it
                });
        }

        function stopCamera() {
            try {
                if (vm.mediaStream) {
                    vm.mediaStream.getTracks().forEach(function (track) {
                        try {
                            track.stop();
                        } catch (error) {
                            console.error('Error stopping track:', error);
                        }
                    });
                    vm.mediaStream = null;
                }

                vm.cameraActive = false;
                vm.microphoneActive = false;
                vm.cameraReady = false;
                vm.cameraError = '';

                var videoElement = document.getElementById('previewVideo') || document.getElementById('userVideo');
                if (videoElement) {
                    try {
                        videoElement.srcObject = null;
                    } catch (error) {
                        console.error('Error clearing video element:', error);
                    }
                }

                // Use $timeout to safely trigger digest cycle
                $timeout(function () {
                    // This will automatically trigger a digest cycle safely
                }, 0);
            } catch (error) {
                console.error('Error in stopCamera:', error);
            }
        }

        function toggleCamera() {
            if (vm.cameraActive) {
                stopCamera();
            } else {
                startCamera();
            }
        }

        function toggleMicrophone() {
            if (vm.mediaStream) {
                var audioTracks = vm.mediaStream.getAudioTracks();
                audioTracks.forEach(function (track) {
                    track.enabled = !track.enabled;
                });
                vm.microphoneActive = !vm.microphoneActive;
            }
        }

        function toggleRecording() {
            if (vm.isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        }

        function startRecording() {
            if (!vm.mediaStream) {
                vm.error = 'No media stream available for recording.';
                return;
            }

            try {
                vm.mediaRecorder = new MediaRecorder(vm.mediaStream);
                vm.mediaRecorder.start();
                vm.isRecording = true;

                vm.mediaRecorder.ondataavailable = function (event) {
                    // Handle recorded data
                    console.log('Recording data available:', event.data);
                };

                vm.mediaRecorder.onstop = function () {
                    vm.isRecording = false;
                };
            } catch (error) {
                console.error('Error starting recording:', error);
                vm.error = 'Failed to start recording.';
            }
        }

        function stopRecording() {
            if (vm.mediaRecorder && vm.isRecording) {
                vm.mediaRecorder.stop();
                vm.isRecording = false;
            }
        }

        // Posture detection functions
        function initializePostureDetection() {
            if (!PostureService) {
                console.warn('PostureService not available');
                return;
            }
            
            console.log('Initializing posture detection service...');
            
            // Set up posture feedback callback
            PostureService.onPostureFeedback = function(feedback) {
                console.log('Received posture feedback:', feedback);
                
                // Use $timeout to safely update the scope without digest cycle conflicts
                $timeout(function() {
                    vm.postureFeedback = feedback;
                    vm.showPostureFeedback = true;
                    
                    // Auto-hide feedback after 5 seconds if status is good
                    if (feedback.posture_status === 'good') {
                        $timeout(function() {
                            vm.showPostureFeedback = false;
                        }, 5000);
                    }
                }, 0);
            };
            
            PostureService.onError = function(error) {
                console.error('Posture detection error:', error);
                
                // Use $timeout to safely update the scope without digest cycle conflicts
                $timeout(function() {
                    vm.postureFeedback = null;
                    vm.showPostureFeedback = false;
                }, 0);
            };
            
            console.log('Posture detection service initialized successfully');
        }

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
                    
                    // Update all difficulty-related UI elements
                    updateDifficultyUIElements(displayInfo);
                    
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

            // Show notification to user
            showDifficultyChangeNotification(changeData);
        }

        function getDifficultyDisplayInfo() {
            if (!vm.difficultyDisplay) {
                return {
                    current: { label: 'Loading...', color: '#6c757d' },
                    hasChanged: false
                };
            }
            return vm.difficultyDisplay;
        }

        function updateDifficultyUIElements(displayInfo) {
            try {
                // Update difficulty badges and displays in the template
                var difficultyElements = document.querySelectorAll('[data-session-id="' + vm.session.id + '"][data-difficulty-display]');
                
                difficultyElements.forEach(function(element) {
                    element.textContent = displayInfo.current.label;
                    element.style.color = displayInfo.current.color;
                    element.setAttribute('data-current-difficulty', displayInfo.current.string);
                    
                    // Update badge classes if element has badge class
                    if (element.classList.contains('badge')) {
                        // Remove old badge classes
                        element.classList.remove('bg-success', 'bg-warning', 'bg-danger', 'bg-info', 'bg-dark', 'bg-secondary');
                        // Add new badge class
                        var badgeClass = displayInfo.current.badgeClass.split(' ').pop(); // Get the bg-* class
                        element.classList.add(badgeClass);
                    }
                });

                // Trigger Angular digest cycle to update bindings
                $timeout(function() {
                    // This will trigger digest cycle
                }, 0);

            } catch (error) {
                console.error('Error updating difficulty UI elements:', error);
            }
        }

        function showDifficultyChangeNotification(changeData) {
            // Create a temporary notification element
            var notification = document.createElement('div');
            notification.className = 'alert alert-info alert-dismissible fade show position-fixed';
            notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 300px;';
            notification.innerHTML = 
                '<i class="fas fa-info-circle me-2"></i>' +
                '<strong>Difficulty Adjusted:</strong> ' + changeData.newDifficulty.charAt(0).toUpperCase() + changeData.newDifficulty.slice(1) +
                '<br><small>' + (changeData.reason || 'Adaptive adjustment') + '</small>' +
                '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';

            document.body.appendChild(notification);

            // Auto-remove after 5 seconds
            $timeout(function() {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 5000);
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
        
        function togglePostureDetection() {
            if (!vm.cameraActive) {
                vm.error = 'Please enable camera first';
                return;
            }
            
            if (vm.postureEnabled) {
                stopPostureAnalysis();
            } else {
                startPostureAnalysis();
            }
        }
        
        function startPostureAnalysis() {
            if (!PostureService || !vm.cameraActive) {
                console.warn('Cannot start posture analysis - service or camera not available');
                return;
            }
            
            var videoElement = document.getElementById('userVideo');
            if (!videoElement) {
                console.error('Video element not found for posture analysis');
                vm.error = 'Video element not found for posture analysis';
                return;
            }
            
            try {
                console.log('Starting posture analysis with video element:', videoElement);
                PostureService.startPostureAnalysis(videoElement, vm.session.id, 5000); // Analyze every 5 seconds
                vm.postureEnabled = true;
                vm.postureAnalysisActive = true;
                vm.showPostureFeedback = true;
                console.log('Posture analysis started successfully');
            } catch (error) {
                console.error('Error starting posture analysis:', error);
                vm.error = 'Failed to start posture detection: ' + error.message;
            }
        }
        
        function stopPostureAnalysis() {
            if (PostureService) {
                PostureService.stopPostureAnalysis();
                vm.postureEnabled = false;
                vm.postureAnalysisActive = false;
                vm.showPostureFeedback = false;
                vm.postureFeedback = null;
                console.log('Posture analysis stopped');
            }
        }

        function triggerManualPostureAnalysis() {
            if (!vm.cameraActive) {
                vm.error = 'Please enable camera first to trigger manual posture analysis.';
                return;
            }
            if (!PostureService) {
                vm.error = 'PostureService not available.';
                return;
            }

            var videoElement = document.getElementById('userVideo');
            if (!videoElement) {
                vm.error = 'Video element not found for manual posture analysis.';
                return;
            }

            try {
                console.log('Triggering manual posture analysis...');
                PostureService.startPostureAnalysis(videoElement, vm.session.id, 5000); // Analyze every 5 seconds
                vm.postureEnabled = true;
                vm.postureAnalysisActive = true;
                vm.showPostureFeedback = true;
                console.log('Manual posture analysis triggered successfully.');
            } catch (error) {
                console.error('Error triggering manual posture analysis:', error);
                vm.error = 'Failed to trigger manual posture analysis: ' + error.message;
            }
        }

        // Cleanup on destroy - AngularJS component lifecycle hook
        this.$onDestroy = function () {
            stopTimers();
            stopCamera();
            stopRecording();
            // Posture detection cleanup
            stopPostureAnalysis();
        };
    }
})();