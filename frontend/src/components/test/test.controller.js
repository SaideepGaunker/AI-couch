/**
 * Test Controller - Handles quick interview tests
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .controller('TestController', TestController);

    TestController.$inject = ['$location', '$routeParams', '$timeout', 'AuthService', 'InterviewService'];

    function TestController($location, $routeParams, $timeout, AuthService, InterviewService) {
        var vm = this;

        // Properties
        vm.sessionId = $routeParams.sessionId;
        vm.session = null;
        vm.questions = [];
        vm.currentQuestionIndex = 0;
        vm.currentQuestion = null;
        vm.userAnswer = '';
        vm.loading = false;
        vm.error = '';
        vm.timeRemaining = 0;
        vm.timer = null;

        // Methods
        vm.submitAnswer = submitAnswer;
        vm.skipQuestion = skipQuestion;
        vm.nextQuestion = nextQuestion;
        vm.endTest = endTest;
        vm.goToDashboard = goToDashboard;
        vm.formatTime = formatTime;

        // Initialize
        activate();

        function activate() {
            console.log('Test activated with session ID:', vm.sessionId);
            
            if (!vm.sessionId) {
                vm.error = 'No session ID provided';
                return;
            }

            // Initialize session data from URL params
            var sessionData = $routeParams.sessionData;
            if (sessionData) {
                try {
                    var data = JSON.parse(sessionData);
                    vm.session = data.session;
                    vm.questions = data.questions || [];
                    initializeTest();
                } catch (e) {
                    console.error('Error parsing session data:', e);
                    loadSessionData();
                }
            } else {
                loadSessionData();
            }
        }

        function loadSessionData() {
            vm.loading = true;
            InterviewService.getSession(vm.sessionId)
                .then(function(response) {
                    vm.session = response.session;
                    vm.questions = response.questions || [];
                    initializeTest();
                })
                .catch(function(error) {
                    console.error('Error loading session:', error);
                    vm.error = 'Failed to load test session';
                })
                .finally(function() {
                    vm.loading = false;
                });
        }

        function initializeTest() {
            if (vm.questions.length > 0) {
                vm.currentQuestion = vm.questions[0];
                vm.currentQuestionIndex = 0;
                vm.timeRemaining = (vm.session.duration || 15) * 60; // Default 15 minutes for test
                startTimer();
            } else {
                vm.error = 'No questions available for this test';
            }
        }

        function submitAnswer() {
            if (!vm.userAnswer.trim()) {
                vm.error = 'Please provide an answer before submitting.';
                return;
            }

            vm.loading = true;
            vm.error = '';

            var answerData = {
                question_id: parseInt(vm.currentQuestion.id || vm.currentQuestion.question_id || 1),
                answer_text: vm.userAnswer.trim(),
                response_time: Math.floor(Math.random() * 120) + 30 // Simulate response time
            };
            
            console.log('Test answer data being sent:', answerData);

            console.log('Submitting test answer:', answerData);

            InterviewService.submitAnswer(vm.sessionId, answerData)
                .then(function(response) {
                    console.log('Test answer submitted:', response);
                    vm.userAnswer = '';
                    nextQuestion();
                })
                .catch(function(error) {
                    console.error('Test answer submission error:', error);
                    vm.error = error.data?.detail || 'Failed to submit answer.';
                })
                .finally(function() {
                    vm.loading = false;
                });
        }

        function skipQuestion() {
            vm.userAnswer = '';
            nextQuestion();
        }

        function nextQuestion() {
            if (vm.currentQuestionIndex < vm.questions.length - 1) {
                vm.currentQuestionIndex++;
                vm.currentQuestion = vm.questions[vm.currentQuestionIndex];
            } else {
                // All questions completed
                endTest();
            }
        }

        function endTest() {
            console.log('Ending test session');
            stopTimer();

            if (vm.sessionId) {
                InterviewService.completeSession(vm.sessionId)
                    .then(function(response) {
                        console.log('Test completed:', response);
                        $timeout(function() {
                            $location.path('/feedback/' + vm.sessionId);
                        }, 0);
                    })
                    .catch(function(error) {
                        console.error('Error ending test:', error);
                        $timeout(function() {
                            $location.path('/feedback/' + vm.sessionId);
                        }, 0);
                    });
            } else {
                $location.path('/dashboard');
            }
        }

        function goToDashboard() {
            stopTimer();
            $location.path('/dashboard');
        }

        function startTimer() {
            vm.timer = setInterval(function() {
                vm.timeRemaining--;
                if (vm.timeRemaining <= 0) {
                    endTest();
                }
                $timeout(function() {}, 0); // Trigger digest cycle
            }, 1000);
        }

        function stopTimer() {
            if (vm.timer) {
                clearInterval(vm.timer);
                vm.timer = null;
            }
        }

        function formatTime(seconds) {
            var minutes = Math.floor(seconds / 60);
            var remainingSeconds = seconds % 60;
            return minutes + ':' + (remainingSeconds < 10 ? '0' : '') + remainingSeconds;
        }

        // Cleanup on destroy
        this.$onDestroy = function() {
            stopTimer();
        };
    }
})();