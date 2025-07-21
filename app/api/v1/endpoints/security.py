from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from prisma import Prisma
from app.core.database import get_db
from app.core.logger import logger
from app.services.auth_service import AuthService
from app.services.security_service import SecurityService
from pydantic import BaseModel

router = APIRouter()
security = HTTPBearer()

async def get_auth_service(db: Prisma = Depends(get_db)) -> AuthService:
    """Get authentication service"""
    return AuthService(db)

async def get_security_service(db: Prisma = Depends(get_db)) -> SecurityService:
    """Get security service"""
    return SecurityService(db)

async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> str:
    """Get current user ID from token"""
    token = credentials.credentials
    token_data = auth_service.verify_token(token)
    return token_data["user_id"]

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
        from app.core.exceptions import UserNotFoundException
        raise UserNotFoundException()
    
    # Check if email is verified
    if not user.isEmailVerified:
        from app.core.exceptions import EmailNotVerifiedException
        raise EmailNotVerifiedException()
    
    # Check if MFA is enabled
    if not user.isMfaEnabled:
        from app.core.exceptions import MFANotSetupException
        raise MFANotSetupException()
    
    return user_id

# Response Models
class SecurityEventResponse(BaseModel):
    id: str
    eventType: str
    severity: str
    description: str
    ipAddress: Optional[str]
    userAgent: Optional[str]
    location: Optional[str]
    metadata: Optional[dict]
    isResolved: bool
    createdAt: datetime
    userId: Optional[str]
    userEmail: Optional[str]

class LoginAttemptResponse(BaseModel):
    id: str
    email: str
    ipAddress: str
    userAgent: Optional[str]
    location: Optional[str]
    country: Optional[str]
    city: Optional[str]
    isSuccessful: bool
    failureReason: Optional[str]
    riskScore: float
    isSuspicious: bool
    createdAt: datetime

class IPStatsResponse(BaseModel):
    ipAddress: str
    country: Optional[str]
    city: Optional[str]
    loginAttempts: int
    failedLogins: int
    riskScore: float
    reputation: str
    isBlacklisted: bool
    isVpn: bool
    isProxy: bool
    isTor: bool
    lastLoginAt: Optional[datetime]

class SecurityMetricsResponse(BaseModel):
    totalEvents: int
    criticalEvents: int
    highRiskEvents: int
    blockedAttempts: int
    suspiciousLogins: int
    uniqueIPs: int
    accountsLocked: int
    todayVsYesterday: dict

class SecurityChartDataResponse(BaseModel):
    name: str
    events: int
    attempts: int
    blocked: int

@router.get("/events", response_model=List[SecurityEventResponse])
async def get_security_events(
    current_user_id: str = Depends(get_verified_user_id),
    severity: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Prisma = Depends(get_db)
):
    """Get security events with filtering"""
    try:
        # Build where clause
        where_clause = {}
        
        if severity:
            where_clause["severity"] = severity
        
        if event_type:
            where_clause["eventType"] = event_type
        
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["gte"] = start_date
            if end_date:
                date_filter["lte"] = end_date
            where_clause["createdAt"] = date_filter
        
        # Get events
        events = await db.securityevent.find_many(
            where=where_clause,
            include={
                "user": {
                    "select": {"email": True}
                }
            },
            order={"createdAt": "desc"},
            take=limit,
            skip=offset
        )
        
        # Format response
        return [
            SecurityEventResponse(
                id=event.id,
                eventType=event.eventType,
                severity=event.severity,
                description=event.description,
                ipAddress=event.ipAddress,
                userAgent=event.userAgent,
                location=event.location,
                metadata=event.metadata,
                isResolved=event.isResolved,
                createdAt=event.createdAt,
                userId=event.userId,
                userEmail=event.user.email if event.user else None
            )
            for event in events
        ]
    
    except Exception as e:
        logger.error(f"Failed to get security events: {e}")
        raise HTTPException(status_code=500, detail="Failed to get security events")

@router.get("/login-attempts", response_model=List[LoginAttemptResponse])
async def get_login_attempts(
    current_user_id: str = Depends(get_verified_user_id),
    is_successful: Optional[bool] = Query(None),
    is_suspicious: Optional[bool] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Prisma = Depends(get_db)
):
    """Get login attempts with filtering"""
    try:
        # Build where clause
        where_clause = {}
        
        if is_successful is not None:
            where_clause["isSuccessful"] = is_successful
        
        if is_suspicious is not None:
            where_clause["isSuspicious"] = is_suspicious
        
        if start_date or end_date:
            date_filter = {}
            if start_date:
                date_filter["gte"] = start_date
            if end_date:
                date_filter["lte"] = end_date
            where_clause["createdAt"] = date_filter
        
        # Get login attempts
        attempts = await db.loginattempt.find_many(
            where=where_clause,
            order={"createdAt": "desc"},
            take=limit,
            skip=offset
        )
        
        # Format response
        return [
            LoginAttemptResponse(
                id=attempt.id,
                email=attempt.email,
                ipAddress=attempt.ipAddress,
                userAgent=attempt.userAgent,
                location=attempt.location,
                country=attempt.country,
                city=attempt.city,
                isSuccessful=attempt.isSuccessful,
                failureReason=attempt.failureReason,
                riskScore=attempt.riskScore,
                isSuspicious=attempt.isSuspicious,
                createdAt=attempt.createdAt
            )
            for attempt in attempts
        ]
    
    except Exception as e:
        logger.error(f"Failed to get login attempts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get login attempts")

