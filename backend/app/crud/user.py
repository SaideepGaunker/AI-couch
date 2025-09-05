"""
CRUD operations for User model
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.models import User, PasswordReset, UserSession
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password


def get_user(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """Get list of users with pagination"""
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, user: UserCreate) -> User:
    """Create new user"""
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        password_hash=hashed_password,
        name=user.name,
        role=user.role,
        target_roles=user.target_roles if user.target_roles is not None else [],
        experience_level=user.experience_level
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, user_update: UserUpdate) -> Optional[User]:
    """Update user information"""
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int) -> bool:
    """Delete user (soft delete by setting is_active to False)"""
    db_user = get_user(db, user_id)
    if not db_user:
        return False
    
    db_user.is_active = False
    db.commit()
    return True


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate user with email and password"""
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def verify_user_email(db: Session, user_id: int) -> bool:
    """Mark user email as verified"""
    db_user = get_user(db, user_id)
    if not db_user:
        return False
    
    db_user.is_verified = True
    db.commit()
    return True


def change_user_password(db: Session, user_id: int, new_password: str) -> bool:
    """Change user password"""
    db_user = get_user(db, user_id)
    if not db_user:
        return False
    
    db_user.password_hash = get_password_hash(new_password)
    db.commit()
    return True


def create_password_reset_token(db: Session, user_id: int, token: str, expires_at) -> PasswordReset:
    """Create password reset token"""
    # Invalidate existing tokens
    db.query(PasswordReset).filter(
        and_(PasswordReset.user_id == user_id, PasswordReset.used == False)
    ).update({"used": True})
    
    reset_token = PasswordReset(
        user_id=user_id,
        token=token,
        expires_at=expires_at
    )
    db.add(reset_token)
    db.commit()
    db.refresh(reset_token)
    return reset_token


def get_password_reset_token(db: Session, token: str) -> Optional[PasswordReset]:
    """Get password reset token"""
    return db.query(PasswordReset).filter(
        and_(PasswordReset.token == token, PasswordReset.used == False)
    ).first()


def use_password_reset_token(db: Session, token: str) -> bool:
    """Mark password reset token as used"""
    reset_token = get_password_reset_token(db, token)
    if not reset_token:
        return False
    
    reset_token.used = True
    db.commit()
    return True


def create_user_session(db: Session, user_id: int, session_token: str, 
                       ip_address: str, user_agent: str, expires_at) -> UserSession:
    """Create user session"""
    session = UserSession(
        user_id=user_id,
        session_token=session_token,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_user_session(db: Session, session_token: str) -> Optional[UserSession]:
    """Get user session by token"""
    return db.query(UserSession).filter(UserSession.session_token == session_token).first()


def delete_user_session(db: Session, session_token: str) -> bool:
    """Delete user session"""
    session = get_user_session(db, session_token)
    if not session:
        return False
    
    db.delete(session)
    db.commit()
    return True