/**
 * Unified Practice Controller - Consistent practice session creation regardless of navigation path
 * 
 * This controller provides:
 * - Unified practice session creation logic for both feedback and dashboard
 * - Consistent difficulty inheritance using UnifiedDifficultyStateService
 * - Comprehensive error handling and user feedback
 * - Same behavior whether user comes from feedback page or dashboard
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .controller('UnifiedPracticeController', UnifiedPracticeController);

    UnifiedPracticeController.$inject = [
        '$location', 
        '$rootScope', 
        '$q', 
        '$log', 
        'UnifiedDifficultyStateService', 
        'SessionDataService', 
        'AuthService',
        'DifficultyDisplayService'
    ];

    function UnifiedPracticeController(
        $location, 
        $rootScope, 
        $q, 
        $log, 
        UnifiedDifficultyStateService, 
        SessionDataService, 
        AuthService,
        DifficultyDisplayService
    ) {
        var controller = this;

        // Public API
        controller.createPracticeSession = createPracticeSession;
        controller.createPracticeSessionWithConfirmation = createPracticeSessionWithConfirmation;
        controller.validatePracticeSessionCreation = validatePracticeSessionCreation;
        controller.handlePracticeSessionError = handlePracticeSessionError;
        controller.getInheritedSettingsPreview = getInheritedSettingsPreview;

        // Internal state
        var isCreatingSession = false;
        var lastCreatedSessionId = null;

        // Initialize
        init();

        return controller;

        // ==================== Initialization ====================

        function init() {
            $log.info('UnifiedPracticeController: Controller initialized');

            // Listen for practice session requests from other components
            $rootScope.$on('practice:session:request', function(event, data) {
                if (data && data.parentSessionId) {
                    createPracticeSession(data.parentSessionId, data.options);
                }
            });

            // Listen for practice session creation errors
            $rootScope.$on('practice:session:error', function(event, data) {
                handlePracticeSessionError(data.error, data.context);
            });
        }

        // ==================== Public Methods ====================

        /**
         * Create practice session with unified logic
         * @param {number} parentSessionId - The parent session ID
         * @param {Object} options - Creation options
         * @returns {Promise} Promise resolving to practice session data
         */
        function createPracticeSession(parentSessionId, options) {
            options = options || {};

            if (!parentSessionId) {
                var error = new Error('Parent session ID is required for practice session creation');
                return handlePracticeSessionError(error, { source: 'createPracticeSession' });
            }

            // Check authentication
            if (!AuthService.isAuthenticated()) {
                var authError = new Error('Authentication required to create practice session');
                return handlePracticeSessionError(authError, { 
                    source: 'createPracticeSession',
                    parentSessionId: parentSessionId,
                    recoverySuggestion: 'Please log in and try again'
                });
            }

            // Prevent duplicate session creation
            if (isCreatingSession) {
                $log.warn('UnifiedPracticeController: Practice session creation already in progress');
                return $q.reject(new Error('Practice session creation already in progress'));
            }

            // Validate parent session
            return validatePracticeSessionCreation(parentSessionId)
                .then(function(validationResult) {
                    if (!validationResult.isValid) {
                        throw new Error('Parent session validation failed: ' + validationResult.errors.join(', '));
                    }

                    return executeCreatePracticeSession(parentSessionId, options, validationResult);
                })
                .catch(function(error) {
                    return handlePracticeSessionError(error, {
                        source: 'createPracticeSession',
                        parentSessionId: parentSessionId,
                        options: options
                    });
                });
        }

        /**
         * Create practice session with user confirmation dialog
         * @param {number} parentSessionId - The parent session ID
         * @param {Object} sessionInfo - Session information for confirmation
         * @param {Object} options - Creation options
         * @returns {Promise} Promise resolving to practice session data
         */
        function createPracticeSessionWithConfirmation(parentSessionId, sessionInfo, options) {
            options = options || {};

            if (!parentSessionId || !sessionInfo) {
                return $q.reject(new Error('Parent session ID and session info are required'));
            }

            return getInheritedSettingsPreview(parentSessionId)
                .then(function(preview) {
                    return showConfirmationDialog(sessionInfo, preview, options);
                })
                .then(function(confirmed) {
                    if (confirmed) {
                        return createPracticeSession(parentSessionId, options);
                    } else {
                        return $q.reject(new Error('Practice session creation cancelled by user'));
                    }
                })
                .catch(function(error) {
                    return handlePracticeSessionError(error, {
                        source: 'createPracticeSessionWithConfirmation',
                        parentSessionId: parentSessionId,
                        sessionInfo: sessionInfo
                    });
                });
        }

        /**
         * Validate that practice session can be created from parent session
         * @param {number} parentSessionId - The parent session ID
         * @returns {Promise} Promise resolving to validation result
         */
        function validatePracticeSessionCreation(parentSessionId) {
            if (!parentSessionId) {
                return $q.resolve({
                    isValid: false,
                    errors: ['Parent session ID is required'],
                    warnings: []
                });
            }

            $log.info('UnifiedPracticeController: Validating practice session creation for parent', parentSessionId);

            // Get difficulty state to validate parent session exists and has proper state
            return UnifiedDifficultyStateService.getSessionDifficultyState(parentSessionId, {
                suppressErrors: true
            })
            .then(function(difficultyState) {
                var errors = [];
                var warnings = [];

                // Validate difficulty state exists
                if (!difficultyState) {
                    errors.push('Parent session difficulty state not found');
                } else {
                    // Validate difficulty state completeness
                    if (!difficultyState.initial_difficulty) {
                        warnings.push('Parent session missing initial difficulty information');
                    }

                    if (!difficultyState.current_difficulty) {
                        errors.push('Parent session missing current difficulty information');
                    }

                    // Check if session is completed (has final difficulty)
                    if (!difficultyState.final_difficulty && !difficultyState.current_difficulty) {
                        warnings.push('Parent session may not be completed - using current difficulty');
                    }
                }

                return {
                    isValid: errors.length === 0,
                    errors: errors,
                    warnings: warnings,
                    difficultyState: difficultyState
                };
            })
            .catch(function(error) {
                $log.error('UnifiedPracticeController: Error validating parent session:', error);
                
                return {
                    isValid: false,
                    errors: ['Failed to validate parent session: ' + error.message],
                    warnings: [],
                    difficultyState: null
                };
            });
        }

        /**
         * Handle practice session creation errors with user-friendly messages
         * @param {Error} error - The error that occurred
         * @param {Object} context - Error context information
         * @returns {Promise} Rejected promise with enhanced error information
         */
        function handlePracticeSessionError(error, context) {
            context = context || {};
            
            $log.error('UnifiedPracticeController: Practice session error:', error, 'Context:', context);

            // Reset creation state
            isCreatingSession = false;

            // Determine user-friendly error message and recovery suggestions
            var userMessage = 'Failed to create practice session';
            var recoverySuggestions = ['Try again in a moment', 'Refresh the page and try again'];

            if (error.message) {
                if (error.message.includes('Authentication')) {
                    userMessage = 'Please log in to create practice sessions';
                    recoverySuggestions = ['Log in to your account', 'Refresh the page and log in'];
                } else if (error.message.includes('Parent session')) {
                    userMessage = 'The original interview session could not be found';
                    recoverySuggestions = ['Try selecting a different session', 'Go to dashboard and try again'];
                } else if (error.message.includes('difficulty')) {
                    userMessage = 'There was an issue with difficulty settings';
                    recoverySuggestions = ['Try again - difficulty will be set automatically', 'Contact support if problem persists'];
                } else if (error.message.includes('already in progress')) {
                    userMessage = 'Practice session is already being created';
                    recoverySuggestions = ['Wait a moment and check your dashboard', 'Refresh the page if needed'];
                }
            }

            // Broadcast error event for UI components to handle
            $rootScope.$broadcast('practice:session:creation:error', {
                error: error,
                context: context,
                userMessage: userMessage,
                recoverySuggestions: recoverySuggestions,
                timestamp: new Date().toISOString()
            });

            // Enhanced error object for promise rejection
            var enhancedError = new Error(userMessage);
            enhancedError.originalError = error;
            enhancedError.context = context;
            enhancedError.recoverySuggestions = recoverySuggestions;
            enhancedError.isUserFriendly = true;

            return $q.reject(enhancedError);
        }

        /**
         * Get preview of inherited settings for confirmation dialog
         * @param {number} parentSessionId - The parent session ID
         * @returns {Promise} Promise resolving to settings preview
         */
        function getInheritedSettingsPreview(parentSessionId) {
            if (!parentSessionId) {
                return $q.reject(new Error('Parent session ID is required'));
            }

            return UnifiedDifficultyStateService.getSessionDifficultyState(parentSessionId)
                .then(function(difficultyState) {
                    // Get the difficulty that will be inherited
                    var inheritedDifficulty = difficultyState.final_difficulty || 
                                            difficultyState.current_difficulty || 
                                            difficultyState.initial_difficulty || 
                                            'medium';

                    var difficultyInfo = DifficultyDisplayService.getDifficultyInfo(
                        DifficultyDisplayService.normalizeDifficultyInput(inheritedDifficulty)
                    );

                    return {
                        parentSessionId: parentSessionId,
                        inheritedDifficulty: {
                            level: inheritedDifficulty,
                            label: difficultyInfo.label,
                            color: difficultyInfo.color,
                            icon: difficultyInfo.icon
                        },
                        difficultyWasAdjusted: difficultyState.current_difficulty !== difficultyState.initial_difficulty,
                        initialDifficulty: difficultyState.initial_difficulty,
                        finalDifficulty: difficultyState.final_difficulty || difficultyState.current_difficulty,
                        changeCount: (difficultyState.difficulty_changes || []).length,
                        lastUpdated: difficultyState.last_updated
                    };
                })
                .catch(function(error) {
                    $log.error('UnifiedPracticeController: Error getting settings preview:', error);
                    
                    // Return fallback preview
                    return {
                        parentSessionId: parentSessionId,
                        inheritedDifficulty: {
                            level: 'medium',
                            label: 'Medium',
                            color: '#fd7e14',
                            icon: 'fas fa-balance-scale'
                        },
                        difficultyWasAdjusted: false,
                        initialDifficulty: 'medium',
                        finalDifficulty: 'medium',
                        changeCount: 0,
                        lastUpdated: null,
                        isPreviewFallback: true
                    };
                });
        }

        // ==================== Private Helper Methods ====================

        /**
         * Execute the actual practice session creation
         * @param {number} parentSessionId - The parent session ID
         * @param {Object} options - Creation options
         * @param {Object} validationResult - Validation result from parent session
         * @returns {Promise} Promise resolving to practice session data
         */
        function executeCreatePracticeSession(parentSessionId, options, validationResult) {
            isCreatingSession = true;

            $log.info('UnifiedPracticeController: Creating practice session from parent', parentSessionId);

            // Broadcast creation start event
            $rootScope.$broadcast('practice:session:creation:started', {
                parentSessionId: parentSessionId,
                options: options,
                validationResult: validationResult
            });

            return UnifiedDifficultyStateService.createPracticeSessionWithDifficulty(parentSessionId, {
                showLoading: options.showLoading !== false,
                showSuccess: options.showSuccess !== false
            })
            .then(function(response) {
                isCreatingSession = false;
                lastCreatedSessionId = response.session.id;

                $log.info('UnifiedPracticeController: Practice session created successfully:', response.session.id);

                // Validate difficulty inheritance
                if (response.difficulty_validation && !response.difficulty_validation.isValid) {
                    $log.warn('UnifiedPracticeController: Difficulty inheritance validation failed:', 
                             response.difficulty_validation.errors);
                    
                    // Still proceed but warn user
                    $rootScope.$broadcast('practice:session:difficulty:warning', {
                        sessionId: response.session.id,
                        validationErrors: response.difficulty_validation.errors,
                        validationWarnings: response.difficulty_validation.warnings
                    });
                }

                // Store session data for interview
                SessionDataService.setSessionData({
                    sessionId: response.session.id,
                    questions: response.questions,
                    configuration: response.configuration,
                    inheritedSettings: response.inherited_settings,
                    adaptiveDifficulty: response.inherited_settings.difficulty_level,
                    parentSessionId: parentSessionId,
                    isPracticeSession: true,
                    difficultyValidation: response.difficulty_validation
                });

                // Broadcast success event
                $rootScope.$broadcast('practice:session:creation:success', {
                    practiceSession: response.session,
                    parentSessionId: parentSessionId,
                    inheritedSettings: response.inherited_settings,
                    difficultyValidation: response.difficulty_validation
                });

                // Navigate to interview chat
                if (options.autoNavigate !== false) {
                    $location.path('/interview-chat/' + response.session.id);
                }

                return response;
            })
            .catch(function(error) {
                isCreatingSession = false;
                
                $log.error('UnifiedPracticeController: Practice session creation failed:', error);
                
                // Re-throw for caller to handle
                throw error;
            });
        }

        /**
         * Show confirmation dialog for practice session creation
         * @param {Object} sessionInfo - Session information
         * @param {Object} preview - Settings preview
         * @param {Object} options - Dialog options
         * @returns {Promise} Promise resolving to boolean (confirmed/cancelled)
         */
        function showConfirmationDialog(sessionInfo, preview, options) {
            var deferred = $q.defer();

            // Build confirmation message
            var message = 'Create a new practice session with these settings:\n\n';
            message += '• Target Role: ' + (sessionInfo.target_role || 'Unknown') + '\n';
            message += '• Duration: ' + (sessionInfo.duration || 30) + ' minutes\n';
            message += '• Difficulty: ' + preview.inheritedDifficulty.label;
            
            if (preview.difficultyWasAdjusted) {
                message += ' (adjusted from ' + preview.initialDifficulty + ')';
            }
            
            message += '\n• Question Count: ' + (sessionInfo.question_count || 'Auto-generated') + '\n\n';
            
            if (preview.difficultyWasAdjusted) {
                message += 'Note: This practice session will use the adjusted difficulty from your previous session.\n\n';
            }
            
            message += 'Fresh questions will be generated. Ready to start?';

            // Show confirmation dialog
            $rootScope.$broadcast('confirmation:show', {
                type: 'info',
                title: 'Start Practice Session',
                message: message,
                confirmText: 'Start Practice',
                cancelText: 'Cancel',
                data: { 
                    sessionInfo: sessionInfo, 
                    preview: preview,
                    options: options
                },
                confirmAction: function() {
                    deferred.resolve(true);
                    return Promise.resolve();
                },
                cancelAction: function() {
                    deferred.resolve(false);
                    return Promise.resolve();
                }
            });

            return deferred.promise;
        }

        // Log controller initialization
        $log.info('UnifiedPracticeController: Controller definition complete');
    }
})();