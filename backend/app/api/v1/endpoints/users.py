"""
User management endpoints with role-based access control
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.schemas.user import UserResponse, UserUpdate, UserPasswordChange
from app.core.dependencies import (
    get_current_user, get_current_verified_user, 
    require_admin, rate_limit
)
from app.services.user_service import UserService
from app.db.models import User

router = APIRouter()


@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile"""
    return current_user


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    profile_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(max_calls=10, window_seconds=300))
):
    """Update current user profile"""
    user_service = UserService(db)
    
    try:
        updated_user = user_service.update_user_profile(current_user.id, profile_update)
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return updated_user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )


@router.post("/change-password")
async def change_password(
    password_data: UserPasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(max_calls=5, window_seconds=300))
):
    """Change user password"""
    user_service = UserService(db)
    
    try:
        success = user_service.change_password(
            current_user.id,
            password_data.old_password,
            password_data.new_password
        )
        if success:
            return {"message": "Password changed successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password change failed"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.delete("/profile")
async def delete_profile(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(max_calls=3, window_seconds=300))
):
    """Delete user profile (GDPR compliance)"""
    user_service = UserService(db)
    
    try:
        success = user_service.delete_user_data(current_user.id)
        if success:
            return {"message": "User profile deleted successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profile deletion failed"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile deletion failed"
        )


@router.get("/export-data")
async def export_user_data(
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit(max_calls=3, window_seconds=3600))  # 3 per hour
):
    """Export user data (GDPR compliance)"""
    user_service = UserService(db)
    
    try:
        user_data = user_service.export_user_data(current_user.id)
        return {
            "message": "User data exported successfully",
            "data": user_data
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Data export failed"
        )


@router.get("/settings")
async def get_user_settings(
    current_user: User = Depends(get_current_user)
):
    """Get user settings and preferences"""
    return {
        "target_roles": current_user.target_roles,
        "experience_level": current_user.experience_level,
        "email_notifications": True,  # Default setting
        "privacy_settings": {
            "profile_visibility": "private",
            "data_sharing": False
        }
    }


@router.put("/settings")
async def update_user_settings(
    settings_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user settings and preferences"""
    user_service = UserService(db)
    
    try:
        success = user_service.update_user_settings(current_user.id, settings_data)
        if success:
            return {"message": "Settings updated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Settings update failed"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Settings update failed"
        )


# Admin endpoints for user management
@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    role: Optional[str] = Query(None),
    institution_id: Optional[int] = Query(None),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get list of users (admin only)"""
    user_service = UserService(db)
    
    try:
        users = user_service.get_users_list(
            skip=skip,
            limit=limit,
            role=role,
            institution_id=institution_id
        )
        return users
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get user by ID (admin only)"""
    user_service = UserService(db)
    
    try:
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user"
        )


@router.put("/{user_id}/activate")
async def activate_user(
    user_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Activate user account (admin only)"""
    user_service = UserService(db)
    
    try:
        success = user_service.activate_user(user_id)
        if success:
            return {"message": "User activated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User activation failed"
        )


@router.put("/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Deactivate user account (admin only)"""
    user_service = UserService(db)
    
    try:
        success = user_service.deactivate_user(user_id)
        if success:
            return {"message": "User deactivated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User deactivation failed"
        )