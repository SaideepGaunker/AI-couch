/**
 * Dashboard Controller - Component-based Architecture
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .controller('DashboardController', DashboardController);

    DashboardController.$inject = ['$location', 'AuthService', 'ApiService'];

    function DashboardController($location, AuthService, ApiService) {
        var vm = this;

        // Properties
        vm.user = AuthService.getCurrentUser() || {};
        vm.stats = {
            total_sessions: 0,
            total_time: 0,
            avg_score: 0,
            improvement: 0,
            sessions_this_week: 0,
            streak: 0
        };
        vm.recentSessions = [];
        vm.progressData = [];
        vm.loading = true;
        vm.error = '';

        // Methods
        vm.loadDashboardData = loadDashboardData;
        vm.startInterview = startInterview;
        vm.viewProgress = viewProgress;

        // Initialize
        activate();

        function activate() {
            // Check authentication
            if (!AuthService.isAuthenticated()) {
                console.log('User not authenticated in dashboard, redirecting to login');
                $location.path('/login');
                return;
            }
            
            console.log('Dashboard controller activated for user:', vm.user);
            loadDashboardData();
        }

        function loadDashboardData() {
            vm.loading = true;
            vm.error = '';

            // Load user session statistics
            ApiService.get('/interviews/statistics')
                .then(function(response) {
                    if (response) {
                        // Map backend response to frontend stats structure
                        vm.stats.total_sessions = response.total_sessions || 0;
                        vm.stats.total_time = response.practice_hours || 0; // Map practice_hours to total_time
                        vm.stats.avg_score = response.avg_score || 0;
                        vm.stats.improvement = response.improvement_rate || 0; // Map improvement_rate to improvement
                        vm.stats.sessions_this_week = response.sessions_this_week || 0;
                        vm.stats.streak = response.streak || 0;
                        
                        console.log('Dashboard stats loaded:', vm.stats);
                        console.log('Backend response:', response);
                    }
                })
                .catch(function(error) {
                    console.log('Failed to load stats:', error);
                    // Don't show error for stats, just use defaults
                });

            // Load recent sessions
            ApiService.get('/interviews/', { limit: 5, skip: 0 })
                .then(function(response) {
                    if (response && Array.isArray(response)) {
                        vm.recentSessions = response;
                    } else if (response && response.sessions) {
                        vm.recentSessions = response.sessions;
                    }
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
    }
})();