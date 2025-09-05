/**
 * Dashboard Controller - Component-based Architecture
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .controller('DashboardController', DashboardController);

    DashboardController.$inject = ['$location', '$rootScope', 'AuthService', 'ApiService', 'SessionDataService', 'DifficultyDisplayService', 'SessionSettingsService', 'UnifiedDifficultyStateService'];

    function DashboardController($location, $rootScope, AuthService, ApiService, SessionDataService, DifficultyDisplayService, SessionSettingsService, UnifiedDifficultyStateService) {
        var vm = this;

        // Properties
        vm.user = AuthService.getCurrentUser() || { name: 'User' };
        
        // Ensure user has a name for display
        if (!vm.user.name) {
            vm.user.name = vm.user.email ? vm.user.email.split('@')[0] : 'User';
        }
        vm.stats = {
            total_sessions: 0,
            total_time: 0,
            avg_score: 0,
            improvement: 0,
            sessions_this_week: 0,
            streak: 0
        };
        vm.enhancedStats = null; // Enhanced statistics with performance trends
        vm.recentSessions = [];
        vm.progressData = [];
        vm.loading = true;
        vm.error = '';
        vm.loadingStates = {}; // Track loading state for individual sessions

        // Session-specific difficulty state management
        vm.sessionDifficultyStates = {}; // Cache for session difficulty states
        vm.sessionDifficultyDisplays = {}; // Cache for session difficulty displays

        // Methods
        vm.loadDashboardData = loadDashboardData;
        vm.startInterview = startInterview;
        vm.viewProgress = viewProgress;
        vm.practiceAgain = practiceAgain;
        vm.viewSessionDetails = viewSessionDetails;
        vm.viewOriginalSession = viewOriginalSession;
        vm.getEstimatedQuestionCount = getEstimatedQuestionCount;
        vm.getConsistentDifficultyLabel = getConsistentDifficultyLabel;

        // Session-specific difficulty methods
        vm.loadSessionDifficultyStates = loadSessionDifficultyStates;
        vm.getSessionDifficultyDisplay = getSessionDifficultyDisplay;
        vm.hasSessionDifficultyChanged = hasSessionDifficultyChanged;
        vm.createPracticeWithEnhancedDifficulty = createPracticeWithEnhancedDifficulty;

        // Initialize immediately
        init();
        activate();
        
        function init() {
            // Set safe defaults immediately to prevent template errors
            vm.user = vm.user || { name: 'User' };
            vm.stats = vm.stats || {
                total_sessions: 0,
                total_time: 0,
                avg_score: 0,
                improvement: 0,
                sessions_this_week: 0,
                streak: 0
            };
            vm.recentSessions = vm.recentSessions || [];
            vm.loading = false; // Start with loading false so content shows immediately
            vm.error = '';
            
            console.log('Dashboard controller initialized with defaults');
        }

        function activate() {
            console.log('Dashboard controller activating...');
            
            // Initialize with default values to prevent template errors
            vm.user = vm.user || { name: 'Loading...' };
            vm.stats = vm.stats || {
                total_sessions: 0,
                total_time: 0,
                avg_score: 0,
                improvement: 0,
                sessions_this_week: 0,
                streak: 0
            };
            
            // Check authentication
            if (!AuthService.isAuthenticated()) {
                console.log('User not authenticated in dashboard, redirecting to login');
                $location.path('/login');
                return;
            }
            
            console.log('Dashboard controller activated for user:', vm.user);
            
            // Force a digest cycle to update the template immediately
            $rootScope.$applyAsync(function() {
                loadDashboardData();
            });
        }

        function loadDashboardData() {
            vm.loading = true;
            vm.error = '';
            
            console.log('Loading dashboard data...');

            // Load basic user session statistics
            ApiService.get('/interviews/statistics')
                .then(function(response) {
                    console.log('Raw API response for statistics:', response);
                    
                    if (response) {
                        // Map backend response to frontend stats structure
                        vm.stats = {
                            total_sessions: response.total_sessions || 0,
                            total_time: response.practice_hours || 0, // Map practice_hours to total_time
                            avg_score: response.avg_score || 0,
                            improvement: response.improvement_rate || 0, // Map improvement_rate to improvement
                            sessions_this_week: response.sessions_this_week || 0,
                            streak: response.streak || 0
                        };
                        
                        console.log('Dashboard stats mapped:', vm.stats);
                        
                        // Force template update
                        $rootScope.$applyAsync();
                    } else {
                        console.log('No response data, using defaults');
                        vm.stats = {
                            total_sessions: 0,
                            total_time: 0,
                            avg_score: 0,
                            improvement: 0,
                            sessions_this_week: 0,
                            streak: 0
                        };
                    }
                })
                .catch(function(error) {
                    console.error('Failed to load stats:', error);
                    // Use default values and show in console
                    vm.stats = {
                        total_sessions: 0,
                        total_time: 0,
                        avg_score: 0,
                        improvement: 0,
                        sessions_this_week: 0,
                        streak: 0
                    };
                    console.log('Using default stats due to error:', vm.stats);
                })
                .finally(function() {
                    // Always turn off loading after stats are loaded (success or error)
                    vm.loading = false;
                    console.log('Stats loading completed, loading set to false');
                });

            // Load enhanced statistics with performance trends
            ApiService.get('/interviews/statistics/enhanced')
                .then(function(response) {
                    if (response) {
                        vm.enhancedStats = {
                            current_performance_score: response.current_performance_score || 0,
                            next_difficulty_level: DifficultyDisplayService.getDifficultyLabel(
                                DifficultyDisplayService.normalizeDifficultyInput(response.next_difficulty_level || 'medium')
                            ),
                            difficulty_change_reason: response.difficulty_change_reason || '',
                            performance_trend: response.performance_trend || [],
                            trend_direction: response.trend_direction || 'stable',
                            content_score: response.average_scores?.content_quality || 0,
                            body_language_score: response.average_scores?.body_language || 0,
                            voice_score: response.average_scores?.tone_confidence || 0
                        };
                        
                        console.log('Enhanced stats loaded:', vm.enhancedStats);
                    }
                })
                .catch(function(error) {
                    console.log('Failed to load enhanced stats:', error);
                    // Create fallback enhanced stats
                    vm.enhancedStats = {
                        current_performance_score: vm.stats.avg_score || 0,
                        next_difficulty_level: DifficultyDisplayService.getDifficultyLabel(2), // Medium
                        difficulty_change_reason: 'Based on recent performance',
                        performance_trend: [],
                        trend_direction: 'stable',
                        content_score: 0,
                        body_language_score: 0,
                        voice_score: 0
                    };
                });

            // Load recent sessions with family info
            ApiService.get('/interviews/', { limit: 5, skip: 0, include_family_info: true })
                .then(function(response) {
                    if (response && Array.isArray(response)) {
                        vm.recentSessions = response;
                    } else if (response && response.sessions) {
                        vm.recentSessions = response.sessions;
                    }
                    console.log('Recent sessions loaded:', vm.recentSessions);
                    
                    // Load session-specific difficulty states for completed sessions
                    loadSessionDifficultyStates();
                })
                .catch(function(error) {
                    console.log('Failed to load recent sessions:', error);
                    // Don't show error for recent sessions
                })
                .finally(function() {
                    vm.loading = false;
                });
        }

        function startInterview() {
            $location.path('/interview');
        }

        function viewProgress() {
            $location.path('/progress');
        }

        function practiceAgain(session) {
            if (!session || !session.id) {
                console.error('Invalid session for practice again');
                vm.error = 'Invalid session selected';
                return;
            }

            console.log('Starting practice again for session with enhanced difficulty inheritance:', session.id);

            // Use enhanced practice session creation with difficulty inheritance
            createPracticeWithEnhancedDifficulty(session);
        }

        function viewSessionDetails(session) {
            if (!session || !session.id) {
                console.error('Invalid session for view details');
                vm.error = 'Invalid session selected';
                return;
            }

            console.log('Navigating to session details for session:', session.id);
            
            try {
                // Navigate to the feedback page which serves as session details
                $location.path('/feedback/' + session.id);
            } catch (error) {
                console.error('Error navigating to session details:', error);
                vm.error = 'Failed to navigate to session details';
            }
        }

        function viewOriginalSession(originalSessionId) {
            if (!originalSessionId) {
                console.error('Invalid original session ID');
                vm.error = 'Invalid original session selected';
                return;
            }

            console.log('Navigating to original session details for session:', originalSessionId);
            
            try {
                // Navigate to the feedback page for the original session
                $location.path('/feedback/' + originalSessionId);
            } catch (error) {
                console.error('Error navigating to original session details:', error);
                vm.error = 'Failed to navigate to original session details';
            }
        }

        function getEstimatedQuestionCount(session) {
            // Return the actual question count if available, otherwise estimate based on duration
            if (session.question_count) {
                return session.question_count;
            }
            
            // Estimate based on duration (same logic as backend)
            if (session.duration <= 15) {
                return 3;
            } else if (session.duration <= 30) {
                return 5;
            } else if (session.duration <= 45) {
                return 8;
            } else {
                return 10;
            }
        }

        function getConsistentDifficultyLabel(difficulty) {
            return DifficultyDisplayService.getDifficultyLabel(
                DifficultyDisplayService.normalizeDifficultyInput(difficulty)
            );
        }

        // ==================== Session-Specific Difficulty Methods ====================

        function loadSessionDifficultyStates() {
            if (!vm.recentSessions || vm.recentSessions.length === 0) {
                return;
            }

            console.log('Loading session-specific difficulty states for dashboard sessions');

            // Load difficulty states for completed sessions
            var completedSessions = vm.recentSessions.filter(function(session) {
                return session.status === 'completed';
            });

            completedSessions.forEach(function(session) {
                UnifiedDifficultyStateService.getSessionDifficultyState(session.id)
                    .then(function(difficultyState) {
                        vm.sessionDifficultyStates[session.id] = difficultyState;
                        
                        // Get display information
                        return UnifiedDifficultyStateService.getDifficultyForDisplay(session.id);
                    })
                    .then(function(displayInfo) {
                        vm.sessionDifficultyDisplays[session.id] = displayInfo;
                        console.log('Loaded difficulty state for session', session.id, displayInfo);
                    })
                    .catch(function(error) {
                        console.warn('Could not load difficulty state for session', session.id, error);
                        // Create fallback display
                        vm.sessionDifficultyDisplays[session.id] = createFallbackDifficultyDisplay(session);
                    });
            });
        }

        function getSessionDifficultyDisplay(sessionId) {
            if (!sessionId || !vm.sessionDifficultyDisplays[sessionId]) {
                return {
                    current: { label: 'Loading...', color: '#6c757d' },
                    initial: { label: 'Loading...', color: '#6c757d' },
                    hasChanged: false,
                    isCompleted: false
                };
            }
            return vm.sessionDifficultyDisplays[sessionId];
        }

        function hasSessionDifficultyChanged(sessionId) {
            var display = getSessionDifficultyDisplay(sessionId);
            return display.hasChanged;
        }

        function createPracticeWithEnhancedDifficulty(session) {
            // Set loading state for this specific session
            vm.loadingStates[session.id] = true;

            console.log('Creating practice session with enhanced difficulty inheritance from session:', session.id);

            // Try to use UnifiedDifficultyStateService for enhanced practice session creation
            UnifiedDifficultyStateService.createPracticeSessionWithDifficulty(session.id, {
                showLoading: false, // We're managing loading state ourselves
                showSuccess: true
            })
            .then(function(response) {
                console.log('Practice session created with enhanced difficulty inheritance:', response);
                
                // Show success message with inheritance information
                if (response.difficulty_validation && response.difficulty_validation.isValid) {
                    var parentInfo = response.difficulty_validation.parentDifficultyInfo;
                    var inheritedDifficulty = response.difficulty_validation.inheritedDifficulty;
                    
                    console.log('Difficulty inheritance successful from dashboard:', {
                        parent: parentInfo,
                        inherited: inheritedDifficulty,
                        wasAdjusted: parentInfo.wasAdjusted
                    });
                }
                
                // Navigate to the new practice session
                $location.path('/interview-chat/' + response.session.id);
            })
            .catch(function(error) {
                console.error('Enhanced practice session creation failed, falling back to standard method:', error);
                
                // Fallback to UnifiedDifficultyStateService
                console.log('Using UnifiedDifficultyStateService for practice session creation');
                
                return UnifiedDifficultyStateService.createPracticeSessionWithDifficulty(session.id, {
                    showLoading: true,
                    showSuccess: true
                }).then(function(response) {
                    console.log('Practice session created successfully:', response);
                    $location.path('/interview-chat/' + response.session.id);
                }).catch(function(error) {
                    console.error('Failed to create practice session:', error);
                    vm.error = 'Failed to create practice session. Please try again.';
                });
            })
            .finally(function() {
                vm.loadingStates[session.id] = false;
            });
        }

        function createFallbackDifficultyDisplay(session) {
            var fallbackDifficulty = session.difficulty_level || 'medium';
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
                isCompleted: true, // Assume completed since it's in dashboard
                changeCount: 0,
                error: 'Using fallback difficulty display'
            };
        }
    }
})();