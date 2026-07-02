"""
Integration API - Meta endpoints
"""

from fastapi import APIRouter, Depends
from app.core.integration_auth import IntegrationContext, get_integration_context

router = APIRouter(tags=["Integration - Meta"])


@router.get("/health")
async def integration_health(ctx: IntegrationContext = Depends(get_integration_context)):
    """Verify API Key and return key metadata"""
    return {
        "status": "ok",
        "key_id": ctx.api_key.id,
        "key_name": ctx.api_key.name,
        "scopes": ctx.scopes,
        "owner_user_id": ctx.owner_user_id,
        "allowed_bank_ids": ctx.allowed_bank_ids,
    }
