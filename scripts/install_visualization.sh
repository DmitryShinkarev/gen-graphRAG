#!/bin/bash
# Install Plotly visualization dependencies

echo "════════════════════════════════════════════════════════"
echo "📊 Installing Plotly Visualization Dependencies"
echo "════════════════════════════════════════════════════════"
echo

cd python
source venv/bin/activate

echo "📦 Installing Plotly and Kaleido..."
pip install plotly==5.24.0 kaleido==0.2.1

echo
echo "✅ Installation complete!"
echo
echo "To test:"
echo "  python ../visualize_metrics.py --output dashboard.html --open"
echo
echo "════════════════════════════════════════════════════════"

