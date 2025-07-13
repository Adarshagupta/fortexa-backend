# Docker Deployment Guide

This guide provides comprehensive instructions for deploying the Fortexa backend using Docker.

## 📋 Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 4GB RAM available
- Port 8000, 5432, 6379, 5555 available

## 🚀 Quick Start

### Development Environment

1. **Clone and Setup**
   ```bash
   cd backend
   chmod +x docker-dev.sh docker-prod.sh
   ```

2. **Create Environment File**
   ```bash
   cp docker.env.example .env
   # Edit .env file with your settings
   ```

3. **Start Development Environment**
   ```bash
   ./docker-dev.sh build
   ./docker-dev.sh up
   ```

4. **Access Services**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Flower (Celery Monitor): http://localhost:5555
   - Health Check: http://localhost:8000/health

### Production Environment

1. **Create Production Environment**
   ```bash
   cp docker.env.example .env
   cp environment.example .env.production
   # Edit both files with production values
   ```

2. **Build and Deploy**
   ```bash
   ./docker-prod.sh build
   ./docker-prod.sh up
   ```

## 🛠️ Development Commands

### docker-dev.sh Commands

```bash
# Build development environment
./docker-dev.sh build

# Start development environment
./docker-dev.sh up

# Stop development environment
./docker-dev.sh down

# Restart development environment
./docker-dev.sh restart

# View logs
./docker-dev.sh logs

# Open shell in API container
./docker-dev.sh shell

# Run tests
./docker-dev.sh test

# Run database migrations
./docker-dev.sh migrate

# Seed database with test data
./docker-dev.sh seed

# Full reset (clean database)
./docker-dev.sh reset

# Clean everything (remove all data)
./docker-dev.sh clean
```

## 🏭 Production Commands

### docker-prod.sh Commands

```bash
# Build production environment
./docker-prod.sh build

# Start production environment
./docker-prod.sh up

# Start with nginx reverse proxy
./docker-prod.sh up with-nginx

# Stop production environment
./docker-prod.sh down

# Restart production environment
./docker-prod.sh restart

# View logs
./docker-prod.sh logs

# Create backup
./docker-prod.sh backup

# Restore from backup
./docker-prod.sh restore backups/20240101_120000

# Check health of all services
./docker-prod.sh health

# Update production environment
./docker-prod.sh update

# Scale services
./docker-prod.sh scale worker 3
```

## 🐳 Docker Architecture

### Services Overview

| Service | Purpose | Port | Dependencies |
|---------|---------|------|--------------|
| **postgres** | PostgreSQL database | 5432 | - |
| **redis** | Redis cache & message broker | 6379 | - |
| **api** | FastAPI application | 8000 | postgres, redis |
| **worker** | Celery worker | - | postgres, redis |
| **beat** | Celery beat scheduler | - | postgres, redis |
| **flower** | Celery monitoring | 5555 | redis |
| **nginx** | Reverse proxy (production) | 80, 443 | api |

### Multi-Stage Dockerfile

The Dockerfile supports multiple build targets:

- **base**: Common dependencies
- **development**: Development tools and hot reload
- **production**: Optimized for production with Gunicorn
- **testing**: Testing dependencies and coverage

## 🔧 Configuration

### Environment Variables

Create `.env` file from templates:

```bash
# Docker-specific variables
cp docker.env.example .env

# Application variables
cp environment.example .env.app
```

### Key Environment Variables

#### Database Configuration
```env
POSTGRES_DB=fortexa
POSTGRES_USER=fortexa
POSTGRES_PASSWORD=your-secure-password
POSTGRES_PORT=5432
```

#### Security Settings
```env
SECRET_KEY=your-very-secure-secret-key
DEBUG=false
ALGORITHM=HS256
```

#### Email Configuration
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

#### External APIs
```env
CRYPTO_API_KEY=your-crypto-api-key
NEWS_API_KEY=your-news-api-key
```

## 🔒 Security Considerations

### Production Security Checklist

- [ ] Change default passwords
- [ ] Use strong SECRET_KEY
- [ ] Set DEBUG=false
- [ ] Configure CORS properly
- [ ] Use SSL certificates
- [ ] Enable rate limiting
- [ ] Set up firewall rules
- [ ] Use non-root user in containers

### SSL/TLS Configuration

