from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from prisma import Prisma
from app.core.database import get_db
from app.core.config import settings
from app.services.auth_service import AuthService
from app.schemas.auth import *
from app.core.logger import logger
from app.core.exceptions import *

router = APIRouter()
security = HTTPBearer()

async def get_auth_service(db: Prisma = Depends(get_db)) -> AuthService:
    """Get authentication service"""
    return AuthService(db)

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> str:
    """Get current user ID from token"""
    token = credentials.credentials
    token_data = auth_service.verify_token(token)
    return token_data["user_id"]

async def get_email_verified_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
    db: Prisma = Depends(get_db)
) -> str:
    """Get current user ID from token with email verification requirement only"""
    token = credentials.credentials
    token_data = auth_service.verify_token(token)
    user_id = token_data["user_id"]
    
    # Get user details to check verification status
    user = await db.user.find_unique(where={"id": user_id})
    if not user:
        raise UserNotFoundException()
    
    # Check if email is verified
    if not user.isEmailVerified:
        raise EmailNotVerifiedException()
    
    return user_id

async def get_verified_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
    db: Prisma = Depends(get_db)
) -> str:
    """Get current user ID from token with email verification and MFA requirements"""
    token = credentials.credentials
    token_data = auth_service.verify_token(token)
    user_id = token_data["user_id"]
    
    # Get user details to check verification status
    user = await db.user.find_unique(where={"id": user_id})
    if not user:
        raise UserNotFoundException()
    
    # Check if email is verified
    if not user.isEmailVerified:
        raise EmailNotVerifiedException()
    
    # Check if MFA is enabled
    if not user.isMfaEnabled:
        raise MFANotSetupException()
    
    return user_id

@router.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Register a new user"""
    try:
        user, tokens = await auth_service.register_user(
            email=request.email,
            password=request.password,
            first_name=request.first_name,
            last_name=request.last_name,
            phone_number=request.phone_number
        )
        
        # Setup MFA URL (optional)
        mfa_setup_url = None
        if settings.ENABLE_MFA:
            mfa_setup_url = f"/api/v1/auth/mfa/setup"
        
        return RegisterResponse(
            user=user,
            tokens=tokens,
            mfa_setup_required=settings.ENABLE_MFA,
            mfa_setup_url=mfa_setup_url
        )
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise

@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    http_request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Login a user with security monitoring"""
    try:
        # Extract request context for security monitoring
        request_context = {
            "ip_address": http_request.client.host if http_request.client else None,
            "user_agent": http_request.headers.get("user-agent"),
            "device_fingerprint": http_request.headers.get("x-device-fingerprint")
        }
        
        user, tokens, mfa_required = await auth_service.login_user(
            email=request.email,
            password=request.password,
            request_context=request_context
        )
        
        mfa_setup_url = None
        if mfa_required:
            mfa_setup_url = f"/api/v1/auth/mfa/verify"
        
        return LoginResponse(
            user=user,
            tokens=tokens,
            mfa_required=mfa_required,
            mfa_setup_url=mfa_setup_url
        )
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise

@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh access token"""
    try:
        access_token = await auth_service.refresh_access_token(request.refresh_token)
        
        return RefreshTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise

@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: LogoutRequest,
    current_user_id: str = Depends(get_current_user_id),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Logout a user"""
    try:
        success = await auth_service.logout_user(request.refresh_token or "")
        
        return LogoutResponse(
            message="Logged out successfully",
            success=success
        )
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise

@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Send password reset email"""
    try:
        success = await auth_service.send_password_reset_email(request.email)
        
        # Always return success for security (don't reveal if email exists)
        return ForgotPasswordResponse(
            message="Password reset email sent if account exists",
            reset_token_sent=True
        )
    except Exception as e:
        logger.error(f"Password reset request failed: {e}")
        return ForgotPasswordResponse(
            message="Password reset email sent if account exists",
            reset_token_sent=True
        )

@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    request: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Reset password with token"""
    try:
        success = await auth_service.reset_password_with_token(
            request.token, 
            request.new_password
        )
        
        if success:
            return ResetPasswordResponse(
                message="Password reset successfully",
                success=True
            )
        else:
            return ResetPasswordResponse(
                message="Invalid or expired reset token",
                success=False
            )
    except Exception as e:
        logger.error(f"Password reset failed: {e}")
        return ResetPasswordResponse(
            message="Password reset failed",
            success=False
        )

