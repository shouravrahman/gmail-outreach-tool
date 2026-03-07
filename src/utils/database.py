"""
Enhanced Database Module with PostgreSQL Support & Legacy SQLAlchemy Models
Features: Connection pooling, encryption at rest, transaction support, backups
Also maintains backward compatibility with existing SQLAlchemy models
Supports NeonDB (PostgreSQL) and SQLite fallback
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple, cast
from contextlib import contextmanager
from dataclasses import dataclass
import threading
import uuid

# Configure logging FIRST before any conditional imports
logger = logging.getLogger(__name__)

from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import sqlalchemy as sa

# Try to import PostgreSQL driver (optional)
try:
    import psycopg2  # type: ignore
    from psycopg2 import pool, sql  # type: ignore
    PSYCOPG2_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    PSYCOPG2_AVAILABLE = False
    logger.debug(f"PostgreSQL driver not available: {type(e).__name__}")

from src.utils.security import encrypt_data, decrypt_data, SecretsManager

# ============================================================================
# DATABASE CONNECTION CONFIG (NeonDB or SQLite)
# ============================================================================

def get_database_url() -> str:
    """
    Get database URL from environment variables.
    Priority:
    1. DATABASE_URL (NeonDB/PostgreSQL from Streamlit secrets or environment)
    2. NEON_DATABASE_URL (Alternative NeonDB variable)
    3. Fallback to SQLite for local development
    """
    # Try NeonDB first (set in Streamlit Cloud secrets)
    db_url = os.getenv('DATABASE_URL') or os.getenv('NEON_DATABASE_URL')
    
    if db_url:
        # Convert postgres:// to postgresql:// for SQLAlchemy 2.0+
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        logger.info(f"Using PostgreSQL database: {db_url.split('@')[1] if '@' in db_url else 'NeonDB'}")
        return db_url
    
    # Fallback to SQLite for local development
    logger.warning("No DATABASE_URL found. Using SQLite for local development.")
    return 'sqlite:///data.db'

logger = logging.getLogger(__name__)

# ============================================================================
# SQLALCHEMY MODELS (LEGACY - BACKWARD COMPATIBILITY)
# ============================================================================

Base = declarative_base()

class GoogleAccount(Base):
    __tablename__ = 'google_accounts'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    _credentials = Column(Text, nullable=False)  # Stores encrypted JSON
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def credentials(self):
        return json.loads(decrypt_data(cast(str, self._credentials)))

    @credentials.setter
    def credentials(self, value):
        self._credentials = encrypt_data(json.dumps(value))

class ResendAccount(Base):
    __tablename__ = 'resend_accounts'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    _api_key = Column(Text, nullable=False)  # Encrypted
    from_email = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def api_key(self):
        return decrypt_data(cast(str, self._api_key))

    @api_key.setter
    def api_key(self, value):
        self._api_key = encrypt_data(value)

class Campaign(Base):
    __tablename__ = 'campaigns'
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey('users.id')) # Added for multi-tenancy
    name = Column(String, nullable=False)
    sheet_url = Column(String, nullable=False)
    prompt_template = Column(String, nullable=False)
    status = Column(String, default='pending')  # pending, drafting, review, sending, completed
    provider = Column(String, default='gemini')
    outreach_provider = Column(String, default='gmail')
    outreach_account_id = Column(Integer)
    settings = Column(JSON, nullable=False)  # {daily_limit: 50, delay_seconds: 120}
    created_at = Column(DateTime, default=datetime.utcnow)
    
    drafts = relationship("Draft", back_populates="campaign", cascade="all, delete-orphan")

class Draft(Base):
    __tablename__ = 'drafts'
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'))
    recipient_email = Column(String, nullable=False)
    recipient_name = Column(String)
    subject = Column(String)
    body = Column(Text)
    status = Column(String, default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    campaign = relationship("Campaign", back_populates="drafts")

class EmailLog(Base):
    __tablename__ = 'email_logs'
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'))
    account_id = Column(Integer, ForeignKey('google_accounts.id'))
    recipient = Column(String, nullable=False)
    subject = Column(String)
    body = Column(String)
    sent_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String)  # sent, failed

# ============================================================================
# ENHANCED DATABASE MODELS
# ============================================================================

class User(Base):
    """User model for enhanced authentication"""
    __tablename__ = 'users'
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    password_salt = Column(String, nullable=False)
    role = Column(String, default='user')
    email_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)

class Template(Base):
    """Email template model"""
    __tablename__ = 'templates'
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'))
    name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    html_content = Column(Text, nullable=False)
    plain_text_content = Column(Text)
    variables = Column(String)  # JSON
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Recipient(Base):
    """Recipient model for campaign recipients"""
    __tablename__ = 'recipients'
    
    id = Column(String, primary_key=True)
    campaign_id = Column(String, ForeignKey('campaigns.id'))
    email = Column(String, nullable=False)
    name = Column(String)
    custom_data = Column(String)  # JSON
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    """Audit log model"""
    __tablename__ = 'audit_logs'
    
    id = Column(String, primary_key=True)
    user_id = Column(String)
    action = Column(String, nullable=False)
    resource_type = Column(String)
    resource_id = Column(String)
    old_values = Column(String)  # JSON
    new_values = Column(String)  # JSON
    status = Column(String)
    ip_address = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

# ============================================================================
# DATABASE CONFIGURATION & MANAGER
# ============================================================================

@dataclass
class DatabaseConfig:
    """Database configuration"""
    db_type: str = "sqlite"  # "sqlite" or "postgresql"
    sqlite_path: str = "bulk_email.db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = ""
    postgres_password: str = ""
    postgres_database: str = "bulk_email"
    pool_size: int = 5
    max_overflow: int = 10
    echo_sql: bool = False

# Initialize SQLAlchemy engine with NeonDB or SQLite fallback
logger = logging.getLogger(__name__)
DATABASE_URL = get_database_url()

if 'postgresql' in DATABASE_URL:
    # PostgreSQL connection with connection pooling
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Test connections before using
        echo=False
    )
else:
    # SQLite fallback for local development
    engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False}, echo=False)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# ========================================================================
# USER MANAGEMENT FUNCTIONS
# ========================================================================

def create_user(user_id: str, email: str, password_hash: str, 
               password_salt: str, role: str = "user") -> bool:
    """Create new user"""
    session = Session()
    try:
        user = User(
            id=user_id,
            email=email,
            password_hash=password_hash,
            password_salt=password_salt,
            role=role
        )
        session.add(user)
        session.commit()
        logger.info(f"User created: {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user by email"""
    session = Session()
    try:
        user = session.query(User).filter(User.email == email).first()
        if not user:
            return None
        return {
            'id': user.id,
            'email': user.email,
            'password_hash': user.password_hash,
            'password_salt': user.password_salt,
            'role': user.role
        }
    except Exception as e:
        logger.error(f"Failed to get user by email: {e}")
        return None
    finally:
        session.close()

