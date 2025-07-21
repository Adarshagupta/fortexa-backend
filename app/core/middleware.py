import time
from typing import Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import redis
from app.core.config import settings
from app.core.logger import logger
from app.core.exceptions import RateLimitException, MaintenanceModeException

# Redis client for rate limiting
redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.public_paths = [
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/forgot-password",
            "/api/v1/auth/reset-password",
            "/api/v1/auth/verify-email",
            "/api/v1/market/public",
            "/api/v1/news/public",
        ]
    
    async def dispatch(self, request: Request, call_next):
        # Skip authentication for public paths
        if any(request.url.path.startswith(path) for path in self.public_paths):
            return await call_next(request)
        
        # Check for auth token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid authorization header", "error_code": "MISSING_AUTH_TOKEN"}
            )
        
        # Extract token
        token = auth_header.split(" ")[1]
        request.state.token = token
        
        return await call_next(request)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.requests_per_minute = settings.RATE_LIMIT_REQUESTS
        self.window_seconds = settings.RATE_LIMIT_WINDOW
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health check
        if request.url.path == "/health":
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Check rate limit
        if await self._is_rate_limited(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise RateLimitException()
        
        return await call_next(request)
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host
    
    async def _is_rate_limited(self, client_ip: str) -> bool:
        """Check if client IP is rate limited"""
        try:
            key = f"rate_limit:{client_ip}"
            current_requests = redis_client.get(key)
            
            if current_requests is None:
                # First request from this IP
                redis_client.setex(key, self.window_seconds, 1)
                return False
            
            if int(current_requests) >= self.requests_per_minute:
                return True
            
            # Increment counter
            redis_client.incr(key)
            return False
            
        except Exception as e:
            logger.error(f"Rate limiting error: {e}")
            # If Redis is down, don't block requests
            return False

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Request logging middleware"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(f"Request: {request.method} {request.url.path}")
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {response.status_code} - {process_time:.4f}s"
        )
        
        return response

class MaintenanceMiddleware(BaseHTTPMiddleware):
    """Maintenance mode middleware"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.maintenance_mode = False  # This would be controlled by a config or Redis flag
    
    async def dispatch(self, request: Request, call_next):
        # Check if in maintenance mode
        if self.maintenance_mode:
            # Allow health check during maintenance
            if request.url.path == "/health":
                return await call_next(request)
            
            raise MaintenanceModeException()
        
        return await call_next(request)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Security headers middleware"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        
        return response

class CORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.allowed_origins = settings.cors_origins
    
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
            if origin in self.allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response
        
        response = await call_next(request)
        
        # Add CORS headers to response
        if origin in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response

class UserContextMiddleware(BaseHTTPMiddleware):
    """User context middleware to extract user info from token"""
    
    async def dispatch(self, request: Request, call_next):
        # This middleware would decode the JWT token and add user info to request state
        # For now, we'll just pass through
        return await call_next(request) 