"""
Tests for Enhanced Markov Walker functionality.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from graph.graph_builder import CodeGraph
from graph.enhanced_markov_walker import EnhancedMarkovWalker
from parser import MethodSignature, MethodInfo, ClassInfo


class TestEnhancedMarkovWalker:
    """Test cases for EnhancedMarkovWalker"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create mock graph
        self.mock_graph = Mock(spec=CodeGraph)
        self.mock_graph.use_graph_db = False
        self.mock_graph.project_id = "test_project"
        
        # Mock graph methods
        self.mock_graph.get_all_methods.return_value = []
        
        # Create proper NetworkX mock
        self.mock_nx_graph = Mock()
        self.mock_nx_graph.neighbors.return_value = []
        self.mock_nx_graph.predecessors.return_value = []
        self.mock_nx_graph.edges = {}
        
        # Make the graph mock behave like a dict for 'in' operator
        self.mock_nx_graph.__contains__ = Mock(return_value=False)
        
        self.mock_graph.graph = self.mock_nx_graph
        
        # Create walker
        self.walker = EnhancedMarkovWalker(self.mock_graph)
    
    def test_initialization(self):
        """Test EnhancedMarkovWalker initialization"""
        assert self.walker.base_weights == self.walker.DEFAULT_WEIGHTS
        assert self.walker.current_weights == self.walker.DEFAULT_WEIGHTS
        assert self.walker.learning_rate == 0.1
        assert self.walker.project_profile is None
        assert self.walker.analysis_cache == {}
    
    def test_project_analysis_empty_project(self):
        """Test project analysis with empty project"""
        self.mock_graph.get_all_methods.return_value = []
        
        profile = self.walker._analyze_project()
        
        assert profile["type"] == "unknown"
        assert profile["characteristics"] == {}
    
    def test_project_analysis_gui_application(self):
        """Test project analysis for GUI application"""
        methods = [
            {
                'source_code': 'public void actionPerformed(ActionEvent e) { JFrame frame = new JFrame(); }',
                'annotations': [],
                'modifiers': ['public'],
                'complexity': 2,
                'parameters': [{'name': 'e', 'type': 'ActionEvent'}]
            },
            {
                'source_code': 'private void setupUI() { JButton button = new JButton(); }',
                'annotations': [],
                'modifiers': ['private'],
                'complexity': 1,
                'parameters': []
            }
        ]
        self.mock_graph.get_all_methods.return_value = methods
        
        profile = self.walker._analyze_project()
        
        assert profile["type"] == "gui_application"
        assert profile["characteristics"]["swing_usage"] > 0
        assert profile["characteristics"]["total_methods"] == 2
    
    def test_project_analysis_framework_library(self):
        """Test project analysis for framework/library"""
        methods = [
            {
                'source_code': 'public class MyService {}',
                'annotations': ['@Service', '@Component'],
                'modifiers': ['public'],
                'complexity': 1,
                'parameters': []
            },
            {
                'source_code': 'public void process() {}',
                'annotations': ['@Transactional'],
                'modifiers': ['public'],
                'complexity': 2,
                'parameters': []
            }
        ]
        self.mock_graph.get_all_methods.return_value = methods
        
        profile = self.walker._analyze_project()
        
        assert profile["type"] == "framework_library"
        assert profile["characteristics"]["annotation_usage"] > 0.5
    
    def test_project_analysis_utility_library(self):
        """Test project analysis for utility library"""
        methods = [
            {
                'source_code': 'public int calculate(int a, int b) { return a + b; }',
                'annotations': [],
                'modifiers': ['public', 'static'],
                'complexity': 1,
                'parameters': [{'name': 'a', 'type': 'int'}, {'name': 'b', 'type': 'int'}]
            },
            {
                'source_code': 'public double computeAverage(List<Double> values) { return values.stream().mapToDouble(Double::doubleValue).average().orElse(0.0); }',
                'annotations': [],
                'modifiers': ['public', 'static'],
                'complexity': 1,
                'parameters': [{'name': 'values', 'type': 'List<Double>'}]
            }
        ]
        self.mock_graph.get_all_methods.return_value = methods
        
        profile = self.walker._analyze_project()
        
        assert profile["type"] == "utility_library"
        assert profile["characteristics"]["math_operations"] > 0.5
        assert profile["characteristics"]["static_methods"] > 0.5
    
    def test_weight_adaptation_gui_application(self):
        """Test weight adaptation for GUI application"""
        # Set up project profile
        self.walker.project_profile = {
            "type": "gui_application",
            "characteristics": {
                "swing_usage": 0.3,
                "average_complexity": 2.5
            }
        }
        
        # Store original weights
        original_weights = self.walker.current_weights.copy()
        
        # Adapt weights
        self.walker._adapt_weights_from_profile()
        
        # Check that weights were adapted
        assert self.walker.current_weights["USES"] > original_weights["USES"]
        assert self.walker.current_weights["CONTAINS"] > original_weights["CONTAINS"]
    
    def test_weight_adaptation_framework_library(self):
        """Test weight adaptation for framework library"""
        # Set up project profile
        self.walker.project_profile = {
            "type": "framework_library",
            "characteristics": {
                "annotation_usage": 0.4,
                "average_complexity": 3.0
            }
        }
        
        # Store original weights
        original_weights = self.walker.current_weights.copy()
        
        # Adapt weights
        self.walker._adapt_weights_from_profile()
        
        # Check that weights were adapted
        assert self.walker.current_weights["EXTENDS"] > original_weights["EXTENDS"]
        assert self.walker.current_weights["IMPLEMENTS"] > original_weights["IMPLEMENTS"]
        assert self.walker.current_weights["RETURNS"] > original_weights["RETURNS"]
    
    def test_adaptive_walk_no_neighbors(self):
        """Test adaptive walk with no neighbors"""
        start_node_id = "test_node"
        self.mock_graph.graph.neighbors.return_value = []
        self.mock_graph.graph.predecessors.return_value = []
        
        result = self.walker._adaptive_walk(start_node_id, num_steps=5, num_walks=2, include_reverse=True)
        
        assert result["start_node"] == start_node_id
        assert result["total_nodes"] == 1  # Only start node
        assert len(result["paths"]) == 2
        assert len(result["top_nodes"]) == 0
    
    def test_hybrid_walk_with_guidance(self):
        """Test hybrid walk with vector guidance"""
        start_node_id = "test_node"
        
        # Mock neighbors
        self.mock_nx_graph.neighbors.return_value = ["neighbor1", "neighbor2"]
        self.mock_nx_graph.predecessors.return_value = []
        
        # Mock edge data
        self.mock_nx_graph.edges = {
            ("test_node", "neighbor1"): {"type": "CALLS"},
            ("test_node", "neighbor2"): {"type": "USES"}
        }
        
        # Mock node data
        self.walker._get_node_data = Mock(return_value={"type": "Method", "name": "test_method"})
        
        # Mock find_node_by_name
        self.walker._find_node_by_name = Mock(return_value="neighbor1")
        
        # Vector guidance
        vector_guidance = {
            "results": [
                {
                    "payload": {"method_name": "test_method", "class_name": "TestClass"},
                    "score": 0.8
                }
            ]
        }
        
        result = self.walker._hybrid_walk(
            start_node_id, 
            num_steps=3, 
            num_walks=2, 
            include_reverse=True,
            vector_guidance=vector_guidance
        )
        
        assert result["start_node"] == start_node_id
        assert result["vector_guidance_used"] is True
        assert result["guided_nodes"] == 1
    
    def test_enhance_results(self):
        """Test result enhancement"""
        # Set up project profile
        self.walker.project_profile = {
            "type": "test_type",
            "characteristics": {"total_methods": 10}
        }
        
        # Basic result
        basic_result = {
            "start_node": "test_node",
            "total_nodes": 5,
            "visit_counts": {"node1": 3, "node2": 2}
        }
        
        enhanced_result = self.walker._enhance_results(basic_result, "test_node")
        
        assert "project_analysis" in enhanced_result
        assert "weight_adaptation" in enhanced_result
        assert "performance_metrics" in enhanced_result
        assert enhanced_result["project_analysis"]["type"] == "test_type"
    
    def test_find_node_by_name(self):
        """Test finding node by method and class name"""
        methods = [
            {"id": "method1", "name": "testMethod", "class_name": "TestClass"},
            {"id": "method2", "name": "anotherMethod", "class_name": "AnotherClass"}
        ]
        self.mock_graph.get_all_methods.return_value = methods
        
        # Test finding existing method
        node_id = self.walker._find_node_by_name("testMethod", "TestClass")
        assert node_id == "method1"
        
        # Test finding non-existing method
        node_id = self.walker._find_node_by_name("nonExistent", "TestClass")
        assert node_id is None
    
    def test_weighted_choice(self):
        """Test weighted random choice"""
        weighted_items = [("item1", 0.7), ("item2", 0.3)]
        
        # Test multiple times to ensure randomness
        choices = []
        for _ in range(100):
            choice = self.walker._weighted_choice(weighted_items)
            choices.append(choice)
        
        # Should have both items (with some randomness)
        assert "item1" in choices
        assert "item2" in choices
        
        # item1 should be chosen more often (due to higher weight)
        item1_count = choices.count("item1")
        item2_count = choices.count("item2")
        assert item1_count > item2_count
    
    def test_weighted_choice_empty(self):
        """Test weighted choice with empty list"""
        choice = self.walker._weighted_choice([])
        assert choice is None


if __name__ == "__main__":
    pytest.main([__file__])
