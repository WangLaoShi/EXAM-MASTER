"""
Integration API router
"""

from fastapi import APIRouter
from app.api.integration.banks import router as banks_router
from app.api.integration.questions import router as questions_router
from app.api.integration.import_export import router as import_router
from app.api.integration.meta import router as meta_router

router = APIRouter()

router.include_router(meta_router)
router.include_router(banks_router)
router.include_router(questions_router)
router.include_router(import_router)
