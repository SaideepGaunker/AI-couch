"""comprehensive_database_optimization_indexes

Revision ID: bf1e37acf0a7
Revises: ee86ffe18e68
Create Date: 2025-08-30 23:15:05.656793

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'bf1e37acf0a7'
down_revision = 'ee86ffe18e68'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Comprehensive database optimization with indexes and performance monitoring"""
    
    # Helper function to safely create indexes (MySQL compatible)
    def create_index_safe(index_name, table_name, columns, unique=False, mysql_where=None):
        """Create index if it doesn't already exist (MySQL compatible)"""
        try:
            # Check if index already exists
            check_query = f"""
                SELECT COUNT(*) FROM information_schema.statistics 
                WHERE table_schema = DATABASE() 
                AND table_name = '{table_name}' 
                AND index_name = '{index_name}'
            """
            result = op.get_bind().execute(text(check_query)).scalar()
            
            if result == 0:  # Index doesn't exist
                if mysql_where:
                    # MySQL doesn't support partial indexes like PostgreSQL
                    # We'll create a regular index and note the limitation
                    print(f"Note: MySQL doesn't support partial indexes. Creating regular index {index_name}")
                
                columns_str = ', '.join(columns)
                unique_str = 'UNIQUE' if unique else ''
                
                create_sql = f"CREATE {unique_str} INDEX {index_name} ON {table_name} ({columns_str})"
                op.execute(text(create_sql))
                print(f"Created index: {index_name}")
            else:
                print(f"Index {index_name} already exists, skipping")
                
        except Exception as e:
            print(f"Could not create index {index_name}: {e}")
    
    # ========================================
    # CORE PERFORMANCE INDEXES
    # ========================================
    
    # User table optimization - frequently queried columns
    create_index_safe('idx_users_email_active_optimized', 'users', ['email', 'is_active'])
    create_index_safe('idx_users_role_hierarchy_lookup', 'users', 
                     ['main_role', 'sub_role', 'specialization', 'is_active'])
    create_index_safe('idx_users_last_login_active', 'users', ['last_login', 'is_active'])
    create_index_safe('idx_users_created_updated', 'users', ['created_at', 'updated_at'])
    
    # Interview Sessions - session analysis and user history
    create_index_safe('idx_sessions_user_status_date_optimized', 'interview_sessions', 
                     ['user_id', 'status', 'created_at'])
    create_index_safe('idx_sessions_performance_analysis', 'interview_sessions', 
                     ['user_id', 'performance_score', 'difficulty_level', 'created_at'])
    create_index_safe('idx_sessions_session_continuity', 'interview_sessions', 
                     ['parent_session_id', 'session_mode', 'created_at'])
    create_index_safe('idx_sessions_role_performance', 'interview_sessions', 
                     ['target_role', 'performance_score', 'status'])
    
    # Performance Metrics - analytics and reporting
    create_index_safe('idx_metrics_session_analysis_optimized', 'performance_metrics', 
                     ['session_id', 'created_at', 'content_quality_score'])
    create_index_safe('idx_metrics_comprehensive_scores', 'performance_metrics', 
                     ['session_id', 'content_quality_score', 'body_language_score', 'tone_confidence_score'])
    create_index_safe('idx_metrics_response_time_analysis', 'performance_metrics', 
                     ['response_time', 'content_quality_score'])
    create_index_safe('idx_metrics_question_performance', 'performance_metrics', 
                     ['question_id', 'content_quality_score', 'created_at'])
    
    # User Progress - trend analysis and recommendations
    create_index_safe('idx_progress_user_metric_date_optimized', 'user_progress', 
                     ['user_id', 'metric_type', 'session_date'])
    create_index_safe('idx_progress_trend_analysis', 'user_progress', 
                     ['user_id', 'session_date', 'score', 'improvement_trend'])
    create_index_safe('idx_progress_recommendations_lookup', 'user_progress', 
                     ['user_id'], mysql_where="recommendations IS NOT NULL AND recommendations != '[]'")
    
    # Role Hierarchy - role-based queries
    create_index_safe('idx_role_hierarchy_complete_lookup', 'role_hierarchy', 
                     ['main_role', 'sub_role', 'specialization', 'is_active', 'version'])
    create_index_safe('idx_role_hierarchy_tech_stack', 'role_hierarchy', 
                     ['main_role', 'sub_role'], mysql_where="tech_stack IS NOT NULL AND tech_stack != '[]'")
    
    # Questions - question generation and filtering
    create_index_safe('idx_questions_role_difficulty_type', 'questions', 
                     ['role_category', 'difficulty_level', 'question_type'])
    create_index_safe('idx_questions_generation_lookup', 'questions', 
                     ['generated_by', 'created_at', 'difficulty_level'])
    
    # ========================================
    # SPECIALIZED INDEXES FOR ANALYTICS
    # ========================================
    
    # Note: MySQL doesn't support partial indexes like PostgreSQL
    # These would be partial indexes in PostgreSQL, but we'll create regular indexes in MySQL
    create_index_safe('idx_sessions_active_user_performance', 'interview_sessions', 
                     ['user_id', 'performance_score', 'created_at'], 
                     mysql_where="status IN ('active', 'paused')")
    
    create_index_safe('idx_sessions_completed_with_metrics', 'interview_sessions', 
                     ['user_id', 'target_role', 'performance_score', 'overall_score'], 
                     mysql_where="status = 'completed' AND performance_score IS NOT NULL")
    
    create_index_safe('idx_sessions_recent_performance', 'interview_sessions', 
                     ['user_id', 'performance_score', 'difficulty_level'], 
                     mysql_where="created_at >= CURRENT_DATE - INTERVAL 6 MONTH")
    
    # ========================================
    # COMPOSITE INDEXES FOR COMPLEX QUERIES
    # ========================================
    
    # User session history with performance trends
    create_index_safe('idx_user_session_performance_trend', 'interview_sessions', 
                     ['user_id', 'created_at', 'performance_score', 'difficulty_level', 'target_role'])
    
    # Performance metrics aggregation
    create_index_safe('idx_metrics_aggregation_optimized', 'performance_metrics', 
                     ['session_id', 'question_id', 'content_quality_score', 'body_language_score', 'tone_confidence_score', 'created_at'])
    
    # User progress tracking with recommendations
    create_index_safe('idx_progress_comprehensive_tracking', 'user_progress', 
                     ['user_id', 'metric_type', 'session_date', 'score', 'improvement_trend'])
    
    # ========================================
    # LEARNING RESOURCES AND RECOMMENDATIONS
    # ========================================
    
    # Learning resources optimization
    create_index_safe('idx_resources_recommendation_lookup', 'learning_resources', 
                     ['category', 'level', 'ranking_weight', 'type'])
    create_index_safe('idx_resources_provider_ranking', 'learning_resources', 
                     ['provider', 'ranking_weight', 'category'])
    
    # User recommendations tracking
    create_index_safe('idx_user_recommendations_analytics', 'user_recommendations', 
                     ['user_id', 'recommended_at', 'clicked', 'user_feedback'])
    create_index_safe('idx_user_recommendations_engagement', 'user_recommendations', 
                     ['resource_id', 'clicked', 'user_feedback', 'recommended_at'])
    
    # ========================================
    # SESSION MANAGEMENT OPTIMIZATION
    # ========================================
    
    # User sessions cleanup and security
    create_index_safe('idx_user_sessions_cleanup', 'user_sessions', 
                     ['expires_at', 'created_at'])
    create_index_safe('idx_user_sessions_security', 'user_sessions', 
                     ['user_id', 'ip_address', 'created_at'])
    
    # Password resets security and cleanup
    create_index_safe('idx_password_resets_security', 'password_resets', 
                     ['user_id', 'used', 'expires_at'])
    create_index_safe('idx_password_resets_cleanup', 'password_resets', 
                     ['expires_at', 'used'])
    
    # ========================================
    # JSON COLUMN OPTIMIZATION (MySQL)
    # ========================================
    
    # MySQL JSON indexes (MySQL 5.7+ supports JSON columns and functional indexes in 8.0+)
    try:
        # Note: MySQL doesn't have GIN indexes like PostgreSQL
        # We'll create regular indexes on JSON columns where possible
        
        # For MySQL 8.0+, we could use functional indexes, but for compatibility
        # we'll skip JSON column indexing or use generated columns if needed
        print("JSON column indexing skipped - MySQL doesn't support GIN indexes like PostgreSQL")
        print("Consider using generated columns for frequently queried JSON paths in MySQL 8.0+")
        
    except Exception as e:
        print(f"JSON indexing not supported in this MySQL version: {e}")
    
    # ========================================
    # PERFORMANCE MONITORING SETUP
    # ========================================
    
    # Create a view for performance monitoring (MySQL compatible)
    op.execute(text("""
        CREATE OR REPLACE VIEW performance_monitoring_summary AS
        SELECT 
            'interview_sessions' as table_name,
            COUNT(*) as total_rows,
            SUM(CASE WHEN created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) THEN 1 ELSE 0 END) as recent_rows,
            AVG(performance_score) as avg_performance_score,
            COUNT(DISTINCT user_id) as unique_users
        FROM interview_sessions
        WHERE status = 'completed'
        
        UNION ALL
        
        SELECT 
            'performance_metrics' as table_name,
            COUNT(*) as total_rows,
            SUM(CASE WHEN created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) THEN 1 ELSE 0 END) as recent_rows,
            AVG(content_quality_score) as avg_performance_score,
            COUNT(DISTINCT session_id) as unique_users
        FROM performance_metrics
        
        UNION ALL
        
        SELECT 
            'user_progress' as table_name,
            COUNT(*) as total_rows,
            SUM(CASE WHEN session_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) THEN 1 ELSE 0 END) as recent_rows,
            AVG(score) as avg_performance_score,
            COUNT(DISTINCT user_id) as unique_users
        FROM user_progress
    """))
    
    # Note: MySQL doesn't support stored functions the same way as PostgreSQL
    # We'll create a simple procedure instead
    try:
        op.execute(text("""
            DROP PROCEDURE IF EXISTS analyze_query_performance
        """))
        
        op.execute(text("""
            CREATE PROCEDURE analyze_query_performance()
            BEGIN
                -- This is a placeholder for query performance analysis
                -- In MySQL, we would use performance_schema for query analysis
                SELECT 
                    'session_queries' as query_type,
                    0.0 as avg_execution_time,
                    0 as total_calls,
                    'Monitor session-related queries using performance_schema' as recommendation;
            END
        """))
    except Exception as e:
        print(f"Could not create stored procedure: {e}")


