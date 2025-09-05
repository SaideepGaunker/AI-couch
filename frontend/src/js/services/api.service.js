/**
 * Enhanced API Service for HTTP requests with comprehensive error handling
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .service('ApiService', ApiService);

    ApiService.$inject = ['$http', '$q', '$rootScope', 'ErrorHandlingService'];

    function ApiService($http, $q, $rootScope, ErrorHandlingService) {
        var service = {
            baseUrl: 'http://localhost:8000/api/v1',
            get: get,
            post: post,
            put: put,
            delete: deleteRequest,
            
            // Enhanced methods
            getWithFallback: getWithFallback,
            postWithRetry: postWithRetry,
            putWithRetry: putWithRetry,
            
            // Configuration
            setBaseUrl: setBaseUrl,
            setTimeout: setTimeout,
            
            // Status
            isOnline: isOnline,
            getRequestStats: getRequestStats
        };

        // Private variables
        var requestTimeout = 30000; // 30 seconds
        var requestStats = {
            total: 0,
            successful: 0,
            failed: 0,
            retries: 0
        };
        var onlineStatus = navigator.onLine;

        // Initialize
        init();

        return service;

        // ==================== Initialization ====================

        function init() {
            // Monitor online status
            window.addEventListener('online', function() {
                onlineStatus = true;
                $rootScope.$broadcast('network:online');
            });

            window.addEventListener('offline', function() {
                onlineStatus = false;
                $rootScope.$broadcast('network:offline');
            });
        }

        // ==================== Core HTTP Methods ====================

        function get(endpoint, params, options) {
            options = options || {};
            
            var config = {
                params: params || {},
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                timeout: options.timeout || requestTimeout
            };
            
            // Broadcast request start
            $rootScope.$broadcast('api:request:start', {
                method: 'GET',
                endpoint: endpoint,
                message: options.loadingMessage
            });
            
            return makeRequest('GET', endpoint, null, config, options);
        }

        function post(endpoint, data, options) {
            options = options || {};
            
            var config = {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                timeout: options.timeout || requestTimeout
            };
            
            // Broadcast request start
            $rootScope.$broadcast('api:request:start', {
                method: 'POST',
                endpoint: endpoint,
                message: options.loadingMessage
            });
            
            return makeRequest('POST', endpoint, data, config, options);
        }

        function put(endpoint, data, options) {
            options = options || {};
            
            var config = {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                timeout: options.timeout || requestTimeout
            };
            
            // Broadcast request start
            $rootScope.$broadcast('api:request:start', {
                method: 'PUT',
                endpoint: endpoint,
                message: options.loadingMessage
            });
            
            return makeRequest('PUT', endpoint, data, config, options);
        }

        function deleteRequest(endpoint, options) {
            options = options || {};
            
            var config = {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                timeout: options.timeout || requestTimeout
            };
            
            // Broadcast request start
            $rootScope.$broadcast('api:request:start', {
                method: 'DELETE',
                endpoint: endpoint,
                message: options.loadingMessage
            });
            
            return makeRequest('DELETE', endpoint, null, config, options);
        }

        // ==================== Enhanced Methods ====================

        function getWithFallback(endpoint, params, fallbackData, options) {
            return ErrorHandlingService.executeWithFallback(
                function() {
                    return get(endpoint, params, options);
                },
                function() {
                    return $q.resolve(fallbackData);
                },
                {
                    operation: 'api_get_with_fallback',
                    endpoint: endpoint
                }
            );
        }

        function postWithRetry(endpoint, data, options) {
            options = options || {};
            
            return ErrorHandlingService.retryOperation(
                function() {
                    return post(endpoint, data, options);
                },
                'api',
                {
                    operation: 'api_post_with_retry',
                    endpoint: endpoint
                }
            );
        }

        function putWithRetry(endpoint, data, options) {
            options = options || {};
            
            return ErrorHandlingService.retryOperation(
                function() {
                    return put(endpoint, data, options);
                },
                'api',
                {
                    operation: 'api_put_with_retry',
                    endpoint: endpoint
                }
            );
        }

        // ==================== Core Request Handler ====================

        function makeRequest(method, endpoint, data, config, options) {
            options = options || {};
            requestStats.total++;

            // Check online status
            if (!onlineStatus && !options.allowOffline) {
                var offlineError = {
                    status: 0,
                    statusText: 'Network Offline',
                    data: { detail: 'No internet connection available' }
                };
                
                $rootScope.$broadcast('api:request:end', { success: false });
                return handleError(offlineError, endpoint, options);
            }

            var url = service.baseUrl + endpoint;
            var httpPromise;

            // Make HTTP request based on method
            switch (method.toUpperCase()) {
                case 'GET':
                    httpPromise = $http.get(url, config);
                    break;
                case 'POST':
                    httpPromise = $http.post(url, data, config);
                    break;
                case 'PUT':
                    httpPromise = $http.put(url, data, config);
                    break;
                case 'DELETE':
                    httpPromise = $http.delete(url, config);
                    break;
                default:
                    return $q.reject(new Error('Unsupported HTTP method: ' + method));
            }

            return httpPromise
                .then(function(response) {
                    return handleSuccess(response, endpoint, options);
                })
                .catch(function(error) {
                    return handleError(error, endpoint, options);
                });
        }

        function handleSuccess(response, endpoint, options) {
            requestStats.successful++;
            
            // Broadcast request end
            $rootScope.$broadcast('api:request:end', { 
                success: true,
                endpoint: endpoint 
            });

            // Show success message if requested
            if (options.successMessage) {
                $rootScope.$broadcast('success:occurred', {
                    message: options.successMessage
                });
            }

            return response.data;
        }

        function handleError(error, endpoint, options) {
            requestStats.failed++;
            
            // Broadcast request end
            $rootScope.$broadcast('api:request:end', { 
                success: false,
                endpoint: endpoint,
                error: error 
            });

            // Create error context
            var context = {
                endpoint: endpoint,
                method: options.method || 'unknown',
                timestamp: new Date().toISOString(),
                userAgent: navigator.userAgent,
                online: onlineStatus
            };

            // Handle the error through ErrorHandlingService
            var processedError = ErrorHandlingService.handleApiError(error, context);

            // Don't show error toast if explicitly disabled
            if (options.suppressErrorToast !== true) {
                // Error will be shown by ErrorHandlingService
            }

            return $q.reject(processedError);
        }

        // ==================== Configuration Methods ====================

        function setBaseUrl(url) {
            service.baseUrl = url;
        }

        function setTimeout(timeout) {
            requestTimeout = timeout;
        }

        // ==================== Status Methods ====================

        function isOnline() {
            return onlineStatus;
        }

        function getRequestStats() {
            return {
                ...requestStats,
                successRate: requestStats.total > 0 ? 
                    (requestStats.successful / requestStats.total * 100).toFixed(2) + '%' : '0%'
            };
        }

        // ==================== Utility Methods ====================

        function createRequestOptions(options) {
            return {
                loadingMessage: options.loadingMessage,
                successMessage: options.successMessage,
                suppressErrorToast: options.suppressErrorToast,
                timeout: options.timeout,
                headers: options.headers,
                allowOffline: options.allowOffline,
                retryable: options.retryable !== false
            };
        }

        // ==================== Public Convenience Methods ====================

        service.safeGet = function(endpoint, params, fallbackData) {
            return getWithFallback(endpoint, params, fallbackData, {
                suppressErrorToast: true
            });
        };

        service.silentPost = function(endpoint, data) {
            return post(endpoint, data, {
                suppressErrorToast: true,
                loadingMessage: null
            });
        };

        service.criticalPost = function(endpoint, data, successMessage) {
            return postWithRetry(endpoint, data, {
                successMessage: successMessage,
                loadingMessage: 'Processing...'
            });
        };

        service.quickGet = function(endpoint, params) {
            return get(endpoint, params, {
                timeout: 5000, // 5 second timeout
                suppressErrorToast: true
            });
        };
    }
})();