"""add_performance_optimization_indexes

Revision ID: ee86ffe18e68
Revises: f18c4b44c320
Create Date: 2025-08-30 23:09:20.179279

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ee86ffe18e68'
down_revision = 'f18c4b44c320'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Helper function to create index if it doesn't exist
    def create_index_if_not_exists(index_name, table_name, columns):
        try:
            op.create_index(index_name, table_name, columns)
        except Exception:
            pass  # Index might already exist
    
    # Performance metrics optimization indexes
    create_index_if_not_exists('idx_performance_metrics_session_created', 'performance_metrics', 
                              ['session_id', 'created_at'])
    create_index_if_not_exists('idx_performance_metrics_scores_composite', 'performance_metrics', 
                              ['content_quality_score', 'body_language_score', 'tone_confidence_score'])
    create_index_if_not_exists('idx_performance_metrics_response_time', 'performance_metrics', 
                              ['response_time'])
    
    # Interview sessions optimization indexes
    create_index_if_not_exists('idx_interview_sessions_user_status_date', 'interview_sessions', 
                              ['user_id', 'status', 'created_at'])
    create_index_if_not_exists('idx_interview_sessions_performance_score', 'interview_sessions', 
                              ['performance_score'])
    create_index_if_not_exists('idx_interview_sessions_difficulty_level', 'interview_sessions', 
                              ['difficulty_level'])
    create_index_if_not_exists('idx_interview_sessions_session_mode', 'interview_sessions', 
                              ['session_mode'])
    create_index_if_not_exists('idx_interview_sessions_parent_session', 'interview_sessions', 
                              ['parent_session_id'])
    
    # Role hierarchy optimization indexes
    create_index_if_not_exists('idx_role_hierarchy_main_sub_active', 'role_hierarchy', 
                              ['main_role', 'sub_role', 'is_active'])
    create_index_if_not_exists('idx_role_hierarchy_specialization', 'role_hierarchy', 
                              ['specialization'])
    
    # Users table role hierarchy indexes
    create_index_if_not_exists('idx_users_main_role', 'users', ['main_role'])
    create_index_if_not_exists('idx_users_sub_role', 'users', ['sub_role'])
    create_index_if_not_exists('idx_users_specialization', 'users', ['specialization'])
    create_index_if_not_exists('idx_users_role_hierarchy_composite', 'users', 
                              ['main_role', 'sub_role', 'specialization'])
    
    # Questions table optimization indexes
    create_index_if_not_exists('idx_questions_role_difficulty', 'questions', 
                              ['role_category', 'difficulty_level'])
    create_index_if_not_exists('idx_questions_type_generated', 'questions', 
                              ['question_type', 'generated_by'])
    
    # Learning resources optimization indexes
    create_index_if_not_exists('idx_learning_resources_category_level', 'learning_resources', 
                              ['category', 'level'])
    create_index_if_not_exists('idx_learning_resources_ranking_weight', 'learning_resources', 
                              ['ranking_weight'])
    create_index_if_not_exists('idx_learning_resources_type_provider', 'learning_resources', 
                              ['type', 'provider'])
    
    # User recommendations optimization indexes
    create_index_if_not_exists('idx_user_recommendations_user_recommended', 'user_recommendations', 
                              ['user_id', 'recommended_at'])
    create_index_if_not_exists('idx_user_recommendations_clicked', 'user_recommendations', 
                              ['clicked'])
    create_index_if_not_exists('idx_user_recommendations_feedback', 'user_recommendations', 
                              ['user_feedback'])
    
    # User sessions optimization indexes
    create_index_if_not_exists('idx_user_sessions_expires', 'user_sessions', ['expires_at'])
    create_index_if_not_exists('idx_user_sessions_user_expires', 'user_sessions', 
                              ['user_id', 'expires_at'])
    
    # Password resets optimization indexes
    create_index_if_not_exists('idx_password_resets_token', 'password_resets', ['token'])
    create_index_if_not_exists('idx_password_resets_expires', 'password_resets', ['expires_at'])
    create_index_if_not_exists('idx_password_resets_user_used', 'password_resets', 
                              ['user_id', 'used'])


def downgrade() -> None:
    # Drop all the indexes in reverse order
    op.drop_index('idx_password_resets_user_used', 'password_resets')
    op.drop_index('idx_password_resets_expires', 'password_resets')
    op.drop_index('idx_password_resets_token', 'password_resets')
    
    op.drop_index('idx_user_sessions_user_expires', 'user_sessions')
    op.drop_index('idx_user_sessions_expires', 'user_sessions')
    
    op.drop_index('idx_user_recommendations_feedback', 'user_recommendations')
    op.drop_index('idx_user_recommendations_clicked', 'user_recommendations')
    op.drop_index('idx_user_recommendations_user_recommended', 'user_recommendations')
    
    op.drop_index('idx_learning_resources_type_provider', 'learning_resources')
    op.drop_index('idx_learning_resources_ranking_weight', 'learning_resources')
    try:
        op.drop_index('idx_learning_resources_category_level', 'learning_resources')
    except:
        pass  # Index might not exist
    
    op.drop_index('idx_questions_type_generated', 'questions')
    op.drop_index('idx_questions_role_difficulty', 'questions')
    
    op.drop_index('idx_users_role_hierarchy_composite', 'users')
    op.drop_index('idx_users_specialization', 'users')
    op.drop_index('idx_users_sub_role', 'users')
    op.drop_index('idx_users_main_role', 'users')
    
    op.drop_index('idx_role_hierarchy_specialization', 'role_hierarchy')
    op.drop_index('idx_role_hierarchy_main_sub_active', 'role_hierarchy')
    
    op.drop_index('idx_interview_sessions_parent_session', 'interview_sessions')
    op.drop_index('idx_interview_sessions_session_mode', 'interview_sessions')
    op.drop_index('idx_interview_sessions_difficulty_level', 'interview_sessions')
    op.drop_index('idx_interview_sessions_performance_score', 'interview_sessions')
    op.drop_index('idx_interview_sessions_user_status_date', 'interview_sessions')
    
    op.drop_index('idx_performance_metrics_response_time', 'performance_metrics')
    op.drop_index('idx_performance_metrics_scores_composite', 'performance_metrics')
    op.drop_index('idx_performance_metrics_session_created', 'performance_metrics')