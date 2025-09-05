/**
 * Login Controller - Component-based Architecture
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .controller('LoginController', LoginController);

    LoginController.$inject = ['$scope', '$location', '$routeParams', '$timeout', 'AuthService', 'FormErrorService'];

    function LoginController($scope, $location, $routeParams, $timeout, AuthService, FormErrorService) {
        var vm = this;

        // Properties
        vm.loginForm = {
            email: '',
            password: ''
        };
        vm.loading = false;
        vm.error = '';
        vm.success = '';
        vm.fieldErrors = {};

        // Methods
        vm.login = login;
        vm.clearFieldError = clearFieldError;
        vm.hasFieldError = hasFieldError;
        vm.getFieldError = getFieldError;

        // Initialize
        activate();

        function activate() {
            // Check if user is already authenticated
            if (AuthService.isAuthenticated()) {
                $location.path('/dashboard');
            }
        }

        function login() {
            // Clear previous errors
            vm.error = '';
            vm.fieldErrors = {};
            
            // Validate form using FormErrorService
            var validation = FormErrorService.validateLoginForm(vm.loginForm);
            
            if (!validation.isValid) {
                vm.fieldErrors = validation.errors;
                
                // Set general error message for empty fields
                if (validation.errors.email || validation.errors.username) {
                    if (validation.errors.password) {
                        vm.error = 'Please enter both email and password.';
                    } else {
                        vm.error = 'Please enter your email address.';
                    }
                } else if (validation.errors.password) {
                    vm.error = 'Please enter your password.';
                }
                
                return;
            }

            vm.loading = true;
            vm.error = '';
            vm.success = '';

            AuthService.login(vm.loginForm)
                .then(function(response) {
                    console.log('Login successful:', response);
                    vm.success = 'Login successful! Redirecting...';
                    
                    // Add a small delay to ensure localStorage is properly updated
                    $timeout(function() {
                        $location.path('/dashboard');
                    }, 500);
                })
                .catch(function(error) {
                    console.error('Login error:', error);
                    
                    // Use FormErrorService to handle server errors
                    vm.error = FormErrorService.handleServerError(error);
                    
                    // Handle specific login errors
                    if (error.status === 401) {
                        vm.fieldErrors.email = 'Invalid credentials';
                        vm.fieldErrors.password = 'Invalid credentials';
                    }
                })
                .finally(function() {
                    vm.loading = false;
                });
        }

        /**
         * Clear error for a specific field
         * @param {string} fieldName - Name of the field to clear error for
         */
        function clearFieldError(fieldName) {
            if (vm.fieldErrors[fieldName]) {
                delete vm.fieldErrors[fieldName];
            }
            
            // Clear general error if no field errors remain
            if (Object.keys(vm.fieldErrors).length === 0) {
                vm.error = '';
            }
        }

        /**
         * Check if a field has an error
         * @param {string} fieldName - Name of the field to check
         * @returns {boolean} True if field has error
         */
        function hasFieldError(fieldName) {
            return !!vm.fieldErrors[fieldName];
        }

        /**
         * Get error message for a specific field
         * @param {string} fieldName - Name of the field
         * @returns {string} Error message for the field
         */
        function getFieldError(fieldName) {
            return vm.fieldErrors[fieldName] || '';
        }
    }
})();