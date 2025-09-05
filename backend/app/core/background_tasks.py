"""
Background tasks for maintenance and cleanup
"""
import asyncio
import logging
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.cache import cache_service, session_manager
from app.db.database import SessionLocal
from app.db.models import UserSession, PasswordReset

logger = logging.getLogger(__name__)


async def cleanup_expired_sessions():
    """Clean up expired user sessions from database"""
    try:
        db = SessionLocal()
        
        # Delete expired sessions
        cutoff_time = datetime.utcnow() - timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        expired_count = db.query(UserSession).filter(
            UserSession.expires_at < cutoff_time
        ).delete()
        
        db.commit()
        db.close()
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired user sessions")
            
    except Exception as e:
        logger.error(f"Error cleaning up expired sessions: {e}")


async def cleanup_expired_password_resets():
    """Clean up expired password reset tokens"""
    try:
        db = SessionLocal()
        
        # Delete expired password reset tokens
        expired_count = db.query(PasswordReset).filter(
            PasswordReset.expires_at < datetime.utcnow()
        ).delete()
        
        db.commit()
        db.close()
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired password reset tokens")
            
    except Exception as e:
        logger.error(f"Error cleaning up expired password resets: {e}")


async def cleanup_cache():
    """Clean up expired cache entries"""
    try:
        cache_service.cleanup_expired()
        logger.debug("Cache cleanup completed")
    except Exception as e:
        logger.error(f"Error during cache cleanup: {e}")


async def cleanup_session_manager():
    """Clean up expired session manager entries"""
    try:
        session_manager.cleanup_sessions()
        logger.debug("Session manager cleanup completed")
    except Exception as e:
        logger.error(f"Error during session manager cleanup: {e}")


async def log_system_stats():
    """Log system statistics"""
    try:
        # Cache stats
        cache_stats = cache_service.get_stats()
        logger.info(f"Cache stats: {cache_stats}")
        
        # Session stats
        session_stats = session_manager.get_stats()
        logger.info(f"Session stats: {session_stats}")
        
        # Database connection pool stats
        from app.db.database import engine
        pool = engine.pool
        logger.info(
            f"DB Pool stats: size={pool.size()}, "
            f"checked_in={pool.checkedin()}, "
            f"checked_out={pool.checkedout()}, "
            f"overflow={pool.overflow()}"
        )
        
    except Exception as e:
        logger.error(f"Error logging system stats: {e}")


async def periodic_maintenance():
    """Run periodic maintenance tasks"""
    logger.info("Starting periodic maintenance")
    
    tasks = [
        cleanup_expired_sessions(),
        cleanup_expired_password_resets(),
        cleanup_cache(),
        cleanup_session_manager(),
        log_system_stats()
    ]
    
    # Run all tasks concurrently
    await asyncio.gather(*tasks, return_exceptions=True)
    
    logger.info("Periodic maintenance completed")


async def start_background_tasks():
    """Start all background tasks"""
    logger.info("Starting background tasks")
    
    while True:
        try:
            # Run maintenance every hour
            await periodic_maintenance()
            
            # Wait for next cycle
            await asyncio.sleep(3600)  # 1 hour
            
        except asyncio.CancelledError:
            logger.info("Background tasks cancelled")
            break
        except Exception as e:
            logger.error(f"Error in background tasks: {e}")
            # Wait a bit before retrying
            await asyncio.sleep(300)  # 5 minutes


async def emergency_cleanup():
    """Emergency cleanup for critical situations"""
    logger.warning("Running emergency cleanup")
    
    try:
        # Clear all caches
        cache_service.clear()
        
        # Clear session manager
        session_manager.active_sessions.clear()
        
        # Force garbage collection
        import gc
        gc.collect()
        
        logger.info("Emergency cleanup completed")
        
    except Exception as e:
        logger.error(f"Error during emergency cleanup: {e}")


# Health check for background tasks
class BackgroundTasksHealth:
    def __init__(self):
        self.last_maintenance = None
        self.maintenance_count = 0
        self.error_count = 0
    
    def record_maintenance(self):
        self.last_maintenance = datetime.utcnow()
        self.maintenance_count += 1
    
    def record_error(self):
        self.error_count += 1
    
    def get_health_status(self):
        if not self.last_maintenance:
            return {"status": "starting", "message": "Background tasks not yet started"}
        
        time_since_last = datetime.utcnow() - self.last_maintenance
        
        if time_since_last > timedelta(hours=2):
            return {
                "status": "unhealthy",
                "message": f"No maintenance for {time_since_last}",
                "last_maintenance": self.last_maintenance.isoformat()
            }
        
        return {
            "status": "healthy",
            "maintenance_count": self.maintenance_count,
            "error_count": self.error_count,
            "last_maintenance": self.last_maintenance.isoformat()
        }


# Global health tracker
background_health = BackgroundTasksHealth()