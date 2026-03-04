from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from src.utils.security import encrypt_data, decrypt_data
import datetime
import json

Base = declarative_base()

class GoogleAccount(Base):
    __tablename__ = 'google_accounts'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    _credentials = Column(Text, nullable=False)  # Stores encrypted JSON
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    @property
    def credentials(self):
        return json.loads(decrypt_data(self._credentials))

    @credentials.setter
    def credentials(self, value):
        self._credentials = encrypt_data(json.dumps(value))

class ResendAccount(Base):
    __tablename__ = 'resend_accounts'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False) # e.g., "mvpfication.com"
    _api_key = Column(Text, nullable=False) # Encrypted
    from_email = Column(String, nullable=False) # e.g., hello@mvpfication.com
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    @property
    def api_key(self):
        return decrypt_data(self._api_key)

    @api_key.setter
    def api_key(self, value):
        self._api_key = encrypt_data(value)

class Campaign(Base):
    __tablename__ = 'campaigns'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    sheet_url = Column(String, nullable=False)
    prompt_template = Column(String, nullable=False)
    status = Column(String, default='pending')  # pending, drafting, review, sending, completed
    provider = Column(String, default='gemini') # gemini, openai, ollama
    outreach_provider = Column(String, default='gmail') # gmail, resend
    outreach_account_id = Column(Integer) # ID in either GoogleAccount or ResendAccount
    settings = Column(JSON, nullable=False)  # {daily_limit: 50, delay_seconds: 120}
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    drafts = relationship("Draft", back_populates="campaign", cascade="all, delete-orphan")

class Draft(Base):
    __tablename__ = 'drafts'
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'))
    recipient_email = Column(String, nullable=False)
    recipient_name = Column(String)
    subject = Column(String)
    body = Column(Text)
    status = Column(String, default='pending') # pending, edited, approved, sent, skipped
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    campaign = relationship("Campaign", back_populates="drafts")

class EmailLog(Base):
    __tablename__ = 'email_logs'
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'))
    account_id = Column(Integer, ForeignKey('google_accounts.id'))
    recipient = Column(String, nullable=False)
    subject = Column(String)
    body = Column(String)
    sent_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String)  # sent, failed

engine = create_engine('sqlite:///data.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
