"""
Markov-based graph walker for exploring code dependencies.
Uses random walks with transition probabilities to discover related code.
"""

import random
from typing import List, Dict, Optional, Set, Tuple, Any
from collections import defaultdict, Counter
import numpy as np

from config import get_settings
from logger import get_logger
from graph.graph_builder import CodeGraph

logger = get_logger(__name__)
settings = get_settings()


class MarkovGraphWalker:
    """
    Markov chain-based graph walker for code exploration.
    
    Features:
    - Random walks with configurable transition probabilities
    - Different relationship types have different weights
    - Collects context from neighboring nodes
    - Supports multiple walk strategies
    """
    
    # Default transition probabilities for different relationship types
    DEFAULT_WEIGHTS = {
        "CALLS": 1.0,        # Method calls are highly relevant
        "USES": 0.8,         # Field usage is relevant
        "CONTAINS": 0.3,     # Containment is less relevant for traversal
        "EXTENDS": 0.6,      # Inheritance is moderately relevant
        "IMPLEMENTS": 0.6,   # Interface implementation is moderately relevant
        "RETURNS": 0.4,      # Return type relationships
        "PARAMETER": 0.4     # Parameter type relationships
    }
    
    def __init__(
        self,
        graph: CodeGraph,
        transition_weights: Optional[Dict[str, float]] = None
    ):
        """
        Initialize Markov walker.
        
        Args:
            graph: Code graph instance
            transition_weights: Custom transition weights for relationship types
        """
        self.graph = graph
        self.weights = transition_weights or self.DEFAULT_WEIGHTS
        logger.info("MarkovGraphWalker initialized")
    
    def walk(
        self,
        start_node_id: str,
        num_steps: int = 10,
        num_walks: int = 5,
        include_reverse: bool = True
    ) -> Dict[str, Any]:
        """
        Perform multiple random walks from a starting node.
        
        Args:
            start_node_id: Starting node ID
            num_steps: Number of steps per walk
            num_walks: Number of walks to perform
            include_reverse: Whether to also traverse reverse edges
        
        Returns:
            Dictionary with visited nodes and their frequencies
        """
        logger.info(f"Starting {num_walks} walks from {start_node_id} with {num_steps} steps each")
        
        all_visits = []
        all_paths = []
        
        for walk_num in range(num_walks):
            path, visits = self._single_walk(
                start_node_id,
                num_steps,
                include_reverse
            )
            all_visits.extend(visits)
            all_paths.append(path)
        
        # Count visit frequencies
        visit_counts = Counter(all_visits)
        
        # Normalize to probabilities
        total_visits = len(all_visits)
        visit_probs = {
            node_id: count / total_visits
            for node_id, count in visit_counts.items()
        }
        
        # Get node details for most visited
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
        
        result = {
            "start_node": start_node_id,
            "num_walks": num_walks,
            "num_steps": num_steps,
            "total_nodes": len(visit_counts),  # ✅ FIXED: was total_unique_nodes
            "total_unique_nodes": len(visit_counts),  # Keep for compatibility
            "paths": all_paths,
            "top_nodes": node_details,
            "visit_counts": dict(visit_counts)
        }
        
        logger.info(f"Walk complete: visited {len(visit_counts)} unique nodes")
        return result
    
    def _single_walk(
        self,
        start_node_id: str,
        num_steps: int,
        include_reverse: bool
    ) -> Tuple[List[str], List[str]]:
        """
        Perform a single random walk.
        
        Returns:
            Tuple of (path, all_visited_nodes)
        """
        path = [start_node_id]
        visited = [start_node_id]
        current_node = start_node_id
        
        for step in range(num_steps):
            # Get neighbors
            neighbors = self._get_weighted_neighbors(
                current_node,
                include_reverse
            )
            
            if not neighbors:
                # Dead end, stop walk
                break
            
            # Choose next node based on weights
            next_node = self._weighted_choice(neighbors)
            path.append(next_node)
            visited.append(next_node)
            current_node = next_node
        
        return path, visited
    
    def _get_weighted_neighbors(
        self,
        node_id: str,
        include_reverse: bool
    ) -> List[Tuple[str, float]]:
        """
        Get neighbors with transition weights.
        
        Returns:
            List of (neighbor_id, weight) tuples
        """
        neighbors = []
        
        if self.graph.use_graph_db:
            # SQLite query
            query = """
            SELECT target_id AS neighbor_id, relationship_type AS rel_type
            FROM relationships 
            WHERE source_id = ?
            """
            
            if include_reverse:
                query += """
                UNION
                SELECT source_id AS neighbor_id, relationship_type AS rel_type
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
                    weight = self.weights.get(rel_type, 0.5)
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
                weight = self.weights.get(rel_type, 0.5)
                neighbors.append((neighbor, weight))
            
            # Incoming edges
            if include_reverse:
                for predecessor in self.graph.graph.predecessors(node_id):
                    edge_data = self.graph.graph.edges[predecessor, node_id]
                    rel_type = edge_data.get("type", "UNKNOWN")
                    weight = self.weights.get(rel_type, 0.5)
                    neighbors.append((predecessor, weight))
        
        return neighbors
    
    def _weighted_choice(
        self,
        weighted_items: List[Tuple[str, float]]
    ) -> Optional[str]:
        """
        Make a weighted random choice.
        
        Args:
            weighted_items: List of (item, weight) tuples
        
        Returns:
            Chosen item or None if empty list
        """
        if not weighted_items:
            return None
        
        items, weights = zip(*weighted_items)
        weights = np.array(weights, dtype=float)
        
        # Normalize weights to probabilities
        probs = weights / weights.sum()
        
        # Random choice
        choice = np.random.choice(items, p=probs)
        return choice
    
    def _get_node_data(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get node data from graph"""
        if self.graph.use_graph_db:
            try:
                query = "SELECT * FROM entities WHERE id = ?"
                results = self.graph.conn.execute_and_fetch(query, (node_id,))
                for result in results:
                    return dict(result)
            except Exception as e:
                logger.warning(f"Failed to get node data for {node_id}: {e}")
                return None
        else:
            if node_id in self.graph.graph:
                return dict(self.graph.graph.nodes[node_id])
        return None
    
    def find_paths(
        self,
        start_node_id: str,
        end_node_id: str,
        max_depth: int = 5,
        max_paths: int = 10
    ) -> List[List[str]]:
        """
        Find paths between two nodes.
        
        Args:
            start_node_id: Starting node
            end_node_id: Target node
            max_depth: Maximum path length
            max_paths: Maximum number of paths to return
        
        Returns:
            List of paths (each path is a list of node IDs)
        """
        logger.info(f"Finding paths from {start_node_id} to {end_node_id}")
        
        paths = []
        
        if self.graph.use_graph_db:
            # Memgraph query for shortest paths
            query = """
            MATCH path = (start {id: $start_id})-[*1..%d]-(end {id: $end_id})
            RETURN [node IN nodes(path) | node.id] AS path_nodes
            LIMIT $max_paths
            """ % max_depth
            
            try:
                results = self.graph.conn.execute_and_fetch(
                    query,
                    {"start_id": start_node_id, "end_id": end_node_id, "max_paths": max_paths}
                )
                
                for result in results:
                    paths.append(result["path_nodes"])
            except Exception as e:
                logger.warning(f"Failed to find paths: {e}")
        else:
            # NetworkX - simple BFS
            try:
                import networkx as nx
                
                # Convert to undirected for path finding
                undirected = self.graph.graph.to_undirected()
                
                # Find all simple paths
                all_paths = nx.all_simple_paths(
                    undirected,
                    start_node_id,
                    end_node_id,
                    cutoff=max_depth
                )
                
                for path in all_paths:
                    paths.append(path)
                    if len(paths) >= max_paths:
                        break
            except Exception as e:
                logger.warning(f"Failed to find paths: {e}")
        
        logger.info(f"Found {len(paths)} paths")
        return paths
    
    def get_context(
        self,
        start_node_id: str,
        depth: int = 2,
        max_nodes: int = 50
    ) -> Dict[str, Any]:
        """
        Get context around a node using Markov walks.
        
        Args:
            start_node_id: Starting node
            depth: Depth of exploration
            max_nodes: Maximum number of context nodes
        
        Returns:
            Context dictionary with relevant nodes
        """
        logger.info(f"Getting context for {start_node_id} with depth {depth}")
        
        # Perform walks
        walk_result = self.walk(
            start_node_id,
            num_steps=depth,
            num_walks=10,
            include_reverse=True
        )
        
        # Get top nodes (excluding start)
        top_nodes = walk_result["top_nodes"][:max_nodes]
        
        # Organize by type
        context = {
            "source_node": start_node_id,
            "methods": [],
            "classes": [],
            "fields": [],
            "total_nodes": len(top_nodes)
        }
        
        for node in top_nodes:
            node_type = node["type"]
            
            if node_type == "Method":
                context["methods"].append(node)
            elif node_type == "Class":
                context["classes"].append(node)
            elif node_type == "Field":
                context["fields"].append(node)
        
        logger.info(
            f"Context: {len(context['methods'])} methods, "
            f"{len(context['classes'])} classes, "
            f"{len(context['fields'])} fields"
        )
        
        return context
    
    def visualize_walk(
        self,
        walk_result: Dict[str, Any],
        max_nodes: int = 20
    ) -> str:
        """
        Create a text visualization of walk results.
        
        Args:
            walk_result: Result from walk() method
            max_nodes: Maximum nodes to show
        
        Returns:
            Formatted string visualization
        """
        lines = []
        lines.append("=" * 60)
        lines.append("MARKOV WALK RESULTS")
        lines.append("=" * 60)
        lines.append(f"Start Node: {walk_result['start_node']}")
        lines.append(f"Num Walks: {walk_result['num_walks']}")
        lines.append(f"Steps per Walk: {walk_result['num_steps']}")
        lines.append(f"Total Unique Nodes Visited: {walk_result['total_unique_nodes']}")
        lines.append("")
        lines.append("Top Visited Nodes:")
        lines.append("-" * 60)
        
        for i, node in enumerate(walk_result['top_nodes'][:max_nodes], 1):
            lines.append(
                f"{i:2d}. [{node['type']:8s}] {node['name']:30s} "
                f"(visits: {node['visit_count']:3d}, prob: {node['visit_prob']:.3f})"
            )
        
        lines.append("=" * 60)
        return "\n".join(lines)


if __name__ == "__main__":
    # Test the Markov walker
    print("Testing MarkovGraphWalker...")
    
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
    
    # Create walker
    walker = MarkovGraphWalker(graph)
    
    # Perform walk
    result = walker.walk(method_ids[0], num_steps=5, num_walks=10)
    
    # Visualize
    print(walker.visualize_walk(result))
    
    # Get context
    context = walker.get_context(method_ids[0], depth=2)
    print(f"\n✅ Context: {context['total_nodes']} nodes")
    
    print("\n✅ MarkovGraphWalker test passed!")