def downgrade() -> None:
    """Remove comprehensive database optimization indexes"""
    
    # Drop performance monitoring objects
    try:
        op.execute(text("DROP VIEW IF EXISTS performance_monitoring_summary"))
    except Exception as e:
        print(f"Could not drop view: {e}")
    
    try:
        op.execute(text("DROP PROCEDURE IF EXISTS analyze_query_performance"))
    except Exception as e:
        print(f"Could not drop procedure: {e}")
    
    # Drop all optimization indexes
    indexes_to_drop = [
        # Core performance indexes
        'idx_users_email_active_optimized',
        'idx_users_role_hierarchy_lookup',
        'idx_users_last_login_active',
        'idx_users_created_updated',
        
        # Session indexes
        'idx_sessions_user_status_date_optimized',
        'idx_sessions_performance_analysis',
        'idx_sessions_session_continuity',
        'idx_sessions_role_performance',
        
        # Performance metrics indexes
        'idx_metrics_session_analysis_optimized',
        'idx_metrics_comprehensive_scores',
        'idx_metrics_response_time_analysis',
        'idx_metrics_question_performance',
        
        # User progress indexes
        'idx_progress_user_metric_date_optimized',
        'idx_progress_trend_analysis',
        'idx_progress_recommendations_lookup',
        
        # Role hierarchy indexes
        'idx_role_hierarchy_complete_lookup',
        'idx_role_hierarchy_tech_stack',
        
        # Questions indexes
        'idx_questions_role_difficulty_type',
        'idx_questions_generation_lookup',
        
        # Specialized indexes
        'idx_sessions_active_user_performance',
        'idx_sessions_completed_with_metrics',
        'idx_sessions_recent_performance',
        
        # Composite indexes
        'idx_user_session_performance_trend',
        'idx_metrics_aggregation_optimized',
        'idx_progress_comprehensive_tracking',
        
        # Learning resources indexes
        'idx_resources_recommendation_lookup',
        'idx_resources_provider_ranking',
        
        # User recommendations indexes
        'idx_user_recommendations_analytics',
        'idx_user_recommendations_engagement',
        
        # Session management indexes
        'idx_user_sessions_cleanup',
        'idx_user_sessions_security',
        'idx_password_resets_security',
        'idx_password_resets_cleanup',
    ]
    
    for index_name in indexes_to_drop:
        try:
            op.execute(text(f"DROP INDEX {index_name} ON {get_table_for_index(index_name)}"))
        except Exception as e:
            print(f"Could not drop index {index_name}: {e}")


def get_table_for_index(index_name):
    """Helper function to get table name from index name"""
    if 'users' in index_name:
        return 'users'
    elif 'sessions' in index_name:
        return 'interview_sessions'
    elif 'metrics' in index_name:
        return 'performance_metrics'
    elif 'progress' in index_name:
        return 'user_progress'
    elif 'role_hierarchy' in index_name:
        return 'role_hierarchy'
    elif 'questions' in index_name:
        return 'questions'
    elif 'resources' in index_name:
        return 'learning_resources'
    elif 'recommendations' in index_name:
        return 'user_recommendations'
    elif 'user_sessions' in index_name:
        return 'user_sessions'
    elif 'password_resets' in index_name:
        return 'password_resets'
    else:
        return 'unknown_table'