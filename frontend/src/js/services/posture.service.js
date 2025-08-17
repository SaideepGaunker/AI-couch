/**
 * Posture Detection Service
 * Handles real-time posture analysis during interviews
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .factory('PostureService', PostureService);

    PostureService.$inject = ['$http', '$q', '$interval'];

    function PostureService($http, $q, $interval) {
        var service = {
            // Properties
            isAnalyzing: false,
            currentFeedback: null,
            analysisInterval: null,
            
            // Methods
            startPostureAnalysis: startPostureAnalysis,
            stopPostureAnalysis: stopPostureAnalysis,
            analyzeFrame: analyzeFrame,
            captureFrameFromVideo: captureFrameFromVideo,
            
            // WebSocket methods
            connectWebSocket: connectWebSocket,
            disconnectWebSocket: disconnectWebSocket,
            sendFrameViaWebSocket: sendFrameViaWebSocket,
            
            // Callbacks
            onPostureFeedback: null,
            onError: null
        };

        var websocket = null;
        var baseUrl = 'http://localhost:8000/api/v1';

        return service;

        /**
         * Start continuous posture analysis
         * @param {HTMLVideoElement} videoElement - Video element to capture frames from
         * @param {number} interviewId - Current interview session ID
         * @param {number} intervalMs - Analysis interval in milliseconds (default: 3000ms)
         */
        function startPostureAnalysis(videoElement, interviewId, intervalMs) {
            intervalMs = intervalMs || 3000; // Default: analyze every 3 seconds
            
            if (service.isAnalyzing) {
                console.warn('Posture analysis already running');
                return;
            }

            if (!videoElement) {
                console.error('No video element provided for posture analysis');
                return;
            }

            console.log('Starting posture analysis for interview:', interviewId);
            
            service.isAnalyzing = true;
            startAnalysisInterval(videoElement, interviewId, intervalMs);
        }
        
        /**
         * Start the analysis interval
         * @param {HTMLVideoElement} videoElement - Video element to capture frames from
         * @param {number} interviewId - Current interview session ID
         * @param {number} intervalMs - Analysis interval in milliseconds
         */
        function startAnalysisInterval(videoElement, interviewId, intervalMs) {
            var lastAnalysisTime = Date.now();
            var stuckTimeout = 30000; // 30 seconds timeout for stuck analysis
            
            // Start periodic analysis
            service.analysisInterval = $interval(function() {
                try {
                    // Check if video element is still valid
                    if (!videoElement || !videoElement.parentNode || !document.contains(videoElement)) {
                        console.warn('Video element is no longer valid, stopping posture analysis');
                        service.stopPostureAnalysis();
                        return;
                    }
                    
                    // Check if analysis is stuck
                    var timeSinceLastAnalysis = Date.now() - lastAnalysisTime;
                    if (timeSinceLastAnalysis > stuckTimeout) {
                        console.warn('Posture analysis appears to be stuck, restarting...');
                        if (service.onError) {
                            service.onError(new Error('Posture analysis stuck, restarting...'));
                        }
                        // Restart the analysis
                        service.stopPostureAnalysis();
                        setTimeout(function() {
                            if (videoElement && interviewId) {
                                service.startPostureAnalysis(videoElement, interviewId, intervalMs);
                            }
                        }, 1000);
                        return;
                    }
                    
                    if (videoElement.videoWidth > 0 && videoElement.videoHeight > 0) {
                        var frameData = captureFrameFromVideo(videoElement);
                        if (frameData) {
                            console.log('Captured frame for posture analysis, size:', frameData.length);
                            lastAnalysisTime = Date.now();
                            analyzeFrame(frameData, interviewId)
                                .then(function(result) {
                                    console.log('Posture analysis result:', result);
                                    console.log('Result type:', typeof result);
                                    console.log('Posture score in result:', result.posture_score);
                                    console.log('Posture status in result:', result.posture_status);
                                    
                                    service.currentFeedback = result;
                                    if (service.onPostureFeedback) {
                                        service.onPostureFeedback(result);
                                    }
                                })
                                .catch(function(error) {
                                    console.error('Posture analysis error:', error);
                                    if (service.onError) {
                                        service.onError(error);
                                    }
                                });
                        } else {
                            console.warn('Failed to capture frame from video element');
                        }
                    } else {
                        console.warn('Video element not ready for frame capture:', {
                            videoWidth: videoElement ? videoElement.videoWidth : 'no element',
                            videoHeight: videoElement ? videoElement.videoHeight : 'no element'
                        });
                    }
                } catch (error) {
                    console.error('Error in posture analysis interval:', error);
                    if (service.onError) {
                        service.onError(error);
                    }
                }
            }, intervalMs);
        }

        /**
         * Stop posture analysis
         */
        function stopPostureAnalysis() {
            console.log('Stopping posture analysis');
            service.isAnalyzing = false;
            
            if (service.analysisInterval) {
                $interval.cancel(service.analysisInterval);
                service.analysisInterval = null;
            }
            
            disconnectWebSocket();
        }

        /**
         * Analyze a single frame for posture
         * @param {string} imageData - Base64 encoded image data
         * @param {number} interviewId - Interview session ID
         * @returns {Promise} Promise resolving to posture analysis result
         */
        function analyzeFrame(imageData, interviewId) {
            var deferred = $q.defer();

            var requestData = {
                image_data: imageData,
                interview_id: interviewId
            };

            console.log('Sending posture analysis request for interview:', interviewId);

            $http.post(baseUrl + '/posture/analyze_posture', requestData)
                .then(function(response) {
                    console.log('Posture analysis API response:', response.data);
                    console.log('Response data type:', typeof response.data);
                    console.log('Posture score in response:', response.data.posture_score);
                    console.log('Posture status in response:', response.data.posture_status);
                    deferred.resolve(response.data);
                })
                .catch(function(error) {
                    console.error('Posture analysis API error:', error);
                    
                    // Create a fallback feedback object to avoid breaking the UI
                    var fallbackFeedback = {
                        posture_status: 'no_pose',
                        posture_score: 0,
                        feedback_message: 'Posture analysis temporarily unavailable',
                        timestamp: new Date().toISOString()
                    };
                    
                    // Resolve with fallback instead of rejecting to avoid unhandled promise errors
                    deferred.resolve(fallbackFeedback);
                    
                    // Still call the error callback if it exists
                    if (service.onError) {
                        service.onError(error);
                    }
                });

            return deferred.promise;
        }

        /**
         * Capture frame from video element as base64
         * @param {HTMLVideoElement} videoElement - Video element to capture from
         * @returns {string|null} Base64 encoded image data or null if failed
         */
        function captureFrameFromVideo(videoElement) {
            try {
                // Check if video element is still valid and accessible
                if (!videoElement || !videoElement.parentNode || !document.contains(videoElement)) {
                    console.warn('Video element is no longer valid or accessible');
                    return null;
                }
                
                if (videoElement.videoWidth === 0 || videoElement.videoHeight === 0) {
                    console.warn('Video element not ready for capture');
                    return null;
                }

                // Create canvas to capture frame
                var canvas = document.createElement('canvas');
                var context = canvas.getContext('2d');
                
                // Set canvas dimensions to match video
                canvas.width = videoElement.videoWidth;
                canvas.height = videoElement.videoHeight;
                
                // Draw current video frame to canvas
                context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
                
                // Convert to base64 with higher quality for better analysis
                var imageData = canvas.toDataURL('image/jpeg', 0.9);
                
                // Remove data URL prefix for API
                var base64Data = imageData.split(',')[1];
                
                return base64Data;
                
            } catch (error) {
                console.error('Error capturing frame:', error);
                return null;
            }
        }

        /**
         * Connect to WebSocket for real-time posture analysis
         * @param {number} interviewId - Interview session ID
         */
        function connectWebSocket(interviewId) {
            if (websocket) {
                disconnectWebSocket();
            }

            try {
                var wsUrl = 'ws://localhost:8000/api/v1/posture/ws/posture/' + interviewId;
                websocket = new WebSocket(wsUrl);

                websocket.onopen = function() {
                };

                websocket.onmessage = function(event) {
                    try {
                        var result = JSON.parse(event.data);
                        service.currentFeedback = result;
                        
                        if (service.onPostureFeedback) {
                            service.onPostureFeedback(result);
                        }
                    } catch (error) {
                        console.error('Error parsing WebSocket message:', error);
                    }
                };

                websocket.onerror = function(error) {
                    console.error('WebSocket error:', error);
                    if (service.onError) {
                        service.onError(error);
                    }
                };

                websocket.onclose = function() {
                    websocket = null;
                };

            } catch (error) {
                console.error('Error connecting to WebSocket:', error);
            }
        }

        /**
         * Disconnect WebSocket
         */
        function disconnectWebSocket() {
            if (websocket) {
                websocket.close();
                websocket = null;
            }
        }

        /**
         * Send frame data via WebSocket
         * @param {string} imageData - Base64 encoded image data
         */
        function sendFrameViaWebSocket(imageData) {
            if (websocket && websocket.readyState === WebSocket.OPEN) {
                websocket.send(JSON.stringify({
                    image_data: imageData
                }));
            }
        }
    }
})();