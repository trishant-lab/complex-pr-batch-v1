"""
webhooks package
"""

from fastapi import APIRouter

from .billing_events import router as billing_events

router = APIRouter()
router.include_router(prefix="/billing", router=billing_events)
