"""
RAG-specific Plotly visualizations.
Charts for vector search, context retrieval, and graph navigation.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Any, Optional
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RAGCharts:
    """Generate Plotly charts for RAG system metrics"""
    
    def __init__(self, theme: str = "plotly_dark"):
        self.theme = theme
        self.colors = {
            "high_relevance": "#00FF9F",    # Green
            "medium_relevance": "#FFD700",  # Gold
            "low_relevance": "#FF6B9D",     # Pink
            "vector": "#00D9FF",            # Cyan
            "graph": "#A855F7",             # Purple
            "context": "#F97316"            # Orange
        }
    
    def create_vector_similarity_chart(self, search_results: List[Dict[str, Any]]) -> go.Figure:
        """
        Visualize vector similarity scores from Qdrant search.
        
        Args:
            search_results: List of dicts with 'method_name', 'score', 'tokens'
        """
        fig = go.Figure()
        
        # Sort by score
        sorted_results = sorted(search_results, key=lambda x: x['score'], reverse=True)
        
        methods = [r['method_name'] for r in sorted_results]
        scores = [r['score'] for r in sorted_results]
        tokens = [r.get('tokens', 0) for r in sorted_results]
        
        # Color based on relevance threshold
        colors = []
        for score in scores:
            if score >= 0.8:
                colors.append(self.colors['high_relevance'])
            elif score >= 0.6:
                colors.append(self.colors['medium_relevance'])
            else:
                colors.append(self.colors['low_relevance'])
        
        fig.add_trace(go.Bar(
            x=methods,
            y=scores,
            marker=dict(
                color=colors,
                line=dict(color='white', width=1)
            ),
            text=[f"{s:.3f}" for s in scores],
            textposition='outside',
            hovertemplate='<b>%{x}</b><br>' +
                         'Score: %{y:.4f}<br>' +
                         'Tokens: %{customdata}<br>' +
                         '<extra></extra>',
            customdata=tokens
        ))
        
        # Add threshold lines
        fig.add_hline(y=0.8, line_dash="dash", line_color="green", 
                     annotation_text="High Relevance (0.8)")
        fig.add_hline(y=0.6, line_dash="dash", line_color="orange", 
                     annotation_text="Medium Relevance (0.6)")
        
        fig.update_layout(
            title="Vector Search Results - Similarity Scores",
            xaxis_title="Method Name",
            yaxis_title="Cosine Similarity Score",
            template=self.theme,
            yaxis=dict(range=[0, 1]),
            showlegend=False,
            height=500
        )
        
        return fig
    
    def create_retrieval_funnel(self, funnel_data: Dict[str, int]) -> go.Figure:
        """
        Visualize RAG retrieval funnel.
        
        Args:
            funnel_data: Dict with stages and counts
        """
        stages = list(funnel_data.keys())
        counts = list(funnel_data.values())
        
        fig = go.Figure(go.Funnel(
            y=stages,
            x=counts,
            textposition="inside",
            textinfo="value+percent initial",
            marker=dict(
                color=["#667eea", "#764ba2", "#f093fb", "#4facfe", "#00f2fe"],
            )
        ))
        
        fig.update_layout(
            title="RAG Retrieval Funnel",
            template=self.theme,
            height=400
        )
        
        return fig
    
    def create_embedding_clusters(self, embeddings_data: List[Dict[str, Any]]) -> go.Figure:
        """
        Visualize embedding clusters using dimensionality reduction.
        
        Args:
            embeddings_data: List of dicts with 'x', 'y', 'label', 'type'
        """
        fig = go.Figure()
        
        # Group by type
        types = set(item['type'] for item in embeddings_data)
        colors_map = {
            'class': '#00D9FF',
            'method': '#00FF9F',
            'field': '#FFD700',
            'interface': '#FF6B9D'
        }
        
        for item_type in types:
            filtered = [item for item in embeddings_data if item['type'] == item_type]
            
            fig.add_trace(go.Scatter(
                x=[item['x'] for item in filtered],
                y=[item['y'] for item in filtered],
                mode='markers+text',
                name=item_type.capitalize(),
                marker=dict(
                    size=10,
                    color=colors_map.get(item_type, '#999'),
                    line=dict(width=1, color='white')
                ),
                text=[item['label'] for item in filtered],
                textposition="top center",
                textfont=dict(size=8),
                hovertemplate='<b>%{text}</b><br>' +
                             'Type: ' + item_type + '<br>' +
                             'Position: (%{x:.2f}, %{y:.2f})<br>' +
                             '<extra></extra>'
            ))
        
        fig.update_layout(
            title="Code Embeddings - 2D Projection (t-SNE/UMAP)",
            xaxis_title="Dimension 1",
            yaxis_title="Dimension 2",
            template=self.theme,
            height=600,
            showlegend=True,
            hovermode='closest'
        )
        
        return fig
    
    def create_markov_walk_path(self, walk_path: List[Dict[str, Any]]) -> go.Figure:
        """
        Visualize Markov walk through code graph.
        
        Args:
            walk_path: List of nodes with 'name', 'depth', 'score', 'type'
        """
        fig = go.Figure()
        
        # Create tree layout
        depths = [node['depth'] for node in walk_path]
        scores = [node['score'] for node in walk_path]
        names = [node['name'] for node in walk_path]
        types = [node['type'] for node in walk_path]
        
        # Node colors by type
        color_map = {'calls': '#00D9FF', 'uses': '#00FF9F', 'extends': '#FF6B9D', 'implements': '#FFD700'}
        node_colors = [color_map.get(t, '#999') for t in types]
        
        # Create tree structure
        for i in range(len(walk_path) - 1):
            fig.add_trace(go.Scatter(
                x=[depths[i], depths[i+1]],
                y=[i, i+1],
                mode='lines',
                line=dict(color='rgba(255,255,255,0.3)', width=2),
                hoverinfo='skip',
                showlegend=False
            ))
        
        # Add nodes
        fig.add_trace(go.Scatter(
            x=depths,
            y=list(range(len(walk_path))),
            mode='markers+text',
            marker=dict(
                size=[20 + s*30 for s in scores],  # Size by score
                color=node_colors,
                line=dict(width=2, color='white')
            ),
            text=names,
            textposition='middle right',
            hovertemplate='<b>%{text}</b><br>' +
                         'Depth: %{x}<br>' +
                         'Score: %{customdata:.3f}<br>' +
                         '<extra></extra>',
            customdata=scores,
            showlegend=False
        ))
        
        fig.update_layout(
            title="Markov Walk Through Code Graph",
            xaxis_title="Depth Level",
            yaxis_title="Step in Walk",
            template=self.theme,
            height=max(400, len(walk_path) * 30),
            showlegend=False,
            yaxis=dict(showticklabels=False)
        )
        
        return fig
    
    def create_context_usage_heatmap(self, context_data: List[List[float]]) -> go.Figure:
        """
        Heatmap showing which retrieved contexts are actually used.
        
        Args:
            context_data: 2D array of usage scores
        """
        fig = go.Figure(data=go.Heatmap(
            z=context_data,
            colorscale='Viridis',
            hovertemplate='Query: %{x}<br>Context: %{y}<br>Usage: %{z:.2f}<br><extra></extra>'
        ))
        
        fig.update_layout(
            title="Context Usage Heatmap",
            xaxis_title="Query Index",
            yaxis_title="Retrieved Context Index",
            template=self.theme,
            height=500
        )
        
        return fig
    
    def create_retrieval_performance_timeline(self, timeline_data: List[Dict[str, Any]]) -> go.Figure:
        """
        Timeline of retrieval performance metrics.
        
        Args:
            timeline_data: List of dicts with 'timestamp', 'latency', 'results_count', 'avg_score'
        """
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=('Retrieval Latency', 'Results Count', 'Average Similarity Score'),
            vertical_spacing=0.1
        )
        
        timestamps = [item['timestamp'] for item in timeline_data]
        latencies = [item['latency'] for item in timeline_data]
        counts = [item['results_count'] for item in timeline_data]
        avg_scores = [item['avg_score'] for item in timeline_data]
        
        # Latency
        fig.add_trace(
            go.Scatter(x=timestamps, y=latencies, name='Latency', 
                      line=dict(color=self.colors['vector']),
                      fill='tozeroy'),
            row=1, col=1
        )
        
        # Results count
        fig.add_trace(
            go.Bar(x=timestamps, y=counts, name='Results', 
                  marker=dict(color=self.colors['graph'])),
            row=2, col=1
        )
        
        # Average score
        fig.add_trace(
            go.Scatter(x=timestamps, y=avg_scores, name='Avg Score',
                      line=dict(color=self.colors['high_relevance']),
                      mode='lines+markers'),
            row=3, col=1
        )
        
        fig.update_xaxes(title_text="Time", row=3, col=1)
        fig.update_yaxes(title_text="Latency (s)", row=1, col=1)
        fig.update_yaxes(title_text="Count", row=2, col=1)
        fig.update_yaxes(title_text="Score", row=3, col=1)
        
        fig.update_layout(
            title="RAG Retrieval Performance Over Time",
            template=self.theme,
            height=800,
            showlegend=False
        )
        
        return fig
    
    def create_rag_dashboard(
        self,
        search_results: List[Dict[str, Any]],
        funnel_data: Dict[str, int],
        timeline_data: List[Dict[str, Any]],
        walk_path: List[Dict[str, Any]]
    ) -> go.Figure:
        """Create comprehensive RAG dashboard"""
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Vector Search Results',
                'Retrieval Funnel',
                'Performance Timeline',
                'Graph Navigation'
            ),
            specs=[
                [{"type": "bar"}, {"type": "funnel"}],
                [{"type": "scatter"}, {"type": "scatter"}]
            ],
            vertical_spacing=0.15,
            horizontal_spacing=0.1
        )
        
        # 1. Vector search results (top left)
        sorted_results = sorted(search_results, key=lambda x: x['score'], reverse=True)[:10]
        methods = [r['method_name'][:20] for r in sorted_results]
        scores = [r['score'] for r in sorted_results]
        
        colors = []
        for score in scores:
            if score >= 0.8:
                colors.append(self.colors['high_relevance'])
            elif score >= 0.6:
                colors.append(self.colors['medium_relevance'])
            else:
                colors.append(self.colors['low_relevance'])
        
        fig.add_trace(
            go.Bar(x=methods, y=scores, marker=dict(color=colors), showlegend=False),
            row=1, col=1
        )
        
        # 2. Retrieval funnel (top right)
        stages = list(funnel_data.keys())
        counts = list(funnel_data.values())
        
        fig.add_trace(
            go.Funnel(y=stages, x=counts, textposition="inside", showlegend=False),
            row=1, col=2
        )
        
        # 3. Performance timeline (bottom left)
        timestamps = [item['timestamp'] for item in timeline_data[-20:]]
        latencies = [item['latency'] for item in timeline_data[-20:]]
        
        fig.add_trace(
            go.Scatter(x=timestamps, y=latencies, mode='lines+markers',
                      line=dict(color=self.colors['vector']), showlegend=False),
            row=2, col=1
        )
        
        # 4. Graph navigation (bottom right)
        depths = [node['depth'] for node in walk_path]
        scores_walk = [node['score'] for node in walk_path]
        
        fig.add_trace(
            go.Scatter(x=depths, y=list(range(len(walk_path))),
                      mode='markers+lines',
                      marker=dict(size=10, color=self.colors['graph']),
                      showlegend=False),
            row=2, col=2
        )
        
        # Update axes
        fig.update_xaxes(title_text="Method", row=1, col=1)
        fig.update_yaxes(title_text="Score", row=1, col=1, range=[0, 1])
        
        fig.update_xaxes(title_text="Time", row=2, col=1)
        fig.update_yaxes(title_text="Latency (s)", row=2, col=1)
        
        fig.update_xaxes(title_text="Depth", row=2, col=2)
        fig.update_yaxes(title_text="Step", row=2, col=2)
        
        fig.update_layout(
            title_text="RAG System Dashboard - Comprehensive View",
            template=self.theme,
            height=900,
            showlegend=False
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
        
        logger.info(f"RAG chart saved to {filepath}")

