"""
Database models for the Interview Prep AI Coach application
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # job_seeker, student, admin
    target_roles = Column(JSON, default=lambda: [])
    experience_level = Column(String(50))
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    interview_sessions = relationship("InterviewSession", back_populates="user")
    progress_records = relationship("UserProgress", back_populates="user")
    password_resets = relationship("PasswordReset", back_populates="user")
    user_sessions = relationship("UserSession", back_populates="user")


class Institution(Base):
    __tablename__ = "institutions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(100))  # college, university, bootcamp
    contact_email = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    users = relationship("User", backref="institution")
    analytics = relationship("InstitutionAnalytics", back_populates="institution")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_type = Column(String(50), nullable=False)  # hr, technical, mixed
    target_role = Column(String(100))
    duration = Column(Integer)  # in minutes
    status = Column(String(50), default="active")  # active, completed, paused
    overall_score = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="interview_sessions")
    performance_metrics = relationship("PerformanceMetrics", back_populates="session")


class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False)  # behavioral, technical, situational
    role_category = Column(String(100))
    difficulty_level = Column(String(50))  # beginner, intermediate, advanced
    expected_duration = Column(Integer)  # in minutes
    generated_by = Column(String(50), default="gemini_api")  # gemini_api, manual
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    performance_metrics = relationship("PerformanceMetrics", back_populates="question")


class PerformanceMetrics(Base):
    __tablename__ = "performance_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    answer_text = Column(Text)
    body_language_score = Column(Float, default=0.0)
    tone_confidence_score = Column(Float, default=0.0)
    content_quality_score = Column(Float, default=0.0)
    response_time = Column(Integer)  # in seconds
    improvement_suggestions = Column(JSON, default=lambda: [])
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    session = relationship("InterviewSession", back_populates="performance_metrics")
    question = relationship("Question", back_populates="performance_metrics")


class UserProgress(Base):
    __tablename__ = "user_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    metric_type = Column(String(50), nullable=False)  # confidence, body_language, content_quality
    score = Column(Float, nullable=False)
    session_date = Column(DateTime, server_default=func.now())
    improvement_trend = Column(Float, default=0.0)
    
    # Relationships
    user = relationship("User", back_populates="progress_records")


class InstitutionAnalytics(Base):
    __tablename__ = "institution_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    total_students = Column(Integer, default=0)
    active_students = Column(Integer, default=0)
    average_readiness_score = Column(Float, default=0.0)
    completion_rate = Column(Float, default=0.0)
    report_date = Column(DateTime, server_default=func.now())
    
    # Relationships
    institution = relationship("Institution", back_populates="analytics")


class PasswordReset(Base):
    __tablename__ = "password_resets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="password_resets")


class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="user_sessions")