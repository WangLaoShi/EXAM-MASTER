"""
Integration API Key authentication
"""

import hashlib
import time
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_main_db
from app.core.integration_errors import ErrorCode
from app.models.integration_models import IntegrationApiKey


API_KEY_PREFIX = "em_live_"
ALL_SCOPES = {
    "bank:read", "bank:write",
    "question:read", "question:write", "question:import",
    "resource:write",
}

_bearer = HTTPBearer(auto_error=False)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

_rate_limit_buckets: dict[str, list[float]] = {}


@dataclass
class IntegrationContext:
    api_key: IntegrationApiKey
    owner_user_id: int
    scopes: List[str]
    allowed_bank_ids: Optional[List[str]]


def hash_api_key(raw_key: str) -> str:
    payload = f"{settings.secret_key}:{raw_key}".encode()
    return hashlib.sha256(payload).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    import secrets
    import uuid

    key_id = str(uuid.uuid4())
    token = secrets.token_urlsafe(32)
    raw_key = f"{API_KEY_PREFIX}{token}"
    prefix = raw_key[:16]
    return key_id, raw_key, prefix


def _extract_raw_key(
    credentials: Optional[HTTPAuthorizationCredentials],
    header_key: Optional[str],
) -> Optional[str]:
    if header_key and header_key.startswith(API_KEY_PREFIX):
        return header_key
    if credentials and credentials.credentials.startswith(API_KEY_PREFIX):
        return credentials.credentials
    return None


def _check_rate_limit(api_key: IntegrationApiKey) -> None:
    now = time.time()
    window = 60.0
    bucket = _rate_limit_buckets.setdefault(api_key.id, [])
    bucket[:] = [t for t in bucket if now - t < window]
    if len(bucket) >= api_key.rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": ErrorCode.RATE_LIMIT,
                "message": f"请求过于频繁，限制 {api_key.rate_limit_per_minute} 次/分钟",
                "suggestion": "请降低请求频率，或联系管理员提高限额",
            },
        )
    bucket.append(now)


async def get_integration_context(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    header_key: Optional[str] = Depends(_api_key_header),
    db: Session = Depends(get_main_db),
) -> IntegrationContext:
    raw_key = _extract_raw_key(credentials, header_key)
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": ErrorCode.AUTH_MISSING,
                "message": "缺少 Integration API Key",
                "suggestion": "请在 Header 中设置 Authorization: Bearer em_live_... 或 X-API-Key",
            },
        )

    prefix = raw_key[:16]
    key_record = db.query(IntegrationApiKey).filter(
        IntegrationApiKey.key_prefix == prefix,
        IntegrationApiKey.is_active == True,
    ).first()

    if not key_record or key_record.key_hash != hash_api_key(raw_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": ErrorCode.AUTH_INVALID,
                "message": "API Key 无效或已吊销",
                "suggestion": "请在 Admin 后台检查 Key 状态，或重新申请",
            },
        )

    if key_record.expires_at and key_record.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": ErrorCode.AUTH_EXPIRED,
                "message": "API Key 已过期",
                "suggestion": "请联系管理员续期或重新申请 Key",
            },
        )

    if key_record.ip_whitelist:
        client_ip = request.client.host if request.client else None
        if client_ip not in key_record.ip_whitelist:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": ErrorCode.AUTH_IP_DENIED,
                    "message": f"当前 IP（{client_ip}）不在白名单内",
                    "suggestion": "请在 Admin 后台为该 Key 添加 IP 白名单，或从授权 IP 发起请求",
                },
            )

    _check_rate_limit(key_record)

    key_record.last_used_at = datetime.utcnow()
    db.commit()

    return IntegrationContext(
        api_key=key_record,
        owner_user_id=key_record.owner_user_id,
        scopes=key_record.scopes or [],
        allowed_bank_ids=key_record.allowed_bank_ids,
    )


def require_scopes(*required_scopes: str):
    async def _checker(ctx: IntegrationContext = Depends(get_integration_context)) -> IntegrationContext:
        for scope in required_scopes:
            if scope not in ctx.scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": ErrorCode.SCOPE_DENIED,
                        "message": f"缺少权限：{scope}",
                        "suggestion": "请在 Admin 后台为该 Key 勾选相应 scope 后重试",
                        "required_scope": scope,
                        "your_scopes": ctx.scopes,
                    },
                )
        return ctx
    return _checker


def assert_bank_access(ctx: IntegrationContext, bank_id: str, creator_id: int) -> None:
    if ctx.allowed_bank_ids is not None and len(ctx.allowed_bank_ids) > 0:
        if bank_id not in ctx.allowed_bank_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": ErrorCode.BANK_ACCESS_DENIED,
                    "message": "该 API Key 无权访问此题库",
                    "suggestion": "在 Admin 后台将该 bank_id 加入 Key 的「限定题库」列表",
                    "bank_id": bank_id,
                },
            )
    elif creator_id != ctx.owner_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": ErrorCode.BANK_ACCESS_DENIED,
                "message": "题库不属于此 Key 的归属账号",
                "suggestion": "请使用创建该题库的账号对应的 API Key",
                "bank_id": bank_id,
            },
        )
