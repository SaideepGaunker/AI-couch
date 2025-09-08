/**
 * Unified Practice Controller Integration Tests
 * 
 * Tests to verify that the UnifiedPracticeController is properly integrated
 * and provides consistent behavior across different navigation paths.
 */
describe('UnifiedPracticeController Integration', function() {
    'use strict';

    var controller, $rootScope, $location, $q, UnifiedDifficultyStateService, 
        SessionDataService, AuthService, DifficultyDisplayService;
    var mockSession, mockDifficultyState, mockPracticeResponse;

    beforeEach(function() {
        // Load the module
        module('interviewPrepApp');

        // Mock dependencies
        module(function($provide) {
            $provide.value('UnifiedDifficultyStateService', {
                getSessionDifficultyState: jasmine.createSpy('getSessionDifficultyState'),
                createPracticeSessionWithDifficulty: jasmine.createSpy('createPracticeSessionWithDifficulty')
            });

            $provide.value('SessionDataService', {
                setSessionData: jasmine.createSpy('setSessionData')
            });

            $provide.value('AuthService', {
                isAuthenticated: jasmine.createSpy('isAuthenticated').and.returnValue(true),
                getCurrentUser: jasmine.createSpy('getCurrentUser').and.returnValue({ id: 1, email: 'test@example.com' })
            });

            $provide.value('DifficultyDisplayService', {
                normalizeDifficultyInput: jasmine.createSpy('normalizeDifficultyInput').and.returnValue(3),
                getDifficultyInfo: jasmine.createSpy('getDifficultyInfo').and.returnValue({
                    label: 'Medium',
                    color: '#fd7e14',
                    icon: 'fas fa-balance-scale'
                })
            });
        });

        // Inject dependencies
        inject(function(_$controller_, _$rootScope_, _$location_, _$q_, 
                      _UnifiedDifficultyStateService_, _SessionDataService_, 
                      _AuthService_, _DifficultyDisplayService_) {
            $rootScope = _$rootScope_;
            $location = _$location_;
            $q = _$q_;
            UnifiedDifficultyStateService = _UnifiedDifficultyStateService_;
            SessionDataService = _SessionDataService_;
            AuthService = _AuthService_;
            DifficultyDisplayService = _DifficultyDisplayService_;

            // Create controller
            controller = _$controller_('UnifiedPracticeController', {
                $location: $location,
                $rootScope: $rootScope,
                $q: $q,
                UnifiedDifficultyStateService: UnifiedDifficultyStateService,
                SessionDataService: SessionDataService,
                AuthService: AuthService,
                DifficultyDisplayService: DifficultyDisplayService
            });
        });

        // Setup mock data
        mockSession = {
            id: 123,
            target_role: 'Software Engineer',
            duration: 30,
            question_count: 5,
            difficulty_level: 'medium'
        };

        mockDifficultyState = {
            session_id: 123,
            initial_difficulty: 'medium',
            current_difficulty: 'hard',
            final_difficulty: 'hard',
            difficulty_changes: [
                {
                    from_difficulty: 'medium',
                    to_difficulty: 'hard',
                    reason: 'good performance',
                    timestamp: '2025-01-01T12:00:00Z'
                }
            ],
            last_updated: '2025-01-01T12:00:00Z'
        };

        mockPracticeResponse = {
            session: {
                id: 456,
                target_role: 'Software Engineer',
                duration: 30,
                question_count: 5,
                difficulty_level: 'hard',
                parent_session_id: 123,
                session_mode: 'practice_again'
            },
            questions: [
                { id: 1, text: 'Test question 1' },
                { id: 2, text: 'Test question 2' }
            ],
            configuration: {
                enable_video: true,
                enable_audio: true
            },
            inherited_settings: {
                difficulty_level: 'hard',
                target_role: 'Software Engineer',
                duration: 30,
                question_count: 5
            },
            difficulty_validation: {
                isValid: true,
                errors: [],
                warnings: [],
                parentDifficultyInfo: {
                    initial: 'medium',
                    final: 'hard',
                    wasAdjusted: true
                },
                inheritedDifficulty: 'hard'
            },
            parent_session_info: {
                id: 123,
                initial_difficulty: 'medium',
                final_difficulty: 'hard',
                difficulty_was_adjusted: true
            }
        };
    });

    describe('Controller Initialization', function() {
        it('should initialize the controller successfully', function() {
            expect(controller).toBeDefined();
            expect(controller.createPracticeSession).toBeDefined();
            expect(controller.createPracticeSessionWithConfirmation).toBeDefined();
            expect(controller.validatePracticeSessionCreation).toBeDefined();
        });

        it('should listen for practice session request events', function() {
            spyOn(controller, 'createPracticeSession');
            
            $rootScope.$broadcast('practice:session:request', {
                parentSessionId: 123,
                options: { showLoading: true }
            });

            expect(controller.createPracticeSession).toHaveBeenCalledWith(123, { showLoading: true });
        });
    });

    describe('Practice Session Creation', function() {
        beforeEach(function() {
            UnifiedDifficultyStateService.getSessionDifficultyState.and.returnValue($q.resolve(mockDifficultyState));
            UnifiedDifficultyStateService.createPracticeSessionWithDifficulty.and.returnValue($q.resolve(mockPracticeResponse));
        });

        it('should validate parent session before creating practice session', function() {
            var validationPromise = controller.validatePracticeSessionCreation(123);
            $rootScope.$apply();

            expect(UnifiedDifficultyStateService.getSessionDifficultyState).toHaveBeenCalledWith(123, {
                suppressErrors: true
            });

            validationPromise.then(function(result) {
                expect(result.isValid).toBe(true);
                expect(result.errors.length).toBe(0);
                expect(result.difficultyState).toEqual(mockDifficultyState);
            });

            $rootScope.$apply();
        });

        it('should create practice session with proper difficulty inheritance', function() {
            var createPromise = controller.createPracticeSession(123, { showLoading: true });
            $rootScope.$apply();

            expect(UnifiedDifficultyStateService.createPracticeSessionWithDifficulty).toHaveBeenCalledWith(123, {
                showLoading: true,
                showSuccess: true
            });

            createPromise.then(function(response) {
                expect(response).toEqual(mockPracticeResponse);
                expect(SessionDataService.setSessionData).toHaveBeenCalledWith({
                    sessionId: 456,
                    questions: mockPracticeResponse.questions,
                    configuration: mockPracticeResponse.configuration,
                    inheritedSettings: mockPracticeResponse.inherited_settings,
                    adaptiveDifficulty: 'hard',
                    parentSessionId: 123,
                    isPracticeSession: true,
                    difficultyValidation: mockPracticeResponse.difficulty_validation
                });
            });

            $rootScope.$apply();
        });

        it('should handle authentication errors gracefully', function() {
            AuthService.isAuthenticated.and.returnValue(false);

            var createPromise = controller.createPracticeSession(123);
            var errorHandled = false;

            createPromise.catch(function(error) {
                expect(error.message).toContain('Authentication required');
                errorHandled = true;
            });

            $rootScope.$apply();
            expect(errorHandled).toBe(true);
        });

        it('should handle missing parent session ID', function() {
            var createPromise = controller.createPracticeSession(null);
            var errorHandled = false;

            createPromise.catch(function(error) {
                expect(error.message).toContain('Parent session ID is required');
                errorHandled = true;
            });

            $rootScope.$apply();
            expect(errorHandled).toBe(true);
        });
    });

    describe('Settings Preview', function() {
        beforeEach(function() {
            UnifiedDifficultyStateService.getSessionDifficultyState.and.returnValue($q.resolve(mockDifficultyState));
        });

        it('should generate correct settings preview for adjusted difficulty', function() {
            var previewPromise = controller.getInheritedSettingsPreview(123);
            $rootScope.$apply();

            previewPromise.then(function(preview) {
                expect(preview.parentSessionId).toBe(123);
                expect(preview.inheritedDifficulty.level).toBe('hard');
                expect(preview.inheritedDifficulty.label).toBe('Medium'); // Mocked return value
                expect(preview.difficultyWasAdjusted).toBe(true);
                expect(preview.initialDifficulty).toBe('medium');
                expect(preview.finalDifficulty).toBe('hard');
                expect(preview.changeCount).toBe(1);
            });

            $rootScope.$apply();
        });

        it('should handle fallback preview when difficulty state fails', function() {
            UnifiedDifficultyStateService.getSessionDifficultyState.and.returnValue($q.reject(new Error('Network error')));

            var previewPromise = controller.getInheritedSettingsPreview(123);
            $rootScope.$apply();

            previewPromise.then(function(preview) {
                expect(preview.parentSessionId).toBe(123);
                expect(preview.inheritedDifficulty.level).toBe('medium');
                expect(preview.isPreviewFallback).toBe(true);
            });

            $rootScope.$apply();
        });
    });

    describe('Error Handling', function() {
        it('should broadcast error events for UI components', function() {
            spyOn($rootScope, '$broadcast');
            
            var error = new Error('Test error');
            var context = { source: 'test' };
            
            controller.handlePracticeSessionError(error, context);

            expect($rootScope.$broadcast).toHaveBeenCalledWith('practice:session:creation:error', jasmine.objectContaining({
                error: error,
                context: context,
                userMessage: jasmine.any(String),
                recoverySuggestions: jasmine.any(Array)
            }));
        });

        it('should provide user-friendly error messages', function() {
            var authError = new Error('Authentication required');
            var errorPromise = controller.handlePracticeSessionError(authError, {});
            var caughtError;

            errorPromise.catch(function(error) {
                caughtError = error;
            });

            $rootScope.$apply();

            expect(caughtError.message).toBe('Please log in to create practice sessions');
            expect(caughtError.isUserFriendly).toBe(true);
            expect(caughtError.recoverySuggestions).toContain('Log in to your account');
        });
    });

    describe('Event Broadcasting', function() {
        beforeEach(function() {
            UnifiedDifficultyStateService.getSessionDifficultyState.and.returnValue($q.resolve(mockDifficultyState));
            UnifiedDifficultyStateService.createPracticeSessionWithDifficulty.and.returnValue($q.resolve(mockPracticeResponse));
        });

        it('should broadcast creation started event', function() {
            spyOn($rootScope, '$broadcast');
            
            controller.createPracticeSession(123);
            $rootScope.$apply();

            expect($rootScope.$broadcast).toHaveBeenCalledWith('practice:session:creation:started', jasmine.objectContaining({
                parentSessionId: 123
            }));
        });

        it('should broadcast creation success event', function() {
            spyOn($rootScope, '$broadcast');
            
            var createPromise = controller.createPracticeSession(123);
            $rootScope.$apply();

            createPromise.then(function() {
                expect($rootScope.$broadcast).toHaveBeenCalledWith('practice:session:creation:success', jasmine.objectContaining({
                    practiceSession: mockPracticeResponse.session,
                    parentSessionId: 123,
                    inheritedSettings: mockPracticeResponse.inherited_settings
                }));
            });

            $rootScope.$apply();
        });
    });
});

