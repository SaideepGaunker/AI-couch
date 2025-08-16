"""
Question caching utilities for improved performance
"""
from typing import Dict, List, Any, Optional
import json
import hashlib
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class QuestionCache:
    """In-memory cache for frequently accessed questions"""
    
    def __init__(self, ttl_minutes: int = 60):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def _generate_key(self, **kwargs) -> str:
        """Generate cache key from parameters"""
        key_data = json.dumps(kwargs, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, **kwargs) -> Optional[List[Dict[str, Any]]]:
        """Get cached questions"""
        key = self._generate_key(**kwargs)
        
        if key in self.cache:
            cache_entry = self.cache[key]
            if datetime.utcnow() - cache_entry['timestamp'] < self.ttl:
                logger.debug(f"Cache hit for key: {key}")
                return cache_entry['data']
            else:
                # Remove expired entry
                del self.cache[key]
                logger.debug(f"Cache expired for key: {key}")
        
        return None
    
    def set(self, data: List[Dict[str, Any]], **kwargs) -> None:
        """Cache questions"""
        key = self._generate_key(**kwargs)
        self.cache[key] = {
            'data': data,
            'timestamp': datetime.utcnow()
        }
        logger.debug(f"Cached data for key: {key}")
    
    def clear(self) -> None:
        """Clear all cached data"""
        self.cache.clear()
        logger.info("Question cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_entries = len(self.cache)
        expired_entries = 0
        
        current_time = datetime.utcnow()
        for entry in self.cache.values():
            if current_time - entry['timestamp'] >= self.ttl:
                expired_entries += 1
        
        return {
            'total_entries': total_entries,
            'active_entries': total_entries - expired_entries,
            'expired_entries': expired_entries,
            'cache_size_mb': self._calculate_cache_size()
        }
    
    def _calculate_cache_size(self) -> float:
        """Calculate approximate cache size in MB"""
        try:
            cache_str = json.dumps(self.cache)
            size_bytes = len(cache_str.encode('utf-8'))
            return round(size_bytes / (1024 * 1024), 2)
        except Exception:
            return 0.0


# Global cache instance
question_cache = QuestionCache(ttl_minutes=30)