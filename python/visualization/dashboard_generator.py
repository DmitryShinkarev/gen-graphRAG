"""
Dashboard generator for creating complete HTML dashboards.
Combines multiple Plotly charts into interactive dashboards.
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from datetime import datetime

from .metrics_collector import MetricsCollector
from .plotly_charts import PlotlyCharts

logger = logging.getLogger(__name__)


class DashboardGenerator:
    """Generate complete HTML dashboards"""
    
    def __init__(self, theme: str = "plotly_dark"):
        self.collector = MetricsCollector()
        self.charts = PlotlyCharts(theme=theme)
        self.theme = theme
    
    def generate_html_dashboard(self, output_path: str = "dashboard.html") -> str:
        """Generate complete HTML dashboard"""
        
        # Collect data
        time_series = self.collector.generate_mock_time_series(24)
        summary_stats = self.collector.get_summary_stats()
        
        # Create charts
        calls_chart = self.charts.create_calls_timeline(time_series)
        tokens_chart = self.charts.create_tokens_chart(time_series)
        cost_chart = self.charts.create_cost_breakdown(summary_stats)
        latency_chart = self.charts.create_latency_comparison(time_series)
        dashboard_chart = self.charts.create_performance_dashboard(time_series, summary_stats)
        heatmap_chart = self.charts.create_heatmap(time_series, "calls")
        
        # Generate HTML
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Java Unit Test Agent - Metrics Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: {'#111' if self.theme == 'plotly_dark' else '#f5f5f5'};
            color: {'#fff' if self.theme == 'plotly_dark' else '#333'};
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            padding: 30px 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            color: white;
        }}
        
        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
            color: white;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: {'#1e1e1e' if self.theme == 'plotly_dark' else 'white'};
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            transition: transform 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        
        .stat-card h3 {{
            font-size: 0.9em;
            opacity: 0.7;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .stat-card .value {{
            font-size: 2.5em;
            font-weight: bold;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .stat-card .label {{
            font-size: 0.85em;
            opacity: 0.6;
            margin-top: 5px;
        }}
        
        .chart-container {{
            background: {'#1e1e1e' if self.theme == 'plotly_dark' else 'white'};
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }}
        
        .chart-title {{
            font-size: 1.3em;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid {'#333' if self.theme == 'plotly_dark' else '#eee'};
        }}
        
        .two-column {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        
        @media (max-width: 768px) {{
            .two-column {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .footer {{
            text-align: center;
            padding: 30px;
            margin-top: 50px;
            opacity: 0.6;
            border-top: 1px solid {'#333' if self.theme == 'plotly_dark' else '#ddd'};
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 Java Unit Test Agent</h1>
        <p>Real-time Metrics & Performance Dashboard</p>
        <p style="font-size: 0.9em; margin-top: 10px;">Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <h3>Total LLM Calls</h3>
            <div class="value">{summary_stats['total_calls']}</div>
            <div class="label">Last 24 hours</div>
        </div>
        <div class="stat-card">
            <h3>Total Tokens</h3>
            <div class="value">{summary_stats['total_tokens']:,}</div>
            <div class="label">Input + Output</div>
        </div>
        <div class="stat-card">
            <h3>Total Cost</h3>
            <div class="value">${summary_stats['total_cost']}</div>
            <div class="label">USD</div>
        </div>
        <div class="stat-card">
            <h3>Active Agents</h3>
            <div class="value">4</div>
            <div class="label">Operational</div>
        </div>
    </div>
    
    <div class="chart-container">
        <div class="chart-title">📊 Comprehensive Performance Dashboard</div>
        <div id="dashboard"></div>
    </div>
    
    <div class="two-column">
        <div class="chart-container">
            <div class="chart-title">📈 LLM Calls Timeline</div>
            <div id="calls-chart"></div>
        </div>
        <div class="chart-container">
            <div class="chart-title">🎯 Token Usage</div>
            <div id="tokens-chart"></div>
        </div>
    </div>
    
    <div class="two-column">
        <div class="chart-container">
            <div class="chart-title">💰 Cost Breakdown</div>
            <div id="cost-chart"></div>
        </div>
        <div class="chart-container">
            <div class="chart-title">⚡ Response Latency</div>
            <div id="latency-chart"></div>
        </div>
    </div>
    
    <div class="chart-container">
        <div class="chart-title">🔥 Activity Heatmap</div>
        <div id="heatmap-chart"></div>
    </div>
    
    <div class="footer">
        <p>Java Unit Test Agent - Powered by Langfuse, Plotly & OpenAI</p>
        <p style="margin-top: 10px; font-size: 0.9em;">
            Auto-refresh: <span id="countdown">60</span>s | 
            <a href="#" onclick="location.reload(); return false;" style="color: #667eea;">Refresh Now</a>
        </p>
    </div>
    
    <script>
        // Render charts
        const dashboardData = {dashboard_chart.to_json()};
        const callsData = {calls_chart.to_json()};
        const tokensData = {tokens_chart.to_json()};
        const costData = {cost_chart.to_json()};
        const latencyData = {latency_chart.to_json()};
        const heatmapData = {heatmap_chart.to_json()};
        
        Plotly.newPlot('dashboard', dashboardData.data, dashboardData.layout, {{responsive: true}});
        Plotly.newPlot('calls-chart', callsData.data, callsData.layout, {{responsive: true}});
        Plotly.newPlot('tokens-chart', tokensData.data, tokensData.layout, {{responsive: true}});
        Plotly.newPlot('cost-chart', costData.data, costData.layout, {{responsive: true}});
        Plotly.newPlot('latency-chart', latencyData.data, latencyData.layout, {{responsive: true}});
        Plotly.newPlot('heatmap-chart', heatmapData.data, heatmapData.layout, {{responsive: true}});
        
        // Auto-refresh countdown
        let countdown = 60;
        setInterval(() => {{
            countdown--;
            if (countdown <= 0) {{
                location.reload();
            }}
            document.getElementById('countdown').textContent = countdown;
        }}, 1000);
    </script>
</body>
</html>
"""
        
        # Save to file
        output_file = Path(output_path)
        output_file.write_text(html_content)
        
        logger.info(f"Dashboard generated: {output_file.absolute()}")
        return str(output_file.absolute())
    
    def generate_agent_report(self, agent_name: str, output_path: Optional[str] = None) -> str:
        """Generate detailed report for specific agent"""
        if output_path is None:
            output_path = f"{agent_name.lower()}_report.html"
        
        time_series = self.collector.generate_mock_time_series(24)
        summary_stats = self.collector.get_summary_stats()
        agent_stats = summary_stats["agents"].get(agent_name, {})
        
        # Create agent-specific chart
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                f'{agent_name} - Calls',
                f'{agent_name} - Tokens',
                f'{agent_name} - Latency',
                f'{agent_name} - Cost Over Time'
            )
        )
        
        timestamps = [entry["timestamp"] for entry in time_series]
        calls = [entry[agent_name]["calls"] for entry in time_series]
        tokens = [entry[agent_name]["tokens"] for entry in time_series]
        latency = [entry[agent_name]["latency"] for entry in time_series]
        cost = [entry[agent_name]["cost"] for entry in time_series]
        
        fig.add_trace(go.Scatter(x=timestamps, y=calls, name="Calls"), row=1, col=1)
        fig.add_trace(go.Bar(x=timestamps, y=tokens, name="Tokens"), row=1, col=2)
        fig.add_trace(go.Scatter(x=timestamps, y=latency, name="Latency"), row=2, col=1)
        fig.add_trace(go.Scatter(x=timestamps, y=cost, name="Cost", fill='tozeroy'), row=2, col=2)
        
        fig.update_layout(
            title_text=f"{agent_name} Performance Report",
            template=self.theme,
            height=800,
            showlegend=False
        )
        
        # Save
        fig.write_html(output_path)
        
        logger.info(f"Agent report generated: {output_path}")
        return output_path

