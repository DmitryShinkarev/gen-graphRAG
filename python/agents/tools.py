"""
Tools for Java test generation agents.
Each tool performs a specific task and can be used by multiple agents.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import asyncio
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from agents.base import BaseTool
from parser import JavaParser, ClassInfo
from parser.universal_java_parser import UniversalJavaParser
from graph import MerkleTree, load_gitignore
from graph.graph_builder import CodeGraph
from graph.markov_walker import MarkovGraphWalker
from embedding import CodeEmbedder, VectorStore
from logger import get_logger

logger = get_logger(__name__)


class ScanProjectTool(BaseTool):
    """Scan Java project directory structure"""
    
    name = "scan_project"
    description = "Scan a Java project directory and find all .java files"
    
    async def execute(self, project_path: str, **kwargs) -> Dict[str, Any]:
        """
        Scan project and return file list.
        
        Args:
            project_path: Path to project root
        
        Returns:
            Dictionary with file list and statistics
        """
        try:
            project_path = Path(project_path)
            
            if not project_path.exists():
                return {"error": f"Project path does not exist: {project_path}"}
            
            # Load gitignore patterns
            gitignore_patterns = load_gitignore(project_path)
            
            # Build Merkle tree
            tree = MerkleTree(project_path, gitignore_patterns)
            root = tree.build()
            
            if not root:
                return {"error": "Failed to build project tree"}
            
            # Get all Java files
            java_files = tree.get_all_files({'.java'})
            
            return {
                "project_path": str(project_path),
                "total_files": len(java_files),
                "java_files": [str(f) for f in java_files],
                "tree_hash": root.hash
            }
        except Exception as e:
            logger.error(f"ScanProjectTool failed: {e}")
            return {"error": str(e)}


class ParseJavaFileTool(BaseTool):
    """Parse a Java source file"""
    
    name = "parse_java_file"
    description = "Parse a Java source file and extract classes, methods, fields"
    
    def __init__(self):
        super().__init__()
        self.parser = UniversalJavaParser()
    
    async def execute(self, file_path: str, **kwargs) -> Dict[str, Any]:
        """
        Parse Java file.
        
        Args:
            file_path: Path to Java file
        
        Returns:
            Parsed class information
        """
        print(f"[DEBUG] ParseJavaFileTool.execute called with file_path: {file_path}")
        logger.info(f"ParseJavaFileTool.execute called with file_path: {file_path}")
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return {"error": f"File does not exist: {file_path}"}
            
            class_info = self.parser.parse_file(file_path)
            
            if not class_info:
                logger.error(f"Parser returned None for file: {file_path}")
                return {"error": f"Failed to parse file: {file_path}"}
            
            logger.info(f"Successfully parsed {file_path}: {class_info.name} with {len(class_info.methods)} methods")
            
            return {
                "file_path": str(file_path),
                "class_info": class_info.to_dict()
            }
        except Exception as e:
            logger.error(f"ParseJavaFileTool failed: {e}")
            return {"error": str(e)}


class BuildGraphTool(BaseTool):
    """Build code graph from parsed classes"""
    
    name = "build_graph"
    description = "Build a graph database of code relationships"
    
    def __init__(self, graph: CodeGraph):
        super().__init__()
        self.graph = graph
    
    async def execute(
        self,
        class_info: Dict[str, Any],
        file_path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Add class to graph.
        
        Args:
            class_info: Parsed class information
            file_path: Path to source file
        
        Returns:
            Graph node IDs
        """
        try:
            # Convert dict to ClassInfo
            from parser import ClassInfo, MethodInfo, FieldInfo, MethodSignature
            
            # Reconstruct ClassInfo object
            class_obj = ClassInfo(
                name=class_info["name"],
                package=class_info["package"],
                modifiers=class_info["modifiers"],
                extends=class_info.get("extends"),
                implements=class_info.get("implements", []),
                annotations=class_info.get("annotations", []),
                javadoc=class_info.get("javadoc")
            )
            
            # Add class to graph
            class_id = self.graph.add_class(class_obj, file_path)
            
            # Add fields
            field_ids = []
            for field_data in class_info.get("fields", []):
                field_obj = FieldInfo(
                    name=field_data["name"],
                    type=field_data["type"],
                    modifiers=field_data["modifiers"],
                    initial_value=field_data.get("initial_value"),
                    annotations=field_data.get("annotations", [])
                )
                field_id = self.graph.add_field(field_obj, class_id)
                field_ids.append(field_id)
            
            # Add methods
            method_ids = []
            for method_data in class_info.get("methods", []):
                sig_data = method_data
                method_sig = MethodSignature(
                    name=sig_data["name"],
                    return_type=sig_data["return_type"],
                    parameters=sig_data["parameters"],
                    modifiers=sig_data["modifiers"],
                    annotations=sig_data["annotations"]
                )
                
                method_obj = MethodInfo(
                    signature=method_sig,
                    source_code=method_data["source_code"],
                    start_line=method_data["start_line"],
                    end_line=method_data["end_line"],
                    complexity=method_data["complexity"],
                    loc=method_data["loc"],
                    class_name=method_data["class_name"],
                    package=method_data["package"],
                    javadoc=method_data.get("javadoc"),
                    calls=method_data.get("calls", []),
                    used_fields=method_data.get("used_fields", [])
                )
                
                method_id = self.graph.add_method(method_obj, class_id)
                method_ids.append(method_id)
                
                # Add relationships
                if method_obj.calls:
                    self.graph.add_method_calls(method_id, method_obj.calls)
                
                if method_obj.used_fields:
                    self.graph.add_field_usage(method_id, method_obj.used_fields)
                
                # Add semantic connections from UniversalJavaParser
                if hasattr(method_obj, 'method_calls') and method_obj.method_calls:
                    self.graph.add_method_calls(method_id, method_obj.method_calls)
                
                if hasattr(method_obj, 'field_usage') and method_obj.field_usage:
                    self.graph.add_field_usage(method_id, method_obj.field_usage)
                
                if hasattr(method_obj, 'semantic_connections') and method_obj.semantic_connections:
                    self.graph.add_semantic_connections(method_id, method_obj.semantic_connections)
            
            return {
                "class_id": class_id,
                "method_ids": method_ids,
                "field_ids": field_ids,
                "total_nodes": 1 + len(method_ids) + len(field_ids)
            }
        except Exception as e:
            logger.error(f"BuildGraphTool failed: {e}")
            return {"error": str(e)}


