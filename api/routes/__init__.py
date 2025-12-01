from fastapi import APIRouter
from .upload import router as upload_router
from .simulation import router as simulation_router
from .auth import router as auth_router

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(upload_router, tags=["upload"])
api_router.include_router(simulation_router, tags=["simulation"])

__all__ = ["api_router"]

