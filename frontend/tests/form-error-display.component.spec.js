/**
 * Unit tests for FormErrorDisplay Component - Form error display functionality
 * Tests Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
 */

describe('FormErrorDisplay Component', function() {
    'use strict';

    var $componentController, $log, controller, bindings;

    // Load the module
    beforeEach(module('interviewPrepApp'));

    // Inject dependencies
    beforeEach(inject(function(_$componentController_, _$log_) {
        $componentController = _$componentController_;
        $log = _$log_;
    }));

    beforeEach(function() {
        bindings = {
            errors: {},
            fieldName: 'testField',
            showIcon: true,
            cssClass: 'custom-error'
        };
        controller = $componentController('formErrorDisplay', null, bindings);
    });

    describe('Component Initialization', function() {
        it('should initialize with default values', function() {
            expect(controller).toBeDefined();
            expect(controller.errors).toEqual({});
            expect(controller.fieldName).toBe('testField');
            expect(controller.showIcon).toBe(true);
            expect(controller.cssClass).toBe('custom-error');
        });

        it('should handle undefined bindings gracefully', function() {
            var emptyController = $componentController('formErrorDisplay', null, {});
            expect(emptyController.errors).toBeUndefined();
            expect(emptyController.fieldName).toBeUndefined();
            expect(emptyController.showIcon).toBeUndefined();
        });
    });

    describe('Error Display Logic', function() {
        it('should show error when field has error', function() {
            controller.errors = { testField: 'This field is required' };
            controller.fieldName = 'testField';
            controller.$onChanges();

            expect(controller.hasError()).toBe(true);
            expect(controller.getErrorMessage()).toBe('This field is required');
        });

        it('should not show error when field has no error', function() {
            controller.errors = { otherField: 'Other error' };
            controller.fieldName = 'testField';
            controller.$onChanges();

            expect(controller.hasError()).toBe(false);
            expect(controller.getErrorMessage()).toBe('');
        });

        it('should handle empty errors object', function() {
            controller.errors = {};
            controller.fieldName = 'testField';
            controller.$onChanges();

            expect(controller.hasError()).toBe(false);
            expect(controller.getErrorMessage()).toBe('');
        });

        it('should handle null errors', function() {
            controller.errors = null;
            controller.fieldName = 'testField';
            controller.$onChanges();

            expect(controller.hasError()).toBe(false);
            expect(controller.getErrorMessage()).toBe('');
        });

        it('should handle undefined errors', function() {
            controller.errors = undefined;
            controller.fieldName = 'testField';
            controller.$onChanges();

            expect(controller.hasError()).toBe(false);
            expect(controller.getErrorMessage()).toBe('');
        });
    });

    describe('Multiple Error Messages', function() {
        it('should display first error when multiple errors exist for field', function() {
            controller.errors = { 
                testField: ['First error', 'Second error', 'Third error']
            };
            controller.fieldName = 'testField';
            controller.$onChanges();

            expect(controller.hasError()).toBe(true);
            expect(controller.getErrorMessage()).toBe('First error');
        });

        it('should handle array of error objects', function() {
            controller.errors = { 
                testField: [
                    { message: 'First error' },
                    { message: 'Second error' }
                ]
            };
            controller.fieldName = 'testField';
            controller.$onChanges();

            expect(controller.hasError()).toBe(true);
            expect(controller.getErrorMessage()).toBe('First error');
        });

        it('should display all errors when showAllErrors is true', function() {
            controller.errors = { 
                testField: ['First error', 'Second error']
            };
            controller.fieldName = 'testField';
            controller.showAllErrors = true;
            controller.$onChanges();

            expect(controller.hasError()).toBe(true);
            expect(controller.getAllErrorMessages()).toEqual(['First error', 'Second error']);
        });
    });

    describe('CSS Classes and Styling', function() {
        it('should apply default error CSS class', function() {
            controller.errors = { testField: 'Error message' };
            controller.fieldName = 'testField';
            controller.$onChanges();

            expect(controller.getErrorCssClass()).toContain('error-message');
        });

        it('should apply custom CSS class when provided', function() {
            controller.errors = { testField: 'Error message' };
            controller.fieldName = 'testField';
            controller.cssClass = 'custom-error-style';
            controller.$onChanges();

            expect(controller.getErrorCssClass()).toContain('custom-error-style');
        });

        it('should combine default and custom CSS classes', function() {
            controller.errors = { testField: 'Error message' };
            controller.fieldName = 'testField';
            controller.cssClass = 'custom-error-style';
            controller.$onChanges();

            var cssClass = controller.getErrorCssClass();
            expect(cssClass).toContain('error-message');
            expect(cssClass).toContain('custom-error-style');
        });

        it('should apply severity-based CSS classes', function() {
            controller.errors = { testField: 'Error message' };
            controller.fieldName = 'testField';
            controller.severity = 'warning';
            controller.$onChanges();

            expect(controller.getErrorCssClass()).toContain('error-warning');
        });
    });

    describe('Icon Display', function() {
        it('should show icon when showIcon is true and there is an error', function() {
            controller.errors = { testField: 'Error message' };
            controller.fieldName = 'testField';
            controller.showIcon = true;
            controller.$onChanges();

            expect(controller.shouldShowIcon()).toBe(true);
        });

        it('should not show icon when showIcon is false', function() {
            controller.errors = { testField: 'Error message' };
            controller.fieldName = 'testField';
            controller.showIcon = false;
            controller.$onChanges();

            expect(controller.shouldShowIcon()).toBe(false);
        });

        it('should not show icon when there is no error', function() {
            controller.errors = {};
            controller.fieldName = 'testField';
            controller.showIcon = true;
            controller.$onChanges();

            expect(controller.shouldShowIcon()).toBe(false);
        });

        it('should use custom icon class when provided', function() {
            controller.errors = { testField: 'Error message' };
            controller.fieldName = 'testField';
            controller.showIcon = true;
            controller.iconClass = 'fa-custom-error';
            controller.$onChanges();

            expect(controller.getIconClass()).toContain('fa-custom-error');
        });

        it('should use default icon class when not provided', function() {
            controller.errors = { testField: 'Error message' };
            controller.fieldName = 'testField';
            controller.showIcon = true;
            controller.$onChanges();

            expect(controller.getIconClass()).toContain('fa-exclamation-circle');
        });
    });

    describe('Accessibility Features', function() {
        it('should provide proper ARIA attributes', function() {
            controller.errors = { testField: 'Error message' };
            controller.fieldName = 'testField';
            controller.$onChanges();

            expect(controller.getAriaAttributes()).toEqual({
                'aria-live': 'polite',
                'role': 'alert',
                'aria-describedby': 'testField-error'
            });
        });

        it('should generate unique error ID for field', function() {
            controller.fieldName = 'testField';
            controller.$onChanges();

            expect(controller.getErrorId()).toBe('testField-error');
        });

        it('should handle special characters in field names for IDs', function() {
            controller.fieldName = 'user.email';
            controller.$onChanges();

            expect(controller.getErrorId()).toBe('user-email-error');
        });
    });

    describe('Component Lifecycle', function() {
        it('should update display when errors change', function() {
            // Initial state - no errors
            controller.errors = {};
            controller.fieldName = 'testField';
            controller.$onChanges();
            expect(controller.hasError()).toBe(false);

            // Add error
            controller.errors = { testField: 'New error' };
            controller.$onChanges();
            expect(controller.hasError()).toBe(true);
            expect(controller.getErrorMessage()).toBe('New error');

            // Remove error
            controller.errors = {};
            controller.$onChanges();
            expect(controller.hasError()).toBe(false);
        });

        it('should update display when fieldName changes', function() {
            controller.errors = { 
                field1: 'Error for field 1',
                field2: 'Error for field 2'
            };
            
            // Initially showing field1 error
            controller.fieldName = 'field1';
            controller.$onChanges();
            expect(controller.getErrorMessage()).toBe('Error for field 1');

            // Switch to field2
            controller.fieldName = 'field2';
            controller.$onChanges();
            expect(controller.getErrorMessage()).toBe('Error for field 2');
        });

        it('should log debug information when errors change', function() {
            spyOn($log, 'debug');
            
            controller.errors = { testField: 'Test error' };
            controller.fieldName = 'testField';
            controller.$onChanges();

            expect($log.debug).toHaveBeenCalled();
        });
    });

    describe('Error Message Formatting', function() {
        it('should format error messages with field context', function() {
            controller.errors = { testField: 'is required' };
            controller.fieldName = 'testField';
            controller.formatWithContext = true;
            controller.$onChanges();

            expect(controller.getFormattedErrorMessage()).toBe('Test Field is required');
        });

        it('should handle camelCase field names in formatting', function() {
            controller.errors = { firstName: 'is required' };
            controller.fieldName = 'firstName';
            controller.formatWithContext = true;
            controller.$onChanges();

            expect(controller.getFormattedErrorMessage()).toBe('First Name is required');
        });

        it('should truncate long error messages when specified', function() {
            var longMessage = 'This is a very long error message that should be truncated when the maxLength is set to a smaller value';
            controller.errors = { testField: longMessage };
            controller.fieldName = 'testField';
            controller.maxLength = 50;
            controller.$onChanges();

            var truncated = controller.getTruncatedErrorMessage();
            expect(truncated.length).toBeLessThanOrEqual(53); // 50 + '...'
            expect(truncated).toContain('...');
        });
    });

    describe('Integration with Forms', function() {
        it('should work with login form validation errors', function() {
            var loginErrors = {
                email: 'Email is required',
                password: 'Password is required'
            };

            // Test email field error display
            controller.errors = loginErrors;
            controller.fieldName = 'email';
            controller.$onChanges();
            expect(controller.hasError()).toBe(true);
            expect(controller.getErrorMessage()).toBe('Email is required');

            // Test password field error display
            controller.fieldName = 'password';
            controller.$onChanges();
            expect(controller.hasError()).toBe(true);
            expect(controller.getErrorMessage()).toBe('Password is required');
        });

        it('should work with role selection validation errors', function() {
            var roleErrors = {
                mainRole: 'Please select a main role',
                subRole: 'Please select a sub role',
                roleCompatibility: 'Selected role combination is not valid: Student cannot be Senior Developer'
            };

            // Test role compatibility error display
            controller.errors = roleErrors;
            controller.fieldName = 'roleCompatibility';
            controller.$onChanges();
            expect(controller.hasError()).toBe(true);
            expect(controller.getErrorMessage()).toContain('Student cannot be Senior Developer');
        });

        it('should work with server error messages', function() {
            var serverErrors = {
                server: 'Invalid username or password. Please check your credentials and try again.'
            };

            controller.errors = serverErrors;
            controller.fieldName = 'server';
            controller.$onChanges();
            expect(controller.hasError()).toBe(true);
            expect(controller.getErrorMessage()).toBe('Invalid username or password. Please check your credentials and try again.');
        });
    });

    describe('Error State Management', function() {
        it('should clear error state when errors are removed', function() {
            // Set error
            controller.errors = { testField: 'Error message' };
            controller.fieldName = 'testField';
            controller.$onChanges();
            expect(controller.hasError()).toBe(true);

            // Clear errors
            controller.errors = {};
            controller.$onChanges();
            expect(controller.hasError()).toBe(false);
            expect(controller.getErrorMessage()).toBe('');
        });

        it('should handle rapid error state changes', function() {
            controller.fieldName = 'testField';

            // Rapid changes
            controller.errors = { testField: 'Error 1' };
            controller.$onChanges();
            expect(controller.getErrorMessage()).toBe('Error 1');

            controller.errors = { testField: 'Error 2' };
            controller.$onChanges();
            expect(controller.getErrorMessage()).toBe('Error 2');

            controller.errors = {};
            controller.$onChanges();
            expect(controller.hasError()).toBe(false);
        });
    });
});