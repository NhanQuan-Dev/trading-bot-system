"""
BotManager - Orchestrates bot lifecycle and execution.

Responsibilities:
1. Track all running bot engines in memory
2. Start/stop bots on demand
3. Instantiate strategy and exchange adapter for each bot
4. Handle graceful shutdown of all bots
"""
import asyncio
import logging
import uuid
from typing import Dict, Optional, Any
from datetime import datetime, timezone

from src.trading.domain.bot import Bot, BotStatus
from src.trading.domain.exchange import ExchangeType
from src.trading.infrastructure.execution.bot_engine import BotEngine
from src.trading.infrastructure.exchange.exchange_gateway import ExchangeGateway
from src.trading.infrastructure.exchange.binance_adapter import BinanceAdapter
from src.trading.infrastructure.persistence.repositories.bot_repository import BotRepository
from src.trading.infrastructure.repositories.exchange_repository import ExchangeRepository
from src.trading.strategies.registry import registry as strategy_registry
from src.trading.strategies.base import StrategyBase

logger = logging.getLogger(__name__)


class BotManager:
    """
    Singleton-like manager for all running bot engines.
    
    In a production system, this would be backed by Redis/Celery
    for distributed execution across multiple workers.
    For MVP, we use in-memory dict with asyncio tasks.
    """
    
    def __init__(self, session_factory: Any):
        """
        Initialize the BotManager.
        
        Args:
            session_factory: SQLAlchemy async_sessionmaker for creating DB sessions
        """
        self.session_factory = session_factory
        self._engines: Dict[str, BotEngine] = {}  # bot_id -> BotEngine
        self._lock = asyncio.Lock()
    
    async def start_bot(self, bot_id: uuid.UUID) -> bool:
        """
        Start a bot by its ID.
        
        Args:
            bot_id: UUID of the bot to start
            
        Returns:
            True if started successfully, False otherwise
        """
        bot_id_str = str(bot_id)
        
        async with self._lock:
            # Check if already running - if so, try to cleanup stale engine
            if bot_id_str in self._engines:
                print(f"[BotManager] Bot {bot_id_str} found in engines dict - cleaning up stale engine")
                logger.warning(f"Bot {bot_id_str} has stale engine, cleaning up before restart")
                try:
                    old_engine = self._engines[bot_id_str]
                    await old_engine.stop()
                except Exception as e:
                    logger.warning(f"Error stopping stale engine (ignoring): {e}")
                del self._engines[bot_id_str]
                print(f"[BotManager] Stale engine removed, proceeding with start")
            
            try:
                print(f"[BotManager] Fetching bot from database...")
                # Fetch bot from database
                async with self.session_factory() as session:
                    bot_repo = BotRepository(session)
                    bot = await bot_repo.find_by_id(bot_id)
                    
                    if not bot:
                        print(f"[BotManager] ERROR: Bot {bot_id_str} not found in DB")
                        logger.error(f"Bot {bot_id_str} not found")
                        return False
                    
                    print(f"[BotManager] Found bot: {bot.name}, status={bot.status}")
                    print(f"[BotManager] Strategy ID: {bot.strategy_id}")
                    print(f"[BotManager] Exchange Connection ID: {bot.exchange_connection_id}")
                    print(f"[BotManager] Symbol: {bot.configuration.symbol}")
                    
                    # Validate bot can be started
                    if bot.status not in [BotStatus.PAUSED, BotStatus.ERROR]:
                        print(f"[BotManager] ERROR: Cannot start from status {bot.status}")
                        logger.warning(f"Bot {bot_id_str} cannot be started from status {bot.status}")
                        return False
                    
                    print(f"[BotManager] Creating exchange adapter...")
                    # Create exchange adapter
                    exchange = await self._create_exchange_adapter(session, bot)
                    if not exchange:
                        print(f"[BotManager] ERROR: Failed to create exchange adapter")
                        logger.error(f"Failed to create exchange adapter for bot {bot_id_str}")
                        return False
                    print(f"[BotManager] Exchange adapter created: {type(exchange).__name__}")
                    
                    print(f"[BotManager] Creating strategy instance...")
                    # Create strategy instance - pass session for DB lookup
                    strategy = await self._create_strategy(session, bot, exchange)
                    if not strategy:
                        print(f"[BotManager] ERROR: Failed to create strategy")
                        logger.error(f"Failed to create strategy for bot {bot_id_str}")
                        return False
                    print(f"[BotManager] Strategy created: {type(strategy).__name__}")
                    
                    # Determine check interval from config (default 60s)
                    strategy_settings = bot.configuration.strategy_settings or {}
                    check_interval = strategy_settings.get("check_interval", 10)
                    print(f"[BotManager] Check interval: {check_interval}s")
                    
                    print(f"[BotManager] Creating BotEngine...")
                    # Create and start engine
                    engine = BotEngine(
                        bot_id=bot_id_str,
                        strategy=strategy,
                        exchange=exchange,
                        session_factory=self.session_factory,
                        check_interval_seconds=check_interval
                    )
                    
                    print(f"[BotManager] Starting engine.start()...")
                    await engine.start()
                    self._engines[bot_id_str] = engine
                    print(f"[BotManager] Engine started and stored in _engines dict")
                    
                    # Update bot status to RUNNING
                    bot.status = BotStatus.RUNNING
                    bot.start_time = datetime.now(timezone.utc)
                    bot.last_error = None
                    await bot_repo.save(bot)
                    print(f"[BotManager] Bot status updated to RUNNING in DB")
                    
                print(f"[BotManager] SUCCESS - Bot {bot_id_str} started")
                logger.info(f"Bot {bot_id_str} started successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to start bot {bot_id_str}: {e}", exc_info=True)
                # Try to update bot status to ERROR
                try:
                    async with self.session_factory() as session:
                        bot_repo = BotRepository(session)
                        bot = await bot_repo.find_by_id(bot_id)
                        if bot:
                            bot.status = BotStatus.ERROR
                            bot.last_error = str(e)
                            await bot_repo.save(bot)
                except Exception:
                    pass
                return False
                return False
    
    async def stop_bot(self, bot_id: uuid.UUID) -> bool:
        """
        Stop a running bot.
        
        Args:
            bot_id: UUID of the bot to stop
            
        Returns:
            True if stopped successfully, False otherwise
        """
        bot_id_str = str(bot_id)
        
        async with self._lock:
            engine = self._engines.get(bot_id_str)
            
            if not engine:
                logger.warning(f"Bot {bot_id_str} is not running")
                return False
            
            try:
                # Stop the engine
                await engine.stop()
                
                # Remove from tracked engines
                del self._engines[bot_id_str]
                
                # Update bot status in DB
                async with self.session_factory() as session:
                    bot_repo = BotRepository(session)
                    bot = await bot_repo.find_by_id(bot_id)
                    if bot:
                        bot.status = BotStatus.PAUSED
                        bot.stop_time = datetime.now(timezone.utc)
                        await bot_repo.save(bot)
                
                logger.info(f"Bot {bot_id_str} stopped successfully")
                return True
                
            except Exception as e:
                logger.error(f"Failed to stop bot {bot_id_str}: {e}", exc_info=True)
                return False
    
    async def stop_all_bots(self):
        """Stop all running bots. Called during application shutdown."""
        logger.info(f"Stopping all bots ({len(self._engines)} running)...")
        
        bot_ids = list(self._engines.keys())
        for bot_id_str in bot_ids:
            try:
                await self.stop_bot(uuid.UUID(bot_id_str))
            except Exception as e:
                logger.error(f"Error stopping bot {bot_id_str}: {e}")
        
        logger.info("All bots stopped")
    
    def is_bot_running(self, bot_id: uuid.UUID) -> bool:
        """Check if a bot is currently running."""
        return str(bot_id) in self._engines
    
    def get_running_bot_ids(self) -> list:
        """Get list of all running bot IDs."""
        return list(self._engines.keys())
    
    async def _create_exchange_adapter(
        self, 
        session: Any, 
        bot: Bot
    ) -> Optional[ExchangeGateway]:
        """
        Create an exchange adapter for the bot.
        
        Args:
            session: Database session
            bot: Bot domain entity
            
        Returns:
            ExchangeGateway instance or None if failed
        """
        try:
            print(f"DEBUG: Creating exchange adapter for bot {bot.id}")
            print(f"DEBUG: exchange_connection_id={bot.exchange_connection_id}")
            exchange_repo = ExchangeRepository(session)
            connection = await exchange_repo.find_by_id(bot.exchange_connection_id)
            print(f"DEBUG: Exchange connection result: {connection}")
            
            if not connection:
                logger.error(f"Exchange connection {bot.exchange_connection_id} not found")
                print(f"ERROR: Exchange connection NOT FOUND: {bot.exchange_connection_id}")
                return None
            
            # Create appropriate adapter based on exchange type
            if connection.exchange_type == ExchangeType.BINANCE:
                # Determine if using testnet
                # Official Binance Futures Testnet: https://demo-fapi.binance.com
                # Mainnet: https://fapi.binance.com
                base_url = "https://demo-fapi.binance.com" if connection.is_testnet else "https://fapi.binance.com"
                print(f"DEBUG: Using base_url={base_url}, is_testnet={connection.is_testnet}")
                
                api_key = connection.credentials.api_key
                api_secret = connection.credentials.secret_key
                print(f"DEBUG: API Key (first 10 chars): {api_key[:10]}...")
                print(f"DEBUG: API Secret (first 10 chars): {api_secret[:10]}...")
                print(f"DEBUG: API Secret length: {len(api_secret)}")
                
                return BinanceAdapter(
                    api_key=api_key,
                    api_secret=api_secret,
                    base_url=base_url,
                    testnet=connection.is_testnet
                )
            else:
                logger.error(f"Unsupported exchange type: {connection.exchange_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating exchange adapter: {e}", exc_info=True)
            return None
    
    async def _create_strategy(
        self, 
        session: Any,
        bot: Bot, 
        exchange: ExchangeGateway
    ) -> Optional[StrategyBase]:
        """
        Create a strategy instance for the bot.
        
        Args:
            session: Database session for looking up strategy
            bot: Bot domain entity
            exchange: ExchangeGateway instance
            
        Returns:
            StrategyBase instance or None if failed
        """
        try:
            # Fetch strategy from database to get its name
            from src.trading.infrastructure.persistence.repositories.bot_repository import StrategyRepository
            strategy_repo = StrategyRepository(session)
            strategy_entity = await strategy_repo.find_by_id(bot.strategy_id)
            
            if not strategy_entity:
                logger.error(f"Strategy {bot.strategy_id} not found for bot {bot.id}")
                return None
            
            # Use strategy name to lookup class in registry
            strategy_name = strategy_entity.name
            logger.info(f"Looking up strategy '{strategy_name}' in registry for bot {bot.id}")
            
            # Get strategy class from registry
            strategy_cls = strategy_registry.get_strategy_class(strategy_name)
            
            if not strategy_cls:
                logger.error(f"Strategy '{strategy_name}' not found in registry")
                return None
            
            # Build strategy config from bot configuration
            strategy_settings = bot.configuration.strategy_settings or {}
            
            # Default strategy parameters from strategy definition
            strategy_defaults = strategy_entity.parameters or {}
            
            # Ensure strategy_defaults is a dict (handle potential object/custom type)
            if not isinstance(strategy_defaults, dict):
                if hasattr(strategy_defaults, "dict"):
                    strategy_defaults = strategy_defaults.dict()
                elif hasattr(strategy_defaults, "__dict__"):
                    strategy_defaults = vars(strategy_defaults)
                else:
                    logger.warning(f"Strategy parameters type {type(strategy_defaults)} is not a dict, using empty dict")
                    strategy_defaults = {}
            
            # Flatten 'parameters' key if it exists (fix for nested structure issue)
            if "parameters" in strategy_defaults and isinstance(strategy_defaults["parameters"], dict):
                strategy_defaults.update(strategy_defaults["parameters"])

            strategy_config = {
                **strategy_defaults, # Load defaults first
                "symbol": bot.configuration.symbol,
                "timeframe": strategy_settings.get("timeframe", "1h"),
                "base_quantity": str(bot.configuration.base_quantity),
                "quote_quantity": str(bot.configuration.quote_quantity),
                "take_profit_percentage": str(bot.configuration.take_profit_percentage),
                "stop_loss_percentage": str(bot.configuration.stop_loss_percentage),
                **strategy_settings # Override with bot specific settings
            }
            
            # Instantiate strategy
            logger.info(f"Creating strategy instance: {strategy_cls.__name__}")
            print(f"DEBUG [BotManager]: Final strategy_config={strategy_config}")
            return strategy_cls(exchange=exchange, config=strategy_config)
            
        except Exception as e:
            logger.error(f"Error creating strategy: {e}", exc_info=True)
            return None


# Global instance (will be initialized in app startup)
_bot_manager: Optional[BotManager] = None


def get_bot_manager() -> BotManager:
    """Get the global BotManager instance."""
    if _bot_manager is None:
        raise RuntimeError("BotManager not initialized. Call init_bot_manager first.")
    return _bot_manager


def init_bot_manager(session_factory: Any) -> BotManager:
    """Initialize the global BotManager instance."""
    global _bot_manager
    _bot_manager = BotManager(session_factory)
    logger.info("BotManager initialized")
    return _bot_manager
