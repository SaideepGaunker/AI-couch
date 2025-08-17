/**
 * Authentication Service
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .service('AuthService', AuthService);

    AuthService.$inject = ['$q', '$location', 'ApiService'];

    function AuthService($q, $location, ApiService) {
        var service = {
            login: login,
            register: register,
            logout: logout,
            forgotPassword: forgotPassword,
            resetPassword: resetPassword,
            isAuthenticated: isAuthenticated,
            validateToken: validateToken,
            getCurrentUser: getCurrentUser,
            updateUser: updateUser,
            requireAuth: requireAuth,
            refreshToken: refreshToken,
            isProtectedRoute: isProtectedRoute
        };

        return service;

        function login(credentials) {
            return ApiService.post('/auth/login', credentials)
                .then(function(response) {
                    if (response.access_token) {
                        localStorage.setItem('access_token', response.access_token);
                        localStorage.setItem('refresh_token', response.refresh_token);
                        localStorage.setItem('user', JSON.stringify(response.user));
                        localStorage.setItem('last_login', Date.now().toString());
                        
                        return response;
                    }
                    return $q.reject('Invalid response');
                });
        }

        function register(userData) {
            return ApiService.post('/auth/register', userData)
                .then(function(response) {
                    return response;
                });
        }

        function logout() {
            // Clear all stored data first
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user');
            localStorage.removeItem('last_login');
            
            // Then call backend logout
            return ApiService.post('/auth/logout')
                .finally(function() {
                    $location.path('/');
                });
        }

        function forgotPassword(email) {
            return ApiService.post('/auth/forgot-password', { email: email });
        }

        function resetPassword(token, newPassword) {
            return ApiService.post('/auth/reset-password', {
                token: token,
                new_password: newPassword
            });
        }

        function refreshToken() {
            var refreshToken = localStorage.getItem('refresh_token');
            if (!refreshToken) {
                return $q.reject('No refresh token available');
            }

            return ApiService.post('/auth/refresh', { refresh_token: refreshToken })
                .then(function(response) {
                    if (response.access_token) {
                        localStorage.setItem('access_token', response.access_token);
                        localStorage.setItem('refresh_token', response.refresh_token);
                        return response;
                    }
                    return $q.reject('Invalid refresh response');
                })
                .catch(function(error) {
                    // If refresh fails, clear storage without calling logout to avoid recursion
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('refresh_token');
                    localStorage.removeItem('user');
                    localStorage.removeItem('last_login');
                    return $q.reject(error);
                });
        }

        function isAuthenticated() {
            var token = localStorage.getItem('access_token');
            var user = localStorage.getItem('user');
            
            // Must have both token and user data
            if (!token || !user) {
                return false;
            }
            
            // For development, be more lenient with token validation
            // In production, you might want stricter validation
            try {
                // Basic token format validation
                var parts = token.split('.');
                if (parts.length !== 3) {
                    clearAuthData();
                    return false;
                }
                
                // Try to decode payload to check expiration
                var payload = JSON.parse(atob(parts[1]));
                var currentTime = Math.floor(Date.now() / 1000);
                
                // Add generous buffer for development (30 minutes)
                var bufferTime = 30 * 60; // 30 minutes
                
                // If token is expired (with buffer), try to refresh or return false
                if (payload.exp && payload.exp < (currentTime - bufferTime)) {
                    return false;
                }
                
                return true;
            } catch (e) {
                // If we can't decode the token, but it exists, assume it's valid for now
                // This helps with development when tokens might not be proper JWTs
                return true; // Be lenient in development
            }
        }
        
        function clearAuthData() {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user');
            localStorage.removeItem('last_login');
        }

        function getCurrentUser() {
            var userStr = localStorage.getItem('user');
            return userStr ? JSON.parse(userStr) : null;
        }

        function updateUser(userData) {
            localStorage.setItem('user', JSON.stringify(userData));
        }

        function validateToken() {
            var token = localStorage.getItem('access_token');
            if (!token) {
                return $q.reject('No token available');
            }
            
            // Validate token with backend
            return ApiService.post('/auth/validate-token')
                .then(function(response) {
                    return response;
                })
                .catch(function(error) {
                    // Token is invalid, clear storage without calling logout to avoid recursion
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('refresh_token');
                    localStorage.removeItem('user');
                    localStorage.removeItem('last_login');
                    return $q.reject(error);
                });
        }
        
        function isProtectedRoute(path) {
            var protectedRoutes = ['/dashboard', '/interview', '/progress', '/profile'];
            return protectedRoutes.includes(path);
        }
        
        function requireAuth() {
            if (!isAuthenticated()) {
                // Check if we have a refresh token and try to refresh
                var refreshTokenValue = localStorage.getItem('refresh_token');
                if (refreshTokenValue) {
                    return refreshToken()
                        .then(function() {
                            return $q.resolve();
                        })
                        .catch(function(error) {
                            // Refresh failed, redirect to login
                            $location.path('/login');
                            return $q.reject('Authentication required');
                        });
                } else {
                    // No refresh token, redirect to login
                    $location.path('/login');
                    return $q.reject('Authentication required');
                }
            }
            
            // User is authenticated, return success immediately
            return $q.resolve();
        }
    }
})();