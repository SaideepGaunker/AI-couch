/**
 * Integration tests for Enhanced Statistics Display
 */
describe('Enhanced Statistics Display', function() {
    'use strict';

    var $controller, $httpBackend, $rootScope;
    var AuthService, ApiService;
    var controller, mockScope;

    // Mock enhanced statistics data
    var mockEnhancedStats = {
        current_performance_score: 78,
        next_difficulty_level: 'advanced',
        difficulty_change_reason: 'Consistent high performance',
        performance_trend: [65, 70, 75, 78, 82],
        trend_direction: 'improving',
        average_scores: {
            content_quality: 80,
            body_language: 75,
            tone_confidence: 70
        }
    };

    var mockBasicStats = {
        total_sessions: 10,
        practice_hours: 5.5,
        avg_score: 78,
        improvement_rate: 12,
        sessions_this_week: 3,
        streak: 5
    };

    beforeEach(function() {
        module('interviewPrepApp');

        inject(function(_$controller_, _$httpBackend_, _$rootScope_, _AuthService_, _ApiService_) {
            $controller = _$controller_;
            $httpBackend = _$httpBackend_;
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

    describe('Enhanced Statistics Loading', function() {

        it('should load enhanced statistics successfully', function() {
            $httpBackend.expectGET('/api/v1/interviews/statistics').respond(200, mockBasicStats);
            $httpBackend.expectGET('/api/v1/interviews/statistics/enhanced').respond(200, mockEnhancedStats);
            $httpBackend.expectGET('/api/v1/interviews/?limit=5&skip=0&include_family_info=true').respond(200, []);

            createController();
            $httpBackend.flush();

            expect(controller.enhancedStats).toBeDefined();
            expect(controller.enhancedStats.current_performance_score).toBe(78);
            expect(controller.enhancedStats.next_difficulty_level).toBe('advanced');
            expect(controller.enhancedStats.trend_direction).toBe('improving');
            expect(controller.enhancedStats.performance_trend).toEqual([65, 70, 75, 78, 82]);
        });

        it('should map performance breakdown scores correctly', function() {
            $httpBackend.expectGET('/api/v1/interviews/statistics').respond(200, mockBasicStats);
            $httpBackend.expectGET('/api/v1/interviews/statistics/enhanced').respond(200, mockEnhancedStats);
            $httpBackend.expectGET('/api/v1/interviews/?limit=5&skip=0&include_family_info=true').respond(200, []);

            createController();
            $httpBackend.flush();

            expect(controller.enhancedStats.content_score).toBe(80);
            expect(controller.enhancedStats.body_language_score).toBe(75);
            expect(controller.enhancedStats.voice_score).toBe(70);
        });

        it('should handle enhanced statistics API error gracefully', function() {
            $httpBackend.expectGET('/api/v1/interviews/statistics').respond(200, mockBasicStats);
            $httpBackend.expectGET('/api/v1/interviews/statistics/enhanced').respond(500, 'Server Error');
            $httpBackend.expectGET('/api/v1/interviews/?limit=5&skip=0&include_family_info=true').respond(200, []);

            createController();
            $httpBackend.flush();

            // Should create fallback enhanced stats
            expect(controller.enhancedStats).toBeDefined();
            expect(controller.enhancedStats.current_performance_score).toBe(78); // From basic stats
            expect(controller.enhancedStats.next_difficulty_level).toBe('intermediate');
            expect(controller.enhancedStats.trend_direction).toBe('stable');
            expect(controller.enhancedStats.performance_trend).toEqual([]);
        });

        it('should handle missing average_scores in enhanced stats', function() {
            var statsWithoutBreakdown = angular.copy(mockEnhancedStats);
            delete statsWithoutBreakdown.average_scores;

            $httpBackend.expectGET('/api/v1/interviews/statistics').respond(200, mockBasicStats);
            $httpBackend.expectGET('/api/v1/interviews/statistics/enhanced').respond(200, statsWithoutBreakdown);
            $httpBackend.expectGET('/api/v1/interviews/?limit=5&skip=0&include_family_info=true').respond(200, []);

            createController();
            $httpBackend.flush();

            expect(controller.enhancedStats.content_score).toBe(0);
            expect(controller.enhancedStats.body_language_score).toBe(0);
            expect(controller.enhancedStats.voice_score).toBe(0);
        });
    });

    describe('Performance Trend Analysis', function() {

        beforeEach(function() {
            $httpBackend.expectGET('/api/v1/interviews/statistics').respond(200, mockBasicStats);
            $httpBackend.expectGET('/api/v1/interviews/statistics/enhanced').respond(200, mockEnhancedStats);
            $httpBackend.expectGET('/api/v1/interviews/?limit=5&skip=0&include_family_info=true').respond(200, []);

            createController();
            $httpBackend.flush();
        });

        it('should display performance trend correctly', function() {
            expect(controller.enhancedStats.performance_trend).toEqual([65, 70, 75, 78, 82]);
            expect(controller.enhancedStats.trend_direction).toBe('improving');
        });

        it('should show current performance score', function() {
            expect(controller.enhancedStats.current_performance_score).toBe(78);
        });

        it('should display next difficulty level', function() {
            expect(controller.enhancedStats.next_difficulty_level).toBe('advanced');
            expect(controller.enhancedStats.difficulty_change_reason).toBe('Consistent high performance');
        });
    });

    describe('Performance Breakdown Display', function() {

        beforeEach(function() {
            $httpBackend.expectGET('/api/v1/interviews/statistics').respond(200, mockBasicStats);
            $httpBackend.expectGET('/api/v1/interviews/statistics/enhanced').respond(200, mockEnhancedStats);
            $httpBackend.expectGET('/api/v1/interviews/?limit=5&skip=0&include_family_info=true').respond(200, []);

            createController();
            $httpBackend.flush();
        });

        it('should display content quality score', function() {
            expect(controller.enhancedStats.content_score).toBe(80);
        });

        it('should display body language score', function() {
            expect(controller.enhancedStats.body_language_score).toBe(75);
        });

        it('should display voice/tone score', function() {
            expect(controller.enhancedStats.voice_score).toBe(70);
        });
    });

    describe('Trend Direction Indicators', function() {

        it('should handle improving trend', function() {
            var improvingStats = angular.copy(mockEnhancedStats);
            improvingStats.trend_direction = 'improving';
            improvingStats.performance_trend = [60, 65, 70, 75, 80];

            $httpBackend.expectGET('/api/v1/interviews/statistics').respond(200, mockBasicStats);
            $httpBackend.expectGET('/api/v1/interviews/statistics/enhanced').respond(200, improvingStats);
            $httpBackend.expectGET('/api/v1/interviews/?limit=5&skip=0&include_family_info=true').respond(200, []);

            createController();
            $httpBackend.flush();

            expect(controller.enhancedStats.trend_direction).toBe('improving');
        });

        it('should handle declining trend', function() {
            var decliningStats = angular.copy(mockEnhancedStats);
            decliningStats.trend_direction = 'declining';
            decliningStats.performance_trend = [80, 75, 70, 65, 60];

            $httpBackend.expectGET('/api/v1/interviews/statistics').respond(200, mockBasicStats);
            $httpBackend.expectGET('/api/v1/interviews/statistics/enhanced').respond(200, decliningStats);
            $httpBackend.expectGET('/api/v1/interviews/?limit=5&skip=0&include_family_info=true').respond(200, []);

            createController();
            $httpBackend.flush();

            expect(controller.enhancedStats.trend_direction).toBe('declining');
        });

        it('should handle stable trend', function() {
            var stableStats = angular.copy(mockEnhancedStats);
            stableStats.trend_direction = 'stable';
            stableStats.performance_trend = [75, 74, 76, 75, 75];

            $httpBackend.expectGET('/api/v1/interviews/statistics').respond(200, mockBasicStats);
            $httpBackend.expectGET('/api/v1/interviews/statistics/enhanced').respond(200, stableStats);
            $httpBackend.expectGET('/api/v1/interviews/?limit=5&skip=0&include_family_info=true').respond(200, []);

            createController();
            $httpBackend.flush();

            expect(controller.enhancedStats.trend_direction).toBe('stable');
        });
    });

    describe('Difficulty Level Recommendations', function() {

        it('should recommend beginner difficulty for low scores', function() {
            var beginnerStats = angular.copy(mockEnhancedStats);
            beginnerStats.current_performance_score = 35;
            beginnerStats.next_difficulty_level = 'beginner';
            beginnerStats.difficulty_change_reason = 'Performance below threshold';

            $httpBackend.expectGET('/api/v1/interviews/statistics').respond(200, mockBasicStats);
            $httpBackend.expectGET('/api/v1/interviews/statistics/enhanced').respond(200, beginnerStats);
            $httpBackend.expectGET('/api/v1/interviews/?limit=5&skip=0&include_family_info=true').respond(200, []);

            createController();
            $httpBackend.flush();

            expect(controller.enhancedStats.next_difficulty_level).toBe('beginner');
            expect(controller.enhancedStats.current_performance_score).toBe(35);
        });

        it('should recommend intermediate difficulty for medium scores', function() {
            var intermediateStats = angular.copy(mockEnhancedStats);
            intermediateStats.current_performance_score = 65;
            intermediateStats.next_difficulty_level = 'intermediate';
            intermediateStats.difficulty_change_reason = 'Steady improvement';

            $httpBackend.expectGET('/api/v1/interviews/statistics').respond(200, mockBasicStats);
            $httpBackend.expectGET('/api/v1/interviews/statistics/enhanced').respond(200, intermediateStats);
            $httpBackend.expectGET('/api/v1/interviews/?limit=5&skip=0&include_family_info=true').respond(200, []);

            createController();
            $httpBackend.flush();

            expect(controller.enhancedStats.next_difficulty_level).toBe('intermediate');
            expect(controller.enhancedStats.current_performance_score).toBe(65);
        });

        it('should recommend advanced difficulty for high scores', function() {
            var advancedStats = angular.copy(mockEnhancedStats);
            advancedStats.current_performance_score = 85;
            advancedStats.next_difficulty_level = 'advanced';
            advancedStats.difficulty_change_reason = 'Excellent performance';

            $httpBackend.expectGET('/api/v1/interviews/statistics').respond(200, mockBasicStats);
            $httpBackend.expectGET('/api/v1/interviews/statistics/enhanced').respond(200, advancedStats);
            $httpBackend.expectGET('/api/v1/interviews/?limit=5&skip=0&include_family_info=true').respond(200, []);

            createController();
            $httpBackend.flush();

            expect(controller.enhancedStats.next_difficulty_level).toBe('advanced');
            expect(controller.enhancedStats.current_performance_score).toBe(85);
        });
    });

    describe('Empty State Handling', function() {

        it('should handle empty performance trend gracefully', function() {
            var emptyStats = angular.copy(mockEnhancedStats);
            emptyStats.performance_trend = [];

            $httpBackend.expectGET('/api/v1/interviews/statistics').respond(200, mockBasicStats);
            $httpBackend.expectGET('/api/v1/interviews/statistics/enhanced').respond(200, emptyStats);
            $httpBackend.expectGET('/api/v1/interviews/?limit=5&skip=0&include_family_info=true').respond(200, []);

            createController();
            $httpBackend.flush();

            expect(controller.enhancedStats.performance_trend).toEqual([]);
        });

        it('should handle null enhanced stats', function() {
            $httpBackend.expectGET('/api/v1/interviews/statistics').respond(200, mockBasicStats);
            $httpBackend.expectGET('/api/v1/interviews/statistics/enhanced').respond(200, null);
            $httpBackend.expectGET('/api/v1/interviews/?limit=5&skip=0&include_family_info=true').respond(200, []);

            createController();
            $httpBackend.flush();

            expect(controller.enhancedStats).toBeDefined();
            expect(controller.enhancedStats.current_performance_score).toBe(78); // Fallback to basic stats
        });
    });
});