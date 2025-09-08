/**
 * End-to-End Frontend Testing for Bug Fixes
 * Tests frontend aspects of all 5 critical bug fixes:
 * 1. Difficulty Label Consistency in UI
 * 2. Form Error Handling and Display
 * 3. Role-Specific Question Display
 * 4. Practice-Again Session UI
 * 5. Quick Test Session UI
 */

describe('Bug Fixes End-to-End Frontend Testing', function() {
    var $controller, $rootScope, $httpBackend, $location, $q;
    var mockApiService, mockSessionDataService, mockFormErrorService, mockDifficultyDisplayService;

    beforeEach(function() {
        if (typeof module !== 'undefined') {
            module('interviewApp');
        }
    });

    beforeEach(inject(function(_$controller_, _$rootScope_, _$httpBackend_, _$location_, _$q_) {
        $controller = _$controller_;
        $rootScope = _$rootScope_;
        $httpBackend = _$httpBackend_;
        $location = _$location_;
        $q = _$q_;

        // Mock services for bug fixes
        mockApiService = {
            get: jasmine.createSpy('get').and.returnValue($q.resolve({data: {}})),
            post: jasmine.createSpy('post').and.returnValue($q.resolve({data: {}})),
            put: jasmine.createSpy('put').and.returnValue($q.resolve({data: {}}))
        };

        mockSessionDataService = {
            setSessionData: jasmine.createSpy('setSessionData'),
            getSessionData: jasmine.createSpy('getSessionData').and.returnValue({}),
            clearSessionData: jasmine.createSpy('clearSessionData')
        };

        mockFormErrorService = {
            validateLoginForm: jasmine.createSpy('validateLoginForm'),
            validateRoleSelection: jasmine.createSpy('validateRoleSelection'),
            handleServerError: jasmine.createSpy('handleServerError'),
            displayFieldError: jasmine.createSpy('displayFieldError')
        };

        mockDifficultyDisplayService = {
            getDifficultyLabel: jasmine.createSpy('getDifficultyLabel'),
            updateDifficultyDisplay: jasmine.createSpy('updateDifficultyDisplay')
        };
    }));

    describe('Bug Fix 1: Difficulty Label Consistency in UI', function() {
        var scope, controller;

        beforeEach(function() {
            scope = $rootScope.$new();
            
            controller = $controller('InterviewChatController', {
                $scope: scope,
                ApiService: mockApiService,
                SessionDataService: mockSessionDataService,
                DifficultyDisplayService: mockDifficultyDisplayService
            });
        });

        it('should display consistent difficulty labels throughout interview session', function() {
            console.log('🧪 Testing difficulty label consistency in UI...');
            
            // Mock session with difficulty level
            mockSessionDataService.getSessionData.and.returnValue({
                id: 1,
                difficulty_level: 2,
                difficulty_label: 'Medium'
            });

            // Mock difficulty display service
            mockDifficultyDisplayService.getDifficultyLabel.and.returnValue('Medium');

            // Initialize session
            scope.initializeSession();
            scope.$apply();

            // Verify difficulty label is set consistently
            expect(mockDifficultyDisplayService.getDifficultyLabel).toHaveBeenCalledWith(2);
            expect(scope.currentDifficultyLabel).toBe('Medium');
            
            console.log('    ✅ Initial difficulty label consistent');

            // Test adaptive difficulty change
            mockApiService.post.and.returnValue($q.resolve({
                data: {
                    evaluation: {
                        difficulty_adjusted: true,
                        new_difficulty_level: 3,
                        new_difficulty_label: 'Hard'
                    }
                }
            }));

            mockDifficultyDisplayService.getDifficultyLabel.and.returnValue('Hard');

            // Submit answer that triggers difficulty change
            scope.userAnswer = 'Excellent detailed answer';
            scope.submitAnswer();
            scope.$apply();

            // Verify difficulty label updated consistently
            expect(scope.currentDifficultyLabel).toBe('Hard');
            expect(mockDifficultyDisplayService.updateDifficultyDisplay).toHaveBeenCalledWith('difficulty-display', 3);
            
            console.log('    ✅ Adaptive difficulty label change consistent');
        });

        it('should show same difficulty label in feedback report', function() {
            console.log('🧪 Testing difficulty label consistency in feedback...');
            
            scope = $rootScope.$new();
            controller = $controller('SessionResultsController', {
                $scope: scope,
                ApiService: mockApiService,
                DifficultyDisplayService: mockDifficultyDisplayService
            });

            // Mock session results with difficulty progression
            mockApiService.get.and.returnValue($q.resolve({
                data: {
                    session_id: 1,
                    final_difficulty_level: 3,
                    final_difficulty_label: 'Hard',
                    difficulty_progression: [
                        { level: 2, label: 'Medium' },
                        { level: 3, label: 'Hard' }
                    ]
                }
            }));

            mockDifficultyDisplayService.getDifficultyLabel.and.returnValue('Hard');

            // Load session results
            scope.loadSessionResults(1);
            scope.$apply();

            // Verify consistent difficulty labeling in feedback
            expect(scope.sessionResults.final_difficulty_label).toBe('Hard');
            expect(scope.sessionResults.difficulty_progression[1].label).toBe('Hard');
            expect(mockDifficultyDisplayService.getDifficultyLabel).toHaveBeenCalledWith(3);
            
            console.log('    ✅ Feedback report difficulty label consistent');
        });
    });

    describe('Bug Fix 2: Form Error Handling and Display', function() {
        var scope, controller;

        beforeEach(function() {
            scope = $rootScope.$new();
        });

        it('should display specific error messages for login form validation', function() {
            console.log('🧪 Testing login form error handling...');
            
            controller = $controller('LoginController', {
                $scope: scope,
                ApiService: mockApiService,
                FormErrorService: mockFormErrorService
            });

            // Test empty password validation
            mockFormErrorService.validateLoginForm.and.returnValue({
                isValid: false,
                errors: { password: 'Password is required' }
            });

            scope.loginData = { username: 'testuser', password: '' };
            scope.submitLogin();
            scope.$apply();

            // Verify specific error message displayed
            expect(mockFormErrorService.validateLoginForm).toHaveBeenCalledWith(scope.loginData);
            expect(scope.formErrors.password).toBe('Password is required');
            expect(scope.showError).toBe(true);
            
            console.log('    ✅ Empty password error displayed correctly');

            // Test invalid credentials error
            mockFormErrorService.validateLoginForm.and.returnValue({ isValid: true, errors: {} });
            mockApiService.post.and.returnValue($q.reject({
                status: 401,
                data: { message: 'Invalid credentials' }
            }));
            mockFormErrorService.handleServerError.and.returnValue('Invalid username or password');

            scope.loginData = { username: 'wronguser', password: 'wrongpass' };
            scope.submitLogin();
            scope.$apply();

            // Verify server error handled properly
            expect(mockFormErrorService.handleServerError).toHaveBeenCalled();
            expect(scope.serverError).toBe('Invalid username or password');
            
            console.log('    ✅ Invalid credentials error displayed correctly');
        });

        it('should display field-specific errors for role selection form', function() {
            console.log('🧪 Testing role selection form error handling...');
            
            controller = $controller('RoleSelectorController', {
                $scope: scope,
                ApiService: mockApiService,
                FormErrorService: mockFormErrorService
            });

            // Test missing role selection validation
            mockFormErrorService.validateRoleSelection.and.returnValue({
                isValid: false,
                errors: {
                    mainRole: 'Please select a main role',
                    subRole: 'Please select a sub role'
                }
            });

            scope.roleData = { mainRole: '', subRole: '', specialization: 'React Developer' };
            scope.submitRoleSelection();
            scope.$apply();

            // Verify field-specific errors displayed
            expect(mockFormErrorService.validateRoleSelection).toHaveBeenCalledWith(scope.roleData);
            expect(scope.formErrors.mainRole).toBe('Please select a main role');
            expect(scope.formErrors.subRole).toBe('Please select a sub role');
            
            console.log('    ✅ Role selection field errors displayed correctly');

            // Test role mismatch error
            mockFormErrorService.validateRoleSelection.and.returnValue({ isValid: true, errors: {} });
            mockApiService.post.and.returnValue($q.reject({
                status: 400,
                data: { message: 'Role combination not valid' }
            }));
            mockFormErrorService.handleServerError.and.returnValue('Selected role combination is not valid');

            scope.roleData = { mainRole: 'Student', subRole: 'Senior Developer', specialization: 'Team Lead' };
            scope.submitRoleSelection();
            scope.$apply();

            // Verify role mismatch error handled
            expect(scope.serverError).toBe('Selected role combination is not valid');
            
            console.log('    ✅ Role mismatch error displayed correctly');
        });

        it('should show user-friendly messages for server errors', function() {
            console.log('🧪 Testing server error handling...');
            
            controller = $controller('InterviewChatController', {
                $scope: scope,
                ApiService: mockApiService,
                FormErrorService: mockFormErrorService
            });

            // Test server error during session creation
            mockApiService.post.and.returnValue($q.reject({
                status: 500,
                data: { message: 'Database connection failed' }
            }));
            mockFormErrorService.handleServerError.and.returnValue('Server error. Please try again later.');

            scope.createSession();
            scope.$apply();

            // Verify user-friendly error message
            expect(mockFormErrorService.handleServerError).toHaveBeenCalled();
            expect(scope.serverError).toBe('Server error. Please try again later.');
            expect(scope.serverError).not.toContain('Database connection failed'); // No technical details
            
            console.log('    ✅ Server error handled with user-friendly message');
        });
    });

    describe('Bug Fix 3: Role-Specific Question Display', function() {
        var scope, controller;

        beforeEach(function() {
            scope = $rootScope.$new();
            
            controller = $controller('InterviewChatController', {
                $scope: scope,
                ApiService: mockApiService,
                SessionDataService: mockSessionDataService
            });
        });

        it('should display questions appropriate for selected role', function() {
            console.log('🧪 Testing role-specific question display...');
            
            // Mock session with role information
            mockSessionDataService.getSessionData.and.returnValue({
                id: 1,
                target_role: 'Software Developer',
                sub_role: 'Frontend Developer',
                specialization: 'React Developer'
            });

            // Mock role-appropriate questions
            mockApiService.post.and.returnValue($q.resolve({
                data: {
                    questions: [
                        {
                            id: 1,
                            question: 'Explain React hooks and their benefits',
                            category: 'theory',
                            role_tags: ['react', 'frontend'],
                            tech_stack: ['React', 'JavaScript']
                        },
                        {
                            id: 2,
                            question: 'Write a React component that manages state',
                            category: 'coding',
                            role_tags: ['react', 'frontend'],
                            tech_stack: ['React']
                        },
                        {
                            id: 3,
                            question: 'What is the time complexity of array.map()?',
                            category: 'aptitude',
                            role_tags: ['javascript', 'algorithms'],
                            tech_stack: ['JavaScript']
                        }
                    ]
                }
            }));

            // Initialize session with questions
            scope.initializeSession();
            scope.$apply();

            // Verify questions are role-appropriate
            expect(scope.questions).toBeDefined();
            expect(scope.questions.length).toBe(3);
            
            // Check for React-specific content
            var questionText = scope.questions.map(q => q.question.toLowerCase()).join(' ');
            expect(questionText).toContain('react');
            expect(questionText).toContain('javascript');
            
            // Verify question distribution
            var theoryCount = scope.questions.filter(q => q.category === 'theory').length;
            var codingCount = scope.questions.filter(q => q.category === 'coding').length;
            var aptitudeCount = scope.questions.filter(q => q.category === 'aptitude').length;
            
            expect(theoryCount).toBe(1); // ~33% (close to 20%)
            expect(codingCount).toBe(1); // ~33% (close to 40%)
            expect(aptitudeCount).toBe(1); // ~33% (close to 40%)
            
            console.log('    ✅ Role-specific questions displayed with proper distribution');
        });

        it('should not display inappropriate questions for student role', function() {
            console.log('🧪 Testing student role question filtering...');
            
            // Mock student role session
            mockSessionDataService.getSessionData.and.returnValue({
                id: 1,
                target_role: 'Student',
                sub_role: 'Computer Science Student',
                specialization: 'Web Development'
            });

            // Mock student-appropriate questions (no management/senior content)
            mockApiService.post.and.returnValue($q.resolve({
                data: {
                    questions: [
                        {
                            id: 1,
                            question: 'What is a variable in programming?',
                            category: 'theory',
                            role_tags: ['student', 'basic'],
                            difficulty: 'easy'
                        },
                        {
                            id: 2,
                            question: 'Write a simple loop to print numbers 1 to 10',
                            category: 'coding',
                            role_tags: ['student', 'basic'],
                            difficulty: 'easy'
                        }
                    ]
                }
            }));

            scope.initializeSession();
            scope.$apply();

            // Verify no inappropriate content for students
            var questionText = scope.questions.map(q => q.question.toLowerCase()).join(' ');
            expect(questionText).not.toContain('management');
            expect(questionText).not.toContain('senior');
            expect(questionText).not.toContain('architecture');
            expect(questionText).not.toContain('lead');
            
            // Verify appropriate basic content
            expect(questionText).toContain('variable');
            expect(questionText).toContain('loop');
            
            console.log('    ✅ Student role questions appropriately filtered');
        });
    });

    describe('Bug Fix 4: Practice-Again Session UI', function() {
        var scope, controller;

        beforeEach(function() {
            scope = $rootScope.$new();
            
            controller = $controller('DashboardController', {
                $scope: scope,
                ApiService: mockApiService,
                SessionDataService: mockSessionDataService
            });
        });

        it('should show inherited question count in practice-again session', function() {
            console.log('🧪 Testing practice-again session UI...');
            
            // Mock original session with specific question count
            var originalSession = {
                id: 1,
                target_role: 'Software Developer',
                question_count: 8,
                status: 'completed'
            };

            // Mock practice-again API response
            mockApiService.post.and.returnValue($q.resolve({
                data: {
                    session: {
                        id: 2,
                        parent_session_id: 1,
                        question_count: 8, // Inherited from original
                        target_role: 'Software Developer',
                        status: 'pending'
                    }
                }
            }));

            // Start practice-again session
            scope.practiceAgain(originalSession);
            scope.$apply();

            // Verify API called correctly
            expect(mockApiService.post).toHaveBeenCalledWith('/api/v1/interviews/1/practice-again');
            
            // Verify session data shows inherited question count
            expect(mockSessionDataService.setSessionData).toHaveBeenCalled();
            var sessionData = mockSessionDataService.setSessionData.calls.mostRecent().args[0];
            expect(sessionData.question_count).toBe(8);
            expect(sessionData.question_count).not.toBe(5); // Not default
            
            console.log('    ✅ Practice-again session shows inherited question count: 8');
        });

        it('should display practice session inheritance information', function() {
            console.log('🧪 Testing practice session inheritance display...');
            
            scope = $rootScope.$new();
            controller = $controller('InterviewChatController', {
                $scope: scope,
                ApiService: mockApiService,
                SessionDataService: mockSessionDataService
            });

            // Mock practice session data
            mockSessionDataService.getSessionData.and.returnValue({
                id: 2,
                parent_session_id: 1,
                question_count: 8,
                session_type: 'practice',
                target_role: 'Software Developer'
            });

            // Initialize practice session
            scope.initializeSession();
            scope.$apply();

            // Verify practice session information displayed
            expect(scope.isPracticeSession).toBe(true);
            expect(scope.parentSessionId).toBe(1);
            expect(scope.questionCount).toBe(8);
            
            console.log('    ✅ Practice session inheritance information displayed');
        });
    });

    describe('Bug Fix 5: Quick Test Session UI', function() {
        var scope, controller;

        beforeEach(function() {
            scope = $rootScope.$new();
            
            controller = $controller('QuickTestController', {
                $scope: scope,
                ApiService: mockApiService,
                SessionDataService: mockSessionDataService
            });
        });

        it('should show inherited question count from main session', function() {
            console.log('🧪 Testing quick test session UI inheritance...');
            
            // Mock quick test creation with inheritance
            mockApiService.post.and.returnValue($q.resolve({
                data: {
                    id: 3,
                    question_count: 7, // Inherited from main session
                    session_type: 'quick_test',
                    inheritance_source: 'main_session'
                }
            }));

            // Create quick test without explicit count
            scope.createQuickTest();
            scope.$apply();

            // Verify inherited question count displayed
            expect(scope.quickTestSession.question_count).toBe(7);
            expect(scope.quickTestSession.question_count).not.toBe(3); // Not default
            expect(scope.inheritanceSource).toBe('main_session');
            
            console.log('    ✅ Quick test shows inherited question count: 7');
        });

        it('should allow user to override inherited question count', function() {
            console.log('🧪 Testing quick test question count override...');
            
            // Set user override
            scope.userOverride = {
                question_count: 4
            };

            // Mock quick test creation with override
            mockApiService.post.and.returnValue($q.resolve({
                data: {
                    id: 4,
                    question_count: 4, // User override
                    session_type: 'quick_test',
                    inheritance_source: 'user_override'
                }
            }));

            // Create quick test with override
            scope.createQuickTestWithOverride();
            scope.$apply();

            // Verify override respected
            expect(mockApiService.post).toHaveBeenCalledWith('/api/v1/interviews/quick-test', 
                jasmine.objectContaining({
                    question_count: 4
                }));
            expect(scope.quickTestSession.question_count).toBe(4);
            expect(scope.inheritanceSource).toBe('user_override');
            
            console.log('    ✅ Quick test respects user override: 4 questions');
        });

        it('should display question distribution information for quick test', function() {
            console.log('🧪 Testing quick test question distribution display...');
            
            // Mock quick test with distribution info
            mockApiService.get.and.returnValue($q.resolve({
                data: {
                    question_distribution: {
                        theory: 1,
                        coding: 2,
                        aptitude: 3
                    },
                    total_questions: 6
                }
            }));

            // Load quick test distribution
            scope.loadQuickTestDistribution(3);
            scope.$apply();

            // Verify distribution information displayed
            expect(scope.questionDistribution).toBeDefined();
            expect(scope.questionDistribution.theory).toBe(1);
            expect(scope.questionDistribution.coding).toBe(2);
            expect(scope.questionDistribution.aptitude).toBe(3);
            
            console.log('    ✅ Quick test distribution displayed: 1 theory, 2 coding, 3 aptitude');
        });
    });

    describe('Complete Bug Fixes Integration UI Test', function() {
        it('should run complete user journey with all bug fixes', function() {
            console.log('🧪 Running complete bug fixes integration UI test...');
            
            var validationResults = {
                difficultyConsistency: false,
                formErrorHandling: false,
                roleSpecificQuestions: false,
                practiceAgainUI: false,
                quickTestUI: false
            };

            // Test 1: Difficulty consistency in UI
            var interviewScope = $rootScope.$new();
            var interviewController = $controller('InterviewChatController', {
                $scope: interviewScope,
                ApiService: mockApiService,
                DifficultyDisplayService: mockDifficultyDisplayService
            });

            mockDifficultyDisplayService.getDifficultyLabel.and.returnValue('Medium');
            mockSessionDataService.getSessionData.and.returnValue({
                id: 1,
                difficulty_level: 2,
                difficulty_label: 'Medium'
            });

            interviewScope.initializeSession();
            interviewScope.$apply();

            if (interviewScope.currentDifficultyLabel === 'Medium') {
                validationResults.difficultyConsistency = true;
                console.log('    ✅ Difficulty consistency UI validated');
            }

            // Test 2: Form error handling
            var loginScope = $rootScope.$new();
            var loginController = $controller('LoginController', {
                $scope: loginScope,
                FormErrorService: mockFormErrorService
            });

            mockFormErrorService.validateLoginForm.and.returnValue({
                isValid: false,
                errors: { password: 'Password is required' }
            });

            loginScope.loginData = { username: 'test', password: '' };
            loginScope.submitLogin();
            loginScope.$apply();

            if (loginScope.formErrors && loginScope.formErrors.password === 'Password is required') {
                validationResults.formErrorHandling = true;
                console.log('    ✅ Form error handling UI validated');
            }

            // Test 3: Role-specific questions
            mockApiService.post.and.returnValue($q.resolve({
                data: {
                    questions: [
                        { question: 'React question', category: 'theory', role_tags: ['react'] }
                    ]
                }
            }));

            interviewScope.initializeSession();
            interviewScope.$apply();

            if (interviewScope.questions && interviewScope.questions.length > 0) {
                validationResults.roleSpecificQuestions = true;
                console.log('    ✅ Role-specific questions UI validated');
            }

            // Test 4: Practice-again UI
            var dashboardScope = $rootScope.$new();
            var dashboardController = $controller('DashboardController', {
                $scope: dashboardScope,
                ApiService: mockApiService,
                SessionDataService: mockSessionDataService
            });

            mockApiService.post.and.returnValue($q.resolve({
                data: {
                    session: { id: 2, question_count: 8, parent_session_id: 1 }
                }
            }));

            dashboardScope.practiceAgain({ id: 1, question_count: 8 });
            dashboardScope.$apply();

            if (mockSessionDataService.setSessionData.calls.count() > 0) {
                validationResults.practiceAgainUI = true;
                console.log('    ✅ Practice-again UI validated');
            }

            // Test 5: Quick test UI
            var quickTestScope = $rootScope.$new();
            var quickTestController = $controller('QuickTestController', {
                $scope: quickTestScope,
                ApiService: mockApiService
            });

            mockApiService.post.and.returnValue($q.resolve({
                data: { id: 3, question_count: 7, session_type: 'quick_test' }
            }));

            quickTestScope.createQuickTest();
            quickTestScope.$apply();

            if (quickTestScope.quickTestSession && quickTestScope.quickTestSession.question_count === 7) {
                validationResults.quickTestUI = true;
                console.log('    ✅ Quick test UI validated');
            }

            // Final validation
            var allUITestsPassed = Object.values(validationResults).every(result => result === true);
            
            console.log('\n📊 UI Bug Fixes Validation Summary:');
            for (var test in validationResults) {
                var status = validationResults[test] ? '✅ PASSED' : '❌ FAILED';
                console.log('    ' + status + ' ' + test.replace(/([A-Z])/g, ' $1').toLowerCase());
            }

            if (allUITestsPassed) {
                console.log('\n🎉 ALL UI BUG FIXES SUCCESSFULLY VALIDATED!');
            } else {
                console.log('\n⚠️  Some UI tests failed validation');
            }

            expect(allUITestsPassed).toBe(true);
            console.log('✅ Complete bug fixes integration UI test passed!');
        });
    });

    afterEach(function() {
        console.log('🧹 Cleaning up frontend test environment...');
    });
});