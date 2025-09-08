/**
 * Unit tests for FormErrorService - Form validation and error handling
 * Tests Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
 */

describe('FormErrorService', function() {
    'use strict';

    var FormErrorService;

    // Load the module
    beforeEach(module('interviewPrepApp'));

    // Inject the service
    beforeEach(inject(function(_FormErrorService_) {
        FormErrorService = _FormErrorService_;
    }));

    describe('validateLoginForm', function() {
        it('should validate valid login form data', function() {
            var validFormData = {
                email: 'test@example.com',
                password: 'validpassword'
            };

            var result = FormErrorService.validateLoginForm(validFormData);

            expect(result.isValid).toBe(true);
            expect(Object.keys(result.errors).length).toBe(0);
        });

        it('should return error for empty email/username', function() {
            var invalidFormData = {
                email: '',
                password: 'validpassword'
            };

            var result = FormErrorService.validateLoginForm(invalidFormData);

            expect(result.isValid).toBe(false);
            expect(result.errors.email).toBe('Email is required');
            expect(result.errors.username).toBe('Username is required');
        });

        it('should return error for missing email/username', function() {
            var invalidFormData = {
                password: 'validpassword'
            };

            var result = FormErrorService.validateLoginForm(invalidFormData);

            expect(result.isValid).toBe(false);
            expect(result.errors.email).toBe('Email is required');
            expect(result.errors.username).toBe('Username is required');
        });

        it('should return error for empty password', function() {
            var invalidFormData = {
                email: 'test@example.com',
                password: ''
            };

            var result = FormErrorService.validateLoginForm(invalidFormData);

            expect(result.isValid).toBe(false);
            expect(result.errors.password).toBe('Password is required');
        });

        it('should return error for missing password', function() {
            var invalidFormData = {
                email: 'test@example.com'
            };

            var result = FormErrorService.validateLoginForm(invalidFormData);

            expect(result.isValid).toBe(false);
            expect(result.errors.password).toBe('Password is required');
        });

        it('should validate email format when email field is used', function() {
            var invalidFormData = {
                email: 'invalid-email',
                password: 'validpassword'
            };

            var result = FormErrorService.validateLoginForm(invalidFormData);

            expect(result.isValid).toBe(false);
            expect(result.errors.email).toBe('Please enter a valid email address');
        });

        it('should handle null or undefined form data', function() {
            var result1 = FormErrorService.validateLoginForm(null);
            var result2 = FormErrorService.validateLoginForm(undefined);

            expect(result1.isValid).toBe(false);
            expect(result1.errors.form).toBe('Form data is required');

            expect(result2.isValid).toBe(false);
            expect(result2.errors.form).toBe('Form data is required');
        });

        it('should handle whitespace-only values', function() {
            var invalidFormData = {
                email: '   ',
                password: '   '
            };

            var result = FormErrorService.validateLoginForm(invalidFormData);

            expect(result.isValid).toBe(false);
            expect(result.errors.email).toBe('Email is required');
            expect(result.errors.username).toBe('Username is required');
            expect(result.errors.password).toBe('Password is required');
        });

        it('should work with username field instead of email', function() {
            var validFormData = {
                username: 'testuser',
                password: 'validpassword'
            };

            var result = FormErrorService.validateLoginForm(validFormData);

            expect(result.isValid).toBe(true);
            expect(Object.keys(result.errors).length).toBe(0);
        });
    });

    describe('validateRoleSelection', function() {
        it('should validate valid role selection data', function() {
            var validRoleData = {
                mainRole: 'Software Engineer',
                subRole: 'Backend Developer',
                specialization: 'Python Developer',
                techStack: ['Python', 'Django']
            };

            var result = FormErrorService.validateRoleSelection(validRoleData);

            expect(result.isValid).toBe(true);
            expect(Object.keys(result.errors).length).toBe(0);
        });

        it('should return error for missing main role', function() {
            var invalidRoleData = {
                subRole: 'Backend Developer',
                specialization: 'Python Developer'
            };

            var result = FormErrorService.validateRoleSelection(invalidRoleData);

            expect(result.isValid).toBe(false);
            expect(result.errors.mainRole).toBe('Please select a main role');
        });

        it('should return error for empty main role', function() {
            var invalidRoleData = {
                mainRole: '',
                subRole: 'Backend Developer',
                specialization: 'Python Developer'
            };

            var result = FormErrorService.validateRoleSelection(invalidRoleData);

            expect(result.isValid).toBe(false);
            expect(result.errors.mainRole).toBe('Please select a main role');
        });

        it('should return error for missing sub role', function() {
            var invalidRoleData = {
                mainRole: 'Software Engineer',
                specialization: 'Python Developer'
            };

            var result = FormErrorService.validateRoleSelection(invalidRoleData);

            expect(result.isValid).toBe(false);
            expect(result.errors.subRole).toBe('Please select a sub role');
        });

        it('should return error for empty sub role', function() {
            var invalidRoleData = {
                mainRole: 'Software Engineer',
                subRole: '',
                specialization: 'Python Developer'
            };

            var result = FormErrorService.validateRoleSelection(invalidRoleData);

            expect(result.isValid).toBe(false);
            expect(result.errors.subRole).toBe('Please select a sub role');
        });

        it('should handle empty specialization gracefully', function() {
            var validRoleData = {
                mainRole: 'Software Engineer',
                subRole: 'Backend Developer'
                // specialization is optional
            };

            var result = FormErrorService.validateRoleSelection(validRoleData);

            expect(result.isValid).toBe(true);
            expect(Object.keys(result.errors).length).toBe(0);
        });

        it('should return error for empty string specialization', function() {
            var invalidRoleData = {
                mainRole: 'Software Engineer',
                subRole: 'Backend Developer',
                specialization: ''
            };

            var result = FormErrorService.validateRoleSelection(invalidRoleData);

            expect(result.isValid).toBe(false);
            expect(result.errors.specialization).toBe('Please select a valid specialization or leave empty');
        });

        it('should validate role compatibility - Student cannot be Senior Developer', function() {
            var invalidRoleData = {
                mainRole: 'Student',
                subRole: 'Senior Developer',
                specialization: 'Python Developer'
            };

            var result = FormErrorService.validateRoleSelection(invalidRoleData);

            expect(result.isValid).toBe(false);
            expect(result.errors.roleCompatibility).toContain('Selected role combination is not valid');
            expect(result.errors.roleCompatibility).toContain('Student cannot be Senior Developer');
        });

        it('should validate role compatibility - Entry Level cannot be Team Lead', function() {
            var invalidRoleData = {
                mainRole: 'Entry Level',
                subRole: 'Team Lead'
            };

            var result = FormErrorService.validateRoleSelection(invalidRoleData);

            expect(result.isValid).toBe(false);
            expect(result.errors.roleCompatibility).toContain('Entry Level cannot be Team Lead');
        });

        it('should validate tech stack limit - maximum 3 items', function() {
            var invalidRoleData = {
                mainRole: 'Software Engineer',
                subRole: 'Backend Developer',
                techStack: ['Python', 'Django', 'PostgreSQL', 'Redis', 'Docker']
            };

            var result = FormErrorService.validateRoleSelection(invalidRoleData);

            expect(result.isValid).toBe(false);
            expect(result.errors.techStack).toBe('Please select no more than 3 tech stack items');
        });

        it('should handle null or undefined role data', function() {
            var result1 = FormErrorService.validateRoleSelection(null);
            var result2 = FormErrorService.validateRoleSelection(undefined);

            expect(result1.isValid).toBe(false);
            expect(result1.errors.form).toBe('Role selection data is required');

            expect(result2.isValid).toBe(false);
            expect(result2.errors.form).toBe('Role selection data is required');
        });

        it('should handle whitespace-only role values', function() {
            var invalidRoleData = {
                mainRole: '   ',
                subRole: '   ',
                specialization: '   '
            };

            var result = FormErrorService.validateRoleSelection(invalidRoleData);

            expect(result.isValid).toBe(false);
            expect(result.errors.mainRole).toBe('Please select a main role');
            expect(result.errors.subRole).toBe('Please select a sub role');
            expect(result.errors.specialization).toBe('Please select a valid specialization or leave empty');
        });
    });

    describe('handleServerError', function() {
        it('should handle 401 Unauthorized errors', function() {
            var error = {
                status: 401,
                data: {}
            };

            var result = FormErrorService.handleServerError(error);

            expect(result).toBe('Invalid username or password. Please check your credentials and try again.');
        });

        it('should handle 400 Bad Request errors with message', function() {
            var error = {
                status: 400,
                data: {
                    message: 'Invalid input data provided'
                }
            };

            var result = FormErrorService.handleServerError(error);

            expect(result).toBe('Invalid input data provided');
        });

        it('should handle 400 Bad Request errors with detail', function() {
            var error = {
                status: 400,
                data: {
                    detail: 'Missing required field: email'
                }
            };

            var result = FormErrorService.handleServerError(error);

            expect(result).toBe('Missing required field: email');
        });

        it('should handle 403 Forbidden errors', function() {
            var error = {
                status: 403,
                data: {}
            };

            var result = FormErrorService.handleServerError(error);

            expect(result).toBe('You don\'t have permission to perform this action. Please contact support.');
        });

        it('should handle 404 Not Found errors', function() {
            var error = {
                status: 404,
                data: {}
            };

            var result = FormErrorService.handleServerError(error);

            expect(result).toBe('The requested resource was not found. Please check the URL and try again.');
        });

        it('should handle 422 Validation errors with FastAPI format', function() {
            var error = {
                status: 422,
                data: {
                    detail: [
                        { msg: 'Field is required' },
                        { msg: 'Invalid email format' }
                    ]
                }
            };

            var result = FormErrorService.handleServerError(error);

            expect(result).toBe('Validation failed: Field is required, Invalid email format');
        });

        it('should handle 500 Internal Server errors', function() {
            var error = {
                status: 500,
                data: {}
            };

            var result = FormErrorService.handleServerError(error);

            expect(result).toBe('Server error. Please try again later or contact support if the problem persists.');
        });

        it('should handle 503 Service Unavailable errors', function() {
            var error = {
                status: 503,
                data: {}
            };

            var result = FormErrorService.handleServerError(error);

            expect(result).toBe('Service temporarily unavailable. Please try again in a few minutes.');
        });

        it('should handle network errors (status 0)', function() {
            var error = {
                status: 0,
                data: {}
            };

            var result = FormErrorService.handleServerError(error);

            expect(result).toBe('Network error. Please check your internet connection and try again.');
        });

        it('should handle unknown status codes', function() {
            var error = {
                status: 999,
                data: {}
            };

            var result = FormErrorService.handleServerError(error);

            expect(result).toBe('An unexpected error occurred. Please try again or contact support.');
        });

        it('should handle null or undefined errors', function() {
            var result1 = FormErrorService.handleServerError(null);
            var result2 = FormErrorService.handleServerError(undefined);

            expect(result1).toBe('An unexpected error occurred. Please try again.');
            expect(result2).toBe('An unexpected error occurred. Please try again.');
        });

        it('should handle errors without status', function() {
            var error = {
                data: { message: 'Some error' }
            };

            var result = FormErrorService.handleServerError(error);

            expect(result).toBe('An unexpected error occurred. Please try again or contact support.');
        });

        it('should handle 429 Too Many Requests errors', function() {
            var error = {
                status: 429,
                data: {}
            };

            var result = FormErrorService.handleServerError(error);

            expect(result).toBe('Too many requests. Please wait a few minutes before trying again.');
        });
    });

    describe('validateRequiredFields', function() {
        it('should validate all required fields are present', function() {
            var formData = {
                firstName: 'John',
                lastName: 'Doe',
                email: 'john@example.com'
            };
            var requiredFields = ['firstName', 'lastName', 'email'];

            var result = FormErrorService.validateRequiredFields(formData, requiredFields);

            expect(result.isValid).toBe(true);
            expect(Object.keys(result.errors).length).toBe(0);
        });

        it('should return errors for missing required fields', function() {
            var formData = {
                firstName: 'John'
                // lastName and email missing
            };
            var requiredFields = ['firstName', 'lastName', 'email'];

            var result = FormErrorService.validateRequiredFields(formData, requiredFields);

            expect(result.isValid).toBe(false);
            expect(result.errors.lastName).toBe('Last Name is required');
            expect(result.errors.email).toBe('Email is required');
        });

        it('should return errors for empty string fields', function() {
            var formData = {
                firstName: 'John',
                lastName: '',
                email: '   '
            };
            var requiredFields = ['firstName', 'lastName', 'email'];

            var result = FormErrorService.validateRequiredFields(formData, requiredFields);

            expect(result.isValid).toBe(false);
            expect(result.errors.lastName).toBe('Last Name is required');
            expect(result.errors.email).toBe('Email is required');
        });

        it('should handle invalid inputs gracefully', function() {
            var result1 = FormErrorService.validateRequiredFields(null, ['field1']);
            var result2 = FormErrorService.validateRequiredFields({}, null);

            expect(result1.isValid).toBe(false);
            expect(result1.errors.form).toBe('Invalid form data or field configuration');

            expect(result2.isValid).toBe(false);
            expect(result2.errors.form).toBe('Invalid form data or field configuration');
        });
    });

    describe('validateEmailFormat', function() {
        it('should validate correct email formats', function() {
            var validEmails = [
                'test@example.com',
                'user.name@domain.co.uk',
                'user+tag@example.org',
                'user123@test-domain.com'
            ];

            validEmails.forEach(function(email) {
                expect(FormErrorService.validateEmailFormat(email)).toBe(true);
            });
        });

        it('should reject invalid email formats', function() {
            var invalidEmails = [
                'invalid-email',
                '@example.com',
                'user@',
                'user@domain',
                'user.domain.com',
                '',
                null,
                undefined,
                123
            ];

            invalidEmails.forEach(function(email) {
                expect(FormErrorService.validateEmailFormat(email)).toBe(false);
            });
        });

        it('should handle whitespace correctly', function() {
            expect(FormErrorService.validateEmailFormat('  test@example.com  ')).toBe(true);
            expect(FormErrorService.validateEmailFormat('   ')).toBe(false);
        });
    });

    describe('validatePasswordStrength', function() {
        it('should validate strong passwords', function() {
            var strongPasswords = [
                'StrongPass123!',
                'MySecure@Password2024',
                'Complex#Pass1'
            ];

            strongPasswords.forEach(function(password) {
                var result = FormErrorService.validatePasswordStrength(password);
                expect(result.isValid).toBe(true);
                expect(result.strength).toBe('strong');
            });
        });

        it('should identify medium strength passwords', function() {
            var mediumPasswords = [
                'GoodPass123',  // Missing special char
                'goodpass123!', // Missing uppercase
                'GOODPASS123!'  // Missing lowercase
            ];

            mediumPasswords.forEach(function(password) {
                var result = FormErrorService.validatePasswordStrength(password);
                expect(result.isValid).toBe(true);
                expect(result.strength).toBe('medium');
            });
        });

        it('should identify weak passwords', function() {
            var weakPasswords = [
                'password',
                '12345678',
                'weakpass'
            ];

            weakPasswords.forEach(function(password) {
                var result = FormErrorService.validatePasswordStrength(password);
                expect(result.isValid).toBe(true);
                expect(result.strength).toBe('weak');
            });
        });

        it('should reject passwords that are too short', function() {
            var shortPasswords = [
                'short',
                '123',
                'Ab1!'
            ];

            shortPasswords.forEach(function(password) {
                var result = FormErrorService.validatePasswordStrength(password);
                expect(result.isValid).toBe(false);
                expect(result.errors).toContain('Password must be at least 8 characters long');
            });
        });

        it('should provide helpful suggestions', function() {
            var result = FormErrorService.validatePasswordStrength('password123');

            expect(result.suggestions).toContain('Add uppercase letters');
            expect(result.suggestions).toContain('Add special characters');
        });

        it('should handle invalid inputs', function() {
            var result1 = FormErrorService.validatePasswordStrength(null);
            var result2 = FormErrorService.validatePasswordStrength(undefined);
            var result3 = FormErrorService.validatePasswordStrength(123);

            expect(result1.isValid).toBe(false);
            expect(result1.errors).toContain('Password is required');

            expect(result2.isValid).toBe(false);
            expect(result2.errors).toContain('Password is required');

            expect(result3.isValid).toBe(false);
            expect(result3.errors).toContain('Password is required');
        });
    });

    describe('getFieldErrorMessage', function() {
        it('should return formatted error messages for known fields', function() {
            expect(FormErrorService.getFieldErrorMessage('email', 'required')).toBe('Email is required');
            expect(FormErrorService.getFieldErrorMessage('password', 'invalid')).toBe('Please enter a valid Password');
            expect(FormErrorService.getFieldErrorMessage('mainRole', 'required')).toBe('Main Role is required');
        });

        it('should handle unknown fields gracefully', function() {
            expect(FormErrorService.getFieldErrorMessage('unknownField', 'required')).toBe('unknownField is required');
        });

        it('should handle unknown error types gracefully', function() {
            expect(FormErrorService.getFieldErrorMessage('email', 'unknownError')).toBe('Invalid Email');
        });
    });

    describe('formatValidationErrors', function() {
        it('should format errors object into array', function() {
            var errors = {
                email: 'Email is required',
                password: 'Password is too weak'
            };

            var result = FormErrorService.formatValidationErrors(errors);

            expect(result.length).toBe(2);
            expect(result[0].field).toBe('email');
            expect(result[0].message).toBe('Email is required');
            expect(result[1].field).toBe('password');
            expect(result[1].message).toBe('Password is too weak');
        });

        it('should handle empty errors object', function() {
            var result = FormErrorService.formatValidationErrors({});
            expect(result.length).toBe(0);
        });

        it('should handle invalid inputs gracefully', function() {
            expect(FormErrorService.formatValidationErrors(null)).toEqual([]);
            expect(FormErrorService.formatValidationErrors(undefined)).toEqual([]);
            expect(FormErrorService.formatValidationErrors('invalid')).toEqual([]);
        });
    });

    describe('Integration Tests', function() {
        it('should handle complete login form validation flow', function() {
            // Test invalid form
            var invalidForm = {
                email: 'invalid-email',
                password: ''
            };

            var validation = FormErrorService.validateLoginForm(invalidForm);
            expect(validation.isValid).toBe(false);
            expect(validation.errors.email).toBe('Please enter a valid email address');
            expect(validation.errors.password).toBe('Password is required');

            // Test valid form
            var validForm = {
                email: 'test@example.com',
                password: 'validpassword'
            };

            validation = FormErrorService.validateLoginForm(validForm);
            expect(validation.isValid).toBe(true);
            expect(Object.keys(validation.errors).length).toBe(0);
        });

        it('should handle complete role selection validation flow', function() {
            // Test invalid role selection
            var invalidRoles = {
                mainRole: 'Student',
                subRole: 'Senior Developer',
                techStack: ['Python', 'Django', 'React', 'Node.js', 'MongoDB']
            };

            var validation = FormErrorService.validateRoleSelection(invalidRoles);
            expect(validation.isValid).toBe(false);
            expect(validation.errors.roleCompatibility).toContain('Student cannot be Senior Developer');
            expect(validation.errors.techStack).toBe('Please select no more than 3 tech stack items');

            // Test valid role selection
            var validRoles = {
                mainRole: 'Software Engineer',
                subRole: 'Backend Developer',
                specialization: 'Python Developer',
                techStack: ['Python', 'Django']
            };

            validation = FormErrorService.validateRoleSelection(validRoles);
            expect(validation.isValid).toBe(true);
            expect(Object.keys(validation.errors).length).toBe(0);
        });

        it('should provide consistent error handling across all methods', function() {
            // Test that all validation methods handle null/undefined consistently
            var loginResult = FormErrorService.validateLoginForm(null);
            var roleResult = FormErrorService.validateRoleSelection(null);
            var requiredResult = FormErrorService.validateRequiredFields(null, ['field']);
            var serverResult = FormErrorService.handleServerError(null);

            expect(loginResult.isValid).toBe(false);
            expect(roleResult.isValid).toBe(false);
            expect(requiredResult.isValid).toBe(false);
            expect(typeof serverResult).toBe('string');
        });
    });
});