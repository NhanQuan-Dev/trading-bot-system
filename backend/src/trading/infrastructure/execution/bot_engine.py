import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import uuid
from sqlalchemy import select

from src.trading.domain.bot import Bot, BotStatus
from src.trading.strategies.base import StrategyBase
from src.trading.infrastructure.exchange.exchange_gateway import ExchangeGateway, ExchangeAPIError
from src.trading.infrastructure.persistence.repositories.bot_repository import BotRepository

logger = logging.getLogger(__name__)

class BotEngine:
    """
    Engine for running a single trading bot.
    
    Responsible for:
    1. Fetching market data (candles)
    2. Executing strategy logic
    3. Managing the execution loop
    4. Handling errors and updating bot status
    """
    
    def __init__(
        self,
        bot_id: str,
        strategy: StrategyBase,
        exchange: ExchangeGateway,
        session_factory: Any, # async_sessionmaker[AsyncSession]
        check_interval_seconds: int = 60
    ):
        self.bot_id = bot_id
        self.strategy = strategy
        self.exchange = exchange
        self.session_factory = session_factory
        self.check_interval_seconds = check_interval_seconds
        
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self._error_count = 0
        self._max_errors = 5
        
        # Context
        self.user_id = None
        self.exchange_id = None
        
        # Hook persistence callback
        self.strategy.on_order = self._on_order

    async def start(self):
        """Start the bot execution loop."""
        print(f"\n[BotEngine] start() called for bot {self.bot_id}")
        if self.is_running:
            print(f"[BotEngine] Bot {self.bot_id} is already running, skipping")
            logger.warning(f"Bot {self.bot_id} is already running")
            return
            
        # Load context (user_id, exchange_id)
        print(f"[BotEngine] Loading context...")
        if not await self._load_context():
            print(f"[BotEngine] ERROR: Failed to load context")
            logger.error(f"Failed to load context for bot {self.bot_id}, cannot start")
            return
        print(f"[BotEngine] Context loaded: user_id={self.user_id}, exchange_id={self.exchange_id}")
            
        self.is_running = True
        self._error_count = 0
        print(f"[BotEngine] Creating asyncio task for _run_loop()...")
        self._task = asyncio.create_task(self._run_loop())
        print(f"[BotEngine] Task created. Engine is now running!")
        logger.info(f"Bot {self.bot_id} engine started")

    async def _load_context(self) -> bool:
        """Load bot owner and exchange info from DB."""
        try:
            print(f"[BotEngine] _load_context started...")
            async with self.session_factory() as session:
                bot_repo = BotRepository(session)
                bot = await bot_repo.find_by_id(self.bot_id)
                if not bot:
                    print(f"[BotEngine] ERROR: Bot not found in DB")
                    return False
                self.user_id = bot.user_id
                print(f"[BotEngine] User ID: {self.user_id}")
                
                # Fetch exchange_id (Integer) from the connection
                print(f"[BotEngine] Importing APIConnectionModel...")
                from src.trading.infrastructure.persistence.models.core_models import APIConnectionModel
                
                print(f"[BotEngine] Querying exchange_id for connection {bot.exchange_connection_id}...")
                stmt = select(APIConnectionModel.exchange_id).where(APIConnectionModel.id == bot.exchange_connection_id)
                result = await session.execute(stmt)
                exchange_id_int = result.scalar_one_or_none()
                print(f"[BotEngine] Exchange ID result: {exchange_id_int}")
                
                if exchange_id_int is None:
                    print(f"[BotEngine] ERROR: Could not find exchange_id for connection {bot.exchange_connection_id}")
                    return False
                    
                self.exchange_id = exchange_id_int
                return True
        except Exception as e:
            print(f"[BotEngine] EXCEPTION in _load_context: {e}")
            logger.error(f"Error loading context for bot {self.bot_id}: {e}")
            return False

    async def stop(self):
        """Stop the bot execution loop."""
        if not self.is_running:
            return

        logger.info(f"Stopping bot {self.bot_id}...")
        self.is_running = False
        
        if self._task:
            try:
                # Cancel the task and wait for it to finish
                self._task.cancel()
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error stopping bot {self.bot_id}: {e}")
            finally:
                self._task = None
                
        logger.info(f"Bot {self.bot_id} engine stopped")

    async def _on_order(self, order_data: Dict[str, Any]):
        """Callback to persist order execution."""
        try:
            from src.trading.infrastructure.persistence.models.trading_models import OrderModel
            from src.trading.infrastructure.persistence.repositories.order_repository import OrderRepository
            
            async with self.session_factory() as session:
                repo = OrderRepository(session)
                
                # Map response to OrderModel
                # response typically has: symbol, orderId, price, origQty, executedQty, type, side, status
                
                new_order = OrderModel(
                    bot_id=self.bot_id,
                    user_id=self.user_id,
                    exchange_id=self.exchange_id,
                    symbol=order_data.get("symbol"),
                    exchange_order_id=str(order_data.get("orderId", "")),
                    # Map BUY/SELL to LONG/SHORT to satisfy DB constraint ck_orders_side
                    side="LONG" if order_data.get("side") == "BUY" else "SHORT", 
                    order_type=order_data.get("type"),
                    quantity=order_data.get("quantity"), # Original request quantity
                    price=order_data.get("price"),
                    # Map NEW to PENDING to satisfy DB constraint ck_orders_status
                    status="PENDING" if order_data.get("status", "NEW").upper() == "NEW" else order_data.get("status").upper(),
                    filled_quantity=order_data.get("executedQty", 0),
                    # Default required fields
                    leverage=1,
                    margin_mode="ISOLATED",
                    position_mode="ONE_WAY",
                    time_in_force="GTC"
                )
                
                await repo.add(new_order)
                await session.commit()
                logger.info(f"Persisted order {new_order.exchange_order_id} for bot {self.bot_id}")
                
        except Exception as e:
            logger.error(f"Failed to persist order for bot {self.bot_id}: {e}", exc_info=True)

    async def _run_loop(self):
        """Main execution loop."""
        print(f"\n[BotEngine] _run_loop() STARTED for bot {self.bot_id}")
        print(f"[BotEngine] Check interval: {self.check_interval_seconds}s")
        logger.info(f"Bot {self.bot_id} loop started")
        
        iteration = 0
        while self.is_running:
            iteration += 1
            print(f"\n[BotEngine] === ITERATION {iteration} ===")
            try:
                # 1. Fetch Market Data
                # Strategy config should have 'symbol' and 'timeframe'
                symbol = self.strategy.config.get("symbol")
                # Default to 1h if not specified (should be validated earlier)
                interval = self.strategy.config.get("timeframe", "1h") 
                
                if not symbol:
                    print(f"[BotEngine] ERROR: Missing symbol in config")
                    raise ValueError(f"Bot {self.bot_id} configuration missing 'symbol'")
                
                print(f"[BotEngine] Fetching {interval} candles for {symbol}...")
                logger.debug(f"Bot {self.bot_id} fetching {interval} candles for {symbol}")
                
                # Fetch recent candles (enough for most strategies)
                candles = await self.exchange.get_klines(
                    symbol=symbol, 
                    interval=interval,
                    limit=100
                )
                print(f"[BotEngine] Got {len(candles) if candles else 0} candles")
                
                # 2. Execute Strategy
                print(f"[BotEngine] Calling strategy.on_tick()...")
                # StrategyBase.on_tick expects 'market_data'
                # We pass the raw candles list for now.
                # TODO: Parse into Candle objects if Strategy expects objects
                await self.strategy.on_tick(candles)
                print(f"[BotEngine] strategy.on_tick() completed")
                
                # 3. Update Last Run Time
                # We do this asynchronously to not block, or Fire-and-Forget
                # For now, safe await
                await self._update_last_run()
                
                # Reset error count on successful iteration
                self._error_count = 0
                print(f"[BotEngine] Iteration {iteration} completed successfully")
                
            except asyncio.CancelledError:
                print(f"[BotEngine] Received CancelledError, stopping loop")
                # Normal stop
                break
            except Exception as e:
                self._error_count += 1
                print(f"[BotEngine] ERROR in iteration {iteration}: {e}")
                logger.error(f"Error in bot {self.bot_id} loop (Attempt {self._error_count}/{self._max_errors}): {e}", exc_info=True)
                
                if self._error_count >= self._max_errors:
                    logger.critical(f"Bot {self.bot_id} stopping due to excessive errors")
                    self.is_running = False
                    await self._handle_fatal_error(str(e))
                    break
            
            # Sleep until next tick
            # We handle cancellation during sleep
            print(f"[BotEngine] Sleeping for {self.check_interval_seconds}s...")
            try:
                await asyncio.sleep(self.check_interval_seconds)
            except asyncio.CancelledError:
                print(f"[BotEngine] Sleep cancelled, exiting loop")
                break
        
        print(f"[BotEngine] _run_loop() ENDED for bot {self.bot_id}")

    async def _update_last_run(self):
        """Update the bot's last_run timestamp in DB."""
        try:
            async with self.session_factory() as session:
                bot_repository = BotRepository(session)
                bot = await bot_repository.find_by_id(self.bot_id)
                if bot:
                     # TODO: Actual field update if needed
                     pass
        except Exception as e:
            logger.warning(f"Failed to update heartbeat for bot {self.bot_id}: {e}")

    async def _handle_fatal_error(self, error_msg: str):
        """Update bot status to ERROR in DB."""
        try:
            async with self.session_factory() as session:
                bot_repository = BotRepository(session)
                bot = await bot_repository.find_by_id(self.bot_id)
                if bot:
                    bot.status = BotStatus.ERROR
                    bot.error_message = error_msg
                    bot.stopped_at = datetime.now(timezone.utc)
                    await bot_repository.save(bot)
        except Exception as e:
            logger.error(f"Failed to save fatal error state for bot {self.bot_id}: {e}")
