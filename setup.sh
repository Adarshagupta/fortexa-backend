#!/bin/bash

# Fortexa Backend Setup Script
echo "🚀 Setting up Fortexa Backend..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check for Python installation (for local development)
echo "🐍 Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo "✅ Python $PYTHON_VERSION found"
else
    echo "⚠️  Python 3 not found. Docker setup will proceed, but local development won't be available."
fi

# Create environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp environment.example .env
    echo "✅ Created .env file. Please edit it with your configuration."
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p uploads logs

# Start services with Docker Compose
echo "🐳 Starting services with Docker Compose..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Initialize database
echo "🗄️ Initializing database..."
docker-compose exec api prisma db push

# Generate some initial data
echo "🌱 Seeding database with initial data..."
docker-compose exec api python -c "
import asyncio
from app.core.database import init_db, db

async def seed_data():
    await init_db()
    print('Database seeded successfully!')

asyncio.run(seed_data())
"

echo "✅ Fortexa Backend setup completed!"
echo ""
echo "🔗 Access Points:"
echo "  - API: http://localhost:8000"
echo "  - API Documentation: http://localhost:8000/docs"
echo "  - Flower (Task Monitor): http://localhost:5555"
echo ""
echo "📚 Next Steps:"
echo "  1. Edit the .env file with your configuration"
echo "  2. Restart services: docker-compose restart"
echo "  3. Check logs: docker-compose logs -f"
echo ""
echo "🎉 Happy coding!" echo "  - API Documentation: http://localhost:8000/docs"
echo "  - Flower (Task Monitor): http://localhost:5555"
echo ""
echo "📚 Next Steps:"
echo "  1. Edit the .env file with your configuration"
echo "  2. Restart services: docker-compose restart"
echo "  3. Check logs: docker-compose logs -f"
echo ""
echo "🎉 Happy coding!" 
