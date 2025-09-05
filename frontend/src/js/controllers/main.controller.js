/**
 * Main Controller for home page
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .controller('MainController', MainController);

    MainController.$inject = ['$location', '$scope', '$rootScope', '$timeout', 'AuthService', 'ErrorHandlingService'];

    function MainController($location, $scope, $rootScope, $timeout, AuthService, ErrorHandlingService) {
        var vm = this;
        
        vm.title = 'Interview Prep AI Coach';
        vm.subtitle = 'Master your interviews with AI-powered coaching';
        vm.isAuthenticated = AuthService.isAuthenticated;
        
        vm.features = [
            {
                title: 'Realistic Simulations',
                description: 'Practice with AI-generated questions tailored to your role',
                icon: 'fas fa-comments'
            },
            {
                title: 'Body Language Analysis',
                description: 'Get real-time feedback on your posture and expressions',
                icon: 'fas fa-video'
            },
            {
                title: 'Tone & Confidence Scoring',
                description: 'Improve your vocal delivery and confidence',
                icon: 'fas fa-microphone'
            },
            {
                title: 'Progress Tracking',
                description: 'Monitor your improvement over time',
                icon: 'fas fa-chart-line'
            }
        ];
        
        vm.getStarted = function() {
            if (AuthService.isAuthenticated()) {
                $location.path('/dashboard');
            } else {
                $location.path('/register');
            }
        };
        
        vm.startPractice = function() {
            if (AuthService.isAuthenticated()) {
                $location.path('/interview');
            } else {
                $location.path('/login');
            }
        };
        
        vm.logout = function() {
            if (confirm('Are you sure you want to logout?')) {
                AuthService.logout();
            }
        };
        
        // Error handling properties
        vm.globalError = null;
        vm.isLoading = false;
        vm.networkStatus = 'online';
        
        // Error handling methods
        vm.dismissGlobalError = dismissGlobalError;
        vm.retryLastAction = retryLastAction;
        vm.reportError = reportError;
        
        // Initialize controller
        function activate() {
            setupErrorHandling();
            checkNetworkStatus();
        }
        
        function setupErrorHandling() {
            // Listen for global errors
            $rootScope.$on('error:occurred', function(event, errorInfo) {
                vm.globalError = errorInfo;
                // Use $timeout to avoid $rootScope:inprog errors
                $timeout(function() {
                    // This will trigger a digest cycle safely
                }, 0);
            });
            
            // Listen for loading states
            $rootScope.$on('loading:show', function(event, data) {
                vm.isLoading = true;
                $scope.$apply();
            });
            
            $rootScope.$on('loading:hide', function(event, data) {
                vm.isLoading = false;
                $scope.$apply();
            });
            
            // Listen for network status changes
            $rootScope.$on('network:online', function() {
                vm.networkStatus = 'online';
                $rootScope.$broadcast('success:occurred', {
                    message: 'Connection restored'
                });
                $scope.$apply();
            });
            
            $rootScope.$on('network:offline', function() {
                vm.networkStatus = 'offline';
                $rootScope.$broadcast('warning:occurred', {
                    message: 'Connection lost. Some features may not work.'
                });
                $scope.$apply();
            });
            
            // Listen for feature disabled events
            $rootScope.$on('feature:disabled', function(event, data) {
                $rootScope.$broadcast('warning:occurred', {
                    message: 'Feature "' + data.feature + '" is temporarily unavailable: ' + data.reason
                });
            });
            
            // Listen for feature enabled events
            $rootScope.$on('feature:enabled', function(event, data) {
                $rootScope.$broadcast('info:occurred', {
                    message: 'Feature "' + data.feature + '" is now available'
                });
            });
        }
        
        function checkNetworkStatus() {
            vm.networkStatus = navigator.onLine ? 'online' : 'offline';
        }
        
        function dismissGlobalError() {
            vm.globalError = null;
        }
        
        function retryLastAction() {
            if (vm.globalError && vm.globalError.retryAction) {
                vm.globalError.retryAction();
                vm.globalError = null;
            } else {
                // Default retry action
                window.location.reload();
            }
        }
        
        function reportError() {
            if (vm.globalError) {
                // In a real app, this would send error report to backend
                console.log('Error report:', vm.globalError);
                
                $rootScope.$broadcast('info:occurred', {
                    message: 'Error report sent. Thank you for helping us improve!'
                });
                
                vm.globalError = null;
            }
        }
        
        // Expose error handling service methods
        vm.getErrorStats = function() {
            return ErrorHandlingService.getErrorStats();
        };
        
        vm.isFeatureEnabled = function(featureName) {
            return ErrorHandlingService.isFeatureEnabled(featureName);
        };
        
        activate();
    }
})();