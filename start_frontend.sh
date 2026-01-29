#!/bin/bash
# Start the React frontend development server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

if [ ! -d "$FRONTEND_DIR" ]; then
    echo "Error: Frontend directory not found at $FRONTEND_DIR"
    echo "Please ensure the frontend has been initialized."
    exit 1
fi

cd "$FRONTEND_DIR"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

echo "Starting frontend development server..."
npm run dev
