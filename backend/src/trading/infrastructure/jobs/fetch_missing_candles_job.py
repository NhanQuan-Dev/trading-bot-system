"""Background job to fetch missing candle data in chunks - Sequential Job Approach."""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ...domain.market_data import Candle, CandleInterval
from ..exchange.binance_adapter import BinanceAdapter
from ..persistence.repositories.market_data_repository import CandleRepository

logger = logging.getLogger(__name__)


class FetchMissingCandlesJobV2:
    """
    Background job to fetch missing candle data from exchange.
    
    NEW APPROACH: Sequential Chunked Jobs
    - Each job fetches ONE chunk (batch_size candles)
    - After saving chunk, queues the NEXT chunk job
    - Continues until all data is fetched
    - No single job runs longer than ~30s
    """
    
    # Class constant for batch size - Binance allows max 1500 per request
    BATCH_SIZE = 1500
    
    def __init__(
        self,
        adapter: BinanceAdapter,
        candle_repo: CandleRepository,
        batch_size: int = 1500  # Binance max is 1500
    ):
        self.adapter = adapter
        self.candle_repo = candle_repo
        self.batch_size = batch_size or self.BATCH_SIZE
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the job to fetch ONE CHUNK of candles, then queue next chunk if needed.
        
        Params:
            symbol: Trading pair
            interval: Candle interval
            chunk_start: Start time for THIS chunk
            chunk_end: End time for THIS chunk  
            total_end: Overall end time (for knowing when we're done)
            chunk_number: Which chunk this is (1, 2, 3...)
            job_id: Unique job ID
        """
        from ..persistence.database import get_db_context
        from ..persistence.repositories.market_data_repository import CandleRepository
        from .job_queue import job_queue
        
        job_id = params.get('job_id', 'unknown')
        
        try:
            symbol = params['symbol']
            interval_str = params['interval']
            
            # NEW: Chunk-based parameters
            # For backward compatibility, support both old (start_time/end_time) and new (chunk_start/chunk_end)
            if 'chunk_start' in params:
                chunk_start = self._parse_datetime(params['chunk_start'])
                chunk_end = self._parse_datetime(params['chunk_end'])
                total_end = self._parse_datetime(params['total_end'])
                chunk_number = params.get('chunk_number', 1)
            else:
                # Legacy mode: old-style params - convert to chunked
                chunk_start = self._parse_datetime(params['start_time'])
                total_end = self._parse_datetime(params['end_time'])
                chunk_number = 1
                
                # Calculate chunk_end based on interval and batch size
                interval_minutes = self._get_interval_minutes(interval_str)
                chunk_duration = timedelta(minutes=interval_minutes * self.batch_size)
                chunk_end = min(chunk_start + chunk_duration, total_end)
            
            interval = CandleInterval(interval_str)
            
            print(f"DEBUG [FetchJob]: ========== CHUNK JOB #{chunk_number} STARTED ==========")
            print(f"DEBUG [FetchJob]: Symbol: {symbol}, Interval: {interval_str}")
            print(f"DEBUG [FetchJob]: Chunk range: {chunk_start} to {chunk_end}")
            print(f"DEBUG [FetchJob]: Total end: {total_end}")
            
            logger.info(
                f"[Job {job_id}] Chunk #{chunk_number}: Fetching {symbol} {interval_str} "
                f"from {chunk_start} to {chunk_end}"
            )
            
            fetched_count = 0
            
            # Create a FRESH session for this job execution
            async with get_db_context() as session:
                repo = CandleRepository(session)
                
                try:
                    # Fetch from exchange
                    start_ts = int(chunk_start.timestamp() * 1000)
                    end_ts = int(chunk_end.timestamp() * 1000)
                    
                    raw_klines = await self.adapter.get_klines(
                        symbol=symbol,
                        interval=interval_str,
                        start_time=start_ts,
                        end_time=end_ts,
                        limit=self.batch_size
                    )
                    
                    print(f"DEBUG [FetchJob]: Received {len(raw_klines)} klines from exchange")
                    
                    # Convert to domain objects
                    candles = []
                    for k in raw_klines:
                        candle = Candle(
                            symbol=symbol,
                            interval=interval,
                            open_time=datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc),
                            close_time=datetime.fromtimestamp(k[6] / 1000, tz=timezone.utc),
                            open_price=Decimal(str(k[1])),
                            high_price=Decimal(str(k[2])),
                            low_price=Decimal(str(k[3])),
                            close_price=Decimal(str(k[4])),
                            volume=Decimal(str(k[5])),
                            quote_volume=Decimal(str(k[7])),
                            trade_count=k[8]
                        )
                        candles.append(candle)
                    
                    # Save to database
                    if candles:
                        await repo.save_batch(candles)
                        fetched_count = len(candles)
                        
                        print(f"DEBUG [FetchJob]: Saved {fetched_count} candles to DB")
                        logger.info(
                            f"[Job {job_id}] Chunk #{chunk_number}: "
                            f"Fetched and saved {fetched_count} candles"
                        )
                    
                except Exception as chunk_error:
                    print(f"DEBUG [FetchJob]: !!! CHUNK ERROR: {str(chunk_error)}")
                    logger.error(
                        f"[Job {job_id}] Chunk #{chunk_number} failed: {str(chunk_error)}"
                    )
                    return {
                        'status': 'failed',
                        'error': str(chunk_error),
                        'chunk_number': chunk_number
                    }
            
            # Check if more chunks needed
            # Use the actual last candle time if available, otherwise use planned chunk_end
            if candles:
                actual_end = candles[-1].close_time
            else:
                actual_end = chunk_end
            
            more_chunks_needed = actual_end < total_end
            
            # Check if we're in parallel mode (all jobs already queued)
            parallel_mode = params.get('parallel_mode', False)
            total_chunks = params.get('total_chunks', 0)
            
            if parallel_mode:
                # In parallel mode, don't queue next job - it's already queued
                print(f"DEBUG [FetchJob]: <<< CHUNK #{chunk_number}/{total_chunks} DONE (PARALLEL MODE)")
                
                return {
                    'status': 'completed',
                    'candles_fetched': fetched_count,
                    'chunk_number': chunk_number,
                    'total_chunks': total_chunks,
                    'parallel_mode': True
                }
            
            # Sequential mode - queue next job if needed
            if more_chunks_needed:
                # Calculate next chunk boundaries
                interval_minutes = self._get_interval_minutes(interval_str)
                chunk_duration = timedelta(minutes=interval_minutes * self.batch_size)
                
                next_chunk_start = actual_end  # Start from where we left off
                next_chunk_end = min(next_chunk_start + chunk_duration, total_end)
                
                print(f"DEBUG [FetchJob]: More data needed. Queuing chunk #{chunk_number + 1}")
                print(f"DEBUG [FetchJob]: Next range: {next_chunk_start} to {next_chunk_end}")
                
                # Queue next chunk job
                try:
                    next_job_id = await job_queue.enqueue(
                        name='fetch_missing_candles',
                        args={
                            'job_id': f"{job_id}-chunk{chunk_number + 1}",
                            'symbol': symbol,
                            'interval': interval_str,
                            'chunk_start': next_chunk_start.isoformat(),
                            'chunk_end': next_chunk_end.isoformat(),
                            'total_end': total_end.isoformat(),
                            'chunk_number': chunk_number + 1
                        }
                    )
                    
                    print(f"DEBUG [FetchJob]: <<< CHUNK #{chunk_number} DONE - Next job queued: {next_job_id}")
                    logger.info(f"[Job {job_id}] Queued next chunk job: {next_job_id}")
                    
                    return {
                        'status': 'chunk_completed',
                        'candles_fetched': fetched_count,
                        'chunk_number': chunk_number,
                        'next_chunk_queued': True,
                        'next_job_id': next_job_id
                    }
                    
                except Exception as queue_error:
                    print(f"DEBUG [FetchJob]: !!! FAILED to queue next chunk: {str(queue_error)}")
                    logger.error(f"[Job {job_id}] Failed to queue next chunk: {str(queue_error)}")
                    # Still return success for this chunk, but note the queue failure
                    return {
                        'status': 'chunk_completed',
                        'candles_fetched': fetched_count,
                        'chunk_number': chunk_number,
                        'next_chunk_queued': False,
                        'queue_error': str(queue_error)
                    }
            else:
                # All data fetched!
                print(f"DEBUG [FetchJob]: ========== ALL CHUNKS COMPLETE ==========")
                print(f"DEBUG [FetchJob]: Total chunks: {chunk_number}, Last chunk fetched: {fetched_count}")
                
                logger.info(
                    f"[Job {job_id}] All data fetched! "
                    f"Final chunk #{chunk_number} complete with {fetched_count} candles"
                )
                
                return {
                    'status': 'completed',
                    'candles_fetched': fetched_count,
                    'chunk_number': chunk_number,
                    'all_chunks_done': True
                }
            
        except Exception as e:
            print(f"DEBUG [FetchJob]: !!! JOB FAILED: {str(e)}")
            logger.error(f"[Job {job_id}] Failed: {str(e)}", exc_info=True)
            return {
                'status': 'failed',
                'error': str(e)
            }
    
    def _get_interval_minutes(self, interval_str: str) -> int:
        """Get interval duration in minutes."""
        return {
            '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '2h': 120, '4h': 240, '6h': 360,
            '8h': 480, '12h': 720, '1d': 1440, '3d': 4320,
            '1w': 10080, '1M': 43200
        }.get(interval_str, 60)
    
    def _parse_datetime(self, dt: Any) -> datetime:
        """Parse datetime from string or return as-is if already datetime."""
        if isinstance(dt, str):
            try:
                return datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except:
                return datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
        return dt


# Factory function to create handler
async def create_fetch_missing_candles_handler(
    adapter: BinanceAdapter,
    candle_repo: CandleRepository
) -> FetchMissingCandlesJobV2:
    """Create and return a FetchMissingCandlesJob instance."""
    return FetchMissingCandlesJobV2(adapter=adapter, candle_repo=candle_repo)

