/**
 * Form Error Display Component
 * Reusable component for displaying form validation errors with consistent styling
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .component('formErrorDisplay', {
            templateUrl: 'components/form-error-display/form-error-display.template.html',
            controller: FormErrorDisplayController,
            controllerAs: 'vm',
            bindings: {
                errors: '<',           // Object containing field errors
                fieldName: '@',        // Specific field name to display error for
                errorType: '@',        // Type of error display: 'field', 'summary', 'inline'
                showIcon: '<',         // Whether to show error icon (default: true)
                dismissible: '<',      // Whether error can be dismissed (default: false)
                onDismiss: '&'         // Callback when error is dismissed
            }
        });

    FormErrorDisplayController.$inject = ['$log'];

    function FormErrorDisplayController($log) {
        var vm = this;

        // Component properties
        vm.displayErrors = [];
        vm.hasErrors = false;

        // Public methods
        vm.$onInit = onInit;
        vm.$onChanges = onChanges;
        vm.dismissError = dismissError;
        vm.getErrorClass = getErrorClass;
        vm.getIconClass = getIconClass;

        /**
         * Component initialization
         */
        function onInit() {
            // Set default values
            if (vm.errorType === undefined) {
                vm.errorType = 'field';
            }
            if (vm.showIcon === undefined) {
                vm.showIcon = true;
            }
            if (vm.dismissible === undefined) {
                vm.dismissible = false;
            }

            updateDisplayErrors();
        }

        /**
         * Handle input changes
         */
        function onChanges(changes) {
            if (changes.errors || changes.fieldName) {
                updateDisplayErrors();
            }
        }

        /**
         * Update the errors to display based on current inputs
         */
        function updateDisplayErrors() {
            vm.displayErrors = [];
            vm.hasErrors = false;

            if (!vm.errors || typeof vm.errors !== 'object') {
                return;
            }

            if (vm.errorType === 'field' && vm.fieldName) {
                // Display error for specific field
                if (vm.errors[vm.fieldName]) {
                    vm.displayErrors = [{
                        field: vm.fieldName,
                        message: vm.errors[vm.fieldName],
                        type: 'field'
                    }];
                    vm.hasErrors = true;
                }
            } else if (vm.errorType === 'summary') {
                // Display all errors as summary
                vm.displayErrors = Object.keys(vm.errors).map(function(fieldName) {
                    return {
                        field: fieldName,
                        message: vm.errors[fieldName],
                        type: 'summary'
                    };
                });
                vm.hasErrors = vm.displayErrors.length > 0;
            } else if (vm.errorType === 'inline') {
                // Display errors inline (similar to field but with different styling)
                if (vm.fieldName && vm.errors[vm.fieldName]) {
                    vm.displayErrors = [{
                        field: vm.fieldName,
                        message: vm.errors[vm.fieldName],
                        type: 'inline'
                    }];
                    vm.hasErrors = true;
                }
            }

            $log.debug('FormErrorDisplay: Updated display errors', vm.displayErrors);
        }

        /**
         * Dismiss an error
         * @param {Object} error - Error object to dismiss
         * @param {number} index - Index of error in displayErrors array
         */
        function dismissError(error, index) {
            if (vm.dismissible && vm.onDismiss) {
                vm.onDismiss({ 
                    error: error, 
                    fieldName: error.field 
                });
            }

            // Remove from display errors
            vm.displayErrors.splice(index, 1);
            vm.hasErrors = vm.displayErrors.length > 0;
        }

        /**
         * Get CSS class for error display based on type
         * @param {Object} error - Error object
         * @returns {string} CSS class string
         */
        function getErrorClass(error) {
            var baseClass = 'form-error-display';
            
            switch (error.type) {
                case 'field':
                    return baseClass + ' form-error-display--field invalid-feedback d-block';
                case 'summary':
                    return baseClass + ' form-error-display--summary alert alert-danger';
                case 'inline':
                    return baseClass + ' form-error-display--inline text-danger small';
                default:
                    return baseClass + ' invalid-feedback d-block';
            }
        }

        /**
         * Get icon class based on error type
         * @param {Object} error - Error object
         * @returns {string} Icon class string
         */
        function getIconClass(error) {
            switch (error.type) {
                case 'field':
                case 'inline':
                    return 'fas fa-exclamation-triangle';
                case 'summary':
                    return 'fas fa-exclamation-circle';
                default:
                    return 'fas fa-exclamation-triangle';
            }
        }
    }
})();