"""
API routes for RAG-specific visualization.
Provides endpoints for RAG metrics and charts.
"""

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, JSONResponse
import logging

from visualization.rag_charts import RAGCharts
from visualization.rag_metrics import RAGMetricsCollector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag-viz", tags=["rag-visualization"])


@router.get("/dashboard", response_class=HTMLResponse)
async def get_rag_dashboard(
    query: str = Query(default="calculateTotal", description="Search query"),
    theme: str = Query(default="plotly_dark", description="Plotly theme")
):
    """Get full RAG dashboard as HTML"""
    try:
        collector = RAGMetricsCollector()
        charts = RAGCharts(theme=theme)
        
        search_results = collector.generate_mock_search_results(query)
        funnel_data = collector.generate_funnel_data()
        timeline_data = collector.generate_timeline_data(24)
        walk_path = collector.generate_markov_walk(query)
        
        fig = charts.create_rag_dashboard(
            search_results, funnel_data, timeline_data, walk_path
        )
        
        return HTMLResponse(content=fig.to_html())
        
    except Exception as e:
        logger.error(f"Error generating RAG dashboard: {e}")
        return HTMLResponse(
            content=f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>",
            status_code=500
        )


@router.get("/search-results")
async def get_search_results(
    query: str = Query(default="calculateTotal", description="Search query"),
    limit: int = Query(default=20, ge=1, le=100)
):
    """Get vector search results as JSON"""
    try:
        collector = RAGMetricsCollector()
        results = collector.generate_mock_search_results(query, limit)
        return JSONResponse(content={
            "query": query,
            "results": results,
            "count": len(results)
        })
    except Exception as e:
        logger.error(f"Error getting search results: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@router.get("/chart/search", response_class=HTMLResponse)
async def get_search_chart(
    query: str = Query(default="calculateTotal"),
    format: str = Query(default="html", regex="^(html|json)$")
):
    """Get vector search similarity chart"""
    try:
        collector = RAGMetricsCollector()
        charts = RAGCharts()
        
        results = collector.generate_mock_search_results(query)
        fig = charts.create_vector_similarity_chart(results)
        
        if format == "json":
            return JSONResponse(content=fig.to_dict())
        else:
            return HTMLResponse(content=fig.to_html())
    except Exception as e:
        logger.error(f"Error generating search chart: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@router.get("/chart/funnel", response_class=HTMLResponse)
async def get_funnel_chart(format: str = Query(default="html", regex="^(html|json)$")):
    """Get retrieval funnel chart"""
    try:
        collector = RAGMetricsCollector()
        charts = RAGCharts()
        
        funnel_data = collector.generate_funnel_data()
        fig = charts.create_retrieval_funnel(funnel_data)
        
        if format == "json":
            return JSONResponse(content=fig.to_dict())
        else:
            return HTMLResponse(content=fig.to_html())
    except Exception as e:
        logger.error(f"Error generating funnel chart: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@router.get("/chart/timeline", response_class=HTMLResponse)
async def get_timeline_chart(
    hours: int = Query(default=24, ge=1, le=168),
    format: str = Query(default="html", regex="^(html|json)$")
):
    """Get performance timeline chart"""
    try:
        collector = RAGMetricsCollector()
        charts = RAGCharts()
        
        timeline_data = collector.generate_timeline_data(hours)
        fig = charts.create_retrieval_performance_timeline(timeline_data)
        
        if format == "json":
            return JSONResponse(content=fig.to_dict())
        else:
            return HTMLResponse(content=fig.to_html())
    except Exception as e:
        logger.error(f"Error generating timeline chart: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@router.get("/chart/walk", response_class=HTMLResponse)
async def get_walk_chart(
    start_method: str = Query(default="calculateTotal"),
    format: str = Query(default="html", regex="^(html|json)$")
):
    """Get Markov walk visualization"""
    try:
        collector = RAGMetricsCollector()
        charts = RAGCharts()
        
        walk_path = collector.generate_markov_walk(start_method)
        fig = charts.create_markov_walk_path(walk_path)
        
        if format == "json":
            return JSONResponse(content=fig.to_dict())
        else:
            return HTMLResponse(content=fig.to_html())
    except Exception as e:
        logger.error(f"Error generating walk chart: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@router.get("/chart/clusters", response_class=HTMLResponse)
async def get_clusters_chart(
    n_points: int = Query(default=100, ge=10, le=500),
    format: str = Query(default="html", regex="^(html|json)$")
):
    """Get embedding clusters visualization"""
    try:
        collector = RAGMetricsCollector()
        charts = RAGCharts()
        
        embeddings = collector.generate_embedding_clusters(n_points)
        fig = charts.create_embedding_clusters(embeddings)
        
        if format == "json":
            return JSONResponse(content=fig.to_dict())
        else:
            return HTMLResponse(content=fig.to_html())
    except Exception as e:
        logger.error(f"Error generating clusters chart: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )


@router.get("/summary")
async def get_rag_summary():
    """Get RAG system summary statistics"""
    try:
        collector = RAGMetricsCollector()
        summary = collector.get_rag_summary()
        return JSONResponse(content=summary)
    except Exception as e:
        logger.error(f"Error getting RAG summary: {e}")
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

