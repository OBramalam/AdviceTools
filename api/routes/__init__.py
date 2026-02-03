from fastapi import APIRouter
from .upload import router as upload_router
from .simulation import router as simulation_router
from .auth import router as auth_router
from .financial_plan import router as financial_plan_router
from .cashflow import router as cashflow_router
from .portfolio import router as portfolio_router
from .chat import router as chat_router
from .adviser_config import router as adviser_config_router

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(upload_router, tags=["upload"])
api_router.include_router(simulation_router, tags=["simulation"])
api_router.include_router(financial_plan_router, prefix="/financial-plans", tags=["financial-plans"])
api_router.include_router(cashflow_router, prefix="/cashflows", tags=["cashflows"])
api_router.include_router(portfolio_router, prefix="/portfolios", tags=["portfolios"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(adviser_config_router, prefix="/adviser-configs", tags=["adviser-configs"])

__all__ = ["api_router"]

