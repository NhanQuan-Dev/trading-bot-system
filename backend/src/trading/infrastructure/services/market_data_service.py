"""Market data service implementation."""
import logging
import uuid
from typing import List, Optional, Dict, Any, Tuple, Callable
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ..jobs.job_queue import job_queue

from ...domain.market_data import Candle, CandleInterval, StreamStatus
from ...domain.market_data.gap_detector import GapDetector, TimeRange
from ..persistence.repositories.market_data_repository import (
    CandleRepository,
    MarketMetadataRepository
)
from ..persistence.models.market_data_models import MarketMetadataModel
from ..exchange.exchange_gateway import ExchangeGateway

logger = logging.getLogger(__name__)

class MarketDataService:
    """Service to fetch and manage market data."""
    
    def __init__(
        self,
        exchange_adapter: ExchangeGateway,
        candle_repository: CandleRepository,
        metadata_repository: MarketMetadataRepository,
        gap_detector: GapDetector
    ):
        self.adapter = exchange_adapter
        self.candle_repo = candle_repository
        self.metadata_repo = metadata_repository
        self.gap_detector = gap_detector
    
    async def get_historical_candles(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        limit: Optional[int] = None,  # CRITICAL: No default - callers must be explicit
        repair: bool = False,
        wait_for_data: bool = False,  # NEW: Wait for data to be fetched before returning
        max_wait_seconds: int = 600,  # NEW: Max wait time (10 mins default)
        poll_interval_seconds: int = 5,  # NEW: How often to check for data
        progress_callback: Optional[Callable[[int, str], None]] = None,  # NEW: Progress callback (percent, message)
    ) -> List[Dict[str, Any]]:
        """Fetch historical candles as dicts (for backward compatibility)."""
        domain_candles = await self.get_historical_candles_domain(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            repair=repair,
            wait_for_data=wait_for_data,
            max_wait_seconds=max_wait_seconds,
            poll_interval_seconds=poll_interval_seconds,
            progress_callback=progress_callback,
        )
        return [self._candle_to_dict(c) for c in domain_candles]

    async def get_historical_candles_domain(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        limit: Optional[int] = None,  # CRITICAL: No default - callers must be explicit
        repair: bool = False,
        wait_for_data: bool = False,  # NEW: Wait for data to be fetched before returning
        max_wait_seconds: int = 600,  # NEW: Max wait time (10 mins default)
        poll_interval_seconds: int = 5,  # NEW: How often to check for data
        progress_callback: Optional[Callable[[int, str], None]] = None,  # NEW: Progress callback (percent, message)
    ) -> List[Candle]:
        """Fetch historical candles with auto-repair for missing data.
        
        Implements Use Case 1 & 2 from candlechartreq.md:
        - Validates against exchange earliest supported time
        - Auto-adjusts start_date if before earliest availability
        - Auto-fetches missing data gaps from exchange when repair=True
        
        Args:
            wait_for_data: If True and repair=True, will poll DB until data is available
                           instead of returning immediately with empty data.
            max_wait_seconds: Maximum time to wait for data (default 10 mins)
            poll_interval_seconds: How often to check DB for new data (default 5s)
            progress_callback: Optional async callback function(percent: int, message: str) 
                              called during data fetching to report progress
        """
        # Normalize symbol (BTC/USDT or BTC-USDT -> BTCUSDT)
        normalized_symbol = symbol.replace("/", "").replace("-", "")

        # Normalize datetimes to Aware UTC
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
          # 2. Parse interval
        interval = CandleInterval(timeframe)
        
        # USE CASE 1 & 2: Validate against earliest supported time
        # Binance BTC data starts from ~2017-08-17 for spot, 2019-09-08 for futures
        # For safety, use 2018-01-01 as earliest for all symbols
        EARLIEST_SUPPORTED_TIME = datetime(2018, 1, 1, tzinfo=timezone.utc)
        
        effective_start_date = start_date
        adjusted = False
        
        if start_date < EARLIEST_SUPPORTED_TIME:
            logger.warning(
                f"Requested start_date {start_date} is before earliest supported time {EARLIEST_SUPPORTED_TIME}. "
                f"Adjusting to {EARLIEST_SUPPORTED_TIME}"
            )
            effective_start_date = EARLIEST_SUPPORTED_TIME
            adjusted = True
        
        # Validate effective range is valid
        if effective_start_date >= end_date:
            logger.error(f"Effective start_date {effective_start_date} >= end_date {end_date}. No data available.")
            return []  # NO_DATA_AVAILABLE
        
        # TODO: Get or create metadata
        metadata = await self.metadata_repo.get(
            exchange="BINANCE", 
            symbol=normalized_symbol,
            timeframe=timeframe
        )
        print(f"DEBUG: Metadata found: {metadata}")
        if metadata:
             print(f"DEBUG: Earliest in DB: {metadata.earliest_available_time}")

        if not metadata:
            # First time seeing this pair/tf
            logger.info(f"Initializing metadata for {symbol} {timeframe}")
            earliest_ts = await self.adapter.get_earliest_valid_timestamp(normalized_symbol, timeframe)
            earliest_time = datetime.fromtimestamp(earliest_ts / 1000, tz=timezone.utc) if earliest_ts > 0 else None
            
            metadata = MarketMetadataModel(
                exchange="BINANCE",
                symbol=normalized_symbol,
                timeframe=timeframe,
                earliest_available_time=earliest_time,
                status="EMPTY"
            )
            await self.metadata_repo.save(metadata)
            
        # 2. Adjust Start Time based on availability
        if metadata.earliest_available_time and start_date < metadata.earliest_available_time:
            print(f"DEBUG: Adjusting start {start_date} to {metadata.earliest_available_time}")
            logger.warning(f"Requested start {start_date} is before earliest available {metadata.earliest_available_time}")
            
        # 3. Fetch from DB (use effective_start_date)
        print(f"DEBUG: Fetching from DB: start={effective_start_date}, end={end_date}")
        db_candles = await self.candle_repo.find_by_symbol_and_interval(
            symbol=normalized_symbol,
            interval=interval,
            start_time=effective_start_date,  # USE CASE 2: Use adjusted start time
            end_time=end_date,
            limit=limit  # CRITICAL: Pass limit to repository
        )
        
        # CRITICAL FIX: Repository returns DESC (Newest First), but:
        # 1. GapDetector expects ASC (Oldest First)
        # 2. BacktestEngine expects ASC (Oldest First)
        # We must sort ascending here.
        db_candles.sort(key=lambda c: c.open_time)

        print(f"DEBUG: DB candles found: {len(db_candles)}. Effective start: {effective_start_date}, End: {end_date}")
        
        # 4. Detect Gaps (use effective_start_date)
        gaps = self.gap_detector.detect_gaps(
            candles=db_candles,
            start_time=effective_start_date,  # USE CASE 4: Only detect fetchable gaps
            end_time=end_date,
            interval=interval
        )
        
        if not gaps:
            print(f"DEBUG: No gaps detected. Repair={repair}")
            return db_candles
            
        print(f"DEBUG: Detected {len(gaps)} gaps for {symbol}. Repair={repair}")
        logger.info(f"Detected {len(gaps)} gaps for {symbol}. Repair={repair}")
        
        # 5. Repair if needed
        if repair:
            print(f"DEBUG: Repair requested. Gaps detected: {len(gaps)}")
            logger.info(f"Repair requested. Gaps detected: {len(gaps)}")
            
        if repair and gaps:
            # Queue background jobs to fetch missing data
            # NEW: PARALLEL approach - queue ALL chunks at once, WorkerPool handles concurrency
            base_job_id = str(uuid.uuid4())
            
            # Calculate chunk boundaries
            gap_start = gaps[0].start
            gap_end = gaps[-1].end
            
            # Calculate chunk duration based on interval and batch size (1500 candles - Binance max)
            batch_size = 1500
            interval_minutes = {
                '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
                '1h': 60, '2h': 120, '4h': 240, '6h': 360,
                '8h': 480, '12h': 720, '1d': 1440, '3d': 4320,
                '1w': 10080, '1M': 43200
            }.get(interval.value, 60)
            
            chunk_duration = timedelta(minutes=interval_minutes * batch_size)
            
            # Calculate ALL chunks upfront
            chunks = []
            current_start = gap_start
            chunk_number = 1
            while current_start < gap_end:
                current_end = min(current_start + chunk_duration, gap_end)
                chunks.append({
                    'chunk_number': chunk_number,
                    'chunk_start': current_start,
                    'chunk_end': current_end
                })
                current_start = current_end
                chunk_number += 1
            
            total_chunks = len(chunks)
            
            print(f"DEBUG [MarketDataService]: ========== QUEUING ALL JOBS (PARALLEL) ==========")
            print(f"DEBUG [MarketDataService]: Symbol: {normalized_symbol}, Interval: {interval.value}")
            print(f"DEBUG [MarketDataService]: Gap range: {gap_start} to {gap_end}")
            print(f"DEBUG [MarketDataService]: Total chunks to queue: {total_chunks}")
            
            # Queue ALL jobs at once
            jobs_queued = 0
            for chunk in chunks:
                job_params = {
                    'job_id': f"{base_job_id}-chunk{chunk['chunk_number']}",
                    'symbol': normalized_symbol,
                    'interval': interval.value,
                    'chunk_start': chunk['chunk_start'].isoformat(),
                    'chunk_end': chunk['chunk_end'].isoformat(),
                    'total_end': gap_end.isoformat(),
                    'chunk_number': chunk['chunk_number'],
                    'total_chunks': total_chunks,
                    'parallel_mode': True  # Flag to skip queueing next job
                }
                
                try:
                    await job_queue.enqueue(
                        name='fetch_missing_candles',
                        args=job_params
                    )
                    jobs_queued += 1
                except Exception as e:
                    print(f"DEBUG [MarketDataService]: !!! Failed to queue chunk {chunk['chunk_number']}: {str(e)}")
                    logger.error(f"Failed to queue chunk {chunk['chunk_number']}: {str(e)}")
            
            print(f"DEBUG [MarketDataService]: >>> Queued {jobs_queued}/{total_chunks} jobs for PARALLEL execution")
            logger.info(f"Queued {jobs_queued} parallel chunk jobs for {symbol}")
            
            # NEW: If wait_for_data is enabled, poll DB until data is available
            if wait_for_data:
                import asyncio
                
                print(f"DEBUG [MarketDataService]: ========== STARTING POLLING LOOP ==========")
                print(f"DEBUG [MarketDataService]: Max wait: {max_wait_seconds}s, Poll interval: {poll_interval_seconds}s")
                logger.info(f"wait_for_data enabled. Polling DB every {poll_interval_seconds}s for up to {max_wait_seconds}s")
                
                # Initial callback - starting data fetch
                if progress_callback:
                    try:
                        await progress_callback(0, f"Fetching data for {symbol}...")
                    except Exception as cb_err:
                        logger.warning(f"Progress callback error: {cb_err}")
                
                elapsed = 0
                last_count = len(db_candles)
                # Calculate initial total gap duration for granular progress
                def get_total_duration(g_list):
                    return sum((g.end - g.start).total_seconds() for g in g_list)
                
                initial_gap_seconds = get_total_duration(gaps)
                
                while elapsed < max_wait_seconds:
                    await asyncio.sleep(poll_interval_seconds)
                    elapsed += poll_interval_seconds
                    
                    # Re-fetch from DB to check if data has been populated
                    db_candles = await self.candle_repo.find_by_symbol_and_interval(
                        symbol=normalized_symbol,
                        interval=interval,
                        start_time=effective_start_date,
                        end_time=end_date,
                        limit=limit
                    )
                    db_candles.sort(key=lambda c: c.open_time)
                    
                    current_count = len(db_candles)
                    
                    # Re-detect gaps
                    new_gaps = self.gap_detector.detect_gaps(
                        candles=db_candles,
                        start_time=effective_start_date,
                        end_time=end_date,
                        interval=interval
                    )
                    
                    remaining_gaps = len(new_gaps)
                    
                    # DEBUG: Log each poll iteration
                    print(f"DEBUG [MarketDataService]: Poll [{elapsed}s/{max_wait_seconds}s] - Candles: {current_count}, Gaps: {remaining_gaps}")
                    
                    # Calculate progress based on Duration of gaps closed (more granular than count)
                    if initial_gap_seconds > 0:
                        current_gap_seconds = get_total_duration(new_gaps)
                        # Ensure strictly increasing or at least non-decreasing
                        closed_seconds = max(0, initial_gap_seconds - current_gap_seconds)
                        progress_pct = int((closed_seconds / initial_gap_seconds) * 100)
                    else:
                        progress_pct = 100
                    
                    # Call progress callback
                    
                    # Call progress callback
                    if progress_callback:
                        try:
                            message = f"Fetching data: {current_count} candles loaded"
                            if remaining_gaps > 0:
                                message += f", {remaining_gaps} gaps remaining"
                            await progress_callback(progress_pct, message)
                        except Exception as cb_err:
                            logger.warning(f"Progress callback error: {cb_err}")
                    
                    logger.info(
                        f"[Wait {elapsed}s/{max_wait_seconds}s] "
                        f"Candles: {last_count} -> {current_count}, Gaps remaining: {remaining_gaps}"
                    )
                    
                    # If we have data and no more gaps, we're done
                    if current_count > 0 and remaining_gaps == 0:
                        print(f"DEBUG [MarketDataService]: ========== DATA FETCH COMPLETE ==========")
                        print(f"DEBUG [MarketDataService]: Final candle count: {current_count}")
                        logger.info(f"Data is now complete! {current_count} candles, 0 gaps.")
                        if progress_callback:
                            try:
                                await progress_callback(100, f"Data fetch complete: {current_count} candles")
                            except Exception as cb_err:
                                logger.warning(f"Progress callback error: {cb_err}")
                        return db_candles
                    
                    # If data count increased, reset last_count for progress tracking
                    if current_count > last_count:
                        last_count = current_count
                        # Data is being fetched, continue waiting
                    
                    # If we have some data but gaps remain, keep waiting
                    # Background job may still be processing chunks
                
                # Max wait exceeded
                print(f"DEBUG [MarketDataService]: ========== MAX WAIT EXCEEDED ==========")
                print(f"DEBUG [MarketDataService]: Elapsed: {elapsed}s, Candles: {len(db_candles)}")
                if len(db_candles) > 0:
                    # Return partial data with warning
                    logger.warning(
                        f"Max wait time {max_wait_seconds}s exceeded. "
                        f"Returning {len(db_candles)} candles (gaps may remain)"
                    )
                    return db_candles
                else:
                    # No data at all after waiting
                    raise ValueError(
                        f"No data available for {symbol} {timeframe} "
                        f"from {effective_start_date} to {end_date} after waiting {max_wait_seconds}s"
                    )
            
            # Return immediately with current data (don't block!)
            return db_candles

        return db_candles

    async def _fetch_and_save(
        self,
        symbol: str, 
        interval: CandleInterval, 
        start_time: datetime, 
        end_time: datetime,
        limit: int
    ) -> List[Candle]:
        """Fetch from adapter and save to DB."""
        start_ts = int(start_time.timestamp() * 1000)
        end_ts = int(end_time.timestamp() * 1000)
        
        raw_klines = await self.adapter.get_klines(
            symbol=symbol,
            interval=interval.value,
            start_time=start_ts,
            end_time=end_ts,
            limit=limit
        )
        
        domain_candles = []
        for k in raw_klines:
            # Parse Binance kline
            ts = datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc)
            # Check if within range (Binance might return outside)
            
            candle = Candle(
                symbol=symbol,
                interval=interval,
                open_time=ts,
                close_time=datetime.fromtimestamp(k[6] / 1000, tz=timezone.utc), # Close time
                open_price=Decimal(k[1]),
                high_price=Decimal(k[2]),
                low_price=Decimal(k[3]),
                close_price=Decimal(k[4]),
                volume=Decimal(k[5]),
                quote_volume=Decimal(k[7]),
                trade_count=int(k[8]),
                taker_buy_volume=Decimal(k[9]),
                taker_buy_quote_volume=Decimal(k[10])
            )
            domain_candles.append(candle)
            
        if domain_candles:
            # Save to DB
            # Use bulk save if available, else loop
            # Repo implementation has 'save', maybe loop for now or add save_all
            await self.candle_repo.save_batch(domain_candles)
                
        return domain_candles

    def _candle_to_dict(self, candle: Candle) -> Dict[str, Any]:
        """Convert domain candle to dictionary for API response."""
        return {
            "timestamp": candle.open_time,
            "open": candle.open_price,
            "high": candle.high_price,
            "low": candle.low_price,
            "close": candle.close_price,
            "volume": candle.volume
        }
