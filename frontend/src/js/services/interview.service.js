/**
 * Interview Service for managing interview sessions
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .service('InterviewService', InterviewService);

    InterviewService.$inject = ['$q', '$rootScope', 'ApiService'];

    function InterviewService($q, $rootScope, ApiService) {
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
            deleteSession: deleteSession,
            practiceAgain: practiceAgain,
            getDifficultyStatistics: getDifficultyStatistics
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
            
            // Include hierarchical role data if available
            if (sessionConfig.hierarchical_role) {
                sessionData.hierarchical_role = sessionConfig.hierarchical_role;
            }

            // Broadcast interview starting event
            $rootScope.$broadcast('interview:starting', {
                message: 'Starting interview session...'
            });

            return ApiService.postWithRetry('/interviews/start', sessionData, {
                loadingMessage: 'Starting interview session...',
                successMessage: 'Interview session started successfully!'
            })
                .then(function(response) {
                    $rootScope.$broadcast('interview:started', response);
                    return response;
                })
                .catch(function(error) {
                    $rootScope.$broadcast('interview:start-failed', error);
                    throw error;
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
            
            // Include hierarchical role data if available
            if (sessionConfig.hierarchical_role) {
                sessionData.hierarchical_role = sessionConfig.hierarchical_role;
            }

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
            // Ensure answerData is properly structured
            var data = {
                question_id: answerData.question_id,
                answer_text: answerData.answer_text,
                response_time: answerData.response_time
            };
            
            // Include posture data if available
            if (answerData.posture_data) {
                data.posture_data = answerData.posture_data;
                console.log('InterviewService: Including posture data in submission:', data.posture_data);
            }
            
            // Broadcast answer submission event
            $rootScope.$broadcast('interview:submitting-answer', {
                message: 'Submitting your answer...'
            });
            
            return ApiService.postWithRetry('/interviews/' + sessionId + '/submit-answer', data, {
                loadingMessage: 'Submitting your answer...',
                retryable: true
            })
                .then(function(response) {
                    $rootScope.$broadcast('interview:answer-submitted', response);
                    return response;
                })
                .catch(function(error) {
                    $rootScope.$broadcast('interview:answer-submit-failed', error);
                    throw error;
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

        function completeSession(sessionId, sessionData) {
            var data = sessionData || {};
            data.session_id = sessionId;
            
            return ApiService.put('/interviews/' + sessionId + '/complete', data)
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
            console.log('InterviewService: Getting session feedback for session:', sessionId);
            
            // Broadcast feedback generation event
            $rootScope.$broadcast('feedback:generating', {
                message: 'Generating your feedback...'
            });
            
            var fallbackResponse = {
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
                },
                learning_recommendations: null
            };
            
            return ApiService.getWithFallback('/interviews/' + sessionId + '/feedback', {
                _t: Date.now() // Cache busting parameter
            }, fallbackResponse, {
                loadingMessage: 'Generating your feedback...',
                timeout: 30000 // 30 second timeout for feedback generation
            })
                .then(function(response) {
                    console.log('InterviewService: Feedback response received:', response);
                    
                    // Debug log for score consistency
                    if (response && response.session && response.feedback) {
                        console.log('Score consistency check:');
                        console.log('  Session overall_score:', response.session.overall_score);
                        console.log('  Feedback overall_score:', response.feedback.overall_score);
                        console.log('  Individual scores:', {
                            content: response.feedback.content_quality,
                            body: response.feedback.body_language,
                            voice: response.feedback.voice_tone
                        });
                    }
                    
                    $rootScope.$broadcast('feedback:generated', response);
                    return response;
                })
                .catch(function(error) {
                    console.error('InterviewService: Error getting session feedback:', error);
                    $rootScope.$broadcast('feedback:generation-failed', error);
                    
                    console.log('InterviewService: Returning fallback response:', fallbackResponse);
                    return fallbackResponse;
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

        function practiceAgain(sessionId) {
            console.log('InterviewService: Creating practice session for session:', sessionId);
            
            // Use SessionSettingsService for proper inheritance handling
            // Note: We'll inject SessionSettingsService when needed to avoid circular dependencies
            return ApiService.postWithRetry('/interviews/' + sessionId + '/practice-again', {}, {
                loadingMessage: 'Creating practice session with your preferred settings...',
                successMessage: 'Practice session created with inherited settings!'
            })
                .then(function(response) {
                    console.log('InterviewService: Practice session created:', response);
                    
                    // Log inherited settings for user feedback
                    if (response.inherited_settings) {
                        console.log('InterviewService: Settings inherited:', {
                            questionCount: response.inherited_settings.question_count,
                            duration: response.inherited_settings.duration,
                            difficulty: response.inherited_settings.difficulty_level
                        });
                    }
                    
                    // Validate inheritance if verification data is available
                    if (response.inheritance_verification) {
                        var verification = response.inheritance_verification;
                        if (verification.settings_inherited && verification.question_count_matched) {
                            console.log('InterviewService: Settings inheritance verified successfully');
                        } else {
                            console.warn('InterviewService: Settings inheritance verification issues:', verification);
                        }
                    }
                    
                    $rootScope.$broadcast('practice:session-created', response);
                    return response;
                })
                .catch(function(error) {
                    console.error('InterviewService: Error creating practice session:', error);
                    $rootScope.$broadcast('practice:session-failed', error);
                    throw error;
                });
        }

        function getDifficultyStatistics() {
            return ApiService.get('/interviews/difficulty/statistics')
                .then(function(response) {
                    console.log('InterviewService: Difficulty statistics received:', response);
                    return response;
                })
                .catch(function(error) {
                    console.error('InterviewService: Error getting difficulty statistics:', error);
                    throw error;
                });
        }
    }
})();