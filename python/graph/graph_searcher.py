"""
Optimized graph search functionality for code graph.
Provides fast, cached search with filtering and ranking.
"""

import time
import hashlib
from typing import List, Dict, Optional, Any, Tuple
from functools import lru_cache
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from database.sqlite_graph_client import SQLiteGraphClient
from logger import get_logger

logger = get_logger("graph_searcher")


class GraphSearcher:
    """
    Optimized search functionality for code graph.
    
    Features:
    - Fast method search with filtering
    - Class-priority search
    - Caching for repeated queries
    - Pagination support
    - Full-text search (when FTS5 is available)
    """
    
    def __init__(self, graph_client: SQLiteGraphClient, cache_size: int = 1000):
        """
        Initialize graph searcher.
        
        Args:
            graph_client: SQLite graph client instance
            cache_size: Maximum number of cached queries
        """
        self.client = graph_client
        self.cache_size = cache_size
        self._cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
        logger.info(f"Initialized GraphSearcher with cache size: {cache_size}")
    
    def _cache_key(self, method: str, **kwargs) -> str:
        """Generate cache key for query parameters"""
        key_data = f"{method}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get result from cache"""
        if cache_key in self._cache:
            self._cache_hits += 1
            logger.debug(f"Cache hit: {cache_key}")
            return self._cache[cache_key]
        
        self._cache_misses += 1
        return None
    
    def _put_to_cache(self, cache_key: str, result: Any) -> None:
        """Put result to cache with LRU eviction"""
        # Simple LRU: remove oldest if cache is full
        if len(self._cache) >= self.cache_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        
        self._cache[cache_key] = result
        logger.debug(f"Cached result: {cache_key}")
    
    def search_methods(
        self, 
        name_pattern: Optional[str] = None,
        class_name: Optional[str] = None,
        package: Optional[str] = None,
        project_id: str = "default",
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search methods with filtering and pagination.
        
        Args:
            name_pattern: Pattern to match method name (supports LIKE)
            class_name: Class name to search in
            package: Package name to filter by
            project_id: Project identifier
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            Dictionary with methods, total count, and pagination info
        """
        start_time = time.time()
        
        # Build WHERE conditions
        conditions = ["type = 'Method'", "project_id = ?"]
        params = [project_id]
        
        if name_pattern:
            conditions.append("name LIKE ?")
            params.append(f"%{name_pattern}%")
        
        if class_name:
            conditions.append("package LIKE ?")
            params.append(f"%{class_name}%")
        
        if package:
            conditions.append("package = ?")
            params.append(package)
        
        # Main query with pagination
        query = f"""
        SELECT * FROM entities 
        WHERE {' AND '.join(conditions)}
        ORDER BY name, package
        LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        # Count query for total
        count_query = f"""
        SELECT COUNT(*) as total FROM entities 
        WHERE {' AND '.join(conditions)}
        """
        count_params = params[:-2]  # Remove limit and offset
        
        try:
            methods = self.client.execute_and_fetch(query, params)
            count_result = self.client.execute_and_fetch(count_query, count_params)
            total_count = count_result[0]['total'] if count_result else 0
            
            # Parse JSON properties for each method
            parsed_methods = []
            for method in methods:
                if method.get("properties"):
                    try:
                        import json
                        properties = json.loads(method["properties"])
                        method.update(properties)
                    except (json.JSONDecodeError, TypeError):
                        pass
                parsed_methods.append(method)
            
            duration = time.time() - start_time
            
            result = {
                'methods': parsed_methods,
                'total_count': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + len(parsed_methods) < total_count,
                'duration_ms': round(duration * 1000, 2)
            }
            
            logger.info(f"Search methods: {len(parsed_methods)}/{total_count} results in {duration:.3f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error searching methods: {e}")
            return {
                'methods': [],
                'total_count': 0,
                'limit': limit,
                'offset': offset,
                'has_more': False,
                'error': str(e),
                'duration_ms': round((time.time() - start_time) * 1000, 2)
            }
    
    def find_method_by_signature(
        self, 
        method_name: str,
        class_name: Optional[str] = None,
        project_id: str = "default",
        exact_match: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Find method by signature with class priority.
        
        This is the core method that fixes the original issue where
        the system would return methods from wrong classes.
        
        Args:
            method_name: Name of the method to find
            class_name: Preferred class name (gets priority)
            project_id: Project identifier
            exact_match: Whether to use exact name matching
            
        Returns:
            Method data if found, None otherwise
        """
        start_time = time.time()
        
        # Check cache first
        cache_key = self._cache_key(
            "find_method_by_signature", 
            method_name=method_name,
            class_name=class_name,
            exact_match=exact_match
        )
        
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            if exact_match:
                name_condition = "name = ?"
            else:
                name_condition = "name LIKE ?"
            
            conditions = ["type = 'Method'", "project_id = ?", name_condition]
            params = [project_id, method_name]
            
            if class_name:
                # Priority: first try exact class match, then partial
                query = f"""
                SELECT * FROM entities 
                WHERE {' AND '.join(conditions)}
                ORDER BY 
                    CASE 
                        WHEN package = ? THEN 0
                        WHEN package LIKE ? THEN 1
                        ELSE 2
                    END,
                    name
                LIMIT 1
                """
                params.extend([class_name, f"%{class_name}%"])
            else:
                query = f"""
                SELECT * FROM entities 
                WHERE {' AND '.join(conditions)}
                ORDER BY name
                LIMIT 1
                """
            
            results = self.client.execute_and_fetch(query, params)
            
            if results:
                method = results[0]
                
                # Parse JSON properties
                if method.get("properties"):
                    try:
                        import json
                        properties = json.loads(method["properties"])
                        method.update(properties)
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                duration = time.time() - start_time
                logger.info(f"Found method {method_name} in {duration:.3f}s: {method.get('package', 'unknown')}.{method.get('name', 'unknown')}")
                
                # Cache the result
                self._put_to_cache(cache_key, method)
                return method
            
            duration = time.time() - start_time
            logger.warning(f"Method {method_name} not found in {duration:.3f}s")
            return None
            
        except Exception as e:
            logger.error(f"Error finding method {method_name}: {e}")
            return None
    
    def find_methods_by_class(
        self, 
        class_name: str,
        project_id: str = "default",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Find all methods in a specific class.
        
        Args:
            class_name: Name of the class
            project_id: Project identifier
            limit: Maximum number of methods to return
            
        Returns:
            List of method data
        """
        start_time = time.time()
        
        query = """
        SELECT * FROM entities 
        WHERE type = 'Method' 
        AND project_id = ? 
        AND package LIKE ?
        ORDER BY name
        LIMIT ?
        """
        
        try:
            results = self.client.execute_and_fetch(query, (project_id, f"%{class_name}%", limit))
            
            # Parse JSON properties
            methods = []
            for method in results:
                if method.get("properties"):
                    try:
                        import json
                        properties = json.loads(method["properties"])
                        method.update(properties)
                    except (json.JSONDecodeError, TypeError):
                        pass
                methods.append(method)
            
            duration = time.time() - start_time
            logger.info(f"Found {len(methods)} methods in class {class_name} in {duration:.3f}s")
            return methods
            
        except Exception as e:
            logger.error(f"Error finding methods in class {class_name}: {e}")
            return []
    
    def get_method_by_id(self, method_id: str, project_id: str = "default") -> Optional[Dict[str, Any]]:
        """
        Get method by exact ID (cached).
        
        Args:
            method_id: Full method ID
            project_id: Project identifier
            
        Returns:
            Method data if found, None otherwise
        """
        # Check cache first
        cache_key = self._cache_key("get_method_by_id", method_id=method_id)
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        query = "SELECT * FROM entities WHERE id = ? AND project_id = ?"
        
        try:
            results = self.client.execute_and_fetch(query, (method_id, project_id))
            
            if results:
                method = results[0]
                
                # Parse JSON properties
                if method.get("properties"):
                    try:
                        import json
                        properties = json.loads(method["properties"])
                        method.update(properties)
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                # Cache the result
                self._put_to_cache(cache_key, method)
                return method
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting method by ID {method_id}: {e}")
            return None
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'cache_size': len(self._cache),
            'max_cache_size': self.cache_size,
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate_percent': round(hit_rate, 2),
            'total_requests': total_requests
        }
    
    def clear_cache(self) -> None:
        """Clear the search cache"""
        self._cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        logger.info("Search cache cleared")


class CachedGraphSearcher(GraphSearcher):
    """
    Enhanced graph searcher with additional caching strategies.
    """
    
    def __init__(self, graph_client: SQLiteGraphClient, cache_size: int = 1000):
        super().__init__(graph_client, cache_size)
        self._method_cache = {}  # Cache for individual methods
        self._class_cache = {}   # Cache for class methods
    
    @lru_cache(maxsize=500)
    def get_method_by_id_cached(self, method_id: str, project_id: str = "default") -> Optional[Dict[str, Any]]:
        """LRU cached version of get_method_by_id"""
        return self.get_method_by_id(method_id, project_id)
    
    def find_methods_by_class_cached(
        self, 
        class_name: str,
        project_id: str = "default",
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Cached version of find_methods_by_class"""
        cache_key = f"class_methods:{class_name}:{project_id}:{limit}"
        
        if cache_key in self._class_cache:
            return self._class_cache[cache_key]
        
        methods = self.find_methods_by_class(class_name, project_id, limit)
        self._class_cache[cache_key] = methods
        
        # Simple cache size management
        if len(self._class_cache) > 100:
            oldest_key = next(iter(self._class_cache))
            del self._class_cache[oldest_key]
        
        return methods
