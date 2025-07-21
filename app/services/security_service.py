import asyncio
import json
import hashlib
import ipaddress
import requests
from maxminddb import open_database
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
from prisma import Prisma
from app.core.config import settings
from app.core.logger import logger
from app.core.exceptions import SecurityException
from app.services.email_service import EmailService
from dataclasses import dataclass
from enum import Enum
import ssl
import socket
import dns.resolver
import concurrent.futures
import threading

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class SecurityContext:
    """Security context for a request"""
    user_id: Optional[str] = None
    email: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_fingerprint: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    is_suspicious: bool = False
    threats: List[str] = None
    
    def __post_init__(self):
        if self.threats is None:
            self.threats = []

@dataclass
class LoginAnalysis:
    """Analysis result for a login attempt"""
    is_allowed: bool = True
    risk_score: float = 0.0
    threats: List[str] = None
    required_actions: List[str] = None
    block_reason: Optional[str] = None
    
    def __post_init__(self):
        if self.threats is None:
            self.threats = []
        if self.required_actions is None:
            self.required_actions = []

class SecurityService:
    def __init__(self, db: Prisma):
        self.db = db
        self.email_service = EmailService()
        self.geoip_reader = None
        self.threat_intel_cache = {}
        self.cache_lock = threading.Lock()
        self.init_geolocation()
        
        # Threat intelligence API endpoints
        self.threat_apis = {
            "abuseipdb": "https://api.abuseipdb.com/api/v2/check",
            "virustotal": "https://www.virustotal.com/vtapi/v2/ip-address/report",
            "ipqualityscore": "https://ipqualityscore.com/api/json/ip"
        }
        
        # Known VPN/Proxy providers
        self.vpn_providers = [
            "nordvpn", "expressvpn", "surfshark", "cyberghost", "privateinternetaccess",
            "mullvad", "protonvpn", "windscribe", "tunnelbear", "hidemyass"
        ]
        
        # Tor exit node list (in production, fetch from official sources)
        self.tor_exit_nodes = set()
        self._load_tor_exit_nodes()

    # === EMAIL NOTIFICATION METHODS ===

    async def send_login_notification(self, context: SecurityContext, user_name: str):
        """Send email notification for successful login"""
        if not context.email:
            return
            
        try:
            login_details = {
                'time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
                'ip_address': context.ip_address or 'Unknown',
                'location': self._format_location(context.location),
                'device': self._extract_device_info(context.user_agent),
                'browser': self._extract_browser_info(context.user_agent)
            }
            
            await self.email_service.send_login_notification(
                context.email, user_name, login_details
            )
            
            logger.info(f"Login notification sent to {context.email}")
        except Exception as e:
            logger.error(f"Failed to send login notification: {e}")

    async def send_failed_login_notification(self, context: SecurityContext, user_name: str, attempt_count: int):
        """Send email notification for failed login attempts"""
        if not context.email:
            return
            
        try:
            attempt_details = {
                'time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
                'ip_address': context.ip_address or 'Unknown',
                'location': self._format_location(context.location),
                'device': self._extract_device_info(context.user_agent),
                'browser': self._extract_browser_info(context.user_agent),
                'attempt_count': str(attempt_count)
            }
            
            await self.email_service.send_failed_login_notification(
                context.email, user_name, attempt_details
            )
            
            logger.info(f"Failed login notification sent to {context.email}")
        except Exception as e:
            logger.error(f"Failed to send failed login notification: {e}")

    async def send_security_alert_notification(self, context: SecurityContext, user_name: str, 
                                             alert_type: str, analysis: LoginAnalysis):
        """Send security alert email notification"""
        if not context.email:
            return
            
        try:
            alert_details = {
                'time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
                'ip_address': context.ip_address or 'Unknown',
                'location': self._format_location(context.location),
                'device': self._extract_device_info(context.user_agent),
                'browser': self._extract_browser_info(context.user_agent),
                'risk_score': f"{analysis.risk_score:.1f}/10.0"
            }
            
            await self.email_service.send_security_alert(
                context.email, user_name, alert_type, alert_details
            )
            
            logger.info(f"Security alert notification sent to {context.email}")
        except Exception as e:
            logger.error(f"Failed to send security alert notification: {e}")

    async def send_mfa_event_notification(self, context: SecurityContext, user_name: str, 
                                        mfa_event: str):
        """Send MFA event email notification"""
        if not context.email:
            return
            
        try:
            event_details = {
                'time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
                'ip_address': context.ip_address or 'Unknown',
                'location': self._format_location(context.location),
                'device': self._extract_device_info(context.user_agent),
                'browser': self._extract_browser_info(context.user_agent)
            }
            
            await self.email_service.send_mfa_notification(
                context.email, user_name, mfa_event, event_details
            )
            
            logger.info(f"MFA event notification sent to {context.email}")
        except Exception as e:
            logger.error(f"Failed to send MFA event notification: {e}")

    async def send_password_change_notification(self, context: SecurityContext, user_name: str):
        """Send password change email notification"""
        if not context.email:
            return
            
        try:
            change_details = {
                'time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
                'ip_address': context.ip_address or 'Unknown',
                'location': self._format_location(context.location),
                'device': self._extract_device_info(context.user_agent),
                'browser': self._extract_browser_info(context.user_agent)
            }
            
            await self.email_service.send_password_change_notification(
                context.email, user_name, change_details
            )
            
            logger.info(f"Password change notification sent to {context.email}")
        except Exception as e:
            logger.error(f"Failed to send password change notification: {e}")

    def _format_location(self, location: Optional[Dict[str, Any]]) -> str:
        """Format location information for email"""
        if not location:
            return "Unknown"
        
        parts = []
        if location.get('city'):
            parts.append(location['city'])
        if location.get('region'):
            parts.append(location['region'])
        if location.get('country'):
            parts.append(location['country'])
        
        return ", ".join(parts) if parts else "Unknown"

    def _extract_device_info(self, user_agent: Optional[str]) -> str:
        """Extract device information from user agent"""
        if not user_agent:
            return "Unknown"
        
        user_agent_lower = user_agent.lower()
        
        # Mobile devices
        if 'mobile' in user_agent_lower or 'android' in user_agent_lower:
            return "Mobile Device"
        elif 'iphone' in user_agent_lower or 'ipad' in user_agent_lower:
            return "iOS Device"
        elif 'macintosh' in user_agent_lower:
            return "Mac Computer"
        elif 'windows' in user_agent_lower:
            return "Windows Computer"
        elif 'linux' in user_agent_lower:
            return "Linux Computer"
        else:
            return "Unknown Device"

    def _extract_browser_info(self, user_agent: Optional[str]) -> str:
        """Extract browser information from user agent"""
        if not user_agent:
            return "Unknown"
        
        user_agent_lower = user_agent.lower()
        
        if 'chrome' in user_agent_lower:
            return "Google Chrome"
        elif 'firefox' in user_agent_lower:
            return "Mozilla Firefox"
        elif 'safari' in user_agent_lower:
            return "Safari"
        elif 'edge' in user_agent_lower:
            return "Microsoft Edge"
        elif 'opera' in user_agent_lower:
            return "Opera"
        else:
            return "Unknown Browser"

    # === EXISTING METHODS ===
    
    def init_geolocation(self):
        """Initialize real GeoIP database"""
        try:
            from geolite2 import geolite2
            self.geoip_reader = geolite2.reader()
            logger.info("GeoIP database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GeoIP database: {e}")
            self.geoip_reader = None
    
    def _load_tor_exit_nodes(self):
        """Load Tor exit nodes from official source"""
        try:
            # Use the correct Tor Project API endpoint
            response = requests.get(
                "https://onionoo.torproject.org/summary?type=relay&running=true&flag=Exit", 
                timeout=10,
                headers={'User-Agent': 'Fortexa-Security/1.0'}
            )
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Extract IP addresses from the relays data
                    exit_ips = set()
                    relays = data.get('relays', [])
                    for relay in relays:
                        if relay.get('or_addresses'):
                            for address in relay['or_addresses']:
                                # Extract IP from format like "1.2.3.4:9001" or "[ipv6]:port"
                                if ':' in address and not address.startswith('['):
                                    ip = address.split(':')[0]
                                    exit_ips.add(ip)
                    
                    self.tor_exit_nodes = exit_ips
                    logger.info(f"Loaded {len(self.tor_exit_nodes)} Tor exit nodes")
                except ValueError as json_error:
                    logger.warning(f"Invalid JSON response from Tor API: {json_error}")
                    # Fall back to hardcoded list or empty set
                    self.tor_exit_nodes = set()
            else:
                logger.warning(f"Tor API returned status {response.status_code}")
                self.tor_exit_nodes = set()
        except requests.RequestException as e:
            logger.error(f"Failed to load Tor exit nodes: {e}")
            # In development, just use an empty set to avoid blocking
            self.tor_exit_nodes = set()
        except Exception as e:
            logger.error(f"Unexpected error loading Tor exit nodes: {e}")
            self.tor_exit_nodes = set()
    
    async def analyze_login_attempt(self, context: SecurityContext) -> LoginAnalysis:
        """Comprehensive analysis of a login attempt"""
        analysis = LoginAnalysis()
        
        # In development mode, be very permissive with security checks
        if settings.DEBUG:
            logger.info("DEBUG MODE: Skipping most security checks for development")
            
            # Still do basic rate limiting to prevent abuse, but with much higher limits
            await self._check_rate_limits(context, analysis)
            
            # Calculate minimal risk score
            analysis.risk_score = self._calculate_risk_score(analysis.threats)
            
            # In debug mode, only block if risk score is extremely high (basically never)
            if analysis.risk_score > 15.0:  # Virtually impossible threshold
                analysis.is_allowed = False
                analysis.block_reason = "Extremely high risk score detected"
            
            logger.info(f"DEBUG MODE: Risk score={analysis.risk_score}, threats={analysis.threats}, allowed={analysis.is_allowed}")
            return analysis
        
        # Production mode: Full security checks
        # Perform security checks concurrently for better performance
        await asyncio.gather(
            self._check_rate_limits(context, analysis),
            self._check_ip_reputation(context, analysis),
            self._check_geolocation_anomalies(context, analysis),
            self._check_device_fingerprint(context, analysis),
            self._check_user_behavior_patterns(context, analysis),
            self._check_concurrent_sessions(context, analysis),
            return_exceptions=True
        )
        
        # Run threat intelligence check separately as it may be slower
        await self._check_threat_intelligence(context, analysis)
        
        # Calculate final risk score
        analysis.risk_score = self._calculate_risk_score(analysis.threats)
        
        # Determine if login should be blocked
        if analysis.risk_score > 8.0:
            analysis.is_allowed = False
            analysis.block_reason = "High risk score detected"
        
        return analysis
    
    async def _check_rate_limits(self, context: SecurityContext, analysis: LoginAnalysis):
        """Check rate limiting rules"""
        if not context.ip_address:
            return
        
        # Check IP-based rate limits
        await self._check_ip_rate_limit(context.ip_address, analysis)
        
        # Check user-based rate limits if user exists
        if context.user_id:
            await self._check_user_rate_limit(context.user_id, analysis)
    
    async def _check_ip_rate_limit(self, ip_address: str, analysis: LoginAnalysis):
        """Check IP-based rate limiting"""
        window_minutes = 15
        
        # In development mode, be much more permissive with rate limits
        if settings.DEBUG:
            max_attempts = 100  # Very high limit for development
        else:
            max_attempts = 20  # Production limit
        
        window_start = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        
        # Count recent attempts from this IP
        recent_attempts = await self.db.loginattempt.count(
            where={
                "ipAddress": ip_address,
                "createdAt": {"gte": window_start}
            }
        )
        
        logger.info(f"IP rate limit check for {ip_address}: {recent_attempts}/{max_attempts} attempts in last {window_minutes} minutes")
        
        if recent_attempts >= max_attempts:
            analysis.threats.append("IP_RATE_LIMIT_EXCEEDED")
            analysis.required_actions.append("BLOCK_REQUEST")
            analysis.is_allowed = False
            analysis.block_reason = f"Too many login attempts from IP {ip_address}"
    
    async def _check_user_rate_limit(self, user_id: str, analysis: LoginAnalysis):
        """Check user-based rate limiting"""
        window_minutes = 10
        
        # In development mode, be much more permissive with rate limits
        if settings.DEBUG:
            max_attempts = 50  # Very high limit for development
        else:
            max_attempts = 10  # Production limit
        
        window_start = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        
        # Count recent failed attempts for this user
        recent_failures = await self.db.loginattempt.count(
            where={
                "userId": user_id,
                "isSuccessful": False,
                "createdAt": {"gte": window_start}
            }
        )
        
        logger.info(f"User rate limit check for {user_id}: {recent_failures}/{max_attempts} failed attempts in last {window_minutes} minutes")
        
        if recent_failures >= max_attempts:
            analysis.threats.append("USER_RATE_LIMIT_EXCEEDED")
            analysis.required_actions.append("LOCK_ACCOUNT")
            analysis.is_allowed = False
            analysis.block_reason = f"Too many failed login attempts for user"
    
    async def _check_ip_reputation(self, context: SecurityContext, analysis: LoginAnalysis):
        """Check IP reputation and blacklist status"""
        if not context.ip_address:
            return
        
        # Check our local IP database
        ip_record = await self.db.ipaddress.find_unique(
            where={"ipAddress": context.ip_address}
        )
        
        logger.info(f"IP reputation check for {context.ip_address}: record exists={ip_record is not None}")
        
        if ip_record:
            logger.info(f"IP record details: blacklisted={ip_record.isBlacklisted}, reputation={ip_record.reputation}, vpn={ip_record.isVpn}, proxy={ip_record.isProxy}, tor={ip_record.isTor}")
            
            if ip_record.isBlacklisted:
                analysis.threats.append("BLACKLISTED_IP")
                analysis.required_actions.append("BLOCK_REQUEST")
                analysis.is_allowed = False
                analysis.block_reason = "IP address is blacklisted"
            
            if ip_record.reputation == "MALICIOUS":
                analysis.threats.append("MALICIOUS_IP_REPUTATION")
                analysis.required_actions.append("REQUIRE_MFA")
            
            if ip_record.isVpn or ip_record.isProxy or ip_record.isTor:
                analysis.threats.append("ANONYMIZING_SERVICE")
                analysis.required_actions.append("REQUIRE_VERIFICATION")
        
        # Update IP record with real data
        await self._update_ip_record(context.ip_address, context.location)
    
    async def _check_geolocation_anomalies(self, context: SecurityContext, analysis: LoginAnalysis):
        """Check for unusual geographic locations"""
        if not context.user_id or not context.location:
            return
        
        # Get user's recent login locations
        recent_sessions = await self.db.usersession.find_many(
            where={
                "userId": context.user_id,
                "createdAt": {"gte": datetime.now(timezone.utc) - timedelta(days=30)}
            },
            order={"createdAt": "desc"},
            take=10
        )
        
        if recent_sessions:
            # Check for impossible travel
            for session in recent_sessions:
                if session.country and session.country != context.location.get("country"):
                    time_diff = (datetime.now(timezone.utc) - session.createdAt).total_seconds() / 3600
                    
                    # Calculate approximate distance and travel time
                    if session.latitude and session.longitude and context.location.get("latitude") and context.location.get("longitude"):
                        distance = self._calculate_distance(
                            session.latitude, session.longitude,
                            context.location["latitude"], context.location["longitude"]
                        )
                        # Assume max travel speed of 1000 km/h (commercial aviation)
                        min_travel_time = distance / 1000
                        
                        if time_diff < min_travel_time:
                            analysis.threats.append("IMPOSSIBLE_TRAVEL")
                            analysis.required_actions.append("REQUIRE_MFA")
                            break
            
            # Check for completely new geographic region
            known_countries = set(s.country for s in recent_sessions if s.country)
            if context.location.get("country") not in known_countries:
                analysis.threats.append("NEW_GEOGRAPHIC_LOCATION")
                analysis.required_actions.append("REQUIRE_VERIFICATION")
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
        import math
        
        R = 6371  # Earth's radius in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat / 2) ** 2 + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    async def _check_device_fingerprint(self, context: SecurityContext, analysis: LoginAnalysis):
        """Check device fingerprint patterns"""
        if not context.user_id or not context.device_fingerprint:
            return
        
        # Check if device is trusted
        trusted_device = await self.db.trusteddevice.find_first(
            where={
                "userId": context.user_id,
                "deviceFingerprint": context.device_fingerprint,
                "isActive": True
            }
        )
        
        if not trusted_device:
            analysis.threats.append("UNKNOWN_DEVICE")
            analysis.required_actions.append("REQUIRE_MFA")
        
        # Check for suspicious user agents
        if context.user_agent:
            if self._is_suspicious_user_agent(context.user_agent):
                analysis.threats.append("SUSPICIOUS_USER_AGENT")
                analysis.required_actions.append("REQUIRE_VERIFICATION")
    
    async def _check_user_behavior_patterns(self, context: SecurityContext, analysis: LoginAnalysis):
        """Analyze user behavior patterns"""
        if not context.user_id:
            return
        
        # Check login time patterns
        current_hour = datetime.now(timezone.utc).hour
        
        # Get user's typical login hours
        recent_logins = await self.db.loginattempt.find_many(
            where={
                "userId": context.user_id,
                "isSuccessful": True,
                "createdAt": {"gte": datetime.now(timezone.utc) - timedelta(days=30)}
            },
            take=50
        )
        
        if recent_logins:
            typical_hours = [login.createdAt.hour for login in recent_logins]
            
            # Statistical analysis of login patterns
            if len(set(typical_hours)) >= 3:  # User has established patterns
                hour_differences = [abs(current_hour - h) for h in typical_hours]
                min_diff = min(hour_differences)
                
                if min_diff > 6:  # More than 6 hours from typical login times
                    analysis.threats.append("UNUSUAL_LOGIN_TIME")
                    analysis.required_actions.append("REQUIRE_MFA")
    
    async def _check_concurrent_sessions(self, context: SecurityContext, analysis: LoginAnalysis):
        """Check for excessive concurrent sessions"""
        if not context.user_id:
            return
        
        # Count active sessions
        active_sessions = await self.db.usersession.count(
            where={
                "userId": context.user_id,
                "isActive": True,
                "expiresAt": {"gt": datetime.now(timezone.utc)}
            }
        )
        
        if active_sessions > 5:  # More than 5 active sessions
            analysis.threats.append("EXCESSIVE_CONCURRENT_SESSIONS")
            analysis.required_actions.append("REQUIRE_VERIFICATION")
    
    async def _check_threat_intelligence(self, context: SecurityContext, analysis: LoginAnalysis):
        """Check against real threat intelligence feeds"""
        if not context.ip_address:
            return
        
        # Check cache first
        with self.cache_lock:
            cached_result = self.threat_intel_cache.get(context.ip_address)
            if cached_result and cached_result['timestamp'] > datetime.now() - timedelta(hours=1):
                if cached_result['is_threat']:
                    analysis.threats.append("THREAT_INTELLIGENCE_MATCH")
                    analysis.required_actions.append("BLOCK_REQUEST")
                    analysis.is_allowed = False
                    analysis.block_reason = "IP matches threat intelligence"
                return
        
        # Real threat intelligence checks
        is_threat = await self._check_multiple_threat_sources(context.ip_address)
        
        # Cache result
        with self.cache_lock:
            self.threat_intel_cache[context.ip_address] = {
                'is_threat': is_threat,
                'timestamp': datetime.now()
            }
        
        if is_threat:
            analysis.threats.append("THREAT_INTELLIGENCE_MATCH")
            analysis.required_actions.append("BLOCK_REQUEST")
            analysis.is_allowed = False
            analysis.block_reason = "IP matches threat intelligence"
    
    async def _check_multiple_threat_sources(self, ip_address: str) -> bool:
        """Check IP against multiple threat intelligence sources"""
        try:
            # Check if IP is in known malicious ranges
            if self._is_malicious_ip_range(ip_address):
                return True
            
            # Check Tor exit nodes
            if ip_address in self.tor_exit_nodes:
                return True
            
            # Check against public threat feeds (implement with your API keys)
            threat_checks = await asyncio.gather(
                self._check_abuseipdb(ip_address),
                self._check_virustotal(ip_address),
                self._check_dns_blacklists(ip_address),
                return_exceptions=True
            )
            
            # If any source indicates threat, consider it malicious
            return any(check for check in threat_checks if isinstance(check, bool) and check)
            
        except Exception as e:
            logger.error(f"Error checking threat intelligence: {e}")
            return False
    
    def _is_malicious_ip_range(self, ip_address: str) -> bool:
        """Check if IP is in known malicious ranges"""
        try:
            ip = ipaddress.ip_address(ip_address)
            
            # Known malicious ranges (expand based on threat intelligence)
            malicious_ranges = [
                ipaddress.ip_network("192.0.2.0/24"),  # RFC 5737 test range
                ipaddress.ip_network("203.0.113.0/24"),  # RFC 5737 test range
                # Add more known malicious ranges here
            ]
            
            return any(ip in network for network in malicious_ranges)
        except:
            return False
    
    async def _check_abuseipdb(self, ip_address: str) -> bool:
        """Check IP against AbuseIPDB"""
        try:
            # Implement with your AbuseIPDB API key
            # api_key = settings.ABUSEIPDB_API_KEY
            # headers = {'Key': api_key, 'Accept': 'application/json'}
            # params = {'ipAddress': ip_address, 'maxAgeInDays': 90, 'verbose': ''}
            # response = requests.get(self.threat_apis["abuseipdb"], headers=headers, params=params, timeout=5)
            # if response.status_code == 200:
            #     data = response.json()
            #     return data.get('data', {}).get('abuseConfidencePercentage', 0) > 25
            return False
        except Exception as e:
            logger.warning(f"AbuseIPDB check failed: {e}")
            return False
    
    async def _check_virustotal(self, ip_address: str) -> bool:
        """Check IP against VirusTotal"""
        try:
            # Implement with your VirusTotal API key
            # api_key = settings.VIRUSTOTAL_API_KEY
            # params = {'apikey': api_key, 'ip': ip_address}
            # response = requests.get(self.threat_apis["virustotal"], params=params, timeout=5)
            # if response.status_code == 200:
            #     data = response.json()
            #     return data.get('positives', 0) > 2
            return False
        except Exception as e:
            logger.warning(f"VirusTotal check failed: {e}")
            return False
    
    async def _check_dns_blacklists(self, ip_address: str) -> bool:
        """Check IP against DNS blacklists"""
        try:
            # Reverse IP for DNS blacklist lookup
            reversed_ip = '.'.join(reversed(ip_address.split('.')))
            
            # Common DNS blacklists
            blacklists = [
                'zen.spamhaus.org',
                'bl.spamcop.net',
                'dnsbl.sorbs.net',
                'cbl.abuseat.org'
            ]
            
            for blacklist in blacklists:
                try:
                    query = f"{reversed_ip}.{blacklist}"
                    result = dns.resolver.resolve(query, 'A')
                    if result:
                        return True
                except:
                    continue
            
            return False
        except Exception as e:
            logger.warning(f"DNS blacklist check failed: {e}")
            return False
    
    def _calculate_risk_score(self, threats: List[str]) -> float:
        """Calculate overall risk score based on threats"""
        threat_weights = {
            "BLACKLISTED_IP": 10.0,
            "MALICIOUS_IP_REPUTATION": 8.0,
            "THREAT_INTELLIGENCE_MATCH": 9.0,
            "IP_RATE_LIMIT_EXCEEDED": 7.0,
            "USER_RATE_LIMIT_EXCEEDED": 6.0,
            "IMPOSSIBLE_TRAVEL": 8.0,
            "ANONYMIZING_SERVICE": 5.0,
            "NEW_GEOGRAPHIC_LOCATION": 3.0,
            "UNKNOWN_DEVICE": 4.0,
            "SUSPICIOUS_USER_AGENT": 6.0,
            "UNUSUAL_LOGIN_TIME": 2.0,
            "EXCESSIVE_CONCURRENT_SESSIONS": 4.0,
        }
        
        total_score = sum(threat_weights.get(threat, 1.0) for threat in threats)
        return min(total_score, 10.0)  # Cap at 10.0
    
    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is suspicious"""
        suspicious_patterns = [
            "bot", "crawler", "spider", "scraper", "python", "curl", "wget",
            "automated", "script", "headless", "phantom", "selenium", "mechanize",
            "libwww", "urllib", "httpie", "postman", "insomnia"
        ]
        
        ua_lower = user_agent.lower()
        
        # Check for suspicious patterns
        if any(pattern in ua_lower for pattern in suspicious_patterns):
            return True
        
        # Check for unusual browser versions or formats
        if len(user_agent) < 20 or len(user_agent) > 500:
            return True
        
        # Check for missing common browser indicators
        common_indicators = ["mozilla", "webkit", "chrome", "firefox", "safari", "edge"]
        if not any(indicator in ua_lower for indicator in common_indicators):
            return True
        
        return False
    
    async def _update_ip_record(self, ip_address: str, location: Optional[Dict[str, Any]]):
        """Update or create IP address record with real geolocation"""
        try:
            # Get real geolocation info
            geo_info = self._get_geolocation(ip_address)
            
            # Detect VPN/Proxy/Tor
            vpn_detection = await self._detect_vpn_proxy_tor(ip_address)
            
            # Upsert IP record
            await self.db.ipaddress.upsert(
                where={"ipAddress": ip_address},
                create={
                    "ipAddress": ip_address,
                    "country": geo_info.get("country"),
                    "city": geo_info.get("city"),
                    "region": geo_info.get("region"),
                    "latitude": geo_info.get("latitude"),
                    "longitude": geo_info.get("longitude"),
                    "isp": geo_info.get("isp"),
                    "isVpn": vpn_detection["is_vpn"],
                    "isProxy": vpn_detection["is_proxy"],
                    "isTor": vpn_detection["is_tor"],
                    "loginAttempts": 1,
                    "lastLoginAt": datetime.now(timezone.utc)
                },
                update={
                    "loginAttempts": {"increment": 1},
                    "lastLoginAt": datetime.now(timezone.utc),
                    "country": geo_info.get("country"),
                    "city": geo_info.get("city"),
                    "region": geo_info.get("region"),
                    "latitude": geo_info.get("latitude"),
                    "longitude": geo_info.get("longitude"),
                    "isp": geo_info.get("isp"),
                    "isVpn": vpn_detection["is_vpn"],
                    "isProxy": vpn_detection["is_proxy"],
                    "isTor": vpn_detection["is_tor"]
                }
            )
        except Exception as e:
            logger.error(f"Failed to update IP record: {e}")
    
    def _get_geolocation(self, ip_address: str) -> Dict[str, Any]:
        """Get real geolocation information for IP address"""
        try:
            if not self.geoip_reader:
                return {
                    "country": "Unknown",
                    "city": "Unknown",
                    "region": "Unknown",
                    "latitude": 0.0,
                    "longitude": 0.0,
                    "isp": "Unknown"
                }
            
            match = self.geoip_reader.get(ip_address)
            if not match:
                return {
                    "country": "Unknown",
                    "city": "Unknown",
                    "region": "Unknown",
                    "latitude": 0.0,
                    "longitude": 0.0,
                    "isp": "Unknown"
                }
            
            country = match.get('country', {}).get('names', {}).get('en', 'Unknown')
            city = match.get('city', {}).get('names', {}).get('en', 'Unknown')
            region = match.get('subdivisions', [{}])[0].get('names', {}).get('en', 'Unknown')
            
            location = match.get('location', {})
            latitude = location.get('latitude', 0.0)
            longitude = location.get('longitude', 0.0)
            
            # Get ISP information (requires separate ASN database)
            isp = "Unknown"
            
            return {
                "country": country,
                "city": city,
                "region": region,
                "latitude": latitude,
                "longitude": longitude,
                "isp": isp
            }
        except Exception as e:
            logger.error(f"Geolocation lookup failed for {ip_address}: {e}")
            return {
                "country": "Unknown",
                "city": "Unknown",
                "region": "Unknown",
                "latitude": 0.0,
                "longitude": 0.0,
                "isp": "Unknown"
            }
    
    async def _detect_vpn_proxy_tor(self, ip_address: str) -> Dict[str, bool]:
        """Detect if IP is VPN, Proxy, or Tor"""
        try:
            # Check Tor first (we already have the list)
            is_tor = ip_address in self.tor_exit_nodes
            
            # Check for proxy indicators
            is_proxy = await self._check_proxy_indicators(ip_address)
            
            # Check for VPN indicators
            is_vpn = await self._check_vpn_indicators(ip_address)
            
            return {
                "is_vpn": is_vpn,
                "is_proxy": is_proxy,
                "is_tor": is_tor
            }
        except Exception as e:
            logger.error(f"VPN/Proxy/Tor detection failed: {e}")
            return {"is_vpn": False, "is_proxy": False, "is_tor": False}
    
    async def _check_proxy_indicators(self, ip_address: str) -> bool:
        """Check for proxy indicators"""
        try:
            # Check common proxy ports
            proxy_ports = [3128, 8080, 8118, 9050, 1080]
            
            for port in proxy_ports:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    result = sock.connect_ex((ip_address, port))
                    sock.close()
                    if result == 0:  # Connection successful
                        return True
                except:
                    continue
            
            # Check reverse DNS for proxy indicators
            try:
                hostname = socket.gethostbyaddr(ip_address)[0].lower()
                proxy_keywords = ['proxy', 'cache', 'gateway', 'squid']
                if any(keyword in hostname for keyword in proxy_keywords):
                    return True
            except:
                pass
            
            return False
        except Exception as e:
            logger.error(f"Proxy check failed: {e}")
            return False
    
    async def _check_vpn_indicators(self, ip_address: str) -> bool:
        """Check for VPN indicators"""
        try:
            # Check reverse DNS for VPN indicators
            try:
                hostname = socket.gethostbyaddr(ip_address)[0].lower()
                vpn_keywords = ['vpn', 'tunnel', 'private', 'secure']
                if any(keyword in hostname for keyword in vpn_keywords):
                    return True
                
                # Check against known VPN provider domains
                if any(provider in hostname for provider in self.vpn_providers):
                    return True
            except:
                pass
            
            # Additional VPN detection logic can be added here
            # (e.g., checking against commercial VPN IP ranges)
            
            return False
        except Exception as e:
            logger.error(f"VPN check failed: {e}")
            return False
    
    async def log_security_event(self, event_type: str, user_id: Optional[str], 
                                severity: str, description: str, ip_address: Optional[str] = None,
                                metadata: Optional[Dict[str, Any]] = None):
        """Log a security event"""
        try:
            await self.db.securityevent.create(
                data={
                    "eventType": event_type,
                    "userId": user_id,
                    "severity": severity,
                    "description": description,
                    "ipAddress": ip_address,
                    "metadata": metadata or {}
                }
            )
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    async def log_login_attempt(self, context: SecurityContext, is_successful: bool, 
                               failure_reason: Optional[str] = None):
        """Log a login attempt"""
        try:
            await self.db.loginattempt.create(
                data={
                    "userId": context.user_id,
                    "email": context.email or "",
                    "ipAddress": context.ip_address or "",
                    "userAgent": context.user_agent,
                    "deviceFingerprint": context.device_fingerprint,
                    "location": json.dumps(context.location) if context.location else None,
                    "country": context.location.get("country") if context.location else None,
                    "city": context.location.get("city") if context.location else None,
                    "isSuccessful": is_successful,
                    "failureReason": failure_reason,
                    "riskScore": context.risk_score,
                    "isSuspicious": context.is_suspicious
                }
            )
        except Exception as e:
            logger.error(f"Failed to log login attempt: {e}")
    
    async def update_user_risk_score(self, user_id: str, risk_score: float):
        """Update user's overall risk score"""
        try:
            await self.db.user.update(
                where={"id": user_id},
                data={"riskScore": risk_score}
            )
        except Exception as e:
            logger.error(f"Failed to update user risk score: {e}")
    
    async def lock_user_account(self, user_id: str, duration_hours: int = 24):
        """Lock user account for specified duration"""
        try:
            lock_until = datetime.now(timezone.utc) + timedelta(hours=duration_hours)
            await self.db.user.update(
                where={"id": user_id},
                data={
                    "accountLockedUntil": lock_until,
                    "failedLoginAttempts": {"increment": 1}
                }
            )
            
            await self.log_security_event(
                "ACCOUNT_LOCKED", user_id, "HIGH", 
                f"Account locked for {duration_hours} hours due to security concerns"
            )
        except Exception as e:
            logger.error(f"Failed to lock user account: {e}")
    
    async def blacklist_ip(self, ip_address: str, reason: str):
        """Add IP to blacklist"""
        try:
            await self.db.ipaddress.upsert(
                where={"ipAddress": ip_address},
                create={
                    "ipAddress": ip_address,
                    "isBlacklisted": True,
                    "reputation": "MALICIOUS"
                },
                update={
                    "isBlacklisted": True,
                    "reputation": "MALICIOUS"
                }
            )
            
            await self.log_security_event(
                "IP_BLACKLISTED", None, "HIGH", 
                f"IP {ip_address} blacklisted: {reason}", ip_address
            )
        except Exception as e:
            logger.error(f"Failed to blacklist IP: {e}")
    
    def generate_device_fingerprint(self, user_agent: str, accept_language: str = "", 
                                  accept_encoding: str = "", accept: str = "") -> str:
        """Generate device fingerprint"""
        fingerprint_data = f"{user_agent}:{accept_language}:{accept_encoding}:{accept}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]
    
    async def is_account_locked(self, user_id: str) -> bool:
        """Check if user account is locked"""
        try:
            user = await self.db.user.find_unique(
                where={"id": user_id},
                select={"accountLockedUntil": True}
            )
            
            if user and user.accountLockedUntil:
                return user.accountLockedUntil > datetime.now(timezone.utc)
            
            return False
        except Exception as e:
            logger.error(f"Failed to check account lock status: {e}")
            return False
    
    async def create_security_context(self, request_data: Dict[str, Any]) -> SecurityContext:
        """Create security context from request data"""
        context = SecurityContext(
            user_id=request_data.get("user_id"),
            email=request_data.get("email"),
            ip_address=request_data.get("ip_address"),
            user_agent=request_data.get("user_agent"),
            device_fingerprint=request_data.get("device_fingerprint")
        )
        
        # Add real location data
        if context.ip_address:
            context.location = self._get_geolocation(context.ip_address)
        
        return context 