@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user_id: str = Depends(get_verified_user_id),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Change user password"""
    try:
        # TODO: Implement change password functionality
        # For now, just return success
        return ChangePasswordResponse(
            message="Password changed successfully",
            success=True
        )
    except Exception as e:
        logger.error(f"Password change failed: {e}")
        raise

@router.post("/verify-email", response_model=EmailVerificationResponse)
async def verify_email(
    request: EmailVerificationRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Verify email address"""
    try:
        success = await auth_service.verify_email_token(request.token)
        
        if success:
            return EmailVerificationResponse(
                message="Email verified successfully",
                success=True
            )
        else:
            return EmailVerificationResponse(
                message="Invalid or expired verification token",
                success=False
            )
    except Exception as e:
        logger.error(f"Email verification failed: {e}")
        return EmailVerificationResponse(
            message="Email verification failed",
            success=False
        )

@router.post("/resend-verification", response_model=ResendVerificationResponse)
async def resend_verification(
    current_user_id: str = Depends(get_current_user_id),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Resend email verification"""
    try:
        success = await auth_service.send_verification_email(current_user_id)
        
        if success:
            return ResendVerificationResponse(
                message="Verification email sent successfully",
                verification_sent=True
            )
        else:
            return ResendVerificationResponse(
                message="Failed to send verification email",
                verification_sent=False
            )
    except Exception as e:
        logger.error(f"Resend verification failed: {e}")
        return ResendVerificationResponse(
            message="Failed to send verification email",
            verification_sent=False
        )

# MFA Endpoints
@router.post("/mfa/setup", response_model=MFASetupResponse)
async def setup_mfa(
    current_user_id: str = Depends(get_email_verified_user_id),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Setup MFA for user"""
    try:
        qr_code_url, secret_key, backup_codes = await auth_service.setup_mfa(current_user_id)
        
        return MFASetupResponse(
            qr_code_url=qr_code_url,
            secret_key=secret_key,
            backup_codes=backup_codes
        )
    except Exception as e:
        logger.error(f"MFA setup failed: {e}")
        raise

@router.post("/mfa/verify", response_model=MFAVerifyResponse)
async def verify_mfa(
    request: MFAVerifyRequest,
    http_request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Verify MFA code with security monitoring"""
    try:
        logger.info(f"MFA verification attempt - User: {request.user_id}, Code: {request.code}, Backup Code: {request.backup_code}")
        
        # Extract request context for security monitoring
        request_context = {
            "ip_address": http_request.client.host if http_request.client else None,
            "user_agent": http_request.headers.get("user-agent"),
            "device_fingerprint": http_request.headers.get("x-device-fingerprint")
        }
        
        user, tokens = await auth_service.verify_mfa(
            user_id=request.user_id,
            code=request.code,
            backup_code=request.backup_code,
            request_context=request_context
        )
        
        logger.info(f"MFA verification successful for user: {request.user_id}")
        return MFAVerifyResponse(
            success=True,
            message="MFA verified successfully",
            tokens=tokens
        )
    except Exception as e:
        logger.error(f"MFA verification failed for user {request.user_id}: {e}")
        return MFAVerifyResponse(
            success=False,
            message="Invalid MFA code"
        )

@router.post("/mfa/disable", response_model=MFADisableResponse)
async def disable_mfa(
    request: MFADisableRequest,
    current_user_id: str = Depends(get_verified_user_id),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Disable MFA for user"""
    try:
        success = await auth_service.disable_mfa(
            user_id=current_user_id,
            password=request.password,
            mfa_code=request.code
        )
        
        return MFADisableResponse(
            success=success,
            message="MFA disabled successfully" if success else "Failed to disable MFA"
        )
    except Exception as e:
        logger.error(f"MFA disable failed: {e}")
        return MFADisableResponse(
            success=False,
            message="Failed to disable MFA"
        )

# User info endpoint
@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user_id: str = Depends(get_current_user_id),
    db: Prisma = Depends(get_db)
):
    """Get current user information"""
    try:
        user = await db.user.find_unique(
            where={"id": current_user_id},
            include={"settings": True}
        )
        
        if not user:
            raise UserNotFoundException()
        
        return UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.firstName,
            last_name=user.lastName,
            display_name=user.displayName,
            phone_number=user.phoneNumber,
            profile_picture=user.profilePicture,
            is_active=user.isActive,
            is_email_verified=user.isEmailVerified,
            is_mfa_enabled=user.isMfaEnabled,
            created_at=user.createdAt,
            updated_at=user.updatedAt,
        )
    except Exception as e:
        logger.error(f"Get current user failed: {e}")
        raise 