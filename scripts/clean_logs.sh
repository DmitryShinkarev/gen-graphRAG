#!/bin/bash

# Simple Log Cleanup Script
# Cleans up and organizes logs in the original simple format

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧹 Cleaning up log files...${NC}"
echo ""

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS_DIR="$PROJECT_ROOT/logs"

# Create backup directory
BACKUP_DIR="$LOGS_DIR/backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo -e "${YELLOW}📦 Creating backup in: $BACKUP_DIR${NC}"

# Function to backup and clean log file
clean_log() {
    local log_file="$1"
    local description="$2"
    
    if [ -f "$log_file" ]; then
        local size=$(du -h "$log_file" | cut -f1)
        
        # Backup original
        cp "$log_file" "$BACKUP_DIR/"
        
        # Clean the log file (keep last 1000 lines if large)
        local lines=$(wc -l < "$log_file")
        if [ "$lines" -gt 1000 ]; then
            tail -n 1000 "$log_file" > "$log_file.tmp"
            mv "$log_file.tmp" "$log_file"
            echo -e "   ✅ ${GREEN}$description${NC} (${size}, ${lines} lines) → cleaned to 1000 lines"
        else
            echo -e "   ✅ ${GREEN}$description${NC} (${size}, ${lines} lines) → no cleaning needed"
        fi
    else
        echo -e "   ⚠️  ${YELLOW}$description${NC} - file not found"
    fi
}

# Clean main log files
echo -e "${YELLOW}🔄 Cleaning main log files...${NC}"
clean_log "$LOGS_DIR/api.log" "Main API log"
clean_log "$LOGS_DIR/api_current.log" "Current API session"
clean_log "$LOGS_DIR/api_server.log" "API server log"
clean_log "$LOGS_DIR/api_server_new.log" "New API server log"
clean_log "$LOGS_DIR/api_restart.log" "API restart log"

echo ""
echo -e "${YELLOW}🔄 Cleaning agent logs...${NC}"
clean_log "$LOGS_DIR/agents.log" "Agents log"

echo ""
echo -e "${YELLOW}🔄 Cleaning database logs...${NC}"
clean_log "$LOGS_DIR/database.log" "Database log"
clean_log "$LOGS_DIR/memgraph.log" "Memgraph log"
clean_log "$LOGS_DIR/qdrant.log" "Qdrant log"
clean_log "$LOGS_DIR/redis.log" "Redis log"

echo ""
echo -e "${YELLOW}🔄 Cleaning system logs...${NC}"
clean_log "$LOGS_DIR/main.log" "Main system log"

echo ""
echo -e "${YELLOW}🔄 Also cleaning python/logs (source logs)...${NC}"
PYTHON_LOGS_DIR="$PROJECT_ROOT/python/logs"
if [ -d "$PYTHON_LOGS_DIR" ]; then
    clean_log "$PYTHON_LOGS_DIR/api.log" "Python API log"
    clean_log "$PYTHON_LOGS_DIR/agents.log" "Python Agents log"
    clean_log "$PYTHON_LOGS_DIR/memgraph.log" "Python Memgraph log"
    clean_log "$PYTHON_LOGS_DIR/main.log" "Python Main log"
    clean_log "$PYTHON_LOGS_DIR/database.log" "Python Database log"
    clean_log "$PYTHON_LOGS_DIR/qdrant.log" "Python Qdrant log"
    clean_log "$PYTHON_LOGS_DIR/redis.log" "Python Redis log"
fi

echo ""
echo -e "${YELLOW}🔄 Removing obsolete logs...${NC}"
if [ -f "$LOGS_DIR/neo4j.log" ]; then
    mv "$LOGS_DIR/neo4j.log" "$BACKUP_DIR/neo4j_obsolete.log"
    echo -e "   🗑️  ${YELLOW}Neo4j log${NC} → moved to backup (obsolete)"
fi

# Create simple log viewer script
echo ""
echo -e "${YELLOW}🔧 Creating simple log viewer...${NC}"

cat > "$PROJECT_ROOT/scripts/view_logs_simple.py" << 'EOF'
#!/usr/bin/env python3
"""
Simple Log Viewer for Java Unit Test Agent
Views logs in the original simple format
"""

import argparse
import subprocess
import sys
from pathlib import Path

def view_log(component, follow=False, lines=50):
    """View log file"""
    logs_dir = Path("logs")
    log_file = logs_dir / f"{component}.log"
    
    if not log_file.exists():
        print(f"❌ Log file not found: {log_file}")
        print("Available logs:")
        for log in logs_dir.glob("*.log"):
            print(f"  • {log.stem}")
        return
    
    print(f"📄 Viewing: {log_file}")
    
    cmd = ["tail", "-n", str(lines)]
    if follow:
        cmd.append("-f")
    cmd.append(str(log_file))
    
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Log viewing stopped")

def list_logs():
    """List all available log files"""
    logs_dir = Path("logs")
    
    print("📁 Available log files:")
    print("")
    
    for log_file in sorted(logs_dir.glob("*.log")):
        size = log_file.stat().st_size
        print(f"  • {log_file.stem}: {size:,} bytes")

def main():
    parser = argparse.ArgumentParser(description="Simple log viewer")
    parser.add_argument("component", nargs="?", help="Log component to view")
    parser.add_argument("-l", "--list", action="store_true", help="List all logs")
    parser.add_argument("-f", "--follow", action="store_true", help="Follow log output")
    parser.add_argument("-n", "--lines", type=int, default=50, help="Number of lines to show")
    
    args = parser.parse_args()
    
    if args.list:
        list_logs()
    elif args.component:
        view_log(args.component, args.follow, args.lines)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
EOF

chmod +x "$PROJECT_ROOT/scripts/view_logs_simple.py"
echo "   ✅ view_logs_simple.py (executable)"

# Create summary
echo ""
echo -e "${YELLOW}📋 Creating cleanup summary...${NC}"

SUMMARY_FILE="$BACKUP_DIR/cleanup_summary.txt"
cat > "$SUMMARY_FILE" << EOF
Log Cleanup Summary
==================
Date: $(date)
Backup directory: $BACKUP_DIR

Actions performed:
- Backed up all original log files
- Cleaned large log files (>1000 lines) to keep last 1000 lines
- Removed obsolete Neo4j logs
- Created simple log viewer script

Log files cleaned:
$(ls -la "$LOGS_DIR"/*.log 2>/dev/null | wc -l) log files processed

Quick commands:
- View logs: python scripts/view_logs_simple.py [component]
- List logs: python scripts/view_logs_simple.py -l
- Follow logs: python scripts/view_logs_simple.py [component] -f
EOF

echo "   📄 cleanup_summary.txt"

echo ""
echo -e "${GREEN}✅ Log cleanup completed!${NC}"
echo ""
echo -e "${YELLOW}📋 Summary:${NC}"
echo "   • Backed up original logs to: $BACKUP_DIR"
echo "   • Cleaned large log files"
echo "   • Removed obsolete logs"
echo "   • Created simple log viewer"
echo ""
echo -e "${YELLOW}🚀 Quick commands:${NC}"
echo "   • View logs: ${BLUE}python scripts/view_logs_simple.py api${NC}"
echo "   • List logs: ${BLUE}python scripts/view_logs_simple.py -l${NC}"
echo "   • Follow logs: ${BLUE}python scripts/view_logs_simple.py api -f${NC}"
echo ""
echo -e "${GREEN}🎉 Logs are now clean and organized!${NC}"
