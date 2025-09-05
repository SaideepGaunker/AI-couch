"""
Database Query Performance Monitoring Utility
"""
import time
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

# Configure logging for query monitoring
query_logger = logging.getLogger('query_performance')
query_logger.setLevel(logging.INFO)

# Create handler if it doesn't exist
if not query_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    query_logger.addHandler(handler)


class QueryPerformanceMonitor:
    """Monitor and log database query performance"""
    
    def __init__(self):
        self.slow_query_threshold = 1.0  # seconds
        self.query_stats = {}
        self.enabled = True
    
    def enable_monitoring(self, engine: Engine):
        """Enable query performance monitoring on SQLAlchemy engine"""
        
        @event.listens_for(engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            if self.enabled:
                context._query_start_time = time.time()
                context._query_statement = statement
        
        @event.listens_for(engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            if self.enabled and hasattr(context, '_query_start_time'):
                total_time = time.time() - context._query_start_time
                
                # Log slow queries
                if total_time > self.slow_query_threshold:
                    query_logger.warning(
                        f"Slow query detected: {total_time:.3f}s - {statement[:100]}..."
                    )
                
                # Update query statistics
                self._update_query_stats(statement, total_time)
    
    def _update_query_stats(self, statement: str, execution_time: float):
        """Update query statistics"""
        
        # Extract query type (SELECT, INSERT, UPDATE, DELETE)
        query_type = statement.strip().split()[0].upper()
        
        if query_type not in self.query_stats:
            self.query_stats[query_type] = {
                'count': 0,
                'total_time': 0.0,
                'avg_time': 0.0,
                'max_time': 0.0,
                'min_time': float('inf')
            }
        
        stats = self.query_stats[query_type]
        stats['count'] += 1
        stats['total_time'] += execution_time
        stats['avg_time'] = stats['total_time'] / stats['count']
        stats['max_time'] = max(stats['max_time'], execution_time)
        stats['min_time'] = min(stats['min_time'], execution_time)
    
    def get_query_stats(self) -> Dict[str, Any]:
        """Get current query statistics"""
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'slow_query_threshold': self.slow_query_threshold,
            'query_stats': self.query_stats.copy()
        }
    
    def reset_stats(self):
        """Reset query statistics"""
        self.query_stats.clear()
    
    def set_slow_query_threshold(self, threshold: float):
        """Set the threshold for slow query detection"""
        self.slow_query_threshold = threshold
    
    def disable_monitoring(self):
        """Disable query monitoring"""
        self.enabled = False
    
    def enable_monitoring_flag(self):
        """Enable query monitoring"""
        self.enabled = True


# Global query monitor instance
query_monitor = QueryPerformanceMonitor()


def monitor_query_performance(func: Callable) -> Callable:
    """Decorator to monitor individual function query performance"""
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not query_monitor.enabled:
            return func(*args, **kwargs)
        
        start_time = time.time()
        function_name = f"{func.__module__}.{func.__name__}"
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            if execution_time > query_monitor.slow_query_threshold:
                query_logger.warning(
                    f"Slow function execution: {function_name} took {execution_time:.3f}s"
                )
            
            return result
        
        except Exception as e:
            execution_time = time.time() - start_time
            query_logger.error(
                f"Function {function_name} failed after {execution_time:.3f}s: {str(e)}"
            )
            raise
    
    return wrapper


class DatabaseConnectionMonitor:
    """Monitor database connection pool performance"""
    
    def __init__(self):
        self.connection_stats = {
            'total_connections': 0,
            'active_connections': 0,
            'pool_size': 0,
            'checked_out': 0,
            'overflow': 0,
            'checked_in': 0
        }
    
    def enable_pool_monitoring(self, engine: Engine):
        """Enable connection pool monitoring"""
        
        @event.listens_for(Pool, "connect")
        def receive_connect(dbapi_connection, connection_record):
            self.connection_stats['total_connections'] += 1
            query_logger.info("New database connection established")
        
        @event.listens_for(Pool, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            self.connection_stats['checked_out'] += 1
        
        @event.listens_for(Pool, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            self.connection_stats['checked_in'] += 1
    
    def get_pool_status(self, engine: Engine) -> Dict[str, Any]:
        """Get current connection pool status"""
        
        pool = engine.pool
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'pool_size': pool.size(),
            'checked_out_connections': pool.checkedout(),
            'overflow_connections': pool.overflow(),
            'checked_in_connections': pool.checkedin(),
            'total_connections_created': self.connection_stats['total_connections'],
            'total_checkouts': self.connection_stats['checked_out'],
            'total_checkins': self.connection_stats['checked_in']
        }


# Global connection monitor instance
connection_monitor = DatabaseConnectionMonitor()


def setup_database_monitoring(engine: Engine):
    """Setup comprehensive database monitoring"""
    
    query_logger.info("Setting up database performance monitoring...")
    
    # Enable query performance monitoring
    query_monitor.enable_monitoring(engine)
    
    # Enable connection pool monitoring
    connection_monitor.enable_pool_monitoring(engine)
    
    query_logger.info("Database monitoring enabled successfully")


def get_performance_metrics(engine: Engine) -> Dict[str, Any]:
    """Get comprehensive performance metrics"""
    
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'query_performance': query_monitor.get_query_stats(),
        'connection_pool': connection_monitor.get_pool_status(engine)
    }


def log_performance_summary():
    """Log a summary of performance metrics"""
    
    stats = query_monitor.get_query_stats()
    
    if stats['query_stats']:
        query_logger.info("=== Query Performance Summary ===")
        
        for query_type, metrics in stats['query_stats'].items():
            query_logger.info(
                f"{query_type}: {metrics['count']} queries, "
                f"avg: {metrics['avg_time']:.3f}s, "
                f"max: {metrics['max_time']:.3f}s"
            )
    else:
        query_logger.info("No query statistics available")


# Example usage functions for testing
@monitor_query_performance
def example_slow_function():
    """Example function that might be slow"""
    time.sleep(0.1)  # Simulate some work
    return "completed"


@monitor_query_performance
def example_database_operation(db_session):
    """Example database operation with monitoring"""
    # This would contain actual database operations
    # The decorator will monitor the execution time
    pass