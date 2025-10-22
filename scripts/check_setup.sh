#!/bin/bash
# Quick setup verification script

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║         🔍 Java Unit Test Agent - Setup Verification            ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check .env file
echo "1. Checking .env file..."
if [ -f ".env" ]; then
    echo -e "${GREEN}✅ .env file exists${NC}"
    
    # Check if keys are configured
    if grep -q "OPENAI_API_KEY=sk-your-openai-api-key-here" .env; then
        echo -e "${YELLOW}⚠️  OpenAI API key not configured (still placeholder)${NC}"
    elif grep -q "OPENAI_API_KEY=sk-" .env; then
        echo -e "${GREEN}✅ OpenAI API key configured${NC}"
    else
        echo -e "${RED}❌ OpenAI API key not found${NC}"
    fi
    
    if grep -q "LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key-here" .env; then
        echo -e "${YELLOW}⚠️  Langfuse keys not configured (still placeholder)${NC}"
    elif grep -q "LANGFUSE_PUBLIC_KEY=pk-lf-" .env; then
        echo -e "${GREEN}✅ Langfuse keys configured${NC}"
    else
        echo -e "${YELLOW}⚠️  Langfuse keys not found (optional)${NC}"
    fi
else
    echo -e "${RED}❌ .env file not found${NC}"
fi

echo ""

# Check Python venv
echo "2. Checking Python virtual environment..."
if [ -d "python/venv" ]; then
    echo -e "${GREEN}✅ Python venv exists${NC}"
else
    echo -e "${YELLOW}⚠️  Python venv not found. Run: cd python && python -m venv venv${NC}"
fi

echo ""

# Check Docker containers
echo "3. Checking Docker services..."
if command -v docker &> /dev/null; then
    if docker ps | grep -q "memgraph\|qdrant\|redis"; then
        echo -e "${GREEN}✅ Docker services running${NC}"
        docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "memgraph|qdrant|redis" | sed 's/^/   /'
    else
        echo -e "${YELLOW}⚠️  Docker services not running. Run: docker-compose up -d${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Docker not found${NC}"
fi

echo ""

# Check Langfuse package
echo "4. Checking Langfuse installation..."
if [ -f "python/venv/bin/python" ]; then
    if python/venv/bin/python -c "import langfuse" 2>/dev/null; then
        VERSION=$(python/venv/bin/python -c "import langfuse; print(langfuse.__version__)")
        echo -e "${GREEN}✅ Langfuse package installed (version $VERSION)${NC}"
    else
        echo -e "${YELLOW}⚠️  Langfuse not installed. Run: pip install langfuse${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Python venv not activated${NC}"
fi

echo ""

# Summary
echo "═══════════════════════════════════════════════════════════════════"
echo ""
echo "📝 Next Steps:"
echo ""
echo "   If you see warnings above:"
echo "   1. Edit .env file and add your API keys"
echo "   2. Start Docker: docker-compose up -d"
echo "   3. Setup Python: cd python && python -m venv venv && source venv/bin/activate"
echo "   4. Install deps: pip install -r requirements.txt"
echo "   5. Start API: python api/server.py"
echo ""
echo "   For detailed Langfuse setup:"
echo "   • Read: LANGFUSE_QUICKSTART.md"
echo "   • Check: python3 check_langfuse.py"
echo ""
echo "═══════════════════════════════════════════════════════════════════"

