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

    
    # New hierarchical role fields
    main_role = Column(String(100))
    sub_role = Column(String(100))
    specialization = Column(String(100))
    
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
    recommendations = relationship("UserRecommendation", back_populates="user")



class LearningResource(Base):
    __tablename__ = "learning_resources"
    
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False)  # body_language, voice_analysis, content_quality, overall
    type = Column(String(50), nullable=False)  # video, course, article, book, tutorial
    level = Column(String(20), nullable=False)  # beginner, intermediate, advanced
    title = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    provider = Column(String(100))  # YouTube, Coursera, Udemy, etc.
    tags = Column(JSON, default=lambda: [])  # Array of tags for filtering
    ranking_weight = Column(Float, default=1.0)  # 0.0 to 2.0 for recommendation ranking
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user_recommendations = relationship("UserRecommendation", back_populates="resource")


class UserRecommendation(Base):
    __tablename__ = "user_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resource_id = Column(Integer, ForeignKey("learning_resources.id"), nullable=False)
    
    # User interaction tracking
    recommended_at = Column(DateTime, server_default=func.now())
    clicked = Column(Boolean, default=False)
    user_feedback = Column(String(20), default="neutral")  # liked, disliked, neutral
    feedback_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="recommendations")
    resource = relationship("LearningResource", back_populates="user_recommendations")


class RoleHierarchy(Base):
    __tablename__ = "role_hierarchy"
    
    id = Column(Integer, primary_key=True, index=True)
    main_role = Column(String(100), nullable=False)
    sub_role = Column(String(100), nullable=False)
    specialization = Column(String(100))
    
    # Associated data
    tech_stack = Column(JSON, default=lambda: [])  # Array of technology stacks
    question_tags = Column(JSON, default=lambda: [])  # Tags for question filtering
    
    # Versioning support
    version = Column(String(20), default="1.0")
    is_active = Column(Boolean, default=True)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())


class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_type = Column(String(50), nullable=False)  # hr, technical, mixed
    target_role = Column(String(100))
    duration = Column(Integer)  # in minutes
    status = Column(String(50), default="active")  # active, completed, paused
    overall_score = Column(Float, default=0.0)
    
    # New adaptive difficulty fields
    performance_score = Column(Float, default=0.0)
    difficulty_level = Column(String(50), default="medium")  # easy, medium, hard, expert
    next_difficulty = Column(String(50), nullable=True)  # calculated difficulty for next session
    
    # Session-specific difficulty tracking fields
    initial_difficulty_level = Column(String(50), nullable=True)  # difficulty when session started
    current_difficulty_level = Column(String(50), nullable=True)  # current difficulty during session
    final_difficulty_level = Column(String(50), nullable=True)  # final difficulty when session completed
    difficulty_changes_count = Column(Integer, default=0)  # number of difficulty adjustments
    difficulty_state_json = Column(JSON, nullable=True)  # detailed difficulty change history
    
    # New session continuity fields
    parent_session_id = Column(Integer, ForeignKey("interview_sessions.id"), nullable=True)
    session_mode = Column(String(50), default="new")  # new, practice_again, continued, quick_test
    resume_state = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="interview_sessions")
    performance_metrics = relationship("PerformanceMetrics", back_populates="session")
    parent_session = relationship("InterviewSession", remote_side=[id], backref="practice_sessions")
    
    def serialize_difficulty_state(self, difficulty_changes: list = None) -> dict:
        """Serialize difficulty state for JSON storage"""
        import json
        from datetime import datetime
        
        state = {
            "initial_difficulty": self.initial_difficulty_level,
            "current_difficulty": self.current_difficulty_level,
            "final_difficulty": self.final_difficulty_level,
            "changes_count": self.difficulty_changes_count or 0,
            "difficulty_changes": difficulty_changes or [],
            "last_updated": datetime.utcnow().isoformat(),
            "session_id": self.id
        }
        
        self.difficulty_state_json = state
        return state
    
    def deserialize_difficulty_state(self) -> dict:
        """Deserialize difficulty state from JSON storage"""
        if self.difficulty_state_json:
            return self.difficulty_state_json
        
        # Fallback to basic state if no JSON data
        return {
            "initial_difficulty": self.initial_difficulty_level,
            "current_difficulty": self.current_difficulty_level,
            "final_difficulty": self.final_difficulty_level,
            "changes_count": self.difficulty_changes_count or 0,
            "difficulty_changes": [],
            "session_id": self.id
        }
    
    def update_difficulty_tracking(self, new_difficulty: str, change_reason: str = None):
        """Update difficulty tracking fields when difficulty changes"""
        from datetime import datetime
        
        # Initialize if not set
        if not self.initial_difficulty_level:
            self.initial_difficulty_level = self.difficulty_level or "medium"
        
        if not self.current_difficulty_level:
            self.current_difficulty_level = self.initial_difficulty_level
        
        # Record the change
        old_difficulty = self.current_difficulty_level
        self.current_difficulty_level = new_difficulty
        self.difficulty_level = new_difficulty  # Keep legacy field in sync
        
        # Increment changes count
        self.difficulty_changes_count = (self.difficulty_changes_count or 0) + 1
        
        # Update difficulty state JSON
        current_state = self.deserialize_difficulty_state()
        
        change_record = {
            "from_difficulty": old_difficulty,
            "to_difficulty": new_difficulty,
            "reason": change_reason or "adaptive_adjustment",
            "timestamp": datetime.utcnow().isoformat(),
            "change_number": self.difficulty_changes_count
        }
        
        current_state["difficulty_changes"].append(change_record)
        current_state["current_difficulty"] = new_difficulty
        current_state["changes_count"] = self.difficulty_changes_count
        current_state["last_updated"] = datetime.utcnow().isoformat()
        
        self.serialize_difficulty_state(current_state["difficulty_changes"])
    
    def finalize_difficulty(self):
        """Mark the final difficulty when session completes"""
        self.final_difficulty_level = self.current_difficulty_level or self.difficulty_level
        
        # Update JSON state
        current_state = self.deserialize_difficulty_state()
        current_state["final_difficulty"] = self.final_difficulty_level
        self.serialize_difficulty_state(current_state["difficulty_changes"])
    
    def get_difficulty_for_practice(self) -> str:
        """Get the appropriate difficulty for practice sessions"""
        # Use final difficulty if available, otherwise current, otherwise initial
        return (self.final_difficulty_level or 
                self.current_difficulty_level or 
                self.initial_difficulty_level or 
                self.difficulty_level or 
                "medium")


