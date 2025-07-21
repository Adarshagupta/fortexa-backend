import os
from typing import List, Any, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Fortexa Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True
    PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "postgresql://fortexa:fortexa123@localhost:5432/fortexa"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Password settings
    MIN_PASSWORD_LENGTH: int = 8
    REQUIRE_SPECIAL_CHARS: bool = True
    REQUIRE_NUMBERS: bool = True
    REQUIRE_UPPERCASE: bool = True
    REQUIRE_LOWERCASE: bool = True
    
    # MFA settings
    MFA_ISSUER: str = "Fortexa"
    MFA_WINDOW: int = 2
    
    # CORS settings (simplified)
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://localhost:8080,http://localhost:19006,https://fortexa.tech,https://www.fortexa.tech,https://app.fortexa.com"
    
    @property
    def cors_origins(self) -> List[str]:
        """Get CORS origins as a list"""
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",")]
    
    # Trusted hosts
    ALLOWED_HOSTS: str = "*"
    
    @property 
    def allowed_hosts(self) -> List[str]:
        """Get allowed hosts as a list"""
        if self.ALLOWED_HOSTS == "*":
            return ["*"]
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",")]
    
    # Email settings
    SMTP_TLS: bool = True
    SMTP_PORT: int = 587
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM_EMAIL: str = "noreply@fortexa.com"
    EMAILS_FROM_NAME: str = "Fortexa"
    
    # Frontend URL for email links
    FRONTEND_URL: str = "https://fortexa.tech"
    
    # Redis settings
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # Celery settings
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # External API settings
    CRYPTO_API_KEY: str = ""
    NEWS_API_KEY: str = ""
    MARKET_DATA_API_KEY: str = ""
    
    # API Key Encryption
    API_KEY_ENCRYPTION_KEY: str = ""
    
    # Angel One OAuth Integration
    ANGEL_ONE_CLIENT_ID: str = ""
    ANGEL_ONE_CLIENT_SECRET: str = ""
    ANGEL_ONE_REDIRECT_URL: str = "https://fortexa.tech/api/v1/api-keys/angel-one/callback"
    
    # Zerodha OAuth Integration  
    ZERODHA_CLIENT_ID: str = ""
    ZERODHA_CLIENT_SECRET: str = ""
    ZERODHA_REDIRECT_URL: str = "https://fortexa.tech/api/v1/api-keys/zerodha/callback"
    
    # File upload settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIRECTORY: str = "uploads"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60
    
    # Background jobs
    MARKET_DATA_UPDATE_INTERVAL: int = 60  # seconds
    NEWS_UPDATE_INTERVAL: int = 300  # seconds
    PORTFOLIO_UPDATE_INTERVAL: int = 300  # seconds
    
    # AI/ML settings
    AI_MODEL_PATH: str = "models/"
    PREDICTION_CONFIDENCE_THRESHOLD: float = 0.7
    
    # Notification settings
    PUSH_NOTIFICATION_ENABLED: bool = True
    EMAIL_NOTIFICATION_ENABLED: bool = True
    
    # Feature flags
    ENABLE_MFA: bool = True
    ENABLE_TRADING: bool = True
    ENABLE_AI_SIGNALS: bool = True
    ENABLE_PORTFOLIO_ANALYTICS: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings() 