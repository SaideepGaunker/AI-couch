"""Optimize database indexes for performance

Revision ID: optimize_indexes_001
Revises: 8c9edc2b6bb8
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'optimize_indexes_001'
down_revision = '8c9edc2b6bb8'
branch_labels = None
depends_on = None


def upgrade():
    """Add performance indexes"""
    
    # Users table indexes
    op.create_index('idx_users_email_active', 'users', ['email', 'is_active'])
    op.create_index('idx_users_role_active', 'users', ['role', 'is_active'])
    op.create_index('idx_users_last_login', 'users', ['last_login'])
    op.create_index('idx_users_created_at', 'users', ['created_at'])
    
    # Interview sessions indexes
    op.create_index('idx_sessions_user_status', 'interview_sessions', ['user_id', 'status'])
    op.create_index('idx_sessions_user_created', 'interview_sessions', ['user_id', 'created_at'])
    op.create_index('idx_sessions_status_created', 'interview_sessions', ['status', 'created_at'])
    op.create_index('idx_sessions_target_role', 'interview_sessions', ['target_role'])
    op.create_index('idx_sessions_difficulty', 'interview_sessions', ['difficulty_level'])
    op.create_index('idx_sessions_completed_at', 'interview_sessions', ['completed_at'])
    
    # Questions table indexes
    op.create_index('idx_questions_type_role', 'questions', ['question_type', 'role_category'])
    op.create_index('idx_questions_difficulty', 'questions', ['difficulty_level'])
    op.create_index('idx_questions_role_difficulty', 'questions', ['role_category', 'difficulty_level'])
    op.create_index('idx_questions_generated_by', 'questions', ['generated_by'])
    op.create_index('idx_questions_created_at', 'questions', ['created_at'])
    
    # Performance metrics indexes
    op.create_index('idx_metrics_session_question', 'performance_metrics', ['session_id', 'question_id'])
    op.create_index('idx_metrics_session_created', 'performance_metrics', ['session_id', 'created_at'])
    op.create_index('idx_metrics_content_score', 'performance_metrics', ['content_quality_score'])
    op.create_index('idx_metrics_body_score', 'performance_metrics', ['body_language_score'])
    op.create_index('idx_metrics_tone_score', 'performance_metrics', ['tone_confidence_score'])
    
    # User progress indexes
    op.create_index('idx_progress_user_metric', 'user_progress', ['user_id', 'metric_type'])
    op.create_index('idx_progress_user_date', 'user_progress', ['user_id', 'session_date'])
    op.create_index('idx_progress_metric_score', 'user_progress', ['metric_type', 'score'])
    
    # Role hierarchy indexes
    op.create_index('idx_role_hierarchy_main', 'role_hierarchy', ['main_role'])
    op.create_index('idx_role_hierarchy_sub', 'role_hierarchy', ['sub_role'])
    op.create_index('idx_role_hierarchy_specialization', 'role_hierarchy', ['specialization'])
    op.create_index('idx_role_hierarchy_active', 'role_hierarchy', ['is_active'])
    
    # Learning resources indexes
    op.create_index('idx_resources_category_level', 'learning_resources', ['category', 'level'])
    op.create_index('idx_resources_type_level', 'learning_resources', ['type', 'level'])
    op.create_index('idx_resources_ranking', 'learning_resources', ['ranking_weight'])
    
    # User recommendations indexes
    op.create_index('idx_recommendations_user_recommended', 'user_recommendations', ['user_id', 'recommended_at'])
    op.create_index('idx_recommendations_clicked', 'user_recommendations', ['clicked'])
    op.create_index('idx_recommendations_feedback', 'user_recommendations', ['user_feedback'])
    
    # Password resets indexes
    op.create_index('idx_password_resets_token', 'password_resets', ['token'])
    op.create_index('idx_password_resets_user_expires', 'password_resets', ['user_id', 'expires_at'])
    op.create_index('idx_password_resets_used', 'password_resets', ['used'])
    
    # User sessions indexes
    op.create_index('idx_user_sessions_token', 'user_sessions', ['session_token'])
    op.create_index('idx_user_sessions_user_expires', 'user_sessions', ['user_id', 'expires_at'])
    op.create_index('idx_user_sessions_expires', 'user_sessions', ['expires_at'])
    
    # Institution analytics indexes
    op.create_index('idx_institution_analytics_date', 'institution_analytics', ['report_date'])
    op.create_index('idx_institution_analytics_inst_date', 'institution_analytics', ['institution_id', 'report_date'])


def downgrade():
    """Remove performance indexes"""
    
    # Users table indexes
    op.drop_index('idx_users_email_active', 'users')
    op.drop_index('idx_users_role_active', 'users')
    op.drop_index('idx_users_last_login', 'users')
    op.drop_index('idx_users_created_at', 'users')
    
    # Interview sessions indexes
    op.drop_index('idx_sessions_user_status', 'interview_sessions')
    op.drop_index('idx_sessions_user_created', 'interview_sessions')
    op.drop_index('idx_sessions_status_created', 'interview_sessions')
    op.drop_index('idx_sessions_target_role', 'interview_sessions')
    op.drop_index('idx_sessions_difficulty', 'interview_sessions')
    op.drop_index('idx_sessions_completed_at', 'interview_sessions')
    
    # Questions table indexes
    op.drop_index('idx_questions_type_role', 'questions')
    op.drop_index('idx_questions_difficulty', 'questions')
    op.drop_index('idx_questions_role_difficulty', 'questions')
    op.drop_index('idx_questions_generated_by', 'questions')
    op.drop_index('idx_questions_created_at', 'questions')
    
    # Performance metrics indexes
    op.drop_index('idx_metrics_session_question', 'performance_metrics')
    op.drop_index('idx_metrics_session_created', 'performance_metrics')
    op.drop_index('idx_metrics_content_score', 'performance_metrics')
    op.drop_index('idx_metrics_body_score', 'performance_metrics')
    op.drop_index('idx_metrics_tone_score', 'performance_metrics')
    
    # User progress indexes
    op.drop_index('idx_progress_user_metric', 'user_progress')
    op.drop_index('idx_progress_user_date', 'user_progress')
    op.drop_index('idx_progress_metric_score', 'user_progress')
    
    # Role hierarchy indexes
    op.drop_index('idx_role_hierarchy_main', 'role_hierarchy')
    op.drop_index('idx_role_hierarchy_sub', 'role_hierarchy')
    op.drop_index('idx_role_hierarchy_specialization', 'role_hierarchy')
    op.drop_index('idx_role_hierarchy_active', 'role_hierarchy')
    
    # Learning resources indexes
    op.drop_index('idx_resources_category_level', 'learning_resources')
    op.drop_index('idx_resources_type_level', 'learning_resources')
    op.drop_index('idx_resources_ranking', 'learning_resources')
    
    # User recommendations indexes
    op.drop_index('idx_recommendations_user_recommended', 'user_recommendations')
    op.drop_index('idx_recommendations_clicked', 'user_recommendations')
    op.drop_index('idx_recommendations_feedback', 'user_recommendations')
    
    # Password resets indexes
    op.drop_index('idx_password_resets_token', 'password_resets')
    op.drop_index('idx_password_resets_user_expires', 'password_resets')
    op.drop_index('idx_password_resets_used', 'password_resets')
    
    # User sessions indexes
    op.drop_index('idx_user_sessions_token', 'user_sessions')
    op.drop_index('idx_user_sessions_user_expires', 'user_sessions')
    op.drop_index('idx_user_sessions_expires', 'user_sessions')
    
    # Institution analytics indexes
    op.drop_index('idx_institution_analytics_date', 'institution_analytics')
    op.drop_index('idx_institution_analytics_inst_date', 'institution_analytics')