class GenerateEmbeddingTool(BaseTool):
    """Generate code embeddings"""
    
    name = "generate_embedding"
    description = "Generate vector embedding for code"
    
    def __init__(self, embedder: CodeEmbedder):
        super().__init__()
        self.embedder = embedder
    
    async def execute(
        self,
        methods: List[Dict[str, Any]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate embeddings for methods.
        
        Args:
            methods: List of method dictionaries
        
        Returns:
            List of embeddings
        """
        try:
            embeddings = self.embedder.embed_code_methods_batch(
                methods,
                show_progress=True
            )
            
            return {
                "num_embeddings": len(embeddings),
                "embeddings": embeddings,
                "dimension": self.embedder.get_embedding_dimension()
            }
        except Exception as e:
            logger.error(f"GenerateEmbeddingTool failed: {e}")
            return {"error": str(e)}


class StoreVectorTool(BaseTool):
    """Store embeddings in vector database"""
    
    name = "store_vector"
    description = "Store code embeddings in Qdrant vector database"
    
    def __init__(self, vector_store: VectorStore):
        super().__init__()
        self.vector_store = vector_store
    
    async def execute(
        self,
        embeddings: List,
        payloads: List[Dict[str, Any]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Store embeddings.
        
        Args:
            embeddings: List of embedding vectors
            payloads: List of metadata dictionaries
        
        Returns:
            Storage result
        """
        try:
            point_ids = self.vector_store.upsert_batch(
                vectors=embeddings,
                payloads=payloads,
                batch_size=100
            )
            
            return {
                "num_stored": len(point_ids),
                "point_ids": point_ids
            }
        except Exception as e:
            logger.error(f"StoreVectorTool failed: {e}")
            return {"error": str(e)}


class MarkovWalkTool(BaseTool):
    """Perform Markov walk on code graph"""
    
    name = "markov_walk"
    description = "Explore code dependencies using Markov random walk"
    
    def __init__(self, walker: MarkovGraphWalker):
        super().__init__()
        self.walker = walker
    
    async def execute(
        self,
        start_node_id: str,
        num_steps: int = 10,
        num_walks: int = 5,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Perform Markov walk.
        
        Args:
            start_node_id: Starting node ID
            num_steps: Steps per walk
            num_walks: Number of walks
        
        Returns:
            Walk results with visited nodes
        """
        try:
            result = self.walker.walk(
                start_node_id=start_node_id,
                num_steps=num_steps,
                num_walks=num_walks,
                include_reverse=True
            )
            
            return result
        except Exception as e:
            logger.error(f"MarkovWalkTool failed: {e}")
            return {"error": str(e)}


class VectorSearchTool(BaseTool):
    """Search vector database for similar code"""
    
    name = "vector_search"
    description = "Search for semantically similar code using vector embeddings"
    
    def __init__(self, vector_store: VectorStore, embedder: CodeEmbedder):
        super().__init__()
        self.vector_store = vector_store
        self.embedder = embedder
    
    async def execute(
        self,
        query_text: str,
        limit: int = 10,
        filter_conditions: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search for similar code.
        
        Args:
            query_text: Query text
            limit: Maximum results
            filter_conditions: Optional filters
        
        Returns:
            Search results
        """
        try:
            # Generate query embedding
            query_embedding = self.embedder.embed_text(query_text)
            
            # Search
            results = self.vector_store.search(
                query_vector=query_embedding,
                limit=limit,
                filter_conditions=filter_conditions
            )
            
            return {
                "num_results": len(results),
                "results": results
            }
        except Exception as e:
            logger.error(f"VectorSearchTool failed: {e}")
            return {"error": str(e)}


# Export all tools
__all__ = [
    "ScanProjectTool",
    "ParseJavaFileTool",
    "BuildGraphTool",
    "GenerateEmbeddingTool",
    "StoreVectorTool",
    "MarkovWalkTool",
    "VectorSearchTool"
]

