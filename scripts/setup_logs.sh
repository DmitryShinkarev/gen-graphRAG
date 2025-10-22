#!/bin/bash
# Setup log file symbolic links
# This creates convenient symlinks in the root logs/ directory pointing to python/logs/

echo "🔗 Setting up log file symbolic links..."

# Create logs directory if it doesn't exist
mkdir -p logs

# Remove old files/links
rm -f logs/*.log

# Create symbolic links
ln -sf ../python/logs/api.log logs/api.log
ln -sf ../python/logs/agents.log logs/agents.log
ln -sf ../python/logs/qdrant.log logs/qdrant.log
ln -sf ../python/logs/redis.log logs/redis.log
ln -sf ../python/logs/memgraph.log logs/memgraph.log
ln -sf ../python/logs/database.log logs/database.log
ln -sf ../python/logs/main.log logs/main.log

echo "✅ Log symlinks created successfully!"
echo ""
echo "📁 You can now view logs from the project root:"
echo "   logs/api.log     → API server logs"
echo "   logs/agents.log  → Agent operations (detailed indexing)"
echo "   logs/qdrant.log  → Vector database logs"
echo "   logs/redis.log   → Cache logs"
echo "   logs/memgraph.log→ Graph database logs"
echo "   logs/database.log→ General database logs"

