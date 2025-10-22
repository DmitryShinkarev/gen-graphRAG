"""
Metrics collector for agent performance monitoring.
Collects data from agents, Langfuse, and databases.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collect metrics from various sources"""
    
    def __init__(self):
        self.metrics_cache: Dict[str, Any] = {}
        
    def collect_agent_metrics(self) -> Dict[str, Any]:
        """Collect metrics from agent operations"""
        # This would normally collect from Redis/database
        # For now, return mock data structure
        return {
            "agents": {
                "IndexerAgent": {
                    "total_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "avg_duration": 0.0,
                    "total_tokens": 0,
                    "total_cost": 0.0
                },
                "ResearcherAgent": {
                    "total_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "avg_duration": 0.0,
                    "total_tokens": 0,
                    "total_cost": 0.0
                },
                "GeneratorAgent": {
                    "total_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "avg_duration": 0.0,
                    "total_tokens": 0,
                    "total_cost": 0.0
                },
                "CriticAgent": {
                    "total_calls": 0,
                    "successful_calls": 0,
                    "failed_calls": 0,
                    "avg_duration": 0.0,
                    "total_tokens": 0,
                    "total_cost": 0.0
                }
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def collect_langfuse_metrics(self) -> Dict[str, Any]:
        """
        Collect metrics from Langfuse.
        In production, this would use Langfuse API.
        """
        return {
            "total_traces": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "avg_latency": 0.0,
            "traces_by_agent": {},
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def collect_database_metrics(self) -> Dict[str, Any]:
        """Collect database statistics"""
        return {
            "memgraph": {
                "nodes": 0,
                "relationships": 0,
                "indexed_files": 0
            },
            "qdrant": {
                "vectors": 0,
                "collections": 0
            },
            "redis": {
                "keys": 0,
                "memory_used": 0
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def generate_mock_time_series(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Generate mock time series data for demonstration"""
        data = []
        now = datetime.utcnow()
        
        for i in range(hours):
            timestamp = now - timedelta(hours=hours-i)
            data.append({
                "timestamp": timestamp.isoformat(),
                "IndexerAgent": {
                    "calls": i * 2 + (i % 3),
                    "tokens": i * 500 + (i % 100),
                    "cost": round((i * 500 + (i % 100)) * 0.000002, 6),
                    "latency": 1.2 + (i % 5) * 0.1
                },
                "ResearcherAgent": {
                    "calls": i + (i % 2),
                    "tokens": i * 300 + (i % 50),
                    "cost": round((i * 300 + (i % 50)) * 0.000002, 6),
                    "latency": 0.8 + (i % 3) * 0.1
                },
                "GeneratorAgent": {
                    "calls": i * 3 + (i % 4),
                    "tokens": i * 800 + (i % 200),
                    "cost": round((i * 800 + (i % 200)) * 0.000002, 6),
                    "latency": 2.5 + (i % 7) * 0.2
                },
                "CriticAgent": {
                    "calls": i + (i % 2),
                    "tokens": i * 400 + (i % 80),
                    "cost": round((i * 400 + (i % 80)) * 0.000002, 6),
                    "latency": 1.5 + (i % 4) * 0.15
                }
            })
        
        return data
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics across all agents"""
        time_series = self.generate_mock_time_series(24)
        
        total_calls = 0
        total_tokens = 0
        total_cost = 0.0
        
        agents_summary = {}
        
        for agent_name in ["IndexerAgent", "ResearcherAgent", "GeneratorAgent", "CriticAgent"]:
            agent_calls = sum(entry[agent_name]["calls"] for entry in time_series)
            agent_tokens = sum(entry[agent_name]["tokens"] for entry in time_series)
            agent_cost = sum(entry[agent_name]["cost"] for entry in time_series)
            agent_avg_latency = sum(entry[agent_name]["latency"] for entry in time_series) / len(time_series)
            
            agents_summary[agent_name] = {
                "calls": agent_calls,
                "tokens": agent_tokens,
                "cost": round(agent_cost, 4),
                "avg_latency": round(agent_avg_latency, 2)
            }
            
            total_calls += agent_calls
            total_tokens += agent_tokens
            total_cost += agent_cost
        
        return {
            "total_calls": total_calls,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 4),
            "agents": agents_summary,
            "period": "Last 24 hours",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def save_metrics(self, filepath: str):
        """Save collected metrics to file"""
        metrics = {
            "agent_metrics": self.collect_agent_metrics(),
            "langfuse_metrics": self.collect_langfuse_metrics(),
            "database_metrics": self.collect_database_metrics(),
            "summary_stats": self.get_summary_stats(),
            "time_series": self.generate_mock_time_series(24)
        }
        
        with open(filepath, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        logger.info(f"Metrics saved to {filepath}")
        return metrics

