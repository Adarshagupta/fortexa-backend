#!/usr/bin/env python3
"""
Test script for email notifications
Run this script to test all email notification types
"""

import asyncio
import sys
from datetime import datetime, timezone
from app.services.email_service import EmailService
from app.services.security_service import SecurityContext

async def test_basic_email():
    """Test basic email functionality"""
    print("🔧 Testing basic email functionality...")
    
    email_service = EmailService()
    
    success = await email_service.send_email(
        to_email="test@example.com",
        subject="🧪 Fortexa Email Test",
        html_content="""
        <h1>🎉 Email Test Successful!</h1>
        <p>If you receive this email, your SMTP configuration is working correctly.</p>
        <p><strong>Server:</strong> Fortexa Backend</p>
        <p><strong>Time:</strong> {}</p>
        """.format(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')),
        text_content=f"""
        Email Test Successful!
        
        If you receive this email, your SMTP configuration is working correctly.
        
        Server: Fortexa Backend
        Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}
        """
    )
    
    if success:
        print("✅ Basic email test passed")
    else:
        print("❌ Basic email test failed")
    
    return success

async def test_login_notification():
    """Test login notification email"""
    print("🔧 Testing login notification...")
    
    email_service = EmailService()
    
    login_details = {
        'time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'ip_address': '192.168.1.100',
        'location': 'New York, NY, United States',
        'device': 'Mac Computer',
        'browser': 'Google Chrome'
    }
    
    success = await email_service.send_login_notification(
        to_email="test@example.com",
        user_name="Test User",
        login_details=login_details
    )
    
    if success:
        print("✅ Login notification test passed")
    else:
        print("❌ Login notification test failed")
    
    return success

async def test_failed_login_notification():
    """Test failed login notification email"""
    print("🔧 Testing failed login notification...")
    
    email_service = EmailService()
    
    attempt_details = {
        'time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'ip_address': '203.0.113.15',
        'location': 'Unknown Location',
        'device': 'Unknown Device',
        'browser': 'Unknown Browser',
        'attempt_count': '3'
    }
    
    success = await email_service.send_failed_login_notification(
        to_email="test@example.com",
        user_name="Test User",
        attempt_details=attempt_details
    )
    
    if success:
        print("✅ Failed login notification test passed")
    else:
        print("❌ Failed login notification test failed")
    
    return success

async def test_password_change_notification():
    """Test password change notification email"""
    print("🔧 Testing password change notification...")
    
    email_service = EmailService()
    
    change_details = {
        'time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'ip_address': '192.168.1.100',
        'location': 'New York, NY, United States',
        'device': 'Mac Computer',
        'browser': 'Google Chrome'
    }
    
    success = await email_service.send_password_change_notification(
        to_email="test@example.com",
        user_name="Test User",
        change_details=change_details
    )
    
    if success:
        print("✅ Password change notification test passed")
    else:
        print("❌ Password change notification test failed")
    
    return success

async def test_mfa_notification():
    """Test MFA notification email"""
    print("🔧 Testing MFA notification...")
    
    email_service = EmailService()
    
    event_details = {
        'time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'ip_address': '192.168.1.100',
        'location': 'New York, NY, United States',
        'device': 'Mac Computer',
        'browser': 'Google Chrome'
    }
    
    success = await email_service.send_mfa_notification(
        to_email="test@example.com",
        user_name="Test User",
        mfa_event="enabled",
        event_details=event_details
    )
    
    if success:
        print("✅ MFA notification test passed")
    else:
        print("❌ MFA notification test failed")
    
    return success

async def test_security_alert():
    """Test security alert email"""
    print("🔧 Testing security alert...")
    
    email_service = EmailService()
    
    alert_details = {
        'time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        'ip_address': '198.51.100.42',
        'location': 'Unknown Location',
        'device': 'Unknown Device',
        'browser': 'Unknown Browser',
        'risk_score': '7.5/10.0'
    }
    
    success = await email_service.send_security_alert(
        to_email="test@example.com",
        user_name="Test User",
        alert_type="suspicious_activity",
        alert_details=alert_details
    )
    
    if success:
        print("✅ Security alert test passed")
    else:
        print("❌ Security alert test failed")
    
    return success

async def main():
    """Run all email tests"""
    print("🚀 Starting Fortexa Email Notification Tests")
    print("=" * 50)
    
    # Update email address for testing
    test_email = input("Enter your email address for testing (or press Enter for test@example.com): ").strip()
    if not test_email:
        test_email = "test@example.com"
    
    print(f"📧 Testing with email: {test_email}")
    print("=" * 50)
    
    # Update the test email in all test functions
    global TEST_EMAIL
    TEST_EMAIL = test_email
    
    tests = [
        ("Basic Email", test_basic_email),
        ("Login Notification", test_login_notification),
        ("Failed Login Notification", test_failed_login_notification),
        ("Password Change Notification", test_password_change_notification),
        ("MFA Notification", test_mfa_notification),
        ("Security Alert", test_security_alert)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📝 Running {test_name} test...")
        try:
            # Replace test@example.com with actual test email
            import inspect
            source = inspect.getsource(test_func)
            source = source.replace("test@example.com", test_email)
            exec(source)
            
            result = await test_func()
            results.append((test_name, result))
            
            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
                
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Email notifications are working correctly.")
    else:
        print("⚠️  Some tests failed. Please check your SMTP configuration.")
        print("\n🔧 Troubleshooting tips:")
        print("1. Verify SMTP credentials in your .env file")
        print("2. Check if your email provider requires app passwords")
        print("3. Ensure TLS settings are correct")
        print("4. Check firewall settings")
        print("5. Review server logs for detailed error messages")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        sys.exit(1) 