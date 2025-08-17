/**
 * Posture Feedback Integration Service
 * Handles integration between posture analysis and feedback system
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .factory('PostureFeedbackIntegrationService', PostureFeedbackIntegrationService);

    PostureFeedbackIntegrationService.$inject = ['$http', '$q', '$timeout'];

    function PostureFeedbackIntegrationService($http, $q, $timeout) {
        var service = {
            // Methods
            updateBodyLanguageScore: updateBodyLanguageScore,
            getBodyLanguageScore: getBodyLanguageScore,
            calculateBodyLanguageScore: calculateBodyLanguageScore
        };

        var baseUrl = 'http://localhost:8000/api/v1';

        return service;

        /**
         * Update body language score in the feedback system
         * @param {number} sessionId - Interview session ID
         * @param {number} bodyLanguageScore - Calculated body language score
         * @param {Object} postureData - Posture analysis data
         * @returns {Promise} Promise resolving to update result
         */
        function updateBodyLanguageScore(sessionId, bodyLanguageScore, postureData) {
            var deferred = $q.defer();

            var requestData = {
                session_id: sessionId,
                body_language_score: bodyLanguageScore,
                posture_data: postureData
            };

            $http.post(baseUrl + '/feedback/update-body-language', requestData)
                .then(function(response) {
                    console.log('Body language score updated:', response.data);
                    deferred.resolve(response.data);
                })
                .catch(function(error) {
                    console.error('Error updating body language score:', error);
                    deferred.reject(error);
                });

            return deferred.promise;
        }

        /**
         * Get body language score from PerformanceMetrics for a session
         * @param {number} sessionId - Interview session ID
         * @returns {Promise} Promise resolving to body language score data
         */
        function getBodyLanguageScore(sessionId) {
            var deferred = $q.defer();

            // Add timeout protection
            var timeoutPromise = $timeout(function() {
                console.warn('Body language score request timeout for session:', sessionId);
                deferred.resolve({
                    error: 'timeout',
                    message: 'Body language data request timed out',
                    body_language_score: 0
                });
            }, 10000); // 10 second timeout

            // Fetch session feedback which includes PerformanceMetrics data
            $http.get(baseUrl + '/interviews/' + sessionId + '/feedback')
                .then(function(response) {
                    $timeout.cancel(timeoutPromise);
                    
                    if (response.data && response.data.feedback) {
                        // Extract body language score from PerformanceMetrics
                        var bodyLanguageScore = response.data.feedback.body_language || 0;
                        deferred.resolve({
                            body_language_score: bodyLanguageScore,
                            success: true
                        });
                    } else {
                        deferred.resolve({
                            error: 'no_data',
                            message: 'No feedback data available',
                            body_language_score: 0
                        });
                    }
                })
                .catch(function(error) {
                    $timeout.cancel(timeoutPromise);
                    console.error('Error getting body language score:', error);
                    
                    // Return default data instead of rejecting to prevent blocking
                    deferred.resolve({
                        error: 'request_failed',
                        message: 'Failed to load body language data',
                        body_language_score: 0
                    });
                });

            return deferred.promise;
        }

        /**
         * Calculate body language score from posture data
         * @param {Array} postureScores - Array of posture scores
         * @returns {number} Calculated body language score (0-100)
         */
        function calculateBodyLanguageScore(postureScores) {
            if (!postureScores || postureScores.length === 0) {
                return 0;
            }

            // Calculate weighted average based on posture status
            var totalWeightedScore = 0;
            var totalWeight = 0;

            postureScores.forEach(function(posture) {
                var weight = 1;
                var score = posture.score || 0;

                // Adjust weight based on posture status
                switch (posture.status) {
                    case 'good':
                        weight = 1.2; // Boost good posture scores
                        break;
                    case 'needs_improvement':
                        weight = 1.0; // Normal weight
                        break;
                    case 'bad':
                        weight = 0.8; // Reduce bad posture scores
                        break;
                    case 'no_pose':
                        weight = 0.5; // Significantly reduce no pose scores
                        break;
                    default:
                        weight = 1.0;
                }

                totalWeightedScore += score * weight;
                totalWeight += weight;
            });

            var averageScore = totalWeight > 0 ? totalWeightedScore / totalWeight : 0;
            
            // Ensure score is within 0-100 range
            return Math.max(0, Math.min(100, Math.round(averageScore)));
        }
    }
})();
