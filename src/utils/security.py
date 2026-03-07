"""
Enhanced Security Module for Bulk Email Tool
Implements comprehensive security controls for production use
"""

import os
import json
import hashlib
import secrets
import hmac
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, cast
from dataclasses import dataclass
import uuid
from functools import wraps

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import jwt

# Try to import Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

# ============================================================================
# 1. SECRETS MANAGEMENT
# ============================================================================

class SecretsManager:
    """Secure secrets management with rotation support"""
    
    def __init__(self):
        self.master_key = os.getenv("MASTER_KEY")
        if not self.master_key:
            raise ValueError("MASTER_KEY environment variable not set. Required for encryption.")
        
        self.salt = os.getenv("ENCRYPTION_SALT", "").encode()
        if not self.salt:
            raise ValueError("ENCRYPTION_SALT environment variable not set")
        
        if len(self.salt) < 16:
            raise ValueError("ENCRYPTION_SALT must be at least 16 bytes")
    
    def _get_cipher(self) -> Fernet:
        """Derive encryption key using PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=480000,  # OWASP recommended for 2024
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
        return Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            cipher = self._get_cipher()
            encrypted = cipher.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            cipher = self._get_cipher()
            decrypted = cipher.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except InvalidToken:
            logger.error("Decryption failed: Invalid token")
            raise ValueError("Invalid encrypted data")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def hash_password(self, password: str, salt: Optional[str] = None) -> Tuple[str, str]:
        """Hash password using PBKDF2-SHA256"""
        if salt is None:
            salt = base64.b64encode(secrets.token_bytes(32)).decode()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=base64.b64decode(salt),
            iterations=480000,
        )
        hash_obj = base64.b64encode(kdf.derive(password.encode())).decode()
        return hash_obj, salt
    
    def verify_password(self, password: str, hash_obj: str, salt: str) -> bool:
        """Verify password against hash"""
        computed_hash, _ = self.hash_password(password, salt)
        return hmac.compare_digest(computed_hash, hash_obj)


# ============================================================================
# 2. RATE LIMITING & THROTTLING
# ============================================================================

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10
    cleanup_interval: int = 300  # Clean old entries every 5 minutes


class RateLimiter:
    """Token bucket rate limiter with multiple time windows"""
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.requests: Dict[str, List[datetime]] = {}
        self.blocked_until: Dict[str, datetime] = {}
        self.redis = None
        
        if REDIS_AVAILABLE and os.getenv("REDIS_URL"):
            try:
                self.redis = redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)
                logger.info("RateLimiter connected to Redis")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
    
    def is_rate_limited(self, identifier: str) -> Tuple[bool, Optional[str]]:
        """
        Check if request should be rate limited
        Returns: (is_limited, reason)
        """
        now = datetime.utcnow()
        
        # Redis Implementation
        if self.redis:
            try:
                # Check blocked key
                blocked_key = f"blocked:{identifier}"
                if self.redis.exists(blocked_key):
                    ttl = self.redis.ttl(blocked_key)
                    return True, f"Rate limited. Retry after {ttl} seconds"
                
                # Sliding window using sorted sets
                key = f"requests:{identifier}"
                now_ts = now.timestamp()
                window_start = now_ts - 60 # 1 minute window
                
                pipe = self.redis.pipeline()
                pipe.zremrangebyscore(key, 0, window_start) # Remove old
                pipe.zadd(key, {str(now_ts): now_ts}) # Add new
                pipe.zcard(key) # Count
                pipe.expire(key, 3600) # Expire set after 1 hour
                _, _, count, _ = pipe.execute()
                
                if count > self.config.requests_per_minute:
                    self.redis.setex(blocked_key, 60, "1") # Block for 1 min
                    return True, f"Rate limit exceeded: {self.config.requests_per_minute}/min"
                    
                return False, None
            except Exception as e:
                logger.error(f"Redis rate limit error: {e}")
                # Fallback to in-memory
        
        # Check if temporarily blocked
        if identifier in self.blocked_until:
            if now < self.blocked_until[identifier]:
                remaining = (self.blocked_until[identifier] - now).total_seconds()
                return True, f"Rate limited. Retry after {remaining:.0f} seconds"
            else:
                del self.blocked_until[identifier]
        
        # Initialize request list
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        # Remove old requests outside time windows
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        self.requests[identifier] = [
            t for t in self.requests[identifier] if t > hour_ago
        ]
        
        # Check minute limit
        minute_requests = [t for t in self.requests[identifier] if t > minute_ago]
        if len(minute_requests) >= self.config.requests_per_minute:
            self.blocked_until[identifier] = now + timedelta(minutes=1)
            return True, f"Rate limit exceeded: {self.config.requests_per_minute}/min"
        
        # Check hour limit
        if len(self.requests[identifier]) >= self.config.requests_per_hour:
            self.blocked_until[identifier] = now + timedelta(hours=1)
            return True, f"Rate limit exceeded: {self.config.requests_per_hour}/hour"
        
        # Check burst
        if len(minute_requests) >= self.config.burst_size:
            self.blocked_until[identifier] = now + timedelta(seconds=10)
            return True, f"Burst limit exceeded: {self.config.burst_size}/10s"
        
        # Record request
        self.requests[identifier].append(now)
        return False, None
    
    def cleanup_expired(self):
        """Remove expired rate limit records"""
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=2)
        
        # Clean up request history
        identifiers_to_remove = []
        for identifier, requests in self.requests.items():
            self.requests[identifier] = [t for t in requests if t > hour_ago]
            if not self.requests[identifier]:
                identifiers_to_remove.append(identifier)
        
        for identifier in identifiers_to_remove:
            del self.requests[identifier]
        
        # Clean up blocked entries
        for identifier in list(self.blocked_until.keys()):
            if now >= self.blocked_until[identifier]:
                del self.blocked_until[identifier]


# ============================================================================
# 3. INPUT VALIDATION
# ============================================================================

class InputValidator:
    """Validate and sanitize user inputs"""
    
    # Email validation regex (RFC 5322 simplified)
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"('\s*(OR|AND)\s*')",  # ' OR '
        r'("\s*(OR|AND)\s*")',   # " OR "
        r'(;\s*DROP)',            # ; DROP
        r'(;\s*DELETE)',          # ; DELETE
        r'(UNION\s+SELECT)',      # UNION SELECT
        r'(xp_|sp_)',             # Extended stored procedures
    ]
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        import re
        if not isinstance(email, str) or len(email) > 254:
            return False
        return bool(re.match(InputValidator.EMAIL_PATTERN, email))
    
    @staticmethod
    def validate_emails_list(emails: List[str], max_count: int = 1000) -> Tuple[bool, Optional[str]]:
        """Validate list of emails"""
        if not isinstance(emails, list):
            return False, "Emails must be a list"
        
        if len(emails) > max_count:
            return False, f"Maximum {max_count} emails allowed"
        
        if len(emails) == 0:
            return False, "At least one email required"
        
        invalid_emails = [e for e in emails if not InputValidator.validate_email(e)]
        if invalid_emails:
            return False, f"Invalid emails: {invalid_emails[:5]}"
        
        return True, None
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = 10000) -> Tuple[str, bool]:
        """Sanitize text input"""
        if not isinstance(text, str):
            return "", False
        
        # Limit length
        if len(text) > max_length:
            return "", False
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text, True
    
    @staticmethod
    def check_sql_injection(query: str) -> bool:
        """Check for SQL injection patterns"""
        import re
        query_upper = query.upper()
        for pattern in InputValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, query_upper, re.IGNORECASE):
                logger.warning(f"Potential SQL injection detected: {pattern}")
                return True
        return False
    
    @staticmethod
    def validate_json(data: str, max_size: int = 1000000) -> Tuple[Optional[Dict], Optional[str]]:
        """Safely parse JSON with size limits"""
        if not isinstance(data, str):
            return None, "Input must be string"
        
        if len(data) > max_size:
            return None, f"JSON exceeds maximum size of {max_size} bytes"
        
        try:
            parsed = json.loads(data)
            return parsed, None
        except json.JSONDecodeError as e:
            return None, f"Invalid JSON: {str(e)}"


# ============================================================================
# 4. AUTHENTICATION & AUTHORIZATION
# ============================================================================

class TokenManager:
    """JWT token management for API authentication"""
    
    def __init__(self, secret_key: Optional[str] = None, algorithm: str = "HS256"):
        self.secret_key = secret_key or os.getenv("JWT_SECRET")
        if not self.secret_key:
            raise ValueError("JWT_SECRET environment variable not set")
        self.algorithm = algorithm
        self.token_blacklist = set()
        self.redis = None
        
        if REDIS_AVAILABLE and os.getenv("REDIS_URL"):
            try:
                self.redis = redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)
            except Exception as e:
                logger.error(f"TokenManager failed to connect to Redis: {e}")
    
    def generate_token(self, user_id: str, expires_in_hours: int = 24) -> str:
        """Generate JWT token"""
        payload = {
            'user_id': user_id,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=expires_in_hours),
            'jti': str(uuid.uuid4())  # JWT ID for revocation
        }
        token = jwt.encode(payload, cast(str, self.secret_key), algorithm=self.algorithm)
        return token
    
    def verify_token(self, token: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, cast(str, self.secret_key), algorithms=[self.algorithm])
            
            # Check blacklist
            jti = payload.get('jti')
            is_revoked = False
            if self.redis:
                is_revoked = self.redis.exists(f"revoked:{jti}")
            elif jti in self.token_blacklist:
                is_revoked = True
                
            if is_revoked:
                return None, "Token has been revoked"
            
            return payload, None
        except jwt.ExpiredSignatureError:
            return None, "Token has expired"
        except jwt.InvalidTokenError as e:
            return None, f"Invalid token: {str(e)}"
    
    def revoke_token(self, token: str):
        """Revoke a token"""
        try:
            payload = jwt.decode(token, cast(str, self.secret_key), algorithms=[self.algorithm])
            jti = payload.get('jti')
            
            if self.redis:
                self.redis.setex(f"revoked:{jti}", 86400, "1")
            else:
                self.token_blacklist.add(jti)
        except:
            pass
    
    def generate_refresh_token(self, user_id: str) -> str:
        """Generate refresh token (longer expiry)"""
        return self.generate_token(user_id, expires_in_hours=7*24)


class AccessControl:
    """Role-based access control"""
    
    ROLES = {
        'admin': {'send_emails', 'view_analytics', 'manage_users', 'manage_templates', 'approve_campaigns'},
        'manager': {'send_emails', 'view_analytics', 'manage_templates', 'approve_campaigns'},
        'user': {'send_emails', 'view_analytics'},
        'viewer': {'view_analytics'},
    }
    
    @staticmethod
    def has_permission(user_role: str, required_permission: str) -> bool:
        """Check if user has required permission"""
        if user_role not in AccessControl.ROLES:
            return False
        return required_permission in AccessControl.ROLES[user_role]
    
    @staticmethod
    def require_permission(permission: str):
        """Decorator for permission checking"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, user_role: Optional[str] = None, **kwargs):
                if not user_role or not AccessControl.has_permission(user_role, permission):
                    raise PermissionError(f"User lacks required permission: {permission}")
                return func(*args, **kwargs)
            return wrapper
        return decorator


