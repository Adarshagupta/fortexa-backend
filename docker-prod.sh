#!/bin/bash

# Docker Production Management Script
# This script provides commands for production deployment

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
        print_color $RED "Error: .env file not found!"
        print_color $YELLOW "Please create .env file with production values"
        print_color $BLUE "You can start from docker.env.example and environment.example"
        exit 1
    fi
}

# Security check for production
security_check() {
    print_header "Running Security Checks"
    
    # Check for default passwords
    if grep -q "fortexa123" .env; then
        print_color $RED "❌ Default database password detected!"
        print_color $YELLOW "Please change POSTGRES_PASSWORD in .env file"
        exit 1
    fi
    
    if grep -q "your-secret-key-here" .env; then
        print_color $RED "❌ Default secret key detected!"
        print_color $YELLOW "Please change SECRET_KEY in .env file"
        exit 1
    fi
    
    if grep -q "admin:admin" .env; then
        print_color $RED "❌ Default Flower credentials detected!"
        print_color $YELLOW "Please change FLOWER_USER and FLOWER_PASSWORD in .env file"
        exit 1
    fi
    
    # Check DEBUG setting
    if grep -q "DEBUG=true" .env; then
        print_color $YELLOW "⚠️  DEBUG mode is enabled in production!"
        print_color $YELLOW "Please set DEBUG=false in .env file"
        exit 1
    fi
    
    print_color $GREEN "✅ Security checks passed"
}

# Production commands
prod_build() {
    print_header "Building Production Environment"
    check_env_file
    security_check
    export BUILD_TARGET=production
    docker-compose build --no-cache
    print_color $GREEN "✅ Production build completed"
}

prod_up() {
    print_header "Starting Production Environment"
    check_env_file
    security_check
    export BUILD_TARGET=production
    
    # Start core services first
    docker-compose up -d postgres redis
    print_color $BLUE "Waiting for core services to be ready..."
    sleep 15
    
    # Start application services
    docker-compose up -d api worker beat flower
    print_color $BLUE "Waiting for application services to be ready..."
    sleep 10
    
    # Start nginx if in production profile
    if [ "$1" = "with-nginx" ]; then
        docker-compose --profile production up -d nginx
        print_color $BLUE "Nginx reverse proxy started"
    fi
    
    print_color $GREEN "✅ Production environment started"
    print_color $BLUE "🌐 API: http://localhost:8000"
    print_color $BLUE "📊 Flower: http://localhost:5555"
    print_color $BLUE "🔧 Health: http://localhost:8000/health"
    
    if [ "$1" = "with-nginx" ]; then
        print_color $BLUE "🌐 Nginx: http://localhost:80"
    fi
}

prod_down() {
    print_header "Stopping Production Environment"
    docker-compose --profile production down
    print_color $GREEN "✅ Production environment stopped"
}

prod_restart() {
    print_header "Restarting Production Environment"
    prod_down
    prod_up $1
}

prod_logs() {
    print_header "Viewing Production Logs"
    docker-compose logs -f --tail=100 api worker beat
}

prod_backup() {
    print_header "Creating Production Backup"
    
    # Create backup directory
    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup database
    print_color $BLUE "Backing up database..."
    docker-compose exec -T postgres pg_dump -U fortexa -d fortexa > "$BACKUP_DIR/database.sql"
    
    # Backup uploads
    print_color $BLUE "Backing up uploads..."
    docker-compose exec -T api tar -czf - -C /app uploads > "$BACKUP_DIR/uploads.tar.gz"
    
    # Backup logs
    print_color $BLUE "Backing up logs..."
    docker-compose exec -T api tar -czf - -C /app logs > "$BACKUP_DIR/logs.tar.gz"
    
    print_color $GREEN "✅ Backup completed: $BACKUP_DIR"
}

