/**
 * Home Controller - Component-based Architecture
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .controller('HomeController', HomeController);

    HomeController.$inject = ['$location', 'AuthService'];

    function HomeController($location, AuthService) {
        var vm = this;

        // Properties
        vm.isAuthenticated = AuthService.isAuthenticated();

        // Methods
        vm.getStarted = getStarted;
        vm.startPractice = startPractice;
        vm.goToLogin = goToLogin;
        vm.goToRegister = goToRegister;

        // Initialize
        activate();

        function activate() {
            // If user is already authenticated, redirect to dashboard
            if (vm.isAuthenticated) {
                $location.path('/dashboard');
            }
        }

        function getStarted() {
            if (vm.isAuthenticated) {
                $location.path('/dashboard');
            } else {
                $location.path('/register');
            }
        }

        function startPractice() {
            if (vm.isAuthenticated) {
                $location.path('/interview');
            } else {
                $location.path('/login');
            }
        }

        function goToLogin() {
            $location.path('/login');
        }

        function goToRegister() {
            $location.path('/register');
        }
    }
})();