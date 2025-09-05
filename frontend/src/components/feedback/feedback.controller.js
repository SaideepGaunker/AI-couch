/**
 * Feedback Controller - Handles interview results and performance feedback
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .controller('FeedbackController', FeedbackController);

    FeedbackController.$inject = ['$location', '$routeParams', 'InterviewService', 'PostureFeedbackIntegrationService', '$timeout', 'AuthService', 'SessionDataService', 'DifficultyDisplayService', 'UnifiedDifficultyStateService'];

    function FeedbackController($location, $routeParams, InterviewService, PostureFeedbackIntegrationService, $timeout, AuthService, SessionDataService, DifficultyDisplayService, UnifiedDifficultyStateService) {
        var vm = this;

        // Properties
        vm.sessionId = $routeParams.sessionId;
        vm.feedback = null;
        vm.session = null;
        vm.learningRecommendations = null;
        vm.difficultyInfo = null;
        vm.loading = true;
        vm.error = '';

        // Session-specific difficulty state
        vm.sessionDifficultyState = null;
        vm.difficultyDisplay = null;
        vm.difficultyInheritanceInfo = null;

        // Methods
        vm.practiceAgain = practiceAgain;
        vm.viewProgress = viewProgress;
        vm.goToDashboard = goToDashboard;
        vm.getDifficultyIndex = getDifficultyIndex;
        vm.getConsistentDifficultyLabel = getConsistentDifficultyLabel;
        
        // Session-specific difficulty methods
        vm.loadSessionDifficultyState = loadSessionDifficultyState;
        vm.createPracticeWithDifficultyInheritance = createPracticeWithDifficultyInheritance;
        vm.getSessionDifficultyDisplay = getSessionDifficultyDisplay;

        // Difficulty levels for comparison (backward compatibility)
        vm.difficultyLevels = ['easy', 'medium', 'hard', 'expert'];

        // Initialize
        activate();

        function activate() {
            // Route-level authentication is handled in app.js
            console.log('Feedback controller activated for session:', vm.sessionId);

            if (!vm.sessionId) {
                vm.error = 'No session ID provided';
                vm.loading = false;
                return;
            }

            console.log('Starting feedback loading process...');
            loadFeedback();
        }

        function loadFeedback() {
            vm.loading = true;
            vm.error = '';

            // Set a timeout to prevent infinite loading
            var loadingTimeout = $timeout(function() {
                if (vm.loading) {
                    console.warn('Feedback loading timeout - falling back to basic feedback');
                    vm.loading = false;
                    loadBasicFeedback();
                }
            }, 15000); // 15 second timeout

            // First, try to load just the interview feedback quickly
            InterviewService.getSessionFeedback(vm.sessionId)
                .then(function(response) {
                    console.log('Feedback response received:', response);
                    console.log('Response keys:', Object.keys(response));
                    
                    vm.feedback = response.feedback;
                    vm.session = response.session;
                    
                    // Ensure overall_score consistency - use session's overall_score if available
                    if (response.session && response.session.overall_score !== undefined) {
                        vm.feedback.overall_score = response.session.overall_score;
                        console.log('Score consistency enforced - using session overall_score:', response.session.overall_score);
                    }
                    
                    // Additional debug logging
                    console.log('Final feedback scores:', {
                        overall: vm.feedback.overall_score,
                        content: vm.feedback.content_quality,
                        body: vm.feedback.body_language,
                        voice: vm.feedback.voice_tone
                    });
                    
                    // Extract difficulty information if available and normalize labels
                    console.log('Processing difficulty info from response:', {
                        difficulty_info: response.difficulty_info,
                        session_difficulty: response.session ? response.session.difficulty_level : null,
                        session_next_difficulty: response.session ? response.session.next_difficulty : null,
                        session_final_difficulty: response.session ? response.session.final_difficulty : null
                    });
                    
                    if (response.difficulty_info) {
                        console.log('Using response.difficulty_info:', response.difficulty_info);
                        vm.difficultyInfo = {
                            current_difficulty: DifficultyDisplayService.getDifficultyLabel(
                                DifficultyDisplayService.normalizeDifficultyInput(response.difficulty_info.current_difficulty)
                            ),
                            next_difficulty: DifficultyDisplayService.getDifficultyLabel(
                                DifficultyDisplayService.normalizeDifficultyInput(response.difficulty_info.next_difficulty)
                            ),
                            difficulty_change_reason: response.difficulty_info.difficulty_change_reason || 'Based on your performance in this session'
                        };
                    } else if (response.session && response.session.difficulty_level) {
                        // Fallback to session-level difficulty info with consistent labeling
                        var currentDifficulty = response.session.difficulty_level || 'medium';
                        var nextDifficulty;
                        
                        // Check if there's a calculated next difficulty
                        if (response.session.next_difficulty && response.session.next_difficulty !== currentDifficulty) {
                            nextDifficulty = response.session.next_difficulty;
                        } else if (response.session.final_difficulty && response.session.final_difficulty !== currentDifficulty) {
                            // Use final difficulty if it's different from current
                            nextDifficulty = response.session.final_difficulty;
                        } else {
                            // If no progression info, keep current difficulty but note it
                            nextDifficulty = currentDifficulty;
                        }
                        
                        vm.difficultyInfo = {
                            current_difficulty: DifficultyDisplayService.getDifficultyLabel(
                                DifficultyDisplayService.normalizeDifficultyInput(currentDifficulty)
                            ),
                            next_difficulty: DifficultyDisplayService.getDifficultyLabel(
                                DifficultyDisplayService.normalizeDifficultyInput(nextDifficulty)
                            ),
                            difficulty_change_reason: nextDifficulty !== currentDifficulty ? 
                                'Difficulty adjusted based on your performance in this session' :
                                'Difficulty remained consistent throughout this session'
                        };
                    } else {
                        // Default difficulty info if none available
                        vm.difficultyInfo = {
                            current_difficulty: 'Medium',
                            next_difficulty: 'Medium',
                            difficulty_change_reason: 'Complete more sessions for difficulty adjustment'
                        };
                    }
                    
                    // Extract learning recommendations if available
                    if (response.learning_recommendations) {
                        console.log('Learning recommendations found:', response.learning_recommendations);
                        console.log('Learning recommendations keys:', Object.keys(response.learning_recommendations));
                        vm.learningRecommendations = response.learning_recommendations;
                    } else {
                        console.log('No learning recommendations in response');
                        console.log('Full response structure:', JSON.stringify(response, null, 2));
                    }
                    
                    // Now try to enhance with body language data (non-blocking)
                    PostureFeedbackIntegrationService.getBodyLanguageScore(vm.sessionId)
                        .then(function(bodyLanguageResult) {
                            // Use body language score directly from PerformanceMetrics
                            if (bodyLanguageResult && bodyLanguageResult.success && bodyLanguageResult.body_language_score > 0) {
                                vm.feedback.body_language = Math.round(bodyLanguageResult.body_language_score);
                            }
                        })
                        .catch(function(bodyLanguageError) {
                            console.warn('Body language data enhancement failed, using basic feedback:', bodyLanguageError);
                        });
                    
                    // Load session-specific difficulty state
                    loadSessionDifficultyState();
                    
                    $timeout.cancel(loadingTimeout);
                    vm.loading = false;
                })
                .catch(function(error) {
                    $timeout.cancel(loadingTimeout);
                    console.error('Error loading basic feedback:', error);
                    vm.error = error.data?.detail || 'Failed to load feedback';
                    loadBasicFeedback();
                });
        }

        function loadBasicFeedback() {
            vm.loading = false;
            // Create mock feedback for demo purposes
            vm.feedback = {
                overall_score: 0,
                content_quality: 0,
                body_language: 0,
                voice_tone: 0,
                areas_for_improvement: ['Complete more practice sessions for detailed feedback'],
                recommendations: ['Keep practicing to improve your interview skills!'],
                detailed_analysis: 'Complete more interview sessions to receive AI-powered detailed analysis of your performance.',
                question_specific_feedback: []
            };
            vm.session = {
                id: vm.sessionId,
                target_role: 'Unknown',
                session_type: 'mixed'
            };
            vm.difficultyInfo = {
                current_difficulty: DifficultyDisplayService.getDifficultyLabel(2), // Medium
                next_difficulty: DifficultyDisplayService.getDifficultyLabel(2), // Medium
                difficulty_change_reason: 'Complete more sessions for difficulty adjustment'
            };
        }

        function practiceAgain() {
            console.log('Practice Again clicked for session:', vm.sessionId);
            
            if (!vm.sessionId) {
                console.error('No session ID available for practice again');
                vm.error = 'No session ID available';
                return;
            }

            // Check authentication
            if (!AuthService.isAuthenticated()) {
                console.error('User not authenticated');
                vm.error = 'Please log in to continue';
                return;
            }
            
            console.log('Creating practice session with enhanced difficulty inheritance');
            
            // Use the enhanced practice session creation method
            createPracticeWithDifficultyInheritance();
        }

        function viewProgress() {
            $location.path('/progress');
        }

        function goToDashboard() {
            $location.path('/dashboard');
        }

        function getDifficultyIndex(difficulty) {
            // Convert to internal level and then to index for backward compatibility
            var internalLevel = DifficultyDisplayService.normalizeDifficultyInput(difficulty);
            var stringLevel = DifficultyDisplayService.getStringLevel(internalLevel);
            return vm.difficultyLevels.indexOf(stringLevel);
        }

        function getConsistentDifficultyLabel(difficulty) {
            return DifficultyDisplayService.getDifficultyLabel(
                DifficultyDisplayService.normalizeDifficultyInput(difficulty)
            );
        }

        // ==================== Session-Specific Difficulty Methods ====================

        function loadSessionDifficultyState() {
            if (!vm.sessionId) {
                return;
            }

            console.log('Loading session-specific difficulty state for session:', vm.sessionId);

            UnifiedDifficultyStateService.getSessionDifficultyState(vm.sessionId)
                .then(function(difficultyState) {
                    vm.sessionDifficultyState = difficultyState;
                    
                    // Update difficulty display with session-specific information
                    return UnifiedDifficultyStateService.getDifficultyForDisplay(vm.sessionId);
                })
                .then(function(displayInfo) {
                    vm.difficultyDisplay = displayInfo;
                    
                    // Update the legacy difficultyInfo with session-specific data
                    updateDifficultyInfoFromSessionState();
                    
                    console.log('Session difficulty state loaded:', {
                        state: vm.sessionDifficultyState,
                        display: vm.difficultyDisplay
                    });
                })
                .catch(function(error) {
                    console.error('Error loading session difficulty state:', error);
                    // Keep existing difficultyInfo as fallback
                });
        }

        function createPracticeWithDifficultyInheritance() {
            // Set loading state
            vm.loading = true;
            vm.error = '';

            console.log('Creating practice session with difficulty inheritance from session:', vm.sessionId);

            // Use UnifiedDifficultyStateService for enhanced practice session creation
            UnifiedDifficultyStateService.createPracticeSessionWithDifficulty(vm.sessionId, {
                showLoading: true,
                showSuccess: true
            })
            .then(function(response) {
                console.log('Practice session created with difficulty inheritance:', response);
                
                // Store inheritance information for user transparency
                vm.difficultyInheritanceInfo = response.difficulty_validation;
                
                // Show inheritance information to user
                if (response.difficulty_validation && response.difficulty_validation.isValid) {
                    var parentInfo = response.difficulty_validation.parentDifficultyInfo;
                    var inheritedDifficulty = response.difficulty_validation.inheritedDifficulty;
                    
                    console.log('Difficulty inheritance successful:', {
                        parent: parentInfo,
                        inherited: inheritedDifficulty,
                        wasAdjusted: parentInfo.wasAdjusted
                    });
                    
                    // Navigate to the new practice session
                    $timeout(function() {
                        $location.path('/interview-chat/' + response.session.id);
                    }, 1000);
                } else {
                    // Show validation errors if any
                    var errors = response.difficulty_validation ? response.difficulty_validation.errors : ['Unknown validation error'];
                    console.warn('Difficulty inheritance validation failed:', errors);
                    vm.error = 'Practice session created but difficulty inheritance may not be accurate: ' + errors.join(', ');
                    
                    // Still navigate to practice session
                    $timeout(function() {
                        $location.path('/interview-chat/' + response.session.id);
                    }, 2000);
                }
                
                vm.loading = false;
            })
            .catch(function(error) {
                console.error('Error creating practice session with difficulty inheritance:', error);
                
                // Fallback to UnifiedDifficultyStateService
                console.log('Using UnifiedDifficultyStateService for practice session creation');
                
                return UnifiedDifficultyStateService.createPracticeSessionWithDifficulty(vm.sessionId, {
                    showLoading: true,
                    showSuccess: true
                }).then(function(response) {
                    console.log('Practice session created successfully:', response);
                    $location.path('/interview-chat/' + response.session.id);
                }).catch(function(error) {
                    console.error('Failed to create practice session:', error);
                    vm.error = 'Failed to create practice session. Please try again.';
                    vm.loading = false;
                });
            })
            .catch(function(fallbackError) {
                console.error('Fallback practice session creation also failed:', fallbackError);
                vm.error = fallbackError.data?.detail || fallbackError.message || 'Failed to create practice session';
                vm.loading = false;
            });
        }

        function getSessionDifficultyDisplay() {
            if (!vm.difficultyDisplay) {
                return {
                    current: { label: 'Loading...', color: '#6c757d' },
                    initial: { label: 'Loading...', color: '#6c757d' },
                    hasChanged: false,
                    isCompleted: false
                };
            }
            return vm.difficultyDisplay;
        }

        function updateDifficultyInfoFromSessionState() {
            if (!vm.sessionDifficultyState || !vm.difficultyDisplay) {
                return;
            }

            // Update the legacy difficultyInfo object with session-specific data
            var currentDifficulty = vm.difficultyDisplay.current.label;
            var finalDifficulty = vm.difficultyDisplay.final ? vm.difficultyDisplay.final.label : currentDifficulty;
            
            // Determine next difficulty for practice session
            var nextDifficulty;
            if (vm.difficultyDisplay.isCompleted && vm.difficultyDisplay.final) {
                // Session is completed and has a final difficulty - use that for next session
                nextDifficulty = finalDifficulty;
            } else if (vm.difficultyDisplay.hasChanged && vm.difficultyDisplay.final) {
                // Difficulty changed during session - use the final adjusted difficulty
                nextDifficulty = finalDifficulty;
            } else if (vm.sessionDifficultyState && vm.sessionDifficultyState.next_difficulty) {
                // Use the calculated next difficulty from the session state
                nextDifficulty = DifficultyDisplayService.getDifficultyLabel(
                    DifficultyDisplayService.normalizeDifficultyInput(vm.sessionDifficultyState.next_difficulty)
                );
            } else {
                // Fallback: keep current difficulty if no progression info available
                nextDifficulty = currentDifficulty;
            }
            
            vm.difficultyInfo = {
                current_difficulty: currentDifficulty,
                next_difficulty: nextDifficulty,
                difficulty_change_reason: vm.difficultyDisplay.hasChanged ? 
                    'Difficulty was adjusted during this session based on your performance' :
                    'Difficulty remained consistent throughout this session'
            };

            console.log('Updated difficulty info from session state:', vm.difficultyInfo);
        }
    }
})();