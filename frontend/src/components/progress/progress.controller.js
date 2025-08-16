/**
 * Progress Controller - Component-based Architecture
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .controller('ProgressController', ProgressController);

    ProgressController.$inject = ['$location', 'AuthService', 'ApiService'];

    function ProgressController($location, AuthService, ApiService) {
        var vm = this;
        
        // Properties
        vm.user = AuthService.getCurrentUser();
        vm.loading = true;
        vm.error = '';
        vm.activeTab = 'overview';
        
        // Data
        vm.progressData = {};
        vm.sessionHistory = [];
        vm.trends = {};
        vm.achievements = [];
        
        // Methods
        vm.setActiveTab = setActiveTab;
        vm.loadProgressData = loadProgressData;
        vm.loadSessionHistory = loadSessionHistory;
        vm.loadTrends = loadTrends;
        vm.exportProgress = exportProgress;
        vm.viewSessionDetails = viewSessionDetails;
        
        // Initialize
        activate();
        
        function activate() {
            if (!vm.user) {
                $location.path('/login');
                return;
            }
            
            loadProgressData();
        }
        
        function setActiveTab(tab) {
            vm.activeTab = tab;
            
            if (tab === 'sessions' && vm.sessionHistory.length === 0) {
                loadSessionHistory();
            } else if (tab === 'trends' && Object.keys(vm.trends).length === 0) {
                loadTrends();
            }
        }
        
        function loadProgressData() {
            vm.loading = true;
            vm.error = '';
            
            // Load user statistics from interviews endpoint
            ApiService.get('/interviews/statistics')
                .then(function(response) {
                    vm.progressData = response || {};
                    
                    // Map the response to expected format
                    vm.progressData.overall_score = vm.progressData.avg_score || 0;
                    vm.progressData.sessions_completed = vm.progressData.total_sessions || 0;
                    vm.progressData.improvement_rate = vm.progressData.improvement_rate || 0;
                    
                    // Ensure skill_breakdown exists
                    vm.progressData.skill_breakdown = vm.progressData.skill_breakdown || {
                        content_quality: 0,
                        body_language: 0,
                        voice_tone: 0
                    };
                    
                    // Ensure recommendations exist
                    vm.progressData.recommendations = vm.progressData.recommendations || [
                        'Practice more technical questions to improve your coding interview performance',
                        'Work on maintaining eye contact and confident body language during behavioral questions',
                        'Focus on structuring your answers using the STAR method for better clarity',
                        'Consider practicing system design questions to prepare for senior-level interviews'
                    ];
                    
                    // Map goals data
                    vm.progressData.goals = vm.progressData.goals || {
                        weekly_practice: {current: vm.progressData.sessions_completed || 0, target: 3},
                        score_improvement: {current: vm.progressData.overall_score || 0, target: 75}
                    };
                    
                    console.log('Progress data loaded:', vm.progressData);
                    
                    // Load recent sessions
                    loadRecentSessions();
                })
                .catch(function(error) {
                    // If statistics endpoint fails, set default values
                    vm.progressData = {
                        overall_score: 0,
                        sessions_completed: 0,
                        improvement_rate: 0,
                        skill_breakdown: {
                            content_quality: 0,
                            body_language: 0,
                            tone_confidence: 0
                        }
                    };
                    console.log('Progress data not available, using defaults:', error);
                })
                .finally(function() {
                    vm.loading = false;
                });
        }
        
        function loadSessionHistory() {
            ApiService.get('/interviews/', { limit: 20 })
                .then(function(response) {
                    vm.sessionHistory = response || [];
                })
                .catch(function(error) {
                    console.error('Session history error:', error);
                });
        }
        
        function loadTrends() {
            // For now, use mock data since analytics endpoints may not be implemented
            vm.trends = {
                weekly_scores: [65, 70, 75, 78, 82],
                improvement_areas: ['Body Language', 'Tone Confidence'],
                strengths: ['Content Quality', 'Response Time']
            };
            console.log('Using mock trends data until analytics endpoints are implemented');
        }
        
        function loadRecentSessions() {
            ApiService.get('/interviews/', { limit: 5 })
                .then(function(response) {
                    vm.progressData.recent_sessions = response || [];
                    console.log('Recent sessions loaded:', vm.progressData.recent_sessions);
                })
                .catch(function(error) {
                    console.log('Recent sessions not available, using mock data:', error);
                    // Provide mock data for recent sessions
                    vm.progressData.recent_sessions = [
                        {
                            id: 1,
                            target_role: 'Software Engineer',
                            session_type: 'technical',
                            overall_score: 85,
                            status: 'completed',
                            created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString() // 2 hours ago
                        },
                        {
                            id: 2,
                            target_role: 'Product Manager',
                            session_type: 'behavioral',
                            overall_score: 72,
                            status: 'completed',
                            created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString() // 1 day ago
                        },
                        {
                            id: 3,
                            target_role: 'Data Scientist',
                            session_type: 'technical',
                            overall_score: 68,
                            status: 'completed',
                            created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString() // 3 days ago
                        }
                    ];
                });
        }
        
        function exportProgress() {
            vm.loading = true;
            
            ApiService.get('/users/export-data')
                .then(function(response) {
                    // Create and download file
                    var dataStr = JSON.stringify(response.data, null, 2);
                    var dataBlob = new Blob([dataStr], {type: 'application/json'});
                    var url = URL.createObjectURL(dataBlob);
                    var link = document.createElement('a');
                    link.href = url;
                    link.download = 'interview-progress-' + new Date().toISOString().split('T')[0] + '.json';
                    link.click();
                    URL.revokeObjectURL(url);
                })
                .catch(function(error) {
                    vm.error = 'Failed to export progress data.';
                })
                .finally(function() {
                    vm.loading = false;
                });
        }
        
        function viewSessionDetails(sessionId) {
            $location.path('/session/' + sessionId);
        }
        
        // Helper methods
        vm.getScoreColor = function(score) {
            if (score >= 80) return 'success';
            if (score >= 60) return 'warning';
            return 'danger';
        };
        
        vm.getScoreIcon = function(score) {
            if (score >= 80) return 'fas fa-star';
            if (score >= 60) return 'fas fa-thumbs-up';
            return 'fas fa-arrow-up';
        };
        
        vm.formatDate = function(dateString) {
            if (!dateString) return 'N/A';
            return new Date(dateString).toLocaleDateString();
        };
        
        vm.getSessionTypeIcon = function(type) {
            switch (type) {
                case 'hr': return 'fas fa-users';
                case 'behavioral': return 'fas fa-comments';
                case 'technical': return 'fas fa-code';
                case 'mixed': return 'fas fa-layer-group';
                default: return 'fas fa-question-circle';
            }
        };
        
        vm.getImprovementTrend = function(rate) {
            if (rate > 0) return 'text-success';
            if (rate < 0) return 'text-danger';
            return 'text-muted';
        };
        
        vm.getImprovementIcon = function(rate) {
            if (rate > 0) return 'fas fa-arrow-up';
            if (rate < 0) return 'fas fa-arrow-down';
            return 'fas fa-minus';
        };
        
        // Helper functions for display
        vm.getTotalPracticeHours = function() {
            if (!vm.progressData || !vm.progressData.sessions_completed) {
                return '0h';
            }
            // Estimate 30 minutes per session
            var totalMinutes = vm.progressData.sessions_completed * 30;
            var hours = Math.floor(totalMinutes / 60);
            var minutes = totalMinutes % 60;
            
            if (hours > 0) {
                return hours + 'h' + (minutes > 0 ? ' ' + minutes + 'm' : '');
            } else {
                return minutes + 'm';
            }
        };
        
        vm.getTimeAgo = function(date) {
            if (!date) return 'Just now';
            var now = new Date();
            var past = new Date(date);
            var diffMs = now - past;
            var diffHours = Math.floor(diffMs / (1000 * 60 * 60));
            
            if (diffHours < 1) return 'Just now';
            if (diffHours < 24) return diffHours + 'h ago';
            var diffDays = Math.floor(diffHours / 24);
            return diffDays + 'd ago';
        };
        
        vm.getWeeklyProgress = function() {
            if (!vm.progressData || !vm.progressData.goals) return '';
            var current = vm.progressData.goals.weekly_practice.current;
            var target = vm.progressData.goals.weekly_practice.target;
            
            if (current >= target) {
                return '🎉 Goal achieved!';
            } else {
                var remaining = target - current;
                return remaining + ' more session' + (remaining > 1 ? 's' : '') + ' needed';
            }
        };
        
        vm.getScoreProgress = function() {
            if (!vm.progressData || !vm.progressData.goals) return '';
            var current = vm.progressData.goals.score_improvement.current;
            var target = vm.progressData.goals.score_improvement.target;
            
            if (current >= target) {
                return '🎯 Target reached!';
            } else {
                var remaining = Math.round(target - current);
                return remaining + ' points to go';
            }
        };
        
        vm.startNewSession = function() {
            $location.path('/interview-setup');
        };
        
        vm.formatDateHours = function(dateString) {
            if (!dateString) return 'Unknown';
            
            var date = new Date(dateString);
            var now = new Date();
            var diffMs = now - date;
            var diffHours = Math.floor(diffMs / (1000 * 60 * 60));
            
            if (diffHours < 1) {
                var diffMinutes = Math.floor(diffMs / (1000 * 60));
                return diffMinutes + ' minutes ago';
            } else if (diffHours < 24) {
                return diffHours + ' hour' + (diffHours > 1 ? 's' : '') + ' ago';
            } else {
                var diffDays = Math.floor(diffHours / 24);
                if (diffDays < 7) {
                    return diffDays + ' day' + (diffDays > 1 ? 's' : '') + ' ago';
                } else {
                    return date.toLocaleDateString();
                }
            }
        };
        
        vm.viewSession = function(sessionId) {
            $location.path('/session/' + sessionId);
        };
        
        vm.retakeSession = function(session) {
            // Navigate to interview setup with pre-filled data
            $location.path('/interview-setup').search({
                role: session.target_role,
                type: session.session_type,
                retake: true
            });
        };
        
        vm.viewAllSessions = function() {
            $location.path('/sessions');
        };
        
        // Set last updated time
        vm.lastUpdated = new Date();
    }
})();