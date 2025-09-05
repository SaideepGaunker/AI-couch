/**
 * Comprehensive Error Handling Service for Frontend
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .service('ErrorHandlingService', ErrorHandlingService);

    ErrorHandlingService.$inject = ['$q', '$timeout', '$rootScope'];

    function ErrorHandlingService($q, $timeout, $rootScope) {
        var service = {
            // Error handling methods
            handleError: handleError,
            handleApiError: handleApiError,
            showUserFriendlyError: showUserFriendlyError,
            
            // Recovery methods
            getRecoverySuggestions: getRecoverySuggestions,
            executeWithFallback: executeWithFallback,
            retryOperation: retryOperation,
            
            // Error tracking
            trackError: trackError,
            getErrorStats: getErrorStats,
            
            // Graceful degradation
            disableFeature: disableFeature,
            enableFeature: enableFeature,
            isFeatureEnabled: isFeatureEnabled,
            
            // User feedback
            showErrorToast: showErrorToast,
            showRecoveryDialog: showRecoveryDialog,
            
            // Configuration
            setErrorDisplayDuration: setErrorDisplayDuration,
            setRetryConfig: setRetryConfig
        };

        // Private variables
        var errorStats = {
            totalErrors: 0,
            errorsByType: {},
            recentErrors: []
        };
        
        var disabledFeatures = new Set();
        var fallbackData = {};
        var errorDisplayDuration = 5000; // 5 seconds
        var retryConfigs = {
            'api': { maxRetries: 2, delay: 1000, backoff: 1.5 },
            'default': { maxRetries: 1, delay: 500, backoff: 1 }
        };

        return service;

        // ==================== Error Handling Methods ====================

        function handleError(error, context) {
            context = context || {};
            
            var errorInfo = {
                timestamp: new Date().toISOString(),
                message: error.message || 'Unknown error',
                stack: error.stack,
                context: context,
                userAgent: navigator.userAgent,
                url: window.location.href
            };

            // Track the error
            trackError(errorInfo);

            // Log to console in development
            if (isDevelopment()) {
                console.error('Error handled:', errorInfo);
            }

            // Determine error type and get user-friendly message
            var errorType = determineErrorType(error);
            var userFriendlyMessage = getUserFriendlyMessage(errorType, error);
            var recoverySuggestions = getRecoverySuggestions(errorType);

            var processedError = {
                type: errorType,
                originalError: error,
                userFriendlyMessage: userFriendlyMessage,
                recoverySuggestions: recoverySuggestions,
                context: context,
                timestamp: errorInfo.timestamp
            };

            // Show error to user
            showUserFriendlyError(processedError);

            return processedError;
        }

        function handleApiError(error, context) {
            context = context || {};
            context.type = 'api_error';

            var apiError = {
                status: error.status || 0,
                statusText: error.statusText || 'Unknown',
                data: error.data || {},
                config: error.config || {}
            };

            // Extract error details from API response
            var errorDetails = extractApiErrorDetails(apiError);
            
            var processedError = {
                type: 'api_error',
                status: apiError.status,
                statusText: apiError.statusText,
                message: errorDetails.message,
                userFriendlyMessage: errorDetails.userFriendlyMessage,
                recoverySuggestions: errorDetails.recoverySuggestions,
                context: context,
                timestamp: new Date().toISOString()
            };

            // Track the error
            trackError(processedError);

            // Show error to user
            showUserFriendlyError(processedError);

            return processedError;
        }

        function extractApiErrorDetails(apiError) {
            var details = {
                message: 'API request failed',
                userFriendlyMessage: 'Something went wrong. Please try again.',
                recoverySuggestions: ['Refresh the page', 'Try again in a few moments']
            };

            // Extract from backend error response
            if (apiError.data && apiError.data.detail) {
                if (typeof apiError.data.detail === 'string') {
                    details.message = apiError.data.detail;
                } else if (apiError.data.detail.message) {
                    details.message = apiError.data.detail.message;
                    details.userFriendlyMessage = apiError.data.detail.message || details.userFriendlyMessage;
                    details.recoverySuggestions = apiError.data.detail.recovery_suggestions || details.recoverySuggestions;
                }
            }

            // Status-specific handling
            switch (apiError.status) {
                case 400:
                    details.userFriendlyMessage = 'Please check your input and try again.';
                    details.recoverySuggestions = ['Review the form for errors', 'Check required fields'];
                    break;
                case 401:
                    details.userFriendlyMessage = 'Please log in to continue.';
                    details.recoverySuggestions = ['Log in again', 'Check if your session expired'];
                    break;
                case 403:
                    details.userFriendlyMessage = 'You don\'t have permission to perform this action.';
                    details.recoverySuggestions = ['Contact support', 'Check your account permissions'];
                    break;
                case 404:
                    details.userFriendlyMessage = 'The requested resource was not found.';
                    details.recoverySuggestions = ['Check the URL', 'Go back and try again'];
                    break;
                case 429:
                    details.userFriendlyMessage = 'Too many requests. Please wait before trying again.';
                    details.recoverySuggestions = ['Wait a few minutes', 'Try again later'];
                    break;
                case 500:
                case 502:
                case 503:
                case 504:
                    details.userFriendlyMessage = 'Server error. Please try again later.';
                    details.recoverySuggestions = ['Try again in a few minutes', 'Contact support if problem persists'];
                    break;
                case 0:
                    details.userFriendlyMessage = 'Network error. Please check your connection.';
                    details.recoverySuggestions = ['Check internet connection', 'Try again'];
                    break;
            }

            return details;
        }

        function showUserFriendlyError(errorInfo) {
            // Broadcast error event for components to handle - use $timeout to avoid digest cycle conflicts
            $timeout(function() {
                $rootScope.$broadcast('error:occurred', errorInfo);
            }, 0);

            // Show toast notification
            showErrorToast(errorInfo.userFriendlyMessage, errorInfo.recoverySuggestions);
        }

        // ==================== Recovery Methods ====================

        function getRecoverySuggestions(errorType) {
            var suggestions = {
                'network_error': [
                    'Check your internet connection',
                    'Try refreshing the page',
                    'Try again in a few moments'
                ],
                'authentication_error': [
                    'Log out and log back in',
                    'Clear browser cache',
                    'Check if your account is locked'
                ],
                'validation_error': [
                    'Check all required fields are filled',
                    'Verify data formats are correct',
                    'Review any error messages on the form'
                ],
                'server_error': [
                    'Try again in a few minutes',
                    'Contact support if problem persists',
                    'Check system status page'
                ],
                'session_error': [
                    'Refresh the page',
                    'Log out and log back in',
                    'Clear browser cache'
                ],
                'feature_unavailable': [
                    'Try using a different browser',
                    'Check if feature is under maintenance',
                    'Contact support for assistance'
                ]
            };

            return suggestions[errorType] || [
                'Refresh the page and try again',
                'Contact support if the problem persists'
            ];
        }

        function executeWithFallback(primaryFunction, fallbackFunction, context) {
            context = context || {};
            
            return $q(function(resolve, reject) {
                primaryFunction()
                    .then(function(result) {
                        resolve(result);
                    })
                    .catch(function(error) {
                        console.warn('Primary function failed, executing fallback:', error);
                        
                        if (fallbackFunction) {
                            fallbackFunction()
                                .then(function(fallbackResult) {
                                    // Track that fallback was used
                                    trackError({
                                        type: 'fallback_used',
                                        context: context,
                                        originalError: error,
                                        timestamp: new Date().toISOString()
                                    });
                                    
                                    resolve(fallbackResult);
                                })
                                .catch(function(fallbackError) {
                                    // Both primary and fallback failed
                                    var combinedError = handleError(fallbackError, {
                                        ...context,
                                        primaryError: error,
                                        fallbackFailed: true
                                    });
                                    reject(combinedError);
                                });
                        } else {
                            var processedError = handleError(error, context);
                            reject(processedError);
                        }
                    });
            });
        }

        function retryOperation(operation, operationType, context) {
            operationType = operationType || 'default';
            context = context || {};
            
            var config = retryConfigs[operationType] || retryConfigs.default;
            var attempts = 0;

            function attemptOperation() {
                attempts++;
                
                return operation()
                    .catch(function(error) {
                        if (attempts < config.maxRetries + 1) {
                            console.log('Retry attempt', attempts, 'for operation:', operationType);
                            
                            return $timeout(function() {
                                return attemptOperation();
                            }, config.delay * Math.pow(config.backoff, attempts - 1));
                        } else {
                            // All retries exhausted
                            var retryError = handleError(error, {
                                ...context,
                                totalAttempts: attempts,
                                operationType: operationType
                            });
                            throw retryError;
                        }
                    });
            }

            return attemptOperation();
        }

        // ==================== Error Tracking ====================

        function trackError(errorInfo) {
            errorStats.totalErrors++;
            
            var errorType = errorInfo.type || 'unknown';
            if (!errorStats.errorsByType[errorType]) {
                errorStats.errorsByType[errorType] = 0;
            }
            errorStats.errorsByType[errorType]++;

            // Add to recent errors (keep last 50)
            errorStats.recentErrors.unshift(errorInfo);
            if (errorStats.recentErrors.length > 50) {
                errorStats.recentErrors = errorStats.recentErrors.slice(0, 50);
            }

            // Send to analytics if available
            if (window.gtag) {
                window.gtag('event', 'exception', {
                    description: errorInfo.message || 'Unknown error',
                    fatal: false
                });
            }
        }

        function getErrorStats() {
            return {
                ...errorStats,
                disabledFeatures: Array.from(disabledFeatures),
                timestamp: new Date().toISOString()
            };
        }

        // ==================== Graceful Degradation ====================

        function disableFeature(featureName, reason) {
            disabledFeatures.add(featureName);
            console.warn('Feature disabled:', featureName, 'Reason:', reason);
            
            // Broadcast feature disabled event
            $rootScope.$broadcast('feature:disabled', {
                feature: featureName,
                reason: reason
            });
        }

        function enableFeature(featureName) {
            disabledFeatures.delete(featureName);
            console.info('Feature enabled:', featureName);
            
            // Broadcast feature enabled event
            $rootScope.$broadcast('feature:enabled', {
                feature: featureName
            });
        }

        function isFeatureEnabled(featureName) {
            return !disabledFeatures.has(featureName);
        }

        // ==================== User Feedback ====================

        function showErrorToast(message, suggestions) {
            // Create toast notification
            var toast = {
                type: 'error',
                message: message,
                suggestions: suggestions || [],
                timestamp: new Date().toISOString(),
                duration: errorDisplayDuration
            };

            // Broadcast toast event
            $rootScope.$broadcast('toast:show', toast);
        }

        function showRecoveryDialog(errorInfo) {
            // Broadcast recovery dialog event
            $rootScope.$broadcast('recovery-dialog:show', errorInfo);
        }

        // ==================== Configuration ====================

        function setErrorDisplayDuration(duration) {
            errorDisplayDuration = duration;
        }

        function setRetryConfig(operationType, config) {
            retryConfigs[operationType] = config;
        }

        // ==================== Helper Functions ====================

        function determineErrorType(error) {
            if (!error) return 'unknown';

            var message = (error.message || '').toLowerCase();
            var status = error.status || 0;

            if (status === 0 || message.includes('network')) {
                return 'network_error';
            } else if (status === 401 || message.includes('auth')) {
                return 'authentication_error';
            } else if (status === 400 || message.includes('validation')) {
                return 'validation_error';
            } else if (status >= 500) {
                return 'server_error';
            } else if (message.includes('session')) {
                return 'session_error';
            } else {
                return 'unknown';
            }
        }

        function getUserFriendlyMessage(errorType, error) {
            var messages = {
                'network_error': 'Network connection problem. Please check your internet connection.',
                'authentication_error': 'Authentication required. Please log in to continue.',
                'validation_error': 'Please check your input and try again.',
                'server_error': 'Server error. Please try again later.',
                'session_error': 'Your session has expired. Please refresh the page.',
                'feature_unavailable': 'This feature is temporarily unavailable.',
                'unknown': 'An unexpected error occurred. Please try again.'
            };

            return messages[errorType] || messages.unknown;
        }

        function isDevelopment() {
            return window.location.hostname === 'localhost' || 
                   window.location.hostname === '127.0.0.1' ||
                   window.location.hostname.includes('dev');
        }
    }
})();