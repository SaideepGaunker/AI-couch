/**
 * Interview Service for managing interview sessions
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .service('InterviewService', InterviewService);

    InterviewService.$inject = ['$q', 'ApiService'];

    function InterviewService($q, ApiService) {
        var service = {
            startSession: startSession,
            startTestSession: startTestSession,
            getSession: getSession,
            getSessionProgress: getSessionProgress,
            getCurrentQuestion: getCurrentQuestion,
            submitAnswer: submitAnswer,
            pauseSession: pauseSession,
            resumeSession: resumeSession,
            completeSession: completeSession,
            getSessionSummary: getSessionSummary,
            getSessionFeedback: getSessionFeedback,
            getUserSessions: getUserSessions,
            deleteSession: deleteSession
        };

        return service;

        function startSession(sessionConfig) {
            var sessionData = {
                session_type: sessionConfig.session_type,
                target_role: sessionConfig.target_role,
                duration: sessionConfig.duration,
                difficulty: sessionConfig.difficulty,
                question_count: sessionConfig.question_count
            };

            return ApiService.post('/interviews/start', sessionData)
                .then(function(response) {
                    return response;
                });
        }
        
        function startTestSession(sessionConfig) {
            var sessionData = {
                session_type: sessionConfig.session_type,
                target_role: sessionConfig.target_role,
                duration: sessionConfig.duration,
                difficulty: sessionConfig.difficulty,
                question_count: sessionConfig.question_count
            };

            return ApiService.post('/interviews/start-test', sessionData)
                .then(function(response) {
                    return response;
                });
        }

        function getSession(sessionId) {
            return ApiService.get('/interviews/' + sessionId)
                .then(function(response) {
                    return response;
                });
        }

        function getSessionProgress(sessionId) {
            return ApiService.get('/interviews/' + sessionId + '/progress')
                .then(function(response) {
                    return response;
                });
        }

        function getCurrentQuestion(sessionId) {
            return ApiService.get('/interviews/' + sessionId + '/current-question')
                .then(function(response) {
                    return response;
                });
        }

        function submitAnswer(sessionId, answerData) {
            return ApiService.post('/interviews/' + sessionId + '/submit-answer', answerData)
                .then(function(response) {
                    return response;
                });
        }

        function pauseSession(sessionId) {
            return ApiService.put('/interviews/' + sessionId + '/pause')
                .then(function(response) {
                    return response;
                });
        }

        function resumeSession(sessionId) {
            return ApiService.put('/interviews/' + sessionId + '/resume')
                .then(function(response) {
                    return response;
                });
        }

        function completeSession(sessionId) {
            return ApiService.put('/interviews/' + sessionId + '/complete')
                .then(function(response) {
                    return response;
                });
        }

        function getSessionSummary(sessionId) {
            return ApiService.get('/interviews/' + sessionId + '/summary')
                .then(function(response) {
                    return response;
                });
        }

        function getSessionFeedback(sessionId) {
            return ApiService.get('/interviews/' + sessionId + '/feedback')
                .then(function(response) {
                    return response;
                })
                .catch(function(error) {
                    console.error('Error getting session feedback:', error);
                    // Return a default structure if the backend fails
                    return {
                        feedback: {
                            overall_score: 0,
                            content_quality: 0,
                            body_language: 0,
                            voice_tone: 0,
                            areas_for_improvement: ['Complete more practice sessions for detailed feedback'],
                            recommendations: 'Keep practicing to improve your interview skills!'
                        },
                        session: {
                            id: sessionId,
                            target_role: 'Unknown',
                            session_type: 'mixed'
                        }
                    };
                });
        }

        function getUserSessions(limit, skip) {
            var params = {
                limit: limit || 10,
                skip: skip || 0
            };

            return ApiService.get('/interviews/', params)
                .then(function(response) {
                    return response;
                });
        }

        function deleteSession(sessionId) {
            return ApiService.delete('/interviews/' + sessionId)
                .then(function(response) {
                    return response;
                });
        }
    }
})();