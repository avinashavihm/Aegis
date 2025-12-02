"""Service for data caching"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import time

class Cache:
    """Simple in-memory cache with TTL"""
    
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
    
    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Set a cache entry"""
        entry = {
            "value": value,
            "created_at": datetime.utcnow(),
            "ttl_seconds": ttl_seconds
        }
        if ttl_seconds:
            entry["expires_at"] = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        self.cache[key] = entry
    
    def get(self, key: str) -> Optional[Any]:
        """Get a cache entry"""
        entry = self.cache.get(key)
        if not entry:
            return None
        
        # Check if expired
        if "expires_at" in entry:
            if datetime.utcnow() > entry["expires_at"]:
                del self.cache[key]
                return None
        
        return entry["value"]
    
    def delete(self, key: str) -> bool:
        """Delete a cache entry"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cache entries"""
        self.cache.clear()
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate entries matching a pattern (simple prefix match)"""
        count = 0
        keys_to_delete = [k for k in self.cache.keys() if k.startswith(pattern)]
        for key in keys_to_delete:
            del self.cache[key]
            count += 1
        return count


# Global cache instance
_cache = Cache()


def get_cache() -> Cache:
    """Get the global cache instance"""
    return _cache

