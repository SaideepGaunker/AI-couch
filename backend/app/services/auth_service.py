"""
Authentication Service - Business logic for user authentication
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.crud.user import (
    get_user_by_email, create_user, authenticate_user, 
    create_password_reset_token, get_password_reset_token,
    use_password_reset_token, change_user_password,
    create_user_session, get_user_session, delete_user_session,
    verify_user_email
)
from app.db.models import User
from app.schemas.user import UserCreate
from app.schemas.auth import LoginResponse, RegisterResponse
from app.core.security import (
    create_access_token, create_refresh_token, verify_token,
    generate_password_reset_token, generate_session_token
)
from app.services.email_service import send_password_reset_email, send_verification_email


class AuthenticationService:
    """Authentication service with security features"""
    
    def __init__(self, db: Session):
        self.db = db
        self.failed_attempts = {}  # In production, use Redis or database
        self.max_attempts = 5
        self.lockout_duration = timedelta(minutes=15)
    
    def register_user(self, user_data: UserCreate) -> RegisterResponse:
        """Register new user with email verification"""
        # Check if user already exists
        existing_user = get_user_by_email(self.db, user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        try:
            # Create user
            user = create_user(self.db, user_data)
            
            # Send verification email
            try:
                send_verification_email(user.email, user.name, user.id)
            except Exception as e:
                # Log error but don't fail registration
                print(f"Failed to send verification email: {e}")
            
            return RegisterResponse(
                message="User registered successfully. Please check your email for verification.",
                user_id=user.id,
                email=user.email
            )
        except Exception as e:
            # Log the specific error for debugging
            print(f"User creation failed: {e}")
            print(f"User data: {user_data.dict()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Registration failed: {str(e)}"
            )
    
    def login_user(self, email: str, password: str, ip_address: str, user_agent: str) -> LoginResponse:
        """Login user with account lockout protection"""
        # Check if account is locked
        if self._is_account_locked(email):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account temporarily locked due to too many failed attempts"
            )
        
        # Authenticate user
        user = authenticate_user(self.db, email, password)
        if not user:
            self._record_failed_attempt(email)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        # Clear failed attempts on successful login
        self._clear_failed_attempts(email)
        
        # Create tokens
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role}
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        # Create user session
        session_token = generate_session_token()
        expires_at = datetime.utcnow() + timedelta(days=7)
        create_user_session(
            self.db, user.id, session_token, ip_address, user_agent, expires_at
        )
        
        # Update last login
        user.last_login = datetime.utcnow()
        self.db.commit()
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user={
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "is_verified": user.is_verified
            }
        )
    
    def logout_user(self, session_token: str) -> bool:
        """Logout user and invalidate session"""
        return delete_user_session(self.db, session_token)
    
    def refresh_token(self, refresh_token: str) -> Tuple[str, str]:
        """Refresh access token using refresh token"""
        payload = verify_token(refresh_token, "refresh")
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("sub")
        email = payload.get("email")
        
        # Get user to check if still active
        user = get_user_by_email(self.db, email)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new tokens
        new_access_token = create_access_token(
            data={"sub": user_id, "email": email, "role": user.role}
        )
        new_refresh_token = create_refresh_token(
            data={"sub": user_id, "email": email}
        )
        
        return new_access_token, new_refresh_token
    
    def forgot_password(self, email: str) -> bool:
        """Send password reset email"""
        user = get_user_by_email(self.db, email)
        if not user:
            # Don't reveal if email exists
            return True
        
        # Generate reset token
        reset_token = generate_password_reset_token()
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Store reset token
        create_password_reset_token(self.db, user.id, reset_token, expires_at)
        
        # Send reset email
        try:
            send_password_reset_email(user.email, user.name, reset_token)
            return True
        except Exception as e:
            print(f"Failed to send password reset email: {e}")
            return False
    
    def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password using reset token"""
        reset_token = get_password_reset_token(self.db, token)
        if not reset_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Check if token is expired
        if reset_token.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired"
            )
        
        # Change password
        success = change_user_password(self.db, reset_token.user_id, new_password)
        if success:
            # Mark token as used
            use_password_reset_token(self.db, token)
            return True
        
        return False
    
    def verify_token(self, token: str) -> Optional[dict]:
        """Verify JWT token and return payload"""
        return verify_token(token, "access")
    
    def verify_email(self, user_id: int) -> bool:
        """Verify user email"""
        return verify_user_email(self.db, user_id)
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """Change user password with old password verification"""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # Verify old password
        if not authenticate_user(self.db, user.email, old_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        return change_user_password(self.db, user_id, new_password)
    
    def _is_account_locked(self, email: str) -> bool:
        """Check if account is locked due to failed attempts"""
        if email not in self.failed_attempts:
            return False
        
        attempts_data = self.failed_attempts[email]
        if attempts_data["count"] >= self.max_attempts:
            if datetime.utcnow() < attempts_data["locked_until"]:
                return True
            else:
                # Lock period expired, clear attempts
                self._clear_failed_attempts(email)
        
        return False
    
    def _record_failed_attempt(self, email: str):
        """Record failed login attempt"""
        if email not in self.failed_attempts:
            self.failed_attempts[email] = {"count": 0, "locked_until": None}
        
        self.failed_attempts[email]["count"] += 1
        
        if self.failed_attempts[email]["count"] >= self.max_attempts:
            self.failed_attempts[email]["locked_until"] = datetime.utcnow() + self.lockout_duration
    
    def _clear_failed_attempts(self, email: str):
        """Clear failed login attempts"""
        if email in self.failed_attempts:
            del self.failed_attempts[email]