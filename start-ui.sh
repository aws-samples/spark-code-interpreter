#!/bin/bash

# Start Spark Code Interpreter UI (backend + frontend)

cleanup() {
    echo ""
    echo "Stopping Spark Code Interpreter..."
    [ ! -z "$BACKEND_PID" ] && kill $BACKEND_PID 2>/dev/null && echo "Backend stopped"
    [ ! -z "$FRONTEND_PID" ] && kill $FRONTEND_PID 2>/dev/null && echo "Frontend stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "Starting Spark Code Interpreter UI..."
echo ""

# Ensure AWS profile is set
export AWS_PROFILE=${AWS_PROFILE:-vivekml+development-east}
echo "AWS Profile: $AWS_PROFILE"

# Start backend
echo "Starting backend (port 8000)..."
cd backend
python3 -m uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

sleep 3

# Start frontend
echo "Starting frontend (port 3000)..."
cd frontend
npm install --silent 2>/dev/null
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "Spark Code Interpreter started!"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo "  Health:   http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop"
echo ""

wait
