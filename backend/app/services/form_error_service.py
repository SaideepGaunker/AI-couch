"""
Form Error Service for handling form validation and error messages
Provides consistent error handling across all forms in the application
"""
from typing import Dict, Any, Optional
from fastapi import HTTPException


class FormErrorService:
    """Service for handling form validation and error messages"""
    
    # Standard error messages
    ERROR_MESSAGES = {
        'required_field': '{field_name} is required',
        'invalid_credentials': 'Invalid username or password',
        'invalid_format': 'Please enter a valid {field_type}',
        'server_error': 'Server error. Please try again later.',
        'role_mismatch': 'Selected role combination is not valid',
        'password_required': 'Password is required',
        'username_required': 'Username is required',
        'main_role_required': 'Please select a main role',
        'sub_role_required': 'Please select a sub role',
        'specialization_required': 'Please select a specialization'
    }
    
    def validate_login_form(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate login form data
        
        Args:
            form_data: Dictionary containing username and password
            
        Returns:
            Dictionary with validation results
        """
        errors = {}
        
        # Check username
        if not form_data.get('username') or str(form_data['username']).strip() == '':
            errors['username'] = self.ERROR_MESSAGES['username_required']
        
        # Check password
        if not form_data.get('password') or str(form_data['password']).strip() == '':
            errors['password'] = self.ERROR_MESSAGES['password_required']
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    def validate_role_selection(self, role_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate role selection form data
        
        Args:
            role_data: Dictionary containing role selection data
            
        Returns:
            Dictionary with validation results
        """
        errors = {}
        
        # Check main role
        if not role_data.get('main_role') or str(role_data['main_role']).strip() == '':
            errors['main_role'] = self.ERROR_MESSAGES['main_role_required']
        
        # Check sub role
        if not role_data.get('sub_role') or str(role_data['sub_role']).strip() == '':
            errors['sub_role'] = self.ERROR_MESSAGES['sub_role_required']
        
        # Check specialization
        if not role_data.get('specialization') or str(role_data['specialization']).strip() == '':
            errors['specialization'] = self.ERROR_MESSAGES['specialization_required']
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    def handle_server_error(self, error: Any) -> str:
        """
        Convert server errors to user-friendly messages
        
        Args:
            error: Error object or HTTP status code
            
        Returns:
            User-friendly error message
        """
        if hasattr(error, 'status_code'):
            status_code = error.status_code
        elif hasattr(error, 'status'):
            status_code = error.status
        elif isinstance(error, int):
            status_code = error
        else:
            status_code = 500
        
        if status_code == 401:
            return self.ERROR_MESSAGES['invalid_credentials']
        elif status_code == 400:
            if hasattr(error, 'data') and error.data and error.data.get('message'):
                return error.data['message']
            return 'Invalid input data'
        elif status_code >= 500:
            return self.ERROR_MESSAGES['server_error']
        else:
            return 'An unexpected error occurred. Please try again.'
    
    def validate_field_format(self, field_name: str, field_value: Any, field_type: str) -> Optional[str]:
        """
        Validate field format
        
        Args:
            field_name: Name of the field
            field_value: Value to validate
            field_type: Expected type (email, phone, etc.)
            
        Returns:
            Error message if validation fails, None if valid
        """
        if field_type == 'email':
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, str(field_value)):
                return f'Please enter a valid email address'
        
        return None
    
    def get_field_specific_error(self, field_name: str, error_type: str) -> str:
        """
        Get field-specific error message
        
        Args:
            field_name: Name of the field
            error_type: Type of error
            
        Returns:
            Formatted error message
        """
        if error_type == 'required':
            return self.ERROR_MESSAGES['required_field'].format(field_name=field_name.replace('_', ' ').title())
        elif error_type == 'invalid_format':
            return self.ERROR_MESSAGES['invalid_format'].format(field_type=field_name.replace('_', ' '))
        else:
            return f'Invalid {field_name.replace("_", " ")}'