@router.get("/ip-stats", response_model=List[IPStatsResponse])
async def get_ip_stats(
    current_user_id: str = Depends(get_verified_user_id),
    reputation: Optional[str] = Query(None),
    is_blacklisted: Optional[bool] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Prisma = Depends(get_db)
):
    """Get IP address statistics"""
    try:
        # Build where clause
        where_clause = {}
        
        if reputation:
            where_clause["reputation"] = reputation
        
        if is_blacklisted is not None:
            where_clause["isBlacklisted"] = is_blacklisted
        
        # Get IP stats
        ip_stats = await db.ipaddress.find_many(
            where=where_clause,
            order={"loginAttempts": "desc"},
            take=limit,
            skip=offset
        )
        
        # Format response
        return [
            IPStatsResponse(
                ipAddress=ip.ipAddress,
                country=ip.country,
                city=ip.city,
                loginAttempts=ip.loginAttempts,
                failedLogins=ip.failedLogins,
                riskScore=ip.riskScore,
                reputation=ip.reputation,
                isBlacklisted=ip.isBlacklisted,
                isVpn=ip.isVpn,
                isProxy=ip.isProxy,
                isTor=ip.isTor,
                lastLoginAt=ip.lastLoginAt
            )
            for ip in ip_stats
        ]
    
    except Exception as e:
        logger.error(f"Failed to get IP stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get IP stats")

@router.get("/metrics", response_model=SecurityMetricsResponse)
async def get_security_metrics(
    current_user_id: str = Depends(get_verified_user_id),
    days: int = Query(7, le=90),
    db: Prisma = Depends(get_db)
):
    """Get security metrics and KPIs"""
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        yesterday = end_date - timedelta(days=1)
        day_before_yesterday = yesterday - timedelta(days=1)
        
        # Total events
        total_events = await db.securityevent.count(
            where={"createdAt": {"gte": start_date}}
        )
        
        # Critical events
        critical_events = await db.securityevent.count(
            where={
                "severity": "CRITICAL",
                "createdAt": {"gte": start_date}
            }
        )
        
        # High risk events
        high_risk_events = await db.securityevent.count(
            where={
                "severity": "HIGH",
                "createdAt": {"gte": start_date}
            }
        )
        
        # Blocked attempts (failed login attempts)
        blocked_attempts = await db.loginattempt.count(
            where={
                "isSuccessful": False,
                "createdAt": {"gte": start_date}
            }
        )
        
        # Suspicious logins
        suspicious_logins = await db.loginattempt.count(
            where={
                "isSuspicious": True,
                "createdAt": {"gte": start_date}
            }
        )
        
        # Unique IPs
        unique_ips_result = await db.loginattempt.group_by(
            by=["ipAddress"],
            where={"createdAt": {"gte": start_date}},
            _count={"ipAddress": True}
        )
        unique_ips = len(unique_ips_result)
        
        # Accounts locked
        accounts_locked = await db.user.count(
            where={
                "accountLockedUntil": {"gt": datetime.now(timezone.utc)}
            }
        )
        
        # Yesterday vs day before yesterday comparison
        yesterday_events = await db.securityevent.count(
            where={
                "createdAt": {
                    "gte": yesterday,
                    "lt": end_date
                }
            }
        )
        
        day_before_events = await db.securityevent.count(
            where={
                "createdAt": {
                    "gte": day_before_yesterday,
                    "lt": yesterday
                }
            }
        )
        
        yesterday_attempts = await db.loginattempt.count(
            where={
                "createdAt": {
                    "gte": yesterday,
                    "lt": end_date
                }
            }
        )
        
        day_before_attempts = await db.loginattempt.count(
            where={
                "createdAt": {
                    "gte": day_before_yesterday,
                    "lt": yesterday
                }
            }
        )
        
        yesterday_blocked = await db.loginattempt.count(
            where={
                "isSuccessful": False,
                "createdAt": {
                    "gte": yesterday,
                    "lt": end_date
                }
            }
        )
        
        day_before_blocked = await db.loginattempt.count(
            where={
                "isSuccessful": False,
                "createdAt": {
                    "gte": day_before_yesterday,
                    "lt": yesterday
                }
            }
        )
        
        # Calculate percentage changes
        events_change = ((yesterday_events - day_before_events) / max(day_before_events, 1)) * 100
        attempts_change = ((yesterday_attempts - day_before_attempts) / max(day_before_attempts, 1)) * 100
        blocked_change = ((yesterday_blocked - day_before_blocked) / max(day_before_blocked, 1)) * 100
        
        return SecurityMetricsResponse(
            totalEvents=total_events,
            criticalEvents=critical_events,
            highRiskEvents=high_risk_events,
            blockedAttempts=blocked_attempts,
            suspiciousLogins=suspicious_logins,
            uniqueIPs=unique_ips,
            accountsLocked=accounts_locked,
            todayVsYesterday={
                "events": round(events_change, 1),
                "attempts": round(attempts_change, 1),
                "blocked": round(blocked_change, 1)
            }
        )
    
    except Exception as e:
        logger.error(f"Failed to get security metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get security metrics")

