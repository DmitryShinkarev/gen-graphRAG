"""
Plotly chart generators for agent metrics visualization.
Creates interactive charts for monitoring and analysis.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PlotlyCharts:
    """Generate Plotly charts for agent metrics"""
    
    def __init__(self, theme: str = "plotly_dark"):
        self.theme = theme
        self.colors = {
            "IndexerAgent": "#00D9FF",      # Cyan
            "ResearcherAgent": "#FF6B9D",   # Pink
            "GeneratorAgent": "#00FF9F",    # Green
            "CriticAgent": "#FFD700"        # Gold
        }
    
    def create_calls_timeline(self, time_series: List[Dict[str, Any]]) -> go.Figure:
        """Create timeline chart of agent calls"""
        fig = go.Figure()
        
        timestamps = [entry["timestamp"] for entry in time_series]
        
        for agent_name in ["IndexerAgent", "ResearcherAgent", "GeneratorAgent", "CriticAgent"]:
            calls = [entry[agent_name]["calls"] for entry in time_series]
            
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=calls,
                name=agent_name,
                mode='lines+markers',
                line=dict(color=self.colors[agent_name], width=2),
                marker=dict(size=6)
            ))
        
        fig.update_layout(
            title="Agent LLM Calls Over Time",
            xaxis_title="Time",
            yaxis_title="Number of Calls",
            template=self.theme,
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return fig
    
    def create_tokens_chart(self, time_series: List[Dict[str, Any]]) -> go.Figure:
        """Create stacked area chart for token usage"""
        fig = go.Figure()
        
        timestamps = [entry["timestamp"] for entry in time_series]
        
        for agent_name in ["IndexerAgent", "ResearcherAgent", "GeneratorAgent", "CriticAgent"]:
            tokens = [entry[agent_name]["tokens"] for entry in time_series]
            
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=tokens,
                name=agent_name,
                mode='lines',
                stackgroup='one',
                fillcolor=self.colors[agent_name],
                line=dict(color=self.colors[agent_name], width=0.5)
            ))
        
        fig.update_layout(
            title="Token Usage by Agent (Stacked)",
            xaxis_title="Time",
            yaxis_title="Total Tokens",
            template=self.theme,
            hovermode='x unified',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return fig
    
    def create_cost_breakdown(self, summary_stats: Dict[str, Any]) -> go.Figure:
        """Create pie chart of cost breakdown by agent"""
        agents = summary_stats["agents"]
        
        labels = list(agents.keys())
        values = [agents[agent]["cost"] for agent in labels]
        colors = [self.colors[agent] for agent in labels]
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker=dict(colors=colors),
            textposition='inside',
            textinfo='label+percent'
        )])
        
        fig.update_layout(
            title=f"Cost Distribution (Total: ${summary_stats['total_cost']})",
            template=self.theme,
            showlegend=True
        )
        
        return fig
    
    def create_latency_comparison(self, time_series: List[Dict[str, Any]]) -> go.Figure:
        """Create box plot comparing agent latencies"""
        data = []
        
        for agent_name in ["IndexerAgent", "ResearcherAgent", "GeneratorAgent", "CriticAgent"]:
            latencies = [entry[agent_name]["latency"] for entry in time_series]
            
            data.append(go.Box(
                y=latencies,
                name=agent_name,
                marker=dict(color=self.colors[agent_name]),
                boxmean='sd'
            ))
        
        fig = go.Figure(data=data)
        
        fig.update_layout(
            title="Agent Response Latency Distribution",
            yaxis_title="Latency (seconds)",
            template=self.theme,
            showlegend=False
        )
        
        return fig
    
    def create_performance_dashboard(
        self, 
        time_series: List[Dict[str, Any]], 
        summary_stats: Dict[str, Any]
    ) -> go.Figure:
        """Create comprehensive dashboard with multiple charts"""
        
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'LLM Calls Over Time',
                'Token Usage Distribution',
                'Average Latency by Agent',
                'Cost Per Agent'
            ),
            specs=[
                [{"type": "scatter"}, {"type": "bar"}],
                [{"type": "bar"}, {"type": "pie"}]
            ],
            vertical_spacing=0.12,
            horizontal_spacing=0.1
        )
        
        timestamps = [entry["timestamp"] for entry in time_series]
        
        # 1. Calls timeline (top left)
        for agent_name in ["IndexerAgent", "ResearcherAgent", "GeneratorAgent", "CriticAgent"]:
            calls = [entry[agent_name]["calls"] for entry in time_series]
            fig.add_trace(
                go.Scatter(
                    x=timestamps, 
                    y=calls, 
                    name=agent_name,
                    line=dict(color=self.colors[agent_name]),
                    showlegend=True
                ),
                row=1, col=1
            )
        
        # 2. Token distribution (top right)
        agents = list(summary_stats["agents"].keys())
        tokens = [summary_stats["agents"][agent]["tokens"] for agent in agents]
        colors_list = [self.colors[agent] for agent in agents]
        
        fig.add_trace(
            go.Bar(
                x=agents,
                y=tokens,
                marker=dict(color=colors_list),
                showlegend=False
            ),
            row=1, col=2
        )
        
        # 3. Average latency (bottom left)
        latencies = [summary_stats["agents"][agent]["avg_latency"] for agent in agents]
        
        fig.add_trace(
            go.Bar(
                x=agents,
                y=latencies,
                marker=dict(color=colors_list),
                showlegend=False
            ),
            row=2, col=1
        )
        
        # 4. Cost pie chart (bottom right)
        costs = [summary_stats["agents"][agent]["cost"] for agent in agents]
        
        fig.add_trace(
            go.Pie(
                labels=agents,
                values=costs,
                marker=dict(colors=colors_list),
                showlegend=False
            ),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            title_text=f"Agent Performance Dashboard - {summary_stats['period']}",
            template=self.theme,
            height=800,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.15,
                xanchor="center",
                x=0.5
            )
        )
        
        # Update axes
        fig.update_xaxes(title_text="Time", row=1, col=1)
        fig.update_yaxes(title_text="Calls", row=1, col=1)
        
        fig.update_xaxes(title_text="Agent", row=1, col=2)
        fig.update_yaxes(title_text="Tokens", row=1, col=2)
        
        fig.update_xaxes(title_text="Agent", row=2, col=1)
        fig.update_yaxes(title_text="Latency (s)", row=2, col=1)
        
        return fig
    
    def create_heatmap(self, time_series: List[Dict[str, Any]], metric: str = "calls") -> go.Figure:
        """Create heatmap of metric over time"""
        agents = ["IndexerAgent", "ResearcherAgent", "GeneratorAgent", "CriticAgent"]
        timestamps = [entry["timestamp"][:13] for entry in time_series]  # Hour precision
        
        # Build matrix
        z_data = []
        for agent in agents:
            row = [entry[agent][metric] for entry in time_series]
            z_data.append(row)
        
        fig = go.Figure(data=go.Heatmap(
            z=z_data,
            x=timestamps,
            y=agents,
            colorscale='Viridis',
            hoverongaps=False
        ))
        
        fig.update_layout(
            title=f"Agent Activity Heatmap ({metric.title()})",
            xaxis_title="Time",
            yaxis_title="Agent",
            template=self.theme
        )
        
        return fig
    
    def save_chart(self, fig: go.Figure, filepath: str, format: str = "html"):
        """Save chart to file"""
        if format == "html":
            fig.write_html(filepath)
        elif format == "png":
            fig.write_image(filepath)
        elif format == "json":
            fig.write_json(filepath)
        
        logger.info(f"Chart saved to {filepath}")

