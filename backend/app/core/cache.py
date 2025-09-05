"""
Caching service with Redis fallback to in-memory storage
"""
import json
import time
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)

class CacheService:
    """Unified caching service with Redis and in-memory fallback"""
    
    def __init__(self):
        self.redis_client = None
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_stats = {"hits": 0, "misses": 0, "sets": 0}
        
        # Try to initialize Redis if enabled
        if settings.REDIS_ENABLED:
            try:
                import redis
                self.redis_client = redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    retry_on_timeout=True
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Redis cache initialized successfully")
            except Exception as e:
                logger.warning(f"Redis not available, using in-memory cache: {e}")
                self.redis_client = None
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self.redis_client:
                value = self.redis_client.get(key)
                if value:
                    self.cache_stats["hits"] += 1
                    return json.loads(value)
            else:
                # In-memory cache
                if key in self.memory_cache:
                    cache_entry = self.memory_cache[key]
                    if cache_entry["expires_at"] > time.time():
                        self.cache_stats["hits"] += 1
                        return cache_entry["value"]
                    else:
                        # Expired, remove it
                        del self.memory_cache[key]
            
            self.cache_stats["misses"] += 1
            return None
            
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            self.cache_stats["misses"] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache with TTL"""
        try:
            ttl = ttl or settings.CACHE_TTL
            
            if self.redis_client:
                serialized_value = json.dumps(value, default=str)
                self.redis_client.setex(key, ttl, serialized_value)
            else:
                # In-memory cache
                self.memory_cache[key] = {
                    "value": value,
                    "expires_at": time.time() + ttl
                }
            
            self.cache_stats["sets"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            if self.redis_client:
                return bool(self.redis_client.delete(key))
            else:
                return bool(self.memory_cache.pop(key, None))
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def clear(self) -> bool:
        """Clear all cache"""
        try:
            if self.redis_client:
                self.redis_client.flushdb()
            else:
                self.memory_cache.clear()
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    def cleanup_expired(self):
        """Clean up expired entries from in-memory cache"""
        if not self.redis_client:
            current_time = time.time()
            expired_keys = [
                key for key, entry in self.memory_cache.items()
                if entry["expires_at"] <= current_time
            ]
            for key in expired_keys:
                del self.memory_cache[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.cache_stats["hits"] + self.cache_stats["misses"]
        hit_rate = (self.cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "backend": "redis" if self.redis_client else "memory",
            "hits": self.cache_stats["hits"],
            "misses": self.cache_stats["misses"],
            "sets": self.cache_stats["sets"],
            "hit_rate": round(hit_rate, 2),
            "memory_entries": len(self.memory_cache) if not self.redis_client else "N/A"
        }


class SessionManager:
    """Improved session management with caching"""
    
    def __init__(self, cache_service: CacheService):
        self.cache = cache_service
        self.active_sessions: Dict[int, Dict[str, Any]] = {}
        self.last_cleanup = time.time()
    
    def create_session(self, session_id: int, session_data: Dict[str, Any]) -> bool:
        """Create a new session"""
        try:
            session_key = f"session:{session_id}"
            session_data["created_at"] = datetime.utcnow().isoformat()
            session_data["last_activity"] = datetime.utcnow().isoformat()
            
            # Store in cache
            self.cache.set(session_key, session_data, settings.SESSION_CACHE_TTL)
            
            # Also keep in memory for quick access
            self.active_sessions[session_id] = session_data
            
            logger.info(f"Created session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating session {session_id}: {e}")
            return False
    
    def get_session(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get session data"""
        try:
            # Try memory first
            if session_id in self.active_sessions:
                return self.active_sessions[session_id]
            
            # Try cache
            session_key = f"session:{session_id}"
            session_data = self.cache.get(session_key)
            
            if session_data:
                # Update memory cache
                self.active_sessions[session_id] = session_data
                return session_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None
    
    def update_session(self, session_id: int, updates: Dict[str, Any]) -> bool:
        """Update session data"""
        try:
            session_data = self.get_session(session_id)
            if not session_data:
                return False
            
            session_data.update(updates)
            session_data["last_activity"] = datetime.utcnow().isoformat()
            
            # Update cache
            session_key = f"session:{session_id}"
            self.cache.set(session_key, session_data, settings.SESSION_CACHE_TTL)
            
            # Update memory
            self.active_sessions[session_id] = session_data
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating session {session_id}: {e}")
            return False
    
    def delete_session(self, session_id: int) -> bool:
        """Delete session"""
        try:
            session_key = f"session:{session_id}"
            self.cache.delete(session_key)
            self.active_sessions.pop(session_id, None)
            
            logger.info(f"Deleted session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False
    
    def cleanup_sessions(self):
        """Clean up expired sessions"""
        try:
            current_time = time.time()
            
            # Only run cleanup every hour
            if current_time - self.last_cleanup < settings.SESSION_CLEANUP_INTERVAL:
                return
            
            expired_sessions = []
            cutoff_time = datetime.utcnow() - timedelta(seconds=settings.SESSION_CACHE_TTL)
            
            for session_id, session_data in list(self.active_sessions.items()):
                try:
                    last_activity = datetime.fromisoformat(session_data.get("last_activity", ""))
                    if last_activity < cutoff_time:
                        expired_sessions.append(session_id)
                except (ValueError, TypeError):
                    # Invalid timestamp, consider expired
                    expired_sessions.append(session_id)
            
            # Remove expired sessions
            for session_id in expired_sessions:
                self.delete_session(session_id)
            
            self.last_cleanup = current_time
            
            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
                
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
    
    def get_user_sessions(self, user_id: int) -> List[int]:
        """Get all active sessions for a user"""
        user_sessions = []
        for session_id, session_data in self.active_sessions.items():
            if session_data.get("user_id") == user_id:
                user_sessions.append(session_id)
        return user_sessions
    
    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        return {
            "active_sessions": len(self.active_sessions),
            "cache_stats": self.cache.get_stats()
        }


# Global instances
cache_service = CacheService()
session_manager = SessionManager(cache_service)