/**
 * Integration test to verify consistent behavior between feedback and dashboard
 */
describe('Unified Practice Controller - Navigation Consistency', function() {
    'use strict';

    var FeedbackController, DashboardController, UnifiedPracticeController;
    var $rootScope, $location, $routeParams, $q;
    var mockServices = {};

    beforeEach(function() {
        module('interviewPrepApp');

        // Create mock services
        module(function($provide) {
            mockServices.UnifiedPracticeController = {
                createPracticeSessionWithConfirmation: jasmine.createSpy('createPracticeSessionWithConfirmation').and.returnValue($q.resolve({}))
            };

            $provide.value('UnifiedPracticeController', mockServices.UnifiedPracticeController);
            $provide.value('InterviewService', { getSessionFeedback: jasmine.createSpy().and.returnValue($q.resolve({})) });
            $provide.value('PostureFeedbackIntegrationService', { getBodyLanguageScore: jasmine.createSpy().and.returnValue($q.resolve({})) });
            $provide.value('AuthService', { 
                isAuthenticated: jasmine.createSpy().and.returnValue(true),
                getCurrentUser: jasmine.createSpy().and.returnValue({ id: 1 })
            });
            $provide.value('ApiService', { get: jasmine.createSpy().and.returnValue($q.resolve([])) });
            $provide.value('SessionDataService', { setSessionData: jasmine.createSpy() });
            $provide.value('DifficultyDisplayService', { 
                getDifficultyLabel: jasmine.createSpy().and.returnValue('Medium'),
                normalizeDifficultyInput: jasmine.createSpy().and.returnValue(3)
            });
            $provide.value('SessionSettingsService', {});
        });

        inject(function(_$controller_, _$rootScope_, _$location_, _$q_) {
            $rootScope = _$rootScope_;
            $location = _$location_;
            $q = _$q_;

            // Create controllers
            FeedbackController = _$controller_('FeedbackController', {
                $routeParams: { sessionId: '123' }
            });

            DashboardController = _$controller_('DashboardController');
        });
    });

    it('should use same UnifiedPracticeController method in both feedback and dashboard', function() {
        var mockSession = {
            id: 123,
            target_role: 'Software Engineer',
            duration: 30,
            question_count: 5,
            difficulty_level: 'medium'
        };

        // Test feedback controller
        FeedbackController.session = mockSession;
        FeedbackController.difficultyInfo = { current_difficulty: 'Medium' };
        FeedbackController.practiceAgain();

        expect(mockServices.UnifiedPracticeController.createPracticeSessionWithConfirmation).toHaveBeenCalledWith(
            123,
            jasmine.objectContaining({
                target_role: 'Software Engineer',
                duration: 30,
                difficulty_level: 'Medium'
            }),
            jasmine.objectContaining({
                showLoading: true,
                showSuccess: true,
                autoNavigate: true
            })
        );

        // Reset spy
        mockServices.UnifiedPracticeController.createPracticeSessionWithConfirmation.calls.reset();

        // Test dashboard controller
        DashboardController.practiceAgain(mockSession);

        expect(mockServices.UnifiedPracticeController.createPracticeSessionWithConfirmation).toHaveBeenCalledWith(
            123,
            jasmine.objectContaining({
                target_role: 'Software Engineer',
                duration: 30,
                difficulty_level: 'Medium'
            }),
            jasmine.objectContaining({
                showLoading: true,
                showSuccess: true,
                autoNavigate: true
            })
        );
    });

    it('should handle errors consistently in both controllers', function() {
        var mockError = new Error('Test error');
        mockError.isUserFriendly = true;
        mockServices.UnifiedPracticeController.createPracticeSessionWithConfirmation.and.returnValue($q.reject(mockError));

        var mockSession = { id: 123, target_role: 'Test Role', duration: 30 };

        // Test feedback controller error handling
        FeedbackController.session = mockSession;
        FeedbackController.difficultyInfo = { current_difficulty: 'Medium' };
        FeedbackController.practiceAgain();
        $rootScope.$apply();

        expect(FeedbackController.error).toBe('Test error');

        // Test dashboard controller error handling
        DashboardController.practiceAgain(mockSession);
        $rootScope.$apply();

        expect(DashboardController.error).toBe('Test error');
    });
});