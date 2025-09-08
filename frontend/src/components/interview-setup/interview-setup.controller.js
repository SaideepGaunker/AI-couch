/**
 * Interview Setup Controller - Handles interview configuration
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .controller('InterviewSetupController', InterviewSetupController);

    InterviewSetupController.$inject = ['$location', '$timeout', 'AuthService', 'InterviewService', 'DifficultyDisplayService', 'SessionSettingsService'];

    function InterviewSetupController($location, $timeout, AuthService, InterviewService, DifficultyDisplayService, SessionSettingsService) {
        var vm = this;

        // Properties
        vm.config = {
            target_role: null, // Will be set based on selectedRole
            selectedRole: null, // New hierarchical role data
            session_type: 'mixed',
            difficulty: 'medium', // Fixed to match backend levels (easy, medium, hard)
            duration: 30,
            question_count: 5,
            enable_video: true,
            enable_audio: true
        };
        
        // UI state
        vm.showLegacyRoleSelector = false;
        vm.showQuickTestInfo = true; // Show quick test info by default
        vm.showQuickTestCustomization = false;
        vm.quickTestSettings = {
            question_count: 3,
            question_count_source: 'default',
            distribution_summary: null
        };
        
        // Initialize custom quick test settings
        vm.customQuickTestSettings = {
            question_count: 3,
            difficulty: 'medium',
            duration: 15
        };
        vm.customOverrideSettings = null;
        
        vm.loading = false;
        vm.error = '';
        vm.cameraError = '';
        vm.cameraReady = false;
        vm.cameraActive = false;
        vm.mediaStream = null;
        
        // Difficulty information
        vm.currentDifficulty = null;
        vm.recommendedDifficulty = null;
        vm.difficultyReason = null;

        // Methods
        vm.startInterview = startInterview;
        vm.startTest = startTest;
        vm.goToDashboard = goToDashboard;
        vm.startCamera = startCamera;
        vm.stopCamera = stopCamera;
        vm.onRoleChange = onRoleChange;
        vm.customizeQuickTest = customizeQuickTest;
        vm.loadQuickTestSettings = loadQuickTestSettings;
        vm.applyMainFormToQuickTest = applyMainFormToQuickTest;
        vm.applyCustomSettings = applyCustomSettings;
        vm.loadPracticeSessionSettings = loadPracticeSessionSettings;

        // Initialize
        activate();

        function activate() {
            console.log('Interview Setup activated');
            
            // Initialize with safe defaults to prevent template errors
            vm.config = vm.config || {
                target_role: null,
                selectedRole: null,
                session_type: 'mixed',
                difficulty: 'medium',
                duration: 30,
                question_count: 5,
                enable_video: true,
                enable_audio: true
            };
            
            // Check if this is a practice session
            var searchParams = $location.search();
            if (searchParams.practiceSession && searchParams.mode === 'practice_again') {
                vm.isPracticeSession = true;
                vm.originalSessionId = parseInt(searchParams.practiceSession);
                console.log('Practice session mode detected for session:', vm.originalSessionId);
                loadPracticeSessionSettings();
            } else {
                vm.isPracticeSession = false;
                loadDifficultyRecommendation();
            }
            
            loadQuickTestSettings();
            
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

            // Check if this is a practice session
            if (vm.isPracticeSession && vm.originalSessionId) {
                console.log('Starting practice session for original session:', vm.originalSessionId);
                
                InterviewService.practiceAgain(vm.originalSessionId)
                    .then(function(response) {
                        console.log('Practice session created:', response);
                        // Navigate to chat interface with session data
                        $location.path('/interview-chat').search({
                            sessionId: response.session_id || response.session.id,
                            sessionData: JSON.stringify(response)
                        });
                    })
                    .catch(function(error) {
                        console.error('Practice session error:', error);
                        vm.error = error.data?.detail || 'Failed to start practice session.';
                    })
                    .finally(function() {
                        vm.loading = false;
                    });
            } else {
                // Regular new session
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

                console.log('Starting new interview with config:', sessionConfig);

                InterviewService.startSession(sessionConfig)
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
        }

        function startTest() {
            vm.loading = true;
            vm.error = '';

            // Validate role selection before starting quick test
            var hasRole = (vm.config.selectedRole && vm.config.selectedRole.mainRole) || 
                         vm.config.target_role;
            
            if (!hasRole) {
                vm.error = 'Please select a target role before starting the quick test.';
                vm.loading = false;
                return;
            }

            // Prepare override settings for quick test
            var overrideSettings = {};
            
            // Apply custom settings if user has customized
            if (vm.customOverrideSettings) {
                // Make a deep copy to avoid reference issues
                overrideSettings = angular.copy(vm.customOverrideSettings);
                
                // Ensure question_count is an integer
                if (overrideSettings.question_count) {
                    overrideSettings.question_count = parseInt(overrideSettings.question_count);
                }
                
                // Add save_as_preference flag to persist user's custom settings
                overrideSettings.save_as_preference = true;
                
                console.log('Using custom override settings with save_as_preference:', overrideSettings);
            } else if (vm.quickTestSettings && vm.quickTestSettings.question_count) {
                // Always include question count from quickTestSettings if not already overridden
                overrideSettings.question_count = parseInt(vm.quickTestSettings.question_count);
                
                // Include difficulty from quickTestSettings if available
                if (vm.quickTestSettings.difficulty) {
                    overrideSettings.difficulty = vm.quickTestSettings.difficulty;
                } else if (vm.config.difficulty) {
                    // Fall back to main config difficulty
                    overrideSettings.difficulty = vm.config.difficulty;
                }
                
                console.log('Using quick test settings:', overrideSettings);
            }
            
            // Only override if user has explicitly changed from defaults
            if (vm.config.target_role && vm.config.target_role !== 'General') {
                overrideSettings.target_role = vm.config.target_role;
            }
            
            // Add hierarchical role data if available
            if (vm.config.selectedRole && vm.config.selectedRole.mainRole) {
                overrideSettings.hierarchical_role = {
                    main_role: vm.config.selectedRole.mainRole,
                    sub_role: vm.config.selectedRole.subRole,
                    specialization: vm.config.selectedRole.specialization,
                    tech_stack: vm.config.selectedRole.techStack
                };
                overrideSettings.target_role = vm.config.selectedRole.displayName || vm.config.selectedRole.mainRole;
            }

            console.log('Starting quick test with override settings:', overrideSettings);

            // Use SessionSettingsService for proper inheritance
            SessionSettingsService.createQuickTestSession(Object.keys(overrideSettings).length > 0 ? overrideSettings : null)
                .then(function(response) {
                    console.log('Quick test session created:', response);
                    
                    // Show inheritance information to user
                    if (response.settings_info) {
                        var settingsInfo = response.settings_info;
                        var message = '';
                        
                        if (settingsInfo.question_count_source === 'inherited') {
                            message = 'Using your preferred question count (' + settingsInfo.question_count + ') from previous sessions.';
                        } else if (settingsInfo.question_count_source === 'user_override') {
                            message = 'Using your custom settings for this quick test.';
                        } else {
                            message = 'Using default settings for your first quick test (' + settingsInfo.question_count + ' questions).';
                        }
                        
                        // Show distribution information
                        if (response.question_distribution && response.question_distribution.summary) {
                            message += ' Question types: ' + response.question_distribution.summary;
                        }
                        
                        console.log('Quick test settings:', message);
                        // Could show this in a toast notification
                    }
                    
                    // Navigate to test interface
                    $location.path('/test').search({
                        sessionId: response.session_id || response.session.id,
                        sessionData: JSON.stringify(response)
                    });
                })
                .catch(function(error) {
                    console.error('Quick test session error:', error);
                    vm.error = error.data?.detail || 'Failed to start quick test session.';
                })
                .finally(function() {
                    vm.loading = false;
                });
        }

        function goToDashboard() {
            stopCamera();
            $location.path('/dashboard');
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

        function loadDifficultyRecommendation() {
            // Load user's difficulty statistics to provide recommendations
            InterviewService.getDifficultyStatistics()
                .then(function(response) {
                    console.log('Difficulty statistics loaded:', response);
                    
                    if (response && response.data) {
                        // Use consistent difficulty labels
                        vm.currentDifficulty = DifficultyDisplayService.getDifficultyLabel(
                            DifficultyDisplayService.normalizeDifficultyInput(response.data.current_difficulty)
                        );
                        vm.recommendedDifficulty = DifficultyDisplayService.getDifficultyLabel(
                            DifficultyDisplayService.normalizeDifficultyInput(response.data.next_difficulty)
                        );
                        
                        // Set the recommended difficulty as default (convert to string level for form)
                        if (response.data.next_difficulty) {
                            var recommendedStringLevel = DifficultyDisplayService.getStringLevel(
                                DifficultyDisplayService.normalizeDifficultyInput(response.data.next_difficulty)
                            );
                            vm.config.difficulty = recommendedStringLevel;
                            console.log('Set recommended difficulty:', recommendedStringLevel);
                        }
                        
                        // Generate reason for recommendation using consistent labels
                        if (vm.currentDifficulty && vm.recommendedDifficulty) {
                            if (vm.currentDifficulty === vm.recommendedDifficulty) {
                                vm.difficultyReason = 'Based on your consistent performance';
                            } else {
                                var currentLevel = DifficultyDisplayService.normalizeDifficultyInput(response.data.current_difficulty);
                                var nextLevel = DifficultyDisplayService.normalizeDifficultyInput(response.data.next_difficulty);
                                
                                if (nextLevel > currentLevel) {
                                    vm.difficultyReason = 'You\'re ready for a challenge!';
                                } else if (nextLevel < currentLevel) {
                                    vm.difficultyReason = 'Let\'s build your confidence';
                                }
                            }
                        }
                    }
                })
                .catch(function(error) {
                    console.log('Could not load difficulty statistics:', error);
                    // Don't show error to user, just use defaults
                });
        }

        function loadQuickTestSettings() {
            // Load user's last main session to show what settings will be inherited
            SessionSettingsService.getUserLastMainSession()
                .then(function(lastSession) {
                    if (lastSession) {
                        // Estimate question count from last session
                        var questionCount = lastSession.question_count || 
                                          (lastSession.duration <= 15 ? 3 : 
                                           lastSession.duration <= 30 ? 5 : 
                                           lastSession.duration <= 45 ? 8 : 10);
                        
                        vm.quickTestSettings = {
                            question_count: questionCount,
                            question_count_source: 'inherited',
                            distribution_summary: 'Theory: 20%, Coding: 40%, Aptitude: 40%',
                            inherited_from_session_id: lastSession.id,
                            last_session_role: lastSession.target_role,
                            last_session_difficulty: lastSession.difficulty_level,
                            duration: lastSession.duration || 15
                        };
                        
                        // Initialize custom settings with inherited values
                        vm.customQuickTestSettings = {
                            question_count: questionCount,
                            difficulty: lastSession.difficulty_level || 'medium',
                            duration: lastSession.duration || 15
                        };
                        
                        console.log('Quick test will inherit settings from session:', lastSession.id);
                    } else {
                        // No previous sessions - use defaults
                        vm.quickTestSettings = {
                            question_count: 3,
                            question_count_source: 'default',
                            distribution_summary: 'Theory: 1, Coding: 1, Aptitude: 1',
                            duration: 15
                        };
                        
                        // Initialize custom settings with defaults
                        vm.customQuickTestSettings = {
                            question_count: 3,
                            difficulty: 'medium',
                            duration: 15
                        };
                        
                        console.log('No previous sessions found, using defaults');
                    }
                })
                .catch(function(error) {
                    console.log('Could not load last session for quick test settings:', error);
                    // Use defaults
                    vm.quickTestSettings = {
                        question_count: 3,
                        question_count_source: 'default',
                        distribution_summary: 'Theory: 1, Coding: 1, Aptitude: 1',
                        duration: 15
                    };
                    
                    // Initialize custom settings with defaults
                    vm.customQuickTestSettings = {
                        question_count: 3,
                        difficulty: 'medium',
                        duration: 15
                    };
                });
        }

        function customizeQuickTest() {
            // Show modal or expand form to allow customization
            // For now, just toggle to show that customization is available
            vm.showQuickTestCustomization = !vm.showQuickTestCustomization;
            
            if (vm.showQuickTestCustomization) {
                // Initialize customization form with current settings
                // First check if we have custom override settings
                var difficultyValue = 'medium';
                
                if (vm.customOverrideSettings && vm.customOverrideSettings.difficulty) {
                    difficultyValue = vm.customOverrideSettings.difficulty;
                } else if (vm.quickTestSettings && vm.quickTestSettings.difficulty) {
                    difficultyValue = vm.quickTestSettings.difficulty;
                } else if (vm.config && vm.config.difficulty) {
                    difficultyValue = vm.config.difficulty;
                }
                
                // Get duration value from various sources
                var durationValue = 15; // Default
                if (vm.customOverrideSettings && vm.customOverrideSettings.duration) {
                    durationValue = vm.customOverrideSettings.duration;
                } else if (vm.quickTestSettings && vm.quickTestSettings.duration) {
                    durationValue = vm.quickTestSettings.duration;
                } else if (vm.config && vm.config.duration) {
                    durationValue = vm.config.duration;
                }
                
                // Get question count value
                var questionCountValue = 3; // Default
                if (vm.customOverrideSettings && vm.customOverrideSettings.question_count) {
                    questionCountValue = vm.customOverrideSettings.question_count;
                } else if (vm.quickTestSettings && vm.quickTestSettings.question_count) {
                    questionCountValue = vm.quickTestSettings.question_count;
                }
                
                // Update the custom settings object
                vm.customQuickTestSettings.question_count = questionCountValue;
                vm.customQuickTestSettings.difficulty = difficultyValue;
                vm.customQuickTestSettings.duration = durationValue;
                
                console.log('Initialized quick test customization with:', vm.customQuickTestSettings);
            }
        }

        function applyCustomSettings() {
            // Update quick test settings with custom values
            vm.quickTestSettings.question_count = parseInt(vm.customQuickTestSettings.question_count);
            vm.quickTestSettings.question_count_source = 'user_override';
            vm.quickTestSettings.difficulty = vm.customQuickTestSettings.difficulty;
            vm.quickTestSettings.duration = parseInt(vm.customQuickTestSettings.duration);
            
            // Update distribution summary based on new question count
            var count = parseInt(vm.customQuickTestSettings.question_count);
            if (count === 3) {
                vm.quickTestSettings.distribution_summary = 'Theory: 1, Coding: 1, Aptitude: 1';
            } else if (count === 5) {
                vm.quickTestSettings.distribution_summary = 'Theory: 1, Coding: 2, Aptitude: 2';
            } else if (count === 7) {
                vm.quickTestSettings.distribution_summary = 'Theory: 1, Coding: 3, Aptitude: 3';
            } else if (count === 10) {
                vm.quickTestSettings.distribution_summary = 'Theory: 2, Coding: 4, Aptitude: 4';
            }
            
            // Store custom settings for use in startTest
            // Make sure we're storing the values as the correct types
            vm.customOverrideSettings = {
                question_count: parseInt(vm.customQuickTestSettings.question_count),
                difficulty: vm.customQuickTestSettings.difficulty,
                duration: parseInt(vm.customQuickTestSettings.duration),
                save_as_preference: true // Always save custom settings as preference
            };
            
            // Also update the main config to keep UI consistent
            vm.config.question_count = parseInt(vm.customQuickTestSettings.question_count);
            vm.config.difficulty = vm.customQuickTestSettings.difficulty;
            vm.config.duration = parseInt(vm.customQuickTestSettings.duration);
            
            vm.showQuickTestCustomization = false;
            console.log('Applied custom quick test settings with save_as_preference:', vm.customOverrideSettings);
        }

        function applyMainFormToQuickTest() {
            // Apply current main form settings to quick test
            vm.customOverrideSettings = {
                question_count: parseInt(vm.config.question_count),
                difficulty: vm.config.difficulty,
                duration: parseInt(vm.config.duration),
                save_as_preference: false // Don't save as preference, just use for this test
            };
            
            // Update quick test settings display
            vm.quickTestSettings.question_count = parseInt(vm.config.question_count);
            vm.quickTestSettings.question_count_source = 'user_override';
            vm.quickTestSettings.difficulty = vm.config.difficulty;
            vm.quickTestSettings.duration = parseInt(vm.config.duration);
            
            // Update distribution summary
            var count = parseInt(vm.config.question_count);
            if (count === 3) {
                vm.quickTestSettings.distribution_summary = 'Theory: 1, Coding: 1, Aptitude: 1';
            } else if (count === 5) {
                vm.quickTestSettings.distribution_summary = 'Theory: 1, Coding: 2, Aptitude: 2';
            } else if (count === 7) {
                vm.quickTestSettings.distribution_summary = 'Theory: 1, Coding: 3, Aptitude: 3';
            } else if (count === 10) {
                vm.quickTestSettings.distribution_summary = 'Theory: 2, Coding: 4, Aptitude: 4';
            }
            
            console.log('Applied main form settings to quick test:', vm.customOverrideSettings);
        }

        function loadPracticeSessionSettings() {
            console.log('Loading practice session settings for session:', vm.originalSessionId);
            
            // Load the original session details and difficulty recommendation
            InterviewService.getSession(vm.originalSessionId)
                .then(function(response) {
                    if (response && response.data) {
                        var originalSession = response.data;
                        console.log('Original session loaded:', originalSession);
                        
                        // Pre-fill form with original session settings
                        vm.config.target_role = originalSession.target_role;
                        vm.config.session_type = originalSession.session_type;
                        vm.config.duration = originalSession.duration;
                        vm.config.question_count = originalSession.question_count;
                        
                        // Show original difficulty
                        vm.originalDifficulty = DifficultyDisplayService.getDifficultyLabel(
                            DifficultyDisplayService.normalizeDifficultyInput(originalSession.difficulty_level)
                        );
                        
                        // Load adaptive difficulty recommendation
                        return InterviewService.getDifficultyStatistics();
                    }
                })
                .then(function(statsResponse) {
                    if (statsResponse && statsResponse.data) {
                        console.log('Difficulty statistics loaded for practice session:', statsResponse);
                        
                        // Set recommended difficulty as default
                        vm.recommendedDifficulty = DifficultyDisplayService.getDifficultyLabel(
                            DifficultyDisplayService.normalizeDifficultyInput(statsResponse.data.next_difficulty)
                        );
                        
                        // Set the recommended difficulty as default (convert to string level for form)
                        if (statsResponse.data.next_difficulty) {
                            var recommendedStringLevel = DifficultyDisplayService.getStringLevel(
                                DifficultyDisplayService.normalizeDifficultyInput(statsResponse.data.next_difficulty)
                            );
                            vm.config.difficulty = recommendedStringLevel;
                            console.log('Set recommended difficulty for practice session:', recommendedStringLevel);
                        }
                        
                        // Generate reason for recommendation
                        if (vm.originalDifficulty && vm.recommendedDifficulty) {
                            if (vm.originalDifficulty === vm.recommendedDifficulty) {
                                vm.difficultyReason = 'Based on your performance, we recommend continuing with the same difficulty';
                            } else {
                                var originalLevel = DifficultyDisplayService.normalizeDifficultyInput(vm.originalDifficulty);
                                var nextLevel = DifficultyDisplayService.normalizeDifficultyInput(statsResponse.data.next_difficulty);
                                
                                if (nextLevel > originalLevel) {
                                    vm.difficultyReason = 'Based on your excellent performance, we recommend increasing the difficulty!';
                                } else if (nextLevel < originalLevel) {
                                    vm.difficultyReason = 'Based on your performance, we recommend an easier difficulty to build confidence';
                                }
                            }
                        }
                        
                        vm.showPracticeInfo = true;
                    }
                })
                .catch(function(error) {
                    console.error('Error loading practice session settings:', error);
                    vm.error = 'Failed to load practice session settings. Please try again.';
                });
        }

        // Cleanup on destroy
        this.$onDestroy = function() {
            stopCamera();
        };
    }
})();