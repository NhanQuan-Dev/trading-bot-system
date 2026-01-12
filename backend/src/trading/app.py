"""FastAPI application factory."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from jose import JWTError
import logging
import time
from typing import AsyncGenerator

from .infrastructure.persistence.database import async_engine
from .infrastructure.config.settings import get_settings
from .infrastructure.websocket.websocket_service import websocket_service
from .infrastructure.cache import cache_service, CacheMiddleware
from .infrastructure.jobs import job_service, register_default_scheduled_tasks

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown."""
    try:
        await cache_service.start()
        logger.info("Cache services started successfully")
    except Exception as e:
        logger.error(f"Error starting cache services: {e}")

    try:
        await websocket_service.start()
        logger.info("WebSocket services started successfully")
    except Exception as e:
        logger.error(f"Error starting WebSocket services: {e}")

    # Job Services
    try:
        await job_service.start()
        register_default_scheduled_tasks()
        
        # Register background job handlers
        from .infrastructure.jobs.job_worker import JobWorker
        from .infrastructure.jobs.fetch_missing_candles_job import FetchMissingCandlesJobV2
        from .infrastructure.exchange.binance_adapter import BinanceAdapter

        # Use public adapter for background fetching (empty keys for public API)
        adapter = BinanceAdapter(api_key="", api_secret="") 
        handler = FetchMissingCandlesJobV2(adapter=adapter, candle_repo=None)
        
        JobWorker.register_handler(
            'fetch_missing_candles',
            handler.execute
        )
        logger.info("Registered fetch_missing_candles handler")
        
        logger.info("Job services started successfully")
    except Exception as e:
        logger.error(f"Error starting job services: {e}")

    # Create tables if they don't exist
    from .infrastructure.persistence.database import async_engine, Base, get_db_context
    from .infrastructure.persistence import models  # Ensure models are imported
    
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")

    # Initialize Bot Manager
    from .application.services.bot_manager import init_bot_manager, get_bot_manager
    try:
        # Pass the database context (async_sessionmaker) to the manager
        from .infrastructure.persistence.database import get_db_context
        # get_db_context is context manager, but we need the factory.
        # Actually async_sessionmaker is usually provided by database module directly
        from .infrastructure.persistence.database import AsyncSessionLocal
        init_bot_manager(AsyncSessionLocal)
        logger.info("Bot Manager initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing Bot Manager: {e}")

    # Seed initial data
    from .infrastructure.persistence.seed_exchanges import seed_exchanges
    from .infrastructure.persistence.seed_users import seed_users
    from .infrastructure.persistence.seed_strategies import seed_strategies
    
    try:
        async with get_db_context() as session:
            await seed_users(session)
            # await seed_strategies(session) # User requested to disable auto-seeding
            await seed_exchanges(session)
            logger.info("Database seeded successfully")
    except Exception as e:
        logger.error(f"Error seeding database: {e}")

    yield

    # Stop Bot Manager (Graceful Shutdown)
    try:
        bot_manager = get_bot_manager()
        await bot_manager.stop_all_bots()
        logger.info("Bot Manager stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping Bot Manager: {e}")

    try:
        await websocket_service.stop()
        logger.info("WebSocket services stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping WebSocket services: {e}")
    
    try:
        await cache_service.stop()
        logger.info("Cache services stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping cache services: {e}")
    
    try:
        await job_service.stop()
        logger.info("Job services stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping job services: {e}")
    
    await async_engine.dispose()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="Trading Bot Platform API",
        description="RESTful API for automated trading bot management",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    
    # CORS Configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    
    # Cache middleware
    app.add_middleware(CacheMiddleware, cache_headers=True)
    
    # Request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        """Add unique request ID to each request."""
        import uuid
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    
    # Logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all requests."""
        start_time = time.time()
        
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "method": request.method,
                "path": request.url.path,
            }
        )
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        logger.info(
            f"Request completed: {request.method} {request.url.path} - {response.status_code} ({duration:.3f}s)",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration": duration,
            }
        )
        
        return response
    
    # Exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors and ensure payload is JSON serializable."""
        sanitized_errors = []
        for err in exc.errors():
            err_copy = dict(err)
            ctx = err_copy.get("ctx")
            if ctx:
                err_copy["ctx"] = {k: str(v) for k, v in ctx.items()}
            sanitized_errors.append(err_copy)

        body = exc.body
        if isinstance(body, Exception):
            body = str(body)

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": sanitized_errors,
                "body": body,
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(JWTError)
    async def jwt_exception_handler(request: Request, exc: JWTError):
        """Handle JWT errors."""
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "detail": f"Invalid authentication credentials: {str(exc)}",
                "request_id": getattr(request.state, "request_id", None),
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all unhandled exceptions."""
        logger.error(
            f"Unhandled exception: {str(exc)}",
            exc_info=True,
            extra={"request_id": getattr(request.state, "request_id", None)}
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "request_id": getattr(request.state, "request_id", None),
            },
        )
    
    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "environment": settings.ENVIRONMENT,
            "version": "1.0.0",
        }
    
    # Register routers
    from .interfaces.api.v1 import router as api_v1_router
    from .presentation.controllers.websocket_controller import router as websocket_router

    # Import Phase 1 & 2 Integration API routers
    import sys
    sys.path.insert(0, str(settings.BASE_DIR))
    from presentation.api.v1.connection_controller import router as connection_router
    # from presentation.api.v1.portfolio_controller import router as portfolio_router
    # from presentation.api.v1.performance_controller import router as performance_router
    # from presentation.api.v1.risk_controller import router as risk_router

    app.include_router(api_v1_router)
    app.include_router(websocket_router)
    
    # Include Phase 1 & 2 Integration APIs
    app.include_router(connection_router)  # Enabled for bot details
    # app.include_router(portfolio_router)
    # app.include_router(performance_router)
    # app.include_router(risk_router)

    return app


# Create application instance
app = create_app()
