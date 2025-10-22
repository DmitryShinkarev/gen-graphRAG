"""
Code graph builder using Memgraph for storing relationships between code entities.
Creates nodes for classes, methods, fields and edges for various relationships.
"""

from typing import List, Dict, Optional, Any, Set, Tuple
from pathlib import Path
import networkx as nx
from datetime import datetime
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from config import get_settings
from logger import get_logger
from parser import JavaParser, MethodInfo, ClassInfo, FieldInfo

# Import SQLite graph client
from database.sqlite_graph_client import SQLiteGraphClient

logger = get_logger(__name__)
settings = get_settings()


class CodeGraph:
    """
    Code graph database for storing and querying code relationships.
    
    Node types:
    - Package
    - Class
    - Method
    - Field
    
    Relationship types:
    - CONTAINS (Package->Class, Class->Method, Class->Field)
    - CALLS (Method->Method)
    - USES (Method->Field)
    - EXTENDS (Class->Class)
    - IMPLEMENTS (Class->Interface)
    - RETURNS (Method->Type)
    - PARAMETER (Method->Type)
    """
    
    def __init__(
        self,
        use_graph_db: bool = True,
        project_id: Optional[str] = None
    ):
        """
        Initialize code graph.
        
        Args:
            use_graph_db: If True, use SQLite; if False, use NetworkX (for development)
            project_id: Unique project identifier
        """
        self.use_graph_db = use_graph_db
        self.project_id = project_id or "default"
        
        if use_graph_db:
            try:
                self.conn = SQLiteGraphClient()
                logger.info(f"Connected to SQLite graph database: {settings.database.sqlite_graph_db_path}")
                self.conn.init_schema()
            except Exception as e:
                logger.warning(f"SQLite connection failed: {e}. Falling back to NetworkX.")
                self.use_graph_db = False
                self.graph = nx.DiGraph()
        else:
            self.use_graph_db = False
            self.graph = nx.DiGraph()
            logger.info("Using NetworkX graph (development mode)")
    
    def clear(self) -> None:
        """Clear all data from the graph"""
        logger.info(f"Clearing graph for project: {self.project_id}")
        
        if self.use_graph_db:
            try:
                # Clear all entities and relationships in SQLite
                self.conn.clear_database()
                logger.info("SQLite graph database cleared successfully")
                
                # Reinitialize schema
                self.conn.init_schema()
            except Exception as e:
                logger.error(f"Failed to clear SQLite graph database: {e}")
                raise
        else:
            # Clear NetworkX graph
            self.graph.clear()
            logger.info("NetworkX graph cleared successfully")
    
    def add_package(self, package_name: str) -> str:
        """Add a package node"""
        node_id = f"package:{package_name}"
        
        if self.use_graph_db:
            self.conn.insert_entity(
                entity_id=node_id,
                entity_type="Package",
                name=package_name,
                package=None,
                project_id=self.project_id,
                properties={}
            )
        else:
            self.graph.add_node(
                node_id,
                type="Package",
                name=package_name,
                project_id=self.project_id
            )
        
        return node_id
    
    def add_class(
        self,
        class_info: ClassInfo,
        file_path: Optional[str] = None
    ) -> str:
        """Add a class node"""
        class_id = f"class:{class_info.package}.{class_info.name}"
        
        properties = {
            "modifiers": class_info.modifiers,
            "file_path": str(file_path) if file_path else None,
            "extends": class_info.extends,
            "implements": class_info.implements,
            "annotations": class_info.annotations,
            "javadoc": class_info.javadoc
        }
        
        if self.use_graph_db:
            self.conn.insert_entity(
                entity_id=class_id,
                entity_type="Class",
                name=class_info.name,
                package=class_info.package,
                project_id=self.project_id,
                properties=properties
            )
        else:
            # For NetworkX compatibility
            properties.update({
                "id": class_id,
                "type": "Class",
                "name": class_info.name,
                "package": class_info.package,
                "project_id": self.project_id
            })
            self.graph.add_node(class_id, node_type="Class", **properties)
        
        # Add package relationship
        package_id = self.add_package(class_info.package)
        self.add_relationship(package_id, class_id, "CONTAINS")
        
        return class_id
    
    def add_method(
        self,
        method_info: MethodInfo,
        class_id: str,
        embedding_id: Optional[str] = None
    ) -> str:
        """Add a method node"""
        method_id = f"method:{class_id}:{method_info.signature.name}"
        
        properties = {
            "signature": method_info.signature.to_string(),
            "return_type": method_info.signature.return_type,
            "parameters": method_info.signature.parameters,
            "modifiers": method_info.signature.modifiers,
            "annotations": method_info.signature.annotations,
            "source_code": method_info.source_code,
            "start_line": method_info.start_line,
            "end_line": method_info.end_line,
            "complexity": method_info.complexity,
            "loc": method_info.loc,
            "class_name": method_info.class_name,
            "embedding_id": embedding_id,
            "javadoc": method_info.javadoc
        }
        
        if self.use_graph_db:
            self.conn.insert_entity(
                entity_id=method_id,
                entity_type="Method",
                name=method_info.signature.name,
                package=method_info.package,
                project_id=self.project_id,
                properties=properties
            )
        else:
            # For NetworkX compatibility
            properties.update({
                "id": method_id,
                "type": "Method",
                "name": method_info.signature.name,
                "class_name": method_info.class_name,
                "package": method_info.package,
                "project_id": self.project_id
            })
            self.graph.add_node(method_id, node_type="Method", **properties)
        
        # Add class relationship
        self.add_relationship(class_id, method_id, "CONTAINS")
        
        return method_id
    
    def add_field(
        self,
        field_info: FieldInfo,
        class_id: str
    ) -> str:
        """Add a field node"""
        field_id = f"field:{class_id}:{field_info.name}"
        
        properties = {
            "field_type": field_info.type,
            "modifiers": field_info.modifiers,
            "initial_value": field_info.initial_value,
            "annotations": field_info.annotations
        }
        
        if self.use_graph_db:
            self.conn.insert_entity(
                entity_id=field_id,
                entity_type="Field",
                name=field_info.name,
                package=None,  # Fields don't have package directly
                project_id=self.project_id,
                properties=properties
            )
        else:
            # For NetworkX compatibility
            properties.update({
                "id": field_id,
                "type": "Field",
                "name": field_info.name,
                "project_id": self.project_id
            })
            self.graph.add_node(field_id, node_type="Field", **properties)
        
        # Add class relationship
        self.add_relationship(class_id, field_id, "CONTAINS")
        
        return field_id
    
    def add_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a relationship between nodes"""
        if properties is None:
            properties = {}
        
        if self.use_graph_db:
            self.conn.insert_relationship(
                source_id=from_id,
                target_id=to_id,
                rel_type=rel_type,
                project_id=self.project_id,
                properties=properties
            )
        else:
            # Check if both nodes exist before adding edge
            if from_id in self.graph.nodes and to_id in self.graph.nodes:
                self.graph.add_edge(from_id, to_id, rel_type=rel_type, **properties)
            else:
                logger.warning(f"Cannot add relationship {rel_type} from {from_id} to {to_id}: nodes don't exist")
                logger.debug(f"Available nodes: {list(self.graph.nodes)}")
    
    def add_method_calls(
        self,
        method_id: str,
        called_methods: List[str]
    ) -> None:
        """Add CALLS relationships for a method"""
        for called_method in called_methods:
            # Try to find the method in the graph
            target_method_id = self._find_method_by_name(called_method)
            if target_method_id:
                self.add_relationship(method_id, target_method_id, "CALLS")
    
    def add_field_usage(
        self,
        method_id: str,
        used_fields: List[str]
    ) -> None:
        """Add USES relationships for field access"""
        for field_name in used_fields:
            # Try to find the field in the same class
            field_id = self._find_field_by_name(method_id, field_name)
            if field_id:
                self.add_relationship(method_id, field_id, "USES")
    
    def add_semantic_connections(
        self,
        source_id: str,
        connections: List[Dict[str, Any]]
    ) -> None:
        """Add semantic connections from UniversalJavaParser"""
        for connection in connections:
            connection_type = connection.get('type', 'SEMANTIC')
            target = connection.get('target', '')
            
            if not target:
                continue
            
            # Try to find target entity in the graph
            target_id = self._find_entity_by_name(target)
            if target_id:
                self.add_relationship(source_id, target_id, connection_type)
            else:
                # Create a virtual entity for external references
                virtual_id = f"virtual:{target}"
                self.add_relationship(source_id, virtual_id, connection_type)
    
    def _find_method_by_name(self, method_name: str) -> Optional[str]:
        """Find method ID by name"""
        if self.use_graph_db:
            query = """
            SELECT id FROM entities 
            WHERE type = 'Method' AND name = ? AND project_id = ?
            LIMIT 1
            """
            results = self.conn.execute_and_fetch(query, (method_name, self.project_id))
            if results:
                return results[0]["id"]
        else:
            for node_id, data in self.graph.nodes(data=True):
                if data.get("type") == "Method" and data.get("name") == method_name:
                    return node_id
        return None
    
    def _find_field_by_name(self, method_id: str, field_name: str) -> Optional[str]:
        """Find field ID by name in the same class as method"""
        # Extract class_id from method_id
        # method_id format: method:class:com.test.TestClass:methodName
        parts = method_id.split(":")
        if len(parts) < 4:
            return None
        class_id = f"class:{parts[2]}"  # class:com.test.TestClass
        
        if self.use_graph_db:
            query = """
            SELECT e.id FROM entities e
            JOIN relationships r ON e.id = r.target_id
            WHERE r.source_id = ? AND r.rel_type = 'CONTAINS' 
            AND e.type = 'Field' AND e.name = ?
            LIMIT 1
            """
            results = self.conn.execute_and_fetch(query, (class_id, field_name))
            if results:
                return results[0]["id"]
        else:
            for neighbor in self.graph.neighbors(class_id):
                data = self.graph.nodes[neighbor]
                if data.get("type") == "Field" and data.get("name") == field_name:
                    return neighbor
        return None
    
    def _find_entity_by_name(self, entity_name: str) -> Optional[str]:
        """Find entity ID by name (any type)"""
        if self.use_graph_db:
            query = """
            SELECT id FROM entities 
            WHERE name = ? AND project_id = ?
            LIMIT 1
            """
            results = self.conn.execute_and_fetch(query, (entity_name, self.project_id))
            if results:
                return results[0]["id"]
        else:
            for node_id, data in self.graph.nodes(data=True):
                if data.get("name") == entity_name and data.get("project_id") == self.project_id:
                    return node_id
        return None
    
    def get_method_by_id(self, method_id: str) -> Optional[Dict[str, Any]]:
        """Get method data by ID"""
        if self.use_graph_db:
            return self.conn.get_entity_by_id(method_id)
        else:
            if method_id in self.graph:
                return self.graph.nodes[method_id]
        return None
    
    def get_class_by_id(self, class_id: str) -> Optional[Dict[str, Any]]:
        """Get class data by ID"""
        if self.use_graph_db:
            return self.conn.get_entity_by_id(class_id)
        else:
            if class_id in self.graph:
                return self.graph.nodes[class_id]
        return None
    
    def get_class_by_name(self, class_name: str) -> Optional[Dict[str, Any]]:
        """Get class data by name"""
        if self.use_graph_db:
            query = """
            SELECT * FROM entities 
            WHERE type = 'Class' AND name = ? AND project_id = ?
            LIMIT 1
            """
            results = self.conn.execute_and_fetch(query, (class_name, self.project_id))
            if results:
                class_data = results[0]
                # Parse JSON properties
                if class_data.get("properties"):
                    try:
                        import json
                        properties = json.loads(class_data["properties"])
                        # Merge properties into class_data
                        class_data.update(properties)
                    except (json.JSONDecodeError, TypeError):
                        pass  # Keep original properties if parsing fails
                return class_data
        else:
            # Search in graph nodes
            for node_id, node_data in self.graph.nodes.items():
                if node_data.get("type") == "Class" and node_data.get("name") == class_name:
                    return node_data
        return None
    
    def get_all_classes(self) -> List[Dict[str, Any]]:
        """Get all classes from the graph"""
        if self.use_graph_db:
            return self.conn.get_entities_by_type("Class", self.project_id)
        else:
            # Search in graph nodes
            classes = []
            for node_id, node_data in self.graph.nodes.items():
                if node_data.get("type") == "Class":
                    classes.append(node_data)
            return classes
    
    def get_all_methods(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all methods in the project"""
        if self.use_graph_db:
            query = """
            SELECT * FROM entities 
            WHERE type = 'Method' AND project_id = ?
            """
            params = (self.project_id,)
            if limit:
                query += " LIMIT ?"
                params = (self.project_id, limit)
            
            raw_methods = self.conn.execute_and_fetch(query, params)
            
            # Parse JSON properties for each method
            methods = []
            for method in raw_methods:
                if method.get("properties"):
                    try:
                        import json
                        properties = json.loads(method["properties"])
                        # Merge properties into method dict
                        method.update(properties)
                    except (json.JSONDecodeError, TypeError):
                        pass  # Keep original properties if parsing fails
                methods.append(method)
            
            return methods
        else:
            methods = []
            for node_id, data in self.graph.nodes(data=True):
                if data.get("type") == "Method":
                    methods.append(data)
                    if limit and len(methods) >= limit:
                        break
            return methods
    
    def get_method_dependencies(
        self,
        method_id: str,
        depth: int = 1
    ) -> Dict[str, Any]:
        """Get all dependencies of a method"""
        if self.use_graph_db:
            # For SQLite, we'll implement a simplified BFS using recursive queries
            # This is a basic implementation - could be optimized with CTEs for complex graphs
            dependencies = {
                "methods": [],
                "fields": [],
                "classes": []
            }
            
            # Get direct relationships
            relationships = self.conn.get_entity_relationships(method_id, "outgoing")
            
            for rel in relationships:
                target_id = rel["target_id"]
                target_entity = self.conn.get_entity_by_id(target_id)
                
                if target_entity:
                    entity_type = target_entity["type"]
                    if entity_type == "Method":
                        dependencies["methods"].append(target_entity)
                    elif entity_type == "Field":
                        dependencies["fields"].append(target_entity)
                    elif entity_type == "Class":
                        dependencies["classes"].append(target_entity)
            
            return dependencies
        else:
            # NetworkX implementation
            dependencies = {
                "methods": [],
                "fields": [],
                "classes": []
            }
            
            # BFS to depth
            visited = set()
            queue = [(method_id, 0)]
            
            while queue:
                node_id, current_depth = queue.pop(0)
                if node_id in visited or current_depth > depth:
                    continue
                
                visited.add(node_id)
                node_data = self.graph.nodes.get(node_id, {})
                node_type = node_data.get("type")
                
                if node_type == "Method" and node_id != method_id:
                    dependencies["methods"].append(node_data)
                elif node_type == "Field":
                    dependencies["fields"].append(node_data)
                elif node_type == "Class":
                    dependencies["classes"].append(node_data)
                
                # Add neighbors to queue
                if current_depth < depth:
                    for neighbor in self.graph.neighbors(node_id):
                        queue.append((neighbor, current_depth + 1))
            
            return dependencies
    
    def clear_project(self) -> None:
        """Clear all nodes for this project"""
        if self.use_graph_db:
            self.conn.clear_project(self.project_id)
            logger.info(f"Cleared project: {self.project_id}")
        else:
            nodes_to_remove = [
                n for n, d in self.graph.nodes(data=True)
                if d.get("project_id") == self.project_id
            ]
            self.graph.remove_nodes_from(nodes_to_remove)
            logger.info(f"Cleared {len(nodes_to_remove)} nodes from project")


