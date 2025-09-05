#!/usr/bin/env python3
"""
Database Maintenance Scripts for Interview Coach Application

This module provides comprehensive database maintenance functionality including:
- Index optimization and analysis
- Query performance monitoring
- Database cleanup operations
- Performance statistics collection
- Automated maintenance tasks

Usage:
    python database_maintenance.py --analyze-indexes
    python database_maintenance.py --optimize-performance
    python database_maintenance.py --cleanup-old-data
    python database_maintenance.py --full-maintenance
"""

import argparse
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import asyncio

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text, inspect, create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.db.database import Base
from app.db.models import *
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('database_maintenance.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class DatabaseMaintenanceManager:
    """Comprehensive database maintenance and optimization manager"""
    
    def __init__(self):
        # Create engine and session
        self.engine = create_engine(settings.DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = SessionLocal()
        self.inspector = inspect(self.engine)
    
    def analyze_table_sizes(self) -> Dict[str, Dict]:
        """Analyze table sizes and row counts"""
        logger.info("Analyzing table sizes and statistics...")
        
        tables_info = {}
        
        # Get all table names
        table_names = self.inspector.get_table_names()
        
        for table_name in table_names:
            try:
                # Get row count
                result = self.db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                row_count = result.scalar()
                
                # Get table size (PostgreSQL specific)
                try:
                    size_result = self.db.execute(text(f"""
                        SELECT 
                            pg_size_pretty(pg_total_relation_size('{table_name}')) as total_size,
                            pg_size_pretty(pg_relation_size('{table_name}')) as table_size,
                            pg_size_pretty(pg_total_relation_size('{table_name}') - pg_relation_size('{table_name}')) as index_size
                    """))
                    size_info = size_result.fetchone()
                    
                    tables_info[table_name] = {
                        'row_count': row_count,
                        'total_size': size_info[0] if size_info else 'N/A',
                        'table_size': size_info[1] if size_info else 'N/A',
                        'index_size': size_info[2] if size_info else 'N/A'
                    }
                except Exception as e:
                    # Fallback for non-PostgreSQL databases
                    tables_info[table_name] = {
                        'row_count': row_count,
                        'total_size': 'N/A',
                        'table_size': 'N/A',
                        'index_size': 'N/A'
                    }
                    
            except Exception as e:
                logger.error(f"Error analyzing table {table_name}: {e}")
                tables_info[table_name] = {'error': str(e)}
        
        return tables_info
    
    def analyze_index_usage(self) -> Dict[str, Dict]:
        """Analyze index usage statistics"""
        logger.info("Analyzing index usage statistics...")
        
        try:
            # MySQL specific index usage query using information_schema
            query = text("""
                SELECT 
                    TABLE_SCHEMA as schema_name,
                    TABLE_NAME as table_name,
                    INDEX_NAME as index_name,
                    CARDINALITY,
                    CASE 
                        WHEN INDEX_NAME = 'PRIMARY' THEN 'PRIMARY_KEY'
                        WHEN NON_UNIQUE = 0 THEN 'UNIQUE'
                        ELSE 'REGULAR'
                    END as index_type
                FROM information_schema.STATISTICS 
                WHERE TABLE_SCHEMA = DATABASE()
                AND TABLE_NAME NOT LIKE 'alembic%'
                ORDER BY TABLE_NAME, INDEX_NAME;
            """)
            
            result = self.db.execute(query)
            indexes = result.fetchall()
            
            index_stats = {}
            for row in indexes:
                index_name = row[2]
                index_stats[index_name] = {
                    'schema': row[0],
                    'table': row[1],
                    'cardinality': row[3],
                    'index_type': row[4],
                    'usage_category': 'UNKNOWN'  # MySQL doesn't provide usage stats like PostgreSQL
                }
            
            return index_stats
            
        except Exception as e:
            logger.warning(f"Could not analyze index usage: {e}")
            return {}
    
    def analyze_query_performance(self) -> List[Dict]:
        """Analyze slow queries and performance bottlenecks"""
        logger.info("Analyzing query performance...")
        
        try:
            # Check if performance_schema is enabled in MySQL
            check_performance_schema = text("""
                SELECT @@performance_schema;
            """)
            
            performance_schema_enabled = self.db.execute(check_performance_schema).scalar()
            
            if not performance_schema_enabled:
                logger.warning("performance_schema is not enabled in MySQL")
                return []
            
            # Get slow queries from performance_schema (MySQL 5.6+)
            query = text("""
                SELECT 
                    DIGEST_TEXT as query_text,
                    COUNT_STAR as exec_count,
                    SUM_TIMER_WAIT/1000000000000 as total_time_sec,
                    AVG_TIMER_WAIT/1000000000000 as avg_time_sec,
                    MAX_TIMER_WAIT/1000000000000 as max_time_sec,
                    SUM_ROWS_EXAMINED as rows_examined,
                    SUM_ROWS_SENT as rows_sent
                FROM performance_schema.events_statements_summary_by_digest 
                WHERE DIGEST_TEXT IS NOT NULL
                AND DIGEST_TEXT NOT LIKE '%performance_schema%'
                AND DIGEST_TEXT NOT LIKE '%information_schema%'
                ORDER BY AVG_TIMER_WAIT DESC 
                LIMIT 20;
            """)
            
            result = self.db.execute(query)
            slow_queries = []
            
            for row in result.fetchall():
                if row[0]:  # Check if query_text is not None
                    slow_queries.append({
                        'query': row[0][:200] + '...' if len(row[0]) > 200 else row[0],
                        'calls': row[1],
                        'total_time': round(row[2], 2) if row[2] else 0,
                        'mean_time': round(row[3], 2) if row[3] else 0,
                        'max_time': round(row[4], 2) if row[4] else 0,
                        'rows_examined': row[5] if row[5] else 0,
                        'rows_sent': row[6] if row[6] else 0
                    })
            
            return slow_queries
            
        except Exception as e:
            logger.warning(f"Could not analyze query performance: {e}")
            return []
    
    def optimize_database_performance(self) -> Dict[str, str]:
        """Run database optimization operations"""
        logger.info("Running database optimization operations...")
        
        optimization_results = {}
        
        try:
            # Update table statistics (MySQL equivalent)
            logger.info("Updating table statistics...")
            
            # Get all table names
            tables_result = self.db.execute(text("""
                SELECT TABLE_NAME FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_TYPE = 'BASE TABLE'
                AND TABLE_NAME NOT LIKE 'alembic%'
            """))
            
            tables = [row[0] for row in tables_result.fetchall()]
            
            # Run ANALYZE TABLE for each table
            for table in tables:
                try:
                    self.db.execute(text(f"ANALYZE TABLE {table}"))
                    logger.info(f"Analyzed table: {table}")
                except Exception as table_error:
                    logger.warning(f"Could not analyze table {table}: {table_error}")
            
            optimization_results['analyze'] = "SUCCESS"
            
        except Exception as e:
            logger.error(f"Error running ANALYZE: {e}")
            optimization_results['analyze'] = f"ERROR: {e}"
        
        try:
            # MySQL doesn't have VACUUM, but we can optimize tables
            logger.info("Optimizing tables (MySQL equivalent of VACUUM)...")
            self.db.commit()
            
            # Get all table names again
            tables_result = self.db.execute(text("""
                SELECT TABLE_NAME FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_TYPE = 'BASE TABLE'
                AND TABLE_NAME NOT LIKE 'alembic%'
            """))
            
            tables = [row[0] for row in tables_result.fetchall()]
            
            # Run OPTIMIZE TABLE for each table (be careful in production)
            for table in tables:
                try:
                    self.db.execute(text(f"OPTIMIZE TABLE {table}"))
                    logger.info(f"Optimized table: {table}")
                except Exception as table_error:
                    logger.warning(f"Could not optimize table {table}: {table_error}")
            
            optimization_results['optimize'] = "SUCCESS"
            
        except Exception as e:
            logger.error(f"Error running OPTIMIZE: {e}")
            optimization_results['optimize'] = f"ERROR: {e}"
        
        try:
            # Reindex if needed (be careful with this in production)
            logger.info("Checking for index bloat...")
            # This is a simplified check - in production, use more sophisticated bloat detection
            optimization_results['reindex'] = "SKIPPED - Manual review recommended"
            
        except Exception as e:
            logger.error(f"Error checking indexes: {e}")
            optimization_results['reindex'] = f"ERROR: {e}"
        
        return optimization_results
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> Dict[str, int]:
        """Clean up old data based on retention policies"""
        logger.info(f"Cleaning up data older than {days_to_keep} days...")
        
        cleanup_results = {}
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        try:
            # Clean up old password reset tokens
            old_resets = self.db.query(PasswordReset).filter(
                PasswordReset.expires_at < cutoff_date
            )
            count = old_resets.count()
            old_resets.delete()
            cleanup_results['password_resets'] = count
            
        except Exception as e:
            logger.error(f"Error cleaning password resets: {e}")
            cleanup_results['password_resets'] = f"ERROR: {e}"
        
        try:
            # Clean up expired user sessions
            old_sessions = self.db.query(UserSession).filter(
                UserSession.expires_at < datetime.now()
            )
            count = old_sessions.count()
            old_sessions.delete()
            cleanup_results['user_sessions'] = count
            
        except Exception as e:
            logger.error(f"Error cleaning user sessions: {e}")
            cleanup_results['user_sessions'] = f"ERROR: {e}"
        
        try:
            # Archive old performance metrics (instead of deleting)
            # This is a placeholder - implement archiving logic as needed
            old_metrics_count = self.db.query(PerformanceMetrics).filter(
                PerformanceMetrics.created_at < cutoff_date
            ).count()
            cleanup_results['performance_metrics'] = f"FOUND {old_metrics_count} old records (archiving recommended)"
            
        except Exception as e:
            logger.error(f"Error checking performance metrics: {e}")
            cleanup_results['performance_metrics'] = f"ERROR: {e}"
        
        try:
            self.db.commit()
            logger.info("Data cleanup completed successfully")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error committing cleanup changes: {e}")
        
        return cleanup_results
    
    def generate_performance_report(self) -> Dict:
        """Generate comprehensive performance report"""
        logger.info("Generating comprehensive performance report...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'table_analysis': self.analyze_table_sizes(),
            'index_usage': self.analyze_index_usage(),
            'slow_queries': self.analyze_query_performance(),
        }
        
        # Add summary statistics
        try:
            # Get recent activity statistics
            recent_sessions = self.db.query(InterviewSession).filter(
                InterviewSession.created_at >= datetime.now() - timedelta(days=7)
            ).count()
            
            recent_metrics = self.db.query(PerformanceMetrics).filter(
                PerformanceMetrics.created_at >= datetime.now() - timedelta(days=7)
            ).count()
            
            active_users = self.db.query(User).filter(
                User.is_active == True,
                User.last_login >= datetime.now() - timedelta(days=30)
            ).count()
            
            report['summary'] = {
                'recent_sessions_7d': recent_sessions,
                'recent_metrics_7d': recent_metrics,
                'active_users_30d': active_users,
            }
            
        except Exception as e:
            logger.error(f"Error generating summary statistics: {e}")
            report['summary'] = {'error': str(e)}
        
        return report
    
    def run_maintenance_checks(self) -> Dict:
        """Run comprehensive maintenance checks"""
        logger.info("Running comprehensive maintenance checks...")
        
        checks = {}
        
        # Check for missing indexes on foreign keys
        try:
            missing_fk_indexes = []
            for table_name in self.inspector.get_table_names():
                fks = self.inspector.get_foreign_keys(table_name)
                indexes = self.inspector.get_indexes(table_name)
                
                for fk in fks:
                    fk_columns = fk['constrained_columns']
                    # Check if there's an index starting with these columns
                    has_index = any(
                        idx['column_names'][:len(fk_columns)] == fk_columns
                        for idx in indexes
                    )
                    if not has_index:
                        missing_fk_indexes.append({
                            'table': table_name,
                            'columns': fk_columns,
                            'referenced_table': fk['referred_table']
                        })
            
            checks['missing_fk_indexes'] = missing_fk_indexes
            
        except Exception as e:
            logger.error(f"Error checking foreign key indexes: {e}")
            checks['missing_fk_indexes'] = f"ERROR: {e}"
        
        # Check for unused indexes
        try:
            index_usage = self.analyze_index_usage()
            unused_indexes = [
                name for name, stats in index_usage.items()
                if stats.get('usage_category') == 'UNUSED'
            ]
            checks['unused_indexes'] = unused_indexes
            
        except Exception as e:
            logger.error(f"Error checking unused indexes: {e}")
            checks['unused_indexes'] = f"ERROR: {e}"
        
        return checks
    
    def close(self):
        """Close database connection"""
        self.db.close()


def main():
    """Main function to run database maintenance operations"""
    parser = argparse.ArgumentParser(description='Database Maintenance Tool')
    parser.add_argument('--analyze-indexes', action='store_true',
                       help='Analyze index usage and performance')
    parser.add_argument('--optimize-performance', action='store_true',
                       help='Run database optimization operations')
    parser.add_argument('--cleanup-old-data', action='store_true',
                       help='Clean up old data based on retention policies')
    parser.add_argument('--generate-report', action='store_true',
                       help='Generate comprehensive performance report')
    parser.add_argument('--maintenance-checks', action='store_true',
                       help='Run maintenance checks for potential issues')
    parser.add_argument('--full-maintenance', action='store_true',
                       help='Run all maintenance operations')
    parser.add_argument('--retention-days', type=int, default=90,
                       help='Number of days to retain data (default: 90)')
    
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    maintenance_manager = DatabaseMaintenanceManager()
    
    try:
        if args.analyze_indexes or args.full_maintenance:
            logger.info("=== INDEX ANALYSIS ===")
            index_stats = maintenance_manager.analyze_index_usage()
            for index_name, stats in index_stats.items():
                if 'scans' in stats:
                    # PostgreSQL format
                    logger.info(f"Index {index_name}: {stats['usage_category']} "
                              f"({stats['scans']} scans)")
                else:
                    # MySQL format
                    logger.info(f"Index {index_name}: {stats['index_type']} on {stats['table']} "
                              f"(cardinality: {stats['cardinality']})")
        
        if args.optimize_performance or args.full_maintenance:
            logger.info("=== PERFORMANCE OPTIMIZATION ===")
            optimization_results = maintenance_manager.optimize_database_performance()
            for operation, result in optimization_results.items():
                logger.info(f"{operation.upper()}: {result}")
        
        if args.cleanup_old_data or args.full_maintenance:
            logger.info("=== DATA CLEANUP ===")
            cleanup_results = maintenance_manager.cleanup_old_data(args.retention_days)
            for table, count in cleanup_results.items():
                logger.info(f"Cleaned {table}: {count}")
        
        if args.generate_report or args.full_maintenance:
            logger.info("=== PERFORMANCE REPORT ===")
            report = maintenance_manager.generate_performance_report()
            
            # Print summary
            if 'summary' in report:
                summary = report['summary']
                logger.info(f"Recent sessions (7d): {summary.get('recent_sessions_7d', 'N/A')}")
                logger.info(f"Recent metrics (7d): {summary.get('recent_metrics_7d', 'N/A')}")
                logger.info(f"Active users (30d): {summary.get('active_users_30d', 'N/A')}")
            
            # Save detailed report to file
            import json
            report_filename = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"Detailed report saved to {report_filename}")
        
        if args.maintenance_checks or args.full_maintenance:
            logger.info("=== MAINTENANCE CHECKS ===")
            checks = maintenance_manager.run_maintenance_checks()
            
            if 'missing_fk_indexes' in checks and checks['missing_fk_indexes']:
                logger.warning("Missing foreign key indexes found:")
                for missing in checks['missing_fk_indexes']:
                    logger.warning(f"  Table {missing['table']}, columns {missing['columns']}")
            
            if 'unused_indexes' in checks and checks['unused_indexes']:
                logger.warning("Unused indexes found:")
                for unused in checks['unused_indexes']:
                    logger.warning(f"  {unused}")
    
    finally:
        maintenance_manager.close()
    
    logger.info("Database maintenance completed successfully")


if __name__ == "__main__":
    main()