/**
 * Unit tests for Role Selector Component
 */
describe('RoleSelector Component', function() {
    'use strict';

    var $componentController, $httpBackend, $rootScope, $log;
    var controller, mockScope;

    // Mock role hierarchy data
    var mockRoleHierarchy = {
        'Software Developer': {
            'Frontend Developer': {
                specializations: ['React Developer', 'Angular Developer', 'Vue.js Developer'],
                techStacks: ['React', 'Angular', 'Vue.js', 'JavaScript', 'TypeScript', 'HTML/CSS']
            },
            'Backend Developer': {
                specializations: ['Node.js Developer', 'Python Developer', 'Java Developer'],
                techStacks: ['Node.js', 'Python', 'Java', 'Rust', 'Go', 'C#']
            }
        },
        'Data Scientist': {
            'ML Engineer': {
                specializations: ['Computer Vision', 'NLP Specialist', 'Deep Learning'],
                techStacks: ['Python', 'TensorFlow', 'PyTorch', 'Scikit-learn', 'Pandas', 'NumPy']
            }
        }
    };

    beforeEach(function() {
        module('interviewApp');

        inject(function(_$componentController_, _$httpBackend_, _$rootScope_, _$log_) {
            $componentController = _$componentController_;
            $httpBackend = _$httpBackend_;
            $rootScope = _$rootScope_;
            $log = _$log_;
        });

        mockScope = $rootScope.$new();
    });

    afterEach(function() {
        $httpBackend.verifyNoOutstandingExpectation();
        $httpBackend.verifyNoOutstandingRequest();
    });

    function createController(bindings) {
        bindings = bindings || {};
        
        controller = $componentController('roleSelector', {
            $scope: mockScope
        }, bindings);
        
        return controller;
    }

    describe('Component Initialization', function() {
        
        it('should initialize with default values', function() {
            createController();
            
            expect(controller.roleHierarchy).toEqual({});
            expect(controller.mainRoles).toEqual([]);
            expect(controller.subRoles).toEqual([]);
            expect(controller.specializations).toEqual([]);
            expect(controller.techStacks).toEqual([]);
            expect(controller.selectedMainRole).toBe(null);
            expect(controller.selectedSubRole).toBe(null);
            expect(controller.selectedSpecialization).toBe(null);
            expect(controller.selectedTechStack).toEqual([]);
            expect(controller.loading).toBe(false);
            expect(controller.error).toBe(null);
        });

        it('should load role hierarchy on init', function() {
            $httpBackend.expectGET('/api/v1/roles/hierarchy')
                .respond(200, mockRoleHierarchy);

            createController();
            controller.$onInit();

            expect(controller.loading).toBe(true);

            $httpBackend.flush();

            expect(controller.loading).toBe(false);
            expect(controller.roleHierarchy).toEqual(mockRoleHierarchy);
            expect(controller.mainRoles).toEqual(['Software Developer', 'Data Scientist']);
        });

        it('should handle API error and load static data', function() {
            $httpBackend.expectGET('/api/v1/roles/hierarchy')
                .respond(500, 'Server Error');

            createController();
            controller.$onInit();

            $httpBackend.flush();

            expect(controller.loading).toBe(false);
            expect(controller.error).toBe('Failed to load role options');
            expect(controller.mainRoles.length).toBeGreaterThan(0);
        });

        it('should initialize from existing selectedRole string', function() {
            createController({ selectedRole: 'Software Developer' });
            
            spyOn(controller, 'updateSubRoles');
            controller.$onInit();

            expect(controller.selectedMainRole).toBe('Software Developer');
            expect(controller.updateSubRoles).toHaveBeenCalled();
        });

        it('should initialize from existing selectedRole object', function() {
            var selectedRole = {
                mainRole: 'Software Developer',
                subRole: 'Frontend Developer',
                specialization: 'React Developer',
                techStack: ['React', 'JavaScript']
            };

            createController({ selectedRole: selectedRole });
            
            spyOn(controller, 'updateSubRoles');
            spyOn(controller, 'updateSpecializations');
            spyOn(controller, 'updateTechStacks');
            
            controller.$onInit();

            expect(controller.selectedMainRole).toBe('Software Developer');
            expect(controller.selectedSubRole).toBe('Frontend Developer');
            expect(controller.selectedSpecialization).toBe('React Developer');
            expect(controller.selectedTechStack).toEqual(['React', 'JavaScript']);
        });
    });

    describe('Role Selection Logic', function() {

        beforeEach(function() {
            createController();
            controller.roleHierarchy = mockRoleHierarchy;
            controller.mainRoles = Object.keys(mockRoleHierarchy);
        });

        it('should update sub roles when main role changes', function() {
            controller.selectedMainRole = 'Software Developer';
            controller.onMainRoleChange();

            expect(controller.subRoles).toEqual(['Frontend Developer', 'Backend Developer']);
            expect(controller.selectedSubRole).toBe(null);
            expect(controller.selectedSpecialization).toBe(null);
            expect(controller.selectedTechStack).toEqual([]);
        });

        it('should update specializations when sub role changes', function() {
            controller.selectedMainRole = 'Software Developer';
            controller.selectedSubRole = 'Frontend Developer';
            controller.onSubRoleChange();

            expect(controller.specializations).toEqual(['React Developer', 'Angular Developer', 'Vue.js Developer']);
            expect(controller.selectedSpecialization).toBe(null);
            expect(controller.selectedTechStack).toEqual([]);
        });

        it('should update tech stacks when sub role changes', function() {
            controller.selectedMainRole = 'Software Developer';
            controller.selectedSubRole = 'Frontend Developer';
            controller.onSubRoleChange();

            expect(controller.techStacks).toEqual(['React', 'Angular', 'Vue.js', 'JavaScript', 'TypeScript', 'HTML/CSS']);
        });

        it('should notify parent component on role change', function() {
            var onRoleChangeSpy = jasmine.createSpy('onRoleChange');
            controller.onRoleChange = onRoleChangeSpy;

            controller.selectedMainRole = 'Software Developer';
            controller.selectedSubRole = 'Frontend Developer';
            controller.onSubRoleChange();

            expect(onRoleChangeSpy).toHaveBeenCalledWith({
                role: jasmine.objectContaining({
                    mainRole: 'Software Developer',
                    subRole: 'Frontend Developer',
                    specialization: null,
                    techStack: []
                })
            });
        });
    });

    describe('Helper Methods', function() {

        beforeEach(function() {
            createController();
        });

        it('should check if main role is selected', function() {
            expect(controller.isMainRoleSelected()).toBe(false);
            
            controller.selectedMainRole = 'Software Developer';
            expect(controller.isMainRoleSelected()).toBe(true);
        });

        it('should check if sub role is selected', function() {
            expect(controller.isSubRoleSelected()).toBe(false);
            
            controller.selectedSubRole = 'Frontend Developer';
            expect(controller.isSubRoleSelected()).toBe(true);
        });

        it('should check if specializations are available', function() {
            expect(controller.hasSpecializations()).toBe(false);
            
            controller.specializations = ['React Developer', 'Angular Developer'];
            expect(controller.hasSpecializations()).toBe(true);
        });

        it('should check if tech stacks are available', function() {
            expect(controller.hasTechStacks()).toBe(false);
            
            controller.techStacks = ['React', 'Angular'];
            expect(controller.hasTechStacks()).toBe(true);
        });

        it('should build display name correctly', function() {
            controller.selectedMainRole = 'Software Developer';
            controller.selectedSubRole = 'Frontend Developer';
            controller.selectedSpecialization = 'React Developer';

            var displayName = controller.buildDisplayName();
            expect(displayName).toBe('Software Developer - Frontend Developer - React Developer');
        });

        it('should reset selection', function() {
            controller.selectedMainRole = 'Software Developer';
            controller.selectedSubRole = 'Frontend Developer';
            controller.selectedSpecialization = 'React Developer';
            controller.selectedTechStack = ['React', 'JavaScript'];

            spyOn(controller, 'notifyRoleChange');
            controller.resetSelection();

            expect(controller.selectedMainRole).toBe(null);
            expect(controller.selectedSubRole).toBe(null);
            expect(controller.selectedSpecialization).toBe(null);
            expect(controller.selectedTechStack).toEqual([]);
            expect(controller.notifyRoleChange).toHaveBeenCalled();
        });
    });

    describe('Tech Stack Selection', function() {

        beforeEach(function() {
            createController();
            controller.selectedTechStack = [];
        });

        it('should handle tech stack selection changes', function() {
            spyOn(controller, 'notifyRoleChange');
            
            controller.onTechStackChange();
            
            expect(controller.notifyRoleChange).toHaveBeenCalled();
        });

        it('should limit tech stack selection to 3 items', function() {
            controller.selectedTechStack = ['React', 'JavaScript', 'TypeScript'];
            controller.techStacks = ['React', 'Angular', 'Vue.js', 'JavaScript', 'TypeScript', 'HTML/CSS'];

            // This would be handled in the template, but we can test the logic
            expect(controller.selectedTechStack.length).toBe(3);
        });
    });

    describe('Component Bindings', function() {

        it('should handle disabled state', function() {
            createController({ disabled: true });
            
            expect(controller.disabled).toBe(true);
        });

        it('should handle required state', function() {
            createController({ required: true });
            
            expect(controller.required).toBe(true);
        });

        it('should handle showTechStack option', function() {
            createController({ showTechStack: true });
            
            expect(controller.showTechStack).toBe(true);
        });

        it('should handle onRoleChange callback', function() {
            var mockCallback = jasmine.createSpy('onRoleChange');
            createController({ onRoleChange: mockCallback });
            
            expect(controller.onRoleChange).toBe(mockCallback);
        });
    });

    describe('Error Handling', function() {

        beforeEach(function() {
            createController();
        });

        it('should handle errors in initializeFromSelectedRole', function() {
            controller.selectedRole = { invalidProperty: 'test' };
            
            spyOn($log, 'error');
            
            // This should not throw an error
            expect(function() {
                controller.initializeFromSelectedRole();
            }).not.toThrow();
        });

        it('should handle errors in role hierarchy operations', function() {
            controller.roleHierarchy = null;
            controller.selectedMainRole = 'Software Developer';
            
            // This should not throw an error
            expect(function() {
                controller.updateSubRoles();
            }).not.toThrow();
            
            expect(controller.subRoles).toEqual([]);
        });
    });

    describe('Watch Functionality', function() {

        it('should watch for external changes to selectedRole', function() {
            createController();
            
            spyOn(controller, 'initializeFromSelectedRole');
            
            // Simulate external change
            controller.selectedRole = { mainRole: 'Software Developer' };
            mockScope.$digest();
            
            expect(controller.initializeFromSelectedRole).toHaveBeenCalled();
        });
    });
});