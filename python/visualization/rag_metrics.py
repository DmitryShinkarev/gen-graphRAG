"""
RAG-specific metrics collector.
Collects data from Qdrant, Memgraph, and RAG operations.
"""

import numpy as np
from typing import Dict, List, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RAGMetricsCollector:
    """Collect RAG-specific metrics"""
    
    def __init__(self):
        self.cache = {}
    
    def generate_mock_search_results(self, query: str = "calculateTotal", limit: int = 20) -> List[Dict[str, Any]]:
        """Generate mock vector search results"""
        method_names = [
            "calculateTotal", "getTotalPrice", "computeSum", "addItems",
            "processOrder", "validateInput", "formatOutput", "parseData",
            "initializeConnection", "closeSession", "handleRequest", "sendResponse",
            "authenticateUser", "authorizeAccess", "logActivity", "cacheResult",
            "transformData", "validateSchema", "executeQuery", "fetchResults"
        ]
        
        results = []
        for i, method in enumerate(method_names[:limit]):
            # Simulate realistic similarity distribution
            if i == 0:
                score = 0.95 + np.random.random() * 0.04  # Best match
            elif i < 5:
                score = 0.75 + np.random.random() * 0.15  # Good matches
            elif i < 10:
                score = 0.60 + np.random.random() * 0.15  # Medium matches
            else:
                score = 0.40 + np.random.random() * 0.20  # Lower matches
            
            results.append({
                'method_name': method,
                'score': score,
                'tokens': np.random.randint(50, 500),
                'file_path': f'src/main/java/com/example/{method}.java',
                'class_name': f'{method}Service'
            })
        
        return sorted(results, key=lambda x: x['score'], reverse=True)
    
    def generate_funnel_data(self) -> Dict[str, int]:
        """Generate RAG retrieval funnel data"""
        return {
            "Total Methods Indexed": 1250,
            "Vector Search Candidates": 500,
            "Score Threshold Filter": 150,
            "Markov Walk Expansion": 80,
            "Context Ranking": 40,
            "Final Context Selected": 15
        }
    
    def generate_timeline_data(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Generate retrieval performance timeline"""
        data = []
        now = datetime.utcnow()
        
        for i in range(hours):
            timestamp = (now - timedelta(hours=hours-i)).isoformat()
            
            # Simulate realistic patterns
            hour_of_day = (now - timedelta(hours=hours-i)).hour
            is_peak = 9 <= hour_of_day <= 17  # Peak hours
            
            base_latency = 0.15 if is_peak else 0.10
            latency = base_latency + np.random.random() * 0.05
            
            results_count = np.random.randint(8, 25) if is_peak else np.random.randint(5, 15)
            avg_score = 0.70 + np.random.random() * 0.20
            
            data.append({
                'timestamp': timestamp,
                'latency': latency,
                'results_count': results_count,
                'avg_score': avg_score,
                'cache_hit_rate': 0.3 + np.random.random() * 0.4
            })
        
        return data
    
    def generate_markov_walk(self, start_method: str = "calculateTotal") -> List[Dict[str, Any]]:
        """Generate Markov walk through code graph"""
        walk = []
        
        # Starting node
        walk.append({
            'name': start_method,
            'depth': 0,
            'score': 1.0,
            'type': 'start'
        })
        
        # Level 1 - Direct calls
        level1_methods = ['getTotalPrice', 'addItems', 'validateInput']
        for i, method in enumerate(level1_methods):
            walk.append({
                'name': method,
                'depth': 1,
                'score': 0.9 - i * 0.1,
                'type': 'calls'
            })
        
        # Level 2 - Indirect calls
        level2_methods = ['processOrder', 'formatOutput', 'authenticateUser']
        for i, method in enumerate(level2_methods):
            walk.append({
                'name': method,
                'depth': 2,
                'score': 0.7 - i * 0.1,
                'type': 'uses'
            })
        
        # Level 3 - Further relations
        level3_methods = ['logActivity', 'cacheResult']
        for i, method in enumerate(level3_methods):
            walk.append({
                'name': method,
                'depth': 3,
                'score': 0.5 - i * 0.1,
                'type': 'implements'
            })
        
        return walk
    
    def generate_embedding_clusters(self, n_points: int = 100) -> List[Dict[str, Any]]:
        """Generate mock embedding clusters (2D projection)"""
        data = []
        
        types = ['class', 'method', 'field', 'interface']
        type_centers = {
            'class': (0, 0),
            'method': (3, 2),
            'field': (-2, 3),
            'interface': (2, -2)
        }
        
        for _ in range(n_points):
            item_type = np.random.choice(types)
            center = type_centers[item_type]
            
            # Add noise around center
            x = center[0] + np.random.normal(0, 0.8)
            y = center[1] + np.random.normal(0, 0.8)
            
            # Generate label
            labels = {
                'class': ['UserService', 'OrderService', 'PaymentService', 'AuthService'],
                'method': ['calculate', 'process', 'validate', 'format'],
                'field': ['userId', 'orderId', 'amount', 'status'],
                'interface': ['IService', 'IRepository', 'IValidator', 'IProcessor']
            }
            label = np.random.choice(labels[item_type])
            
            data.append({
                'x': x,
                'y': y,
                'label': label,
                'type': item_type
            })
        
        return data
    
    def generate_context_usage_heatmap(self, n_queries: int = 10, n_contexts: int = 15) -> List[List[float]]:
        """Generate context usage heatmap data"""
        # Simulate that top-ranked contexts are used more
        heatmap = []
        for i in range(n_contexts):
            row = []
            for j in range(n_queries):
                # Top contexts (low i) are used more
                base_usage = 1.0 - (i / n_contexts)
                usage = base_usage + np.random.random() * 0.3
                usage = min(1.0, usage)
                row.append(usage)
            heatmap.append(row)
        
        return heatmap
    
    def get_rag_summary(self) -> Dict[str, Any]:
        """Get summary of RAG system performance"""
        search_results = self.generate_mock_search_results()
        timeline = self.generate_timeline_data(24)
        
        avg_latency = np.mean([t['latency'] for t in timeline])
        avg_results = np.mean([t['results_count'] for t in timeline])
        avg_score = np.mean([t['avg_score'] for t in timeline])
        avg_cache_hit = np.mean([t['cache_hit_rate'] for t in timeline])
        
        top_10_avg_score = np.mean([r['score'] for r in search_results[:10]])
        
        return {
            'total_vectors': 1250,
            'avg_retrieval_latency': round(avg_latency, 3),
            'avg_results_per_query': round(avg_results, 1),
            'avg_similarity_score': round(avg_score, 3),
            'top_10_avg_score': round(top_10_avg_score, 3),
            'cache_hit_rate': round(avg_cache_hit, 3),
            'total_searches_24h': len(timeline),
            'timestamp': datetime.utcnow().isoformat()
        }

