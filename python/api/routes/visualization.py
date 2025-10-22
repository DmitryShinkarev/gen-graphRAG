"""
API routes for metrics visualization.
Provides endpoints to generate and serve Plotly charts.
"""

from fastapi import APIRouter, Query, Response
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional
import logging

from visualization.dashboard_generator import DashboardGenerator
from visualization.metrics_collector import MetricsCollector
from visualization.plotly_charts import PlotlyCharts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/visualization", tags=["visualization"])


@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(
    theme: str = Query(default="plotly_dark", description="Plotly theme")
):
    """
    Get full metrics dashboard as HTML.
    
    Themes: plotly_dark, plotly_white, plotly, ggplot2, seaborn
    """
    try:
        generator = DashboardGenerator(theme=theme)
        
        # Generate to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            output_path = f.name
        
        generator.generate_html_dashboard(output_path)
        
        # Read and return
        with open(output_path, 'r') as f:
            html_content = f.read()
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Error generating dashboard: {e}")
        return HTMLResponse(
            content=f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>",
            status_code=500
        )


@router.get("/agent/{agent_name}", response_class=HTMLResponse)
async def get_agent_report(
    agent_name: str,
    theme: str = Query(default="plotly_dark", description="Plotly theme")
):
    """Get detailed report for specific agent"""
    valid_agents = ["IndexerAgent", "ResearcherAgent", "GeneratorAgent", "CriticAgent"]
    
    if agent_name not in valid_agents:
        return HTMLResponse(
            content=f"<html><body><h1>Error</h1><p>Invalid agent: {agent_name}</p></body></html>",
            status_code=400
        )
    
    try:
        generator = DashboardGenerator(theme=theme)
        
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            output_path = f.name
        
        generator.generate_agent_report(agent_name, output_path)
        
        with open(output_path, 'r') as f:
            html_content = f.read()
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Error generating agent report: {e}")
        return HTMLResponse(
            content=f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>",
            status_code=500
        )


@router.get("/metrics/summary")
async def get_metrics_summary():
    """Get summary statistics as JSON"""
    try:
        collector = MetricsCollector()
        summary = collector.get_summary_stats()
        return JSONResponse(content=summary)
    except Exception as e:
        logger.error(f"Error collecting metrics: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@router.get("/metrics/timeseries")
async def get_metrics_timeseries(hours: int = Query(default=24, ge=1, le=168)):
    """Get time series data as JSON"""
    try:
        collector = MetricsCollector()
        time_series = collector.generate_mock_time_series(hours)
        return JSONResponse(content={
            "data": time_series,
            "hours": hours
        })
    except Exception as e:
        logger.error(f"Error generating time series: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@router.get("/chart/calls")
async def get_calls_chart(format: str = Query(default="json", regex="^(json|html)$")):
    """Get calls timeline chart"""
    try:
        collector = MetricsCollector()
        charts = PlotlyCharts()
        
        time_series = collector.generate_mock_time_series(24)
        fig = charts.create_calls_timeline(time_series)
        
        if format == "json":
            return JSONResponse(content=fig.to_dict())
        else:
            return HTMLResponse(content=fig.to_html())
            
    except Exception as e:
        logger.error(f"Error generating calls chart: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@router.get("/chart/tokens")
async def get_tokens_chart(format: str = Query(default="json", regex="^(json|html)$")):
    """Get tokens usage chart"""
    try:
        collector = MetricsCollector()
        charts = PlotlyCharts()
        
        time_series = collector.generate_mock_time_series(24)
        fig = charts.create_tokens_chart(time_series)
        
        if format == "json":
            return JSONResponse(content=fig.to_dict())
        else:
            return HTMLResponse(content=fig.to_html())
            
    except Exception as e:
        logger.error(f"Error generating tokens chart: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@router.get("/chart/cost")
async def get_cost_chart(format: str = Query(default="json", regex="^(json|html)$")):
    """Get cost breakdown chart"""
    try:
        collector = MetricsCollector()
        charts = PlotlyCharts()
        
        summary = collector.get_summary_stats()
        fig = charts.create_cost_breakdown(summary)
        
        if format == "json":
            return JSONResponse(content=fig.to_dict())
        else:
            return HTMLResponse(content=fig.to_html())
            
    except Exception as e:
        logger.error(f"Error generating cost chart: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@router.get("/chart/latency")
async def get_latency_chart(format: str = Query(default="json", regex="^(json|html)$")):
    """Get latency comparison chart"""
    try:
        collector = MetricsCollector()
        charts = PlotlyCharts()
        
        time_series = collector.generate_mock_time_series(24)
        fig = charts.create_latency_comparison(time_series)
        
        if format == "json":
            return JSONResponse(content=fig.to_dict())
        else:
            return HTMLResponse(content=fig.to_html())
            
    except Exception as e:
        logger.error(f"Error generating latency chart: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

