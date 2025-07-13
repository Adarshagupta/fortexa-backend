from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime

# Base schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None

# Login schemas
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

class LoginResponse(BaseModel):
    user: 'UserResponse'
    tokens: Token
    mfa_required: bool = False
    mfa_setup_url: Optional[str] = None

# Registration schemas
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    phone_number: Optional[str] = Field(None, pattern=r'^\+?1?\d{9,15}$')
    date_of_birth: Optional[datetime] = None
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        if not any(c in '!@#$%^&*(),.?":{}|<>' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v

class RegisterResponse(BaseModel):
    user: 'UserResponse'
    tokens: Token
    mfa_setup_required: bool = True
    mfa_setup_url: Optional[str] = None

# Password reset schemas
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token_sent: bool

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class ResetPasswordResponse(BaseModel):
    message: str
    success: bool

# Email verification schemas
class EmailVerificationRequest(BaseModel):
    token: str

class EmailVerificationResponse(BaseModel):
    message: str
    success: bool

class ResendVerificationRequest(BaseModel):
    email: EmailStr

class ResendVerificationResponse(BaseModel):
    message: str
    verification_sent: bool

# MFA schemas
class MFASetupRequest(BaseModel):
    pass

class MFASetupResponse(BaseModel):
    qr_code_url: str
    secret_key: str
    backup_codes: list[str]

class MFAVerifyRequest(BaseModel):
    user_id: str = Field(..., description="User ID for MFA verification")
    code: str = Field(..., min_length=6, max_length=8, description="6-digit TOTP code or 8-character backup code")
    backup_code: Optional[str] = None

class MFAVerifyResponse(BaseModel):
    success: bool
    message: str
    tokens: Optional[Token] = None

class MFADisableRequest(BaseModel):
    password: str
    code: str = Field(..., min_length=6, max_length=6)

class MFADisableResponse(BaseModel):
    success: bool
    message: str

# Change password schemas
class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class ChangePasswordResponse(BaseModel):
    message: str
    success: bool

# Logout schemas
class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None

class LogoutResponse(BaseModel):
    message: str
    success: bool

# Refresh token schemas
class RefreshTokenRequest(BaseModel):
    refresh_token: str

class RefreshTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

# User response schema (to avoid circular imports)
class UserResponse(BaseModel):
    id: str
    email: str
    first_name: str
    last_name: str
    display_name: Optional[str] = None
    phone_number: Optional[str] = None
    profile_picture: Optional[str] = None
    is_active: bool
    is_email_verified: bool
    is_mfa_enabled: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Update forward references
LoginResponse.model_rebuild()
RegisterResponse.model_rebuild() 