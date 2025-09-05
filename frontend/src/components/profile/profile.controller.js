/**
 * Profile Controller - Component-based Architecture
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .controller('ProfileController', ProfileController);

    ProfileController.$inject = ['$location', 'AuthService', 'UserService', 'RoleHierarchyService'];

    function ProfileController($location, AuthService, UserService, RoleHierarchyService) {
        var vm = this;

        // Properties
        vm.user = AuthService.getCurrentUser() || {};
        vm.activeTab = 'profile';
        vm.loading = false;
        vm.error = '';
        vm.success = '';

        // Profile form
        vm.profileForm = {
            name: vm.user.name || '',
            email: vm.user.email || '',
            experience_level: vm.user.experience_level || '',
            target_roles: vm.user.target_roles || [],
            primaryRole: vm.user.primary_role || null // New hierarchical role
        };
        
        // UI state
        vm.showAdditionalRoles = false;

        // Password form
        vm.passwordForm = {
            current_password: '',
            new_password: '',
            confirm_password: ''
        };

        // Options
        vm.experienceLevels = [
            { value: 'beginner', label: 'Beginner (0-2 years)' },
            { value: 'intermediate', label: 'Intermediate (3-5 years)' },
            { value: 'senior', label: 'Senior (5-10 years)' },
            { value: 'expert', label: 'Expert (10+ years)' }
        ];

        vm.availableRoles = [];
        vm.loadingRoles = false;

        // Methods
        vm.setActiveTab = setActiveTab;
        vm.updateProfile = updateProfile;
        vm.changePassword = changePassword;
        vm.toggleTargetRole = toggleTargetRole;
        vm.onPrimaryRoleChange = onPrimaryRoleChange;
        vm.exportData = exportData;
        vm.deleteAccount = deleteAccount;
        vm.logout = logout;
        vm.loadAvailableRoles = loadAvailableRoles;

        // Initialize
        activate();

        function activate() {
            if (!AuthService.isAuthenticated()) {
                $location.path('/login');
                return;
            }
            
            // Load available roles from API
            loadAvailableRoles();
        }

        function loadAvailableRoles() {
            vm.loadingRoles = true;
            
            RoleHierarchyService.getMainRoles()
                .then(function(roles) {
                    vm.availableRoles = roles;
                })
                .catch(function(error) {
                    console.error('Error loading roles:', error);
                    // Fallback to basic roles if API fails
                    vm.availableRoles = [
                        'Software Developer',
                        'Data Scientist', 
                        'Product Manager',
                        'DevOps Engineer',
                        'UX/UI Designer'
                    ];
                })
                .finally(function() {
                    vm.loadingRoles = false;
                });
        }

        function setActiveTab(tab) {
            vm.activeTab = tab;
            vm.error = '';
            vm.success = '';
        }

        function onPrimaryRoleChange(role) {
            console.log('Primary role changed:', role);
            vm.profileForm.primaryRole = role;
            
            // Clear any previous errors
            if (vm.error && vm.error.includes('role')) {
                vm.error = '';
            }
        }

        function updateProfile() {
            vm.loading = true;
            vm.error = '';
            vm.success = '';

            // Validate form
            if (!vm.profileForm.name || !vm.profileForm.email) {
                vm.error = 'Name and email are required.';
                vm.loading = false;
                return;
            }

            // Email validation
            var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(vm.profileForm.email)) {
                vm.error = 'Please enter a valid email address.';
                vm.loading = false;
                return;
            }

            // Prepare profile data with hierarchical role structure
            var profileData = angular.copy(vm.profileForm);
            
            // If primaryRole is hierarchical, update the role data structure
            if (profileData.primaryRole && typeof profileData.primaryRole === 'object') {
                profileData.hierarchical_role = {
                    main_role: profileData.primaryRole.mainRole,
                    sub_role: profileData.primaryRole.subRole,
                    specialization: profileData.primaryRole.specialization,
                    tech_stack: profileData.primaryRole.techStack
                };
                
                // Keep backward compatibility
                profileData.primary_role = profileData.primaryRole.displayName || profileData.primaryRole.mainRole;
            }

            UserService.updateProfile(profileData)
                .then(function(response) {
                    vm.success = 'Profile updated successfully!';
                    // Update user data in AuthService
                    AuthService.updateUser(response);
                    vm.user = response;
                })
                .catch(function(error) {
                    vm.error = error.data?.detail || 'Failed to update profile.';
                })
                .finally(function() {
                    vm.loading = false;
                });
        }

        function changePassword() {
            vm.loading = true;
            vm.error = '';
            vm.success = '';

            // Validate passwords
            if (!vm.passwordForm.current_password || !vm.passwordForm.new_password || !vm.passwordForm.confirm_password) {
                vm.error = 'All password fields are required.';
                vm.loading = false;
                return;
            }

            if (vm.passwordForm.new_password !== vm.passwordForm.confirm_password) {
                vm.error = 'New passwords do not match.';
                vm.loading = false;
                return;
            }

            if (vm.passwordForm.new_password.length < 8) {
                vm.error = 'New password must be at least 8 characters long.';
                vm.loading = false;
                return;
            }

            UserService.changePassword({
                old_password: vm.passwordForm.current_password,
                new_password: vm.passwordForm.new_password
            })
                .then(function(response) {
                    vm.success = 'Password changed successfully!';
                    // Clear password form
                    vm.passwordForm = {
                        current_password: '',
                        new_password: '',
                        confirm_password: ''
                    };
                })
                .catch(function(error) {
                    vm.error = error.data?.detail || 'Failed to change password.';
                })
                .finally(function() {
                    vm.loading = false;
                });
        }

        function toggleTargetRole(role) {
            var index = vm.profileForm.target_roles.indexOf(role);
            if (index > -1) {
                vm.profileForm.target_roles.splice(index, 1);
            } else {
                vm.profileForm.target_roles.push(role);
            }
        }

        function exportData() {
            if (vm.loading) return; // Prevent multiple clicks
            
            vm.loading = true;
            vm.error = '';
            vm.success = '';

            console.log('Starting data export...');

            UserService.exportUserData()
                .then(function(response) {
                    console.log('Export response:', response);
                    
                    // Handle the response structure from backend
                    var exportData = response.data || response;
                    var dataStr = JSON.stringify(exportData, null, 2);
                    var dataBlob = new Blob([dataStr], { type: 'application/json' });
                    var url = URL.createObjectURL(dataBlob);
                    
                    // Create download link
                    var link = document.createElement('a');
                    link.href = url;
                    link.download = 'interview-prep-data-' + new Date().toISOString().split('T')[0] + '.json';
                    link.style.display = 'none';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    URL.revokeObjectURL(url);
                    
                    vm.success = 'Data exported successfully! Check your downloads folder.';
                })
                .catch(function(error) {
                    console.error('Export error:', error);
                    if (error.status === 429) {
                        vm.error = 'Too many export requests. Please wait before trying again.';
                    } else if (error.status === 401) {
                        vm.error = 'Authentication required. Please log in again.';
                    } else {
                        vm.error = error.data?.detail || 'Failed to export data. Please try again.';
                    }
                })
                .finally(function() {
                    vm.loading = false;
                });
        }

        function deleteAccount() {
            if (vm.loading) return; // Prevent multiple clicks
            
            var confirmMessage = 'WARNING: This will permanently delete your account!\n\n' +
                'All of the following data will be permanently removed:\n' +
                '• Profile information and settings\n' +
                '• Interview session history and recordings\n' +
                '• Progress tracking and analytics data\n' +
                '• All personal preferences\n\n' +
                'This action CANNOT be undone!\n\n' +
                'Type "DELETE" exactly to confirm account deletion:';
            
            var userInput = prompt(confirmMessage);
            
            if (userInput === 'DELETE') {
                // Double confirmation
                var finalConfirm = confirm('FINAL CONFIRMATION: Are you absolutely sure you want to delete your account? This cannot be undone!');
                
                if (finalConfirm) {
                    vm.loading = true;
                    vm.error = '';
                    vm.success = '';

                    console.log('Proceeding with account deletion...');

                    UserService.deleteProfile()
                        .then(function(response) {
                            console.log('Account deletion successful:', response);
                            alert('Your account has been successfully deleted. You will now be logged out.');
                            // Clear all auth data and redirect
                            AuthService.logout();
                        })
                        .catch(function(error) {
                            console.error('Delete account error:', error);
                            if (error.status === 429) {
                                vm.error = 'Too many deletion requests. Please wait before trying again.';
                            } else if (error.status === 401) {
                                vm.error = 'Authentication required. Please log in again to delete your account.';
                            } else if (error.status === 403) {
                                vm.error = 'Account deletion not allowed. Please verify your email first.';
                            } else {
                                vm.error = error.data?.detail || 'Failed to delete account. Please contact support if this problem persists.';
                            }
                        })
                        .finally(function() {
                            vm.loading = false;
                        });
                } else {
                    console.log('Account deletion cancelled at final confirmation');
                }
            } else if (userInput !== null && userInput !== '') {
                vm.error = 'Account deletion cancelled. You must type "DELETE" exactly to confirm.';
            }
            // If userInput is null (user clicked Cancel) or empty string, do nothing
        }

        function logout() {
            if (confirm('Are you sure you want to logout?')) {
                AuthService.logout();
            }
        }
    }
})();