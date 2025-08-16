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
                        vm.stats = angular.extend(vm.stats, response);
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