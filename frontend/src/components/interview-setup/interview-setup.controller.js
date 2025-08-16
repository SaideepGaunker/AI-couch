/**
 * Interview Setup Controller - Handles interview configuration
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .controller('InterviewSetupController', InterviewSetupController);

    InterviewSetupController.$inject = ['$location', '$timeout', 'AuthService', 'InterviewService'];

    function InterviewSetupController($location, $timeout, AuthService, InterviewService) {
        var vm = this;

        // Properties
        vm.config = {
            target_role: 'Marketing Manager',
            session_type: 'mixed',
            difficulty: 'intermediate',
            duration: 30,
            question_count: 5,
            enable_video: true,
            enable_audio: true
        };
        
        vm.loading = false;
        vm.error = '';
        vm.cameraError = '';
        vm.cameraReady = false;
        vm.cameraActive = false;
        vm.mediaStream = null;

        // Methods
        vm.startInterview = startInterview;
        vm.startTest = startTest;
        vm.goToDashboard = goToDashboard;
        vm.startCamera = startCamera;
        vm.stopCamera = stopCamera;

        // Initialize
        activate();

        function activate() {
            console.log('Interview Setup activated');
            
            // Auto-start camera preview
            $timeout(function() {
                startCamera();
            }, 1000);
        }

        function startInterview() {
            if (!validateConfig()) {
                return;
            }

            vm.loading = true;
            vm.error = '';

            console.log('Starting interview with config:', vm.config);

            InterviewService.startSession(vm.config)
                .then(function(response) {
                    console.log('Interview session started:', response);
                    console.log('Questions received:', response.questions);
                    if (response.questions && response.questions.length > 0) {
                        console.log('First question:', response.questions[0]);
                        console.log('Question fields:', Object.keys(response.questions[0]));
                    }
                    // Navigate to chat interface with session data
                    $location.path('/interview-chat').search({
                        sessionId: response.session_id || response.session.id,
                        sessionData: JSON.stringify(response)
                    });
                })
                .catch(function(error) {
                    console.error('Interview session error:', error);
                    vm.error = error.data?.detail || 'Failed to start interview session.';
                })
                .finally(function() {
                    vm.loading = false;
                });
        }

        function startTest() {
            vm.loading = true;
            vm.error = '';

            var testConfig = {
                target_role: 'Product Manager',
                session_type: 'technical',
                difficulty: 'advanced',
                duration: 15,
                question_count: 3
            };

            console.log('Starting test session with config:', testConfig);

            InterviewService.startTestSession(testConfig)
                .then(function(response) {
                    console.log('Test session started:', response);
                    // Navigate to test interface
                    $location.path('/test').search({
                        sessionId: response.session_id || response.session.id,
                        sessionData: JSON.stringify(response)
                    });
                })
                .catch(function(error) {
                    console.error('Test session error:', error);
                    vm.error = error.data?.detail || 'Failed to start test session.';
                })
                .finally(function() {
                    vm.loading = false;
                });
        }

        function goToDashboard() {
            stopCamera();
            $location.path('/dashboard');
        }

        function validateConfig() {
            if (!vm.config.target_role || !vm.config.session_type || 
                !vm.config.difficulty || !vm.config.duration || !vm.config.question_count) {
                vm.error = 'Please fill in all required fields.';
                return false;
            }
            return true;
        }

        function startCamera() {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                vm.cameraError = 'Camera not supported in this browser.';
                return;
            }

            vm.cameraError = '';
            console.log('Starting camera preview...');

            navigator.mediaDevices.getUserMedia({ 
                video: { 
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                    facingMode: 'user'
                }, 
                audio: true 
            })
                .then(function(stream) {
                    console.log('Camera stream obtained:', stream);
                    vm.mediaStream = stream;
                    vm.cameraActive = true;
                    vm.cameraReady = true;
                    vm.cameraError = '';
                    
                    $timeout(function() {
                        var videoElement = document.getElementById('setupPreviewVideo');
                        if (videoElement) {
                            videoElement.srcObject = stream;
                            videoElement.onloadedmetadata = function() {
                                videoElement.play().catch(function(e) {
                                    console.error('Error playing video:', e);
                                });
                            };
                        }
                    }, 100);
                })
                .catch(function(error) {
                    console.error('Error accessing media devices:', error);
                    vm.cameraActive = false;
                    vm.cameraReady = false;
                    
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
                vm.cameraReady = false;
                vm.cameraError = '';
                
                var videoElement = document.getElementById('setupPreviewVideo');
                if (videoElement) {
                    videoElement.srcObject = null;
                }
            } catch (error) {
                console.error('Error stopping camera:', error);
            }
        }

        // Cleanup on destroy
        this.$onDestroy = function() {
            stopCamera();
        };
    }
})();