1. **Generate SSL Certificates**
   ```bash
   mkdir -p nginx/ssl
   # Place your certificates as:
   # nginx/ssl/server.crt
   # nginx/ssl/server.key
   ```

2. **Self-signed Certificate (Development)**
   ```bash
   mkdir -p nginx/ssl
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
     -keyout nginx/ssl/server.key \
     -out nginx/ssl/server.crt
   ```

## 📊 Monitoring & Logging

### Health Checks

All services include health checks:
- **API**: HTTP health endpoint
- **Database**: PostgreSQL connection test
- **Redis**: Redis ping command
- **Celery**: Celery inspect ping

### Logging

Logs are stored in:
- **Application logs**: `./logs/` directory
- **Container logs**: `docker-compose logs`

### Monitoring Services

- **Flower**: Celery task monitoring at http://localhost:5555
- **Health endpoint**: API health at http://localhost:8000/health

## 🔧 Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Check which process is using the port
   lsof -i :8000
   # Kill the process or change port in .env
   ```

2. **Database Connection Issues**
   ```bash
   # Check database health
   docker-compose exec postgres pg_isready -U fortexa
   # View database logs
   docker-compose logs postgres
   ```

3. **Redis Connection Issues**
   ```bash
   # Check Redis health
   docker-compose exec redis redis-cli ping
   # View Redis logs
   docker-compose logs redis
   ```

4. **Out of Memory**
   ```bash
   # Check container memory usage
   docker stats
   # Increase Docker memory limit
   ```

### Debugging

1. **View Service Logs**
   ```bash
   docker-compose logs -f api
   docker-compose logs -f worker
   ```

2. **Access Container Shell**
   ```bash
   docker-compose exec api bash
   docker-compose exec postgres psql -U fortexa -d fortexa
   ```

3. **Check Service Status**
   ```bash
   docker-compose ps
   docker-compose top
   ```

## 📈 Performance Optimization

### Production Optimizations

1. **Resource Limits**
   - Set memory limits for each service
   - Configure proper CPU limits
   - Use health checks for automatic restart

2. **Database Optimization**
   - Configure PostgreSQL memory settings
   - Set up connection pooling
   - Regular database maintenance

3. **Caching Strategy**
   - Redis caching for API responses
   - Database query caching
   - Static file caching with nginx

4. **Load Balancing**
   - Scale API containers: `./docker-prod.sh scale api 3`
   - Scale worker containers: `./docker-prod.sh scale worker 4`
   - Use nginx load balancing

## 🔄 Backup & Recovery

### Automated Backups

```bash
# Create backup
./docker-prod.sh backup

# Restore from backup
./docker-prod.sh restore backups/20240101_120000
```

### Manual Backup

```bash
# Database backup
docker-compose exec postgres pg_dump -U fortexa -d fortexa > backup.sql

# Uploads backup
docker-compose exec api tar -czf uploads.tar.gz uploads/
```

## 🚀 Deployment Strategies

### Blue-Green Deployment

1. **Deploy to staging**
   ```bash
   export COMPOSE_PROJECT_NAME=fortexa-staging
   ./docker-prod.sh build
   ./docker-prod.sh up
   ```

2. **Test staging environment**
   ```bash
   ./docker-prod.sh health
   ```

3. **Switch to production**
   ```bash
   export COMPOSE_PROJECT_NAME=fortexa-prod
   ./docker-prod.sh down
   ./docker-prod.sh up
   ```

### Rolling Updates

```bash
# Update with zero downtime
./docker-prod.sh update
```

## 📋 Maintenance

### Regular Maintenance Tasks

1. **Update Dependencies**
   ```bash
   # Update base images
   docker-compose pull
   ./docker-prod.sh build
   ```

2. **Clean Up**
   ```bash
   # Remove unused images
   docker system prune -f
   # Remove unused volumes
   docker volume prune -f
   ```

3. **Database Maintenance**
   ```bash
   # Vacuum PostgreSQL
   docker-compose exec postgres vacuumdb -U fortexa -d fortexa
   ```

## 📞 Support

For issues or questions:
1. Check this documentation
2. Review container logs
3. Check GitHub issues
4. Contact the development team

## 🔗 Related Documentation

- [API Documentation](http://localhost:8000/docs)
- [Celery Documentation](https://docs.celeryproject.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Documentation](https://docs.docker.com/) 