prod_restore() {
    if [ -z "$1" ]; then
        print_color $RED "Error: Please specify backup directory"
        print_color $BLUE "Usage: $0 restore backups/20240101_120000"
        exit 1
    fi
    
    BACKUP_DIR="$1"
    
    if [ ! -d "$BACKUP_DIR" ]; then
        print_color $RED "Error: Backup directory not found: $BACKUP_DIR"
        exit 1
    fi
    
    print_header "Restoring from Backup: $BACKUP_DIR"
    
    # Restore database
    if [ -f "$BACKUP_DIR/database.sql" ]; then
        print_color $BLUE "Restoring database..."
        docker-compose exec -T postgres psql -U fortexa -d fortexa < "$BACKUP_DIR/database.sql"
    fi
    
    # Restore uploads
    if [ -f "$BACKUP_DIR/uploads.tar.gz" ]; then
        print_color $BLUE "Restoring uploads..."
        docker-compose exec -T api tar -xzf - -C /app < "$BACKUP_DIR/uploads.tar.gz"
    fi
    
    print_color $GREEN "✅ Restore completed"
}

prod_health() {
    print_header "Checking Production Health"
    
    # Check API health
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_color $GREEN "✅ API is healthy"
    else
        print_color $RED "❌ API is unhealthy"
    fi
    
    # Check database
    if docker-compose exec -T postgres pg_isready -U fortexa -d fortexa > /dev/null 2>&1; then
        print_color $GREEN "✅ Database is healthy"
    else
        print_color $RED "❌ Database is unhealthy"
    fi
    
    # Check Redis
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        print_color $GREEN "✅ Redis is healthy"
    else
        print_color $RED "❌ Redis is unhealthy"
    fi
    
    # Check Flower
    if curl -f http://localhost:5555 > /dev/null 2>&1; then
        print_color $GREEN "✅ Flower is healthy"
    else
        print_color $RED "❌ Flower is unhealthy"
    fi
}

prod_update() {
    print_header "Updating Production Environment"
    
    # Pull latest changes
    print_color $BLUE "Pulling latest changes..."
    git pull origin main
    
    # Build new images
    prod_build
    
    # Restart services
    prod_restart
    
    # Run health check
    sleep 30
    prod_health
    
    print_color $GREEN "✅ Production update completed"
}

prod_scale() {
    if [ -z "$1" ] || [ -z "$2" ]; then
        print_color $RED "Error: Please specify service and scale count"
        print_color $BLUE "Usage: $0 scale worker 3"
        exit 1
    fi
    
    SERVICE="$1"
    SCALE="$2"
    
    print_header "Scaling $SERVICE to $SCALE instances"
    docker-compose up -d --scale "$SERVICE=$SCALE" "$SERVICE"
    print_color $GREEN "✅ Scaled $SERVICE to $SCALE instances"
}

# Show help
show_help() {
    echo "Fortexa Backend - Docker Production Script"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  build              - Build production environment"
    echo "  up [with-nginx]    - Start production environment"
    echo "  down               - Stop production environment"
    echo "  restart [with-nginx] - Restart production environment"
    echo "  logs               - View production logs"
    echo "  backup             - Create production backup"
    echo "  restore <dir>      - Restore from backup"
    echo "  health             - Check production health"
    echo "  update             - Update production environment"
    echo "  scale <service> <count> - Scale service instances"
    echo "  help               - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 build           # Build production environment"
    echo "  $0 up with-nginx   # Start with nginx reverse proxy"
    echo "  $0 backup          # Create backup"
    echo "  $0 restore backups/20240101_120000  # Restore backup"
    echo "  $0 scale worker 3  # Scale worker to 3 instances"
    echo "  $0 health          # Check all services health"
}

# Main script logic
case $1 in
    build)
        prod_build
        ;;
    up)
        prod_up $2
        ;;
    down)
        prod_down
        ;;
    restart)
        prod_restart $2
        ;;
    logs)
        prod_logs
        ;;
    backup)
        prod_backup
        ;;
    restore)
        prod_restore $2
        ;;
    health)
        prod_health
        ;;
    update)
        prod_update
        ;;
    scale)
        prod_scale $2 $3
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