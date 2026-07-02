"""
Integration API schemas
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.qbank_schemas_v2 import (
    QuestionBankCreate,
    QuestionBankUpdate,
    QuestionBankResponse,
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
    QuestionTypeEnum,
)


INTEGRATION_SCOPES = [
    "bank:read",
    "bank:write",
    "question:read",
    "question:write",
    "question:import",
    "resource:write",
]


class IntegrationQuestionCreate(QuestionCreate):
    external_id: Optional[str] = Field(
        None, max_length=50, description="远端系统题目 ID，用于 upsert 去重"
    )


class IntegrationQuestionUpdate(QuestionUpdate):
    external_id: Optional[str] = Field(None, max_length=50)


class IntegrationQuestionBatchRequest(BaseModel):
    questions: List[IntegrationQuestionCreate]
    upsert: bool = False


class IntegrationErrorDetail(BaseModel):
    code: str
    message: str
    row: Optional[int] = None
    external_id: Optional[str] = None
    field: Optional[str] = None
    suggestion: Optional[str] = None


class IntegrationBatchResult(BaseModel):
    success: bool
    partial: bool = False
    message: str = ""
    success_count: int
    created_count: int
    updated_count: int
    failed_count: int
    total: int = 0
    errors: List[IntegrationErrorDetail] = []
    errors_truncated: bool = False


class IntegrationImportResult(BaseModel):
    success: bool
    partial: bool = False
    message: str = ""
    bank_id: str
    total_rows: int = 0
    imported_count: int
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    errors: List[IntegrationErrorDetail] = []
    errors_truncated: bool = False
    duration_ms: Optional[int] = None
    source_files: List[str] = []


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scopes: List[str] = Field(default_factory=lambda: ["bank:write", "question:write", "question:import"])
    allowed_bank_ids: Optional[List[str]] = None
    rate_limit_per_minute: int = Field(default=120, ge=1, le=10000)
    ip_whitelist: Optional[List[str]] = None
    owner_user_id: Optional[int] = None
    expires_at: Optional[datetime] = None


class ApiKeyCreatedResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    api_key: str
    scopes: List[str]
    allowed_bank_ids: Optional[List[str]]
    expires_at: Optional[datetime]
    message: str = "请妥善保存 API Key，此密钥仅显示一次"


class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    scopes: List[str]
    allowed_bank_ids: Optional[List[str]]
    rate_limit_per_minute: int
    ip_whitelist: Optional[List[str]]
    owner_user_id: int
    is_active: bool
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: int
    api_key_id: str
    method: str
    path: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    status_code: int
    ip_address: Optional[str]
    request_summary: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
