"""Add performance indexes for enhanced features

Revision ID: add_performance_indexes
Revises: 8c9edc2b6bb8
Create Date: 2024-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_performance_indexes'
down_revision = '8c9edc2b6bb8'
branch_labels = None
depends_on = None


def upgrade():
    """Add performance indexes for enhanced features"""
    
    # Indexes for learning_resources table (recommendations system)
    op.create_index('idx_learning_resources_category_level', 'learning_resources', 
                   ['category', 'level'])
    op.create_index('idx_learning_resources_ranking_weight', 'learning_resources', 
                   ['ranking_weight'], postgresql_using='btree')
    op.create_index('idx_learning_resources_type_provider', 'learning_resources', 
                   ['type', 'provider'])
    
    # Indexes for user_recommendations table (tracking and feedback)
    op.create_index('idx_user_recommendations_user_resource', 'user_recommendations', 
                   ['user_id', 'resource_id'])
    op.create_index('idx_user_recommendations_recommended_at', 'user_recommendations', 
                   ['recommended_at'])
    op.create_index('idx_user_recommendations_feedback', 'user_recommendations', 
                   ['user_feedback'])
    
    # Indexes for interview_sessions table (enhanced session management)
    op.create_index('idx_interview_sessions_user_created', 'interview_sessions', 
                   ['user_id', 'created_at'])
    op.create_index('idx_interview_sessions_parent_session', 'interview_sessions', 
                   ['parent_session_id'])
    op.create_index('idx_interview_sessions_session_mode', 'interview_sessions', 
                   ['session_mode'])
    op.create_index('idx_interview_sessions_difficulty_level', 'interview_sessions', 
                   ['difficulty_level'])
    op.create_index('idx_interview_sessions_performance_score', 'interview_sessions', 
                   ['performance_score'])
    
    # Composite index for session family queries
    op.create_index('idx_interview_sessions_family_lookup', 'interview_sessions', 
                   ['user_id', 'parent_session_id', 'created_at'])
    
    # Indexes for users table (hierarchical roles)
    op.create_index('idx_users_main_role', 'users', ['main_role'])
    op.create_index('idx_users_sub_role', 'users', ['sub_role'])
    op.create_index('idx_users_role_hierarchy', 'users', 
                   ['main_role', 'sub_role', 'specialization'])
    
    # Indexes for role_hierarchy table
    op.create_index('idx_role_hierarchy_main_sub', 'role_hierarchy', 
                   ['main_role', 'sub_role'])
    op.create_index('idx_role_hierarchy_version', 'role_hierarchy', ['version'])
    
    # Indexes for questions table (enhanced question generation)
    op.create_index('idx_questions_difficulty_tags', 'questions', 
                   ['question_difficulty_tags'], postgresql_using='gin')
    op.create_index('idx_questions_role_difficulty', 'questions', 
                   ['role_category', 'difficulty_level'])
    
    # Indexes for performance_metrics table (statistics and trends)
    op.create_index('idx_performance_metrics_session_created', 'performance_metrics', 
                   ['session_id', 'created_at'])
    op.create_index('idx_performance_metrics_scores', 'performance_metrics', 
                   ['content_quality_score', 'body_language_score', 'tone_confidence_score'])
    
    # Partial indexes for active sessions
    op.execute("""
        CREATE INDEX idx_interview_sessions_active 
        ON interview_sessions (user_id, created_at) 
        WHERE status IN ('active', 'paused')
    """)
    
    # Partial index for completed sessions with scores
    op.execute("""
        CREATE INDEX idx_interview_sessions_completed_with_scores 
        ON interview_sessions (user_id, created_at, performance_score) 
        WHERE status = 'completed' AND performance_score IS NOT NULL
    """)


def downgrade():
    """Remove performance indexes"""
    
    # Drop custom partial indexes
    op.drop_index('idx_interview_sessions_active')
    op.drop_index('idx_interview_sessions_completed_with_scores')
    
    # Drop regular indexes
    op.drop_index('idx_learning_resources_category_level')
    op.drop_index('idx_learning_resources_ranking_weight')
    op.drop_index('idx_learning_resources_type_provider')
    
    op.drop_index('idx_user_recommendations_user_resource')
    op.drop_index('idx_user_recommendations_recommended_at')
    op.drop_index('idx_user_recommendations_feedback')
    
    op.drop_index('idx_interview_sessions_user_created')
    op.drop_index('idx_interview_sessions_parent_session')
    op.drop_index('idx_interview_sessions_session_mode')
    op.drop_index('idx_interview_sessions_difficulty_level')
    op.drop_index('idx_interview_sessions_performance_score')
    op.drop_index('idx_interview_sessions_family_lookup')
    
    op.drop_index('idx_users_main_role')
    op.drop_index('idx_users_sub_role')
    op.drop_index('idx_users_role_hierarchy')
    
    op.drop_index('idx_role_hierarchy_main_sub')
    op.drop_index('idx_role_hierarchy_version')
    
    op.drop_index('idx_questions_difficulty_tags')
    op.drop_index('idx_questions_role_difficulty')
    
    op.drop_index('idx_performance_metrics_session_created')
    op.drop_index('idx_performance_metrics_scores')