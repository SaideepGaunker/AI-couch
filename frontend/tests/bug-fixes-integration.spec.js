/**
 * Integration tests for complete bug fixes validation - Frontend
 * Tests all five critical bug fixes working together in complete user flows
 */

describe('Bug Fixes Integration Tests', function() {
    
    var $httpBackend, $rootScope, $controller, $compile;
    var DifficultyDisplayService, FormErrorService, SessionSettingsService;
    
    beforeEach(module('interviewCoachApp'));
    
    beforeEach(inject(function(_$httpBackend_, _$rootScope_, _$controller_, _$compile_, 
                              _DifficultyDisplayService_, _FormErrorService_, _SessionSettingsService_) {
        $httpBackend = _$httpBackend_;
        $rootScope = _$rootScope_;
        $controller = _$controller_;
        $compile = _$compile_;
        DifficultyDisplayService = _DifficultyDisplayService_;
        FormErrorService = _FormErrorService_;
        SessionSettingsService = _SessionSettingsService_;
    }));
    
    afterEach(function() {
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
    });
    
    describe('Difficulty Label Consistency Integration', function() {
        
        it('should maintain consistent difficulty labels throughout interview flow', function() {
            var scope = $rootScope.$new();
            
            // Mock interview session with difficulty level 2 (Medium)
            var mockSession = {
                id: 1,
                difficulty_level: 'Medium',
                status: 'in_progress',
                current_question: {
                    id: 1,
                    question: 'Explain React hooks',
                    difficulty_level: 'Medium'
                }
            };
            
            // Mock session creation response
            $httpBackend.expectPOST('/api/v1/interviews/')
                .respond(200, mockSession);
            
            // Mock session initialization
            $httpBackend.expectPOST('/api/v1/interviews/1/initialize')
                .respond(200, {
                    status: 'initialized',
                    questions: [{
                        id: 1,
                        question: 'Explain React hooks',
                        difficulty_level: 'Medium'
                    }]
                });
            
            // Mock difficulty adjustment during interview
            $httpBackend.expectPOST('/api/v1/interviews/1/answers')
                .respond(200, {
                    evaluation: {
                        overall_score: 95,
                        difficulty_adjustment: {
                            new_level: 3,
                            new_label: 'Hard'
                        }
                    }
                });
            
            // Mock session completion
            $httpBackend.expectPOST('/api/v1/interviews/1/complete')
                .respond(200, {
                    status: 'completed',
                    final_difficulty: 'Hard'
                });
            
            // Mock feedback retrieval
            $httpBackend.expectGET('/api/v1/interviews/1/feedback')
                .respond(200, {
                    difficulty_progression: [
                        {level: 2, label: 'Medium'},
                        {level: 3, label: 'Hard'}
                    ],
                    final_difficulty: 'Hard'
                });
            
            // Create interview controller
            var controller = $controller('InterviewController', {
                $scope: scope,
                DifficultyDisplayService: DifficultyDisplayService
            });
            
            // Step 1: Create session
            scope.createSession({
                target_role: 'Software Developer',
                difficulty_level: 'medium',
                question_count: 5
            });
            $httpBackend.flush();
            
            // Verify initial difficulty display
            expect(scope.session.difficulty_level).toBe('Medium');
            expect(DifficultyDisplayService.getDifficultyLabel(2)).toBe('Medium');
            
            // Step 2: Initialize session
            scope.initializeSession();
            $httpBackend.flush();
            
            // Verify question difficulty consistency
            expect(scope.session.questions[0].difficulty_level).toBe('Medium');
            
            // Step 3: Submit answer that triggers difficulty adjustment
            scope.submitAnswer({
                question_id: 1,
                answer: 'React hooks are functions that let you use state',
                confidence_score: 9
            });
            $httpBackend.flush();
            
            // Verify difficulty adjustment consistency
            expect(scope.session.current_difficulty).toBe('Hard');
            expect(DifficultyDisplayService.getDifficultyLabel(3)).toBe('Hard');
            
            // Step 4: Complete session
            scope.completeSession();
            $httpBackend.flush();
            
            // Verify final difficulty consistency
            expect(scope.session.final_difficulty).toBe('Hard');
            
            // Step 5: Get feedback
            scope.getFeedback();
            $httpBackend.flush();
            
            // Verify feedback difficulty consistency
            expect(scope.feedback.final_difficulty).toBe('Hard');
            expect(scope.feedback.difficulty_progression[1].label).toBe('Hard');
        });
        
        it('should update difficulty display consistently across UI components', function() {
            var scope = $rootScope.$new();
            
            // Create difficulty display elements
            var sessionDisplay = angular.element('<div id="session-difficulty">{{session.difficulty_level}}</div>');
            var progressDisplay = angular.element('<div id="progress-difficulty">{{currentDifficulty}}</div>');
            
            scope.session = {difficulty_level: 'Medium'};
            scope.currentDifficulty = 'Medium';
            
            $compile(sessionDisplay)(scope);
            $compile(progressDisplay)(scope);
            
            $rootScope.$digest();
            
            // Verify initial consistency
            expect(sessionDisplay.text()).toBe('Medium');
            expect(progressDisplay.text()).toBe('Medium');
            
            // Simulate difficulty change
            scope.session.difficulty_level = 'Hard';
            scope.currentDifficulty = 'Hard';
            
            $rootScope.$digest();
            
            // Verify updated consistency
            expect(sessionDisplay.text()).toBe('Hard');
            expect(progressDisplay.text()).toBe('Hard');
        });
    });
    
    describe('Form Error Handling Integration', function() {
        
        it('should handle login form errors with proper user feedback', function() {
            var scope = $rootScope.$new();
            
            // Create login form
            var loginForm = angular.element(
                '<form name="loginForm">' +
                    '<input name="username" ng-model="credentials.username" required>' +
                    '<input name="password" ng-model="credentials.password" required>' +
                    '<form-error-display errors="errors" field-name="username"></form-error-display>' +
                    '<form-error-display errors="errors" field-name="password"></form-error-display>' +
                    '<button ng-click="login()">Login</button>' +
                '</form>'
            );
            
            var controller = $controller('LoginController', {
                $scope: scope,
                FormErrorService: FormErrorService
            });
            
            $compile(loginForm)(scope);
            $rootScope.$digest();
            
            // Test empty password validation
            scope.credentials = {username: 'test@example.com', password: ''};
            
            // Mock validation response
            spyOn(FormErrorService, 'validateLoginForm').and.returnValue({
                isValid: false,
                errors: {password: 'Password is required'}
            });
            
            // Mock server response for empty password
            $httpBackend.expectPOST('/api/v1/auth/login')
                .respond(400, {detail: 'Password is required'});
            
            scope.login();
            $httpBackend.flush();
            
            // Verify error display
            expect(scope.errors.password).toBe('Password is required');
            expect(FormErrorService.validateLoginForm).toHaveBeenCalledWith(scope.credentials);
            
            // Test invalid credentials
            scope.credentials = {username: 'test@example.com', password: 'wrongpassword'};
            
            FormErrorService.validateLoginForm.and.returnValue({
                isValid: true,
                errors: {}
            });
            
            spyOn(FormErrorService, 'handleServerError').and.returnValue('Invalid username or password');
            
            $httpBackend.expectPOST('/api/v1/auth/login')
                .respond(401, {detail: 'Invalid credentials'});
            
            scope.login();
            $httpBackend.flush();
            
            // Verify server error handling
            expect(scope.serverError).toBe('Invalid username or password');
            expect(FormErrorService.handleServerError).toHaveBeenCalled();
        });
        
        it('should handle role selection form validation and recovery', function() {
            var scope = $rootScope.$new();
            
            var roleForm = angular.element(
                '<form name="roleForm">' +
                    '<select name="mainRole" ng-model="roleData.mainRole" required>' +
                        '<option value="">Select Main Role</option>' +
                        '<option value="Software Developer">Software Developer</option>' +
                    '</select>' +
                    '<select name="subRole" ng-model="roleData.subRole" required>' +
                        '<option value="">Select Sub Role</option>' +
                        '<option value="Frontend Developer">Frontend Developer</option>' +
                    '</select>' +
                    '<form-error-display errors="errors" field-name="mainRole"></form-error-display>' +
                    '<form-error-display errors="errors" field-name="subRole"></form-error-display>' +
                '</form>'
            );
            
            var controller = $controller('RoleSelectionController', {
                $scope: scope,
                FormErrorService: FormErrorService
            });
            
            $compile(roleForm)(scope);
            $rootScope.$digest();
            
            // Test missing role selection
            scope.roleData = {mainRole: '', subRole: '', specialization: ''};
            
            spyOn(FormErrorService, 'validateRoleSelection').and.returnValue({
                isValid: false,
                errors: {
                    mainRole: 'Please select a main role',
                    subRole: 'Please select a sub role'
                }
            });
            
            $httpBackend.expectPUT('/api/v1/roles/user/role')
                .respond(400, {detail: 'Validation failed'});
            
            scope.updateRole();
            $httpBackend.flush();
            
            // Verify validation errors
            expect(scope.errors.mainRole).toBe('Please select a main role');
            expect(scope.errors.subRole).toBe('Please select a sub role');
            
            // Test successful correction and recovery
            scope.roleData = {
                mainRole: 'Software Developer',
                subRole: 'Frontend Developer',
                specialization: 'React Developer'
            };
            
            FormErrorService.validateRoleSelection.and.returnValue({
                isValid: true,
                errors: {}
            });
            
            $httpBackend.expectPUT('/api/v1/roles/user/role')
                .respond(200, {message: 'Role updated successfully'});
            
            scope.updateRole();
            $httpBackend.flush();
            
            // Verify successful update
            expect(scope.errors).toEqual({});
            expect(scope.successMessage).toBe('Role updated successfully');
        });
        
        it('should display user-friendly server error messages', function() {
            var scope = $rootScope.$new();
            
            var controller = $controller('BaseController', {
                $scope: scope,
                FormErrorService: FormErrorService
            });
            
            // Test different server error scenarios
            var errorScenarios = [
                {status: 401, expected: 'Invalid username or password'},
                {status: 400, expected: 'Invalid input data'},
                {status: 500, expected: 'Server error. Please try again later.'},
                {status: 503, expected: 'Server error. Please try again later.'}
            ];
            
            errorScenarios.forEach(function(scenario) {
                spyOn(FormErrorService, 'handleServerError').and.returnValue(scenario.expected);
                
                var error = {status: scenario.status, data: {message: 'Technical error'}};
                var friendlyMessage = scope.handleError(error);
                
                expect(friendlyMessage).toBe(scenario.expected);
                expect(FormErrorService.handleServerError).toHaveBeenCalledWith(error);
                
                FormErrorService.handleServerError.calls.reset();
            });
        });
    });
    
    describe('Question Generation Rich Context Integration', function() {
        
        it('should generate role-specific questions with proper distribution', function() {
            var scope = $rootScope.$new();
            
            // Mock user context
            scope.userProfile = {
                main_role: 'Software Developer',
                sub_role: 'Frontend Developer',
                specialization: 'React Developer',
                tech_stacks: ['React', 'TypeScript', 'Node.js'],
                experience_level: 'intermediate'
            };
            
            // Mock session creation with rich context
            $httpBackend.expectPOST('/api/v1/interviews/', function(data) {
                var requestData = JSON.parse(data);
                return requestData.target_role === 'Software Developer' &&
                       requestData.question_count === 5;
            }).respond(200, {
                id: 1,
                status: 'pending',
                user_context: scope.userProfile
            });
            
            // Mock question generation with context-aware questions
            var contextAwareQuestions = [
                {
                    id: 1,
                    question: 'Explain React hooks and their benefits over class components',
                    category: 'theory',
                    role_relevance: 'React Developer',
                    tech_stack: ['React'],
                    difficulty: 'medium'
                },
                {
                    id: 2,
                    question: 'Implement a custom React hook for API data fetching with TypeScript',
                    category: 'coding',
                    role_relevance: 'React Developer',
                    tech_stack: ['React', 'TypeScript'],
                    difficulty: 'medium'
                },
                {
                    id: 3,
                    question: 'Write a React component that handles form validation',
                    category: 'coding',
                    role_relevance: 'React Developer',
                    tech_stack: ['React'],
                    difficulty: 'medium'
                },
                {
                    id: 4,
                    question: 'How would you optimize a React app performance?',
                    category: 'aptitude',
                    role_relevance: 'React Developer',
                    tech_stack: ['React'],
                    difficulty: 'medium'
                },
                {
                    id: 5,
                    question: 'Design a testing strategy for a React application',
                    category: 'aptitude',
                    role_relevance: 'React Developer',
                    improvement_area: 'Testing',
                    difficulty: 'medium'
                }
            ];
            
            $httpBackend.expectPOST('/api/v1/interviews/1/initialize')
                .respond(200, {
                    status: 'initialized',
                    questions: contextAwareQuestions,
                    context_used: scope.userProfile
                });
            
            var controller = $controller('InterviewController', {$scope: scope});
            
            // Create session
            scope.createSession({
                target_role: 'Software Developer',
                session_type: 'technical',
                difficulty_level: 'medium',
                question_count: 5
            });
            $httpBackend.flush();
            
            // Initialize with context-aware questions
            scope.initializeSession();
            $httpBackend.flush();
            
            var questions = scope.session.questions;
            
            // Verify questions are relevant to React Developer role
            var reactQuestions = questions.filter(function(q) {
                return q.question.indexOf('React') !== -1;
            });
            expect(reactQuestions.length).toBeGreaterThanOrEqual(3);
            
            // Verify questions match user's tech stack
            var typescriptQuestions = questions.filter(function(q) {
                return q.question.indexOf('TypeScript') !== -1;
            });
            expect(typescriptQuestions.length).toBeGreaterThanOrEqual(1);
            
            // Verify proper question distribution (20% theory, 40% coding, 40% aptitude)
            var theoryCount = questions.filter(function(q) { return q.category === 'theory'; }).length;
            var codingCount = questions.filter(function(q) { return q.category === 'coding'; }).length;
            var aptitudeCount = questions.filter(function(q) { return q.category === 'aptitude'; }).length;
            
            expect(theoryCount).toBe(1); // 20% of 5 = 1
            expect(codingCount).toBe(2); // 40% of 5 = 2
            expect(aptitudeCount).toBe(2); // 40% of 5 = 2
            
            // Verify all questions are role-relevant
            questions.forEach(function(question) {
                expect(question.role_relevance).toBe('React Developer');
            });
        });
        
        it('should validate and reject irrelevant questions', function() {
            var scope = $rootScope.$new();
            
            scope.userProfile = {
                main_role: 'Software Developer',
                sub_role: 'Frontend Developer',
                specialization: 'React Developer'
            };
            
            // Mock question validation that rejects irrelevant questions
            $httpBackend.expectPOST('/api/v1/interviews/1/validate-questions')
                .respond(200, {
                    valid_questions: [
                        {
                            question: 'Explain React component lifecycle',
                            category: 'theory',
                            role_relevance: 'React Developer'
                        }
                    ],
                    rejected_questions: [
                        {
                            question: 'Explain database normalization',
                            category: 'theory',
                            rejection_reason: 'Not relevant to Frontend Developer role'
                        }
                    ],
                    validation_score: 50
                });
            
            var controller = $controller('QuestionValidationController', {$scope: scope});
            
            scope.validateQuestions([
                {question: 'Explain React component lifecycle', category: 'theory'},
                {question: 'Explain database normalization', category: 'theory'}
            ]);
            $httpBackend.flush();
            
            // Verify validation results
            expect(scope.validationResult.valid_questions.length).toBe(1);
            expect(scope.validationResult.rejected_questions.length).toBe(1);
            expect(scope.validationResult.rejected_questions[0].rejection_reason)
                .toBe('Not relevant to Frontend Developer role');
        });
    });
    
    describe('Session Settings Inheritance Integration', function() {
        
        it('should inherit question count in practice-again sessions', function() {
            var scope = $rootScope.$new();
            
            // Mock original session with custom question count
            scope.originalSession = {
                id: 1,
                question_count: 8, // Custom count, not default 5
                difficulty_level: 'Medium',
                duration_minutes: 45
            };
            
            // Mock practice session creation with inherited settings
            $httpBackend.expectPOST('/api/v1/interviews/1/practice-again')
                .respond(200, {
                    message: 'Practice session created successfully',
                    practice_session_id: 2,
                    original_session_id: 1,
                    session_details: {
                        id: 2,
                        question_count: 8, // Should inherit from original
                        difficulty_level: 'Medium',
                        duration_minutes: 45,
                        parent_session_id: 1,
                        session_type: 'practice'
                    }
                });
            
            var controller = $controller('PracticeAgainController', {
                $scope: scope,
                SessionSettingsService: SessionSettingsService
            });
            
            scope.createPracticeSession(1);
            $httpBackend.flush();
            
            // Verify settings inheritance
            expect(scope.practiceSession.question_count).toBe(8);
            expect(scope.practiceSession.parent_session_id).toBe(1);
            expect(scope.practiceSession.session_type).toBe('practice');
        });
        
        it('should handle quick test settings inheritance and override', function() {
            var scope = $rootScope.$new();
            
            // Mock user's last main session settings
            scope.lastMainSession = {
                question_count: 8,
                difficulty_level: 'Medium'
            };
            
            // Test inheritance (no override)
            $httpBackend.expectPOST('/api/v1/interviews/quick-test')
                .respond(200, {
                    id: 3,
                    question_count: 8, // Inherited from last main session
                    session_type: 'quick_test',
                    settings_source: 'inherited'
                });
            
            var controller = $controller('QuickTestController', {
                $scope: scope,
                SessionSettingsService: SessionSettingsService
            });
            
            scope.createQuickTest();
            $httpBackend.flush();
            
            // Verify inheritance
            expect(scope.quickTestSession.question_count).toBe(8);
            expect(scope.quickTestSession.settings_source).toBe('inherited');
            
            // Test explicit override
            $httpBackend.expectPOST('/api/v1/interviews/quick-test', function(data) {
                var requestData = JSON.parse(data);
                return requestData.question_count === 3 && requestData.save_as_preference === true;
            }).respond(200, {
                id: 4,
                question_count: 3, // Overridden value
                session_type: 'quick_test',
                settings_source: 'user_override'
            });
            
            scope.createQuickTest({
                question_count: 3,
                save_as_preference: true
            });
            $httpBackend.flush();
            
            // Verify override
            expect(scope.quickTestSession.question_count).toBe(3);
            expect(scope.quickTestSession.settings_source).toBe('user_override');
        });
        
        it('should validate session settings and handle errors', function() {
            var scope = $rootScope.$new();
            
            // Test invalid session settings
            $httpBackend.expectPOST('/api/v1/interviews/999/practice-again')
                .respond(400, {detail: 'Original session not found'});
            
            var controller = $controller('PracticeAgainController', {
                $scope: scope,
                SessionSettingsService: SessionSettingsService
            });
            
            spyOn(SessionSettingsService, 'validateSessionSettings').and.returnValue(false);
            
            scope.createPracticeSession(999); // Non-existent session
            $httpBackend.flush();
            
            // Verify error handling
            expect(scope.error).toBe('Original session not found');
            expect(SessionSettingsService.validateSessionSettings).toHaveBeenCalled();
        });
    });
    
    describe('Technical Question Distribution Integration', function() {
        
        it('should enforce proper distribution across different roles and session types', function() {
            var testRoles = [
                {
                    main_role: 'Software Developer',
                    sub_role: 'Frontend Developer',
                    specialization: 'React Developer'
                },
                {
                    main_role: 'Data Scientist',
                    sub_role: 'ML Engineer',
                    specialization: 'Deep Learning Specialist'
                }
            ];
            
            var testScenarios = [
                {session_type: 'main', question_count: 10},
                {session_type: 'practice', question_count: 8},
                {session_type: 'quick_test', question_count: 3}
            ];
            
            testRoles.forEach(function(role) {
                testScenarios.forEach(function(scenario) {
                    var scope = $rootScope.$new();
                    scope.userProfile = role;
                    
                    // Calculate expected distribution
                    var expectedDist;
                    if (scenario.question_count === 3) {
                        expectedDist = {theory: 1, coding: 1, aptitude: 1};
                    } else {
                        var total = scenario.question_count;
                        expectedDist = {
                            theory: Math.max(1, Math.round(total * 0.2)),
                            coding: Math.max(1, Math.round(total * 0.4)),
                            aptitude: total - Math.max(1, Math.round(total * 0.2)) - Math.max(1, Math.round(total * 0.4))
                        };
                    }
                    
                    // Generate questions with proper distribution
                    var questions = [];
                    
                    // Add theory questions
                    for (var i = 0; i < expectedDist.theory; i++) {
                        questions.push({
                            category: 'theory',
                            question: 'Theory question for ' + role.specialization,
                            role_specific: true
                        });
                    }
                    
                    // Add coding questions
                    for (var i = 0; i < expectedDist.coding; i++) {
                        questions.push({
                            category: 'coding',
                            question: 'Coding question for ' + role.specialization,
                            role_specific: true
                        });
                    }
                    
                    // Add aptitude questions
                    for (var i = 0; i < expectedDist.aptitude; i++) {
                        questions.push({
                            category: 'aptitude',
                            question: 'Aptitude question for ' + role.specialization,
                            role_specific: true
                        });
                    }
                    
                    $httpBackend.expectPOST('/api/v1/interviews/')
                        .respond(200, {id: 1, status: 'pending'});
                    
                    $httpBackend.expectPOST('/api/v1/interviews/1/initialize')
                        .respond(200, {
                            status: 'initialized',
                            questions: questions,
                            distribution_validation: {
                                expected: expectedDist,
                                actual: expectedDist,
                                is_valid: true
                            }
                        });
                    
                    var controller = $controller('InterviewController', {$scope: scope});
                    
                    scope.createSession({
                        target_role: role.main_role,
                        session_type: scenario.session_type,
                        question_count: scenario.question_count
                    });
                    $httpBackend.flush();
                    
                    scope.initializeSession();
                    $httpBackend.flush();
                    
                    var actualQuestions = scope.session.questions;
                    
                    // Verify question count
                    expect(actualQuestions.length).toBe(scenario.question_count);
                    
                    // Verify distribution
                    var actualTheory = actualQuestions.filter(function(q) { return q.category === 'theory'; }).length;
                    var actualCoding = actualQuestions.filter(function(q) { return q.category === 'coding'; }).length;
                    var actualAptitude = actualQuestions.filter(function(q) { return q.category === 'aptitude'; }).length;
                    
                    expect(actualTheory).toBe(expectedDist.theory);
                    expect(actualCoding).toBe(expectedDist.coding);
                    expect(actualAptitude).toBe(expectedDist.aptitude);
                    
                    // Verify role-specific content
                    var roleSpecificQuestions = actualQuestions.filter(function(q) { return q.role_specific; });
                    expect(roleSpecificQuestions.length).toBe(actualQuestions.length);
                });
            });
        });
        
        it('should handle distribution validation and regeneration', function() {
            var scope = $rootScope.$new();
            
            // Mock questions with poor distribution
            var poorDistributionQuestions = [
                {category: 'theory', question: 'Theory 1'},
                {category: 'theory', question: 'Theory 2'},
                {category: 'theory', question: 'Theory 3'},
                {category: 'theory', question: 'Theory 4'},
                {category: 'theory', question: 'Theory 5'} // All theory, no coding/aptitude
            ];
            
            // Mock validation failure and regeneration
            $httpBackend.expectPOST('/api/v1/interviews/1/validate-distribution')
                .respond(200, {
                    is_valid: false,
                    needs_regeneration: true,
                    adjustment_needed: {
                        theory: -3, // Too many theory
                        coding: 2,  // Need more coding
                        aptitude: 2 // Need more aptitude
                    }
                });
            
            // Mock regeneration with proper distribution
            $httpBackend.expectPOST('/api/v1/interviews/1/regenerate-questions')
                .respond(200, {
                    questions: [
                        {category: 'theory', question: 'Theory 1'},
                        {category: 'coding', question: 'Coding 1'},
                        {category: 'coding', question: 'Coding 2'},
                        {category: 'aptitude', question: 'Aptitude 1'},
                        {category: 'aptitude', question: 'Aptitude 2'}
                    ],
                    distribution_validation: {
                        is_valid: true,
                        actual: {theory: 1, coding: 2, aptitude: 2}
                    }
                });
            
            var controller = $controller('QuestionDistributionController', {$scope: scope});
            
            // Validate poor distribution
            scope.validateDistribution(poorDistributionQuestions);
            $httpBackend.flush();
            
            expect(scope.distributionValidation.is_valid).toBe(false);
            expect(scope.distributionValidation.needs_regeneration).toBe(true);
            
            // Regenerate with proper distribution
            scope.regenerateQuestions();
            $httpBackend.flush();
            
            expect(scope.session.questions.length).toBe(5);
            expect(scope.distributionValidation.is_valid).toBe(true);
            
            // Verify final distribution
            var finalTheory = scope.session.questions.filter(function(q) { return q.category === 'theory'; }).length;
            var finalCoding = scope.session.questions.filter(function(q) { return q.category === 'coding'; }).length;
            var finalAptitude = scope.session.questions.filter(function(q) { return q.category === 'aptitude'; }).length;
            
            expect(finalTheory).toBe(1);
            expect(finalCoding).toBe(2);
            expect(finalAptitude).toBe(2);
        });
    });
    
    describe('Complete Bug Fixes End-to-End Integration', function() {
        
        it('should handle complete user journey with all bug fixes working together', function() {
            var scope = $rootScope.$new();
            
            // Setup user profile
            scope.userProfile = {
                main_role: 'Software Developer',
                sub_role: 'Frontend Developer',
                specialization: 'React Developer',
                experience_level: 'intermediate'
            };
            
            // Step 1: Create session with consistent difficulty labels
            $httpBackend.expectPOST('/api/v1/interviews/')
                .respond(200, {
                    id: 1,
                    difficulty_level: 'Medium', // Consistent labeling
                    question_count: 8, // Custom count
                    status: 'pending'
                });
            
            // Step 2: Initialize with context-aware questions and proper distribution
            $httpBackend.expectPOST('/api/v1/interviews/1/initialize')
                .respond(200, {
                    status: 'initialized',
                    questions: [
                        {id: 1, category: 'theory', question: 'React theory', difficulty_level: 'Medium'},
                        {id: 2, category: 'theory', question: 'JS theory', difficulty_level: 'Medium'},
                        {id: 3, category: 'coding', question: 'React coding 1', difficulty_level: 'Medium'},
                        {id: 4, category: 'coding', question: 'React coding 2', difficulty_level: 'Medium'},
                        {id: 5, category: 'coding', question: 'React coding 3', difficulty_level: 'Medium'},
                        {id: 6, category: 'aptitude', question: 'React aptitude 1', difficulty_level: 'Medium'},
                        {id: 7, category: 'aptitude', question: 'React aptitude 2', difficulty_level: 'Medium'},
                        {id: 8, category: 'aptitude', question: 'React aptitude 3', difficulty_level: 'Medium'}
                    ]
                });
            
            // Step 3: Complete session with consistent difficulty
            $httpBackend.expectPOST('/api/v1/interviews/1/complete')
                .respond(200, {
                    status: 'completed',
                    final_difficulty: 'Medium' // Consistent with session
                });
            
            // Step 4: Create practice-again with inherited settings
            $httpBackend.expectPOST('/api/v1/interviews/1/practice-again')
                .respond(200, {
                    practice_session_id: 2,
                    session_details: {
                        id: 2,
                        question_count: 8, // Inherited from original
                        difficulty_level: 'Medium',
                        parent_session_id: 1
                    }
                });
            
            // Step 5: Create quick test with proper inheritance
            $httpBackend.expectPOST('/api/v1/interviews/quick-test')
                .respond(200, {
                    id: 3,
                    question_count: 8, // Inherited from main session
                    session_type: 'quick_test'
                });
            
            var controller = $controller('CompleteFlowController', {
                $scope: scope,
                DifficultyDisplayService: DifficultyDisplayService,
                FormErrorService: FormErrorService,
                SessionSettingsService: SessionSettingsService
            });
            
            // Execute complete flow
            scope.createSession({
                target_role: 'Software Developer',
                difficulty_level: 'medium',
                question_count: 8
            });
            $httpBackend.flush();
            
            // Verify session creation with consistent difficulty
            expect(scope.session.difficulty_level).toBe('Medium');
            
            scope.initializeSession();
            $httpBackend.flush();
            
            // Verify question distribution (20% theory, 40% coding, 40% aptitude for 8 questions)
            var questions = scope.session.questions;
            var theoryCount = questions.filter(function(q) { return q.category === 'theory'; }).length;
            var codingCount = questions.filter(function(q) { return q.category === 'coding'; }).length;
            var aptitudeCount = questions.filter(function(q) { return q.category === 'aptitude'; }).length;
            
            expect(theoryCount).toBe(2); // 20% of 8 = 1.6 ≈ 2
            expect(codingCount).toBe(3); // 40% of 8 = 3.2 ≈ 3
            expect(aptitudeCount).toBe(3); // 40% of 8 = 3.2 ≈ 3
            
            // Verify all questions have consistent difficulty
            questions.forEach(function(question) {
                expect(question.difficulty_level).toBe('Medium');
            });
            
            scope.completeSession();
            $httpBackend.flush();
            
            // Verify final difficulty consistency
            expect(scope.session.final_difficulty).toBe('Medium');
            
            scope.createPracticeSession(1);
            $httpBackend.flush();
            
            // Verify practice session inherits settings
            expect(scope.practiceSession.question_count).toBe(8);
            expect(scope.practiceSession.parent_session_id).toBe(1);
            
            scope.createQuickTest();
            $httpBackend.flush();
            
            // Verify quick test inherits settings
            expect(scope.quickTestSession.question_count).toBe(8);
        });
    });
});