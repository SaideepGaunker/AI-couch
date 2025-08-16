/**
 * Main Controller for home page
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .controller('MainController', MainController);

    MainController.$inject = ['$location', 'AuthService'];

    function MainController($location, AuthService) {
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
        
        // Initialize controller
        function activate() {
            // Controller initialization logic if needed
        }
        
        activate();
    }
})();