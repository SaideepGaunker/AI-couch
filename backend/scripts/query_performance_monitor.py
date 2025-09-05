#!/usr/bin/env python3
"""
Query Performance Monitoring for Interview Coach Application

This module provides real-time query performance monitoring and analysis:
- Track slow queries and execution times
- Monitor database connection usage
- Analyze query patterns and bottlenecks
- Generate performance alerts and recommendations
- Provide query optimization suggestions

Usage:
    python query_performance_monitor.py --monitor
    python query_performance_monitor.py --analyze-slow-queries
    python query_performance_monitor.py --connection-stats
"""

import argparse
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import threading
from collections import defaultdict, deque

import os
import sys

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text, event, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from app.db.database import Base
from app.db.models import *
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('query_performance.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class QueryMetrics:
    """Data class for storing query performance metrics"""
    query_hash: str
    query_text: str
    execution_time: float
    timestamp: datetime
    connection_id: str
    rows_affected: int = 0
    error: Optional[str] = None


class QueryPerformanceMonitor:
    """Real-time query performance monitoring system"""
    
    def __init__(self, slow_query_threshold: float = 1.0):
        self.slow_query_threshold = slow_query_threshold
        self.query_metrics: deque = deque(maxlen=10000)  # Keep last 10k queries
        self.slow_queries: List[QueryMetrics] = []
        self.query_patterns: Dict[str, List[float]] = defaultdict(list)
        self.connection_stats: Dict[str, Dict] = defaultdict(dict)
        self.monitoring_active = False
        self.start_time = datetime.now()
        
        # Setup SQLAlchemy event listeners
        self._setup_event_listeners()
    
    def _setup_event_listeners(self):
        """Setup SQLAlchemy event listeners for query monitoring"""
        
        @event.listens_for(Engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Record query start time"""
            context._query_start_time = time.time()
            context._query_statement = statement
            context._query_parameters = parameters
        
        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Record query completion and metrics"""
            if hasattr(context, '_query_start_time'):
                execution_time = time.time() - context._query_start_time
                
                # Create query metrics
                query_hash = str(hash(statement))
                connection_id = str(id(conn))
                
                metrics = QueryMetrics(
                    query_hash=query_hash,
                    query_text=statement[:500],  # Truncate long queries
                    execution_time=execution_time,
                    timestamp=datetime.now(),
                    connection_id=connection_id,
                    rows_affected=cursor.rowcount if hasattr(cursor, 'rowcount') else 0
                )
                
                self._record_query_metrics(metrics)
        
        @event.listens_for(Engine, "handle_error")
        def handle_error(exception_context):
            """Record query errors"""
            if hasattr(exception_context.execution_context, '_query_start_time'):
                execution_time = time.time() - exception_context.execution_context._query_start_time
                
                query_hash = str(hash(exception_context.statement))
                connection_id = str(id(exception_context.connection))
                
                metrics = QueryMetrics(
                    query_hash=query_hash,
                    query_text=str(exception_context.statement)[:500],
                    execution_time=execution_time,
                    timestamp=datetime.now(),
                    connection_id=connection_id,
                    error=str(exception_context.original_exception)
                )
                
                self._record_query_metrics(metrics)
    
    def _record_query_metrics(self, metrics: QueryMetrics):
        """Record query metrics and analyze performance"""
        if not self.monitoring_active:
            return
        
        # Add to metrics collection
        self.query_metrics.append(metrics)
        
        # Track query patterns
        self.query_patterns[metrics.query_hash].append(metrics.execution_time)
        
        # Record slow queries
        if metrics.execution_time > self.slow_query_threshold:
            self.slow_queries.append(metrics)
            logger.warning(f"Slow query detected: {metrics.execution_time:.3f}s - {metrics.query_text[:100]}...")
        
        # Update connection stats
        conn_stats = self.connection_stats[metrics.connection_id]
        conn_stats['last_activity'] = metrics.timestamp
        conn_stats['query_count'] = conn_stats.get('query_count', 0) + 1
        conn_stats['total_time'] = conn_stats.get('total_time', 0) + metrics.execution_time
        
        if metrics.error:
            conn_stats['error_count'] = conn_stats.get('error_count', 0) + 1
    
    def start_monitoring(self):
        """Start query performance monitoring"""
        logger.info("Starting query performance monitoring...")
        self.monitoring_active = True
        self.start_time = datetime.now()
    
    def stop_monitoring(self):
        """Stop query performance monitoring"""
        logger.info("Stopping query performance monitoring...")
        self.monitoring_active = False
    
    def get_performance_summary(self) -> Dict:
        """Get comprehensive performance summary"""
        if not self.query_metrics:
            return {"message": "No query data available"}
        
        total_queries = len(self.query_metrics)
        slow_queries_count = len(self.slow_queries)
        
        # Calculate statistics
        execution_times = [m.execution_time for m in self.query_metrics]
        avg_execution_time = sum(execution_times) / len(execution_times)
        max_execution_time = max(execution_times)
        min_execution_time = min(execution_times)
        
        # Get top slow queries
        top_slow_queries = sorted(self.slow_queries, key=lambda x: x.execution_time, reverse=True)[:10]
        
        # Analyze query patterns
        pattern_analysis = {}
        for query_hash, times in self.query_patterns.items():
            if len(times) > 1:
                pattern_analysis[query_hash] = {
                    'count': len(times),
                    'avg_time': sum(times) / len(times),
                    'max_time': max(times),
                    'min_time': min(times)
                }
        
        # Connection statistics
        active_connections = len([
            conn_id for conn_id, stats in self.connection_stats.items()
            if stats.get('last_activity', datetime.min) > datetime.now() - timedelta(minutes=5)
        ])
        
        return {
            'monitoring_duration': str(datetime.now() - self.start_time),
            'total_queries': total_queries,
            'slow_queries_count': slow_queries_count,
            'slow_query_percentage': (slow_queries_count / total_queries * 100) if total_queries > 0 else 0,
            'avg_execution_time': round(avg_execution_time, 4),
            'max_execution_time': round(max_execution_time, 4),
            'min_execution_time': round(min_execution_time, 4),
            'active_connections': active_connections,
            'total_connections': len(self.connection_stats),
            'top_slow_queries': [
                {
                    'query': q.query_text[:200],
                    'execution_time': round(q.execution_time, 4),
                    'timestamp': q.timestamp.isoformat(),
                    'error': q.error
                }
                for q in top_slow_queries
            ],
            'query_patterns': {
                hash_id: {
                    'count': stats['count'],
                    'avg_time': round(stats['avg_time'], 4),
                    'max_time': round(stats['max_time'], 4)
                }
                for hash_id, stats in sorted(
                    pattern_analysis.items(),
                    key=lambda x: x[1]['avg_time'],
                    reverse=True
                )[:10]
            }
        }
    
    def analyze_slow_queries(self) -> List[Dict]:
        """Analyze slow queries and provide optimization recommendations"""
        if not self.slow_queries:
            return []
        
        analysis = []
        
        # Group slow queries by pattern
        query_groups = defaultdict(list)
        for query in self.slow_queries:
            # Simple grouping by first 100 characters
            pattern = query.query_text[:100].strip()
            query_groups[pattern].append(query)
        
        for pattern, queries in query_groups.items():
            avg_time = sum(q.execution_time for q in queries) / len(queries)
            max_time = max(q.execution_time for q in queries)
            
            # Generate recommendations based on query pattern
            recommendations = self._generate_query_recommendations(pattern, avg_time)
            
            analysis.append({
                'query_pattern': pattern,
                'occurrence_count': len(queries),
                'avg_execution_time': round(avg_time, 4),
                'max_execution_time': round(max_time, 4),
                'recommendations': recommendations,
                'sample_query': queries[0].query_text[:300]
            })
        
        return sorted(analysis, key=lambda x: x['avg_execution_time'], reverse=True)
    
    def _generate_query_recommendations(self, query_pattern: str, avg_time: float) -> List[str]:
        """Generate optimization recommendations for query patterns"""
        recommendations = []
        
        query_lower = query_pattern.lower()
        
        # Check for common performance issues
        if 'select *' in query_lower:
            recommendations.append("Avoid SELECT * - specify only needed columns")
        
        if 'where' not in query_lower and 'select' in query_lower:
            recommendations.append("Consider adding WHERE clause to limit result set")
        
        if 'order by' in query_lower and 'limit' not in query_lower:
            recommendations.append("Consider adding LIMIT clause when using ORDER BY")
        
        if 'join' in query_lower:
            recommendations.append("Ensure JOIN conditions use indexed columns")
        
        if 'like' in query_lower and query_lower.count('%') > 0:
            recommendations.append("LIKE with leading wildcards can't use indexes - consider full-text search")
        
        if avg_time > 5.0:
            recommendations.append("Query is very slow - consider query rewrite or additional indexes")
        elif avg_time > 2.0:
            recommendations.append("Query is slow - review execution plan and indexes")
        
        if not recommendations:
            recommendations.append("Review query execution plan for optimization opportunities")
        
        return recommendations
    
    def get_connection_statistics(self) -> Dict:
        """Get detailed connection statistics"""
        if not self.connection_stats:
            return {"message": "No connection data available"}
        
        stats = {
            'total_connections': len(self.connection_stats),
            'active_connections': 0,
            'connections_with_errors': 0,
            'avg_queries_per_connection': 0,
            'avg_time_per_connection': 0,
            'connection_details': []
        }
        
        total_queries = 0
        total_time = 0
        
        for conn_id, conn_stats in self.connection_stats.items():
            # Check if connection is active (activity in last 5 minutes)
            is_active = conn_stats.get('last_activity', datetime.min) > datetime.now() - timedelta(minutes=5)
            if is_active:
                stats['active_connections'] += 1
            
            if conn_stats.get('error_count', 0) > 0:
                stats['connections_with_errors'] += 1
            
            query_count = conn_stats.get('query_count', 0)
            conn_time = conn_stats.get('total_time', 0)
            
            total_queries += query_count
            total_time += conn_time
            
            stats['connection_details'].append({
                'connection_id': conn_id,
                'query_count': query_count,
                'total_time': round(conn_time, 4),
                'avg_time_per_query': round(conn_time / query_count, 4) if query_count > 0 else 0,
                'error_count': conn_stats.get('error_count', 0),
                'last_activity': conn_stats.get('last_activity', datetime.min).isoformat(),
                'is_active': is_active
            })
        
        if len(self.connection_stats) > 0:
            stats['avg_queries_per_connection'] = round(total_queries / len(self.connection_stats), 2)
            stats['avg_time_per_connection'] = round(total_time / len(self.connection_stats), 4)
        
        # Sort by total time descending
        stats['connection_details'].sort(key=lambda x: x['total_time'], reverse=True)
        
        return stats
    
    def export_metrics(self, filename: Optional[str] = None) -> str:
        """Export query metrics to JSON file"""
        if not filename:
            filename = f"query_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'monitoring_duration': str(datetime.now() - self.start_time),
            'performance_summary': self.get_performance_summary(),
            'slow_query_analysis': self.analyze_slow_queries(),
            'connection_statistics': self.get_connection_statistics(),
            'raw_metrics': [asdict(metric) for metric in list(self.query_metrics)]
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Query metrics exported to {filename}")
        return filename


def main():
    """Main function for query performance monitoring"""
    parser = argparse.ArgumentParser(description='Query Performance Monitor')
    parser.add_argument('--monitor', action='store_true',
                       help='Start real-time query monitoring')
    parser.add_argument('--analyze-slow-queries', action='store_true',
                       help='Analyze slow queries and provide recommendations')
    parser.add_argument('--connection-stats', action='store_true',
                       help='Show connection statistics')
    parser.add_argument('--export-metrics', action='store_true',
                       help='Export metrics to JSON file')
    parser.add_argument('--duration', type=int, default=60,
                       help='Monitoring duration in seconds (default: 60)')
    parser.add_argument('--slow-threshold', type=float, default=1.0,
                       help='Slow query threshold in seconds (default: 1.0)')
    
    args = parser.parse_args()
    
    if not any(vars(args).values()):
        parser.print_help()
        return
    
    monitor = QueryPerformanceMonitor(slow_query_threshold=args.slow_threshold)
    
    try:
        if args.monitor:
            logger.info(f"Starting query monitoring for {args.duration} seconds...")
            monitor.start_monitoring()
            
            # Monitor for specified duration
            time.sleep(args.duration)
            
            monitor.stop_monitoring()
            
            # Show summary
            summary = monitor.get_performance_summary()
            logger.info("=== MONITORING SUMMARY ===")
            logger.info(f"Total queries: {summary['total_queries']}")
            logger.info(f"Slow queries: {summary['slow_queries_count']} ({summary['slow_query_percentage']:.1f}%)")
            logger.info(f"Average execution time: {summary['avg_execution_time']}s")
            logger.info(f"Max execution time: {summary['max_execution_time']}s")
            logger.info(f"Active connections: {summary['active_connections']}")
        
        if args.analyze_slow_queries:
            logger.info("=== SLOW QUERY ANALYSIS ===")
            analysis = monitor.analyze_slow_queries()
            
            if not analysis:
                logger.info("No slow queries found")
            else:
                for i, query_analysis in enumerate(analysis[:5], 1):
                    logger.info(f"\n{i}. Query Pattern (avg: {query_analysis['avg_execution_time']}s):")
                    logger.info(f"   Occurrences: {query_analysis['occurrence_count']}")
                    logger.info(f"   Sample: {query_analysis['sample_query'][:150]}...")
                    logger.info("   Recommendations:")
                    for rec in query_analysis['recommendations']:
                        logger.info(f"   - {rec}")
        
        if args.connection_stats:
            logger.info("=== CONNECTION STATISTICS ===")
            conn_stats = monitor.get_connection_statistics()
            
            logger.info(f"Total connections: {conn_stats['total_connections']}")
            logger.info(f"Active connections: {conn_stats['active_connections']}")
            logger.info(f"Connections with errors: {conn_stats['connections_with_errors']}")
            logger.info(f"Avg queries per connection: {conn_stats['avg_queries_per_connection']}")
            logger.info(f"Avg time per connection: {conn_stats['avg_time_per_connection']}s")
        
        if args.export_metrics:
            filename = monitor.export_metrics()
            logger.info(f"Metrics exported to {filename}")
    
    except KeyboardInterrupt:
        logger.info("Monitoring interrupted by user")
        monitor.stop_monitoring()
    
    except Exception as e:
        logger.error(f"Error during monitoring: {e}")
        monitor.stop_monitoring()


if __name__ == "__main__":
    main()