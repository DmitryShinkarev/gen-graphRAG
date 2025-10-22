#!/bin/bash

# ===========================================
# Java Unit Test Agent - Quick Start Script
# ===========================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     Java Unit Test Agent - Quick Start                    ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}⚠️  IMPORTANT: Please edit .env and set your OPENAI_API_KEY!${NC}"
    echo -e "${YELLOW}Press Enter when ready...${NC}"
    read
fi

# Check Docker
echo -e "${GREEN}🐳 Checking Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker first.${NC}"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker is not running. Please start Docker.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker is running${NC}"

# Start Docker services
echo -e "${GREEN}🚀 Starting Docker services...${NC}"
docker-compose up -d

# Wait for services
echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
sleep 10

# Check services
echo -e "${GREEN}🔍 Checking service health...${NC}"

# Check Qdrant
if curl -sf http://localhost:6333/health > /dev/null; then
    echo -e "${GREEN}  ✅ Qdrant: OK${NC}"
else
    echo -e "${RED}  ❌ Qdrant: FAIL${NC}"
fi

# Check Memgraph
if nc -z localhost 7687 2>/dev/null; then
    echo -e "${GREEN}  ✅ Memgraph: OK${NC}"
else
    echo -e "${RED}  ❌ Memgraph: FAIL${NC}"
fi

# Check Redis
if redis-cli -h localhost ping 2>/dev/null | grep -q PONG; then
    echo -e "${GREEN}  ✅ Redis: OK${NC}"
else
    echo -e "${RED}  ❌ Redis: FAIL (non-critical)${NC}"
fi

echo -e ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Services are ready!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e ""
echo -e "${YELLOW}📊 Available Dashboards:${NC}"
echo -e "  - Memgraph Lab:     ${GREEN}http://localhost:3000${NC}"
echo -e "  - Qdrant:           ${GREEN}http://localhost:6333/dashboard${NC}"
echo -e "  - Grafana:          ${GREEN}http://localhost:3001${NC} (admin/admin)"
echo -e "  - Prometheus:       ${GREEN}http://localhost:9090${NC}"
echo -e ""
echo -e "${YELLOW}🔧 Next Steps:${NC}"
echo -e "  1. Start Python API:"
echo -e "     ${GREEN}cd python && uvicorn api.server:app --reload${NC}"
echo -e ""
echo -e ""
echo -e "  3. Access:"
echo -e "     - API:       ${GREEN}http://localhost:8000${NC}"
echo -e "     - API Docs:  ${GREEN}http://localhost:8000/docs${NC}"
echo -e ""
echo -e ""
echo -e "${YELLOW}📚 Documentation:${NC}"
echo -e "  - Quick Start:  ${GREEN}docs/START_NOW.md${NC}"
echo -e "  - API Guide:    ${GREEN}docs/RUN_INSTRUCTIONS.md${NC}"
echo -e ""
echo -e "${GREEN}✨ Happy Testing!${NC}"
