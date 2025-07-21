from typing import Any, Dict, Optional
from fastapi import HTTPException, status

class CustomException(HTTPException):
    """Base custom exception"""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str = "GENERIC_ERROR",
        headers: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code

# Authentication Exceptions
class AuthenticationException(CustomException):
    """Authentication related exceptions"""
    
    def __init__(self, detail: str = "Authentication failed", error_code: str = "AUTH_ERROR"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code=error_code
        )

class InvalidCredentialsException(AuthenticationException):
    """Invalid credentials exception"""
    
    def __init__(self):
        super().__init__(
            detail="Invalid email or password",
            error_code="INVALID_CREDENTIALS"
        )

class TokenExpiredException(AuthenticationException):
    """Token expired exception"""
    
    def __init__(self):
        super().__init__(
            detail="Token has expired",
            error_code="TOKEN_EXPIRED"
        )

class InvalidTokenException(AuthenticationException):
    """Invalid token exception"""
    
    def __init__(self):
        super().__init__(
            detail="Invalid token",
            error_code="INVALID_TOKEN"
        )

class MFARequiredException(AuthenticationException):
    """MFA required exception"""
    
    def __init__(self):
        super().__init__(
            detail="Multi-factor authentication required",
            error_code="MFA_REQUIRED"
        )

class InvalidMFACodeException(AuthenticationException):
    """Invalid MFA code exception"""
    
    def __init__(self):
        super().__init__(
            detail="Invalid MFA code",
            error_code="INVALID_MFA_CODE"
        )

class EmailNotVerifiedException(AuthenticationException):
    """Email not verified exception"""
    
    def __init__(self):
        super().__init__(
            detail="Email address must be verified before accessing this resource",
            error_code="EMAIL_NOT_VERIFIED"
        )

class MFANotSetupException(AuthenticationException):
    """MFA not setup exception"""
    
    def __init__(self):
        super().__init__(
            detail="Two-factor authentication must be enabled before accessing this resource",
            error_code="MFA_NOT_SETUP"
        )

# Security Exceptions
class SecurityException(CustomException):
    """Security related exceptions"""
    
    def __init__(self, detail: str = "Security violation detected", error_code: str = "SECURITY_ERROR"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code=error_code
        )

class SuspiciousActivityException(SecurityException):
    """Suspicious activity exception"""
    
    def __init__(self, detail: str = "Suspicious activity detected"):
        super().__init__(
            detail=detail,
            error_code="SUSPICIOUS_ACTIVITY"
        )

class RateLimitExceededException(SecurityException):
    """Rate limit exceeded exception"""
    
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(
            detail=detail,
            error_code="RATE_LIMIT_EXCEEDED"
        )

class IPBlockedException(SecurityException):
    """IP blocked exception"""
    
    def __init__(self, ip_address: str):
        super().__init__(
            detail=f"IP address {ip_address} is blocked",
            error_code="IP_BLOCKED"
        )

class AccountLockedException(SecurityException):
    """Account locked exception"""
    
    def __init__(self, detail: str = "Account is temporarily locked"):
        super().__init__(
            detail=detail,
            error_code="ACCOUNT_LOCKED"
        )

# Authorization Exceptions
class AuthorizationException(CustomException):
    """Authorization related exceptions"""
    
    def __init__(self, detail: str = "Access denied", error_code: str = "ACCESS_DENIED"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code=error_code
        )

class InsufficientPermissionsException(AuthorizationException):
    """Insufficient permissions exception"""
    
    def __init__(self):
        super().__init__(
            detail="Insufficient permissions for this action",
            error_code="INSUFFICIENT_PERMISSIONS"
        )

# User Exceptions
class UserException(CustomException):
    """User related exceptions"""
    
    def __init__(self, detail: str, error_code: str = "USER_ERROR"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code=error_code
        )

class UserNotFoundException(CustomException):
    """User not found exception"""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
            error_code="USER_NOT_FOUND"
        )

