"""
Authentication endpoints with comprehensive validation and security
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.schemas.user import UserCreate, UserLogin, PasswordResetRequest, PasswordReset
from app.schemas.auth import LoginResponse, RegisterResponse, RefreshToken
from app.services.auth_service import AuthenticationService
from app.core.dependencies import get_current_user, rate_limit
from app.db.models import User

router = APIRouter()
security = HTTPBearer()


@router.post("/register", response_model=RegisterResponse)
async def register(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(max_calls=5, window_seconds=300))  # 5 calls per 5 minutes
):
    """Register new user with email verification"""
    auth_service = AuthenticationService(db)
    
    try:
        return auth_service.register_user(user_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    user_credentials: UserLogin,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(max_calls=10, window_seconds=300))  # 10 calls per 5 minutes
):
    """Login user with account lockout protection"""
    auth_service = AuthenticationService(db)
    
    # Get client info
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent", "")
    
    try:
        return auth_service.login_user(
            user_credentials.email,
            user_credentials.password,
            ip_address,
            user_agent
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Logout user and invalidate session"""
    auth_service = AuthenticationService(db)
    
    # Extract session token from authorization header
    session_token = credentials.credentials
    
    try:
        success = auth_service.logout_user(session_token)
        if success:
            return {"message": "Successfully logged out"}
        else:
            return {"message": "Logout completed"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.post("/refresh")
async def refresh_token(
    refresh_data: RefreshToken,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(max_calls=20, window_seconds=300))  # 20 calls per 5 minutes
):
    """Refresh access token using refresh token"""
    auth_service = AuthenticationService(db)
    
    try:
        new_access_token, new_refresh_token = auth_service.refresh_token(
            refresh_data.refresh_token
        )
        
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/forgot-password")
async def forgot_password(
    request_data: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(max_calls=3, window_seconds=300))  # 3 calls per 5 minutes
):
    """Send password reset email"""
    auth_service = AuthenticationService(db)
    
    try:
        success = auth_service.forgot_password(request_data.email)
        # Always return success to prevent email enumeration
        return {"message": "If the email exists, a password reset link has been sent"}
    except Exception as e:
        # Log error but don't expose details
        print(f"Password reset error: {e}")
        return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password")
async def reset_password(
    reset_data: PasswordReset,
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(max_calls=5, window_seconds=300))  # 5 calls per 5 minutes
):
    """Reset password using reset token"""
    auth_service = AuthenticationService(db)
    
    try:
        success = auth_service.reset_password(reset_data.token, reset_data.new_password)
        if success:
            return {"message": "Password reset successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset failed"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )


@router.post("/verify-email/{user_id}")
async def verify_email(
    user_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(max_calls=5, window_seconds=300))  # 5 calls per 5 minutes
):
    """Verify user email address"""
    auth_service = AuthenticationService(db)
    
    try:
        success = auth_service.verify_email(user_id)
        if success:
            return {"message": "Email verified successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email verification failed"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current authenticated user information"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role,
        "target_roles": current_user.target_roles,
        "experience_level": current_user.experience_level,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at
    }


@router.post("/validate-token")
async def validate_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Validate JWT token"""
    auth_service = AuthenticationService(db)
    
    try:
        payload = auth_service.verify_token(credentials.credentials)
        if payload:
            return {"valid": True, "payload": payload}
        else:
            return {"valid": False}
    except Exception:
        return {"valid": False}