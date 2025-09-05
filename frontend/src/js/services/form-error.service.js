/**
 * Form Error Service - Comprehensive form validation and error handling
 * Provides validation methods for all forms with specific error messages
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .service('FormErrorService', FormErrorService);

    FormErrorService.$inject = ['$log'];

    function FormErrorService($log) {
        var service = {
            // Login form validation
            validateLoginForm: validateLoginForm,
            
            // Role selection validation
            validateRoleSelection: validateRoleSelection,
            
            // Server error handling
            handleServerError: handleServerError,
            
            // Generic form validation
            validateRequiredFields: validateRequiredFields,
            validateEmailFormat: validateEmailFormat,
            validatePasswordStrength: validatePasswordStrength,
            
            // Error message utilities
            getFieldErrorMessage: getFieldErrorMessage,
            formatValidationErrors: formatValidationErrors
        };

        return service;

        // ==================== Login Form Validation ====================

        /**
         * Validate login form data
         * @param {Object} formData - Login form data with email/username and password
         * @returns {Object} Validation result with isValid flag and errors object
         */
        function validateLoginForm(formData) {
            var errors = {};
            
            if (!formData) {
                return {
                    isValid: false,
                    errors: { form: 'Form data is required' }
                };
            }

            // Validate email/username field
            var emailField = formData.email || formData.username;
            if (!emailField || emailField.trim() === '') {
                errors.email = 'Email is required';
                errors.username = 'Username is required';
            } else if (formData.email && !validateEmailFormat(emailField)) {
                errors.email = 'Please enter a valid email address';
            }

            // Validate password field
            if (!formData.password || formData.password.trim() === '') {
                errors.password = 'Password is required';
            }

            var result = {
                isValid: Object.keys(errors).length === 0,
                errors: errors
            };

            $log.debug('FormErrorService: Login form validation result', result);
            return result;
        }

        // ==================== Role Selection Validation ====================

        /**
         * Validate role selection form data
         * @param {Object} roleData - Role selection data
         * @returns {Object} Validation result with isValid flag and errors object
         */
        function validateRoleSelection(roleData) {
            var errors = {};
            
            if (!roleData) {
                return {
                    isValid: false,
                    errors: { form: 'Role selection data is required' }
                };
            }

            // Validate main role
            if (!roleData.mainRole || roleData.mainRole.trim() === '') {
                errors.mainRole = 'Please select a main role';
            }

            // Validate sub role
            if (!roleData.subRole || roleData.subRole.trim() === '') {
                errors.subRole = 'Please select a sub role';
            }

            // Validate specialization (optional but if provided, should not be empty)
            if (roleData.specialization && roleData.specialization.trim() === '') {
                errors.specialization = 'Please select a valid specialization or leave empty';
            }

            // Validate role combination compatibility
            if (roleData.mainRole && roleData.subRole) {
                var compatibilityError = validateRoleCompatibility(roleData.mainRole, roleData.subRole);
                if (compatibilityError) {
                    errors.roleCompatibility = compatibilityError;
                }
            }

            // Validate tech stack selection (should not exceed 3 items)
            if (roleData.techStack && Array.isArray(roleData.techStack)) {
                if (roleData.techStack.length > 3) {
                    errors.techStack = 'Please select no more than 3 tech stack items';
                }
            }

            var result = {
                isValid: Object.keys(errors).length === 0,
                errors: errors
            };

            $log.debug('FormErrorService: Role selection validation result', result);
            return result;
        }

        /**
         * Validate role combination compatibility
         * @param {string} mainRole - Main role selection
         * @param {string} subRole - Sub role selection
         * @returns {string|null} Error message if incompatible, null if valid
         */
        function validateRoleCompatibility(mainRole, subRole) {
            // Define incompatible role combinations
            var incompatibleCombinations = {
                'Student': ['Senior Developer', 'Team Lead', 'Engineering Manager', 'CTO'],
                'Entry Level': ['Senior Developer', 'Team Lead', 'Engineering Manager', 'CTO'],
                'Junior': ['Senior Developer', 'Team Lead', 'Engineering Manager']
            };

            if (incompatibleCombinations[mainRole] && 
                incompatibleCombinations[mainRole].includes(subRole)) {
                return 'Selected role combination is not valid. ' + mainRole + ' cannot be ' + subRole;
            }

            return null;
        }

        // ==================== Server Error Handling ====================

        /**
         * Handle server errors and convert to user-friendly messages
         * @param {Object} error - Server error object
         * @returns {string} User-friendly error message
         */
        function handleServerError(error) {
            if (!error) {
                return 'An unexpected error occurred. Please try again.';
            }

            var status = error.status || 0;
            var errorData = error.data || {};

            // Handle specific HTTP status codes
            switch (status) {
                case 400:
                    return handleBadRequestError(errorData);
                case 401:
                    return 'Invalid username or password. Please check your credentials and try again.';
                case 403:
                    return 'You don\'t have permission to perform this action. Please contact support.';
                case 404:
                    return 'The requested resource was not found. Please check the URL and try again.';
                case 409:
                    return 'This action conflicts with existing data. Please refresh and try again.';
                case 422:
                    return handleValidationError(errorData);
                case 429:
                    return 'Too many requests. Please wait a few minutes before trying again.';
                case 500:
                    return 'Server error. Please try again later or contact support if the problem persists.';
                case 502:
                case 503:
                case 504:
                    return 'Service temporarily unavailable. Please try again in a few minutes.';
                case 0:
                    return 'Network error. Please check your internet connection and try again.';
                default:
                    return 'An unexpected error occurred. Please try again or contact support.';
            }
        }

        /**
         * Handle 400 Bad Request errors
         * @param {Object} errorData - Error data from server
         * @returns {string} User-friendly error message
         */
        function handleBadRequestError(errorData) {
            if (errorData.message) {
                return errorData.message;
            }
            
            if (errorData.detail) {
                if (typeof errorData.detail === 'string') {
                    return errorData.detail;
                }
                if (errorData.detail.message) {
                    return errorData.detail.message;
                }
            }

            return 'Invalid request. Please check your input and try again.';
        }

        /**
         * Handle 422 Validation errors
         * @param {Object} errorData - Error data from server
         * @returns {string} User-friendly error message
         */
        function handleValidationError(errorData) {
            if (errorData.detail && Array.isArray(errorData.detail)) {
                // FastAPI validation error format
                var messages = errorData.detail.map(function(err) {
                    return err.msg || 'Validation error';
                });
                return 'Validation failed: ' + messages.join(', ');
            }

            if (errorData.message) {
                return errorData.message;
            }

            return 'Please check your input data and try again.';
        }

        // ==================== Generic Validation Methods ====================

        /**
         * Validate required fields in a form
         * @param {Object} formData - Form data object
         * @param {Array} requiredFields - Array of required field names
         * @returns {Object} Validation result
         */
        function validateRequiredFields(formData, requiredFields) {
            var errors = {};

            if (!formData || !requiredFields) {
                return {
                    isValid: false,
                    errors: { form: 'Invalid form data or field configuration' }
                };
            }

            requiredFields.forEach(function(fieldName) {
                var fieldValue = formData[fieldName];
                if (!fieldValue || (typeof fieldValue === 'string' && fieldValue.trim() === '')) {
                    errors[fieldName] = getFieldErrorMessage(fieldName, 'required');
                }
            });

            return {
                isValid: Object.keys(errors).length === 0,
                errors: errors
            };
        }

        /**
         * Validate email format
         * @param {string} email - Email address to validate
         * @returns {boolean} True if valid email format
         */
        function validateEmailFormat(email) {
            if (!email || typeof email !== 'string') {
                return false;
            }

            var emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return emailRegex.test(email.trim());
        }

        /**
         * Validate password strength
         * @param {string} password - Password to validate
         * @returns {Object} Validation result with strength info
         */
        function validatePasswordStrength(password) {
            var result = {
                isValid: true,
                strength: 'weak',
                errors: [],
                suggestions: []
            };

            if (!password || typeof password !== 'string') {
                result.isValid = false;
                result.errors.push('Password is required');
                return result;
            }

            var length = password.length;
            var hasLower = /[a-z]/.test(password);
            var hasUpper = /[A-Z]/.test(password);
            var hasNumber = /\d/.test(password);
            var hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password);

            // Check minimum requirements
            if (length < 8) {
                result.isValid = false;
                result.errors.push('Password must be at least 8 characters long');
            }

            // Determine strength
            var strengthScore = 0;
            if (length >= 8) strengthScore++;
            if (hasLower) strengthScore++;
            if (hasUpper) strengthScore++;
            if (hasNumber) strengthScore++;
            if (hasSpecial) strengthScore++;

            if (strengthScore >= 4) {
                result.strength = 'strong';
            } else if (strengthScore >= 3) {
                result.strength = 'medium';
            } else {
                result.strength = 'weak';
            }

            // Add suggestions for improvement
            if (!hasLower) result.suggestions.push('Add lowercase letters');
            if (!hasUpper) result.suggestions.push('Add uppercase letters');
            if (!hasNumber) result.suggestions.push('Add numbers');
            if (!hasSpecial) result.suggestions.push('Add special characters');
            if (length < 12) result.suggestions.push('Use at least 12 characters for better security');

            return result;
        }

        // ==================== Error Message Utilities ====================

        /**
         * Get specific error message for a field and error type
         * @param {string} fieldName - Name of the field
         * @param {string} errorType - Type of error (required, invalid, etc.)
         * @returns {string} Formatted error message
         */
        function getFieldErrorMessage(fieldName, errorType) {
            var fieldLabels = {
                'email': 'Email',
                'username': 'Username',
                'password': 'Password',
                'confirmPassword': 'Confirm Password',
                'mainRole': 'Main Role',
                'subRole': 'Sub Role',
                'specialization': 'Specialization',
                'techStack': 'Tech Stack',
                'firstName': 'First Name',
                'lastName': 'Last Name',
                'phone': 'Phone Number'
            };

            var errorMessages = {
                'required': '{field} is required',
                'invalid': 'Please enter a valid {field}',
                'format': 'Please enter {field} in the correct format',
                'mismatch': '{field} does not match',
                'exists': '{field} already exists',
                'length': '{field} must meet length requirements'
            };

            var fieldLabel = fieldLabels[fieldName] || fieldName;
            var messageTemplate = errorMessages[errorType] || 'Invalid {field}';

            return messageTemplate.replace('{field}', fieldLabel);
        }

        /**
         * Format validation errors for display
         * @param {Object} errors - Errors object from validation
         * @returns {Array} Array of formatted error messages
         */
        function formatValidationErrors(errors) {
            if (!errors || typeof errors !== 'object') {
                return [];
            }

            return Object.keys(errors).map(function(fieldName) {
                return {
                    field: fieldName,
                    message: errors[fieldName]
                };
            });
        }
    }
})();