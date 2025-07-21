import smtplib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any
from jinja2 import Template
from datetime import datetime
from app.core.config import settings
from app.core.logger import logger

class EmailService:
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.use_tls = settings.SMTP_TLS
        self.from_email = settings.EMAILS_FROM_EMAIL
        self.from_name = settings.EMAILS_FROM_NAME

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send an email"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email

            # Add text part if provided
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                msg.attach(text_part)

            # Add HTML part
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            # Send email
            if not self.smtp_user or not self.smtp_password:
                logger.warning("SMTP credentials not configured. Email not sent.")
                return False

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    # === SECURITY NOTIFICATION METHODS ===

    async def send_login_notification(
        self,
        to_email: str,
        user_name: str,
        login_details: Dict[str, Any]
    ) -> bool:
        """Send successful login notification"""
        subject = "New Login to Your Fortexa Account"
        
        html_template = Template("""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
        .detail-box { background: white; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #28a745; }
        .footer { text-align: center; margin-top: 20px; color: #666; font-size: 12px; }
        .alert { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Fortexa Security</h1>
            <h2>Account Login</h2>
        </div>
        <div class="content">
            <p>Hi {{ user_name }},</p>
            <p>We detected a new login to your Fortexa account:</p>
            
            <div class="detail-box">
                <h3>Login Details</h3>
                <p><strong>Time:</strong> {{ login_time }}</p>
                <p><strong>IP Address:</strong> {{ ip_address }}</p>
                <p><strong>Location:</strong> {{ location }}</p>
                <p><strong>Device:</strong> {{ device }}</p>
                <p><strong>Browser:</strong> {{ browser }}</p>
            </div>
            
            <div class="alert">
                <strong>Security Tip:</strong> If this wasn't you, please change your password immediately and contact our support team.
            </div>
            
            <p>Best regards,<br>The Fortexa Security Team</p>
        </div>
        <div class="footer">
            <p>This is an automated security notification from Fortexa.</p>
        </div>
    </div>
</body>
</html>
        """)
        
        html_content = html_template.render(
            user_name=user_name,
            login_time=login_details.get('time', 'Unknown'),
            ip_address=login_details.get('ip_address', 'Unknown'),
            location=login_details.get('location', 'Unknown'),
            device=login_details.get('device', 'Unknown'),
            browser=login_details.get('browser', 'Unknown')
        )
        
        text_content = f"""
Hi {user_name},

We detected a new login to your Fortexa account:

Login Details:
- Time: {login_details.get('time', 'Unknown')}
- IP Address: {login_details.get('ip_address', 'Unknown')}
- Location: {login_details.get('location', 'Unknown')}
- Device: {login_details.get('device', 'Unknown')}
- Browser: {login_details.get('browser', 'Unknown')}

If this wasn't you, please change your password immediately and contact our support team.

Best regards,
The Fortexa Security Team
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_failed_login_notification(
        self,
        to_email: str,
        user_name: str,
        attempt_details: Dict[str, Any]
    ) -> bool:
        """Send failed login attempt notification"""
        subject = "⚠️ Failed Login Attempt on Your Fortexa Account"
        
        html_template = Template("""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #dc3545 0%, #fd7e14 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
        .detail-box { background: white; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #dc3545; }
        .footer { text-align: center; margin-top: 20px; color: #666; font-size: 12px; }
        .alert { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 15px; border-radius: 5px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚠️ Fortexa Security Alert</h1>
            <h2>Failed Login Attempt</h2>
        </div>
        <div class="content">
            <p>Hi {{ user_name }},</p>
            <p>We detected a failed login attempt on your Fortexa account:</p>
            
            <div class="detail-box">
                <h3>Attempt Details</h3>
                <p><strong>Time:</strong> {{ attempt_time }}</p>
                <p><strong>IP Address:</strong> {{ ip_address }}</p>
                <p><strong>Location:</strong> {{ location }}</p>
                <p><strong>Device:</strong> {{ device }}</p>
                <p><strong>Browser:</strong> {{ browser }}</p>
                <p><strong>Attempt Count:</strong> {{ attempt_count }}</p>
            </div>
            
            <div class="alert">
                <strong>Security Alert:</strong> If this wasn't you, someone may be trying to access your account. Consider changing your password and enabling two-factor authentication.
            </div>
            
            <p>Best regards,<br>The Fortexa Security Team</p>
        </div>
        <div class="footer">
            <p>This is an automated security notification from Fortexa.</p>
        </div>
    </div>
</body>
</html>
        """)
        
        html_content = html_template.render(
            user_name=user_name,
            attempt_time=attempt_details.get('time', 'Unknown'),
            ip_address=attempt_details.get('ip_address', 'Unknown'),
            location=attempt_details.get('location', 'Unknown'),
            device=attempt_details.get('device', 'Unknown'),
            browser=attempt_details.get('browser', 'Unknown'),
            attempt_count=attempt_details.get('attempt_count', 'Unknown')
        )
        
        text_content = f"""
Hi {user_name},

We detected a failed login attempt on your Fortexa account:

Attempt Details:
- Time: {attempt_details.get('time', 'Unknown')}
- IP Address: {attempt_details.get('ip_address', 'Unknown')}
- Location: {attempt_details.get('location', 'Unknown')}
- Device: {attempt_details.get('device', 'Unknown')}
- Browser: {attempt_details.get('browser', 'Unknown')}
- Attempt Count: {attempt_details.get('attempt_count', 'Unknown')}

If this wasn't you, someone may be trying to access your account. Consider changing your password and enabling two-factor authentication.

Best regards,
The Fortexa Security Team
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_password_change_notification(
        self,
        to_email: str,
        user_name: str,
        change_details: Dict[str, Any]
    ) -> bool:
        """Send password change notification"""
        subject = "Password Changed on Your Fortexa Account"
        
        html_template = Template("""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #6f42c1 0%, #e83e8c 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
        .detail-box { background: white; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #6f42c1; }
        .footer { text-align: center; margin-top: 20px; color: #666; font-size: 12px; }
        .alert { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔑 Fortexa Security</h1>
            <h2>Password Changed</h2>
        </div>
        <div class="content">
            <p>Hi {{ user_name }},</p>
            <p>Your password has been successfully changed on your Fortexa account:</p>
            
            <div class="detail-box">
                <h3>Change Details</h3>
                <p><strong>Time:</strong> {{ change_time }}</p>
                <p><strong>IP Address:</strong> {{ ip_address }}</p>
                <p><strong>Location:</strong> {{ location }}</p>
                <p><strong>Device:</strong> {{ device }}</p>
                <p><strong>Browser:</strong> {{ browser }}</p>
            </div>
            
            <div class="alert">
                <strong>Security Note:</strong> If you didn't make this change, please contact our support team immediately.
            </div>
            
            <p>Best regards,<br>The Fortexa Security Team</p>
        </div>
        <div class="footer">
            <p>This is an automated security notification from Fortexa.</p>
        </div>
    </div>
</body>
</html>
        """)
        
        html_content = html_template.render(
            user_name=user_name,
            change_time=change_details.get('time', 'Unknown'),
            ip_address=change_details.get('ip_address', 'Unknown'),
            location=change_details.get('location', 'Unknown'),
            device=change_details.get('device', 'Unknown'),
            browser=change_details.get('browser', 'Unknown')
        )
        
        text_content = f"""
Hi {user_name},

Your password has been successfully changed on your Fortexa account:

Change Details:
- Time: {change_details.get('time', 'Unknown')}
- IP Address: {change_details.get('ip_address', 'Unknown')}
- Location: {change_details.get('location', 'Unknown')}
- Device: {change_details.get('device', 'Unknown')}
- Browser: {change_details.get('browser', 'Unknown')}

If you didn't make this change, please contact our support team immediately.

Best regards,
The Fortexa Security Team
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_mfa_notification(
        self,
        to_email: str,
        user_name: str,
        mfa_event: str,
        event_details: Dict[str, Any]
    ) -> bool:
        """Send MFA-related notifications"""
        event_titles = {
            'enabled': 'Two-Factor Authentication Enabled',
            'disabled': 'Two-Factor Authentication Disabled',
            'backup_used': 'Backup Code Used for Login',
            'failed_attempts': 'Multiple Failed MFA Attempts'
        }
        
        subject = f"🔐 {event_titles.get(mfa_event, 'MFA Event')} - Fortexa"
        
        html_template = Template("""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #007bff 0%, #6610f2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
        .detail-box { background: white; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #007bff; }
        .footer { text-align: center; margin-top: 20px; color: #666; font-size: 12px; }
        .alert { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .warning { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Fortexa Security</h1>
            <h2>{{ event_title }}</h2>
        </div>
        <div class="content">
            <p>Hi {{ user_name }},</p>
            <p>{{ event_description }}</p>
            
            <div class="detail-box">
                <h3>Event Details</h3>
                <p><strong>Time:</strong> {{ event_time }}</p>
                <p><strong>IP Address:</strong> {{ ip_address }}</p>
                <p><strong>Location:</strong> {{ location }}</p>
                <p><strong>Device:</strong> {{ device }}</p>
                <p><strong>Browser:</strong> {{ browser }}</p>
            </div>
            
            {% if event_type == 'enabled' %}
            <div class="alert">
                <strong>Great!</strong> Your account is now more secure with two-factor authentication enabled.
            </div>
            {% elif event_type == 'backup_used' %}
            <div class="warning">
                <strong>Notice:</strong> A backup code was used for login. Consider regenerating new backup codes.
            </div>
            {% elif event_type == 'failed_attempts' %}
            <div class="warning">
                <strong>Security Alert:</strong> Multiple failed MFA attempts detected. Your account may be under attack.
            </div>
            {% endif %}
            
            <p>Best regards,<br>The Fortexa Security Team</p>
        </div>
        <div class="footer">
            <p>This is an automated security notification from Fortexa.</p>
        </div>
    </div>
</body>
</html>
        """)
        
        event_descriptions = {
            'enabled': 'Two-factor authentication has been enabled on your account.',
            'disabled': 'Two-factor authentication has been disabled on your account.',
            'backup_used': 'A backup code was used to authenticate your login.',
            'failed_attempts': 'Multiple failed MFA attempts have been detected on your account.'
        }
        
        html_content = html_template.render(
            user_name=user_name,
            event_title=event_titles.get(mfa_event, 'MFA Event'),
            event_description=event_descriptions.get(mfa_event, 'An MFA event occurred on your account.'),
            event_type=mfa_event,
            event_time=event_details.get('time', 'Unknown'),
            ip_address=event_details.get('ip_address', 'Unknown'),
            location=event_details.get('location', 'Unknown'),
            device=event_details.get('device', 'Unknown'),
            browser=event_details.get('browser', 'Unknown')
        )
        
        text_content = f"""
Hi {user_name},

{event_descriptions.get(mfa_event, 'An MFA event occurred on your account.')}

Event Details:
- Time: {event_details.get('time', 'Unknown')}
- IP Address: {event_details.get('ip_address', 'Unknown')}
- Location: {event_details.get('location', 'Unknown')}
- Device: {event_details.get('device', 'Unknown')}
- Browser: {event_details.get('browser', 'Unknown')}

Best regards,
The Fortexa Security Team
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_security_alert(
        self,
        to_email: str,
        user_name: str,
        alert_type: str,
        alert_details: Dict[str, Any]
    ) -> bool:
        """Send security alert notifications"""
        alert_titles = {
            'suspicious_activity': 'Suspicious Activity Detected',
            'account_locked': 'Account Temporarily Locked',
            'new_device': 'New Device Login',
            'location_change': 'Login from New Location',
            'high_risk_login': 'High Risk Login Detected'
        }
        
        subject = f"🚨 Security Alert: {alert_titles.get(alert_type, 'Security Event')} - Fortexa"
        
        html_template = Template("""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #dc3545 0%, #fd7e14 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
        .detail-box { background: white; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #dc3545; }
        .footer { text-align: center; margin-top: 20px; color: #666; font-size: 12px; }
        .alert { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .button { display: inline-block; background: #dc3545; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 Fortexa Security Alert</h1>
            <h2>{{ alert_title }}</h2>
        </div>
        <div class="content">
            <p>Hi {{ user_name }},</p>
            <p>{{ alert_description }}</p>
            
            <div class="detail-box">
                <h3>Alert Details</h3>
                <p><strong>Time:</strong> {{ alert_time }}</p>
                <p><strong>IP Address:</strong> {{ ip_address }}</p>
                <p><strong>Location:</strong> {{ location }}</p>
                <p><strong>Device:</strong> {{ device }}</p>
                <p><strong>Browser:</strong> {{ browser }}</p>
                <p><strong>Risk Score:</strong> {{ risk_score }}</p>
            </div>
            
            <div class="alert">
                <strong>Immediate Action Required:</strong> Please review this activity and secure your account if necessary.
            </div>
            
            <p style="text-align: center;">
                <a href="{{ security_url }}" class="button">Review Security Settings</a>
            </p>
            
            <p>Best regards,<br>The Fortexa Security Team</p>
        </div>
        <div class="footer">
            <p>This is an automated security notification from Fortexa.</p>
        </div>
    </div>
</body>
</html>
        """)
        
        alert_descriptions = {
            'suspicious_activity': 'Suspicious activity has been detected on your account.',
            'account_locked': 'Your account has been temporarily locked due to security concerns.',
            'new_device': 'A login was detected from a new device.',
            'location_change': 'A login was detected from a new geographical location.',
            'high_risk_login': 'A high-risk login attempt was detected on your account.'
        }
        
        html_content = html_template.render(
            user_name=user_name,
            alert_title=alert_titles.get(alert_type, 'Security Event'),
            alert_description=alert_descriptions.get(alert_type, 'A security event occurred on your account.'),
            alert_time=alert_details.get('time', 'Unknown'),
            ip_address=alert_details.get('ip_address', 'Unknown'),
            location=alert_details.get('location', 'Unknown'),
            device=alert_details.get('device', 'Unknown'),
            browser=alert_details.get('browser', 'Unknown'),
            risk_score=alert_details.get('risk_score', 'Unknown'),
            security_url=f"{settings.FRONTEND_URL}/security"
        )
        
        text_content = f"""
Hi {user_name},

{alert_descriptions.get(alert_type, 'A security event occurred on your account.')}

Alert Details:
- Time: {alert_details.get('time', 'Unknown')}
- IP Address: {alert_details.get('ip_address', 'Unknown')}
- Location: {alert_details.get('location', 'Unknown')}
- Device: {alert_details.get('device', 'Unknown')}
- Browser: {alert_details.get('browser', 'Unknown')}
- Risk Score: {alert_details.get('risk_score', 'Unknown')}

Immediate Action Required: Please review this activity and secure your account if necessary.

Review your security settings: {settings.FRONTEND_URL}/security

Best regards,
The Fortexa Security Team
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)

    # === EXISTING METHODS ===
    
    async def send_verification_email(
        self,
        to_email: str,
        user_name: str,
        verification_token: str
    ) -> bool:
        """Send email verification email"""
        verification_url = f"{settings.FRONTEND_URL}/auth/verify-email?token={verification_token}"
        
        subject = "Verify Your Fortexa Account"
        
        html_template = Template("""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
        .button { display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .footer { text-align: center; margin-top: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>₿ Fortexa</h1>
            <h2>Welcome to Fortexa!</h2>
        </div>
        <div class="content">
            <p>Hi {{ user_name }},</p>
            <p>Thank you for signing up for Fortexa! To complete your registration and secure your account, please verify your email address by clicking the button below:</p>
            <p style="text-align: center;">
                <a href="{{ verification_url }}" class="button">Verify Email Address</a>
            </p>
            <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #667eea;">{{ verification_url }}</p>
            <p><strong>This verification link will expire in 24 hours.</strong></p>
            <p>If you didn't create an account with Fortexa, you can safely ignore this email.</p>
            <p>Best regards,<br>The Fortexa Team</p>
        </div>
        <div class="footer">
            <p>This email was sent from Fortexa. Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>
        """)
        
        html_content = html_template.render(
            user_name=user_name,
            verification_url=verification_url
        )
        
        text_content = f"""
Hi {user_name},

Welcome to Fortexa! Please verify your email address by visiting this link:
{verification_url}

This verification link will expire in 24 hours.

If you didn't create an account with Fortexa, you can safely ignore this email.

Best regards,
The Fortexa Team
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)

    async def send_password_reset_email(
        self,
        to_email: str,
        user_name: str,
        reset_token: str
    ) -> bool:
        """Send password reset email"""
        reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={reset_token}"
        
        subject = "Reset Your Fortexa Password"
        
        html_template = Template("""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
        .button { display: inline-block; background: #e74c3c; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .footer { text-align: center; margin-top: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>₿ Fortexa</h1>
            <h2>Password Reset Request</h2>
        </div>
        <div class="content">
            <p>Hi {{ user_name }},</p>
            <p>We received a request to reset your Fortexa account password. Click the button below to reset your password:</p>
            <p style="text-align: center;">
                <a href="{{ reset_url }}" class="button">Reset Password</a>
            </p>
            <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #667eea;">{{ reset_url }}</p>
            <p><strong>This reset link will expire in 1 hour.</strong></p>
            <p>If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.</p>
            <p>Best regards,<br>The Fortexa Team</p>
        </div>
        <div class="footer">
            <p>This email was sent from Fortexa. Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>
        """)
        
        html_content = html_template.render(
            user_name=user_name,
            reset_url=reset_url
        )
        
        text_content = f"""
Hi {user_name},

We received a request to reset your Fortexa account password. Please visit this link to reset your password:
{reset_url}

This reset link will expire in 1 hour.

If you didn't request a password reset, you can safely ignore this email.

Best regards,
The Fortexa Team
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)

    def generate_verification_token(self) -> str:
        """Generate email verification token"""
        return secrets.token_urlsafe(32)

    def generate_reset_token(self) -> str:
        """Generate password reset token"""
        return secrets.token_urlsafe(32) 