# ============================================================================
# 5. AUDIT LOGGING
# ============================================================================

class AuditLogger:
    """Comprehensive audit logging for compliance and security"""
    
    def __init__(self, log_file: str = "audit.log"):
        self.log_file = log_file
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup dedicated audit logger"""
        audit_logger = logging.getLogger('audit')
        
        if not audit_logger.handlers:
            handler = logging.FileHandler(self.log_file)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            audit_logger.addHandler(handler)
            audit_logger.setLevel(logging.INFO)
        
        return audit_logger
    
    def log_action(self, user_id: str, action: str, resource: str, 
                   status: str, details: Optional[Dict] = None):
        """Log user action for audit trail"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id,
            'action': action,
            'resource': resource,
            'status': status,
            'details': details or {}
        }
        self.logger.info(json.dumps(log_entry))
    
    def log_security_event(self, event_type: str, severity: str, 
                          details: Dict, user_id: Optional[str] = None):
        """Log security-related events"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'severity': severity,
            'user_id': user_id,
            'details': details
        }
        self.logger.warning(json.dumps(log_entry))


# ============================================================================
# 6. CSRF PROTECTION
# ============================================================================

class CSRFProtection:
    """CSRF token generation and validation"""
    
    def __init__(self):
        self.tokens: Dict[str, Dict[str, Any]] = {}
    
    def generate_token(self, session_id: str) -> str:
        """Generate CSRF token"""
        token = base64.b64encode(secrets.token_bytes(32)).decode()
        self.tokens[token] = {
            'session_id': session_id,
            'created_at': datetime.utcnow(),
            'used': False
        }
        return token
    
    def validate_token(self, token: str, session_id: str) -> Tuple[bool, Optional[str]]:
        """Validate CSRF token"""
        if token not in self.tokens:
            return False, "Invalid CSRF token"
        
        token_data = self.tokens[token]
        
        if token_data['session_id'] != session_id:
            return False, "CSRF token session mismatch"
        
        if token_data['used']:
            return False, "CSRF token already used"
        
        # Check token age (max 1 hour)
        age = datetime.utcnow() - token_data['created_at']
        if age > timedelta(hours=1):
            return False, "CSRF token expired"
        
        token_data['used'] = True
        return True, None
    
    def cleanup_old_tokens(self):
        """Remove expired tokens"""
        now = datetime.utcnow()
        expired = [
            t for t, data in self.tokens.items()
            if now - data['created_at'] > timedelta(hours=2)
        ]
        for token in expired:
            del self.tokens[token]


# ============================================================================
# 7. SECURITY HEADERS & CORS
# ============================================================================

class SecurityHeaders:
    """Generate secure HTTP headers"""
    
    @staticmethod
    def get_security_headers(include_csp: bool = True) -> Dict[str, str]:
        """Get recommended security headers"""
        headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
        }
        
        if include_csp:
            headers['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )
        
        return headers


# ============================================================================
# 8. BACKWARD COMPATIBILITY FUNCTIONS
# ============================================================================

def encrypt_data(data: str) -> str:
    """Encrypt sensitive data - backward compatible"""
    mgr = SecretsManager()
    return mgr.encrypt(data)

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data - backward compatible"""
    mgr = SecretsManager()
    return mgr.decrypt(encrypted_data)

def get_cipher():
    """Get cipher - backward compatible"""
    mgr = SecretsManager()
    return mgr._get_cipher()


# ============================================================================
# 9. INITIALIZATION & HEALTH CHECK
# ============================================================================

def initialize_security() -> Dict[str, Any]:
    """Initialize all security components"""
    try:
        secrets_mgr = SecretsManager()
        rate_limiter = RateLimiter()
        token_mgr = TokenManager()
        audit_logger = AuditLogger()
        csrf_protection = CSRFProtection()
        
        logger.info("Security module initialized successfully")
        
        return {
            'secrets': secrets_mgr,
            'rate_limiter': rate_limiter,
            'token_manager': token_mgr,
            'audit_logger': audit_logger,
            'csrf_protection': csrf_protection,
        }
    except Exception as e:
        logger.error(f"Security initialization failed: {e}")
        raise


# Global security instance
_security_instance = None

def get_security() -> Dict[str, Any]:
    """Get or initialize security components"""
    global _security_instance
    if _security_instance is None:
        _security_instance = initialize_security()
    return _security_instance
