"""
Redis database client with detailed logging.
Wraps redis-py with logging for all cache operations.
"""

from typing import Optional, Any, Dict, List
import redis
import time
import json
from datetime import datetime

from config import get_settings
from logger import get_logger

settings = get_settings()
logger = get_logger("redis")  # Use dedicated redis logger


class RedisClientLogger:
    """
    Redis database client with comprehensive logging.
    
    Logs all cache operations, hits/misses, and performance metrics.
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        password: Optional[str] = None,
        db: int = 0
    ):
        """
        Initialize Redis client.
        
        Args:
            host: Redis host
            port: Redis port
            password: Password
            db: Database number
        """
        self.host = host or settings.database.redis_host
        self.port = port or settings.database.redis_port
        self.password = password or settings.database.redis_password
        self.db = db or settings.database.redis_db
        
        self.operation_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_duration = 0.0
        
        logger.info(f"Initializing Redis client: {self.host}:{self.port} (db: {self.db})")
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to Redis"""
        try:
            start_time = time.time()
            
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                db=self.db,
                decode_responses=False,  # Binary data support
                socket_timeout=5.0,
                socket_connect_timeout=5.0
            )
            
            # Test connection
            self.client.ping()
            
            duration = time.time() - start_time
            logger.info(f"✅ Connected to Redis in {duration:.3f}s")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            raise
    
    def get(self, key: str) -> Optional[bytes]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None
        """
        start_time = time.time()
        self.operation_count += 1
        
        try:
            logger.debug(f"GET {key[:50]}...")
            
            value = self.client.get(key)
            
            duration = time.time() - start_time
            self.total_duration += duration
            
            if value is not None:
                self.cache_hits += 1
                logger.debug(
                    f"✅ Cache HIT for {key[:50]}... "
                    f"({len(value)} bytes in {duration:.3f}s)"
                )
            else:
                self.cache_misses += 1
                logger.debug(f"❌ Cache MISS for {key[:50]}... ({duration:.3f}s)")
            
            return value
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ GET failed after {duration:.3f}s: {e}")
            raise
    
    def set(
        self,
        key: str,
        value: bytes,
        ex: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to store
            ex: Expiration in seconds
        
        Returns:
            True if successful
        """
        start_time = time.time()
        self.operation_count += 1
        
        try:
            logger.debug(
                f"SET {key[:50]}... "
                f"({len(value)} bytes, ttl: {ex}s)"
            )
            
            result = self.client.set(key, value, ex=ex)
            
            duration = time.time() - start_time
            self.total_duration += duration
            
            logger.debug(f"✅ SET completed in {duration:.3f}s")
            return bool(result)
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ SET failed after {duration:.3f}s: {e}")
            raise
    
    def setex(
        self,
        key: str,
        time_seconds: int,
        value: bytes
    ) -> bool:
        """
        Set value with expiration.
        
        Args:
            key: Cache key
            time_seconds: TTL in seconds
            value: Value to store
        
        Returns:
            True if successful
        """
        start_time = time.time()
        self.operation_count += 1
        
        try:
            logger.debug(
                f"SETEX {key[:50]}... "
                f"({len(value)} bytes, ttl: {time_seconds}s)"
            )
            
            result = self.client.setex(key, time_seconds, value)
            
            duration = time.time() - start_time
            self.total_duration += duration
            
            logger.debug(f"✅ SETEX completed in {duration:.3f}s")
            return bool(result)
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ SETEX failed after {duration:.3f}s: {e}")
            raise
    
    def delete(self, *keys: str) -> int:
        """
        Delete keys.
        
        Args:
            keys: Keys to delete
        
        Returns:
            Number of keys deleted
        """
        start_time = time.time()
        self.operation_count += 1
        
        try:
            logger.debug(f"DELETE {len(keys)} keys")
            
            count = self.client.delete(*keys)
            
            duration = time.time() - start_time
            self.total_duration += duration
            
            logger.info(f"✅ Deleted {count} keys in {duration:.3f}s")
            return count
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ DELETE failed after {duration:.3f}s: {e}")
            raise
    
    def keys(self, pattern: str = "*") -> List[bytes]:
        """
        Get keys matching pattern.
        
        Args:
            pattern: Key pattern
        
        Returns:
            List of matching keys
        """
        start_time = time.time()
        self.operation_count += 1
        
        try:
            logger.debug(f"KEYS {pattern}")
            
            keys = self.client.keys(pattern)
            
            duration = time.time() - start_time
            self.total_duration += duration
            
            logger.info(f"✅ Found {len(keys)} keys in {duration:.3f}s")
            return keys
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ KEYS failed after {duration:.3f}s: {e}")
            raise
    
    def flushdb(self) -> bool:
        """
        Flush current database.
        
        Returns:
            True if successful
        """
        start_time = time.time()
        
        try:
            logger.warning(f"⚠️  Flushing database {self.db}")
            
            result = self.client.flushdb()
            
            duration = time.time() - start_time
            logger.info(f"✅ Database flushed in {duration:.3f}s")
            return bool(result)
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ FLUSHDB failed after {duration:.3f}s: {e}")
            raise
    
    def ping(self) -> bool:
        """
        Ping Redis server.
        
        Returns:
            True if server responds
        """
        try:
            result = self.client.ping()
            logger.debug("✅ PING successful")
            return result
        except Exception as e:
            logger.error(f"❌ PING failed: {e}")
            return False
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get Redis server info.
        
        Returns:
            Server information
        """
        try:
            logger.debug("Getting Redis INFO")
            
            info = self.client.info()
            
            relevant_info = {
                "version": info.get("redis_version"),
                "uptime_seconds": info.get("uptime_in_seconds"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "total_commands_processed": info.get("total_commands_processed"),
                "keyspace_db": info.get(f"db{self.db}", {})
            }
            
            logger.info(f"📊 Redis info: {relevant_info}")
            return relevant_info
            
        except Exception as e:
            logger.error(f"❌ Failed to get INFO: {e}")
            return {}
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get client statistics.
        
        Returns:
            Statistics dictionary
        """
        hit_rate = self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
        
        stats = {
            "host": self.host,
            "port": self.port,
            "db": self.db,
            "operations": self.operation_count,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": hit_rate,
            "total_duration": self.total_duration,
            "avg_operation_time": self.total_duration / self.operation_count if self.operation_count > 0 else 0
        }
        
        logger.info(
            f"📊 Redis stats: {self.operation_count} ops, "
            f"hit rate: {hit_rate:.1%}"
        )
        return stats
    
    def close(self) -> None:
        """Close Redis connection"""
        if self.client:
            logger.info(
                f"Closing Redis connection. "
                f"{self.operation_count} operations, "
                f"hit rate: {self.cache_hits/(self.cache_hits + self.cache_misses):.1%}"
                if (self.cache_hits + self.cache_misses) > 0 else "No cache operations"
            )
            self.client.close()
    
    def __del__(self):
        """Cleanup on deletion"""
        self.close()
    
    def __repr__(self) -> str:
        return (
            f"<RedisClient {self.host}:{self.port} db:{self.db} "
            f"(ops: {self.operation_count}, hit rate: "
            f"{self.cache_hits/(self.cache_hits + self.cache_misses):.1%})>"
            if (self.cache_hits + self.cache_misses) > 0
            else f"<RedisClient {self.host}:{self.port} db:{self.db}>"
        )


if __name__ == "__main__":
    # Test Redis client
    print("Testing RedisClientLogger...")
    
    try:
        client = RedisClientLogger()
        
        # Test set/get
        test_key = "test:key"
        test_value = b"test value"
        
        client.set(test_key, test_value, ex=60)
        value = client.get(test_key)
        
        assert value == test_value, "Value mismatch!"
        
        # Test cache miss
        missing = client.get("nonexistent:key")
        assert missing is None
        
        # Get stats
        stats = client.get_stats()
        print(f"\n📊 Stats: {stats}")
        
        # Get server info
        info = client.get_info()
        print(f"\n📊 Server info: {info}")
        
        # Cleanup
        client.delete(test_key)
        client.close()
        
        print("\n✅ RedisClientLogger test passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("💡 Make sure Redis is running: docker-compose up -d redis")

