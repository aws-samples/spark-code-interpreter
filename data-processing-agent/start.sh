#!/bin/bash

cleanup() {
    echo ""
    echo "🛑 Stopping Ray Code Interpreter..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo "✅ Backend stopped"
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo "✅ Frontend stopped"
    fi
    rm -f backend.pid frontend.pid
    exit 0
}

trap cleanup SIGINT SIGTERM

echo "🚀 Starting Ray Code Interpreter..."

# Start backend
echo "📦 Starting backend..."
cd backend
python3 -m uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
echo $BACKEND_PID > ../backend.pid
cd ..

# Wait for backend
sleep 3

# Start frontend
echo "🎨 Starting frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
echo $FRONTEND_PID > ../frontend.pid
cd ..

echo ""
echo "✅ Ray Code Interpreter started!"
echo "   Backend: http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo "   Ray Dashboard: http://$(cd backend && python3 -c 'from config import get_ray_public_ip; print(get_ray_public_ip())'):8265"
echo ""
echo "Press Ctrl+C to stop"
echo ""

wait
