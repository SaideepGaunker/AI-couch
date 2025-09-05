/**
 * Toast Notification Component for Error Messages and User Feedback
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .component('toastNotification', {
            templateUrl: 'components/toast-notification/toast-notification.template.html',
            controller: ToastNotificationController,
            bindings: {}
        });

    ToastNotificationController.$inject = ['$scope', '$timeout', '$rootScope'];

    function ToastNotificationController($scope, $timeout, $rootScope) {
        var vm = this;

        // Public properties
        vm.toasts = [];
        vm.maxToasts = 5;

        // Public methods
        vm.dismissToast = dismissToast;
        vm.dismissAllToasts = dismissAllToasts;
        vm.retryAction = retryAction;

        // Initialize component
        vm.$onInit = function() {
            setupEventListeners();
        };

        // ==================== Event Listeners ====================

        function setupEventListeners() {
            // Listen for toast show events
            $rootScope.$on('toast:show', function(event, toastData) {
                showToast(toastData);
            });

            // Listen for error events
            $rootScope.$on('error:occurred', function(event, errorInfo) {
                var toast = {
                    type: 'error',
                    message: errorInfo.userFriendlyMessage || 'An error occurred',
                    suggestions: errorInfo.recoverySuggestions || [],
                    duration: 5000,
                    dismissible: true,
                    showRetry: errorInfo.context && errorInfo.context.retryable !== false
                };
                showToast(toast);
            });

            // Listen for success events
            $rootScope.$on('success:occurred', function(event, successInfo) {
                var toast = {
                    type: 'success',
                    message: successInfo.message || 'Operation completed successfully',
                    duration: 3000,
                    dismissible: true
                };
                showToast(toast);
            });

            // Listen for warning events
            $rootScope.$on('warning:occurred', function(event, warningInfo) {
                var toast = {
                    type: 'warning',
                    message: warningInfo.message || 'Warning',
                    duration: 4000,
                    dismissible: true
                };
                showToast(toast);
            });

            // Listen for info events
            $rootScope.$on('info:occurred', function(event, infoData) {
                var toast = {
                    type: 'info',
                    message: infoData.message || 'Information',
                    duration: 3000,
                    dismissible: true
                };
                showToast(toast);
            });
        }

        // ==================== Toast Management ====================

        function showToast(toastData) {
            var toast = {
                id: generateToastId(),
                type: toastData.type || 'info',
                message: toastData.message || '',
                suggestions: toastData.suggestions || [],
                duration: toastData.duration || 3000,
                dismissible: toastData.dismissible !== false,
                showRetry: toastData.showRetry || false,
                retryAction: toastData.retryAction,
                timestamp: new Date().toISOString(),
                visible: true
            };

            // Add toast to the beginning of the array
            vm.toasts.unshift(toast);

            // Limit number of toasts
            if (vm.toasts.length > vm.maxToasts) {
                vm.toasts = vm.toasts.slice(0, vm.maxToasts);
            }

            // Auto-dismiss after duration
            if (toast.duration > 0) {
                $timeout(function() {
                    dismissToast(toast.id);
                }, toast.duration);
            }

            // Changes will be applied automatically by Angular data binding
            if (!$scope.$$phase) {
                // Use $timeout to avoid digest cycle conflicts

            }
        }

        function dismissToast(toastId) {
            var index = vm.toasts.findIndex(function(toast) {
                return toast.id === toastId;
            });

            if (index !== -1) {
                vm.toasts[index].visible = false;
                
                // Remove from array after animation
                $timeout(function() {
                    vm.toasts.splice(index, 1);
                }, 300);
            }
        }

        function dismissAllToasts() {
            vm.toasts.forEach(function(toast) {
                toast.visible = false;
            });

            $timeout(function() {
                vm.toasts = [];
            }, 300);
        }

        function retryAction(toast) {
            if (toast.retryAction && typeof toast.retryAction === 'function') {
                toast.retryAction();
            } else {
                // Default retry action - reload page
                window.location.reload();
            }
            
            dismissToast(toast.id);
        }

        // ==================== Helper Functions ====================

        function generateToastId() {
            return 'toast_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        }

        // ==================== Public API ====================

        // Expose methods for programmatic use
        vm.showSuccess = function(message, duration) {
            showToast({
                type: 'success',
                message: message,
                duration: duration || 3000
            });
        };

        vm.showError = function(message, suggestions, duration) {
            showToast({
                type: 'error',
                message: message,
                suggestions: suggestions || [],
                duration: duration || 5000
            });
        };

        vm.showWarning = function(message, duration) {
            showToast({
                type: 'warning',
                message: message,
                duration: duration || 4000
            });
        };

        vm.showInfo = function(message, duration) {
            showToast({
                type: 'info',
                message: message,
                duration: duration || 3000
            });
        };
    }
})();