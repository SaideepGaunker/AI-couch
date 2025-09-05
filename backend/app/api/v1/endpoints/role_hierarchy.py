"""
Role Hierarchy API endpoints
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.crud import role_hierarchy as role_crud
from app.schemas.role_hierarchy import (
    RoleHierarchyCreate,
    RoleHierarchyResponse,
    RoleHierarchyStructure,
    UserRoleUpdate
)
from app.core.dependencies import get_current_user, require_admin

router = APIRouter()


@router.get("/structure", response_model=Dict[str, Any])
async def get_role_hierarchy_structure(
    db: Session = Depends(get_db)
):
    """
    Get complete role hierarchy structure for frontend dropdowns
    Public endpoint - no authentication required
    """
    try:
        structure = role_crud.get_complete_role_hierarchy_structure(db)
        return structure
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving role hierarchy structure: {str(e)}"
        )


@router.get("/hierarchy", response_model=Dict[str, Any])
async def get_role_hierarchy(
    db: Session = Depends(get_db)
):
    """
    Get complete role hierarchy structure for frontend dropdowns
    Public endpoint - no authentication required (alias for /structure)
    """
    try:
        structure = role_crud.get_complete_role_hierarchy_structure(db)
        return structure
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving role hierarchy structure: {str(e)}"
        )


@router.get("/main-roles", response_model=List[str])
async def get_main_roles(
    db: Session = Depends(get_db)
):
    """
    Get all available main roles
    Public endpoint - no authentication required
    """
    try:
        main_roles = role_crud.get_main_roles(db)
        return main_roles
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving main roles: {str(e)}"
        )


@router.get("/sub-roles/{main_role}", response_model=List[str])
async def get_sub_roles(
    main_role: str,
    db: Session = Depends(get_db)
):
    """
    Get sub-roles for a specific main role
    Public endpoint - no authentication required
    """
    try:
        sub_roles = role_crud.get_sub_roles_for_main_role(db, main_role)
        return sub_roles
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving sub-roles for {main_role}: {str(e)}"
        )


@router.get("/specializations/{main_role}", response_model=List[str])
async def get_specializations(
    main_role: str,
    sub_role: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get specializations for a role combination
    Public endpoint - no authentication required
    """
    try:
        specializations = role_crud.get_specializations_for_role(db, main_role, sub_role)
        return specializations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving specializations: {str(e)}"
        )


@router.get("/tech-stacks/{main_role}", response_model=List[str])
async def get_tech_stacks(
    main_role: str,
    sub_role: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get tech stacks for a role combination
    Public endpoint - no authentication required
    """
    try:
        tech_stacks = role_crud.get_tech_stacks_for_role(db, main_role, sub_role)
        return tech_stacks
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving tech stacks: {str(e)}"
        )


@router.put("/user/role", response_model=Dict[str, str])
async def update_user_role(
    role_update: UserRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's hierarchical role information
    """
    try:
        updated_user = role_crud.update_user_role(db, current_user.id, role_update)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "message": "User role updated successfully",
            "main_role": updated_user.main_role,
            "sub_role": updated_user.sub_role,
            "specialization": updated_user.specialization
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user role: {str(e)}"
        )


# Admin-only endpoints for managing role hierarchy
@router.post("/", response_model=RoleHierarchyResponse)
async def create_role_hierarchy(
    role_data: RoleHierarchyCreate,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create new role hierarchy entry (Admin only)
    """
    try:
        created_role = role_crud.create_role_hierarchy(db, role_data)
        return created_role
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating role hierarchy: {str(e)}"
        )


@router.get("/", response_model=List[RoleHierarchyResponse])
async def list_role_hierarchies(
    main_role: Optional[str] = Query(None),
    sub_role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    version: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    List role hierarchies with optional filtering (Admin only)
    """
    try:
        roles = role_crud.get_role_hierarchies(
            db=db,
            main_role=main_role,
            sub_role=sub_role,
            is_active=is_active,
            version=version,
            skip=skip,
            limit=limit
        )
        return roles
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving role hierarchies: {str(e)}"
        )


@router.get("/{role_id}", response_model=RoleHierarchyResponse)
async def get_role_hierarchy(
    role_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get role hierarchy by ID (Admin only)
    """
    try:
        role = role_crud.get_role_hierarchy(db, role_id)
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role hierarchy not found"
            )
        
        return role
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving role hierarchy: {str(e)}"
        )


@router.put("/{role_id}", response_model=RoleHierarchyResponse)
async def update_role_hierarchy(
    role_id: int,
    update_data: Dict[str, Any],
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update role hierarchy (Admin only)
    """
    try:
        updated_role = role_crud.update_role_hierarchy(db, role_id, update_data)
        
        if not updated_role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role hierarchy not found"
            )
        
        return updated_role
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating role hierarchy: {str(e)}"
        )


@router.delete("/{role_id}")
async def delete_role_hierarchy(
    role_id: int,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Soft delete role hierarchy (Admin only)
    """
    try:
        success = role_crud.delete_role_hierarchy(db, role_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role hierarchy not found"
            )
        
        return {"message": "Role hierarchy deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting role hierarchy: {str(e)}"
        )


@router.post("/seed")
async def seed_role_hierarchy(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Seed database with initial role hierarchy data (Admin only)
    """
    try:
        created_count = role_crud.seed_role_hierarchy(db)
        return {
            "message": f"Successfully seeded {created_count} role hierarchy entries",
            "created_count": created_count
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error seeding role hierarchy: {str(e)}"
        )