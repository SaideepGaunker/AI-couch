/**
 * Progress Indicator Component for Long-Running Operations
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .component('progressIndicator', {
            templateUrl: 'components/progress-indicator/progress-indicator.template.html',
            controller: ProgressIndicatorController,
            bindings: {
                show: '<',
                progress: '<',
                message: '@',
                steps: '<',
                currentStep: '<',
                type: '@',
                size: '@'
            }
        });

    ProgressIndicatorController.$inject = ['$scope', '$rootScope', '$timeout'];

    function ProgressIndicatorController($scope, $rootScope, $timeout) {
        var vm = this;

        // Public properties
        vm.isVisible = false;
        vm.currentProgress = 0;
        vm.currentMessage = '';
        vm.currentSteps = [];
        vm.currentStepIndex = 0;
        vm.progressType = 'linear';
        vm.progressSize = 'medium';
        vm.estimatedTimeRemaining = null;
        vm.startTime = null;

        // Public methods
        vm.updateProgress = updateProgress;
        vm.updateStep = updateStep;
        vm.complete = complete;
        vm.cancel = cancel;

        // Initialize component
        vm.$onInit = function() {
            setupEventListeners();
            updateFromBindings();
        };

        vm.$onChanges = function(changes) {
            updateFromBindings();
            
            if (changes.progress && changes.progress.currentValue !== changes.progress.previousValue) {
                updateProgress(changes.progress.currentValue);
            }
            
            if (changes.currentStep && changes.currentStep.currentValue !== changes.currentStep.previousValue) {
                updateStep(changes.currentStep.currentValue);
            }
        };

        // ==================== Event Listeners ====================

        function setupEventListeners() {
            // Listen for progress events
            $rootScope.$on('progress:show', function(event, data) {
                showProgress(data);
            });

            $rootScope.$on('progress:hide', function(event, data) {
                hideProgress(data);
            });

            $rootScope.$on('progress:update', function(event, data) {
                updateProgress(data.progress, data.message);
            });

            $rootScope.$on('progress:step', function(event, data) {
                updateStep(data.step, data.message);
            });

            $rootScope.$on('progress:complete', function(event, data) {
                complete(data);
            });

            // Listen for specific operation progress
            $rootScope.$on('interview:generation:progress', function(event, data) {
                showProgress({
                    type: 'steps',
                    steps: [
                        'Analyzing role requirements',
                        'Generating questions',
                        'Validating content',
                        'Preparing session'
                    ],
                    message: 'Preparing your interview...'
                });
                updateStep(data.step || 0, data.message);
            });

            $rootScope.$on('feedback:generation:progress', function(event, data) {
                showProgress({
                    type: 'linear',
                    message: 'Analyzing your performance...'
                });
                updateProgress(data.progress || 0, data.message);
            });

            $rootScope.$on('upload:progress', function(event, data) {
                showProgress({
                    type: 'linear',
                    message: 'Uploading file...'
                });
                updateProgress(data.progress || 0, data.message);
            });
        }

        // ==================== Progress Management ====================

        function showProgress(options) {
            options = options || {};
            
            vm.progressType = options.type || vm.type || 'linear';
            vm.progressSize = options.size || vm.size || 'medium';
            vm.currentMessage = options.message || vm.message || 'Processing...';
            vm.currentSteps = options.steps || vm.steps || [];
            vm.currentProgress = options.progress || 0;
            vm.currentStepIndex = options.currentStep || 0;
            vm.startTime = new Date();
            vm.estimatedTimeRemaining = null;
            
            vm.isVisible = true;
            // Use $timeout to avoid digest cycle conflicts
            if (!$scope.$$phase && !$rootScope.$$phase) {
                $scope.$apply();
            }
        }

        function hideProgress(options) {
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
            if (progress !== undefined) {
                vm.currentProgress = Math.max(0, Math.min(100, progress));
                
                // Calculate estimated time remaining
                if (vm.startTime && progress > 0) {
                    var elapsed = new Date() - vm.startTime;
                    var totalEstimated = (elapsed / progress) * 100;
                    vm.estimatedTimeRemaining = Math.max(0, totalEstimated - elapsed);
                }
            }
            
            if (message) {
                vm.currentMessage = message;
            }
            
            // Use $timeout to avoid digest cycle conflicts
            if (!$scope.$$phase && !$rootScope.$$phase) {
                $scope.$apply();
            }
        }

        function updateStep(stepIndex, message) {
            if (stepIndex !== undefined) {
                vm.currentStepIndex = Math.max(0, Math.min(vm.currentSteps.length - 1, stepIndex));
                
                // Calculate progress based on steps
                if (vm.currentSteps.length > 0) {
                    vm.currentProgress = ((vm.currentStepIndex + 1) / vm.currentSteps.length) * 100;
                }
            }
            
            if (message) {
                vm.currentMessage = message;
            } else if (vm.currentSteps[vm.currentStepIndex]) {
                vm.currentMessage = vm.currentSteps[vm.currentStepIndex];
            }
            
            // Use $timeout to avoid digest cycle conflicts
            if (!$scope.$$phase && !$rootScope.$$phase) {
                $scope.$apply();
            }
        }

        function complete(options) {
            options = options || {};
            
            vm.currentProgress = 100;
            vm.currentMessage = options.message || 'Complete!';
            
            // Show completion state briefly before hiding
            $timeout(function() {
                hideProgress({ delay: options.hideDelay || 1000 });
            }, 500);
        }

        function cancel() {
            vm.isVisible = false;
            $rootScope.$broadcast('progress:cancelled');
        }

        function updateFromBindings() {
            if (vm.show !== undefined) {
                vm.isVisible = vm.show;
            }
            if (vm.progress !== undefined) {
                vm.currentProgress = vm.progress;
            }
            if (vm.message) {
                vm.currentMessage = vm.message;
            }
            if (vm.steps) {
                vm.currentSteps = vm.steps;
            }
            if (vm.currentStep !== undefined) {
                vm.currentStepIndex = vm.currentStep;
            }
            if (vm.type) {
                vm.progressType = vm.type;
            }
            if (vm.size) {
                vm.progressSize = vm.size;
            }
        }

        // ==================== Helper Functions ====================

        function formatTimeRemaining(milliseconds) {
            if (!milliseconds || milliseconds <= 0) return null;
            
            var seconds = Math.ceil(milliseconds / 1000);
            
            if (seconds < 60) {
                return seconds + ' second' + (seconds !== 1 ? 's' : '');
            } else {
                var minutes = Math.ceil(seconds / 60);
                return minutes + ' minute' + (minutes !== 1 ? 's' : '');
            }
        }

        // ==================== Public API ====================

        vm.getFormattedTimeRemaining = function() {
            return formatTimeRemaining(vm.estimatedTimeRemaining);
        };

        vm.getProgressPercentage = function() {
            return Math.round(vm.currentProgress);
        };

        vm.getCurrentStepName = function() {
            return vm.currentSteps[vm.currentStepIndex] || '';
        };

        vm.isStepComplete = function(index) {
            return index < vm.currentStepIndex;
        };

        vm.isStepActive = function(index) {
            return index === vm.currentStepIndex;
        };

        vm.isStepPending = function(index) {
            return index > vm.currentStepIndex;
        };

        // Expose convenience methods
        vm.showLinearProgress = function(message) {
            showProgress({
                type: 'linear',
                message: message || 'Processing...'
            });
        };

        vm.showStepProgress = function(steps, message) {
            showProgress({
                type: 'steps',
                steps: steps,
                message: message || 'Processing...'
            });
        };

        vm.showCircularProgress = function(message) {
            showProgress({
                type: 'circular',
                message: message || 'Processing...'
            });
        };
    }
})();