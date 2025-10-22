#!/bin/bash

# ===========================================
# Start Python API Server
# ===========================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Java Unit Test Agent API...${NC}"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found!${NC}"
    echo -e "${YELLOW}Run: cp .env.example .env${NC}"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "python/venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    cd python
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
fi

# Activate virtual environment
echo -e "${GREEN}🔧 Activating virtual environment...${NC}"
cd python
source venv/bin/activate

# Create logs directory
mkdir -p logs

# Check dependencies
echo -e "${GREEN}📦 Checking dependencies...${NC}"
pip install -q -r requirements.txt

# Check configuration
echo -e "${GREEN}⚙️  Checking configuration...${NC}"
python -c "from config import get_settings; settings = get_settings(); print(f'Environment: {settings.environment}')"

# Start server
echo -e "${GREEN}✨ Starting API server...${NC}"
echo -e "${YELLOW}Access API at: http://localhost:8000${NC}"
echo -e "${YELLOW}API Docs at: http://localhost:8000/docs${NC}"
echo -e ""

uvicorn api.server:app --reload --host 0.0.0.0 --port 8000