@router.get("/chart-data", response_model=List[SecurityChartDataResponse])
async def get_security_chart_data(
    current_user_id: str = Depends(get_verified_user_id),
    days: int = Query(7, le=30),
    db: Prisma = Depends(get_db)
):
    """Get data for security charts"""
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        chart_data = []
        
        for i in range(days):
            day_start = start_date + timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            
            # Events for this day
            events_count = await db.securityevent.count(
                where={
                    "createdAt": {
                        "gte": day_start,
                        "lt": day_end
                    }
                }
            )
            
            # Login attempts for this day
            attempts_count = await db.loginattempt.count(
                where={
                    "createdAt": {
                        "gte": day_start,
                        "lt": day_end
                    }
                }
            )
            
            # Blocked attempts for this day
            blocked_count = await db.loginattempt.count(
                where={
                    "isSuccessful": False,
                    "createdAt": {
                        "gte": day_start,
                        "lt": day_end
                    }
                }
            )
            
            chart_data.append(SecurityChartDataResponse(
                name=day_start.strftime("%a"),
                events=events_count,
                attempts=attempts_count,
                blocked=blocked_count
            ))
        
        return chart_data
    
    except Exception as e:
        logger.error(f"Failed to get chart data: {e}")
        raise HTTPException(status_code=500, detail="Failed to get chart data")

@router.post("/blacklist-ip/{ip_address}")
async def blacklist_ip(
    ip_address: str,
    reason: str,
    current_user_id: str = Depends(get_verified_user_id),
    security_service: SecurityService = Depends(get_security_service)
):
    """Blacklist an IP address"""
    try:
        await security_service.blacklist_ip(ip_address, reason)
        return {"message": f"IP {ip_address} has been blacklisted", "success": True}
    
    except Exception as e:
        logger.error(f"Failed to blacklist IP: {e}")
        raise HTTPException(status_code=500, detail="Failed to blacklist IP")

@router.post("/unlock-account/{user_id}")
async def unlock_account(
    user_id: str,
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Unlock a user account"""
    try:
        await db.user.update(
            where={"id": user_id},
            data={
                "accountLockedUntil": None,
                "failedLoginAttempts": 0
            }
        )
        
        # Log the unlock event
        await db.securityevent.create(
            data={
                "eventType": "ACCOUNT_UNLOCKED",
                "userId": user_id,
                "severity": "LOW",
                "description": f"Account unlocked by admin {current_user_id}",
                "metadata": {"unlocked_by": current_user_id}
            }
        )
        
        return {"message": "Account has been unlocked", "success": True}
    
    except Exception as e:
        logger.error(f"Failed to unlock account: {e}")
        raise HTTPException(status_code=500, detail="Failed to unlock account")

@router.post("/resolve-event/{event_id}")
async def resolve_security_event(
    event_id: str,
    current_user_id: str = Depends(get_verified_user_id),
    db: Prisma = Depends(get_db)
):
    """Mark a security event as resolved"""
    try:
        await db.securityevent.update(
            where={"id": event_id},
            data={
                "isResolved": True,
                "resolvedAt": datetime.now(timezone.utc),
                "resolvedBy": current_user_id
            }
        )
        
        return {"message": "Security event has been resolved", "success": True}
    
    except Exception as e:
        logger.error(f"Failed to resolve security event: {e}")
        raise HTTPException(status_code=500, detail="Failed to resolve security event")

@router.get("/threat-intel/{ip_address}")
async def get_threat_intelligence(
    ip_address: str,
    current_user_id: str = Depends(get_verified_user_id),
    security_service: SecurityService = Depends(get_security_service)
):
    """Get threat intelligence for an IP address"""
    try:
        # This would use the real threat intelligence checking
        is_threat = await security_service._check_multiple_threat_sources(ip_address)
        
        # Get additional details from our database
        ip_record = await security_service.db.ipaddress.find_unique(
            where={"ipAddress": ip_address}
        )
        
        return {
            "ip_address": ip_address,
            "is_threat": is_threat,
            "reputation": ip_record.reputation if ip_record else "UNKNOWN",
            "is_blacklisted": ip_record.isBlacklisted if ip_record else False,
            "is_vpn": ip_record.isVpn if ip_record else False,
            "is_proxy": ip_record.isProxy if ip_record else False,
            "is_tor": ip_record.isTor if ip_record else False,
            "country": ip_record.country if ip_record else None,
            "city": ip_record.city if ip_record else None
        }
    
    except Exception as e:
        logger.error(f"Failed to get threat intelligence: {e}")
        raise HTTPException(status_code=500, detail="Failed to get threat intelligence") 