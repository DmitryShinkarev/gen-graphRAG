"""
Enhanced Markov Walker with adaptive weights and hybrid search.
Improves upon the basic MarkovGraphWalker with:
1. Adaptive weights based on project characteristics
2. Hybrid search combining Markov walks with vector guidance
"""

import random
from typing import List, Dict, Optional, Set, Tuple, Any
from collections import defaultdict, Counter
import numpy as np

from config import get_settings
from logger import get_logger
from graph.graph_builder import CodeGraph
from graph.markov_walker import MarkovGraphWalker

logger = get_logger(__name__)
settings = get_settings()


class EnhancedMarkovWalker(MarkovGraphWalker):
    """
    Enhanced Markov chain-based graph walker with adaptive weights and hybrid search.
    
    Features:
    - Adaptive transition weights based on project analysis
    - Hybrid search combining Markov walks with vector guidance
    - Learning from project characteristics
    - Backward compatibility with original MarkovGraphWalker
    """
    
    def __init__(
        self,
        graph: CodeGraph,
        transition_weights: Optional[Dict[str, float]] = None,
        learning_rate: float = 0.1
    ):
        """
        Initialize Enhanced Markov walker.
        
        Args:
            graph: Code graph instance
            transition_weights: Starting weights for relationships
            learning_rate: Rate of weight adaptation
        """
        super().__init__(graph, transition_weights)
        
        self.base_weights = self.DEFAULT_WEIGHTS.copy()
        self.current_weights = self.weights.copy()
        self.learning_rate = learning_rate
        
        # Project analysis cache
        self.project_profile = None
        self.analysis_cache = {}
        
        logger.info("EnhancedMarkovWalker initialized with adaptive weights")
    
    def walk(
        self,
        start_node_id: str,
        num_steps: int = 10,
        num_walks: int = 5,
        include_reverse: bool = True,
        vector_guidance: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Enhanced walk with adaptive weights and optional vector guidance.
        
        Args:
            start_node_id: Starting node ID
            num_steps: Number of steps per walk
            num_walks: Number of walks to perform
            include_reverse: Whether to traverse reverse edges
            vector_guidance: Optional vector search results for guidance
        
        Returns:
            Enhanced walk results with adaptive analysis
        """
        logger.info(f"Enhanced walk: {num_walks} walks from {start_node_id}")
        
        # 1. Diagnose graph connectivity
        connectivity_status = self._diagnose_graph_connectivity(start_node_id)
        logger.info(f"Graph connectivity: {connectivity_status}")
        
        # 2. Analyze project and adapt weights
        self._analyze_and_adapt_weights()
        
        # 3. Perform multi-level search
        if vector_guidance:
            result = self._multi_level_hybrid_walk(start_node_id, num_steps, num_walks, include_reverse, vector_guidance)
        else:
            result = self._multi_level_adaptive_walk(start_node_id, num_steps, num_walks, include_reverse)
        
        # 3. Enhance results with analysis
        result = self._enhance_results(result, start_node_id)
        
        return result
    
    def _analyze_and_adapt_weights(self):
        """Analyze project characteristics and adapt weights accordingly"""
        
        # Use cached analysis if available
        project_id = getattr(self.graph, 'project_id', 'default')
        if project_id in self.analysis_cache:
            self.project_profile = self.analysis_cache[project_id]
            logger.info(f"Using cached project analysis for {project_id}")
        else:
            # Perform fresh analysis
            self.project_profile = self._analyze_project()
            self.analysis_cache[project_id] = self.project_profile
            logger.info(f"Analyzed project: {self.project_profile['type']}")
        
        # Adapt weights based on project profile
        self._adapt_weights_from_profile()
    
    def _analyze_project(self) -> Dict[str, Any]:
        """Analyze project characteristics"""
        
        # Get all methods for analysis
        methods = self.graph.get_all_methods()
        if not methods:
            return {"type": "unknown", "characteristics": {}}
        
        # Collect statistics
        stats = {
            'total_methods': len(methods),
            'swing_usage': 0,
            'annotation_usage': 0,
            'database_usage': 0,
            'math_operations': 0,
            'complexity_distribution': [],
            'average_parameters': 0,
            'exception_handling': 0,
            'static_methods': 0
        }
        
        total_params = 0
        
        for method in methods:
            source_code = method.get('source_code', '')
            annotations = method.get('annotations', [])
            modifiers = method.get('modifiers', [])
            complexity = method.get('complexity', 0)
            parameters = method.get('parameters', [])
            
            # Count patterns
            if any(gui in source_code for gui in ['JFrame', 'JButton', 'Swing', 'ActionListener']):
                stats['swing_usage'] += 1
            if annotations:
                stats['annotation_usage'] += 1
            if any(db in source_code for db in ['ResultSet', 'Connection', 'SQL', 'Statement']):
                stats['database_usage'] += 1
            if any(math in source_code for math in ['Math.', 'calculate', 'compute', '+', '-', '*', '/']):
                stats['math_operations'] += 1
            if 'try' in source_code or 'catch' in source_code:
                stats['exception_handling'] += 1
            if 'static' in modifiers:
                stats['static_methods'] += 1
            
            stats['complexity_distribution'].append(complexity)
            total_params += len(parameters)
        
        # Normalize statistics
        total = stats['total_methods']
        for key in ['swing_usage', 'annotation_usage', 'database_usage', 'math_operations', 'exception_handling', 'static_methods']:
            stats[key] = stats[key] / total if total > 0 else 0
        
        stats['average_parameters'] = total_params / total if total > 0 else 0
        stats['average_complexity'] = np.mean(stats['complexity_distribution']) if stats['complexity_distribution'] else 0
        
        # Determine project type
        project_type = self._classify_project_type(stats)
        
        return {
            'type': project_type,
            'characteristics': stats
        }
    
    def _classify_project_type(self, stats: Dict[str, Any]) -> str:
        """Classify project type based on statistics"""
        
        # Enterprise/Large projects: check for specific characteristics
        total_methods = stats.get('total_methods', 0)
        total_classes = stats.get('total_classes', 0)
        
        # Check if this is a large enterprise project
        if (total_methods > 30 or total_classes > 10 or 
            stats.get('package_count', 0) > 5 or
            stats.get('average_complexity', 0) > 3.0):
            return "enterprise_large"
        
        # GUI Application
        if stats['swing_usage'] > 0.2:
            return "gui_application"
        
        # Framework/Library
        if stats['annotation_usage'] > 0.3:
            return "framework_library"
        
        # Data Application
        if stats['database_usage'] > 0.15:
            return "data_application"
        
        # Utility/Mathematical
        if stats['math_operations'] > 0.4 or stats['average_complexity'] < 2.0:
            return "utility_library"
        
        # Business Application
        if stats['exception_handling'] > 0.3:
            return "business_application"
        
        return "general_application"
    
    def _adapt_weights_from_profile(self):
        """Adapt weights based on project profile"""
        
        profile = self.project_profile
        if not profile:
            return
        
        # Start with enhanced base weights
        self.current_weights = self.base_weights.copy()
        
        # Add new relationship types with enhanced weights
        enhanced_weights = {
            "CALLS": 1.3,        # Increased importance of method calls
            "USES": 1.0,         # Field usage
            "CONTAINS": 0.4,     # Slightly increased containment
            "EXTENDS": 0.7,      # Increased inheritance importance
            "IMPLEMENTS": 0.7,   # Increased interface implementation
            "RETURNS": 0.5,      # Return type relationships
            "PARAMETER": 0.5,    # Parameter type relationships
            "THROWS": 0.6,       # Exception relationships (new)
            "ANNOTATED": 0.8,    # Annotation relationships (new)
            "OVERRIDES": 0.9,    # Override relationships (new)
            "DEPENDS_ON": 0.6,   # Dependency relationships (new)
        }
        
        # Update weights with enhanced values
        for rel_type, weight in enhanced_weights.items():
            if rel_type in self.current_weights:
                self.current_weights[rel_type] = weight
            else:
                self.current_weights[rel_type] = weight
        
        # Adapt based on project type
        project_type = profile['type']
        characteristics = profile['characteristics']
        
        logger.info(f"Adapting weights for project type: {project_type}")
        
        if project_type == "gui_application":
            # GUI apps: more focus on event handling and UI components
            self.current_weights["USES"] *= 1.3  # UI components are important
            self.current_weights["CONTAINS"] *= 1.4  # Component hierarchy matters
            self.current_weights["ANNOTATED"] *= 1.2  # Event annotations
            
        elif project_type == "framework_library":
            # Frameworks: inheritance and interfaces are crucial
            self.current_weights["EXTENDS"] *= 1.6
            self.current_weights["IMPLEMENTS"] *= 1.5
            self.current_weights["RETURNS"] *= 1.3
            self.current_weights["OVERRIDES"] *= 1.4
            self.current_weights["ANNOTATED"] *= 1.3
            
        elif project_type == "data_application":
            # Data apps: method calls and parameter passing are important
            self.current_weights["CALLS"] *= 1.4
            self.current_weights["PARAMETER"] *= 1.3
            self.current_weights["THROWS"] *= 1.2  # Exception handling important
            self.current_weights["DEPENDS_ON"] *= 1.2
            
        elif project_type == "utility_library":
            # Utilities: simple calls and field usage
            self.current_weights["CALLS"] *= 0.9  # Less complex call chains
            self.current_weights["USES"] *= 1.2
            self.current_weights["RETURNS"] *= 1.1  # Return types matter for utilities
            
        elif project_type == "business_application":
            # Business logic: balanced approach with emphasis on calls
            self.current_weights["CALLS"] *= 1.2
            self.current_weights["USES"] *= 1.2
            self.current_weights["THROWS"] *= 1.1  # Business logic has exceptions
            self.current_weights["DEPENDS_ON"] *= 1.1
            
        elif project_type == "enterprise_large":
            # Enterprise/large projects: optimize for sparse connectivity
            # Reduce CONTAINS weight (too dominant) and boost other relationships
            self.current_weights["CONTAINS"] *= 0.3  # Reduce dominant CONTAINS
            self.current_weights["CALLS"] *= 2.0     # Boost method calls significantly
            self.current_weights["USES"] *= 1.8      # Boost field usage
            self.current_weights["EXTENDS"] *= 1.5   # Boost inheritance
            self.current_weights["IMPLEMENTS"] *= 1.5 # Boost interfaces
            self.current_weights["RETURNS"] *= 1.4   # Boost return types
            self.current_weights["PARAMETER"] *= 1.4 # Boost parameters
            self.current_weights["THROWS"] *= 1.3    # Boost exceptions
            self.current_weights["ANNOTATED"] *= 1.3 # Boost annotations
            self.current_weights["OVERRIDES"] *= 1.4 # Boost overrides
            self.current_weights["DEPENDS_ON"] *= 1.3 # Boost dependencies
            
        # Adapt based on complexity characteristics
        avg_complexity = characteristics.get('average_complexity', 0)
        if avg_complexity > 4.0:
            # High complexity: emphasize method calls and dependencies
            self.current_weights["CALLS"] *= 1.3
            self.current_weights["DEPENDS_ON"] *= 1.2
            self.current_weights["THROWS"] *= 1.1
        elif avg_complexity < 2.0:
            # Low complexity: more balanced weights
            self.current_weights["CALLS"] *= 0.9
            self.current_weights["USES"] *= 1.1
        
        # Adapt based on project size
        total_methods = characteristics.get('total_methods', 0)
        if total_methods > 100:
            # Large projects: emphasize structure and organization
            self.current_weights["CONTAINS"] *= 1.2
            self.current_weights["EXTENDS"] *= 1.1
            self.current_weights["IMPLEMENTS"] *= 1.1
        elif total_methods < 20:
            # Small projects: focus on direct relationships
            self.current_weights["CALLS"] *= 1.2
            self.current_weights["USES"] *= 1.1
        
        # Log adapted weights
        logger.info("Adapted weights:")
        for rel_type, weight in self.current_weights.items():
            base_weight = self.base_weights.get(rel_type, weight)  # Use current weight as base if not in base_weights
            change = (weight - base_weight) / base_weight * 100 if base_weight > 0 else 0
            logger.info(f"  {rel_type}: {base_weight:.2f} → {weight:.2f} ({change:+.1f}%)")
    
    def _multi_level_adaptive_walk(self, start_node_id: str, num_steps: int, num_walks: int, include_reverse: bool) -> Dict[str, Any]:
        """
        Perform multi-level adaptive walk with different strategies.
        
        Args:
            start_node_id: Starting node ID
            num_steps: Base number of steps
            num_walks: Base number of walks
            include_reverse: Whether to include reverse edges
        
        Returns:
            Combined results from multiple search strategies
        """
        logger.info("🔄 Performing multi-level adaptive walk...")
        
        # Define search strategies - optimized for enterprise projects
        project_type = self.project_profile.get('type', 'general_application') if self.project_profile else 'general_application'
        
        if project_type == "enterprise_large":
            # Special strategies for enterprise projects with sparse connectivity
            strategies = [
                {"name": "ultra_wide", "steps": 3, "walks": num_walks * 3, "reverse": True, "boost_calls": True},
                {"name": "deep_exploration", "steps": num_steps * 3, "walks": num_walks // 3, "reverse": True, "boost_uses": True},
                {"name": "balanced_enterprise", "steps": num_steps, "walks": num_walks, "reverse": True, "boost_all": True},
                {"name": "forward_enterprise", "steps": num_steps, "walks": num_walks, "reverse": False, "boost_calls": True},
                {"name": "reverse_enterprise", "steps": num_steps, "walks": num_walks, "reverse": True, "boost_uses": True},
            ]
        else:
            # Standard strategies for other project types
            strategies = [
                {"name": "shallow_wide", "steps": num_steps // 2, "walks": num_walks * 2, "reverse": True},
                {"name": "deep_narrow", "steps": num_steps * 2, "walks": num_walks // 2, "reverse": True},
                {"name": "balanced", "steps": num_steps, "walks": num_walks, "reverse": True},
                {"name": "forward_only", "steps": num_steps, "walks": num_walks, "reverse": False},
            ]
        
        all_results = []
        
        for strategy in strategies:
            logger.info(f"  📊 Strategy: {strategy['name']} (steps: {strategy['steps']}, walks: {strategy['walks']})")
            
            # Apply strategy-specific weight boosts
            original_weights = self.current_weights.copy()
            if strategy.get('boost_calls'):
                self.current_weights["CALLS"] *= 1.5
            if strategy.get('boost_uses'):
                self.current_weights["USES"] *= 1.5
            if strategy.get('boost_all'):
                for rel_type in ["CALLS", "USES", "EXTENDS", "IMPLEMENTS", "RETURNS", "PARAMETER"]:
                    if rel_type in self.current_weights:
                        self.current_weights[rel_type] *= 1.3
            
            strategy_result = self._adaptive_walk(
                start_node_id,
                strategy['steps'],
                strategy['walks'],
                strategy['reverse']
            )
            
            # Restore original weights
            self.current_weights = original_weights
            
            # Add strategy metadata
            strategy_result['strategy'] = strategy['name']
            all_results.append(strategy_result)
        
        # Combine results from all strategies
        combined_result = self._combine_strategy_results(all_results, start_node_id)
        
        logger.info(f"✅ Multi-level search completed: {combined_result.get('total_nodes', 0)} unique nodes found")
        return combined_result
    
    def _multi_level_hybrid_walk(
        self, 
        start_node_id: str, 
        num_steps: int, 
        num_walks: int, 
        include_reverse: bool,
        vector_guidance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform multi-level hybrid walk combining Markov chains with vector guidance.
        
        Args:
            start_node_id: Starting node ID
            num_steps: Base number of steps
            num_walks: Base number of walks
            include_reverse: Whether to include reverse edges
            vector_guidance: Vector search results for guidance
        
        Returns:
            Combined results from multiple hybrid search strategies
        """
        logger.info("🔄 Performing multi-level hybrid walk...")
        
        # Define hybrid search strategies
        strategies = [
            {"name": "vector_guided", "steps": num_steps, "walks": num_walks, "reverse": True, "guidance_weight": 0.7},
            {"name": "markov_heavy", "steps": num_steps * 2, "walks": num_walks, "reverse": True, "guidance_weight": 0.3},
            {"name": "balanced_hybrid", "steps": num_steps, "walks": num_walks * 2, "reverse": True, "guidance_weight": 0.5},
        ]
        
        all_results = []
        
        for strategy in strategies:
            logger.info(f"  📊 Strategy: {strategy['name']} (guidance_weight: {strategy['guidance_weight']})")
            
            # Modify vector guidance weight for this strategy
            modified_guidance = self._modify_guidance_weight(vector_guidance, strategy['guidance_weight'])
            
            strategy_result = self._hybrid_walk(
                start_node_id,
                strategy['steps'],
                strategy['walks'],
                strategy['reverse'],
                modified_guidance
            )
            
            # Add strategy metadata
            strategy_result['strategy'] = strategy['name']
            strategy_result['guidance_weight'] = strategy['guidance_weight']
            all_results.append(strategy_result)
        
        # Combine results from all strategies
        combined_result = self._combine_strategy_results(all_results, start_node_id)
        
        logger.info(f"✅ Multi-level hybrid search completed: {combined_result.get('total_nodes', 0)} unique nodes found")
        return combined_result
    
    def _modify_guidance_weight(self, vector_guidance: Dict[str, Any], weight: float) -> Dict[str, Any]:
        """Modify vector guidance weights for different strategies"""
        if not vector_guidance or 'results' not in vector_guidance:
            return vector_guidance
        
        modified_guidance = vector_guidance.copy()
        modified_results = []
        
        for result in vector_guidance['results']:
            modified_result = result.copy()
            # Scale the score by the guidance weight
            original_score = result.get('score', 0.5)
            modified_result['score'] = original_score * weight
            modified_results.append(modified_result)
        
        modified_guidance['results'] = modified_results
        return modified_guidance
    
    def _combine_strategy_results(self, all_results: List[Dict[str, Any]], start_node_id: str) -> Dict[str, Any]:
        """Combine results from multiple search strategies"""
        
        # Collect all unique nodes with their scores
        node_scores = {}
        node_data = {}
        strategy_contributions = {}
        
        for result in all_results:
            strategy_name = result.get('strategy', 'unknown')
            top_nodes = result.get('top_nodes', [])
            
            for node in top_nodes:
                node_id = node.get('id')
                if node_id == start_node_id:
                    continue
                
                visit_prob = node.get('visit_prob', 0)
                guidance_score = node.get('guidance_score', 0)
                
                # Calculate combined score
                combined_score = visit_prob + (guidance_score * 0.3)  # Weight guidance less
                
                if node_id not in node_scores:
                    node_scores[node_id] = 0
                    node_data[node_id] = node
                    strategy_contributions[node_id] = []
                
                # Add to cumulative score
                node_scores[node_id] += combined_score
                strategy_contributions[node_id].append({
                    'strategy': strategy_name,
                    'score': combined_score,
                    'visit_prob': visit_prob,
                    'guidance_score': guidance_score
                })
        
        # Sort by combined score
        sorted_nodes = sorted(node_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Build final result
        top_nodes = []
        for node_id, total_score in sorted_nodes[:30]:  # Top 30 nodes
            node = node_data[node_id].copy()
            node['combined_score'] = total_score
            node['strategy_contributions'] = strategy_contributions[node_id]
            top_nodes.append(node)
        
        return {
            "start_node": start_node_id,
            "total_nodes": len(top_nodes),
            "top_nodes": top_nodes,
            "multi_level_search": True,
            "strategies_used": [r.get('strategy', 'unknown') for r in all_results],
            "node_scores": dict(sorted_nodes[:30])
        }
    
    def _adaptive_walk(self, start_node_id: str, num_steps: int, num_walks: int, include_reverse: bool) -> Dict[str, Any]:
        """Perform adaptive Markov walk with current weights"""
        
        all_visits = []
        all_paths = []
        
        for walk_num in range(num_walks):
            path, visits = self._single_adaptive_walk(start_node_id, num_steps, include_reverse)
            all_visits.extend(visits)
            all_paths.append(path)
        
        # Process results (same as original)
        visit_counts = Counter(all_visits)
        total_visits = len(all_visits)
        visit_probs = {
            node_id: count / total_visits
            for node_id, count in visit_counts.items()
        }
        
        top_nodes = visit_counts.most_common(20)
        node_details = []
        
        for node_id, count in top_nodes:
            if node_id == start_node_id:
                continue
            
            node_data = self._get_node_data(node_id)
            if node_data:
                node_details.append({
                    "id": node_id,
                    "type": node_data.get("type"),
                    "name": node_data.get("name"),
                    "visit_count": count,
                    "visit_prob": visit_probs[node_id],
                    "data": node_data
                })
        
        return {
            "start_node": start_node_id,
            "num_walks": num_walks,
            "num_steps": num_steps,
            "total_nodes": len(visit_counts),
            "paths": all_paths,
            "top_nodes": node_details,
            "visit_counts": dict(visit_counts),
            "adaptive_weights": self.current_weights.copy()
        }
    
    def _hybrid_walk(
        self, 
        start_node_id: str, 
        num_steps: int, 
        num_walks: int, 
        include_reverse: bool,
        vector_guidance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform hybrid walk combining Markov chains with vector guidance"""
        
        logger.info("Performing hybrid walk with vector guidance")
        
        # Extract guidance from vector results
        guidance_nodes = set()
        guidance_scores = {}
        
        vector_results = vector_guidance.get('results', [])
        for result in vector_results:
            payload = result.get('payload', {})
            method_name = payload.get('method_name', '')
            class_name = payload.get('class_name', '')
            
            if method_name and class_name:
                # Try to find corresponding node in graph
                guidance_id = self._find_node_by_name(method_name, class_name)
                if guidance_id:
                    guidance_nodes.add(guidance_id)
                    guidance_scores[guidance_id] = result.get('score', 0.5)
        
        logger.info(f"Vector guidance: {len(guidance_nodes)} nodes identified")
        
        # Perform walks with guidance
        all_visits = []
        all_paths = []
        
        for walk_num in range(num_walks):
            # Alternate between guided and unguided walks
            if walk_num % 2 == 0:
                path, visits = self._guided_walk(start_node_id, num_steps, include_reverse, guidance_nodes, guidance_scores)
            else:
                path, visits = self._single_adaptive_walk(start_node_id, num_steps, include_reverse)
            
            all_visits.extend(visits)
            all_paths.append(path)
        
        # Process results
        visit_counts = Counter(all_visits)
        total_visits = len(all_visits)
        visit_probs = {
            node_id: count / total_visits
            for node_id, count in visit_counts.items()
        }
        
        top_nodes = visit_counts.most_common(20)
        node_details = []
        
        for node_id, count in top_nodes:
            if node_id == start_node_id:
                continue
            
            node_data = self._get_node_data(node_id)
            if node_data:
                guidance_bonus = guidance_scores.get(node_id, 0)
                node_details.append({
                    "id": node_id,
                    "type": node_data.get("type"),
                    "name": node_data.get("name"),
                    "visit_count": count,
                    "visit_prob": visit_probs[node_id],
                    "guidance_score": guidance_bonus,
                    "data": node_data
                })
        
        return {
            "start_node": start_node_id,
            "num_walks": num_walks,
            "num_steps": num_steps,
            "total_nodes": len(visit_counts),
            "paths": all_paths,
            "top_nodes": node_details,
            "visit_counts": dict(visit_counts),
            "adaptive_weights": self.current_weights.copy(),
            "vector_guidance_used": True,
            "guided_nodes": len(guidance_nodes)
        }
    
    def _single_adaptive_walk(self, start_node_id: str, num_steps: int, include_reverse: bool) -> Tuple[List[str], List[str]]:
        """Single adaptive walk using current weights"""
        
        path = [start_node_id]
        visited = [start_node_id]
        current_node = start_node_id
        
        for step in range(num_steps):
            neighbors = self._get_weighted_neighbors(current_node, include_reverse)
            
            if not neighbors:
                break
            
            next_node = self._weighted_choice(neighbors)
            path.append(next_node)
            visited.append(next_node)
            current_node = next_node
        
        return path, visited
    
    def _guided_walk(
        self, 
        start_node_id: str, 
        num_steps: int, 
        include_reverse: bool,
        guidance_nodes: Set[str],
        guidance_scores: Dict[str, float]
    ) -> Tuple[List[str], List[str]]:
        """Guided walk that prefers nodes from vector guidance"""
        
        path = [start_node_id]
        visited = [start_node_id]
        current_node = start_node_id
        
        for step in range(num_steps):
            neighbors = self._get_weighted_neighbors(current_node, include_reverse)
            
            if not neighbors:
                break
            
            # Enhance weights for guidance nodes
            enhanced_neighbors = []
            for neighbor_id, weight in neighbors:
                enhanced_weight = weight
                if neighbor_id in guidance_nodes:
                    guidance_bonus = guidance_scores.get(neighbor_id, 0.5)
                    enhanced_weight *= (1.0 + guidance_bonus * 0.5)  # 50% bonus max
                
                enhanced_neighbors.append((neighbor_id, enhanced_weight))
            
            next_node = self._weighted_choice(enhanced_neighbors)
            path.append(next_node)
            visited.append(next_node)
            current_node = next_node
        
        return path, visited
    
    def _get_weighted_neighbors(self, node_id: str, include_reverse: bool) -> List[Tuple[str, float]]:
        """Get neighbors with current adaptive weights"""
        
        neighbors = []
        
        if self.graph.use_graph_db:
            # SQLite query
            query = """
            SELECT target_id AS neighbor_id, rel_type AS rel_type
            FROM relationships 
            WHERE source_id = ?
            """
            
            if include_reverse:
                query += """
                UNION
                SELECT source_id AS neighbor_id, rel_type AS rel_type
                FROM relationships 
                WHERE target_id = ?
                """
            
            try:
                if include_reverse:
                    results = self.graph.conn.execute_and_fetch(query, (node_id, node_id))
                else:
                    results = self.graph.conn.execute_and_fetch(query, (node_id,))
                
                for result in results:
                    neighbor_id = result["neighbor_id"]
                    rel_type = result["rel_type"]
                    weight = self.current_weights.get(rel_type, 0.5)
                    neighbors.append((neighbor_id, weight))
            except Exception as e:
                logger.warning(f"Failed to get neighbors for {node_id}: {e}")
        else:
            # NetworkX
            if node_id not in self.graph.graph:
                return neighbors
            
            # Outgoing edges
            for neighbor in self.graph.graph.neighbors(node_id):
                edge_data = self.graph.graph.edges[node_id, neighbor]
                rel_type = edge_data.get("type", "UNKNOWN")
                weight = self.current_weights.get(rel_type, 0.5)
                neighbors.append((neighbor, weight))
            
            # Incoming edges
            if include_reverse:
                for predecessor in self.graph.graph.predecessors(node_id):
                    edge_data = self.graph.graph.edges[predecessor, node_id]
                    rel_type = edge_data.get("type", "UNKNOWN")
                    weight = self.current_weights.get(rel_type, 0.5)
                    neighbors.append((predecessor, weight))
        
        return neighbors
    
    def _find_node_by_name(self, method_name: str, class_name: str) -> Optional[str]:
        """Find graph node by method and class name"""
        
        methods = self.graph.get_all_methods()
        for method in methods:
            if (method.get('name') == method_name and 
                method.get('class_name') == class_name):
                return method.get('id')
        return None
    
    def _enhance_results(self, result: Dict[str, Any], start_node_id: str) -> Dict[str, Any]:
        """Enhance results with additional analysis"""
        
        # Add project analysis
        result["project_analysis"] = self.project_profile
        
        # Add weight adaptation info
        result["weight_adaptation"] = {
            "base_weights": self.base_weights,
            "adapted_weights": self.current_weights,
            "adaptation_reason": f"Project type: {self.project_profile['type']}"
        }
        
        # Add performance metrics
        result["performance_metrics"] = {
            "total_unique_nodes": result.get("total_nodes", 0),
            "average_visits_per_node": len(result.get("visit_counts", {})) / max(1, result.get("total_nodes", 1)),
            "most_visited_node": max(result.get("visit_counts", {}).items(), key=lambda x: x[1]) if result.get("visit_counts") else None
        }
        
        return result
    
    def get_context(self, start_node_id: str, depth: int = 2, max_nodes: int = 50) -> Dict[str, Any]:
        """Get context using enhanced walker (backward compatible)"""
        
        walk_result = self.walk(
            start_node_id,
            num_steps=depth,
            num_walks=10,
            include_reverse=True
        )
        
        top_nodes = walk_result["top_nodes"][:max_nodes]
        
        context = {
            "source_node": start_node_id,
            "methods": [],
            "classes": [],
            "fields": [],
            "total_nodes": len(top_nodes),
            "enhanced_analysis": walk_result.get("project_analysis", {}),
            "weight_adaptation": walk_result.get("weight_adaptation", {})
        }
        
        for node in top_nodes:
            node_type = node["type"]
            
            if node_type == "Method":
                context["methods"].append(node)
            elif node_type == "Class":
                context["classes"].append(node)
            elif node_type == "Field":
                context["fields"].append(node)
        
        return context
    
    def _diagnose_graph_connectivity(self, start_node_id: str) -> str:
        """
        Diagnose graph connectivity and return status.
        
        Args:
            start_node_id: Starting node for connectivity analysis
        
        Returns:
            Connectivity status string
        """
        try:
            # Get basic graph statistics
            total_methods = len(self.graph.get_all_methods())
            total_classes = len(self.graph.get_all_classes())
            
            # Count connections for the starting node
            method_connections = self._count_node_connections(start_node_id)
            
            # Count total edges in graph
            total_edges = self._count_total_edges()
            
            # Calculate connectivity metrics
            avg_connectivity = total_edges / max(1, total_methods) if total_methods > 0 else 0
            node_connectivity_ratio = method_connections / max(1, total_methods) if total_methods > 0 else 0
            
            # Determine connectivity status
            if method_connections == 0:
                status = "ISOLATED"
                logger.warning(f"Node {start_node_id} is isolated (0 connections)")
            elif method_connections < 2:
                status = "LOW_CONNECTIVITY"
                logger.warning(f"Node {start_node_id} has low connectivity ({method_connections} connections)")
            elif method_connections < 5:
                status = "MODERATE_CONNECTIVITY"
                logger.info(f"Node {start_node_id} has moderate connectivity ({method_connections} connections)")
            else:
                status = "HIGH_CONNECTIVITY"
                logger.info(f"Node {start_node_id} has high connectivity ({method_connections} connections)")
            
            # Log detailed statistics
            logger.info(f"Graph Statistics:")
            logger.info(f"  • Total methods: {total_methods}")
            logger.info(f"  • Total classes: {total_classes}")
            logger.info(f"  • Total edges: {total_edges}")
            logger.info(f"  • Avg connectivity: {avg_connectivity:.2f}")
            logger.info(f"  • Node connectivity ratio: {node_connectivity_ratio:.2f}")
            
            return status
            
        except Exception as e:
            logger.warning(f"Failed to diagnose connectivity: {e}")
            return "UNKNOWN"
    
    def _count_node_connections(self, node_id: str) -> int:
        """Count total connections for a specific node"""
        try:
            if self.graph.use_graph_db:
                # SQLite query for relationships
                query = """
                SELECT COUNT(*) as connection_count 
                FROM relationships 
                WHERE source_id = ? OR target_id = ?
                """
                results = self.graph.conn.execute_and_fetch(query, (node_id, node_id))
                if results:
                    return results[0]["connection_count"]
                return 0
            else:
                # NetworkX
                if node_id not in self.graph.graph:
                    return 0
                
                # Count both incoming and outgoing edges
                in_degree = self.graph.graph.in_degree(node_id)
                out_degree = self.graph.graph.out_degree(node_id)
                return in_degree + out_degree
                
        except Exception as e:
            logger.warning(f"Failed to count connections for {node_id}: {e}")
            return 0
    
    def _count_total_edges(self) -> int:
        """Count total edges in the graph"""
        try:
            if self.graph.use_graph_db:
                # SQLite query
                query = "SELECT COUNT(*) as edge_count FROM relationships"
                results = self.graph.conn.execute_and_fetch(query)
                if results:
                    return results[0]["edge_count"]
                return 0
            else:
                # NetworkX
                return self.graph.graph.number_of_edges()
                
        except Exception as e:
            logger.warning(f"Failed to count total edges: {e}")
            return 0


if __name__ == "__main__":
    # Test the Enhanced Markov walker
    print("Testing EnhancedMarkovWalker...")
    
    from .graph_builder import CodeGraph
    from ..parser import MethodSignature, MethodInfo, ClassInfo
    
    # Create test graph
    graph = CodeGraph(use_graph_db=False, project_id="test")
    
    # Add some test data
    class_info = ClassInfo(
        name="TestClass",
        package="com.test",
        modifiers=["public"]
    )
    
    class_id = graph.add_class(class_info)
    
    # Add methods
    method_ids = []
    for i in range(5):
        sig = MethodSignature(
            name=f"method{i}",
            return_type="void",
            parameters=[],
            modifiers=["public"],
            annotations=[]
        )
        
        method_info = MethodInfo(
            signature=sig,
            source_code=f"public void method{i}() {{}}",
            start_line=10 + i*5,
            end_line=12 + i*5,
            complexity=1,
            loc=3,
            class_name="TestClass",
            package="com.test"
        )
        
        method_id = graph.add_method(method_info, class_id)
        method_ids.append(method_id)
    
    # Add some calls
    graph.add_relationship(method_ids[0], method_ids[1], "CALLS")
    graph.add_relationship(method_ids[1], method_ids[2], "CALLS")
    graph.add_relationship(method_ids[2], method_ids[3], "CALLS")
    graph.add_relationship(method_ids[0], method_ids[3], "CALLS")
    
    # Create enhanced walker
    walker = EnhancedMarkovWalker(graph)
    
    # Perform walk
    result = walker.walk(method_ids[0], num_steps=5, num_walks=10)
    
    # Visualize
    print(walker.visualize_walk(result))
    
    # Get context
    context = walker.get_context(method_ids[0], depth=2)
    print(f"\n✅ Context: {context['total_nodes']} nodes")
    
    print("\n✅ EnhancedMarkovWalker test passed!")
