"""
FastAPI dependencies for authentication, authorization, and rate limiting
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from functools import wraps
import time

from app.db.database import get_db
from app.db.models import User
from app.crud.user import get_user
from app.core.security import verify_token

security = HTTPBearer()

# In-memory rate limiting storage (use Redis in production)
rate_limit_storage: Dict[str, Dict[str, Any]] = {}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Verify token
        payload = verify_token(credentials.credentials, "access")
        if payload is None:
            raise credentials_exception
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        
        # Get user from database
        user = get_user(db, user_id=int(user_id))
        if user is None:
            raise credentials_exception
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated"
            )
        
        return user
    
    except HTTPException:
        raise
    except Exception:
        raise credentials_exception


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user (additional check for active status)"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    return current_user


def get_current_verified_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current verified user"""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    return current_user


def require_role(allowed_roles: list):
    """Dependency factory for role-based access control"""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    return role_checker


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def rate_limit(max_calls: int, window_seconds: int):
    """Rate limiting dependency factory"""
    def rate_limiter(request: Request):
        # Get client identifier (IP address)
        client_id = request.client.host
        endpoint = f"{request.method}:{request.url.path}"
        key = f"{client_id}:{endpoint}"
        
        current_time = time.time()
        
        # Clean up old entries
        if key in rate_limit_storage:
            rate_limit_storage[key]["calls"] = [
                call_time for call_time in rate_limit_storage[key]["calls"]
                if current_time - call_time < window_seconds
            ]
        else:
            rate_limit_storage[key] = {"calls": []}
        
        # Check rate limit
        if len(rate_limit_storage[key]["calls"]) >= max_calls:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {max_calls} calls per {window_seconds} seconds"
            )
        
        # Record this call
        rate_limit_storage[key]["calls"].append(current_time)
        
        return True
    
    return rate_limiter


def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Optional authentication - returns user if authenticated, None otherwise"""
    if not credentials:
        return None
    
    try:
        payload = verify_token(credentials.credentials, "access")
        if payload is None:
            return None
        
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        
        user = get_user(db, user_id=int(user_id))
        if user is None or not user.is_active:
            return None
        
        return user
    
    except Exception:
        return None


class RateLimiter:
    """Advanced rate limiter with different strategies"""
    
    def __init__(self):
        self.storage = {}
    
    def sliding_window(self, key: str, max_calls: int, window_seconds: int) -> bool:
        """Sliding window rate limiting"""
        current_time = time.time()
        
        if key not in self.storage:
            self.storage[key] = []
        
        # Remove old entries
        self.storage[key] = [
            call_time for call_time in self.storage[key]
            if current_time - call_time < window_seconds
        ]
        
        # Check limit
        if len(self.storage[key]) >= max_calls:
            return False
        
        # Record call
        self.storage[key].append(current_time)
        return True
    
    def token_bucket(self, key: str, capacity: int, refill_rate: float) -> bool:
        """Token bucket rate limiting"""
        current_time = time.time()
        
        if key not in self.storage:
            self.storage[key] = {
                "tokens": capacity,
                "last_refill": current_time
            }
        
        bucket = self.storage[key]
        
        # Refill tokens
        time_passed = current_time - bucket["last_refill"]
        tokens_to_add = time_passed * refill_rate
        bucket["tokens"] = min(capacity, bucket["tokens"] + tokens_to_add)
        bucket["last_refill"] = current_time
        
        # Check if we have tokens
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True
        
        return False


# Global rate limiter instance
rate_limiter = RateLimiter()