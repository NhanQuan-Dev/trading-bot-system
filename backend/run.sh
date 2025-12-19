#!/bin/bash
# Script to run the Trading Bot Platform API server

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Trading Bot Platform API Server ===${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies if needed
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -q -r requirements.txt
fi
# Set PYTHONPATH to include src directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo -e "${YELLOW}Please copy .env.example to .env and configure your settings:${NC}"
    echo "  cp .env.example .env"
    echo "  nano .env"
    exit 1
fi

# Set PYTHONPATH to include src directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Run the application with uvicorn
echo -e "${GREEN}Starting API server...${NC}"
echo -e "${YELLOW}API Docs: http://localhost:8000/docs${NC}"
echo ""
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
