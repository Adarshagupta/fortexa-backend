# Fortexa Backend

A comprehensive cryptocurrency trading platform backend built with FastAPI, featuring advanced security monitoring, real-time market data, and AI-powered trading signals.

## Features

- **User Authentication & Security**
  - JWT-based authentication
  - Two-factor authentication (2FA)
  - Advanced security monitoring
  - Real-time threat detection
  - Email security notifications

- **Security Email Notifications**
  - Login notifications
  - Failed login attempt alerts
  - Password change notifications
  - MFA event notifications
  - Security alerts for suspicious activity

- **Portfolio Management**
  - Real-time portfolio tracking
  - Performance analytics
  - Asset allocation insights

- **Market Data**
  - Real-time cryptocurrency prices
  - Market analytics and trends
  - News aggregation

- **AI Trading Signals**
  - ML-powered trading recommendations
  - Risk assessment algorithms
  - Market sentiment analysis

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL
- Redis
- Node.js (for Prisma)

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   cp environment.example .env
   ```

4. Configure your database and external services in `.env`

5. Run database migrations:
   ```bash
   python -m prisma migrate dev
   ```

6. Start the server:
   ```bash
   python main.py
   ```

## 📧 Email Configuration

### SMTP Setup

The system supports comprehensive email notifications for security events. Configure your SMTP settings in the `.env` file:

```env
# Email Configuration
SMTP_TLS=true
SMTP_PORT=587
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAILS_FROM_EMAIL=noreply@fortexa.com
EMAILS_FROM_NAME=Fortexa
```

### Supported Email Providers

#### Gmail
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_TLS=true
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

#### Outlook/Hotmail
```env
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_TLS=true
SMTP_USER=your-email@outlook.com
SMTP_PASSWORD=your-password
```

#### AWS SES
```env
SMTP_HOST=email-smtp.us-west-2.amazonaws.com
SMTP_PORT=587
SMTP_TLS=true
SMTP_USER=your-ses-access-key
SMTP_PASSWORD=your-ses-secret-key
```

#### SendGrid
```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_TLS=true
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
```

#### Brevo (Sendinblue)
```env
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_TLS=true
SMTP_USER=your-brevo-email
SMTP_PASSWORD=your-brevo-smtp-key
```

### Email Notification Types

#### 1. Login Notifications
- **Trigger**: Every successful login
- **Content**: Login time, IP address, location, device, browser
- **Purpose**: Keep users informed of account access

#### 2. Failed Login Alerts
- **Trigger**: Failed login attempts
- **Content**: Attempt time, IP address, location, attempt count
- **Purpose**: Alert users to potential unauthorized access attempts

#### 3. Password Change Notifications
- **Trigger**: Password changes via reset or settings
- **Content**: Change time, IP address, location, device
- **Purpose**: Confirm legitimate password changes

#### 4. MFA Event Notifications
- **Trigger**: MFA enable/disable, backup code usage
- **Content**: Event time, IP address, location, device
- **Purpose**: Track MFA-related security events

#### 5. Security Alerts
- **Trigger**: High-risk activities, account lockouts, suspicious behavior
- **Content**: Alert details, risk score, recommended actions
- **Purpose**: Immediate notification of security threats

### Email Templates

All email templates are professionally designed with:
- Responsive HTML design
- Dark theme matching the application
- Clear call-to-action buttons
- Fallback text versions
- Security-focused messaging

### Testing Email Configuration

Test your email configuration with:

```bash
# Test basic email functionality
python -c "
import asyncio
from app.services.email_service import EmailService

async def test_email():
    service = EmailService()
    success = await service.send_email(
        'test@example.com',
        'Test Email',
        '<h1>Test Email</h1><p>If you receive this, SMTP is working!</p>',
        'Test Email - If you receive this, SMTP is working!'
    )
    print(f'Email sent: {success}')

