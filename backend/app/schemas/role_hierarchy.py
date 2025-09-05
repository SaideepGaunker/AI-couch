"""
Role hierarchy related Pydantic schemas
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, field_validator, ConfigDict


class HierarchicalRole(BaseModel):
    main_role: str
    sub_role: Optional[str] = None
    specialization: Optional[str] = None
    tech_stack: Optional[List[str]] = []
    
    @field_validator('main_role')
    @classmethod
    def validate_main_role(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Main role is required')
        return v.strip()


class RoleHierarchyCreate(BaseModel):
    main_role: str
    sub_role: Optional[str] = None
    specialization: Optional[str] = None
    tech_stack: Optional[List[str]] = []
    question_tags: Optional[List[str]] = []
    version: Optional[str] = "1.0"
    is_active: Optional[bool] = True


class RoleHierarchyResponse(BaseModel):
    id: int
    main_role: str
    sub_role: Optional[str] = None
    specialization: Optional[str] = None
    tech_stack: List[str] = []
    question_tags: List[str] = []
    version: str
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class RoleHierarchyStructure(BaseModel):
    """Complete role hierarchy structure for frontend"""
    main_roles: Dict[str, Dict[str, Any]]


class UserRoleUpdate(BaseModel):
    main_role: Optional[str] = None
    sub_role: Optional[str] = None
    specialization: Optional[str] = None