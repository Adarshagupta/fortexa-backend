import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
import pyotp
import qrcode
from io import BytesIO
import base64
from prisma import Prisma
from app.core.config import settings
from app.core.exceptions import *
from app.core.logger import logger
from app.schemas.auth import UserResponse, Token
from app.services.email_service import EmailService
from app.services.security_service import SecurityService, SecurityContext

class AuthService:
    def __init__(self, db: Prisma):
        self.db = db
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_minutes = settings.REFRESH_TOKEN_EXPIRE_MINUTES
        self.security_service = SecurityService(db)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return self.pwd_context.hash(password)
    
    def validate_password_strength(self, password: str) -> bool:
        """Validate password strength based on settings"""
        if len(password) < settings.MIN_PASSWORD_LENGTH:
            return False
        
        if settings.REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
            return False
        
        if settings.REQUIRE_LOWERCASE and not any(c.islower() for c in password):
            return False
        
        if settings.REQUIRE_NUMBERS and not any(c.isdigit() for c in password):
            return False
        
        if settings.REQUIRE_SPECIAL_CHARS and not any(c in '!@#$%^&*(),.?":{}|<>' for c in password):
            return False
        
        return True
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def create_refresh_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create refresh token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.refresh_token_expire_minutes)
        
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> dict:
        """Verify and decode token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("sub")
            token_type: str = payload.get("type")
            
            if user_id is None:
                raise InvalidTokenException()
            
            return {"user_id": user_id, "type": token_type}
        except JWTError:
            raise InvalidTokenException()
    
    async def register_user(self, email: str, password: str, first_name: str, 
                           last_name: str, phone_number: Optional[str] = None) -> Tuple[UserResponse, Token]:
        """Register a new user"""
        # Check if user already exists
        existing_user = await self.db.user.find_unique(where={"email": email})
        if existing_user:
            raise UserAlreadyExistsException()
        
        # Validate password strength
        if not self.validate_password_strength(password):
            raise WeakPasswordException("Password does not meet security requirements")
        
        # Hash password
        hashed_password = self.get_password_hash(password)
        
        # Create user
        user = await self.db.user.create(
            data={
                "email": email,
                "password": hashed_password,
                "firstName": first_name,
                "lastName": last_name,
                "displayName": f"{first_name} {last_name}",
                "phoneNumber": phone_number,
                "isActive": True,
                "isEmailVerified": False,
                "isMfaEnabled": False,
                "emailVerificationToken": secrets.token_urlsafe(32),
                "emailVerificationTokenExpiry": datetime.now(timezone.utc) + timedelta(hours=24),
            }
        )
        
        # Create user portfolio
        await self.db.portfolio.create(
            data={
                "userId": user.id,
                "name": "My Portfolio",
                "totalValue": 0.0,
                "totalCost": 0.0,
                "totalGainLoss": 0.0,
                "totalGainLossPercent": 0.0,
            }
        )
        
        # Create user settings
        await self.db.usersettings.create(
            data={
                "userId": user.id,
                "theme": "dark",
                "currency": "USD",
                "language": "en",
                "timezone": "UTC",
            }
        )
        
        # Create tokens
        tokens = await self._create_user_tokens(user.id)
        
        # Send verification email automatically
        try:
            email_service = EmailService()
            await email_service.send_verification_email(
                to_email=user.email,
                user_name=user.firstName or user.email,
                verification_token=user.emailVerificationToken
            )
            logger.info(f"Verification email sent to {user.email} during registration")
        except Exception as e:
            logger.warning(f"Failed to send verification email during registration: {e}")
            # Don't fail registration if email sending fails
        
        # Convert to response schema
        user_response = UserResponse(
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
        
        logger.info(f"User registered successfully: {email}")
        return user_response, tokens
    
    async def login_user(self, email: str, password: str, request_context: Dict[str, Any]) -> Tuple[UserResponse, Token, bool]:
        """Login a user with comprehensive security monitoring"""
        # Create security context
        context = await self.security_service.create_security_context({
            "email": email,
            "ip_address": request_context.get("ip_address"),
            "user_agent": request_context.get("user_agent"),
            "device_fingerprint": request_context.get("device_fingerprint")
        })
        
        # Find user FIRST - this is critical for proper error messaging
        user = await self.db.user.find_unique(where={"email": email})
        
        # If user doesn't exist, return invalid credentials immediately
        # This prevents security analysis from overriding the "invalid credentials" message
        if not user:
            await self.security_service.log_login_attempt(context, False, "User not found")
            await self.security_service.log_security_event(
                "LOGIN_FAILED", None, "LOW",
                f"Login attempt for non-existent user: {email}", context.ip_address
            )
            raise InvalidCredentialsException()
        
        # User exists, set user_id for security analysis
        context.user_id = user.id
        
        # Check if account is locked
        if await self.security_service.is_account_locked(user.id):
            await self.security_service.log_login_attempt(context, False, "Account locked")
            raise AuthenticationException("Account is temporarily locked due to security concerns")
        
        # Verify password FIRST (before security analysis)
        # This ensures we can authenticate users even if they haven't completed onboarding
        if not self.verify_password(password, user.password):
            await self.security_service.log_login_attempt(context, False, "Invalid password")
            
            # Update failed login attempts
            updated_user = await self.db.user.update(
                where={"id": user.id},
                data={"failedLoginAttempts": {"increment": 1}}
            )
            
            # Send failed login notification email
            user_name = user.firstName or user.email
            await self.security_service.send_failed_login_notification(
                context, user_name, updated_user.failedLoginAttempts
            )
            
            # Lock account if too many failed attempts
            if updated_user.failedLoginAttempts >= 5:
                await self.security_service.lock_user_account(user.id, 24)
                await self.security_service.send_security_alert_notification(
                    context, user_name, "account_locked", analysis
                )
            
            raise InvalidCredentialsException()
        
        # Check if user is active
        if not user.isActive:
            await self.security_service.log_login_attempt(context, False, "Account deactivated")
            raise AuthenticationException("Account is deactivated")
        
        # Now analyze login attempt for security threats (after password verification)
        analysis = await self.security_service.analyze_login_attempt(context)
        
        # Add detailed logging for debugging
        logger.info(f"Security analysis for {email}: risk_score={analysis.risk_score}, threats={analysis.threats}")
        
        # For very high risk logins, still block them even with valid credentials
        # In development mode, be extremely permissive
        block_threshold = 15.0 if settings.DEBUG else 9.5
        
        if analysis.risk_score > block_threshold:
            await self.security_service.log_login_attempt(context, False, analysis.block_reason)
            
            # Log security event
            await self.security_service.log_security_event(
                "LOGIN_BLOCKED", user.id, "HIGH", 
                f"Login blocked: {analysis.block_reason}", context.ip_address,
                {"threats": analysis.threats, "risk_score": analysis.risk_score}
            )
            
            # Add more detailed error message
            raise AuthenticationException(f"Login blocked due to security concerns: {analysis.block_reason}. Threats detected: {', '.join(analysis.threats)}")
        
        # Update security context with successful authentication
        context.risk_score = analysis.risk_score
        context.is_suspicious = analysis.risk_score > 5.0
        
        # Check if email is verified or MFA is enabled
        # Allow login with valid credentials but require onboarding completion for full access
        if not user.isEmailVerified or not user.isMfaEnabled:
            # Log partial login success (onboarding required)
            await self.security_service.log_login_attempt(context, True, "Login successful - onboarding required")
            
            # Create basic access tokens for onboarding
            tokens = await self._create_user_tokens(user.id)
            
            # Return user response with current verification status
            user_response = UserResponse(
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
            
            logger.info(f"User logged in successfully but needs onboarding: {email}")
            return user_response, tokens, False
        
        # If MFA is enabled and email is verified, check for MFA requirement
        if user.isMfaEnabled:
            # Log partial login success (MFA pending)
            await self.security_service.log_login_attempt(context, False, "MFA required")
            
            # Return partial response requiring MFA
            user_response = UserResponse(
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
            
            # Create temporary token for MFA verification
            temp_token = Token(
                access_token="",
                refresh_token="",
                token_type="bearer",
                expires_in=0
            )
            
            return user_response, temp_token, True
        
        # Complete login process
        await self._complete_login(user, context, analysis)
        
        # Create tokens
        tokens = await self._create_user_tokens(user.id)
        
        # Convert to response schema
        user_response = UserResponse(
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
        
        logger.info(f"User logged in successfully: {email}")
        return user_response, tokens, False
    
    async def _complete_login(self, user, context: SecurityContext, analysis):
        """Complete the login process with security updates"""
        # Update last login information
        await self.db.user.update(
            where={"id": user.id},
            data={
                "lastLoginAt": datetime.now(timezone.utc),
                "lastLoginIp": context.ip_address,
                "failedLoginAttempts": 0,  # Reset failed attempts on successful login
                "riskScore": analysis.risk_score
            }
        )
        
        # Log successful login attempt
        await self.security_service.log_login_attempt(context, True)
        
        # Log security event for successful login
        await self.security_service.log_security_event(
            "LOGIN_SUCCESS", user.id, "LOW" if analysis.risk_score < 3.0 else "MEDIUM",
            f"User logged in successfully", context.ip_address,
            {"risk_score": analysis.risk_score, "threats": analysis.threats}
        )
        
        # Send login notification email
        user_name = user.firstName or user.email
        await self.security_service.send_login_notification(context, user_name)
        
        # Handle security actions if any
        if "REQUIRE_MFA" in analysis.required_actions:
            await self.security_service.log_security_event(
                "MFA_REQUIRED", user.id, "MEDIUM",
                "MFA required due to security analysis", context.ip_address
            )
        
        # Send security alert for high-risk logins
        if analysis.risk_score > 5.0:
            await self.security_service.send_security_alert_notification(
                context, user_name, "high_risk_login", analysis
            )
        
        # Update user's overall risk score
        await self.security_service.update_user_risk_score(user.id, analysis.risk_score)
    
    async def refresh_access_token(self, refresh_token: str) -> str:
        """Refresh access token"""
        try:
            payload = self.verify_token(refresh_token)
            
            if payload["type"] != "refresh":
                raise InvalidTokenException()
            
            user_id = payload["user_id"]
            
            # Verify session exists
            session = await self.db.usersession.find_first(
                where={"refreshToken": refresh_token, "isActive": True}
            )
            
            if not session:
                raise InvalidTokenException()
            
            # Create new access token
            access_token = self.create_access_token({"sub": user_id})
            
            return access_token
        except JWTError:
            raise InvalidTokenException()
    
    async def logout_user(self, refresh_token: str) -> bool:
        """Logout a user"""
        try:
            # Deactivate session
            await self.db.usersession.update_many(
                where={"refreshToken": refresh_token},
                data={"isActive": False}
            )
            
            return True
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False
    
    async def setup_mfa(self, user_id: str) -> Tuple[str, str, list[str]]:
        """Setup MFA for user"""
        user = await self.db.user.find_unique(where={"id": user_id})
        if not user:
            raise UserNotFoundException()
        
        # Generate secret
        secret = pyotp.random_base32()
        
        # Generate backup codes
        backup_codes = [secrets.token_hex(4) for _ in range(8)]
        
        # Save MFA secret
        await self.db.user.update(
            where={"id": user_id},
            data={
                "mfaSecret": secret,
                "mfaBackupCodes": backup_codes,
                "isMfaEnabled": True,
            }
        )
        
        # Send MFA enabled notification
        from app.services.security_service import SecurityContext
        context = SecurityContext(
            user_id=user_id,
            email=user.email,
            ip_address=None,
            user_agent=None
        )
        user_name = user.firstName or user.email
        await self.security_service.send_mfa_event_notification(context, user_name, 'enabled')
        
        # Generate QR code
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=settings.MFA_ISSUER
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        qr_code_url = f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"
        
        logger.info(f"MFA setup completed for user: {user.email}")
        return qr_code_url, secret, backup_codes
    
    async def verify_mfa(self, user_id: str, code: str, backup_code: Optional[str] = None, 
                        request_context: Optional[Dict[str, Any]] = None) -> Tuple[UserResponse, Token]:
        """Verify MFA code with security monitoring"""
        user = await self.db.user.find_unique(where={"id": user_id})
        if not user:
            logger.error(f"User not found: {user_id}")
            raise UserNotFoundException()
        
        if not user.isMfaEnabled or not user.mfaSecret:
            logger.error(f"MFA not enabled or no secret for user: {user_id}")
            raise InvalidMFACodeException()
        
        # Create security context for MFA verification
        context = None
        if request_context:
            context = await self.security_service.create_security_context({
                "user_id": user_id,
                "email": user.email,
                "ip_address": request_context.get("ip_address"),
                "user_agent": request_context.get("user_agent"),
                "device_fingerprint": request_context.get("device_fingerprint")
            })
        
        # Verify backup code first
        if backup_code:
            logger.info(f"Verifying backup code: {backup_code}")
            logger.info(f"User's backup codes: {user.mfaBackupCodes}")
            
            # Check both upper and lower case versions
            backup_code_upper = backup_code.upper()
            backup_code_lower = backup_code.lower()
            
            if backup_code in user.mfaBackupCodes or backup_code_upper in user.mfaBackupCodes or backup_code_lower in user.mfaBackupCodes:
                # Find the actual backup code to remove (preserving original case)
                code_to_remove = backup_code
                if backup_code_upper in user.mfaBackupCodes:
                    code_to_remove = backup_code_upper
                elif backup_code_lower in user.mfaBackupCodes:
                    code_to_remove = backup_code_lower
                
                # Remove used backup code
                updated_codes = [c for c in user.mfaBackupCodes if c != code_to_remove]
                await self.db.user.update(
                    where={"id": user_id},
                    data={"mfaBackupCodes": updated_codes}
                )
                logger.info(f"Backup code verified and removed: {code_to_remove}")
                
                # Log security event for backup code usage
                if context:
                    await self.security_service.log_security_event(
                        "MFA_BACKUP_CODE_USED", user_id, "MEDIUM",
                        f"Backup code used for MFA verification", context.ip_address,
                        {"backup_code_used": code_to_remove[:4] + "****"}
                    )
            else:
                logger.error(f"Invalid backup code: {backup_code}")
                
                # Log failed MFA attempt
                if context:
                    await self.security_service.log_security_event(
                        "MFA_FAILED", user_id, "HIGH",
                        f"Invalid backup code provided", context.ip_address,
                        {"method": "backup_code"}
                    )
                
                raise InvalidMFACodeException()
        else:
            # Verify TOTP code
            logger.info(f"Verifying TOTP code: {code}")
            totp = pyotp.TOTP(user.mfaSecret)
            if not totp.verify(code, valid_window=settings.MFA_WINDOW):
                logger.error(f"Invalid TOTP code: {code}")
                
                # Log failed MFA attempt
                if context:
                    await self.security_service.log_security_event(
                        "MFA_FAILED", user_id, "HIGH",
                        f"Invalid TOTP code provided", context.ip_address,
                        {"method": "totp"}
                    )
                
                raise InvalidMFACodeException()
        
        # Update last login and security info
        await self.db.user.update(
            where={"id": user_id},
            data={
                "lastLoginAt": datetime.now(timezone.utc),
                "lastLoginIp": context.ip_address if context else None,
                "failedLoginAttempts": 0
            }
        )
        
        # Log successful MFA verification
        if context:
            await self.security_service.log_login_attempt(context, True)
            await self.security_service.log_security_event(
                "MFA_SUCCESS", user_id, "LOW",
                f"MFA verification successful", context.ip_address,
                {"method": "backup_code" if backup_code else "totp"}
            )
            
            # Send MFA verification notification
            user_name = user.firstName or user.email
            if backup_code:
                await self.security_service.send_mfa_event_notification(
                    context, user_name, 'backup_used'
                )
            else:
                await self.security_service.send_login_notification(context, user_name)
        
        # Create tokens
        tokens = await self._create_user_tokens(user_id)
        
        # Convert to response schema
        user_response = UserResponse(
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
        
        logger.info(f"MFA verified for user: {user.email}")
        return user_response, tokens
    
    async def disable_mfa(self, user_id: str, password: str, mfa_code: str) -> bool:
        """Disable MFA for user"""
        user = await self.db.user.find_unique(where={"id": user_id})
        if not user:
            raise UserNotFoundException()
        
        # Verify password
        if not self.verify_password(password, user.password):
            raise InvalidCredentialsException()
        
        # Verify MFA code
        if not user.mfaSecret:
            raise InvalidMFACodeException()
        
        totp = pyotp.TOTP(user.mfaSecret)
        if not totp.verify(mfa_code, valid_window=settings.MFA_WINDOW):
            raise InvalidMFACodeException()
        
        # Disable MFA
        await self.db.user.update(
            where={"id": user_id},
            data={
                "isMfaEnabled": False,
                "mfaSecret": None,
                "mfaBackupCodes": [],
            }
        )
        
        logger.info(f"MFA disabled for user: {user.email}")
        return True
    
    async def _create_user_tokens(self, user_id: str) -> Token:
        """Create access and refresh tokens for user"""
        # Create tokens
        access_token = self.create_access_token({"sub": user_id})
        refresh_token = self.create_refresh_token({"sub": user_id})
        
        # Save session
        await self.db.usersession.create(
            data={
                "userId": user_id,
                "refreshToken": refresh_token,
                "accessToken": access_token,
                "isActive": True,
                "expiresAt": datetime.now(timezone.utc) + timedelta(minutes=self.refresh_token_expire_minutes),
            }
        )
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self.access_token_expire_minutes * 60
        )

    async def send_verification_email(self, user_id: str) -> bool:
        """Send email verification email to user"""
        try:
            user = await self.db.user.find_unique(where={"id": user_id})
            if not user:
                raise UserNotFoundException()
            
            if user.isEmailVerified:
                logger.info(f"User {user.email} already verified")
                return True
            
            # Generate verification token
            email_service = EmailService()
            verification_token = email_service.generate_verification_token()
            
            # Update user with verification token and expiry
            await self.db.user.update(
                where={"id": user_id},
                data={
                    "emailVerificationToken": verification_token,
                    "emailVerificationTokenExpiry": datetime.now(timezone.utc) + timedelta(hours=24)
                }
            )
            
            # Send verification email
            success = await email_service.send_verification_email(
                to_email=user.email,
                user_name=user.firstName or user.email,
                verification_token=verification_token
            )
            
            if success:
                logger.info(f"Verification email sent to {user.email}")
            else:
                logger.error(f"Failed to send verification email to {user.email}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending verification email: {e}")
            return False

    async def verify_email_token(self, token: str) -> bool:
        """Verify email with token"""
        try:
            user = await self.db.user.find_first(
                where={"emailVerificationToken": token}
            )
            
            if not user:
                logger.warning(f"Invalid verification token: {token}")
                return False
            
            # Check if token expired
            if user.emailVerificationTokenExpiry and user.emailVerificationTokenExpiry < datetime.now(timezone.utc):
                logger.warning(f"Verification token expired for user: {user.email}")
                return False
            
            # Mark email as verified
            await self.db.user.update(
                where={"id": user.id},
                data={
                    "isEmailVerified": True,
                    "emailVerificationToken": None,
                    "emailVerificationTokenExpiry": None,
                    "updatedAt": datetime.now(timezone.utc)
                }
            )
            
            logger.info(f"Email verified successfully for user: {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying email token: {e}")
            return False

    async def send_password_reset_email(self, email: str) -> bool:
        """Send password reset email"""
        try:
            user = await self.db.user.find_unique(where={"email": email})
            if not user:
                # For security, don't reveal if email exists
                logger.info(f"Password reset requested for non-existent email: {email}")
                return True
            
            # Generate reset token
            email_service = EmailService()
            reset_token = email_service.generate_reset_token()
            
            # Update user with reset token and expiry
            await self.db.user.update(
                where={"id": user.id},
                data={
                    "passwordResetToken": reset_token,
                    "passwordResetTokenExpiry": datetime.now(timezone.utc) + timedelta(hours=1)
                }
            )
            
            # Send reset email
            success = await email_service.send_password_reset_email(
                to_email=user.email,
                user_name=user.firstName or user.email,
                reset_token=reset_token
            )
            
            if success:
                logger.info(f"Password reset email sent to {user.email}")
            else:
                logger.error(f"Failed to send password reset email to {user.email}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending password reset email: {e}")
            return False

    async def reset_password_with_token(self, token: str, new_password: str) -> bool:
        """Reset password with token"""
        try:
            user = await self.db.user.find_first(
                where={"passwordResetToken": token}
            )
            
            if not user:
                logger.warning(f"Invalid password reset token: {token}")
                return False
            
            # Check if token expired
            if user.passwordResetTokenExpiry and user.passwordResetTokenExpiry < datetime.now(timezone.utc):
                logger.warning(f"Password reset token expired for user: {user.email}")
                return False
            
            # Validate new password
            if not self.validate_password_strength(new_password):
                raise WeakPasswordException("New password does not meet security requirements")
            
            # Hash new password
            hashed_password = self.get_password_hash(new_password)
            
            # Update password and clear reset token
            await self.db.user.update(
                where={"id": user.id},
                data={
                    "password": hashed_password,
                    "passwordResetToken": None,
                    "passwordResetTokenExpiry": None,
                    "updatedAt": datetime.now(timezone.utc)
                }
            )
            
            # Invalidate all sessions for security
            await self.db.usersession.update_many(
                where={"userId": user.id},
                data={"isActive": False}
            )
            
            # Send password change notification
            from app.services.security_service import SecurityContext
            context = SecurityContext(
                user_id=user.id,
                email=user.email,
                ip_address=None,
                user_agent=None
            )
            user_name = user.firstName or user.email
            await self.security_service.send_password_change_notification(context, user_name)
            
            logger.info(f"Password reset successfully for user: {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            return False 