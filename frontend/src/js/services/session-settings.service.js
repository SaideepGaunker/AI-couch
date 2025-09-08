/**
 * Session Settings Service - Handle session settings inheritance and validation
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .service('SessionSettingsService', SessionSettingsService);

    SessionSettingsService.$inject = ['$q', 'ApiService'];

    function SessionSettingsService($q, ApiService) {
        var service = {
            createPracticeSession: createPracticeSession,
            getSessionInheritanceInfo: getSessionInheritanceInfo,
            validateInheritedSettings: validateInheritedSettings,
            displayInheritedSettings: displayInheritedSettings,
            createQuickTestSession: createQuickTestSession,
            validateQuickTestSettings: validateQuickTestSettings,
            getUserLastMainSession: getUserLastMainSession
        };

        return service;

        /**
         * Create practice session with proper settings inheritance
         * @param {number} originalSessionId - ID of the original session
         * @returns {Promise} Promise resolving to practice session data
         */
        function createPracticeSession(originalSessionId) {
            console.log('SessionSettingsService: Creating practice session from session', originalSessionId);
            
            return ApiService.postWithRetry('/interviews/' + originalSessionId + '/practice-again', {}, {
                loadingMessage: 'Creating practice session with inherited settings...',
                successMessage: 'Practice session created with your preferred settings!'
            })
                .then(function(response) {
                    console.log('SessionSettingsService: Practice session created with response:', response);
                    
                    // Validate that settings were properly inherited
                    var validation = validateInheritedSettings(response);
                    if (!validation.isValid) {
                        console.warn('SessionSettingsService: Settings inheritance validation failed:', validation.errors);
                    } else {
                        console.log('SessionSettingsService: Settings inheritance validated successfully');
                    }
                    
                    // Add validation results to response
                    response.validation = validation;
                    
                    return response;
                })
                .catch(function(error) {
                    console.error('SessionSettingsService: Error creating practice session:', error);
                    throw error;
                });
        }

        /**
         * Get inheritance information for a session
         * @param {number} sessionId - ID of the session
         * @returns {Promise} Promise resolving to inheritance information
         */
        function getSessionInheritanceInfo(sessionId) {
            return ApiService.get('/interviews/' + sessionId + '/inheritance-info')
                .then(function(response) {
                    console.log('SessionSettingsService: Inheritance info received:', response);
                    return response;
                })
                .catch(function(error) {
                    console.error('SessionSettingsService: Error getting inheritance info:', error);
                    throw error;
                });
        }

        /**
         * Validate that inherited settings are properly applied
         * @param {Object} practiceSessionResponse - Response from practice session creation
         * @returns {Object} Validation results
         */
        function validateInheritedSettings(practiceSessionResponse) {
            var errors = [];
            var warnings = [];
            
            try {
                if (!practiceSessionResponse) {
                    errors.push('No practice session response provided');
                    return { isValid: false, errors: errors, warnings: warnings };
                }
                
                var session = practiceSessionResponse.session;
                var inheritedSettings = practiceSessionResponse.inherited_settings;
                var questions = practiceSessionResponse.questions;
                var inheritanceVerification = practiceSessionResponse.inheritance_verification;
                
                // Validate session object
                if (!session) {
                    errors.push('Practice session object missing');
                } else {
                    // Validate parent session relationship
                    if (!session.parent_session_id) {
                        errors.push('Parent session ID not set');
                    }
                    
                    // Validate session mode
                    if (session.session_mode !== 'practice_again') {
                        errors.push('Session mode should be "practice_again", got: ' + session.session_mode);
                    }
                }
                
                // Validate inherited settings
                if (!inheritedSettings) {
                    warnings.push('Inherited settings information not provided');
                } else {
                    // Validate question count inheritance
                    if (questions && inheritedSettings.question_count) {
                        var actualQuestionCount = questions.length;
                        var expectedQuestionCount = inheritedSettings.question_count;
                        
                        if (actualQuestionCount !== expectedQuestionCount) {
                            errors.push('Question count mismatch: expected ' + expectedQuestionCount + ', got ' + actualQuestionCount);
                        }
                    }
                    
                    // Validate other inherited settings
                    if (session && inheritedSettings) {
                        if (session.duration !== inheritedSettings.duration) {
                            errors.push('Duration not inherited correctly');
                        }
                        
                        if (session.difficulty_level !== inheritedSettings.difficulty_level) {
                            errors.push('Difficulty level not inherited correctly');
                        }
                        
                        if (session.target_role !== inheritedSettings.target_role) {
                            errors.push('Target role not inherited correctly');
                        }
                    }
                }
                
                // Check inheritance verification if provided
                if (inheritanceVerification) {
                    if (!inheritanceVerification.settings_inherited) {
                        errors.push('Settings inheritance verification failed');
                    }
                    
                    if (!inheritanceVerification.question_count_matched) {
                        errors.push('Question count inheritance verification failed');
                    }
                    
                    if (!inheritanceVerification.parent_session_linked) {
                        errors.push('Parent session linking verification failed');
                    }
                    
                    if (!inheritanceVerification.session_mode_correct) {
                        errors.push('Session mode verification failed');
                    }
                }
                
                return {
                    isValid: errors.length === 0,
                    errors: errors,
                    warnings: warnings,
                    inheritedSettings: inheritedSettings,
                    verificationResults: inheritanceVerification
                };
                
            } catch (e) {
                console.error('SessionSettingsService: Error validating inherited settings:', e);
                return {
                    isValid: false,
                    errors: ['Validation error: ' + e.message],
                    warnings: warnings
                };
            }
        }

        /**
         * Display inherited settings information to user
         * @param {Object} inheritedSettings - Inherited settings object
         * @returns {Object} Display-friendly settings information
         */
        function displayInheritedSettings(inheritedSettings) {
            if (!inheritedSettings) {
                return {
                    message: 'Settings information not available',
                    details: {}
                };
            }
            
            var displayInfo = {
                message: 'Practice session created with your previous settings:',
                details: {
                    'Question Count': inheritedSettings.question_count || 'Not specified',
                    'Duration': (inheritedSettings.duration || 'Not specified') + (inheritedSettings.duration ? ' minutes' : ''),
                    'Difficulty Level': inheritedSettings.difficulty_level || 'Not specified',
                    'Target Role': inheritedSettings.target_role || 'Not specified'
                },
                summary: 'Your practice session will use the same question count (' + 
                        (inheritedSettings.question_count || 'default') + 
                        ') and settings as your original session.'
            };
            
            return displayInfo;
        }

        /**
         * Create quick test session with proper settings inheritance or override
         * @param {Object} overrideSettings - Optional settings to override defaults
         * @returns {Promise} Promise resolving to quick test session data
         */
        function createQuickTestSession(overrideSettings) {
            console.log('SessionSettingsService: Creating quick test session with overrides:', overrideSettings);
            
            // Use the new quick test endpoint that handles inheritance
            return ApiService.postWithRetry('/interviews/quick-test', overrideSettings || {}, {
                loadingMessage: 'Creating quick test session with your preferences...',
                successMessage: 'Quick test session created!'
            })
                .then(function(response) {
                    console.log('SessionSettingsService: Quick test session created:', response);
                    
                    // Validate that settings were properly applied
                    var validation = validateQuickTestSettings(response);
                    if (!validation.isValid) {
                        console.warn('SessionSettingsService: Quick test settings validation failed:', validation.errors);
                    } else {
                        console.log('SessionSettingsService: Quick test settings validated successfully');
                    }
                    
                    // Add validation results to response
                    response.validation = validation;
                    
                    return response;
                })
                .catch(function(error) {
                    console.error('SessionSettingsService: Error creating quick test session:', error);
                    throw error;
                });
        }

        /**
         * Validate that quick test settings are properly applied
         * @param {Object} quickTestResponse - Response from quick test session creation
         * @returns {Object} Validation results
         */
        function validateQuickTestSettings(quickTestResponse) {
            var errors = [];
            var warnings = [];
            
            try {
                if (!quickTestResponse) {
                    errors.push('No quick test session response provided');
                    return { isValid: false, errors: errors, warnings: warnings };
                }
                
                var session = quickTestResponse.session;
                var settingsInfo = quickTestResponse.settings_info;
                var questions = quickTestResponse.questions;
                var inheritanceVerification = quickTestResponse.inheritance_verification;
                
                // Validate session object
                if (!session) {
                    errors.push('Quick test session object missing');
                } else {
                    // Validate session mode
                    if (session.session_mode !== 'quick_test') {
                        errors.push('Session mode should be "quick_test", got: ' + session.session_mode);
                    }
                    
                    // Validate duration (should always be 15 for quick tests)
                    if (session.duration !== 15) {
                        errors.push('Quick test duration should be 15 minutes, got: ' + session.duration);
                    }
                    
                    // Validate session type (should always be technical for quick tests)
                    if (session.session_type !== 'technical') {
                        errors.push('Quick test session type should be "technical", got: ' + session.session_type);
                    }
                }
                
                // Validate settings info
                if (!settingsInfo) {
                    warnings.push('Settings information not provided');
                } else {
                    // Validate question count
                    if (questions && settingsInfo.question_count) {
                        var actualQuestionCount = questions.length;
                        var expectedQuestionCount = parseInt(settingsInfo.question_count);
                        
                        // Log the question counts for debugging
                        console.log('SessionSettingsService: Validating question count - expected:', expectedQuestionCount, 'actual:', actualQuestionCount);
                        
                        // Allow for a small difference in question count (backend might adjust based on availability)
                        if (Math.abs(actualQuestionCount - expectedQuestionCount) > 1) {
                            warnings.push('Question count difference: expected ' + expectedQuestionCount + ', got ' + actualQuestionCount);
                        }
                    }
                    
                    // Validate question count source
                    var validSources = ['inherited', 'user_override', 'default'];
                    if (!validSources.includes(settingsInfo.question_count_source)) {
                        errors.push('Invalid question count source: ' + settingsInfo.question_count_source);
                    }
                    
                    // Log inheritance information
                    if (settingsInfo.question_count_source === 'inherited' && settingsInfo.inherited_from_session_id) {
                        console.log('SessionSettingsService: Question count inherited from session', settingsInfo.inherited_from_session_id);
                    } else if (settingsInfo.question_count_source === 'user_override') {
                        console.log('SessionSettingsService: Question count overridden by user');
                    } else if (settingsInfo.question_count_source === 'default') {
                        console.log('SessionSettingsService: Using default question count (no previous sessions)');
                    }
                }
                
                // Check inheritance verification if provided
                if (inheritanceVerification) {
                    if (!inheritanceVerification.settings_applied) {
                        errors.push('Settings application verification failed');
                    }
                }
                
                return {
                    isValid: errors.length === 0,
                    errors: errors,
                    warnings: warnings,
                    settingsInfo: settingsInfo,
                    verificationResults: inheritanceVerification
                };
                
            } catch (e) {
                console.error('SessionSettingsService: Error validating quick test settings:', e);
                return {
                    isValid: false,
                    errors: ['Validation error: ' + e.message],
                    warnings: warnings
                };
            }
        }

        /**
         * Get user's last main session for settings inheritance
         * @returns {Promise} Promise resolving to last main session data
         */
        function getUserLastMainSession() {
            return ApiService.get('/interviews/', { limit: 10 })
                .then(function(response) {
                    if (response && response.length > 0) {
                        // Find the most recent non-practice session
                        var mainSessions = response.filter(function(session) {
                            return session.session_mode !== 'practice_again';
                        });
                        
                        if (mainSessions.length > 0) {
                            console.log('SessionSettingsService: Found last main session:', mainSessions[0]);
                            return mainSessions[0];
                        }
                    }
                    
                    console.log('SessionSettingsService: No main sessions found');
                    return null;
                })
                .catch(function(error) {
                    console.error('SessionSettingsService: Error getting last main session:', error);
                    throw error;
                });
        }
    }
})();