def update_user_last_login(user_id: str) -> bool:
    """Update user's last login timestamp"""
    session = Session()
    try:
        session.query(User).filter(User.id == user_id).update({'last_login': datetime.utcnow()})
        session.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to update last login: {e}")
        session.rollback()
        return False
    finally:
        session.close()

# ========================================================================
# CAMPAIGN MANAGEMENT FUNCTIONS
# ========================================================================

def create_campaign(campaign_data: Dict) -> str:
    """Create new campaign."""
    session = Session()
    try:
        campaign = Campaign(
            user_id=campaign_data.get('user_id'),
            name=campaign_data['name'],
            sheet_url=campaign_data.get('sheet_url', ''),
            prompt_template=campaign_data.get('prompt_template', ''),
            status=campaign_data.get('status', 'pending'),
            settings=campaign_data.get('settings', {})
        )
        session.add(campaign)
        session.commit()
        campaign_id = campaign.id # Get the auto-generated ID
        logger.info(f"Campaign created: {campaign_id}")
        return str(campaign_id) # Return as string to be safe
    except Exception as e:
        logger.error(f"Failed to create campaign: {e}")
        session.rollback()
        raise
    finally:
        session.close()

def get_user_campaigns(user_id: str, limit: int = 50) -> List[Dict]:
    """Get campaigns for a user"""
    session = Session()
    try:
        campaigns = session.query(Campaign).filter(Campaign.user_id == user_id).order_by(Campaign.created_at.desc()).limit(limit).all()
        return [{'id': c.id, 'name': c.name, 'status': c.status} for c in campaigns]
    except Exception as e:
        logger.error(f"Failed to list campaigns: {e}")
        return []
    finally:
        session.close()

def approve_campaign(campaign_id: str, approver_id: str) -> bool:
    """Approve a campaign"""
    session = Session()
    try:
        session.query(Campaign).filter(Campaign.id == campaign_id).update({'status': 'approved'})
        session.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to update campaign status: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def get_campaign_stats(campaign_id: str) -> Dict:
    """Get campaign statistics"""
    session = Session()
    try:
        logs = session.query(EmailLog).filter(EmailLog.campaign_id == campaign_id).all()
        total = len(logs)
        sent = sum(1 for l in logs if l.status == 'sent')
        failed = sum(1 for l in logs if l.status == 'failed')
        return {'total': total, 'sent': sent, 'failed': failed, 'opened': 0, 'clicked': 0}
    except Exception as e:
        logger.error(f"Failed to get campaign stats: {e}")
        return {}
    finally:
        session.close()

# ========================================================================
# AUDIT LOGGING FUNCTIONS
# ========================================================================

def get_audit_logs(user_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
    """Get audit logs"""
    session = Session()
    try:
        query = session.query(AuditLog)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
        return [{'id': l.id, 'user_id': l.user_id, 'action': l.action, 'created_at': l.created_at} for l in logs]
    except Exception as e:
        logger.error(f"Failed to get audit logs: {e}")
        return []
    finally:
        session.close()
