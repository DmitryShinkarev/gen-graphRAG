#!/usr/bin/env python3
"""
Standalone script to generate metrics visualizations.
Creates interactive Plotly dashboards for agent monitoring.

Usage:
    python visualize_metrics.py                    # Generate full dashboard
    python visualize_metrics.py --agent IndexerAgent  # Generate agent report
    python visualize_metrics.py --output my_dashboard.html
    python visualize_metrics.py --theme plotly_white
    python visualize_metrics.py --open               # Auto-open in browser
"""

import argparse
import sys
import webbrowser
from pathlib import Path

# Add python directory to path
sys.path.insert(0, str(Path(__file__).parent / "python"))

from visualization.dashboard_generator import DashboardGenerator
from visualization.metrics_collector import MetricsCollector
from visualization.plotly_charts import PlotlyCharts


def main():
    parser = argparse.ArgumentParser(
        description="Generate Plotly visualizations for Java Unit Test Agent metrics"
    )
    
    parser.add_argument(
        "--output", "-o",
        default="dashboard.html",
        help="Output HTML file path (default: dashboard.html)"
    )
    
    parser.add_argument(
        "--agent", "-a",
        choices=["IndexerAgent", "ResearcherAgent", "GeneratorAgent", "CriticAgent"],
        help="Generate report for specific agent only"
    )
    
    parser.add_argument(
        "--theme", "-t",
        choices=["plotly_dark", "plotly_white", "plotly", "ggplot2", "seaborn"],
        default="plotly_dark",
        help="Plotly theme (default: plotly_dark)"
    )
    
    parser.add_argument(
        "--open", "-b",
        action="store_true",
        help="Open dashboard in browser after generation"
    )
    
    parser.add_argument(
        "--save-data",
        help="Save metrics data to JSON file"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("📊 Java Unit Test Agent - Metrics Visualization")
    print("=" * 70)
    print()
    
    # Create generator
    generator = DashboardGenerator(theme=args.theme)
    
    # Save metrics data if requested
    if args.save_data:
        print(f"💾 Saving metrics data to: {args.save_data}")
        collector = MetricsCollector()
        collector.save_metrics(args.save_data)
        print(f"✅ Metrics saved\n")
    
    # Generate visualization
    if args.agent:
        print(f"📈 Generating report for {args.agent}...")
        output_path = generator.generate_agent_report(args.agent, args.output)
    else:
        print(f"📊 Generating comprehensive dashboard...")
        output_path = generator.generate_html_dashboard(args.output)
    
    print(f"✅ Dashboard generated: {output_path}")
    print()
    
    # Print summary
    collector = MetricsCollector()
    summary = collector.get_summary_stats()
    
    print("📋 Summary Statistics:")
    print(f"  Total Calls:  {summary['total_calls']}")
    print(f"  Total Tokens: {summary['total_tokens']:,}")
    print(f"  Total Cost:   ${summary['total_cost']}")
    print(f"  Period:       {summary['period']}")
    print()
    
    print("🤖 By Agent:")
    for agent_name, stats in summary['agents'].items():
        print(f"  {agent_name:20} {stats['calls']:4} calls | "
              f"{stats['tokens']:7,} tokens | "
              f"${stats['cost']:.4f} | "
              f"{stats['avg_latency']:.2f}s avg")
    print()
    
    # Open in browser if requested
    if args.open:
        print("🌐 Opening dashboard in browser...")
        webbrowser.open(f"file://{Path(output_path).absolute()}")
    else:
        print(f"💡 To view: open {output_path}")
        print(f"   Or run: python visualize_metrics.py --open")
    
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

