"""
ResearcherAgent - Gathers context for test generation.

Responsibilities:
- Perform Markov walks on code graph
- Execute vector similarity search
- Collect dependencies and related methods
- Rank and merge results

Pattern: Context Engineering (4.1)
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict

from agents.base import BaseJavaAgent, AgentState, BaseTool
from agents.tools import MarkovWalkTool, VectorSearchTool
from graph.graph_builder import CodeGraph
from graph.markov_walker import MarkovGraphWalker
from graph.enhanced_markov_walker import EnhancedMarkovWalker
from graph.graph_searcher import GraphSearcher
from embedding import CodeEmbedder, VectorStore
from logger import get_logger

logger = get_logger(__name__)


class ResearcherAgent(BaseJavaAgent):
    """
    Agent responsible for context research.
    
    Workflow:
    1. Perform Markov walk from target method
    2. Execute vector similarity search
    3. Collect dependencies
    4. Rank and merge results
    5. Return rich context for test generation
    """
    
    def __init__(
        self,
        graph: CodeGraph,
        embedder: CodeEmbedder,
        vector_store: VectorStore,
        markov_walker: Optional[MarkovGraphWalker] = None
    ):
        """
        Initialize ResearcherAgent.
        
        Args:
            graph: Code graph instance
            embedder: Code embedder instance
            vector_store: Vector store instance
            markov_walker: Optional Markov walker (created if None)
        """
        # Initialize Enhanced Markov walker if not provided
        if markov_walker is None:
            markov_walker = EnhancedMarkovWalker(graph)
        
        # Initialize tools
        tools = [
            MarkovWalkTool(markov_walker),
            VectorSearchTool(vector_store, embedder)
        ]
        
        super().__init__(
            name="ResearcherAgent",
            role="Context research and dependency analysis",
            tools=tools,
            temperature=0.3
        )
        
        self.graph = graph
        self.embedder = embedder
        self.vector_store = vector_store
        self.markov_walker = markov_walker
        
        # Initialize graph searcher for optimized method search
        if hasattr(graph, 'conn') and graph.conn:
            self.searcher = GraphSearcher(graph.conn)
        else:
            self.searcher = None
        
        logger.info(f"Initialized {self.name} with GraphSearcher: {'✅' if self.searcher else '❌'}")
    
    async def execute(self, state: AgentState) -> AgentState:
        """
        Execute context research workflow.
        
        Args:
            state: Current agent state with target_method or target_file
        
        Returns:
            Updated state with method_context and dependencies
        """
        logger.info("="*80)
        logger.info("="*80)
        logger.info(f"[{self.name}] 🚀 STARTING RAG CONTEXT RESEARCH")
        logger.info(f"  Target method: {state.target_method}")
        logger.info(f"  Project ID: {state.project_id}")
        logger.info("="*80)
        logger.info("="*80)
        
        try:
            # Step 1: Find target method in graph
            logger.info(f"[{self.name}] Step 1/5: 🔍 Finding target method in graph...")
            method_id = await self._find_method_id(state)
            
            if not method_id:
                error_msg = f"Target method not found: {state.target_method}"
                logger.error(f"  ❌ {error_msg}")
                self.log_error(error_msg, state)
                return state
            
            logger.info(f"  ✅ Found method ID: {method_id}")
            self.log_step(f"Found method: {method_id}", state)
            logger.info("")
            
            # Step 2: Markov walk for graph-based context
            logger.info(f"[{self.name}] Step 2/5: 🕸️  Markov walk for graph-based context...")
            logger.info("")
            graph_context = await self._graph_walk_context(method_id, state)
            self.log_step(f"Graph walk: {graph_context.get('total_nodes', 0)} nodes", state)
            logger.info("")
            
            # Step 3: Vector search for semantic context
            logger.info(f"[{self.name}] Step 3/5: 🔍 Vector search for semantic context...")
            logger.info("")
            vector_context = await self._vector_search_context(method_id, state)
            self.log_step(f"Vector search: {len(vector_context.get('results', []))} results", state)
            logger.info("")
            
            # Step 4: Get direct dependencies
            logger.info(f"[{self.name}] Step 4/5: 🔗 Getting direct dependencies...")
            logger.info("")
            dependencies = await self._get_dependencies(method_id, state)
            self.log_step(f"Dependencies: {len(dependencies.get('methods', []))} methods", state)
            logger.info("")
            
            # Step 5: Merge and rank context
            logger.info(f"[{self.name}] Step 5/5: 🎯 Merging and ranking all context...")
            logger.info("")
            merged_context = self._merge_context(
                graph_context,
                vector_context,
                dependencies,
                method_id
            )
            
            # Update state
            state.method_context = merged_context
            state.dependencies = dependencies
            state.similar_methods = vector_context.get('results', [])
            
            logger.info("="*80)
            logger.info(f"[{self.name}] ✅ RAG CONTEXT RESEARCH COMPLETED SUCCESSFULLY")
            logger.info("="*80)
            logger.info(f"  📊 Final Statistics:")
            logger.info(f"    • Total methods in context: {merged_context.get('total_methods', 0)}")
            logger.info(f"    • Graph contribution: {merged_context.get('graph_contribution', 0)} methods")
            logger.info(f"    • Vector contribution: {merged_context.get('vector_contribution', 0)} methods")
            logger.info(f"    • Direct dependencies: {len(dependencies.get('methods', []))}")
            logger.info(f"    • Similar methods found: {len(state.similar_methods)}")
            logger.info("="*80)
            logger.info("="*80)
            logger.info("")
            
            return state
            
        except Exception as e:
            error_msg = f"Context research failed: {str(e)}"
            logger.exception(f"[{self.name}] {error_msg}")
            self.log_error(error_msg, state)
            return state
    
    async def _find_method_id(self, state: AgentState) -> Optional[str]:
        """Find method ID in graph by name or signature using optimized GraphSearcher"""
        target = state.target_method
        class_hint = state.metadata.get("class_name") if state.metadata else None
        project_id = state.project_id or "default"
        
        logger.info(f"  🔎 Searching for method: '{target}'" + (f" in class '{class_hint}'" if class_hint else ""))
        
        if not target:
            return None
        
        # Use optimized GraphSearcher if available
        if self.searcher:
            try:
                # Check if target is already a full method ID
                if target.startswith("method:class:"):
                    method = self.searcher.get_method_by_id(target, project_id)
                    if method:
                        logger.info(f"  ✅ Full ID match found: {target}")
                        return target
                    else:
                        logger.warning(f"  ❌ Full method ID not found: {target}")
                        return None
                
                # Use optimized search with class priority
                method = self.searcher.find_method_by_signature(
                    method_name=target,
                    class_name=class_hint,
                    project_id=project_id,
                    exact_match=True
                )
                
                if method:
                    method_id = method.get("id")
                    method_class = method.get("package", "unknown")
                    method_name = method.get("name", "unknown")
                    
                    logger.info(f"  ✅ Found method: {method_class}.{method_name} (ID: {method_id})")
                    return method_id
                
                # Try fuzzy search if exact match failed
                if class_hint:
                    logger.info(f"  ⚠️  No exact match in class '{class_hint}', trying fuzzy search...")
                    method = self.searcher.find_method_by_signature(
                        method_name=target,
                        class_name=class_hint,
                        project_id=project_id,
                        exact_match=False
                    )
                    
                    if method:
                        method_id = method.get("id")
                        method_class = method.get("package", "unknown")
                        method_name = method.get("name", "unknown")
                        
                        logger.info(f"  ✅ Fuzzy match found: {method_class}.{method_name} (ID: {method_id})")
                        return method_id
                
                # If class hint was provided but no match found, show alternatives
                if class_hint:
                    logger.error(f"  ❌ Method '{target}' not found in class '{class_hint}'")
                    
                    # Search for methods with same name in other classes
                    search_result = self.searcher.search_methods(
                        name_pattern=target,
                        project_id=project_id,
                        limit=5
                    )
                    
                    if search_result['methods']:
                        logger.info(f"     Found {len(search_result['methods'])} methods with name '{target}' in other classes:")
                        for method in search_result['methods'][:3]:
                            method_class = method.get("package", "unknown")
                            method_name = method.get("name", "unknown")
                            logger.info(f"       - {method_class}.{method_name}")
                        logger.info(f"     Tip: Check class name or use full method ID")
                    else:
                        logger.info(f"     No methods found with name '{target}'")
                else:
                    logger.error(f"  ❌ Method '{target}' not found")
                
                return None
                
            except Exception as e:
                logger.error(f"  ❌ Error in GraphSearcher: {e}")
                # Fall back to original method
                return await self._find_method_id_fallback(state)
        else:
            # Fall back to original method if GraphSearcher not available
            return await self._find_method_id_fallback(state)
    
    async def _find_method_id_fallback(self, state: AgentState) -> Optional[str]:
        """Fallback method for finding method ID (original implementation)"""
        target = state.target_method
        class_hint = state.metadata.get("class_name") if state.metadata else None
        
        logger.info(f"  🔄 Using fallback search for method: '{target}'")
        
        if not target:
            return None
        
        # Try to find method in graph
        methods = self.graph.get_all_methods()
        logger.info(f"  📊 Searching through {len(methods)} methods in graph...")
        
        class_matches = []  # Matches in specified class (highest priority)
        exact_matches = []  # Exact matches in other classes
        
        # Check if target is already a full method ID
        if target.startswith("method:class:"):
            # Full ID provided, try to find exact match
            for method in methods:
                if method.get("id") == target:
                    logger.info(f"  ✅ Full ID match found: {target}")
                    return target
            logger.warning(f"  ❌ Full method ID not found: {target}")
            return None
        
        # Search for matches
        for method in methods:
            method_id = method.get("id")
            method_name = method.get("name")
            method_class = method.get("class_name", "")
            method_signature = method.get("signature")
            
            # Exact match by name, signature, or ID
            if target in [method_name, method_signature, method_id]:
                # Priority 1: Match in specified class
                if class_hint and class_hint in method_class:
                    class_matches.append((method_id, method_name, method_class))
                else:
                    exact_matches.append((method_id, method_name, method_class))
        
        # Return class match if found
        if class_matches:
            if len(class_matches) == 1:
                method_id, method_name, method_class = class_matches[0]
                logger.info(f"  ✅ Exact match in specified class: {method_class}.{method_name}")
                return method_id
            else:
                # Multiple matches in same class (e.g., overloaded methods)
                method_id, method_name, method_class = class_matches[0]
                logger.warning(f"  ⚠️  Multiple matches in class '{class_hint}': {len(class_matches)} methods")
                logger.info(f"  ✅ Using first match: {method_class}.{method_name}")
                logger.info(f"     Tip: Use full method ID for exact match: {method_id}")
                return method_id
        
        # If class hint was provided but no match found, fail
        if class_hint and not class_matches:
            if exact_matches:
                logger.error(f"  ❌ Method '{target}' not found in class '{class_hint}'")
                logger.info(f"     Found {len(exact_matches)} methods with name '{target}' in other classes:")
                for _, name, cls in exact_matches[:3]:
                    logger.info(f"       - {cls}.{name}")
                logger.info(f"     Tip: Check class name or use full method ID")
            else:
                logger.error(f"  ❌ Method '{target}' not found in class '{class_hint}'")
            return None
        
        # No class hint provided, check exact matches
        if exact_matches:
            if len(exact_matches) == 1:
                method_id, method_name, method_class = exact_matches[0]
                logger.info(f"  ✅ Exact match found: {method_class}.{method_name}")
                return method_id
            else:
                # Multiple matches without class hint - require disambiguation
                logger.error(f"  ❌ Ambiguous: Found {len(exact_matches)} methods named '{target}':")
                for method_id, name, cls in exact_matches[:5]:
                    logger.info(f"       - {cls}.{name} (ID: {method_id})")
                logger.info(f"     Tip: Specify class_name parameter or use full method ID")
                return None
        
        logger.warning(f"  ❌ No match found for: '{target}'")
        return None
    
    async def _graph_walk_context(
        self,
        method_id: str,
        state: AgentState
    ) -> Dict[str, Any]:
        """Enhanced Markov walk with adaptive weights and hybrid search"""
        logger.info("="*80)
        logger.info(f"[{self.name}] 🕸️  ENHANCED MARKOV WALK - Adaptive weights + Hybrid search")
        logger.info("="*80)
        
        # Get vector guidance first (for hybrid search)
        method_data = self.graph.get_method_by_id(method_id)
        vector_guidance = None
        
        if method_data:
            query_text = self._build_query_from_method(method_data)
            vector_result = await self.use_tool(
                "vector_search",
                query_text=query_text,
                limit=5,  # Fewer results for guidance
                filter_conditions=None
            )
            
            if "error" not in vector_result:
                vector_guidance = vector_result
                logger.info(f"  🔗 Vector guidance: {len(vector_guidance.get('results', []))} nodes")
        
        # Perform enhanced walk with improved parameters
        if isinstance(self.markov_walker, EnhancedMarkovWalker):
            result = self.markov_walker.walk(
                start_node_id=method_id,
                num_steps=20,  # Increased from 10 to 20 for deeper exploration
                num_walks=12,  # Increased from 5 to 12 for better coverage
                include_reverse=True,
                vector_guidance=vector_guidance
            )
        else:
            # Fallback to original walker with improved parameters
            result = await self.use_tool(
                "markov_walk",
                start_node_id=method_id,
                num_steps=20,  # Increased from 10 to 20
                num_walks=12   # Increased from 5 to 12
            )
        
        if "error" in result:
            logger.warning(f"Markov walk failed: {result['error']}")
            return {"total_nodes": 0, "top_nodes": []}
        
        # Enhanced logging
        if "project_analysis" in result:
            analysis = result["project_analysis"]
            logger.info(f"📊 Project Analysis:")
            logger.info(f"  • Type: {analysis['type']}")
            logger.info(f"  • Methods: {analysis['characteristics']['total_methods']}")
            logger.info(f"  • Avg Complexity: {analysis['characteristics']['average_complexity']:.1f}")
        
        if "weight_adaptation" in result:
            adaptation = result["weight_adaptation"]
            logger.info(f"⚙️  Weight Adaptation:")
            logger.info(f"  • Reason: {adaptation['adaptation_reason']}")
            for rel_type, weight in adaptation['adapted_weights'].items():
                base_weight = adaptation['base_weights'].get(rel_type, weight)
                if abs(weight - base_weight) > 0.1:
                    change = (weight - base_weight) / base_weight * 100
                    logger.info(f"  • {rel_type}: {base_weight:.2f} → {weight:.2f} ({change:+.1f}%)")
        
        if result.get("vector_guidance_used"):
            logger.info(f"🔗 Hybrid Search: {result['guided_nodes']} nodes guided by vectors")
        
        # Detailed logging of results
        logger.info(f"📊 Enhanced Walk Results:")
        logger.info(f"  • Total nodes visited: {result.get('total_nodes', 0)}")
        logger.info(f"  • Num walks: 12, Steps per walk: 20")
        
        top_nodes = result.get('top_nodes', [])
        if top_nodes:
            logger.info(f"  • Top {len(top_nodes)} nodes by visit frequency:")
            for i, node in enumerate(top_nodes[:10], 1):
                node_id = node.get('id', 'unknown')
                visit_prob = node.get('visit_prob', 0)
                visits = node.get('visit_count', 0)
                guidance_score = node.get('guidance_score', 0)
                
                guidance_info = f" (guidance: {guidance_score:.2f})" if guidance_score > 0 else ""
                logger.info(f"    {i:2d}. {node_id[:50]:50s} | prob: {visit_prob:.3f} | visits: {visits}{guidance_info}")
        
        logger.info("-"*80)
        
        # Check if we need fallback strategies due to low connectivity
        total_nodes = result.get('total_nodes', 0)
        top_nodes = result.get('top_nodes', [])
        
        if total_nodes < 3 or len(top_nodes) < 2:
            logger.warning(f"⚠️  Low graph connectivity: {total_nodes} nodes, {len(top_nodes)} top nodes")
            logger.info("🔄 Applying fallback strategies to expand context...")
            
            # Apply fallback strategies
            fallback_result = await self._apply_fallback_strategies(method_id, result, state)
            if fallback_result:
                result = fallback_result
                logger.info(f"✅ Fallback strategies added {result.get('total_nodes', 0) - total_nodes} additional nodes")
        
        return result
    
    def _build_query_from_method(self, method_data: Dict[str, Any]) -> str:
        """Build query text from method data for vector search"""
        query_components = []
        
        if method_data.get("signature"):
            signature = method_data["signature"]
            query_components.append(signature)
        
        if method_data.get("source_code"):
            code = method_data["source_code"]
            if len(code) > 500:
                code = code[:500]
            query_components.append(code)
        
        return "\n".join(query_components)
    
    async def _vector_search_context(
        self,
        method_id: str,
        state: AgentState
    ) -> Dict[str, Any]:
        """Perform vector search for semantic context"""
        logger.info("="*80)
        logger.info(f"[{self.name}] 🔍 VECTOR SEARCH - Semantic similarity search")
        logger.info("="*80)
        
        # Get method data
        method_data = self.graph.get_method_by_id(method_id)
        
        if not method_data:
            logger.warning(f"  ⚠️  Method data not found for: {method_id}")
            return {"num_results": 0, "results": []}
        
        # Create query from method
        query_components = []
        
        if method_data.get("signature"):
            signature = method_data["signature"]
            query_components.append(signature)
            logger.info(f"  📝 Query signature: {signature[:80]}...")
        
        if method_data.get("source_code"):
            code = method_data["source_code"]
            if len(code) > 500:
                code = code[:500]
            query_components.append(code)
            logger.info(f"  📄 Query code length: {len(code)} chars")
        
        query_text = "\n".join(query_components)
        logger.info(f"  🎯 Total query length: {len(query_text)} chars")
        
        # Perform search
        SIMILARITY_THRESHOLD = 0.7
        TOP_K = 10
        
        logger.info(f"  ⚙️  Parameters:")
        logger.info(f"    • Top-K: {TOP_K}")
        logger.info(f"    • Similarity threshold: {SIMILARITY_THRESHOLD}")
        logger.info(f"  🔎 Searching in Qdrant...")
        
        result = await self.use_tool(
            "vector_search",
            query_text=query_text,
            limit=TOP_K,
            filter_conditions=None
        )
        
        if "error" in result:
            logger.warning(f"  ❌ Vector search failed: {result['error']}")
            return {"num_results": 0, "results": []}
        
        # Detailed logging of vector search results
        results = result.get('results', [])
        logger.info(f"  ✅ Found {len(results)} results from Qdrant")
        
        if results:
            logger.info(f"  📊 Top {min(len(results), 10)} similar methods:")
            for i, item in enumerate(results[:10], 1):
                method_info = item.get('payload', {})
                score = item.get('score', 0)
                method_name = method_info.get('name', 'unknown')
                class_name = method_info.get('class_name', 'unknown')
                
                # Highlight high similarity
                emoji = "🌟" if score >= 0.9 else "⭐" if score >= 0.8 else "✨" if score >= SIMILARITY_THRESHOLD else "📍"
                
                logger.info(f"    {i:2d}. {emoji} {class_name}.{method_name:30s} | similarity: {score:.4f}")
                
                if score < SIMILARITY_THRESHOLD:
                    logger.info(f"        └─ ⚠️  Below threshold ({SIMILARITY_THRESHOLD}), excluded")
        
        # Filter by threshold
        filtered_results = [r for r in results if r.get('score', 0) >= SIMILARITY_THRESHOLD]
        logger.info(f"  🎯 After threshold filter: {len(filtered_results)}/{len(results)} results kept")
        logger.info("-"*80)
        
        return {
            "num_results": len(filtered_results),
            "results": filtered_results,
            "threshold_used": SIMILARITY_THRESHOLD,
            "top_k": TOP_K
        }
    
    async def _get_dependencies(
        self,
        method_id: str,
        state: AgentState
    ) -> Dict[str, Any]:
        """Get direct dependencies of the method"""
        logger.info("="*80)
        logger.info(f"[{self.name}] 🔗 DEPENDENCIES - Direct method dependencies")
        logger.info("="*80)
        logger.info(f"  🎯 Analyzing dependencies for: {method_id}")
        
        dependencies = self.graph.get_method_dependencies(method_id, depth=1)
        
        # Log dependency details
        method_deps = dependencies.get('methods', [])
        field_deps = dependencies.get('fields', [])
        
        logger.info(f"  📊 Dependency Results:")
        logger.info(f"    • Method calls: {len(method_deps)}")
        logger.info(f"    • Field accesses: {len(field_deps)}")
        
        if method_deps:
            logger.info(f"  🔗 Called methods:")
            for i, dep in enumerate(method_deps[:10], 1):
                dep_name = dep.get('name', 'unknown')
                dep_class = dep.get('class_name', 'unknown')
                logger.info(f"    {i:2d}. {dep_class}.{dep_name}")
        
        if field_deps:
            logger.info(f"  📦 Accessed fields:")
            for i, field in enumerate(field_deps[:10], 1):
                field_name = field.get('name', 'unknown')
                logger.info(f"    {i:2d}. {field_name}")
        
        logger.info("-"*80)
        
        return dependencies
    
    def _merge_context(
        self,
        graph_context: Dict[str, Any],
        vector_context: Dict[str, Any],
        dependencies: Dict[str, Any],
        target_method_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Merge and rank context from different sources.
        
        Returns:
            Merged context with ranked methods
        """
        logger.info("="*80)
        logger.info(f"[{self.name}] 🎯 MERGE & RANK - Combining all context sources")
        logger.info("="*80)
        
        # Collect all methods with scores
        method_scores = defaultdict(float)
        method_data = {}
        method_sources = defaultdict(list)  # Track which sources contributed
        
        # Scoring weights
        GRAPH_WEIGHT = 0.7  # 70% for Markov walk results
        VECTOR_WEIGHT = 0.5  # 50% for vector similarity
        DEPENDENCY_WEIGHT = 1.0  # 100% for direct dependencies
        
        logger.info(f"  ⚙️  Scoring Weights:")
        logger.info(f"    • Markov walk: {GRAPH_WEIGHT} (graph structure)")
        logger.info(f"    • Vector search: {VECTOR_WEIGHT} (semantic similarity)")
        logger.info(f"    • Dependencies: {DEPENDENCY_WEIGHT} (direct calls)")
        logger.info("")
        
        # Graph context (higher weight for frequently visited)
        graph_nodes = graph_context.get("top_nodes", [])
        logger.info(f"  📊 Processing Markov walk results: {len(graph_nodes)} nodes")
        graph_method_count = 0
        
        for node in graph_nodes:
            if node.get("type") == "Method":
                method_id = node.get("id")
                visit_prob = node.get("visit_prob", 0)
                score = visit_prob * GRAPH_WEIGHT
                method_scores[method_id] += score
                method_data[method_id] = node.get("data", {})
                method_sources[method_id].append(f"graph(prob={visit_prob:.3f}, score={score:.3f})")
                graph_method_count += 1
        
        logger.info(f"    ✅ Added {graph_method_count} methods from Markov walk")
        
        # Vector context (semantic similarity)
        vector_results = vector_context.get("results", [])
        logger.info(f"  📊 Processing vector search results: {len(vector_results)} results")
        vector_method_count = 0
        
        for result in vector_results:
            # Construct method ID from payload
            payload = result.get("payload", {})
            method_name = payload.get("method_name")
            class_name = payload.get("class_name")
            package = payload.get("package", "")
            
            if method_name and class_name:
                # Use the same ID format as in the database
                if package:
                    method_id = f"method:class:{package}.{class_name}:{method_name}"
                else:
                    method_id = f"method:class:{class_name}:{method_name}"
                
                similarity = result.get("score", 0)
                score = similarity * VECTOR_WEIGHT
                method_scores[method_id] += score
                method_data[method_id] = payload
                method_sources[method_id].append(f"vector(sim={similarity:.4f}, score={score:.3f})")
                vector_method_count += 1
        
        logger.info(f"    ✅ Added {vector_method_count} methods from vector search")
        
        # Dependencies (mandatory - high weight)
        dep_methods = dependencies.get("methods", [])
        logger.info(f"  📊 Processing direct dependencies: {len(dep_methods)} methods")
        dep_count = 0
        
        for method in dep_methods:
            method_id = method.get("id")
            if method_id:
                score = DEPENDENCY_WEIGHT
                method_scores[method_id] += score
                method_data[method_id] = method
                method_sources[method_id].append(f"dependency(score={score:.3f})")
                dep_count += 1
        
        logger.info(f"    ✅ Added {dep_count} direct dependencies")
        logger.info("")
        
        # Calculate total unique methods before ranking
        total_unique = len(method_scores)
        logger.info(f"  🔢 Total unique methods collected: {total_unique}")
        logger.info(f"    • From graph only: {graph_method_count}")
        logger.info(f"    • From vector only: {vector_method_count}")
        logger.info(f"    • From dependencies: {dep_count}")
        logger.info(f"    • Duplicates removed: {graph_method_count + vector_method_count + dep_count - total_unique}")
        logger.info("")
        
        # Sort by score
        TOP_N = 20
        MIN_SCORE_THRESHOLD = 0.1
        
        logger.info(f"  🎯 Ranking and Selection:")
        logger.info(f"    • Top-N to select: {TOP_N}")
        logger.info(f"    • Minimum score threshold: {MIN_SCORE_THRESHOLD}")
        logger.info("")
        
        # Use target method ID for prioritization
        logger.info(f"  🎯 Target method prioritization: {target_method_id or 'None'}")
        
        # Sort by score, but prioritize target method
        def sort_key(item):
            method_id, score = item
            if target_method_id and method_id == target_method_id:
                return (float('inf'), score)  # Target method gets highest priority
            return (score, method_id)  # Then by score, then by ID for consistency
        
        ranked_methods = sorted(
            method_scores.items(),
            key=sort_key,
            reverse=True
        )
        
        # Filter by minimum threshold and take top N
        filtered_ranked = [(mid, score) for mid, score in ranked_methods if score >= MIN_SCORE_THRESHOLD][:TOP_N]
        
        logger.info(f"  📈 Ranking Results:")
        logger.info(f"    • Candidates after threshold filter: {len(filtered_ranked)}/{len(ranked_methods)}")
        logger.info(f"    • Final selection: {len(filtered_ranked)} methods")
        logger.info("")
        
        # Log top ranked methods
        logger.info(f"  🏆 Top {min(len(filtered_ranked), 10)} ranked methods:")
        for i, (method_id, score) in enumerate(filtered_ranked[:10], 1):
            method_name = method_data.get(method_id, {}).get("name", method_id.split(":")[-1])
            sources = ", ".join(method_sources[method_id])
            
            rank_emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📍"
            logger.info(f"    {rank_emoji} {i:2d}. {method_name:40s} | final_score: {score:.4f}")
            logger.info(f"           Sources: {sources}")
        
        logger.info("-"*80)
        
        # Build merged context
        context = {
            "ranked_methods": [
                {
                    "id": method_id,
                    "score": score,
                    "sources": method_sources[method_id],
                    "data": {
                        **method_data.get(method_id, {}),
                        "name": method_data.get(method_id, {}).get("name") or method_id.split(":")[-1]
                    }
                }
                for method_id, score in filtered_ranked
            ],
            "total_methods": len(filtered_ranked),
            "dependencies": dependencies,
            "graph_contribution": graph_method_count,
            "vector_contribution": vector_method_count,
            "scoring_weights": {
                "graph": GRAPH_WEIGHT,
                "vector": VECTOR_WEIGHT,
                "dependency": DEPENDENCY_WEIGHT
            }
        }
        
        logger.info(f"[{self.name}] ✅ Context merge completed:")
        logger.info(f"  • Total methods in final context: {context['total_methods']}")
        logger.info(f"  • From Markov walks: {context['graph_contribution']}")
        logger.info(f"  • From vector search: {context['vector_contribution']}")
        logger.info(f"  • Direct dependencies: {dep_count}")
        logger.info("="*80)
        
        return context
    
    async def _apply_fallback_strategies(
        self,
        method_id: str,
        current_result: Dict[str, Any],
        state: AgentState
    ) -> Optional[Dict[str, Any]]:
        """
        Apply fallback strategies when graph search yields insufficient results.
        
        Args:
            method_id: Target method ID
            current_result: Current graph walk result
            state: Agent state for context
        
        Returns:
            Enhanced result with additional nodes from fallback strategies
        """
        logger.info("🔧 Applying fallback strategies...")
        
        # Get method data for context
        method_data = self.graph.get_method_by_id(method_id)
        if not method_data:
            logger.warning("Cannot apply fallback: method data not found")
            return None
        
        additional_nodes = []
        
        # Strategy 1: Search by class
        class_name = method_data.get('class_name')
        if class_name:
            logger.info(f"  📦 Strategy 1: Searching methods in class '{class_name}'")
            class_methods = self._get_methods_in_class(class_name)
            for method in class_methods[:5]:  # Limit to 5 methods
                if method.get('id') != method_id:  # Exclude target method
                    additional_nodes.append({
                        "id": method.get('id'),
                        "type": "Method",
                        "name": method.get('name'),
                        "visit_count": 1,
                        "visit_prob": 0.1,  # Lower probability for fallback
                        "data": method,
                        "source": "class_fallback"
                    })
            logger.info(f"    ✅ Found {len(additional_nodes)} methods in class")
        
        # Strategy 2: Search by package
        package = method_data.get('package', '')
        if package:
            logger.info(f"  📁 Strategy 2: Searching methods in package '{package}'")
            package_methods = self._get_methods_in_package(package)
            for method in package_methods[:8]:  # Limit to 8 methods
                if method.get('id') != method_id and not any(n['id'] == method.get('id') for n in additional_nodes):
                    additional_nodes.append({
                        "id": method.get('id'),
                        "type": "Method",
                        "name": method.get('name'),
                        "visit_count": 1,
                        "visit_prob": 0.05,  # Even lower probability
                        "data": method,
                        "source": "package_fallback"
                    })
            logger.info(f"    ✅ Found {len([n for n in additional_nodes if n['source'] == 'package_fallback'])} methods in package")
        
        # Strategy 3: Search by name pattern
        method_name = method_data.get('name', '')
        if method_name:
            logger.info(f"  🔍 Strategy 3: Searching methods with similar names to '{method_name}'")
            similar_methods = self._get_methods_by_name_pattern(method_name)
            for method in similar_methods[:5]:  # Limit to 5 methods
                if method.get('id') != method_id and not any(n['id'] == method.get('id') for n in additional_nodes):
                    additional_nodes.append({
                        "id": method.get('id'),
                        "type": "Method",
                        "name": method.get('name'),
                        "visit_count": 1,
                        "visit_prob": 0.08,
                        "data": method,
                        "source": "name_pattern_fallback"
                    })
            logger.info(f"    ✅ Found {len([n for n in additional_nodes if n['source'] == 'name_pattern_fallback'])} methods with similar names")
        
        # Strategy 4: Search by return type
        return_type = method_data.get('return_type', '')
        if return_type and return_type != 'void':
            logger.info(f"  🔄 Strategy 4: Searching methods with return type '{return_type}'")
            return_type_methods = self._get_methods_by_return_type(return_type)
            for method in return_type_methods[:4]:  # Limit to 4 methods
                if method.get('id') != method_id and not any(n['id'] == method.get('id') for n in additional_nodes):
                    additional_nodes.append({
                        "id": method.get('id'),
                        "type": "Method",
                        "name": method.get('name'),
                        "visit_count": 1,
                        "visit_prob": 0.06,
                        "data": method,
                        "source": "return_type_fallback"
                    })
            logger.info(f"    ✅ Found {len([n for n in additional_nodes if n['source'] == 'return_type_fallback'])} methods with same return type")
        
        # Strategy 5: Search by parameter types (for enterprise projects)
        parameters = method_data.get('parameters', [])
        if parameters:
            logger.info(f"  🔧 Strategy 5: Searching methods with similar parameter types")
            param_type_methods = self._get_methods_by_parameter_types(parameters)
            for method in param_type_methods[:6]:  # Limit to 6 methods
                if method.get('id') != method_id and not any(n['id'] == method.get('id') for n in additional_nodes):
                    additional_nodes.append({
                        "id": method.get('id'),
                        "type": "Method",
                        "name": method.get('name'),
                        "visit_count": 1,
                        "visit_prob": 0.07,
                        "data": method,
                        "source": "parameter_type_fallback"
                    })
            logger.info(f"    ✅ Found {len([n for n in additional_nodes if n['source'] == 'parameter_type_fallback'])} methods with similar parameters")
        
        # Strategy 6: Search by annotation patterns (for enterprise projects)
        annotations = method_data.get('annotations', [])
        if annotations:
            logger.info(f"  🏷️ Strategy 6: Searching methods with similar annotations")
            annotation_methods = self._get_methods_by_annotations(annotations)
            for method in annotation_methods[:4]:  # Limit to 4 methods
                if method.get('id') != method_id and not any(n['id'] == method.get('id') for n in additional_nodes):
                    additional_nodes.append({
                        "id": method.get('id'),
                        "type": "Method",
                        "name": method.get('name'),
                        "visit_count": 1,
                        "visit_prob": 0.09,
                        "data": method,
                        "source": "annotation_fallback"
                    })
            logger.info(f"    ✅ Found {len([n for n in additional_nodes if n['source'] == 'annotation_fallback'])} methods with similar annotations")
        
        # Strategy 7: Search by complexity level (for enterprise projects)
        complexity = method_data.get('complexity', 0)
        if complexity > 0:
            logger.info(f"  📊 Strategy 7: Searching methods with similar complexity level")
            complexity_methods = self._get_methods_by_complexity_range(complexity)
            for method in complexity_methods[:5]:  # Limit to 5 methods
                if method.get('id') != method_id and not any(n['id'] == method.get('id') for n in additional_nodes):
                    additional_nodes.append({
                        "id": method.get('id'),
                        "type": "Method",
                        "name": method.get('name'),
                        "visit_count": 1,
                        "visit_prob": 0.06,
                        "data": method,
                        "source": "complexity_fallback"
                    })
            logger.info(f"    ✅ Found {len([n for n in additional_nodes if n['source'] == 'complexity_fallback'])} methods with similar complexity")
        
        if not additional_nodes:
            logger.warning("  ❌ No additional nodes found through fallback strategies")
            return None
        
        # Merge with current result
        current_top_nodes = current_result.get('top_nodes', [])
        enhanced_top_nodes = current_top_nodes + additional_nodes
        
        # Update result
        enhanced_result = current_result.copy()
        enhanced_result['top_nodes'] = enhanced_top_nodes
        enhanced_result['total_nodes'] = len(enhanced_top_nodes)
        enhanced_result['fallback_applied'] = True
        enhanced_result['fallback_nodes'] = len(additional_nodes)
        
        logger.info(f"✅ Fallback strategies completed: {len(additional_nodes)} additional nodes added")
        return enhanced_result
    
    def _get_methods_in_class(self, class_name: str) -> List[Dict[str, Any]]:
        """Get all methods in a specific class"""
        try:
            if self.searcher:
                result = self.searcher.search_methods(
                    class_name=class_name,
                    project_id=getattr(self.graph, 'project_id', None),
                    limit=20
                )
                return result.get('methods', [])
            else:
                # Fallback to graph search
                methods = self.graph.get_all_methods()
                return [m for m in methods if m.get('class_name') == class_name]
        except Exception as e:
            logger.warning(f"Failed to get methods in class {class_name}: {e}")
            return []
    
    def _get_methods_in_package(self, package: str) -> List[Dict[str, Any]]:
        """Get all methods in a specific package"""
        try:
            methods = self.graph.get_all_methods()
            return [m for m in methods if m.get('package', '').startswith(package)]
        except Exception as e:
            logger.warning(f"Failed to get methods in package {package}: {e}")
            return []
    
    def _get_methods_by_name_pattern(self, method_name: str) -> List[Dict[str, Any]]:
        """Get methods with similar names"""
        try:
            if self.searcher:
                result = self.searcher.search_methods(
                    name_pattern=f"*{method_name}*",
                    project_id=getattr(self.graph, 'project_id', None),
                    limit=15
                )
                return result.get('methods', [])
            else:
                # Fallback to graph search
                methods = self.graph.get_all_methods()
                return [m for m in methods if method_name.lower() in m.get('name', '').lower()]
        except Exception as e:
            logger.warning(f"Failed to get methods by name pattern {method_name}: {e}")
            return []
    
    def _get_methods_by_return_type(self, return_type: str) -> List[Dict[str, Any]]:
        """Get methods with specific return type"""
        try:
            methods = self.graph.get_all_methods()
            return [m for m in methods if m.get('return_type') == return_type]
        except Exception as e:
            logger.warning(f"Failed to get methods by return type {return_type}: {e}")
            return []
    
    def _get_methods_by_parameter_types(self, parameters: List[Dict]) -> List[Dict]:
        """Get methods with similar parameter types"""
        if not parameters:
            return []
        
        # Extract parameter types
        param_types = [param.get('type', '') for param in parameters if param.get('type')]
        if not param_types:
            return []
        
        # Search for methods with similar parameter types
        methods = []
        for param_type in param_types:
            query = """
            SELECT * FROM entities 
            WHERE type = 'Method' AND project_id = ? 
            AND (parameters LIKE ? OR parameters LIKE ?)
            LIMIT 10
            """
            # Search for exact type and similar types
            exact_pattern = f'%{param_type}%'
            similar_pattern = f'%{param_type.split(".")[-1]}%'  # Just class name
            
            results = self.graph.conn.execute_and_fetch(query, (self.project_id, exact_pattern, similar_pattern))
            methods.extend(results)
        
        # Remove duplicates
        seen = set()
        unique_methods = []
        for method in methods:
            if method['id'] not in seen:
                seen.add(method['id'])
                unique_methods.append(method)
        
        return unique_methods[:15]  # Limit total results
    
    def _get_methods_by_annotations(self, annotations: List[str]) -> List[Dict]:
        """Get methods with similar annotations"""
        if not annotations:
            return []
        
        methods = []
        for annotation in annotations:
            query = """
            SELECT * FROM entities 
            WHERE type = 'Method' AND project_id = ? 
            AND (annotations LIKE ? OR annotations LIKE ?)
            LIMIT 8
            """
            # Search for exact annotation and similar patterns
            exact_pattern = f'%{annotation}%'
            similar_pattern = f'%{annotation.split(".")[-1]}%'  # Just annotation name
            
            results = self.graph.conn.execute_and_fetch(query, (self.project_id, exact_pattern, similar_pattern))
            methods.extend(results)
        
        # Remove duplicates
        seen = set()
        unique_methods = []
        for method in methods:
            if method['id'] not in seen:
                seen.add(method['id'])
                unique_methods.append(method)
        
        return unique_methods[:12]  # Limit total results
    
    def _get_methods_by_complexity_range(self, target_complexity: int) -> List[Dict]:
        """Get methods with similar complexity levels"""
        # Define complexity ranges
        if target_complexity <= 2:
            complexity_range = (1, 3)
        elif target_complexity <= 5:
            complexity_range = (target_complexity - 1, target_complexity + 2)
        else:
            complexity_range = (target_complexity - 2, target_complexity + 3)
        
        query = """
        SELECT * FROM entities 
        WHERE type = 'Method' AND project_id = ? 
        AND complexity >= ? AND complexity <= ?
        LIMIT 10
        """
        
        results = self.graph.conn.execute_and_fetch(query, (self.project_id, complexity_range[0], complexity_range[1]))
        return results
    
    async def research_method(
        self,
        method_id: str
    ) -> Dict[str, Any]:
        """
        Public method to research a specific method.
        
        Args:
            method_id: Method ID to research
        
        Returns:
            Research results
        """
        state = AgentState()
        state.target_method = method_id
        
        result_state = await self.execute(state)
        
        return {
            "method_context": result_state.method_context,
            "dependencies": result_state.dependencies,
            "similar_methods": result_state.similar_methods,
            "errors": result_state.errors
        }


