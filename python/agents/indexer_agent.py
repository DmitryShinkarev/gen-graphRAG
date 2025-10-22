"""
IndexerAgent - Scans and indexes Java projects.

Responsibilities:
- Scan project directory structure
- Parse all Java files
- Build code graph in Memgraph
- Generate embeddings for methods
- Store embeddings in Qdrant

Pattern: Context Engineering (4.1)
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from tqdm import tqdm
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from agents.base import BaseJavaAgent, AgentState, BaseTool
from agents.tools import (
    ScanProjectTool,
    ParseJavaFileTool,
    BuildGraphTool,
    GenerateEmbeddingTool,
    StoreVectorTool
)
from graph.graph_builder import CodeGraph
from embedding import CodeEmbedder, VectorStore
from logger import get_logger

logger = get_logger(__name__)


class IndexerAgent(BaseJavaAgent):
    """
    Agent responsible for indexing Java projects.
    
    Workflow:
    1. Scan project directory
    2. Parse all Java files
    3. Build code graph
    4. Generate method embeddings
    5. Store in vector database
    """
    
    def __init__(
        self,
        graph: CodeGraph,
        embedder: CodeEmbedder,
        vector_store: VectorStore,
        project_id: Optional[str] = None
    ):
        """
        Initialize IndexerAgent.
        
        Args:
            graph: Code graph instance
            embedder: Code embedder instance
            vector_store: Vector store instance
            project_id: Optional project ID
        """
        # Initialize tools
        tools = [
            ScanProjectTool(),
            ParseJavaFileTool(),
            BuildGraphTool(graph),
            GenerateEmbeddingTool(embedder),
            StoreVectorTool(vector_store)
        ]
        
        super().__init__(
            name="IndexerAgent",
            role="Java project indexing and analysis",
            tools=tools,
            temperature=0.3  # Lower temperature for deterministic parsing
        )
        
        self.graph = graph
        self.embedder = embedder
        self.vector_store = vector_store
        self.project_id = project_id or "default"
    
    async def execute(self, state: AgentState) -> AgentState:
        """
        Execute indexing workflow.
        
        Args:
            state: Current agent state
        
        Returns:
            Updated state with indexing results
        """
        logger.info(f"[{self.name}] Starting indexing for: {state.project_path}")
        
        try:
            # Step 1: Scan project
            scan_result = await self._scan_project(state)
            if "error" in scan_result:
                self.log_error(f"Scan failed: {scan_result['error']}", state)
                return state
            
            self.log_step(f"Scanned {scan_result['total_files']} Java files", state)
            
            # Step 2: Parse and build graph
            java_files = scan_result["java_files"]
            parse_results = await self._parse_and_build_graph(java_files, state)
            
            self.log_step(
                f"Parsed {len(parse_results['classes'])} classes, "
                f"{len(parse_results['methods'])} methods",
                state
            )
            
            # Step 3: Generate embeddings
            if parse_results["methods"]:
                embedding_result = await self._generate_embeddings(
                    parse_results["methods"],
                    state
                )
                
                if "error" in embedding_result:
                    self.log_error(f"Embedding generation failed: {embedding_result['error']}", state)
                else:
                    self.log_step(
                        f"Generated {embedding_result['num_embeddings']} embeddings",
                        state
                    )
                    
                    # Step 4: Store in vector database
                    storage_result = await self._store_embeddings(
                        embedding_result,
                        parse_results["methods"],
                        state
                    )
                    
                    if "error" in storage_result:
                        self.log_error(f"Vector storage failed: {storage_result['error']}", state)
                    else:
                        self.log_step(
                            f"Stored {storage_result['num_stored']} vectors",
                            state
                        )
            
            # Update state
            state.project_id = self.project_id
            state.indexed_files = java_files
            state.parsed_classes = {
                cls["class_id"]: cls 
                for cls in parse_results["classes"]
            }
            
            logger.info(f"[{self.name}] Indexing completed successfully")
            return state
            
        except Exception as e:
            error_msg = f"Indexing failed: {str(e)}"
            logger.exception(f"[{self.name}] {error_msg}")
            self.log_error(error_msg, state)
            return state
    
    async def _scan_project(self, state: AgentState) -> Dict[str, Any]:
        """Scan project directory"""
        logger.info(f"[{self.name}] Scanning project: {state.project_path}")
        
        result = await self.use_tool(
            "scan_project",
            project_path=state.project_path
        )
        
        return result
    
    async def _parse_and_build_graph(
        self,
        java_files: List[str],
        state: AgentState
    ) -> Dict[str, List[Dict]]:
        """
        Parse Java files and build code graph.
        
        Returns:
            Dictionary with parsed classes and methods
        """
        logger.info(f"[{self.name}] Parsing {len(java_files)} files...")
        
        classes = []
        methods = []
        
        # Progress bar
        for file_path in tqdm(java_files, desc="Parsing files"):
            try:
                # Parse file
                parse_result = await self.use_tool(
                    "parse_java_file",
                    file_path=file_path
                )
                
                if "error" in parse_result:
                    logger.warning(f"Failed to parse {file_path}: {parse_result['error']}")
                    continue
                
                class_info = parse_result["class_info"]
                
                # Build graph
                graph_result = await self.use_tool(
                    "build_graph",
                    class_info=class_info,
                    file_path=file_path
                )
                
                if "error" in graph_result:
                    logger.warning(f"Failed to build graph for {file_path}: {graph_result['error']}")
                    continue
                
                # Collect class data
                class_data = {
                    "class_id": graph_result["class_id"],
                    "file_path": file_path,
                    "class_info": class_info,
                    "graph_result": graph_result
                }
                classes.append(class_data)
                
                # Collect method data
                for method_data in class_info.get("methods", []):
                    method_entry = {
                        **method_data,
                        "file_path": file_path,
                        "class_id": graph_result["class_id"]
                    }
                    methods.append(method_entry)
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                continue
        
        logger.info(
            f"[{self.name}] Parsed {len(classes)} classes, "
            f"{len(methods)} methods"
        )
        
        return {
            "classes": classes,
            "methods": methods
        }
    
    async def _generate_embeddings(
        self,
        methods: List[Dict],
        state: AgentState
    ) -> Dict[str, Any]:
        """Generate embeddings for methods"""
        logger.info(f"[{self.name}] Generating embeddings for {len(methods)} methods...")
        
        result = await self.use_tool(
            "generate_embedding",
            methods=methods
        )
        
        return result
    
    async def _store_embeddings(
        self,
        embedding_result: Dict[str, Any],
        methods: List[Dict],
        state: AgentState
    ) -> Dict[str, Any]:
        """Store embeddings in vector database"""
        logger.info(f"[{self.name}] Storing embeddings...")
        
        embeddings = embedding_result["embeddings"]
        
        # Prepare payloads
        payloads = []
        for method in methods:
            payload = {
                "method_name": method["name"],
                "class_name": method["class_name"],
                "package": method["package"],
                "file_path": method["file_path"],
                "signature": method.get("full_signature", ""),
                "source_code": method.get("source_code", ""),  # ✅ ADDED: for context in prompts
                "complexity": method.get("complexity", 0),
                "loc": method.get("loc", 0),
                "start_line": method.get("start_line", 0),
                "end_line": method.get("end_line", 0),
                "project_id": self.project_id,
                "class_id": method.get("class_id", "")
            }
            payloads.append(payload)
        
        result = await self.use_tool(
            "store_vector",
            embeddings=embeddings,
            payloads=payloads
        )
        
        return result
    
    async def get_indexing_stats(self) -> Dict[str, Any]:
        """Get indexing statistics"""
        # Get graph stats
        graph_methods = self.graph.get_all_methods()
        
        # Get vector store stats
        vector_stats = self.vector_store.get_collection_info()
        
        return {
            "project_id": self.project_id,
            "graph": {
                "methods_count": len(graph_methods)
            },
            "vector_store": vector_stats
        }


if __name__ == "__main__":
    # Test the IndexerAgent
    import asyncio
    import sys
    
    async def test_indexer():
        # Initialize components (using NetworkX for testing)
        from ..graph.graph_builder import CodeGraph
        from ..embedding import CodeEmbedder, VectorStore
        
        graph = CodeGraph(use_graph_db=False, project_id="test")
        embedder = CodeEmbedder()
        vector_store = VectorStore(collection_name="test_java_methods")
        
        # Create agent
        agent = IndexerAgent(
            graph=graph,
            embedder=embedder,
            vector_store=vector_store,
            project_id="test"
        )
        
        # Create test state
        state = AgentState()
        
        # Use a test Java project or current directory
        if len(sys.argv) > 1:
            state.project_path = sys.argv[1]
        else:
            state.project_path = str(Path.cwd())
        
        print(f"Testing IndexerAgent with project: {state.project_path}")
        
        # Execute
        result_state = await agent.execute(state)
        
        # Print results
        print("\n" + "="*60)
        print("INDEXING RESULTS")
        print("="*60)
        print(f"Indexed files: {len(result_state.indexed_files)}")
        print(f"Parsed classes: {len(result_state.parsed_classes)}")
        print(f"Steps completed: {len(result_state.steps_completed)}")
        print("\nSteps:")
        for step in result_state.steps_completed:
            print(f"  ✅ {step}")
        
        if result_state.errors:
            print("\nErrors:")
            for error in result_state.errors:
                print(f"  ❌ {error}")
        
        # Get stats
        stats = await agent.get_indexing_stats()
        print("\nStatistics:")
        print(f"  Methods in graph: {stats['graph']['methods_count']}")
        print(f"  Vectors in store: {stats['vector_store'].get('points_count', 0)}")
        
        print("\n✅ IndexerAgent test completed!")
    
    asyncio.run(test_indexer())

