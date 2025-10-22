"""
Memgraph database client with detailed logging.
Uses neo4j driver (compatible with Memgraph Bolt protocol).
"""

from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
from datetime import datetime
import time

from config import get_settings
from logger import get_logger

settings = get_settings()
logger = get_logger("memgraph")  # Use dedicated memgraph logger


class MemgraphResultWrapper:
    """Wrapper to mimic pymemgraph result interface"""
    
    def __init__(self, records):
        self.records = records
        self._index = 0
    
    def fetchall(self):
        """Return all records as tuples"""
        return [tuple(record.values()) for record in self.records]
    
    def fetchone(self):
        """Return next record as tuple"""
        if self._index < len(self.records):
            record = self.records[self._index]
            self._index += 1
            return tuple(record.values())
        return None
    
    def __iter__(self):
        return iter(self.records)


class MemgraphClient:
    """
    Memgraph database client with comprehensive logging.
    Uses Neo4j Bolt driver (compatible with Memgraph).
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize Memgraph client.
        
        Args:
            host: Memgraph host
            port: Memgraph port
            username: Username (optional for Memgraph)
            password: Password (optional for Memgraph)
        """
        self.host = host or settings.database.memgraph_host
        self.port = port or settings.database.memgraph_port
        self.username = username or settings.database.memgraph_user or ""
        self.password = password or settings.database.memgraph_password or ""
        
        self.driver = None
        self.query_count = 0
        self.total_duration = 0.0
        
        logger.info(f"Initializing Memgraph client: {self.host}:{self.port}")
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to Memgraph using Neo4j Bolt protocol"""
        try:
            start_time = time.time()
            
            uri = f"bolt://{self.host}:{self.port}"
            
            # Create driver (no auth for local Memgraph by default)
            if self.username and self.password:
                auth = (self.username, self.password)
            else:
                auth = None
            
            self.driver = GraphDatabase.driver(uri, auth=auth)
            
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1").consume()
            
            duration = time.time() - start_time
            logger.info(f"✅ Connected to Memgraph in {duration:.3f}s")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Memgraph: {e}")
            raise
    
    def execute(self, query: str, parameters: Optional[Dict[str, Any]] = None):
        """
        Execute a query and return result wrapper.
        
        Args:
            query: Cypher query
            parameters: Query parameters
            
        Returns:
            MemgraphResultWrapper with query results
        """
        if not self.driver:
            raise RuntimeError("Not connected to Memgraph")
        
        start_time = time.time()
        self.query_count += 1
        
        try:
            # Detailed query logging
            logger.info("-" * 80)
            logger.info(f"[MEMGRAPH] 📝 Cypher Query #{self.query_count}")
            
            # Format query with line numbers
            query_lines = query.strip().split('\n')
            if len(query_lines) <= 5:
                # Short query - show in one line
                logger.info(f"  Query: {query.strip()}")
            else:
                # Multi-line query - show formatted
                logger.info(f"  Query ({len(query_lines)} lines):")
                for i, line in enumerate(query_lines[:15], 1):
                    logger.info(f"    {i:2d} | {line.strip()}")
                if len(query_lines) > 15:
                    logger.info(f"    ... ({len(query_lines) - 15} more lines)")
            
            if parameters:
                logger.info(f"  Parameters: {parameters}")
            
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                records = list(result)
            
            duration = time.time() - start_time
            self.total_duration += duration
            
            logger.info(
                f"  ✅ Success: {len(records)} records in {duration:.3f}s "
                f"(total: {self.query_count} queries)"
            )
            logger.info("-" * 80)
            
            return MemgraphResultWrapper(records)
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"❌ Query failed after {duration:.3f}s: {e}\n"
                f"Query: {query[:200]}"
            )
            raise
    
    def execute_and_fetch(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a query and fetch results as dictionaries.
        
        Args:
            query: Cypher query
            parameters: Query parameters
        
        Returns:
            List of result dictionaries
        """
        if not self.driver:
            raise RuntimeError("Not connected to Memgraph")
        
        start_time = time.time()
        self.query_count += 1
        
        try:
            # Detailed query logging
            logger.info("=" * 80)
            logger.info(f"[MEMGRAPH] 📝 Cypher Query #{self.query_count} (fetch mode)")
            logger.info("=" * 80)
            
            # Format query with line numbers
            query_lines = query.strip().split('\n')
            if len(query_lines) <= 5:
                # Short query - show in one line
                logger.info(f"  📄 Query: {query.strip()}")
            else:
                # Multi-line query - show formatted
                logger.info(f"  📄 Query ({len(query_lines)} lines):")
                for i, line in enumerate(query_lines[:15], 1):
                    logger.info(f"    {i:2d} | {line.strip()}")
                if len(query_lines) > 15:
                    logger.info(f"    ... ({len(query_lines) - 15} more lines)")
            
            # Log parameters
            if parameters:
                logger.info(f"  🔑 Parameters:")
                for key, value in parameters.items():
                    value_str = str(value)
                    if len(value_str) > 100:
                        value_str = value_str[:100] + "..."
                    logger.info(f"    • {key}: {value_str}")
            
            logger.info(f"  ⏱️  Executing...")
            
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                results = [dict(record) for record in result]
            
            duration = time.time() - start_time
            self.total_duration += duration
            
            # Log results with sample
            logger.info(f"  ✅ Success!")
            logger.info(f"    • Returned: {len(results)} records")
            logger.info(f"    • Duration: {duration:.3f}s")
            logger.info(f"    • Cumulative time: {self.total_duration:.3f}s")
            logger.info(f"    • Avg query time: {self.total_duration / self.query_count:.3f}s")
            
            # Show first few results as sample
            if results:
                logger.info(f"  📊 Sample results (first {min(3, len(results))}):")
                for idx, result in enumerate(results[:3], 1):
                    logger.info(f"    Record {idx}:")
                    for key, value in list(result.items())[:5]:
                        value_str = str(value)
                        if len(value_str) > 60:
                            value_str = value_str[:60] + "..."
                        logger.info(f"      • {key}: {value_str}")
                    if len(result) > 5:
                        logger.info(f"      ... ({len(result) - 5} more fields)")
                
                if len(results) > 3:
                    logger.info(f"    ... ({len(results) - 3} more records)")
            
            logger.info("=" * 80)
            logger.info("")
            
            return results
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"❌ Query failed after {duration:.3f}s: {e}\n"
                f"Query: {query[:200]}"
            )
            raise
    
    def get_connection(self):
        """Get the Memgraph driver"""
        if not self.driver:
            self._connect()
        return self
    
    def create_index(self, label: str, property: str) -> None:
        """
        Create an index on a label and property.
        
        Args:
            label: Node label
            property: Property name
        """
        query = f"CREATE INDEX ON :{label}({property});"
        logger.info(f"Creating index on :{label}({property})")
        try:
            self.execute(query)
            logger.info(f"✅ Index created successfully")
        except Exception as e:
            logger.warning(f"Index creation failed (may already exist): {e}")
    
    def clear_database(self) -> None:
        """Clear all nodes and relationships"""
        logger.warning("⚠️  Clearing entire database...")
        start_time = time.time()
        
        self.execute("MATCH (n) DETACH DELETE n;")
        
        duration = time.time() - start_time
        logger.info(f"✅ Database cleared in {duration:.3f}s")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            # Count nodes by label
            node_result = self.execute_and_fetch(
                "MATCH (n) RETURN labels(n)[0] as label, count(n) as count"
            )
            
            # Count relationships
            rel_result = self.execute_and_fetch(
                "MATCH ()-[r]->() RETURN count(r) as count"
            )
            
            return {
                "nodes": node_result,
                "relationships": rel_result[0]["count"] if rel_result else 0,
                "query_count": self.query_count,
                "total_duration": self.total_duration
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
    
    def close(self) -> None:
        """Close the database connection"""
        if self.driver:
            logger.info(
                f"Closing Memgraph connection. "
                f"Total queries: {self.query_count}, "
                f"Total duration: {self.total_duration:.3f}s"
            )
            self.driver.close()
            self.driver = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def __del__(self):
        """Cleanup on deletion"""
        try:
            self.close()
        except:
            pass


# Test if this module is run directly
if __name__ == "__main__":
    import sys
    
    print("Testing Memgraph connection...")
    
    try:
        client = MemgraphClient()
        
        # Test simple query
        result = client.execute_and_fetch("MATCH (n) RETURN count(n) as count")
        print(f"✅ Node count: {result[0]['count']}")
        
        # Get stats
        stats = client.get_stats()
        print(f"\n📊 Database Stats:")
        print(f"  Nodes: {stats.get('nodes', [])}")
        print(f"  Relationships: {stats.get('relationships', 0)}")
        print(f"  Query count: {stats.get('query_count', 0)}")
        
        client.close()
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
