import redis
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from app.core.config import settings
from app.core.logger import logger

class CacheService:
    """
    Redis-based caching service for market data
    """
    
    def __init__(self):
        self.redis_client = None
        self.default_ttl = 300  # 5 minutes default TTL
        self.market_data_ttl = 60  # 1 minute for market data
        self.price_data_ttl = 30  # 30 seconds for price data
        
    def get_redis_client(self) -> redis.Redis:
        """Get or create Redis client"""
        if self.redis_client is None:
            try:
                self.redis_client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    password=settings.REDIS_PASSWORD,
                    decode_responses=True
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Redis connection established")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self.redis_client = None
        return self.redis_client
    
    def _serialize_data(self, data: Any) -> str:
        """Serialize data for Redis storage"""
        if isinstance(data, (dict, list)):
            return json.dumps(data, default=str)
        return str(data)
    
    def _deserialize_data(self, data: str) -> Any:
        """Deserialize data from Redis"""
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return data
    
    def _get_cache_key(self, prefix: str, identifier: str) -> str:
        """Generate cache key"""
        return f"fortexa:{prefix}:{identifier}"
    
    def get(self, key: str, prefix: str = "market") -> Optional[Any]:
        """Get data from cache"""
        try:
            redis_client = self.get_redis_client()
            if not redis_client:
                return None
                
            cache_key = self._get_cache_key(prefix, key)
            cached_data = redis_client.get(cache_key)
            
            if cached_data:
                return self._deserialize_data(cached_data)
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None, prefix: str = "market") -> bool:
        """Set data in cache"""
        try:
            redis_client = self.get_redis_client()
            if not redis_client:
                return False
                
            cache_key = self._get_cache_key(prefix, key)
            serialized_data = self._serialize_data(data)
            
            if ttl is None:
                ttl = self.default_ttl
                
            redis_client.setex(cache_key, ttl, serialized_data)
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str, prefix: str = "market") -> bool:
        """Delete data from cache"""
        try:
            redis_client = self.get_redis_client()
            if not redis_client:
                return False
                
            cache_key = self._get_cache_key(prefix, key)
            redis_client.delete(cache_key)
            return True
            
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def exists(self, key: str, prefix: str = "market") -> bool:
        """Check if key exists in cache"""
        try:
            redis_client = self.get_redis_client()
            if not redis_client:
                return False
                
            cache_key = self._get_cache_key(prefix, key)
            return redis_client.exists(cache_key) > 0
            
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False
    
    def get_ttl(self, key: str, prefix: str = "market") -> int:
        """Get TTL for a key"""
        try:
            redis_client = self.get_redis_client()
            if not redis_client:
                return -1
                
            cache_key = self._get_cache_key(prefix, key)
            return redis_client.ttl(cache_key)
            
        except Exception as e:
            logger.error(f"Cache TTL error: {e}")
            return -1
    
    def flush_pattern(self, pattern: str, prefix: str = "market") -> int:
        """Delete all keys matching a pattern"""
        try:
            redis_client = self.get_redis_client()
            if not redis_client:
                return 0
                
            cache_pattern = self._get_cache_key(prefix, pattern)
            keys = redis_client.keys(cache_pattern)
            
            if keys:
                return redis_client.delete(*keys)
            return 0
            
        except Exception as e:
            logger.error(f"Cache flush pattern error: {e}")
            return 0
    
    # Market data specific methods
    def get_market_data(self, symbol: str = "all") -> Optional[Dict[str, Any]]:
        """Get cached market data"""
        return self.get(f"data:{symbol}", prefix="market")
    
    def set_market_data(self, symbol: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Cache market data"""
        if ttl is None:
            ttl = self.market_data_ttl
        return self.set(f"data:{symbol}", data, ttl, prefix="market")
    
    def get_price_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached price data"""
        return self.get(f"price:{symbol}", prefix="market")
    
    def set_price_data(self, symbol: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Cache price data"""
        if ttl is None:
            ttl = self.price_data_ttl
        return self.set(f"price:{symbol}", data, ttl, prefix="market")
    
    def get_historical_data(self, symbol: str, interval: str, limit: int) -> Optional[List[Dict[str, Any]]]:
        """Get cached historical data"""
        key = f"historical:{symbol}:{interval}:{limit}"
        return self.get(key, prefix="market")
    
    def set_historical_data(self, symbol: str, interval: str, limit: int, data: List[Dict[str, Any]], ttl: Optional[int] = None) -> bool:
        """Cache historical data"""
        if ttl is None:
            ttl = 300  # 5 minutes for historical data
        key = f"historical:{symbol}:{interval}:{limit}"
        return self.set(key, data, ttl, prefix="market")
    
    def get_top_cryptocurrencies(self, limit: int = 50) -> Optional[List[Dict[str, Any]]]:
        """Get cached top cryptocurrencies"""
        return self.get(f"top_cryptos:{limit}", prefix="market")
    
    def set_top_cryptocurrencies(self, limit: int, data: List[Dict[str, Any]], ttl: Optional[int] = None) -> bool:
        """Cache top cryptocurrencies"""
        if ttl is None:
            ttl = self.market_data_ttl
        return self.set(f"top_cryptos:{limit}", data, ttl, prefix="market")
    
    def get_market_summary(self) -> Optional[Dict[str, Any]]:
        """Get cached market summary"""
        return self.get("summary", prefix="market")
    
    def set_market_summary(self, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Cache market summary"""
        if ttl is None:
            ttl = self.market_data_ttl
        return self.set("summary", data, ttl, prefix="market")
    
    def get_search_results(self, query: str, limit: int = 20) -> Optional[List[Dict[str, Any]]]:
        """Get cached search results"""
        key = f"search:{query}:{limit}"
        return self.get(key, prefix="market")
    
    def set_search_results(self, query: str, limit: int, data: List[Dict[str, Any]], ttl: Optional[int] = None) -> bool:
        """Cache search results"""
        if ttl is None:
            ttl = 600  # 10 minutes for search results
        key = f"search:{query}:{limit}"
        return self.set(key, data, ttl, prefix="market")
    
    def get_order_book(self, symbol: str, limit: int = 20) -> Optional[Dict[str, Any]]:
        """Get cached order book"""
        key = f"orderbook:{symbol}:{limit}"
        return self.get(key, prefix="market")
    
    def set_order_book(self, symbol: str, limit: int, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Cache order book"""
        if ttl is None:
            ttl = 10  # 10 seconds for order book (very dynamic)
        key = f"orderbook:{symbol}:{limit}"
        return self.set(key, data, ttl, prefix="market")
    
    def invalidate_symbol_cache(self, symbol: str) -> int:
        """Invalidate all cache for a specific symbol"""
        patterns = [
            f"data:{symbol}",
            f"price:{symbol}",
            f"historical:{symbol}:*",
            f"orderbook:{symbol}:*"
        ]
        
        total_deleted = 0
        for pattern in patterns:
            total_deleted += self.flush_pattern(pattern, prefix="market")
        
        return total_deleted
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            redis_client = self.get_redis_client()
            if not redis_client:
                return {"error": "Redis not available"}
                
            info = redis_client.info()
            
            # Get market data specific stats
            market_keys = redis_client.keys("fortexa:market:*")
            
            return {
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory": info.get("used_memory_human"),
                "total_keys": info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": info.get("keyspace_hits", 0) / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1) * 100,
                "market_data_keys": len(market_keys),
                "uptime_in_seconds": info.get("uptime_in_seconds"),
            }
            
        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"error": str(e)}

# Global instance
cache_service = CacheService() 