#!/bin/bash

# Phase 3 ATI CEO Dashboard Startup Script
# This script starts both backend and frontend with proper configuration

set -e

echo "🚀 Starting Phase 3 - ATI CEO Dashboard..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
echo -e "${BLUE}Checking dependencies...${NC}"

if ! command_exists python3; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

if ! command_exists npm; then
    echo -e "${RED}Error: Node.js/npm is not installed${NC}"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "simple_main.py" ]; then
    echo -e "${RED}Error: simple_main.py not found. Please run this script from the project root directory.${NC}"
    exit 1
fi

# Kill any existing processes
echo -e "${BLUE}Stopping any existing servers...${NC}"
pkill -f "python.*simple_main.py" 2>/dev/null || true
pkill -f "npm start" 2>/dev/null || true
sleep 2

# Install Python dependencies if needed
if [ ! -d "venv" ] || [ ! -f "venv/bin/activate" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

echo -e "${BLUE}Installing/updating Python dependencies...${NC}"
source venv/bin/activate
pip install -r requirements-minimal.txt > /dev/null 2>&1

# Start backend
echo -e "${GREEN}Starting backend server on port 8000...${NC}"
nohup python simple_main.py > backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to start
sleep 3

# Test backend
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✅ Backend is running successfully${NC}"
else
    echo -e "${RED}❌ Backend failed to start${NC}"
    exit 1
fi

# Start frontend
echo -e "${GREEN}Starting frontend server on port 3000...${NC}"
cd frontend

# Install frontend dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${BLUE}Installing frontend dependencies...${NC}"
    npm install --legacy-peer-deps > /dev/null 2>&1
fi

# Start React development server without HOST environment variable
unset HOST
nohup npm start > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

cd ..

# Wait for frontend to start
echo -e "${BLUE}Waiting for frontend to start...${NC}"
sleep 15

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down servers...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    echo -e "${GREEN}Servers stopped.${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

echo -e "${GREEN}✅ Phase 3 Dashboard is running!${NC}"
echo -e "${BLUE}Backend API: http://localhost:8000${NC}"
echo -e "${BLUE}Frontend UI: http://localhost:3000${NC}"
echo -e "${BLUE}API Health: http://localhost:8000/health${NC}"
echo -e "${BLUE}API Documentation: http://localhost:8000/docs${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""
echo -e "${GREEN}🌐 Open your browser to: http://localhost:3000${NC}"

# Wait for background processes
wait