/**
 * Loading Indicator Component for User Feedback
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .component('loadingIndicator', {
            templateUrl: 'components/loading-indicator/loading-indicator.template.html',
            controller: LoadingIndicatorController,
            bindings: {
                show: '<',
                message: '@',
                type: '@',
                size: '@',
                overlay: '<'
            }
        });

    LoadingIndicatorController.$inject = ['$scope', '$rootScope', '$timeout'];

    function LoadingIndicatorController($scope, $rootScope, $timeout) {
        var vm = this;

        // Public properties
        vm.isVisible = false;
        vm.currentMessage = '';
        vm.currentType = 'spinner';
        vm.currentSize = 'medium';
        vm.showOverlay = false;
        vm.progress = 0;
        vm.progressMessage = '';

        // Public methods
        vm.show = showLoading;
        vm.hide = hideLoading;
        vm.updateProgress = updateProgress;

        // Initialize component
        vm.$onInit = function() {
            setupEventListeners();
            updateFromBindings();
        };

        vm.$onChanges = function(changes) {
            updateFromBindings();
        };

        // ==================== Event Listeners ====================

        function setupEventListeners() {
            // Listen for global loading events
            $rootScope.$on('loading:show', function(event, data) {
                showLoading(data);
            });

            $rootScope.$on('loading:hide', function(event, data) {
                hideLoading(data);
            });

            $rootScope.$on('loading:progress', function(event, data) {
                updateProgress(data.progress, data.message);
            });

            // Listen for API request events
            $rootScope.$on('api:request:start', function(event, data) {
                showLoading({
                    message: data.message || 'Loading...',
                    type: 'spinner',
                    overlay: true
                });
            });

            $rootScope.$on('api:request:end', function(event, data) {
                hideLoading();
            });

            // Listen for specific operation events
            $rootScope.$on('interview:starting', function(event, data) {
                showLoading({
                    message: 'Starting interview session...',
                    type: 'dots',
                    overlay: true
                });
            });

            $rootScope.$on('interview:loading-question', function(event, data) {
                showLoading({
                    message: 'Loading next question...',
                    type: 'spinner',
                    overlay: false
                });
            });

            $rootScope.$on('interview:submitting-answer', function(event, data) {
                showLoading({
                    message: 'Submitting your answer...',
                    type: 'pulse',
                    overlay: true
                });
            });

            $rootScope.$on('feedback:generating', function(event, data) {
                showLoading({
                    message: 'Generating feedback...',
                    type: 'progress',
                    overlay: true
                });
                
                // Simulate progress for feedback generation
                simulateProgress(5000);
            });
        }

        // ==================== Loading Management ====================

        function showLoading(options) {
            options = options || {};
            
            vm.currentMessage = options.message || vm.message || 'Loading...';
            vm.currentType = options.type || vm.type || 'spinner';
            vm.currentSize = options.size || vm.size || 'medium';
            vm.showOverlay = options.overlay !== undefined ? options.overlay : vm.overlay;
            vm.isVisible = true;
            
            // Reset progress
            vm.progress = 0;
            vm.progressMessage = '';

            // Use $timeout to avoid digest cycle conflicts
            if (!$scope.$$phase && !$rootScope.$$phase) {
                $scope.$apply();
            }
        }

        function hideLoading(options) {
            options = options || {};
            
            if (options.delay) {
                $timeout(function() {
                    vm.isVisible = false;
                }, options.delay);
            } else {
                vm.isVisible = false;
                // Use $timeout to avoid digest cycle conflicts
                if (!$scope.$$phase && !$rootScope.$$phase) {
                    $scope.$apply();
                }
            }
        }

        function updateProgress(progress, message) {
            vm.progress = Math.max(0, Math.min(100, progress));
            if (message) {
                vm.progressMessage = message;
            }
            // Use $timeout to avoid digest cycle conflicts
            if (!$scope.$$phase && !$rootScope.$$phase) {
                $scope.$apply();
            }
        }

        function updateFromBindings() {
            if (vm.show !== undefined) {
                vm.isVisible = vm.show;
            }
            if (vm.message) {
                vm.currentMessage = vm.message;
            }
            if (vm.type) {
                vm.currentType = vm.type;
            }
            if (vm.size) {
                vm.currentSize = vm.size;
            }
            if (vm.overlay !== undefined) {
                vm.showOverlay = vm.overlay;
            }
        }

        // ==================== Helper Functions ====================

        function simulateProgress(duration) {
            var startTime = Date.now();
            var interval = 100; // Update every 100ms
            
            var progressInterval = setInterval(function() {
                var elapsed = Date.now() - startTime;
                var progress = Math.min(100, (elapsed / duration) * 100);
                
                updateProgress(progress);
                
                if (progress >= 100) {
                    clearInterval(progressInterval);
                }
            }, interval);
        }

        // ==================== Public API ====================

        // Expose methods for programmatic use
        vm.showSpinner = function(message, overlay) {
            showLoading({
                message: message || 'Loading...',
                type: 'spinner',
                overlay: overlay !== false
            });
        };

        vm.showDots = function(message, overlay) {
            showLoading({
                message: message || 'Processing...',
                type: 'dots',
                overlay: overlay !== false
            });
        };

        vm.showPulse = function(message, overlay) {
            showLoading({
                message: message || 'Working...',
                type: 'pulse',
                overlay: overlay !== false
            });
        };

        vm.showProgress = function(message, overlay) {
            showLoading({
                message: message || 'Processing...',
                type: 'progress',
                overlay: overlay !== false
            });
        };
    }
})();