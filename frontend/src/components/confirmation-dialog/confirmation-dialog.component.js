/**
 * Confirmation Dialog Component for Destructive Actions
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .component('confirmationDialog', {
            templateUrl: 'components/confirmation-dialog/confirmation-dialog.template.html',
            controller: ConfirmationDialogController,
            bindings: {}
        });

    ConfirmationDialogController.$inject = ['$scope', '$rootScope', '$timeout'];

    function ConfirmationDialogController($scope, $rootScope, $timeout) {
        var vm = this;

        // Public properties
        vm.isVisible = false;
        vm.currentDialog = null;
        vm.isProcessing = false;

        // Public methods
        vm.confirm = confirm;
        vm.cancel = cancel;
        vm.dismiss = dismiss;

        // Initialize component
        vm.$onInit = function() {
            setupEventListeners();
        };

        // ==================== Event Listeners ====================

        function setupEventListeners() {
            // Listen for confirmation dialog requests
            $rootScope.$on('confirmation:show', function(event, dialogData) {
                showDialog(dialogData);
            });

            // Listen for dialog dismiss events
            $rootScope.$on('confirmation:dismiss', function(event, data) {
                dismiss();
            });

            // Handle escape key
            document.addEventListener('keydown', function(event) {
                if (event.key === 'Escape' && vm.isVisible) {
                    cancel();
                    $scope.$apply();
                }
            });
        }

        // ==================== Dialog Management ====================

        function showDialog(dialogData) {
            vm.currentDialog = {
                id: generateDialogId(),
                title: dialogData.title || 'Confirm Action',
                message: dialogData.message || 'Are you sure you want to proceed?',
                type: dialogData.type || 'warning', // warning, danger, info
                confirmText: dialogData.confirmText || 'Confirm',
                cancelText: dialogData.cancelText || 'Cancel',
                confirmAction: dialogData.confirmAction,
                cancelAction: dialogData.cancelAction,
                data: dialogData.data || {},
                showCancel: dialogData.showCancel !== false,
                confirmButtonClass: getConfirmButtonClass(dialogData.type),
                icon: getDialogIcon(dialogData.type),
                details: dialogData.details || null,
                timestamp: new Date().toISOString()
            };

            vm.isVisible = true;
            vm.isProcessing = false;

            // Focus management
            $timeout(function() {
                var confirmButton = document.querySelector('.confirmation-dialog .btn-confirm');
                if (confirmButton) {
                    confirmButton.focus();
                }
            }, 100);

            $scope.$apply();
        }

        function confirm() {
            if (vm.isProcessing) return;

            vm.isProcessing = true;

            var dialog = vm.currentDialog;
            var result = {
                confirmed: true,
                data: dialog.data,
                timestamp: new Date().toISOString()
            };

            // Execute confirm action if provided
            if (dialog.confirmAction && typeof dialog.confirmAction === 'function') {
                try {
                    var actionResult = dialog.confirmAction(result);
                    
                    // Handle promise-based actions
                    if (actionResult && typeof actionResult.then === 'function') {
                        actionResult
                            .then(function(response) {
                                handleConfirmSuccess(response);
                            })
                            .catch(function(error) {
                                handleConfirmError(error);
                            });
                    } else {
                        handleConfirmSuccess(actionResult);
                    }
                } catch (error) {
                    handleConfirmError(error);
                }
            } else {
                // No action provided, just close dialog
                handleConfirmSuccess();
            }
        }

        function cancel() {
            if (vm.isProcessing) return;

            var dialog = vm.currentDialog;
            var result = {
                confirmed: false,
                cancelled: true,
                data: dialog.data,
                timestamp: new Date().toISOString()
            };

            // Execute cancel action if provided
            if (dialog.cancelAction && typeof dialog.cancelAction === 'function') {
                try {
                    dialog.cancelAction(result);
                } catch (error) {
                    console.error('Error in cancel action:', error);
                }
            }

            // Broadcast cancel event
            $rootScope.$broadcast('confirmation:cancelled', result);

            dismiss();
        }

        function dismiss() {
            vm.isVisible = false;
            vm.currentDialog = null;
            vm.isProcessing = false;
        }

        function handleConfirmSuccess(response) {
            var result = {
                confirmed: true,
                success: true,
                response: response,
                data: vm.currentDialog.data,
                timestamp: new Date().toISOString()
            };

            // Broadcast success event
            $rootScope.$broadcast('confirmation:confirmed', result);

            // Show success message if action was successful
            if (response && response.message) {
                $rootScope.$broadcast('success:occurred', {
                    message: response.message
                });
            }

            dismiss();
        }

        function handleConfirmError(error) {
            vm.isProcessing = false;

            var result = {
                confirmed: true,
                success: false,
                error: error,
                data: vm.currentDialog.data,
                timestamp: new Date().toISOString()
            };

            // Broadcast error event
            $rootScope.$broadcast('confirmation:error', result);

            // Show error message
            $rootScope.$broadcast('error:occurred', {
                userFriendlyMessage: 'Action failed: ' + (error.message || 'Unknown error'),
                recoverySuggestions: ['Try again', 'Contact support if problem persists'],
                context: { type: 'confirmation_action_failed', error: error }
            });

            // Keep dialog open so user can try again or cancel
        }

        // ==================== Helper Functions ====================

        function generateDialogId() {
            return 'dialog_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        }

        function getConfirmButtonClass(type) {
            var classes = {
                'warning': 'btn-warning',
                'danger': 'btn-danger',
                'info': 'btn-primary',
                'success': 'btn-success'
            };
            return classes[type] || 'btn-primary';
        }

        function getDialogIcon(type) {
            var icons = {
                'warning': 'fas fa-exclamation-triangle',
                'danger': 'fas fa-exclamation-circle',
                'info': 'fas fa-info-circle',
                'success': 'fas fa-check-circle'
            };
            return icons[type] || 'fas fa-question-circle';
        }

        // ==================== Public API ====================

        // Expose methods for programmatic use
        vm.showWarning = function(message, confirmAction, options) {
            options = options || {};
            showDialog({
                type: 'warning',
                title: options.title || 'Warning',
                message: message,
                confirmAction: confirmAction,
                confirmText: options.confirmText || 'Proceed',
                ...options
            });
        };

        vm.showDanger = function(message, confirmAction, options) {
            options = options || {};
            showDialog({
                type: 'danger',
                title: options.title || 'Danger',
                message: message,
                confirmAction: confirmAction,
                confirmText: options.confirmText || 'Delete',
                ...options
            });
        };

        vm.showInfo = function(message, confirmAction, options) {
            options = options || {};
            showDialog({
                type: 'info',
                title: options.title || 'Information',
                message: message,
                confirmAction: confirmAction,
                confirmText: options.confirmText || 'OK',
                ...options
            });
        };
    }
})();