"""
Integration API models (Main Database)
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Text
from datetime import datetime
from app.core.database import BaseMain


class IntegrationApiKey(BaseMain):
    __tablename__ = "integration_api_keys"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    key_prefix = Column(String(20), nullable=False, index=True)
    key_hash = Column(String(64), nullable=False)
    scopes = Column(JSON, nullable=False, default=list)
    allowed_bank_ids = Column(JSON, nullable=True)
    rate_limit_per_minute = Column(Integer, default=120, nullable=False)
    ip_whitelist = Column(JSON, nullable=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IntegrationAuditLog(BaseMain):
    __tablename__ = "integration_audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    api_key_id = Column(String(36), ForeignKey("integration_api_keys.id"), nullable=False, index=True)
    method = Column(String(10), nullable=False)
    path = Column(String(255), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(50), nullable=True)
    status_code = Column(Integer, nullable=False)
    ip_address = Column(String(45), nullable=True)
    request_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
