/**
 * Feedback Controller - Handles interview results and performance feedback
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .controller('FeedbackController', FeedbackController);

    FeedbackController.$inject = ['$location', '$routeParams', 'AuthService', 'InterviewService', 'PostureFeedbackIntegrationService', '$q', '$timeout'];

    function FeedbackController($location, $routeParams, AuthService, InterviewService, PostureFeedbackIntegrationService, $q, $timeout) {
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

            console.log('Starting feedback loading process...');
            loadFeedback();
        }

        function loadFeedback() {
            vm.loading = true;
            vm.error = '';

            // Set a timeout to prevent infinite loading
            var loadingTimeout = $timeout(function() {
                if (vm.loading) {
                    console.warn('Feedback loading timeout - falling back to basic feedback');
                    vm.loading = false;
                    loadBasicFeedback();
                }
            }, 15000); // 15 second timeout

            // First, try to load just the interview feedback quickly
            InterviewService.getSessionFeedback(vm.sessionId)
                .then(function(response) {
                    console.log('Basic feedback loaded quickly:', response);
                    vm.feedback = response.feedback;
                    vm.session = response.session;
                    
                    // Now try to enhance with body language data (non-blocking)
                    PostureFeedbackIntegrationService.getBodyLanguageScore(vm.sessionId)
                        .then(function(bodyLanguageResult) {
                            // Use body language score directly from PerformanceMetrics
                            if (bodyLanguageResult && bodyLanguageResult.success && bodyLanguageResult.body_language_score > 0) {
                                vm.feedback.body_language = Math.round(bodyLanguageResult.body_language_score);
                            }
                        })
                        .catch(function(bodyLanguageError) {
                            console.warn('Body language data enhancement failed, using basic feedback:', bodyLanguageError);
                        });
                    
                    $timeout.cancel(loadingTimeout);
                    vm.loading = false;
                })
                .catch(function(error) {
                    $timeout.cancel(loadingTimeout);
                    console.error('Error loading basic feedback:', error);
                    vm.error = error.data?.detail || 'Failed to load feedback';
                    loadBasicFeedback();
                });
        }

        function loadBasicFeedback() {
            vm.loading = false;
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
    }
})();