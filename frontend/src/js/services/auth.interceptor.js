/**
 * HTTP Interceptor for handling authentication tokens and automatic refresh
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .factory('AuthInterceptor', AuthInterceptor);

    AuthInterceptor.$inject = ['$q', '$injector', '$location'];

    function AuthInterceptor($q, $injector, $location) {
        var isRefreshing = false;
        var failedQueue = [];

        function processQueue(error, token) {
            failedQueue.forEach(function(prom) {
                if (error) {
                    prom.reject(error);
                } else {
                    prom.resolve(token);
                }
            });
            
            failedQueue = [];
        }

        return {
            request: request,
            responseError: responseError
        };

        function request(config) {
            var token = localStorage.getItem('access_token');
            if (token) {
                config.headers = config.headers || {};
                config.headers.Authorization = 'Bearer ' + token;
            }
            return config;
        }

        function responseError(rejection) {
            var originalRequest = rejection.config;

            // If the error is 401 and we haven't already tried to refresh the token
            if (rejection.status === 401 && !originalRequest._retry) {
                if (isRefreshing) {
                    // If we're already refreshing, queue this request
                    return $q(function(resolve, reject) {
                        failedQueue.push({ resolve: resolve, reject: reject });
                    }).then(function(token) {
                        originalRequest.headers.Authorization = 'Bearer ' + token;
                        return $injector.get('$http')(originalRequest);
                    });
                }

                originalRequest._retry = true;
                isRefreshing = true;

                var refreshToken = localStorage.getItem('refresh_token');
                if (!refreshToken) {
                    // No refresh token, clear storage and redirect to login
                    clearAuthData();
                    $location.path('/login');
                    return $q.reject(rejection);
                }

                // Try to refresh the token
                return $injector.get('$http').post('http://localhost:8000/api/v1/auth/refresh', {
                    refresh_token: refreshToken
                }).then(function(response) {
                    if (response.data.access_token) {
                        localStorage.setItem('access_token', response.data.access_token);
                        localStorage.setItem('refresh_token', response.data.refresh_token);
                        
                        // Update the original request with new token
                        originalRequest.headers.Authorization = 'Bearer ' + response.data.access_token;
                        
                        // Process queued requests
                        processQueue(null, response.data.access_token);
                        
                        // Retry the original request
                        return $injector.get('$http')(originalRequest);
                    } else {
                        throw new Error('Invalid refresh response');
                    }
                }).catch(function(error) {
                    // Refresh failed, clear storage and redirect to login
                    processQueue(error, null);
                    clearAuthData();
                    $location.path('/login');
                    return $q.reject(rejection);
                }).finally(function() {
                    isRefreshing = false;
                });
            }

            return $q.reject(rejection);
        }

        function clearAuthData() {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user');
            localStorage.removeItem('last_login');
        }
    }
})();