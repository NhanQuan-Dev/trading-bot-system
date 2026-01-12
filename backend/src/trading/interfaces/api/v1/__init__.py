"""API v1 router."""
from fastapi import APIRouter

from .auth import router as auth_router
from .users import router as users_router
from .exchanges import router as exchanges_router
from .orders import router as orders_router

# Import new comprehensive routes
from ....presentation.controllers import (
    bots_router,
    market_data_router,
    strategies_router,
)
from ....presentation.controllers.risk.risk_controller import router as risk_router
from ....presentation.controllers.cache_controller import router as cache_router
from ....presentation.controllers.jobs_controller import router as jobs_router
from ....presentation.controllers.backtest_controller import router as backtest_router


# Create API v1 router
router = APIRouter(prefix="/api/v1")

# Include sub-routers
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(exchanges_router)
router.include_router(orders_router)

# Include new comprehensive routers
router.include_router(bots_router)
router.include_router(strategies_router)
router.include_router(market_data_router)
router.include_router(risk_router)
router.include_router(cache_router)
router.include_router(jobs_router)
router.include_router(backtest_router)