class UserAlreadyExistsException(UserException):
    """User already exists exception"""
    
    def __init__(self):
        super().__init__(
            detail="User with this email already exists",
            error_code="USER_ALREADY_EXISTS"
        )

class WeakPasswordException(UserException):
    """Weak password exception"""
    
    def __init__(self, requirements: str):
        super().__init__(
            detail=f"Password does not meet requirements: {requirements}",
            error_code="WEAK_PASSWORD"
        )

# Validation Exceptions
class ValidationException(CustomException):
    """Validation related exceptions"""
    
    def __init__(self, detail: str, error_code: str = "VALIDATION_ERROR"):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code=error_code
        )

class EmailValidationException(ValidationException):
    """Email validation exception"""
    
    def __init__(self):
        super().__init__(
            detail="Invalid email format",
            error_code="INVALID_EMAIL"
        )

# Business Logic Exceptions
class BusinessLogicException(CustomException):
    """Business logic related exceptions"""
    
    def __init__(self, detail: str, error_code: str = "BUSINESS_ERROR"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code=error_code
        )

class InsufficientFundsException(BusinessLogicException):
    """Insufficient funds exception"""
    
    def __init__(self):
        super().__init__(
            detail="Insufficient funds for this transaction",
            error_code="INSUFFICIENT_FUNDS"
        )

class AssetNotFoundException(CustomException):
    """Asset not found exception"""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
            error_code="ASSET_NOT_FOUND"
        )

class PortfolioNotFoundException(CustomException):
    """Portfolio not found exception"""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
            error_code="PORTFOLIO_NOT_FOUND"
        )

class TradeNotFoundException(CustomException):
    """Trade not found exception"""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trade not found",
            error_code="TRADE_NOT_FOUND"
        )

class AlertNotFoundException(CustomException):
    """Alert not found exception"""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
            error_code="ALERT_NOT_FOUND"
        )

# Rate Limiting Exceptions
class RateLimitException(CustomException):
    """Rate limit exceeded exception"""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            error_code="RATE_LIMIT_EXCEEDED"
        )

# External API Exceptions
class ExternalAPIException(CustomException):
    """External API related exceptions"""
    
    def __init__(self, detail: str, error_code: str = "EXTERNAL_API_ERROR"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code=error_code
        )

class MarketDataUnavailableException(ExternalAPIException):
    """Market data unavailable exception"""
    
    def __init__(self):
        super().__init__(
            detail="Market data is currently unavailable",
            error_code="MARKET_DATA_UNAVAILABLE"
        )

# File Upload Exceptions
class FileUploadException(CustomException):
    """File upload related exceptions"""
    
    def __init__(self, detail: str, error_code: str = "FILE_UPLOAD_ERROR"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_code=error_code
        )

class FileSizeExceededException(FileUploadException):
    """File size exceeded exception"""
    
    def __init__(self, max_size: int):
        super().__init__(
            detail=f"File size exceeds maximum allowed size of {max_size} bytes",
            error_code="FILE_SIZE_EXCEEDED"
        )

class InvalidFileTypeException(FileUploadException):
    """Invalid file type exception"""
    
    def __init__(self, allowed_types: list):
        super().__init__(
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}",
            error_code="INVALID_FILE_TYPE"
        )

# Database Exceptions
class DatabaseException(CustomException):
    """Database related exceptions"""
    
    def __init__(self, detail: str = "Database operation failed", error_code: str = "DATABASE_ERROR"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code=error_code
        )

class DuplicateEntryException(DatabaseException):
    """Duplicate entry exception"""
    
    def __init__(self, field: str):
        super().__init__(
            detail=f"Duplicate entry for field: {field}",
            error_code="DUPLICATE_ENTRY"
        )

# System Exceptions
class SystemException(CustomException):
    """System level exceptions"""
    
    def __init__(self, detail: str = "System error occurred", error_code: str = "SYSTEM_ERROR"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            error_code=error_code
        )

class MaintenanceModeException(CustomException):
    """Maintenance mode exception"""
    
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="System is currently under maintenance",
            error_code="MAINTENANCE_MODE"
        ) 