"""
SQLite graph database client for code graph storage.
Uses adjacency list pattern to store entities and relationships in SQLite.
"""

import sqlite3
import json
import time
import sys
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from datetime import datetime
import logging

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config import get_settings
from logger import get_logger

settings = get_settings()
logger = get_logger("sqlite_graph")


class SQLiteGraphClient:
    """
    SQLite graph database client using adjacency list pattern.
    
    Schema:
    - entities: Stores all nodes (packages, classes, methods, fields)
    - relationships: Stores all edges between entities
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize SQLite graph client.
        
        Args:
            db_path: Path to SQLite database file (default: from config)
        """
        self.db_path = db_path or getattr(settings.database, 'sqlite_graph_db_path', 'data/code_graph.db')
        
        # Ensure data directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.connection = None
        self.query_count = 0
        self.total_duration = 0.0
        
        logger.info(f"Initializing SQLite graph client: {self.db_path}")
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to SQLite database"""
        try:
            start_time = time.time()
            
            # Connect to SQLite database
            self.connection = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False  # Allow multi-threading
            )
            
            # Enable foreign key constraints
            self.connection.execute("PRAGMA foreign_keys = ON")
            
            # Optimize for performance
            self.connection.execute("PRAGMA journal_mode = WAL")
            self.connection.execute("PRAGMA synchronous = NORMAL")
            self.connection.execute("PRAGMA cache_size = 10000")
            self.connection.execute("PRAGMA temp_store = MEMORY")
            
            duration = time.time() - start_time
            logger.info(f"✅ Connected to SQLite in {duration:.3f}s")
            logger.info(f"   Database: {self.db_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to SQLite: {e}")
            raise
    
    def init_schema(self) -> None:
        """Initialize graph schema (create tables and indexes)"""
        try:
            logger.info("Initializing SQLite graph schema...")
            
            # Create entities table
            entities_table = """
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                package TEXT,
                project_id TEXT NOT NULL,
                properties TEXT,  -- JSON blob for flexible properties
                created_at TEXT NOT NULL
            )
            """
            self._execute_query(entities_table, log_query=False)
            
            # Create relationships table
            relationships_table = """
            CREATE TABLE IF NOT EXISTS relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                rel_type TEXT NOT NULL,
                properties TEXT,  -- JSON blob for edge properties
                project_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (source_id) REFERENCES entities(id),
                FOREIGN KEY (target_id) REFERENCES entities(id)
            )
            """
            self._execute_query(relationships_table, log_query=False)
            
            # Create indexes for entities
            entity_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type)",
                "CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)",
                "CREATE INDEX IF NOT EXISTS idx_entities_package ON entities(package)",
                "CREATE INDEX IF NOT EXISTS idx_entities_project ON entities(project_id)",
                "CREATE INDEX IF NOT EXISTS idx_entities_type_project ON entities(type, project_id)"
            ]
            
            for index_query in entity_indexes:
                self._execute_query(index_query, log_query=False)
            
            # Create indexes for relationships
            relationship_indexes = [
                "CREATE INDEX IF NOT EXISTS idx_rel_source ON relationships(source_id)",
                "CREATE INDEX IF NOT EXISTS idx_rel_target ON relationships(target_id)",
                "CREATE INDEX IF NOT EXISTS idx_rel_type ON relationships(rel_type)",
                "CREATE INDEX IF NOT EXISTS idx_rel_project ON relationships(project_id)",
                "CREATE INDEX IF NOT EXISTS idx_rel_source_type ON relationships(source_id, rel_type)",
                "CREATE INDEX IF NOT EXISTS idx_rel_target_type ON relationships(target_id, rel_type)"
            ]
            
            for index_query in relationship_indexes:
                self._execute_query(index_query, log_query=False)
            
            logger.info("✅ SQLite graph schema initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize schema: {e}")
            raise
    
    def _execute_query(self, query: str, params: Optional[tuple] = None, log_query: bool = True) -> sqlite3.Cursor:
        """Execute a query and return cursor"""
        if not self.connection:
            raise RuntimeError("Not connected to SQLite database")
        
        start_time = time.time()
        self.query_count += 1
        
        try:
            if log_query:
                # Detailed query logging
                logger.info("-" * 80)
                logger.info(f"[SQLITE] 📝 SQL Query #{self.query_count}")
                
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
                
                if params:
                    logger.info(f"  Params: {params}")
            
            cursor = self.connection.execute(query, params or ())
            self.connection.commit()
            
            duration = time.time() - start_time
            self.total_duration += duration
            
            if log_query:
                logger.info(
                    f"  ✅ Success in {duration:.3f}s "
                    f"(total: {self.query_count} queries)"
                )
                logger.info("-" * 80)
            
            return cursor
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"❌ Query failed after {duration:.3f}s: {e}\n"
                f"Query: {query[:200]}"
            )
            raise
    
    def execute(self, query: str, params: Optional[tuple] = None) -> sqlite3.Cursor:
        """
        Execute a query and return cursor.
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            SQLite cursor
        """
        return self._execute_query(query, params)
    
    def execute_and_fetch(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a query and fetch results as dictionaries.
        
        Args:
            query: SQL query
            params: Query parameters
        
        Returns:
            List of result dictionaries
        """
        cursor = self._execute_query(query, params)
        
        # Get column names
        columns = [description[0] for description in cursor.description] if cursor.description else []
        
        # Convert rows to dictionaries
        results = []
        for row in cursor.fetchall():
            result = {}
            for i, value in enumerate(row):
                column_name = columns[i] if i < len(columns) else f"column_{i}"
                result[column_name] = value
            results.append(result)
        
        return results
    
    def insert_entity(
        self,
        entity_id: str,
        entity_type: str,
        name: str,
        package: Optional[str],
        project_id: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Insert an entity (node) into the graph.
        
        Args:
            entity_id: Unique entity identifier
            entity_type: Type of entity (Package/Class/Method/Field)
            name: Entity name
            package: Package name (optional)
            project_id: Project identifier
            properties: Additional properties as dictionary
        """
        properties_json = json.dumps(properties) if properties else None
        created_at = datetime.utcnow().isoformat()
        
        query = """
        INSERT OR REPLACE INTO entities (id, type, name, package, project_id, properties, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (entity_id, entity_type, name, package, project_id, properties_json, created_at)
        
        self._execute_query(query, params)
        logger.debug(f"Inserted entity: {entity_id} ({entity_type})")
    
    def insert_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        project_id: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Insert a relationship (edge) into the graph.
        
        Args:
            source_id: Source entity ID
            target_id: Target entity ID
            rel_type: Relationship type (CONTAINS/CALLS/USES/etc.)
            project_id: Project identifier
            properties: Additional properties as dictionary
        """
        properties_json = json.dumps(properties) if properties else None
        created_at = datetime.utcnow().isoformat()
        
        query = """
        INSERT OR IGNORE INTO relationships (source_id, target_id, rel_type, project_id, properties, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (source_id, target_id, rel_type, project_id, properties_json, created_at)
        
        self._execute_query(query, params)
        logger.debug(f"Inserted relationship: {source_id} -[{rel_type}]-> {target_id}")
    
    def get_entity_by_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an entity by ID.
        
        Args:
            entity_id: Entity identifier
            
        Returns:
            Entity data or None if not found
        """
        query = "SELECT * FROM entities WHERE id = ?"
        results = self.execute_and_fetch(query, (entity_id,))
        
        if results:
            entity = results[0]
            # Parse JSON properties
            if entity.get('properties'):
                try:
                    entity['properties'] = json.loads(entity['properties'])
                except json.JSONDecodeError:
                    entity['properties'] = {}
            return entity
        return None
    
    def get_entities_by_type(self, entity_type: str, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all entities of a specific type.
        
        Args:
            entity_type: Type of entities to retrieve
            project_id: Optional project filter
            
        Returns:
            List of entity dictionaries
        """
        if project_id:
            query = "SELECT * FROM entities WHERE type = ? AND project_id = ?"
            params = (entity_type, project_id)
        else:
            query = "SELECT * FROM entities WHERE type = ?"
            params = (entity_type,)
        
        results = self.execute_and_fetch(query, params)
        
        # Parse JSON properties for all entities and merge them
        for entity in results:
            if entity.get('properties'):
                try:
                    properties = json.loads(entity['properties'])
                    # Merge properties into entity dict
                    entity.update(properties)
                except json.JSONDecodeError:
                    entity['properties'] = {}
        
        return results
    
    def get_relationships(
        self,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
        rel_type: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get relationships with optional filters.
        
        Args:
            source_id: Filter by source entity ID
            target_id: Filter by target entity ID
            rel_type: Filter by relationship type
            project_id: Filter by project ID
            
        Returns:
            List of relationship dictionaries
        """
        conditions = []
        params = []
        
        if source_id:
            conditions.append("source_id = ?")
            params.append(source_id)
        
        if target_id:
            conditions.append("target_id = ?")
            params.append(target_id)
        
        if rel_type:
            conditions.append("rel_type = ?")
            params.append(rel_type)
        
        if project_id:
            conditions.append("project_id = ?")
            params.append(project_id)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM relationships WHERE {where_clause}"
        
        results = self.execute_and_fetch(query, tuple(params))
        
        # Parse JSON properties for all relationships
        for rel in results:
            if rel.get('properties'):
                try:
                    rel['properties'] = json.loads(rel['properties'])
                except json.JSONDecodeError:
                    rel['properties'] = {}
        
        return results
    
    def get_entity_relationships(
        self,
        entity_id: str,
        direction: str = "outgoing",
        rel_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get relationships for a specific entity.
        
        Args:
            entity_id: Entity identifier
            direction: "outgoing", "incoming", or "both"
            rel_type: Optional relationship type filter
            
        Returns:
            List of relationship dictionaries
        """
        conditions = []
        params = []
        
        if direction in ["outgoing", "both"]:
            conditions.append("source_id = ?")
            params.append(entity_id)
        
        if direction in ["incoming", "both"]:
            if conditions:
                conditions.append("OR target_id = ?")
            else:
                conditions.append("target_id = ?")
            params.append(entity_id)
        
        if rel_type:
            if conditions:
                conditions.append("AND rel_type = ?")
            else:
                conditions.append("rel_type = ?")
            params.append(rel_type)
        
        where_clause = " ".join(conditions)
        query = f"SELECT * FROM relationships WHERE {where_clause}"
        
        results = self.execute_and_fetch(query, tuple(params))
        
        # Parse JSON properties
        for rel in results:
            if rel.get('properties'):
                try:
                    rel['properties'] = json.loads(rel['properties'])
                except json.JSONDecodeError:
                    rel['properties'] = {}
        
        return results
    
    def clear_database(self) -> None:
        """Clear all entities and relationships"""
        logger.warning("⚠️  Clearing entire SQLite graph database...")
        start_time = time.time()
        
        try:
            # Delete all relationships first (foreign key constraint)
            self._execute_query("DELETE FROM relationships", log_query=False)
            
            # Delete all entities
            self._execute_query("DELETE FROM entities", log_query=False)
            
            # Reset auto-increment counter
            self._execute_query("DELETE FROM sqlite_sequence WHERE name='relationships'", log_query=False)
            
            duration = time.time() - start_time
            logger.info(f"✅ Database cleared in {duration:.3f}s")
            
        except Exception as e:
            logger.error(f"❌ Failed to clear database: {e}")
            raise
    
    def clear_project(self, project_id: str) -> None:
        """Clear all entities and relationships for a specific project"""
        logger.info(f"Clearing project: {project_id}")
        start_time = time.time()
        
        try:
            # Delete relationships first
            self._execute_query("DELETE FROM relationships WHERE project_id = ?", (project_id,), log_query=False)
            
            # Delete entities
            self._execute_query("DELETE FROM entities WHERE project_id = ?", (project_id,), log_query=False)
            
            duration = time.time() - start_time
            logger.info(f"✅ Project {project_id} cleared in {duration:.3f}s")
            
        except Exception as e:
            logger.error(f"❌ Failed to clear project {project_id}: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            # Count entities by type
            entity_stats = self.execute_and_fetch("""
                SELECT type, COUNT(*) as count 
                FROM entities 
                GROUP BY type
            """)
            
            # Count relationships by type
            rel_stats = self.execute_and_fetch("""
                SELECT rel_type, COUNT(*) as count 
                FROM relationships 
                GROUP BY rel_type
            """)
            
            # Total counts
            total_entities = self.execute_and_fetch("SELECT COUNT(*) as count FROM entities")[0]['count']
            total_relationships = self.execute_and_fetch("SELECT COUNT(*) as count FROM relationships")[0]['count']
            
            return {
                "entities": {
                    "total": total_entities,
                    "by_type": {row['type']: row['count'] for row in entity_stats}
                },
                "relationships": {
                    "total": total_relationships,
                    "by_type": {row['rel_type']: row['count'] for row in rel_stats}
                },
                "query_count": self.query_count,
                "total_duration": self.total_duration,
                "database_path": self.db_path
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}
    
    def close(self) -> None:
        """Close the database connection"""
        if self.connection:
            logger.info(
                f"Closing SQLite connection. "
                f"Total queries: {self.query_count}, "
                f"Total duration: {self.total_duration:.3f}s"
            )
            self.connection.close()
            self.connection = None
    
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
    
    print("Testing SQLite Graph Client...")
    
    try:
        client = SQLiteGraphClient("test_code_graph.db")
        
        # Initialize schema
        client.init_schema()
        
        # Test entity insertion
        client.insert_entity(
            entity_id="class:com.example.Calculator",
            entity_type="Class",
            name="Calculator",
            package="com.example",
            project_id="test-project",
            properties={"modifiers": ["public"], "file_path": "Calculator.java"}
        )
        
        # Test relationship insertion
        client.insert_relationship(
            source_id="package:com.example",
            target_id="class:com.example.Calculator",
            rel_type="CONTAINS",
            project_id="test-project"
        )
        
        # Test queries
        entity = client.get_entity_by_id("class:com.example.Calculator")
        print(f"✅ Retrieved entity: {entity['name']} ({entity['type']})")
        
        classes = client.get_entities_by_type("Class", "test-project")
        print(f"✅ Found {len(classes)} classes")
        
        relationships = client.get_relationships(rel_type="CONTAINS")
        print(f"✅ Found {len(relationships)} CONTAINS relationships")
        
        # Get stats
        stats = client.get_stats()
        print(f"\n📊 Database Stats:")
        print(f"  Entities: {stats['entities']['total']}")
        print(f"  Relationships: {stats['relationships']['total']}")
        print(f"  Query count: {stats['query_count']}")
        
        client.close()
        
        # Clean up test database
        Path("test_code_graph.db").unlink(missing_ok=True)
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
