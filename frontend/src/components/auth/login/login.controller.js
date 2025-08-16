/**
 * Login Controller - Component-based Architecture
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .controller('LoginController', LoginController);

    LoginController.$inject = ['$scope', '$location', '$routeParams', '$timeout', 'AuthService'];

    function LoginController($scope, $location, $routeParams, $timeout, AuthService) {
        var vm = this;

        // Properties
        vm.loginForm = {
            email: '',
            password: ''
        };
        vm.loading = false;
        vm.error = '';
        vm.success = '';

        // Methods
        vm.login = login;

        // Initialize
        activate();

        function activate() {
            // Check if user is already authenticated
            if (AuthService.isAuthenticated()) {
                $location.path('/dashboard');
            }
        }

        function login() {
            if (!vm.loginForm.email || !vm.loginForm.password) {
                vm.error = 'Please enter both email and password.';
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
                        console.log('Redirecting to dashboard...');
                        $location.path('/dashboard');
                        
                        // No need for manual $apply - $timeout will handle it
                    }, 500);
                })
                .catch(function(error) {
                    console.error('Login error:', error);
                    vm.error = error || 'Login failed. Please check your credentials.';
                })
                .finally(function() {
                    vm.loading = false;
                });
        }
    }
})();