class Question(Base):
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False)  # behavioral, technical, situational
    role_category = Column(String(100))
    difficulty_level = Column(String(50))  # beginner, intermediate, advanced
    expected_duration = Column(Integer)  # in minutes
    generated_by = Column(String(50), default="gemini_api")  # gemini_api, manual
    
    # New field for enhanced role filtering
    question_difficulty_tags = Column(JSON, default=lambda: [])
    
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
    
    # Enhanced performance tracking fields
    recommendations = Column(JSON, default=lambda: [])
    improvement_areas = Column(JSON, default=lambda: [])
    learning_suggestions = Column(JSON, default=lambda: [])
    
    # Relationships
    user = relationship("User", back_populates="progress_records")
    
    def add_recommendation(self, category: str, resource_type: str, title: str, url: str, priority: str = "medium"):
        """Add a learning recommendation"""
        if not self.recommendations:
            self.recommendations = []
        
        recommendation = {
            "category": category,
            "resource_type": resource_type,
            "title": title,
            "url": url,
            "priority": priority,
            "added_at": func.now()
        }
        self.recommendations.append(recommendation)
    
    def add_improvement_area(self, area: str, priority: str, suggestions: list):
        """Add an area for improvement with specific suggestions"""
        if not self.improvement_areas:
            self.improvement_areas = []
        
        improvement_area = {
            "area": area,
            "priority": priority,
            "suggestions": suggestions,
            "added_at": func.now()
        }
        self.improvement_areas.append(improvement_area)
    
    def add_learning_suggestion(self, suggestion: str, category: str, difficulty: str = "intermediate"):
        """Add a learning suggestion"""
        if not self.learning_suggestions:
            self.learning_suggestions = []
        
        learning_suggestion = {
            "suggestion": suggestion,
            "category": category,
            "difficulty": difficulty,
            "added_at": func.now()
        }
        self.learning_suggestions.append(learning_suggestion)





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


