/**
 * Role Selector Component
 * Multi-level dropdown interface for hierarchical role selection
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .component('roleSelector', {
            templateUrl: 'components/role-selector/role-selector.template.html',
            controller: RoleSelectorController,
            controllerAs: 'vm',
            bindings: {
                selectedRole: '=',
                onRoleChange: '&',
                disabled: '<',
                required: '<',
                showTechStack: '<'
            }
        });

    RoleSelectorController.$inject = ['$scope', 'RoleHierarchyService', '$log', 'FormErrorService'];

    function RoleSelectorController($scope, RoleHierarchyService, $log, FormErrorService) {
        var vm = this;

        // Component properties
        vm.roleHierarchy = {};
        vm.mainRoles = [];
        vm.subRoles = [];
        vm.specializations = [];
        vm.techStacks = [];
        
        // Selected values
        vm.selectedMainRole = null;
        vm.selectedSubRole = null;
        vm.selectedSpecialization = null;
        vm.selectedTechStack = [];
        
        // Component state
        vm.loading = false;
        vm.loadingSubRoles = false;
        vm.loadingSpecializations = false;
        vm.loadingTechStacks = false;
        vm.error = null;
        vm.fieldErrors = {};

        // Public methods
        vm.$onInit = onInit;
        vm.$onChanges = onChanges;
        vm.onMainRoleChange = onMainRoleChange;
        vm.onSubRoleChange = onSubRoleChange;
        vm.onSpecializationChange = onSpecializationChange;
        vm.onTechStackChange = onTechStackChange;
        vm.isMainRoleSelected = isMainRoleSelected;
        vm.isSubRoleSelected = isSubRoleSelected;
        vm.hasSpecializations = hasSpecializations;
        vm.hasTechStacks = hasTechStacks;
        vm.resetSelection = resetSelection;
        vm.isValidSelection = isValidSelection;
        vm.getValidationMessage = getValidationMessage;
        vm.validateRoleSelection = validateRoleSelection;
        vm.clearFieldError = clearFieldError;
        vm.hasFieldError = hasFieldError;
        vm.getFieldError = getFieldError;

        /**
         * Component initialization
         */
        function onInit() {
            $log.debug('RoleSelector: Initializing component');
            loadRoleHierarchy();
            
            // Initialize from existing selectedRole if provided
            if (vm.selectedRole) {
                initializeFromSelectedRole();
            }
        }

        /**
         * Handle input changes
         */
        function onChanges(changes) {
            if (changes.selectedRole && !changes.selectedRole.isFirstChange()) {
                initializeFromSelectedRole();
            }
        }

        /**
         * Load role hierarchy data from API
         */
        function loadRoleHierarchy() {
            vm.loading = true;
            vm.error = null;

            RoleHierarchyService.getRoleHierarchy()
                .then(function(roleHierarchy) {
                    vm.roleHierarchy = roleHierarchy;
                    vm.mainRoles = Object.keys(vm.roleHierarchy);
                    $log.debug('RoleSelector: Loaded role hierarchy', vm.roleHierarchy);
                })
                .catch(function(error) {
                    vm.error = 'Failed to load role options';
                    $log.error('RoleSelector: Error loading role hierarchy', error);
                })
                .finally(function() {
                    vm.loading = false;
                });
        }



        /**
         * Initialize component from existing selectedRole
         */
        function initializeFromSelectedRole() {
            if (!vm.selectedRole) return;

            try {
                if (typeof vm.selectedRole === 'string') {
                    // Legacy format - just set as main role
                    vm.selectedMainRole = vm.selectedRole;
                    updateSubRoles();
                } else if (typeof vm.selectedRole === 'object') {
                    // New hierarchical format
                    vm.selectedMainRole = vm.selectedRole.mainRole;
                    vm.selectedSubRole = vm.selectedRole.subRole;
                    vm.selectedSpecialization = vm.selectedRole.specialization;
                    vm.selectedTechStack = vm.selectedRole.techStack || [];
                    
                    updateSubRoles();
                    updateSpecializations();
                    updateTechStacks();
                }
            } catch (error) {
                $log.error('RoleSelector: Error initializing from selectedRole', error);
            }
        }

        /**
         * Handle main role selection change
         */
        function onMainRoleChange() {
            $log.debug('RoleSelector: Main role changed to', vm.selectedMainRole);
            
            // Clear field errors for main role
            clearFieldError('mainRole');
            clearFieldError('roleCompatibility');
            
            // Reset dependent selections
            vm.selectedSubRole = null;
            vm.selectedSpecialization = null;
            vm.selectedTechStack = [];
            
            // Update available options
            updateSubRoles();
            updateSpecializations();
            updateTechStacks();
            
            // Validate selection
            if (vm.required) {
                validateRoleSelection();
            }
            
            // Notify parent component
            notifyRoleChange();
        }

        /**
         * Handle sub role selection change
         */
        function onSubRoleChange() {
            $log.debug('RoleSelector: Sub role changed to', vm.selectedSubRole);
            
            // Clear field errors for sub role
            clearFieldError('subRole');
            clearFieldError('roleCompatibility');
            
            // Reset dependent selections
            vm.selectedSpecialization = null;
            vm.selectedTechStack = [];
            
            // Update available options
            updateSpecializations();
            updateTechStacks();
            
            // Validate selection
            if (vm.required) {
                validateRoleSelection();
            }
            
            // Notify parent component
            notifyRoleChange();
        }

        /**
         * Handle specialization selection change
         */
        function onSpecializationChange() {
            $log.debug('RoleSelector: Specialization changed to', vm.selectedSpecialization);
            
            // Clear field errors for specialization
            clearFieldError('specialization');
            
            // Validate selection
            if (vm.required) {
                validateRoleSelection();
            }
            
            notifyRoleChange();
        }

        /**
         * Handle tech stack selection change
         */
        function onTechStackChange() {
            $log.debug('RoleSelector: Tech stack changed to', vm.selectedTechStack);
            
            // Clear field errors for tech stack
            clearFieldError('techStack');
            
            // Validate selection
            if (vm.required) {
                validateRoleSelection();
            }
            
            notifyRoleChange();
        }

        /**
         * Update available sub roles based on main role selection
         */
        function updateSubRoles() {
            vm.subRoles = [];
            
            if (vm.selectedMainRole) {
                // Try to get from cached hierarchy first
                if (vm.roleHierarchy && vm.roleHierarchy[vm.selectedMainRole]) {
                    vm.subRoles = Object.keys(vm.roleHierarchy[vm.selectedMainRole]);
                } else {
                    // Fetch from API if not in cache
                    vm.loadingSubRoles = true;
                    RoleHierarchyService.getSubRoles(vm.selectedMainRole)
                        .then(function(subRoles) {
                            vm.subRoles = subRoles;
                        })
                        .catch(function(error) {
                            $log.error('RoleSelector: Error loading sub roles', error);
                            vm.error = 'Failed to load sub roles';
                        })
                        .finally(function() {
                            vm.loadingSubRoles = false;
                        });
                }
            }
        }

        /**
         * Update available specializations based on sub role selection
         */
        function updateSpecializations() {
            vm.specializations = [];
            
            if (vm.selectedMainRole && vm.selectedSubRole) {
                // Try to get from cached hierarchy first
                if (vm.roleHierarchy && 
                    vm.roleHierarchy[vm.selectedMainRole] && 
                    vm.roleHierarchy[vm.selectedMainRole][vm.selectedSubRole]) {
                    
                    var subRoleData = vm.roleHierarchy[vm.selectedMainRole][vm.selectedSubRole];
                    vm.specializations = subRoleData.specializations || [];
                } else {
                    // Fetch from API if not in cache
                    vm.loadingSpecializations = true;
                    RoleHierarchyService.getSpecializations(vm.selectedMainRole, vm.selectedSubRole)
                        .then(function(specializations) {
                            vm.specializations = specializations;
                        })
                        .catch(function(error) {
                            $log.error('RoleSelector: Error loading specializations', error);
                            vm.error = 'Failed to load specializations';
                        })
                        .finally(function() {
                            vm.loadingSpecializations = false;
                        });
                }
            }
        }

        /**
         * Update available tech stacks based on sub role selection
         */
        function updateTechStacks() {
            vm.techStacks = [];
            
            if (vm.selectedMainRole && vm.selectedSubRole) {
                // Try to get from cached hierarchy first
                if (vm.roleHierarchy && 
                    vm.roleHierarchy[vm.selectedMainRole] && 
                    vm.roleHierarchy[vm.selectedMainRole][vm.selectedSubRole]) {
                    
                    var subRoleData = vm.roleHierarchy[vm.selectedMainRole][vm.selectedSubRole];
                    vm.techStacks = subRoleData.tech_stacks || subRoleData.techStacks || [];
                } else {
                    // Fetch from API if not in cache
                    vm.loadingTechStacks = true;
                    RoleHierarchyService.getTechStacks(vm.selectedMainRole, vm.selectedSubRole)
                        .then(function(techStacks) {
                            vm.techStacks = techStacks;
                        })
                        .catch(function(error) {
                            $log.error('RoleSelector: Error loading tech stacks', error);
                            vm.error = 'Failed to load tech stacks';
                        })
                        .finally(function() {
                            vm.loadingTechStacks = false;
                        });
                }
            }
        }

        /**
         * Notify parent component of role changes
         */
        function notifyRoleChange() {
            var roleData = {
                mainRole: vm.selectedMainRole,
                subRole: vm.selectedSubRole,
                specialization: vm.selectedSpecialization,
                techStack: vm.selectedTechStack,
                // Legacy format for backward compatibility
                displayName: buildDisplayName(),
                fullRole: buildDisplayName()
            };

            vm.selectedRole = roleData;

            if (vm.onRoleChange) {
                vm.onRoleChange({ role: roleData });
            }
        }

        /**
         * Build display name for the selected role
         */
        function buildDisplayName() {
            var parts = [];
            
            if (vm.selectedMainRole) {
                parts.push(vm.selectedMainRole);
            }
            
            if (vm.selectedSubRole) {
                parts.push(vm.selectedSubRole);
            }
            
            if (vm.selectedSpecialization) {
                parts.push(vm.selectedSpecialization);
            }
            
            return parts.join(' - ');
        }

        /**
         * Check if main role is selected
         */
        function isMainRoleSelected() {
            return !!vm.selectedMainRole;
        }

        /**
         * Check if sub role is selected
         */
        function isSubRoleSelected() {
            return !!vm.selectedSubRole;
        }

        /**
         * Check if current selection has specializations
         */
        function hasSpecializations() {
            return vm.specializations && vm.specializations.length > 0;
        }

        /**
         * Check if current selection has tech stacks
         */
        function hasTechStacks() {
            return vm.techStacks && vm.techStacks.length > 0;
        }

        /**
         * Reset all selections
         */
        function resetSelection() {
            vm.selectedMainRole = null;
            vm.selectedSubRole = null;
            vm.selectedSpecialization = null;
            vm.selectedTechStack = [];
            
            vm.subRoles = [];
            vm.specializations = [];
            vm.techStacks = [];
            
            notifyRoleChange();
        }

        /**
         * Check if the current role selection is valid
         */
        function isValidSelection() {
            if (vm.required) {
                return vm.selectedMainRole && vm.selectedSubRole;
            }
            return true;
        }

        /**
         * Get validation message for incomplete selection
         */
        function getValidationMessage() {
            if (!vm.selectedMainRole) {
                return 'Please select a main role';
            }
            if (vm.required && !vm.selectedSubRole) {
                return 'Please select a sub role';
            }
            return '';
        }

        /**
         * Validate role selection using FormErrorService
         * @returns {Object} Validation result
         */
        function validateRoleSelection() {
            var roleData = {
                mainRole: vm.selectedMainRole,
                subRole: vm.selectedSubRole,
                specialization: vm.selectedSpecialization,
                techStack: vm.selectedTechStack
            };

            var validation = FormErrorService.validateRoleSelection(roleData);
            
            if (!validation.isValid) {
                vm.fieldErrors = validation.errors;
                $log.debug('RoleSelector: Validation failed', validation.errors);
            } else {
                vm.fieldErrors = {};
            }

            return validation;
        }

        /**
         * Clear error for a specific field
         * @param {string} fieldName - Name of the field to clear error for
         */
        function clearFieldError(fieldName) {
            if (vm.fieldErrors[fieldName]) {
                delete vm.fieldErrors[fieldName];
            }
        }

        /**
         * Check if a field has an error
         * @param {string} fieldName - Name of the field to check
         * @returns {boolean} True if field has error
         */
        function hasFieldError(fieldName) {
            return !!vm.fieldErrors[fieldName];
        }

        /**
         * Get error message for a specific field
         * @param {string} fieldName - Name of the field
         * @returns {string} Error message for the field
         */
        function getFieldError(fieldName) {
            return vm.fieldErrors[fieldName] || '';
        }

        // Watch for external changes to selectedRole
        $scope.$watch('vm.selectedRole', function(newVal, oldVal) {
            if (newVal !== oldVal && newVal) {
                initializeFromSelectedRole();
            }
        }, true);
    }
})();