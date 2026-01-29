#!/bin/bash
# Start both the API backend and React frontend

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "============================================"
echo "Microsoft Foundry Bootstrap - Full Stack"
echo "============================================"
echo ""

# Start API server in background
echo "Starting API server on http://localhost:8000..."
python "$SCRIPT_DIR/start_api.py" &
API_PID=$!

# Give API server time to start
sleep 2

# Check if frontend exists
if [ -d "$SCRIPT_DIR/frontend" ]; then
    echo "Starting frontend on http://localhost:5173..."
    cd "$SCRIPT_DIR/frontend"

    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo "Installing frontend dependencies..."
        npm install
    fi

    npm run dev &
    FRONTEND_PID=$!

    echo ""
    echo "============================================"
    echo "Services started:"
    echo "  API:      http://localhost:8000"
    echo "  Docs:     http://localhost:8000/docs"
    echo "  Frontend: http://localhost:5173"
    echo "============================================"
    echo ""
    echo "Press Ctrl+C to stop all services"

    # Wait for either process to exit
    trap "kill $API_PID $FRONTEND_PID 2>/dev/null" EXIT
    wait $API_PID $FRONTEND_PID
else
    echo ""
    echo "============================================"
    echo "API server started on http://localhost:8000"
    echo "Documentation: http://localhost:8000/docs"
    echo "============================================"
    echo ""
    echo "Note: Frontend not found. Initialize it with:"
    echo "  cd frontend && npm create vite@latest . -- --template react-ts"
    echo ""
    echo "Press Ctrl+C to stop"

    trap "kill $API_PID 2>/dev/null" EXIT
    wait $API_PID
fi