if __name__ == "__main__":
    # Test the ResearcherAgent
    import asyncio
    import sys
    from pathlib import Path
    
    async def test_researcher():
        from ..graph.graph_builder import CodeGraph
        from ..embedding import CodeEmbedder, VectorStore
        
        # Initialize components
        graph = CodeGraph(use_graph_db=False, project_id="test")
        embedder = CodeEmbedder()
        vector_store = VectorStore(collection_name="test_methods")
        
        # Create agent
        agent = ResearcherAgent(
            graph=graph,
            embedder=embedder,
            vector_store=vector_store
        )
        
        # Create test state
        state = AgentState()
        state.target_method = "testMethod"
        
        print(f"Testing ResearcherAgent with method: {state.target_method}")
        
        # Execute
        result_state = await agent.execute(state)
        
        # Print results
        print("\n" + "="*60)
        print("RESEARCH RESULTS")
        print("="*60)
        print(f"Method Context: {len(result_state.method_context)} items")
        print(f"Dependencies: {len(result_state.dependencies)} items")
        print(f"Similar Methods: {len(result_state.similar_methods)}")
        print(f"Steps completed: {len(result_state.steps_completed)}")
        
        if result_state.errors:
            print("\nErrors:")
            for error in result_state.errors:
                print(f"  ❌ {error}")
        else:
            print("\n✅ Research completed successfully!")
    
    asyncio.run(test_researcher())

