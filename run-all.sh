#!/bin/bash
# Script to run both Backend and Frontend simultaneously

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Trading Bot Platform - Full Stack       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Function to kill process on port
kill_port() {
    local port=$1
    local service=$2
    
    # Find PIDs using the port
    local pids=$(lsof -ti :$port 2>/dev/null)
    
    if [ ! -z "$pids" ]; then
        echo -e "${YELLOW}Found existing $service process(es) on port $port${NC}"
        echo -e "${YELLOW}Killing PIDs: $pids${NC}"
        kill -9 $pids 2>/dev/null
        sleep 1
        echo -e "${GREEN}✓ Cleaned up old $service process(es)${NC}"
    fi
}

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    
    # Kill background processes
    if [ ! -z "$BACKEND_PID" ]; then
        echo -e "${YELLOW}Stopping Backend (PID: $BACKEND_PID)...${NC}"
        kill -TERM $BACKEND_PID 2>/dev/null
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        echo -e "${YELLOW}Stopping Frontend (PID: $FRONTEND_PID)...${NC}"
        kill -TERM $FRONTEND_PID 2>/dev/null
    fi
    
    echo -e "${GREEN}✓ All services stopped${NC}"
    exit 0
}

# Set up trap to catch Ctrl+C
trap cleanup SIGINT SIGTERM

# Kill old processes
echo -e "${BLUE}[1/5] Cleaning up old processes...${NC}"
kill_port 8000 "Backend"
kill_port 8080 "Frontend"
echo ""

# Check if Redis is running
echo -e "${BLUE}[2/5] Checking Redis...${NC}"
if ! sudo docker ps | grep -q redis; then
    echo -e "${YELLOW}Starting Redis container...${NC}"
    sudo docker start redis 2>/dev/null || sudo docker run -d --name redis -p 6379:6379 redis:alpine
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Redis started${NC}"
    else
        echo -e "${RED}✗ Failed to start Redis${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Redis is running${NC}"
fi
echo ""

# Start Backend
echo -e "${BLUE}[3/5] Starting Backend API...${NC}"
cd backend

# Check if venv exists
if [ ! -d "venv" ]; then
    echo -e "${RED}✗ Virtual environment not found!${NC}"
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    echo -e "${YELLOW}Installing dependencies...${NC}"
    pip install -q -r requirements.txt
else
    source venv/bin/activate
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}✗ .env file not found!${NC}"
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}Copying .env.example to .env...${NC}"
        cp .env.example .env
        echo -e "${YELLOW}Please update .env with your actual configuration${NC}"
    else
        echo -e "${RED}✗ .env.example not found!${NC}"
        exit 1
    fi
fi

export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
nohup python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait a bit for backend to start
sleep 3

# Check if backend started successfully
if ps -p $BACKEND_PID > /dev/null; then
    echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"
    echo -e "  ${YELLOW}API: http://localhost:8000/api${NC}"
    echo -e "  ${YELLOW}Docs: http://localhost:8000/api/docs${NC}"
else
    echo -e "${RED}✗ Backend failed to start${NC}"
    echo -e "${YELLOW}Last 20 lines of backend.log:${NC}"
    tail -20 backend/backend.log
    exit 1
fi
echo ""

# Start Frontend
echo -e "${BLUE}[4/5] Starting Frontend...${NC}"
cd frontend

# Check if node_modules exists, if not install dependencies
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    npm install
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ Failed to install frontend dependencies${NC}"
        cd ..
        cleanup
        exit 1
    fi
fi

# Use npm instead of bun
nohup npm run dev > frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait a bit for frontend to start
sleep 3

# Check if frontend started successfully
if ps -p $FRONTEND_PID > /dev/null; then
    echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
    echo -e "  ${YELLOW}App: http://localhost:8080${NC}"
else
    echo -e "${RED}✗ Frontend failed to start${NC}"
    echo -e "${YELLOW}Last 20 lines of frontend.log:${NC}"
    tail -20 frontend/frontend.log
    cleanup
    exit 1
fi
echo ""

# Show status
echo -e "${BLUE}[5/5] Status Check${NC}"
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ All services running successfully!${NC}"
echo -e "${GREEN}════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Services:${NC}"
echo -e "  • Backend API: ${YELLOW}http://localhost:8000/api${NC}"
echo -e "  • API Docs:    ${YELLOW}http://localhost:8000/api/docs${NC}"
echo -e "  • Frontend:    ${YELLOW}http://localhost:8080${NC}"
echo -e "  • Redis:       ${YELLOW}localhost:6379${NC}"
echo ""
echo -e "${BLUE}Logs:${NC}"
echo -e "  • Backend:     ${YELLOW}tail -f backend/backend.log${NC}"
echo -e "  • Frontend:    ${YELLOW}tail -f frontend/frontend.log${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Keep script running and wait for interrupt
wait
