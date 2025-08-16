/**
 * Main AngularJS application module
 */
(function() {
    'use strict';

    angular.module('interviewPrepApp', [
        'ngRoute',
        'ngAnimate',
        'ngSanitize'
    ])
    .config(['$routeProvider', '$locationProvider', '$httpProvider', function($routeProvider, $locationProvider, $httpProvider) {
        // Re-enable auth interceptor now that loading is fixed
        $httpProvider.interceptors.push('AuthInterceptor');
        $routeProvider
            .when('/', {
                template: '<home-component></home-component>'
            })
            .when('/login', {
                template: '<login-component></login-component>'
            })
            .when('/register', {
                template: '<register-component></register-component>'
            })
            .when('/dashboard', {
                template: '<dashboard-component></dashboard-component>'
            })
            .when('/interview', {
                template: '<interview-setup-component></interview-setup-component>'
            })
            .when('/interview-chat', {
                template: '<interview-chat-component></interview-chat-component>'
            })
            .when('/test', {
                template: '<test-component></test-component>'
            })
            .when('/progress', {
                template: '<progress-component></progress-component>'
            })
            .when('/profile', {
                template: '<profile-component></profile-component>'
            })
            .when('/feedback/:sessionId', {
                template: '<feedback-component></feedback-component>'
            })
            .when('/debug', {
                template: '<div class="container mt-4"><h2>Debug Page</h2><div class="card"><div class="card-body"><h5>Authentication Status</h5><p><strong>Authenticated:</strong> {{isAuth}}</p><p><strong>Access Token:</strong> {{token ? "Present" : "Missing"}}</p><p><strong>User Data:</strong> {{user ? user.email : "Missing"}}</p><button class="btn btn-primary me-2" onclick="window.mockLogin()">Mock Login</button><button class="btn btn-secondary me-2" onclick="window.clearAuth()">Clear Auth</button><button class="btn btn-info" onclick="window.debugAuth()">Debug Auth</button></div></div></div>',
                controller: ['$scope', 'AuthService', function($scope, AuthService) {
                    $scope.isAuth = AuthService.isAuthenticated();
                    $scope.token = localStorage.getItem('access_token');
                    $scope.user = AuthService.getCurrentUser();
                }]
            })
            .otherwise({
                redirectTo: '/'
            });

        // Enable HTML5 mode
        $locationProvider.html5Mode(false);
    }])
    .run(['$rootScope', '$location', 'AuthService', function($rootScope, $location, AuthService) {
        // Handle route change start
        $rootScope.$on('$routeChangeStart', function(event, next, current) {
            var targetPath = next.originalPath;
            var isAuthenticated = AuthService.isAuthenticated();
            
            console.log('Route change start:', {
                from: current ? current.originalPath : 'none',
                to: targetPath,
                authenticated: isAuthenticated
            });
            
            // Check if route requires authentication
            var protectedRoutes = ['/dashboard', '/interview', '/interview-chat', '/test', '/progress', '/profile', '/feedback'];
            var isProtectedRoute = protectedRoutes.some(function(route) {
                return targetPath === route || targetPath.startsWith(route + '/');
            });
            
            if (isProtectedRoute && !isAuthenticated) {
                console.log('Protected route accessed without authentication, redirecting to login');
                event.preventDefault();
                $location.path('/login');
            }
        });
        
        // Handle route change errors (mainly authentication failures)
        $rootScope.$on('$routeChangeError', function(event, current, previous, rejection) {
            console.log('Route change error:', rejection);
            console.log('Current route:', current ? current.originalPath : 'none');
            console.log('Previous route:', previous ? previous.originalPath : 'none');
            
            if (rejection === 'Authentication required') {
                console.log('Authentication required, redirecting to login');
                $location.path('/login');
            }
        });
        
        // Handle successful route changes
        $rootScope.$on('$routeChangeSuccess', function(event, current, previous) {
            if (current && current.originalPath) {
                console.log('Route change successful:', {
                    from: previous ? previous.originalPath : 'none',
                    to: current.originalPath,
                    authenticated: AuthService.isAuthenticated()
                });
            }
        });
        
        // Add global logout function
        $rootScope.logout = function() {
            if (confirm('Are you sure you want to logout?')) {
                AuthService.logout();
            }
        };
        
        // Add debug function to check auth state
        $rootScope.debugAuth = function() {
            console.log('=== Authentication Debug Info ===');
            console.log('Current path:', $location.path());
            console.log('Is authenticated:', AuthService.isAuthenticated());
            console.log('Is protected route:', AuthService.isProtectedRoute($location.path()));
            console.log('Access token exists:', !!localStorage.getItem('access_token'));
            console.log('Refresh token exists:', !!localStorage.getItem('refresh_token'));
            console.log('User data exists:', !!localStorage.getItem('user'));
            console.log('Current user:', AuthService.getCurrentUser());
            console.log('================================');
        };
        
        // Make debug function available globally
        window.debugAuth = $rootScope.debugAuth;
        
        // Development helper: Mock login function
        window.mockLogin = function() {
            console.log('Creating mock login session...');
            localStorage.setItem('access_token', 'mock-jwt-token-for-development');
            localStorage.setItem('refresh_token', 'mock-refresh-token');
            localStorage.setItem('user', JSON.stringify({
                id: 1,
                email: 'test@example.com',
                name: 'Test User',
                role: 'job_seeker'
            }));
            localStorage.setItem('last_login', Date.now().toString());
            console.log('Mock login created. Try navigating to /interview now.');
            window.location.reload();
        };
        
        // Development helper: Clear auth data
        window.clearAuth = function() {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('user');
            localStorage.removeItem('last_login');
            console.log('Auth data cleared');
            window.location.reload();
        };
        
        console.log('Development helpers available:');
        console.log('- window.debugAuth() - Check auth state');
        console.log('- window.mockLogin() - Create mock login session');
        console.log('- window.clearAuth() - Clear auth data');
    }]);
})();