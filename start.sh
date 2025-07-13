#!/bin/bash

echo "🚀 Starting Fortexa Backend..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# Generate Prisma client if needed
echo "🔧 Checking Prisma client..."
prisma generate

# Start the FastAPI server
echo "🌟 Starting FastAPI server..."
echo "📍 API: http://localhost:8000"
echo "📖 Docs: http://localhost:8000/docs"
echo "🔧 Health: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"

uvicorn main:app --reload --host 0.0.0.0 --port 8000 

echo "🚀 Starting Fortexa Backend..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# Generate Prisma client if needed
echo "🔧 Checking Prisma client..."
prisma generate

# Start the FastAPI server
echo "🌟 Starting FastAPI server..."
echo "📍 API: http://localhost:8000"
echo "📖 Docs: http://localhost:8000/docs"
echo "🔧 Health: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"

uvicorn main:app --reload --host 0.0.0.0 --port 8000 
 