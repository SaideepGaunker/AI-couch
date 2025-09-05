/**
 * Register Controller - Component-based Architecture
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .controller('RegisterController', RegisterController);

    RegisterController.$inject = ['$location', 'AuthService'];

    function RegisterController($location, AuthService) {
        var vm = this;

        // Properties
        vm.registerForm = {
            name: '',
            email: '',
            password: '',
            confirmPassword: '',
            role: '',
            experience_level: '',
            target_roles: []
        };
        vm.loading = false;
        vm.error = '';
        vm.success = '';

        // Options
        vm.roles = [
            { value: 'job_seeker', label: 'Job Seeker' },
            { value: 'student', label: 'Student' },
            { value: 'admin', label: 'Admin' }
        ];

        vm.experienceLevels = [
            { value: 'entry', label: 'Entry Level (0-2 years)' },
            { value: 'mid', label: 'Mid Level (3-5 years)' },
            { value: 'senior', label: 'Senior Level (6-10 years)' },
            { value: 'lead', label: 'Lead/Principal (10+ years)' },
            { value: 'executive', label: 'Executive/C-Level' }
        ];

        vm.targetRoleOptions = [
            'Software Engineer',
            'Product Manager',
            'Data Scientist',
            'Marketing Manager',
            'Sales Representative',
            'Business Analyst',
            'Project Manager',
            'UX Designer'
        ];

        // Methods
        vm.register = register;
        vm.toggleTargetRole = toggleTargetRole;

        // Initialize
        activate();

        function activate() {
            // Check if user is already authenticated
            if (AuthService.isAuthenticated()) {
                $location.path('/dashboard');
            }
        }

        function register() {
            if (!validateForm()) {
                return;
            }

            vm.loading = true;
            vm.error = '';
            vm.success = '';

            AuthService.register(vm.registerForm)
                .then(function(response) {
                    console.log('Registration successful:', response);
                    vm.success = 'Account created successfully! Please log in.';
                    
                    // Redirect to login after a short delay
                    setTimeout( () => {
                        $location.path('/login');
                    }, 1000);
                })
                .catch(function(error) {
                    console.error('Registration error:', error);
                    vm.error = error || 'Registration failed. Please try again.';
                })
                .finally(function() {
                    vm.loading = false;
                });
        }

        function toggleTargetRole(role) {
            var index = vm.registerForm.target_roles.indexOf(role);
            if (index > -1) {
                vm.registerForm.target_roles.splice(index, 1);
            } else {
                vm.registerForm.target_roles.push(role);
            }
        }

        function validateForm() {
            // Reset error
            vm.error = '';

            // Check required fields
            if (!vm.registerForm.name || !vm.registerForm.email || 
                !vm.registerForm.password || !vm.registerForm.confirmPassword || 
                !vm.registerForm.role) {
                vm.error = 'Please fill in all required fields.';
                return false;
            }

            // Validate email format
            var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(vm.registerForm.email)) {
                vm.error = 'Please enter a valid email address.';
                return false;
            }

            // Validate password strength
            if (vm.registerForm.password.length < 8) {
                vm.error = 'Password must be at least 8 characters long.';
                return false;
            }

            var passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/;
            if (!passwordRegex.test(vm.registerForm.password)) {
                vm.error = 'Password must contain at least one uppercase letter, one lowercase letter, and one number.';
                return false;
            }

            // Check password confirmation
            if (vm.registerForm.password !== vm.registerForm.confirmPassword) {
                vm.error = 'Passwords do not match.';
                return false;
            }

            return true;
        }
    }
})();