/**
 * Unit tests for Enhanced Dashboard Component (Session History UI)
 */
describe('Enhanced Dashboard Component', function() {
    'use strict';

    var $controller, $httpBackend, $location, $rootScope;
    var AuthService, ApiService;
    var controller, mockScope;

    // Mock session data with family info
    var mockSessionsWithFamily = [
        {
            id: 1,
            created_at: '2024-01-15T10:00:00Z',
            target_role: 'Software Developer',
            session_type: 'technical',
            difficulty_level: 'medium',
            overall_score: 85,
            performance_score: 80,
            duration: 30,
            status: 'completed',
            family_info: {
                is_original: true,
                practice_count: 2,
                has_practices: true,
                original_session_id: 1,
                session_family_size: 3
            },
            hierarchical_role: {
                main_role: 'Software Developer',
                sub_role: 'Frontend Developer',
                specialization: 'React Developer'
            }
        },
        {
            id: 2,
            created_at: '2024-01-16T14:00:00Z',
            target_role: 'Software Developer',
            session_type: 'technical',
            difficulty_level: 'medium',
            overall_score: 90,
            performance_score: 88,
            duration: 30,
            status: 'completed',
            parent_session_id: 1,
            family_info: {
                is_original: false,
                is_practice: true,
                original_session_id: 1,
                original_session_role: 'Software Developer',
                practice_number: 1,
                session_family_size: 3
            }
        }
    ];

    var mockStats = {
        total_sessions: 5,
        practice_hours: 2.5,
        avg_score: 82,
        improvement_rate: 15,
        sessions_this_week: 3,
        streak: 7
    };

    beforeEach(function() {
        module('interviewPrepApp');

        inject(function(_$controller_, _$httpBackend_, _$location_, _$rootScope_, _AuthService_, _ApiService_) {
            $controller = _$controller_;
            $httpBackend = _$httpBackend_;
            $location = _$location_;
            $rootScope = _$rootScope_;
            AuthService = _AuthService_;
            ApiService = _ApiService_;
        });

        mockScope = $rootScope.$new();

        // Mock AuthService
        spyOn(AuthService, 'isAuthenticated').and.returnValue(true);
        spyOn(AuthService, 'getCurrentUser').and.returnValue({
            id: 1,
            name: 'Test User',
            email: 'test@example.com'
        });
    });

    afterEach(function() {
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
    });

    function createController() {
        controller = $controller('DashboardController', {
            $scope: mockScope,
            AuthService: AuthService,
            ApiService: ApiService
        });
        return controller;
    }

    describe('Enhanced Session Loading', function() {

        it('should load sessions with family information', function() {
            $httpBackend.expectGET('/api/v1/interviews/statistics').respond(200, mockStats);
            $httpBackend.expectGET('/api/v1/interviews/?limit=5&skip=0&include_family_info=true')
                .respond(200, mockSessionsWithFamily);

            createController();
            $httpBackend.flush();

            expect(controller.recentSessions).toEqual(mockSessionsWithFamily);
            expect(controller.recentSessions[0].family_info.is_original).toBe(true);
            expect(controller.recentSessions[1].family_info.is_practice).toBe(true);
        });

        it('should handle sessions without family info gracefully', function() {
            var sessionsWithoutFamily = [
                {
                    id: 1,
                    created_at: '2024-01-15T10:00:00Z',
                    target_role: 'Software Developer',
                    session_type: 'technical',
                    overall_score: 85,
                    duration: 30,
                    status: 'completed'
                }
            ];

            $httpBackend.expectGET('/api/v1/interviews/statistics').respond(200, mockStats);
            $httpBackend.expectGET('/api/v1/interviews/?limit=5&skip=0&include_family_info=true')
                .respond(200, sessionsWithoutFamily);

            createController();
            $httpBackend.flush();

            expect(controller.recentSessions).toEqual(sessionsWithoutFamily);
            expect(controller.recentSessions[0].family_info).toBeUndefined();
        });

        it('should map backend stats to frontend structure correctly', function() {
            $httpBackend.expectGET('/api/v1/interviews/statistics').respond(200, mockStats);
            $httpBackend.expectGET('/api/v1/interviews/?limit=5&skip=0&include_family_info=true')
                .respond(200, []);

            createController();
            $httpBackend.flush();

            expect(controller.stats.total_sessions).toBe(5);
            expect(controller.stats.total_time).toBe(2.5); // practice_hours mapped to total_time
            expect(controller.stats.avg_score).toBe(82);
            expect(controller.stats.improvement).toBe(15); // improvement_rate mapped to improvement
            expect(controller.stats.sessions_this_week).toBe(3);
            expect(controller.stats.streak).toBe(7);
        });
    });

    describe('Practice Again Functionality', function() {

        beforeEach(function() {
            $httpBackend.expectGET('/api/v1/interviews/statistics').respond(200, mockStats);
            $httpBackend.expectGET('/api/v1/interviews/?limit=5&skip=0&include_family_info=true')
                .respond(200, mockSessionsWithFamily);

            createController();
            $httpBackend.flush();
        });

        it('should create practice session successfully', function() {
            var mockPracticeResponse = {
                message: 'Practice session created successfully',
                practice_session_id: 3,
                original_session_id: 1,
                session_mode: 'practice_again'
            };

            $httpBackend.expectPOST('/api/v1/interviews/1/practice-again', {
                generate_fresh_questions: true
            }).respond(200, mockPracticeResponse);

            spyOn($location, 'path').and.returnValue($location);
            spyOn($location, 'search').and.returnValue($location);

            controller.practiceAgain(mockSessionsWithFamily[0]);
            $httpBackend.flush();

            expect($location.path).toHaveBeenCalledWith('/interview-chat');
            expect($location.search).toHaveBeenCalledWith({
                sessionId: 3,
                isPractice: true,
                originalSessionId: 1
            });
        });

        it('should handle practice again API error', function() {
            $httpBackend.expectPOST('/api/v1/interviews/1/practice-again', {
                generate_fresh_questions: true
            }).respond(404, { detail: 'Session not found' });

            controller.practiceAgain(mockSessionsWithFamily[0]);
            $httpBackend.flush();

            expect(controller.error).toBe('Session not found');
            expect(controller.loading).toBe(false);
        });

        it('should handle invalid session for practice again', function() {
            spyOn(console, 'error');

            controller.practiceAgain(null);

            expect(console.error).toHaveBeenCalledWith('Invalid session for practice again');
            expect(controller.loading).toBe(false);
        });

        it('should handle practice response without session ID', function() {
            var invalidResponse = {
                message: 'Practice session created successfully'
                // Missing practice_session_id
            };

            $httpBackend.expectPOST('/api/v1/interviews/1/practice-again', {
                generate_fresh_questions: true
            }).respond(200, invalidResponse);

            controller.practiceAgain(mockSessionsWithFamily[0]);
            $httpBackend.flush();

            expect(controller.error).toBe('Failed to create practice session');
        });
    });

    describe('Session Display Logic', function() {

        it('should identify original sessions correctly', function() {
            createController();
            
            var originalSession = mockSessionsWithFamily[0];
            expect(originalSession.family_info.is_original).toBe(true);
            expect(originalSession.family_info.has_practices).toBe(true);
            expect(originalSession.family_info.practice_count).toBe(2);
        });

        it('should identify practice sessions correctly', function() {
            createController();
            
            var practiceSession = mockSessionsWithFamily[1];
            expect(practiceSession.family_info.is_practice).toBe(true);
            expect(practiceSession.family_info.original_session_id).toBe(1);
            expect(practiceSession.family_info.practice_number).toBe(1);
        });

        it('should display hierarchical role information', function() {
            createController();
            
            var sessionWithHierarchy = mockSessionsWithFamily[0];
            expect(sessionWithHierarchy.hierarchical_role.main_role).toBe('Software Developer');
            expect(sessionWithHierarchy.hierarchical_role.sub_role).toBe('Frontend Developer');
            expect(sessionWithHierarchy.hierarchical_role.specialization).toBe('React Developer');
        });
    });

    describe('Error Handling', function() {

        it('should handle statistics loading error gracefully', function() {
            $httpBackend.expectGET('/api/v1/interviews/statistics').respond(500, 'Server Error');
            $httpBackend.expectGET('/api/v1/interviews/?limit=5&skip=0&include_family_info=true')
                .respond(200, []);

            createController();
            $httpBackend.flush();

            // Should use default stats values
            expect(controller.stats.total_sessions).toBe(0);
            expect(controller.stats.avg_score).toBe(0);
            expect(controller.loading).toBe(false);
        });

        it('should handle sessions loading error gracefully', function() {
            $httpBackend.expectGET('/api/v1/interviews/statistics').respond(200, mockStats);
            $httpBackend.expectGET('/api/v1/interviews/?limit=5&skip=0&include_family_info=true')
                .respond(500, 'Server Error');

            createController();
            $httpBackend.flush();

            expect(controller.recentSessions).toEqual([]);
            expect(controller.loading).toBe(false);
        });
    });

    describe('Navigation', function() {

        beforeEach(function() {
            createController();
        });

        it('should navigate to interview setup', function() {
            spyOn($location, 'path');

            controller.startInterview();

            expect($location.path).toHaveBeenCalledWith('/interview');
        });

        it('should navigate to progress page', function() {
            spyOn($location, 'path');

            controller.viewProgress();

            expect($location.path).toHaveBeenCalledWith('/progress');
        });
    });

    describe('Authentication', function() {

        it('should redirect to login if not authenticated', function() {
            AuthService.isAuthenticated.and.returnValue(false);
            spyOn($location, 'path');

            createController();

            expect($location.path).toHaveBeenCalledWith('/login');
        });
    });
});