if __name__ == "__main__":
    # Test the graph builder
    print("Testing CodeGraph...")
    
    # Use NetworkX for testing
    graph = CodeGraph(use_graph_db=False, project_id="test-project")
    
    # Create test data
    from ..parser import MethodSignature, FieldInfo, ClassInfo, MethodInfo
    
    class_info = ClassInfo(
        name="Calculator",
        package="com.example",
        modifiers=["public"],
        fields=[],
        methods=[]
    )
    
    class_id = graph.add_class(class_info)
    print(f"✅ Added class: {class_id}")
    
    # Add method
    method_sig = MethodSignature(
        name="add",
        return_type="int",
        parameters=[{"name": "a", "type": "int"}, {"name": "b", "type": "int"}],
        modifiers=["public"],
        annotations=[]
    )
    
    method_info = MethodInfo(
        signature=method_sig,
        source_code="public int add(int a, int b) { return a + b; }",
        start_line=10,
        end_line=12,
        complexity=1,
        loc=3,
        class_name="Calculator",
        package="com.example"
    )
    
    method_id = graph.add_method(method_info, class_id)
    print(f"✅ Added method: {method_id}")
    
    # Get all methods
    methods = graph.get_all_methods()
    print(f"✅ Total methods: {len(methods)}")
    
    print("\n✅ Graph builder test passed!")

