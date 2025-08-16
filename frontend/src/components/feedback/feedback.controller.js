/**
 * Feedback Controller - Handles interview results and performance feedback
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .controller('FeedbackController', FeedbackController);

    FeedbackController.$inject = ['$location', '$routeParams', 'AuthService', 'InterviewService'];

    function FeedbackController($location, $routeParams, AuthService, InterviewService) {
        var vm = this;

        // Properties
        vm.sessionId = $routeParams.sessionId;
        vm.feedback = null;
        vm.session = null;
        vm.loading = true;
        vm.error = '';

        // Methods
        vm.practiceAgain = practiceAgain;
        vm.viewProgress = viewProgress;
        vm.goToDashboard = goToDashboard;

        // Initialize
        activate();

        function activate() {
            // Route-level authentication is handled in app.js
            console.log('Feedback controller activated for session:', vm.sessionId);

            if (!vm.sessionId) {
                vm.error = 'No session ID provided';
                vm.loading = false;
                return;
            }

            loadFeedback();
        }

        function loadFeedback() {
            vm.loading = true;
            vm.error = '';

            InterviewService.getSessionFeedback(vm.sessionId)
                .then(function(response) {
                    console.log('Feedback loaded:', response);
                    vm.feedback = response.feedback;
                    vm.session = response.session;
                })
                .catch(function(error) {
                    console.error('Error loading feedback:', error);
                    vm.error = error.data?.detail || 'Failed to load feedback';
                    
                    // Create mock feedback for demo purposes
                    vm.feedback = {
                        overall_score: 0,
                        content_quality: 0,
                        body_language: 0,
                        voice_tone: 0,
                        areas_for_improvement: ['Complete more practice sessions for detailed feedback'],
                        recommendations: ['Keep practicing to improve your interview skills!'],
                        detailed_analysis: 'Complete more interview sessions to receive AI-powered detailed analysis of your performance.',
                        question_specific_feedback: []
                    };
                    vm.session = {
                        id: vm.sessionId,
                        target_role: 'Unknown',
                        session_type: 'mixed'
                    };
                })
                .finally(function() {
                    vm.loading = false;
                });
        }

        function practiceAgain() {
            $location.path('/interview');
        }

        function viewProgress() {
            $location.path('/progress');
        }

        function goToDashboard() {
            $location.path('/dashboard');
        }

        // Helper function to check if value is array
        vm.isArray = function(value) {
            return Array.isArray(value);
        };

        // Debug function to test feedback loading
        vm.debugFeedback = function() {
            console.log('=== Feedback Debug Info ===');
            console.log('Session ID:', vm.sessionId);
            console.log('Feedback:', vm.feedback);
            console.log('Session:', vm.session);
            console.log('Loading:', vm.loading);
            console.log('Error:', vm.error);
            console.log('Recommendations type:', typeof vm.feedback?.recommendations);
            console.log('Recommendations is array:', Array.isArray(vm.feedback?.recommendations));
            console.log('==========================');
        };
    }
})();