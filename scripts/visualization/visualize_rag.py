#!/usr/bin/env python3
"""
RAG-specific visualization tool.
Creates interactive Plotly dashboards for RAG system metrics.

Usage:
    python visualize_rag.py                          # Full RAG dashboard
    python visualize_rag.py --chart search           # Vector search chart
    python visualize_rag.py --chart funnel           # Retrieval funnel
    python visualize_rag.py --chart timeline         # Performance timeline
    python visualize_rag.py --chart walk             # Markov walk
    python visualize_rag.py --chart clusters         # Embedding clusters
    python visualize_rag.py --chart heatmap          # Context usage
    python visualize_rag.py --open                   # Auto-open in browser
"""

import argparse
import sys
import webbrowser
from pathlib import Path

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent / "python"))

from visualization.rag_charts import RAGCharts
from visualization.rag_metrics import RAGMetricsCollector


def main():
    parser = argparse.ArgumentParser(
        description="Generate RAG system visualizations"
    )
    
    parser.add_argument(
        "--chart", "-c",
        choices=["search", "funnel", "timeline", "walk", "clusters", "heatmap", "dashboard"],
        default="dashboard",
        help="Type of chart to generate (default: dashboard)"
    )
    
    parser.add_argument(
        "--output", "-o",
        default="rag_dashboard.html",
        help="Output HTML file path (default: rag_dashboard.html)"
    )
    
    parser.add_argument(
        "--theme", "-t",
        choices=["plotly_dark", "plotly_white", "plotly"],
        default="plotly_dark",
        help="Plotly theme (default: plotly_dark)"
    )
    
    parser.add_argument(
        "--open", "-b",
        action="store_true",
        help="Open dashboard in browser after generation"
    )
    
    parser.add_argument(
        "--query", "-q",
        default="calculateTotal",
        help="Search query for demonstrations (default: calculateTotal)"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("📊 RAG System Visualization")
    print("=" * 70)
    print()
    
    # Create collector and charts
    collector = RAGMetricsCollector()
    charts = RAGCharts(theme=args.theme)
    
    print(f"📈 Generating {args.chart} visualization...")
    print()
    
    # Generate requested chart
    if args.chart == "search":
        search_results = collector.generate_mock_search_results(args.query)
        fig = charts.create_vector_similarity_chart(search_results)
        
    elif args.chart == "funnel":
        funnel_data = collector.generate_funnel_data()
        fig = charts.create_retrieval_funnel(funnel_data)
        
    elif args.chart == "timeline":
        timeline_data = collector.generate_timeline_data(24)
        fig = charts.create_retrieval_performance_timeline(timeline_data)
        
    elif args.chart == "walk":
        walk_path = collector.generate_markov_walk(args.query)
        fig = charts.create_markov_walk_path(walk_path)
        
    elif args.chart == "clusters":
        embeddings = collector.generate_embedding_clusters(100)
        fig = charts.create_embedding_clusters(embeddings)
        
    elif args.chart == "heatmap":
        heatmap_data = collector.generate_context_usage_heatmap()
        fig = charts.create_context_usage_heatmap(heatmap_data)
        
    else:  # dashboard
        search_results = collector.generate_mock_search_results(args.query)
        funnel_data = collector.generate_funnel_data()
        timeline_data = collector.generate_timeline_data(24)
        walk_path = collector.generate_markov_walk(args.query)
        fig = charts.create_rag_dashboard(search_results, funnel_data, timeline_data, walk_path)
    
    # Save
    fig.write_html(args.output)
    print(f"✅ Visualization saved: {args.output}")
    print()
    
    # Print summary
    summary = collector.get_rag_summary()
    print("📋 RAG System Summary:")
    print(f"  Total Vectors:        {summary['total_vectors']}")
    print(f"  Avg Retrieval Time:   {summary['avg_retrieval_latency']:.3f}s")
    print(f"  Avg Results/Query:    {summary['avg_results_per_query']:.1f}")
    print(f"  Avg Similarity Score: {summary['avg_similarity_score']:.3f}")
    print(f"  Top 10 Avg Score:     {summary['top_10_avg_score']:.3f}")
    print(f"  Cache Hit Rate:       {summary['cache_hit_rate']:.1%}")
    print()
    
    # Open in browser if requested
    if args.open:
        print("🌐 Opening in browser...")
        webbrowser.open(f"file://{Path(args.output).absolute()}")
    else:
        print(f"💡 To view: open {args.output}")
    
    print()
    print("=" * 70)
    print("✨ Done!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

