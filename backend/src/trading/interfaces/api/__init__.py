"""API v1 router."""
from fastapi import APIRouter
from .auth import router as auth_router

# Create API v1 router
router = APIRouter(prefix="/v1")

# Include sub-routers
router.include_router(auth_router)
