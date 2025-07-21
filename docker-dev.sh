#!/bin/bash

# Docker Development Management Script
# This script provides easy commands for development workflow

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    printf "${1}${2}${NC}\n"
}

# Function to print header
print_header() {
    echo "=================================="
    print_color $BLUE "$1"
    echo "=================================="
}

# Check if .env file exists
check_env_file() {
    if [ ! -f ".env" ]; then
        print_color $YELLOW "Warning: .env file not found. Creating from docker.env.example..."
        if [ -f "docker.env.example" ]; then
            cp docker.env.example .env
            print_color $GREEN "Created .env file from docker.env.example"
            print_color $YELLOW "Please edit .env file with your actual values"
        else
            print_color $RED "Error: docker.env.example not found!"
            exit 1
        fi
    fi
}

# Development commands
dev_build() {
    print_header "Building Development Environment"
    check_env_file
    export BUILD_TARGET=development
    docker-compose build --no-cache
    print_color $GREEN "✅ Development build completed"
}

dev_up() {
    print_header "Starting Development Environment"
    check_env_file
    export BUILD_TARGET=development
    docker-compose up -d postgres redis
    print_color $BLUE "Waiting for services to be ready..."
    sleep 10
    docker-compose up -d api worker beat flower
    print_color $GREEN "✅ Development environment started"
    print_color $BLUE "🌐 API: http://localhost:8000"
    print_color $BLUE "📊 Flower: http://localhost:5555"
    print_color $BLUE "🔧 Health: http://localhost:8000/health"
}

dev_down() {
    print_header "Stopping Development Environment"
    docker-compose down
    print_color $GREEN "✅ Development environment stopped"
}

dev_restart() {
    print_header "Restarting Development Environment"
    dev_down
    dev_up
}

dev_logs() {
    print_header "Viewing Development Logs"
    docker-compose logs -f --tail=100 api worker beat
}

dev_shell() {
    print_header "Opening Development Shell"
    docker-compose exec api bash
}

dev_test() {
    print_header "Running Tests"
    docker-compose run --rm api pytest -v --cov=app
}

dev_migrate() {
    print_header "Running Database Migrations"
    docker-compose exec api prisma migrate dev
}

dev_seed() {
    print_header "Seeding Database"
    docker-compose exec api python seed_data.py
}

dev_reset() {
    print_header "Resetting Development Environment"
    docker-compose down -v
    docker-compose build --no-cache
    dev_up
    sleep 15
    dev_migrate
    dev_seed
    print_color $GREEN "✅ Development environment reset completed"
}

dev_clean() {
    print_header "Cleaning Development Environment"
    docker-compose down -v --remove-orphans
    docker system prune -f
    docker volume prune -f
    print_color $GREEN "✅ Development environment cleaned"
}

# Show help
show_help() {
    echo "Fortexa Backend - Docker Development Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  build     - Build development environment"
    echo "  up        - Start development environment"
    echo "  down      - Stop development environment"
    echo "  restart   - Restart development environment"
    echo "  logs      - View development logs"
    echo "  shell     - Open development shell"
    echo "  test      - Run tests"
    echo "  migrate   - Run database migrations"
    echo "  seed      - Seed database with test data"
    echo "  reset     - Reset development environment (clean start)"
    echo "  clean     - Clean development environment (remove all)"
    echo "  help      - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 build    # Build development environment"
    echo "  $0 up       # Start development environment"
    echo "  $0 logs     # View logs"
    echo "  $0 shell    # Open shell in API container"
    echo "  $0 test     # Run tests"
    echo "  $0 reset    # Full reset with clean database"
}

# Main script logic
case $1 in
    build)
        dev_build
        ;;
    up)
        dev_up
        ;;
    down)
        dev_down
        ;;
    restart)
        dev_restart
        ;;
    logs)
        dev_logs
        ;;
    shell)
        dev_shell
        ;;
    test)
        dev_test
        ;;
    migrate)
        dev_migrate
        ;;
    seed)
        dev_seed
        ;;
    reset)
        dev_reset
        ;;
    clean)
        dev_clean
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_color $RED "Error: Unknown command '$1'"
        echo ""
        show_help
        exit 1
        ;;
esac 