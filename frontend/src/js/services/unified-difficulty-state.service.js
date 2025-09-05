/**
 * Unified Difficulty State Service - Centralized difficulty state management for frontend consistency
 * 
 * This service provides:
 * - Session-specific difficulty state management with caching
 * - Practice session creation with difficulty validation
 * - Real-time difficulty change notifications
 * - Component synchronization across the application
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .service('UnifiedDifficultyStateService', UnifiedDifficultyStateService);

    UnifiedDifficultyStateService.$inject = ['$rootScope', '$q', '$log', 'ApiService', 'DifficultyDisplayService'];

    function UnifiedDifficultyStateService($rootScope, $q, $log, ApiService, DifficultyDisplayService) {
        var service = {
            // State management
            getSessionDifficultyState: getSessionDifficultyState,
            updateSessionDifficulty: updateSessionDifficulty,
            subscribeToChanges: subscribeToChanges,
            
            // Practice session handling
            createPracticeSessionWithDifficulty: createPracticeSessionWithDifficulty,
            validateDifficultyInheritance: validateDifficultyInheritance,
            
            // Component synchronization
            syncDifficultyAcrossComponents: syncDifficultyAcrossComponents,
            getDifficultyForDisplay: getDifficultyForDisplay,
            
            // Cache management
            clearCache: clearCache,
            refreshSessionState: refreshSessionState,
            
            // Utility methods
            isSessionStateLoaded: isSessionStateLoaded,
            getLoadedSessions: getLoadedSessions
        };

        // Internal state cache - stores difficulty state per session
        var sessionDifficultyCache = {};
        
        // Subscribers for difficulty change notifications
        var difficultyChangeSubscribers = [];
        
        // Loading states to prevent duplicate requests
        var loadingStates = {};
        
        // Service initialization
        init();

        return service;

        // ==================== Initialization ====================

        function init() {
            $log.info('UnifiedDifficultyStateService: Initializing service');
            
            // Listen for session completion events to update final difficulty
            $rootScope.$on('interview:session:completed', function(event, data) {
                if (data && data.sessionId) {
                    refreshSessionState(data.sessionId);
                }
            });
            
            // Listen for difficulty adjustment events from adaptive engine
            $rootScope.$on('difficulty:adjusted', function(event, data) {
                if (data && data.sessionId && data.newDifficulty) {
                    handleDifficultyAdjustment(data.sessionId, data.newDifficulty, data.reason);
                }
            });
            
            // Clear cache when user logs out
            $rootScope.$on('auth:logout', function() {
                clearCache();
            });
        }

        // ==================== State Management ====================

        /**
         * Get difficulty state for a specific session with caching and server fallback
         * @param {number} sessionId - The session ID
         * @param {Object} options - Options for state retrieval
         * @returns {Promise} Promise resolving to difficulty state
         */
        function getSessionDifficultyState(sessionId, options) {
            options = options || {};
            
            if (!sessionId) {
                return $q.reject(new Error('Session ID is required'));
            }

            // Check cache first unless forced refresh
            if (!options.forceRefresh && sessionDifficultyCache[sessionId]) {
                $log.debug('UnifiedDifficultyStateService: Returning cached state for session', sessionId);
                return $q.resolve(angular.copy(sessionDifficultyCache[sessionId]));
            }

            // Check if already loading to prevent duplicate requests
            if (loadingStates[sessionId]) {
                return loadingStates[sessionId];
            }

            // Fetch from server
            $log.info('UnifiedDifficultyStateService: Fetching difficulty state for session', sessionId);
            
            var loadingPromise = ApiService.get('/interviews/' + sessionId + '/difficulty-state', null, {
                loadingMessage: options.showLoading ? 'Loading difficulty state...' : null,
                suppressErrorToast: options.suppressErrors
            })
            .then(function(response) {
                // Cache the result
                sessionDifficultyCache[sessionId] = response;
                
                $log.info('UnifiedDifficultyStateService: Loaded difficulty state for session', sessionId, response);
                
                // Broadcast state loaded event
                $rootScope.$broadcast('difficulty:state:loaded', {
                    sessionId: sessionId,
                    state: response
                });
                
                return angular.copy(response);
            })
            .catch(function(error) {
                $log.error('UnifiedDifficultyStateService: Error loading difficulty state for session', sessionId, error);
                
                // Try to create fallback state from session data
                return createFallbackState(sessionId);
            })
            .finally(function() {
                delete loadingStates[sessionId];
            });

            loadingStates[sessionId] = loadingPromise;
            return loadingPromise;
        }

        /**
         * Update difficulty for a specific session
         * @param {number} sessionId - The session ID
         * @param {string} newDifficulty - The new difficulty level
         * @param {string} reason - Reason for the change
         * @param {Object} options - Update options
         * @returns {Promise} Promise resolving to updated state
         */
        function updateSessionDifficulty(sessionId, newDifficulty, reason, options) {
            options = options || {};
            
            if (!sessionId || !newDifficulty) {
                return $q.reject(new Error('Session ID and new difficulty are required'));
            }

            $log.info('UnifiedDifficultyStateService: Updating difficulty for session', sessionId, 'to', newDifficulty);

            var updateData = {
                difficulty: newDifficulty,
                reason: reason || 'Manual update',
                question_index: options.questionIndex
            };

            return ApiService.put('/interviews/' + sessionId + '/difficulty', updateData, {
                loadingMessage: options.showLoading ? 'Updating difficulty...' : null,
                successMessage: options.showSuccess ? 'Difficulty updated successfully' : null
            })
            .then(function(response) {
                // Update cache
                if (sessionDifficultyCache[sessionId]) {
                    sessionDifficultyCache[sessionId].current_difficulty = newDifficulty;
                    sessionDifficultyCache[sessionId].last_updated = new Date().toISOString();
                    
                    // Add to difficulty changes if not already present
                    if (!sessionDifficultyCache[sessionId].difficulty_changes) {
                        sessionDifficultyCache[sessionId].difficulty_changes = [];
                    }
                    
                    sessionDifficultyCache[sessionId].difficulty_changes.push({
                        from_difficulty: sessionDifficultyCache[sessionId].current_difficulty,
                        to_difficulty: newDifficulty,
                        reason: reason,
                        question_index: options.questionIndex,
                        timestamp: new Date().toISOString()
                    });
                }

                // Notify subscribers and sync components
                notifyDifficultyChange(sessionId, newDifficulty, reason);
                syncDifficultyAcrossComponents(sessionId, newDifficulty);

                return response;
            })
            .catch(function(error) {
                $log.error('UnifiedDifficultyStateService: Error updating difficulty for session', sessionId, error);
                throw error;
            });
        }

        /**
         * Subscribe to difficulty changes for real-time notifications
         * @param {Function} callback - Callback function to receive change notifications
         * @returns {Function} Unsubscribe function
         */
        function subscribeToChanges(callback) {
            if (typeof callback !== 'function') {
                throw new Error('Callback must be a function');
            }

            difficultyChangeSubscribers.push(callback);
            
            $log.debug('UnifiedDifficultyStateService: Added difficulty change subscriber, total:', difficultyChangeSubscribers.length);

            // Return unsubscribe function
            return function() {
                var index = difficultyChangeSubscribers.indexOf(callback);
                if (index > -1) {
                    difficultyChangeSubscribers.splice(index, 1);
                    $log.debug('UnifiedDifficultyStateService: Removed difficulty change subscriber, remaining:', difficultyChangeSubscribers.length);
                }
            };
        }

        // ==================== Practice Session Handling ====================

        /**
         * Create practice session with proper difficulty inheritance and validation
         * @param {number} parentSessionId - The parent session ID
         * @param {Object} options - Creation options
         * @returns {Promise} Promise resolving to practice session data with validation
         */
        function createPracticeSessionWithDifficulty(parentSessionId, options) {
            options = options || {};
            
            if (!parentSessionId) {
                return $q.reject(new Error('Parent session ID is required'));
            }

            $log.info('UnifiedDifficultyStateService: Creating practice session from parent', parentSessionId);
            
            return ApiService.post('/interviews/' + parentSessionId + '/practice-again-enhanced', {}, {
                loadingMessage: options.showLoading ? 'Creating practice session...' : null,
                successMessage: options.showSuccess ? 'Practice session created successfully' : null
            })
            .then(function(response) {
                var practiceSession = response.session;
                var inheritedDifficulty = response.inherited_settings.difficulty_level;
                
                // Cache the difficulty state for the new practice session
                sessionDifficultyCache[practiceSession.id] = {
                    session_id: practiceSession.id,
                    initial_difficulty: inheritedDifficulty,
                    current_difficulty: inheritedDifficulty,
                    final_difficulty: null,
                    parent_session_id: parentSessionId,
                    is_practice_session: true,
                    difficulty_changes: [],
                    last_updated: new Date().toISOString()
                };
                
                // Validate inheritance
                var validation = validateDifficultyInheritance(response);
                response.difficulty_validation = validation;
                
                // Broadcast practice session created event
                $rootScope.$broadcast('practice:session:created', {
                    practiceSession: practiceSession,
                    parentSessionId: parentSessionId,
                    inheritedDifficulty: inheritedDifficulty,
                    validation: validation
                });
                
                $log.info('UnifiedDifficultyStateService: Practice session created with difficulty', inheritedDifficulty, 'validation:', validation.isValid);
                
                return response;
            })
            .catch(function(error) {
                $log.error('UnifiedDifficultyStateService: Error creating practice session from parent', parentSessionId, error);
                throw error;
            });
        }

        /**
         * Validate that difficulty was properly inherited in practice session
         * @param {Object} practiceSessionResponse - Response from practice session creation
         * @returns {Object} Validation result with detailed information
         */
        function validateDifficultyInheritance(practiceSessionResponse) {
            var errors = [];
            var warnings = [];
            
            try {
                var parentInfo = practiceSessionResponse.parent_session_info;
                var inheritedSettings = practiceSessionResponse.inherited_settings;
                var inheritanceVerification = practiceSessionResponse.inheritance_verification;
                
                if (!parentInfo || !inheritedSettings) {
                    errors.push('Missing parent session or inherited settings information');
                    return { isValid: false, errors: errors, warnings: warnings };
                }
                
                // Check if difficulty was properly inherited from final state
                if (inheritanceVerification && !inheritanceVerification.difficulty_inherited_from_final) {
                    errors.push('Difficulty was not inherited from parent session final state');
                }
                
                // Check if difficulty changed during parent session
                if (parentInfo.difficulty_was_adjusted) {
                    if (inheritedSettings.difficulty_level === parentInfo.initial_difficulty) {
                        errors.push('Practice session used initial difficulty instead of final adjusted difficulty');
                    }
                    
                    if (inheritedSettings.difficulty_level !== parentInfo.final_difficulty) {
                        errors.push('Practice session difficulty does not match parent final difficulty');
                    }
                } else {
                    // If no adjustment occurred, inherited should match both initial and final
                    if (inheritedSettings.difficulty_level !== parentInfo.initial_difficulty) {
                        warnings.push('Inherited difficulty differs from parent difficulty despite no adjustments');
                    }
                }
                
                // Validate difficulty format
                var normalizedDifficulty = DifficultyDisplayService.normalizeDifficultyInput(inheritedSettings.difficulty_level);
                var expectedString = DifficultyDisplayService.getStringLevel(normalizedDifficulty);
                
                if (inheritedSettings.difficulty_level !== expectedString) {
                    warnings.push('Inherited difficulty format may be inconsistent');
                }
                
                return {
                    isValid: errors.length === 0,
                    errors: errors,
                    warnings: warnings,
                    parentDifficultyInfo: {
                        initial: parentInfo.initial_difficulty,
                        final: parentInfo.final_difficulty,
                        wasAdjusted: parentInfo.difficulty_was_adjusted
                    },
                    inheritedDifficulty: inheritedSettings.difficulty_level,
                    inheritanceVerification: inheritanceVerification
                };
                
            } catch (e) {
                $log.error('UnifiedDifficultyStateService: Validation error:', e);
                return {
                    isValid: false,
                    errors: ['Validation error: ' + e.message],
                    warnings: warnings
                };
            }
        }

        // ==================== Component Synchronization ====================

        /**
         * Sync difficulty across all components for a session
         * @param {number} sessionId - The session ID
         * @param {string} newDifficulty - The new difficulty level
         */
        function syncDifficultyAcrossComponents(sessionId, newDifficulty) {
            try {
                // Update all difficulty displays for this session
                var difficultyElements = document.querySelectorAll('[data-session-id="' + sessionId + '"][data-difficulty-display]');
                
                difficultyElements.forEach(function(element) {
                    var displayInfo = DifficultyDisplayService.getDifficultyInfo(
                        DifficultyDisplayService.normalizeDifficultyInput(newDifficulty)
                    );
                    
                    element.textContent = displayInfo.label;
                    element.setAttribute('data-current-difficulty', newDifficulty);
                    
                    // Update color if element supports it
                    if (element.style) {
                        element.style.color = displayInfo.color;
                    }
                });
                
                // Broadcast to Angular components
                $rootScope.$broadcast('difficulty:changed', {
                    sessionId: sessionId,
                    newDifficulty: newDifficulty,
                    timestamp: new Date().toISOString()
                });
                
                $log.debug('UnifiedDifficultyStateService: Synced difficulty across', difficultyElements.length, 'components for session', sessionId);
                
            } catch (error) {
                $log.error('UnifiedDifficultyStateService: Error syncing difficulty across components:', error);
                
                // Broadcast error event
                $rootScope.$broadcast('difficulty:sync:error', {
                    sessionId: sessionId,
                    newDifficulty: newDifficulty,
                    error: error.message
                });
            }
        }

        /**
         * Get difficulty for display with consistent formatting
         * @param {number} sessionId - The session ID
         * @param {Object} options - Display options
         * @returns {Promise} Promise resolving to formatted difficulty display data
         */
        function getDifficultyForDisplay(sessionId, options) {
            options = options || {};
            
            return getSessionDifficultyState(sessionId, options)
                .then(function(state) {
                    var currentLevel = DifficultyDisplayService.normalizeDifficultyInput(state.current_difficulty);
                    var initialLevel = DifficultyDisplayService.normalizeDifficultyInput(state.initial_difficulty);
                    
                    var currentInfo = DifficultyDisplayService.getDifficultyInfo(currentLevel);
                    var initialInfo = DifficultyDisplayService.getDifficultyInfo(initialLevel);
                    
                    return {
                        current: {
                            level: currentLevel,
                            string: state.current_difficulty,
                            label: currentInfo.label,
                            color: currentInfo.color,
                            icon: currentInfo.icon,
                            badgeClass: currentInfo.badgeClass
                        },
                        initial: {
                            level: initialLevel,
                            string: state.initial_difficulty,
                            label: initialInfo.label,
                            color: initialInfo.color,
                            icon: initialInfo.icon,
                            badgeClass: initialInfo.badgeClass
                        },
                        final: state.final_difficulty ? {
                            level: DifficultyDisplayService.normalizeDifficultyInput(state.final_difficulty),
                            string: state.final_difficulty,
                            label: DifficultyDisplayService.getDifficultyInfo(
                                DifficultyDisplayService.normalizeDifficultyInput(state.final_difficulty)
                            ).label
                        } : null,
                        hasChanged: state.current_difficulty !== state.initial_difficulty,
                        isCompleted: !!state.final_difficulty,
                        changeCount: (state.difficulty_changes || []).length,
                        lastUpdated: state.last_updated
                    };
                })
                .catch(function(error) {
                    $log.error('UnifiedDifficultyStateService: Error getting difficulty for display:', error);
                    
                    // Return fallback display data
                    return {
                        current: {
                            level: 3,
                            string: 'medium',
                            label: 'Medium',
                            color: '#fd7e14',
                            icon: 'fas fa-balance-scale',
                            badgeClass: 'badge bg-warning'
                        },
                        initial: null,
                        final: null,
                        hasChanged: false,
                        isCompleted: false,
                        changeCount: 0,
                        lastUpdated: null,
                        error: error.message
                    };
                });
        }

        // ==================== Cache Management ====================

        /**
         * Clear all cached difficulty states
         */
        function clearCache() {
            sessionDifficultyCache = {};
            loadingStates = {};
            $log.info('UnifiedDifficultyStateService: Cache cleared');
            
            $rootScope.$broadcast('difficulty:cache:cleared');
        }

        /**
         * Refresh difficulty state for a specific session
         * @param {number} sessionId - The session ID
         * @returns {Promise} Promise resolving to refreshed state
         */
        function refreshSessionState(sessionId) {
            if (!sessionId) {
                return $q.reject(new Error('Session ID is required'));
            }

            // Remove from cache and loading states
            delete sessionDifficultyCache[sessionId];
            delete loadingStates[sessionId];
            
            // Fetch fresh state
            return getSessionDifficultyState(sessionId, { forceRefresh: true });
        }

        // ==================== Utility Methods ====================

        /**
         * Check if session state is loaded in cache
         * @param {number} sessionId - The session ID
         * @returns {boolean} True if state is loaded
         */
        function isSessionStateLoaded(sessionId) {
            return !!sessionDifficultyCache[sessionId];
        }

        /**
         * Get list of loaded session IDs
         * @returns {Array} Array of session IDs that have loaded states
         */
        function getLoadedSessions() {
            return Object.keys(sessionDifficultyCache).map(function(id) {
                return parseInt(id);
            });
        }

        // ==================== Private Helper Methods ====================

        /**
         * Handle difficulty adjustment from adaptive engine
         * @param {number} sessionId - The session ID
         * @param {string} newDifficulty - The new difficulty level
         * @param {string} reason - Reason for adjustment
         */
        function handleDifficultyAdjustment(sessionId, newDifficulty, reason) {
            // Update cache if session is loaded
            if (sessionDifficultyCache[sessionId]) {
                var oldDifficulty = sessionDifficultyCache[sessionId].current_difficulty;
                sessionDifficultyCache[sessionId].current_difficulty = newDifficulty;
                sessionDifficultyCache[sessionId].last_updated = new Date().toISOString();
                
                // Add to difficulty changes
                if (!sessionDifficultyCache[sessionId].difficulty_changes) {
                    sessionDifficultyCache[sessionId].difficulty_changes = [];
                }
                
                sessionDifficultyCache[sessionId].difficulty_changes.push({
                    from_difficulty: oldDifficulty,
                    to_difficulty: newDifficulty,
                    reason: reason,
                    timestamp: new Date().toISOString()
                });
            }

            // Notify subscribers and sync components
            notifyDifficultyChange(sessionId, newDifficulty, reason);
            syncDifficultyAcrossComponents(sessionId, newDifficulty);
        }

        /**
         * Notify all subscribers of difficulty change
         * @param {number} sessionId - The session ID
         * @param {string} newDifficulty - The new difficulty level
         * @param {string} reason - Reason for change
         */
        function notifyDifficultyChange(sessionId, newDifficulty, reason) {
            var changeData = {
                sessionId: sessionId,
                newDifficulty: newDifficulty,
                reason: reason,
                timestamp: new Date().toISOString()
            };

            // Notify all subscribers
            difficultyChangeSubscribers.forEach(function(callback) {
                try {
                    callback(changeData);
                } catch (error) {
                    $log.error('UnifiedDifficultyStateService: Error in difficulty change subscriber:', error);
                }
            });
        }

        /**
         * Create fallback state when server request fails
         * @param {number} sessionId - The session ID
         * @returns {Promise} Promise resolving to fallback state
         */
        function createFallbackState(sessionId) {
            $log.warn('UnifiedDifficultyStateService: Creating fallback state for session', sessionId);
            
            // Try to get session data from other sources
            return ApiService.get('/interviews/' + sessionId, null, {
                suppressErrorToast: true
            })
            .then(function(sessionData) {
                var fallbackState = {
                    session_id: sessionId,
                    initial_difficulty: sessionData.difficulty_level || 'medium',
                    current_difficulty: sessionData.difficulty_level || 'medium',
                    final_difficulty: sessionData.final_difficulty_level || null,
                    difficulty_changes: [],
                    last_updated: new Date().toISOString(),
                    is_fallback: true
                };
                
                // Cache fallback state
                sessionDifficultyCache[sessionId] = fallbackState;
                
                return fallbackState;
            })
            .catch(function() {
                // Ultimate fallback
                var ultimateFallback = {
                    session_id: sessionId,
                    initial_difficulty: 'medium',
                    current_difficulty: 'medium',
                    final_difficulty: null,
                    difficulty_changes: [],
                    last_updated: new Date().toISOString(),
                    is_fallback: true,
                    is_ultimate_fallback: true
                };
                
                sessionDifficultyCache[sessionId] = ultimateFallback;
                return ultimateFallback;
            });
        }

        // Log service initialization
        $log.info('UnifiedDifficultyStateService: Service initialized');
    }
})();