asyncio.run(test_email())
"
```

### Security Best Practices

1. **Use App Passwords**: For Gmail, use app-specific passwords instead of your regular password
2. **Enable TLS**: Always use TLS encryption for email transmission
3. **Monitor Bounce Rates**: Track email delivery success rates
4. **Rate Limiting**: Implement rate limiting to prevent email spam
5. **Authentication**: Use proper SMTP authentication

### Troubleshooting

#### Common Issues

1. **Gmail "Less Secure Apps" Error**
   - Enable 2FA on your Google account
   - Generate an app-specific password
   - Use the app password instead of your regular password

2. **Connection Timeout**
   - Check firewall settings
   - Verify SMTP port is correct
   - Ensure TLS settings match your provider

3. **Authentication Failed**
   - Verify username and password
   - Check if your email provider requires app passwords
   - Ensure account is not locked

4. **Emails Not Delivering**
   - Check spam folders
   - Verify email addresses are correct
   - Monitor server logs for errors

### Email Logs

All email activities are logged for debugging:

```bash
# View email logs
tail -f logs/fortexa.log | grep -i email
```

### Performance Optimization

- Email sending is asynchronous to prevent blocking
- Failed email attempts are retried automatically
- Email templates are cached for performance
- SMTP connections are pooled for efficiency

## 🔐 Security Features

### Real-Time Security Monitoring

- **IP Reputation Checking**: Validates IP addresses against threat intelligence databases
- **Geolocation Tracking**: Monitors login locations and detects impossible travel
- **Device Fingerprinting**: Tracks trusted devices and detects new device logins
- **Behavioral Analysis**: Learns user patterns and flags anomalous activity
- **Rate Limiting**: Prevents brute force attacks with intelligent rate limiting

### Threat Detection

- **VPN/Proxy Detection**: Identifies connections through anonymization services
- **Tor Network Detection**: Flags connections from Tor exit nodes
- **Malicious IP Detection**: Checks against multiple threat intelligence feeds
- **Suspicious User Agents**: Identifies potentially malicious client signatures

### Automated Response

- **Account Locking**: Temporarily locks accounts showing suspicious activity
- **Email Alerts**: Sends immediate notifications for security events
- **Risk Scoring**: Assigns dynamic risk scores to login attempts
- **Session Management**: Automatically manages and invalidates suspicious sessions

## 🛠️ API Documentation

### Authentication Endpoints

- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/mfa/setup` - Setup two-factor authentication
- `POST /api/v1/auth/mfa/verify` - Verify MFA code
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - User logout

### Security Endpoints

- `GET /api/v1/security/events` - Get security events
- `GET /api/v1/security/login-attempts` - Get login attempts
- `GET /api/v1/security/ip-stats` - Get IP address statistics
- `POST /api/v1/security/blacklist-ip` - Blacklist IP address
- `POST /api/v1/security/unlock-account` - Unlock user account

### Portfolio Endpoints

- `GET /api/v1/portfolio` - Get user portfolio
- `POST /api/v1/portfolio` - Create portfolio
- `PUT /api/v1/portfolio/{id}` - Update portfolio
- `DELETE /api/v1/portfolio/{id}` - Delete portfolio

## 📊 Database Schema

The application uses PostgreSQL with Prisma ORM. Key models include:

- **User**: User accounts with security fields
- **SecurityEvent**: Security monitoring events
- **LoginAttempt**: Login attempt tracking
- **IpAddress**: IP address reputation and geolocation
- **TrustedDevice**: Device fingerprinting
- **Portfolio**: User investment portfolios
- **Asset**: Cryptocurrency asset information

## 🚀 Production Deployment

### Docker Deployment

```bash
# Build and run with Docker
docker-compose up -d
```

### Environment Variables

Ensure all required environment variables are set:

- Database connection strings
- SMTP credentials
- API keys for external services
- Security configuration
- Redis connection details

### Health Checks

The application includes health check endpoints:

- `GET /health` - Basic health check
- `GET /health/db` - Database connectivity check
- `GET /health/redis` - Redis connectivity check

## 📈 Monitoring & Logging

### Application Logs

Comprehensive logging for:
- Security events
- Authentication attempts
- Email notifications
- API requests
- Database operations

### Metrics

Built-in metrics tracking:
- Login success/failure rates
- Security event counts
- Email delivery rates
- API response times
- Database query performance

## 🔧 Development

### Code Structure

```
backend/
├── app/
│   ├── api/v1/        # API endpoints
│   ├── core/          # Core configuration
│   ├── services/      # Business logic
│   ├── schemas/       # Pydantic models
│   └── tasks/         # Background tasks
├── prisma/            # Database schema
├── tests/             # Test files
└── main.py           # Application entry point
```

### Testing

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=app tests/
```

### Code Quality

```bash
# Format code
black app/

# Lint code
pylint app/

# Type checking
mypy app/
```

## 📋 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the logs for troubleshooting

## 🔄 Updates

The application includes automatic update mechanisms:
- Real-time market data updates
- Security threat intelligence updates
- User behavior analysis improvements
- Performance optimizations # fortexa-backend
