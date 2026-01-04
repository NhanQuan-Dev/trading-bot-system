"""Register background job handlers."""

import logging
from ..infrastructure.jobs.fetch_missing_candles_job import FetchMissingCandlesJobV2

logger = logging.getLogger(__name__)


async def register_job_handlers(
    binance_adapter,
    candle_repository
):
    """
    Register all background job handlers.
    
    Call this during application startup.
    """
    # Create job handler instance
    fetch_candles_job = FetchMissingCandlesJobV2(
        adapter=binance_adapter,
        candle_repo=candle_repository
    )
    
    # Register handler
    JobWorker.register_handler(
        'fetch_missing_candles',
        fetch_candles_job.execute
    )
    
    logger.info("Registered fetch_missing_candles job handler")
    
    # Start job worker if not already running
    if not job_worker._running:
        await job_worker.start()
        logger.info("Job worker started")
