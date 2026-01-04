"""FastAPI dependency providers for repositories, use cases, and services."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import get_current_user
from ...infrastructure.persistence.database import get_db
from ...domain.user import User

# Repository imports
from ...infrastructure.persistence.repositories.bot_repository import BotRepository, StrategyRepository
from ...infrastructure.persistence.repositories.market_data_repository import (
    MarketDataSubscriptionRepository,
    CandleRepository,
    TickRepository,
    OrderBookRepository,
    MarketStatsRepository,
    MarketMetadataRepository
)
from ...infrastructure.persistence.repositories.trade_repository import TradeRepository
from ...infrastructure.persistence.sqlalchemy.repositories.risk.risk_limit_repository import SqlAlchemyRiskLimitRepository
from ...infrastructure.persistence.sqlalchemy.repositories.risk.risk_alert_repository import SqlAlchemyRiskAlertRepository
from ...infrastructure.services.market_data_service import MarketDataService
from ...infrastructure.exchange.binance_adapter import BinanceAdapter
from ...infrastructure.repositories.exchange_repository import ExchangeRepository
from ...domain.market_data.gap_detector import GapDetector

# Use case imports
from ...application.use_cases.bot_use_cases import (
    CreateBotUseCase,
    GetBotByIdUseCase,
    GetBotsUseCase,
    StartBotUseCase,
    StopBotUseCase,
    PauseBotUseCase,
    ResumeBotUseCase,
    UpdateBotConfigurationUseCase,
    DeleteBotUseCase
)
from ...application.use_cases.strategy_use_cases import (
    CreateStrategyUseCase,
    GetStrategyByIdUseCase,
    GetStrategiesUseCase,
    UpdateStrategyUseCase,
    ActivateStrategyUseCase,
    DeactivateStrategyUseCase,
    DeleteStrategyUseCase,
)
from ...application.use_cases.market_data_use_cases import (
    CreateMarketDataSubscriptionUseCase,
    GetMarketDataSubscriptionUseCase,
    GetMarketDataSubscriptionsUseCase,
    DeleteMarketDataSubscriptionUseCase,
    GetCandleDataUseCase,
    GetOHLCDataUseCase,
    GetTickDataUseCase,
    GetLatestPriceUseCase,
    GetTradeDataUseCase,
    GetOrderBookUseCase,
    GetMarketStatsUseCase,
    GetMarketOverviewUseCase
)
from src.application.services.connection_service import ConnectionService
from ...application.services.position_service import PositionService
from ...application.use_cases.risk import (
    CreateRiskLimitUseCase,
    GetRiskLimitsUseCase,
    UpdateRiskLimitUseCase,
    DeleteRiskLimitUseCase,
    MonitorRiskUseCase,
    GetRiskAlertsUseCase,
    AcknowledgeRiskAlertUseCase
)


# ============================================================================
# Repository Dependencies
# ============================================================================

async def get_bot_repository(db: AsyncSession = Depends(get_db)) -> BotRepository:
    """Provide bot repository instance."""
    return BotRepository(db)



async def get_strategy_repository(db: AsyncSession = Depends(get_db)) -> StrategyRepository:
    """Provide strategy repository instance."""
    print("DEBUG: Instantiating StrategyRepository")
    return StrategyRepository(db)


async def get_exchange_repository(db: AsyncSession = Depends(get_db)) -> ExchangeRepository:
    """Provide exchange repository instance."""
    return ExchangeRepository(db)



async def get_market_data_subscription_repository(
    db: AsyncSession = Depends(get_db)
) -> MarketDataSubscriptionRepository:
    """Provide market data subscription repository instance."""
    return MarketDataSubscriptionRepository(db)


async def get_candle_repository(db: AsyncSession = Depends(get_db)) -> CandleRepository:
    """Provide candle repository instance."""
    return CandleRepository(db)


async def get_tick_repository(db: AsyncSession = Depends(get_db)) -> TickRepository:
    """Provide tick repository instance."""
    return TickRepository(db)


async def get_trade_repository(db: AsyncSession = Depends(get_db)) -> TradeRepository:
    """Provide trade repository instance."""
    return TradeRepository(db)


async def get_order_book_repository(db: AsyncSession = Depends(get_db)) -> OrderBookRepository:
    """Provide order book repository instance."""
    return OrderBookRepository(db)


async def get_market_stats_repository(db: AsyncSession = Depends(get_db)) -> MarketStatsRepository:
    """Provide market stats repository instance."""
    return MarketStatsRepository(db)


async def get_risk_limit_repository(db: AsyncSession = Depends(get_db)) -> SqlAlchemyRiskLimitRepository:
    """Provide risk limit repository instance."""
    return SqlAlchemyRiskLimitRepository(db)


async def get_risk_alert_repository(db: AsyncSession = Depends(get_db)) -> SqlAlchemyRiskAlertRepository:
    """Provide risk alert repository instance."""
async def get_risk_alert_repository(db: AsyncSession = Depends(get_db)) -> SqlAlchemyRiskAlertRepository:
    """Provide risk alert repository instance."""
    return SqlAlchemyRiskAlertRepository(db)


async def get_market_metadata_repository(db: AsyncSession = Depends(get_db)) -> MarketMetadataRepository:
    """Provide market metadata repository instance."""
    return MarketMetadataRepository(db)


# ============================================================================
# Service Dependencies
# ============================================================================

def get_gap_detector() -> GapDetector:
    """Provide gap detector instance."""
    return GapDetector()


async def get_connection_service(db: AsyncSession = Depends(get_db)) -> ConnectionService:
    """Provide connection service instance."""
    return ConnectionService(db)


from ...infrastructure.persistence.repositories.order_repository import OrderRepository
from ...application.services.bot_stats_service import BotStatsService
from ...application.use_cases.order.update_order_status import UpdateOrderStatusUseCase

# ... existing imports ...

async def get_order_repository(db: AsyncSession = Depends(get_db)) -> OrderRepository:
    """Provide order repository instance."""
    return OrderRepository(db)


async def get_bot_stats_service(db: AsyncSession = Depends(get_db)) -> BotStatsService:
    """Provide bot stats service instance."""
    return BotStatsService(db)


async def get_update_order_status_use_case(
    order_repo: OrderRepository = Depends(get_order_repository),
    trade_repo: TradeRepository = Depends(get_trade_repository),
    bot_stats_service: BotStatsService = Depends(get_bot_stats_service)
) -> UpdateOrderStatusUseCase:
    """Provide update order status use case instance."""
    return UpdateOrderStatusUseCase(order_repo, trade_repo, bot_stats_service)


async def get_position_service(
    db: AsyncSession = Depends(get_db),
    bot_repo: BotRepository = Depends(get_bot_repository),
    connection_service: ConnectionService = Depends(get_connection_service),
    order_repo: OrderRepository = Depends(get_order_repository),
    update_order_status_use_case: UpdateOrderStatusUseCase = Depends(get_update_order_status_use_case)
) -> PositionService:
    """Provide position service instance."""
    return PositionService(db, bot_repo, connection_service, order_repo, update_order_status_use_case)


def get_public_binance_adapter() -> BinanceAdapter:
    """Provide public Binance adapter (no credentials)."""
    return BinanceAdapter(api_key=None, api_secret=None)


def get_market_data_service(
    adapter: BinanceAdapter = Depends(get_public_binance_adapter),
    candle_repo: CandleRepository = Depends(get_candle_repository),
    metadata_repo: MarketMetadataRepository = Depends(get_market_metadata_repository),
    gap_detector: GapDetector = Depends(get_gap_detector)
) -> MarketDataService:
    """Provide market data service instance."""
    return MarketDataService(
        exchange_adapter=adapter,
        candle_repository=candle_repo,
        metadata_repository=metadata_repo,
        gap_detector=gap_detector
    )


# ============================================================================
# Bot Use Case Dependencies
# ============================================================================

async def get_create_bot_use_case(
    bot_repo: BotRepository = Depends(get_bot_repository),
    strategy_repo: StrategyRepository = Depends(get_strategy_repository),
    exchange_repo: ExchangeRepository = Depends(get_exchange_repository)
) -> CreateBotUseCase:
    """Provide create bot use case instance."""
    return CreateBotUseCase(bot_repo, strategy_repo, exchange_repo)


async def get_get_bot_by_id_use_case(
    bot_repo: BotRepository = Depends(get_bot_repository)
) -> GetBotByIdUseCase:
    """Provide get bot by ID use case instance."""
    return GetBotByIdUseCase(bot_repo)


async def get_get_bots_use_case(
    bot_repo: BotRepository = Depends(get_bot_repository)
) -> GetBotsUseCase:
    """Provide get bots use case instance."""
    return GetBotsUseCase(bot_repo)


async def get_start_bot_use_case(
    bot_repo: BotRepository = Depends(get_bot_repository)
) -> StartBotUseCase:
    """Provide start bot use case instance."""
    from ...application.services.bot_manager import get_bot_manager
    try:
        bot_manager = get_bot_manager()
    except RuntimeError:
        # BotManager not initialized (shouldn't happen in production)
        bot_manager = None
    return StartBotUseCase(bot_repo, bot_manager=bot_manager)


async def get_stop_bot_use_case(
    bot_repo: BotRepository = Depends(get_bot_repository)
) -> StopBotUseCase:
    """Provide stop bot use case instance."""
    from ...application.services.bot_manager import get_bot_manager
    try:
        bot_manager = get_bot_manager()
    except RuntimeError:
        bot_manager = None
    return StopBotUseCase(bot_repo, bot_manager=bot_manager)


async def get_pause_bot_use_case(
    bot_repo: BotRepository = Depends(get_bot_repository)
) -> PauseBotUseCase:
    """Provide pause bot use case instance."""
    return PauseBotUseCase(bot_repo)


async def get_resume_bot_use_case(
    bot_repo: BotRepository = Depends(get_bot_repository)
) -> ResumeBotUseCase:
    """Provide resume bot use case instance."""
    return ResumeBotUseCase(bot_repo)


async def get_update_bot_config_use_case(
    bot_repo: BotRepository = Depends(get_bot_repository)
) -> UpdateBotConfigurationUseCase:
    """Provide update bot configuration use case instance."""
    return UpdateBotConfigurationUseCase(bot_repo)


async def get_delete_bot_use_case(
    bot_repo: BotRepository = Depends(get_bot_repository)
) -> DeleteBotUseCase:
    """Provide delete bot use case instance."""
    return DeleteBotUseCase(bot_repo)


# NOTE: GetBotPerformanceUseCase not yet implemented
# async def get_get_bot_performance_use_case(
#     bot_repo: BotRepository = Depends(get_bot_repository)
# ) -> GetBotPerformanceUseCase:
#     """Provide get bot performance use case instance."""
#     return GetBotPerformanceUseCase(bot_repo)


# ============================================================================
# Strategy Use Case Dependencies
# ============================================================================

async def get_create_strategy_use_case(
    strategy_repo: StrategyRepository = Depends(get_strategy_repository)
) -> CreateStrategyUseCase:
    """Provide create strategy use case instance."""
    return CreateStrategyUseCase(strategy_repo)


async def get_get_strategy_by_id_use_case(
    strategy_repo: StrategyRepository = Depends(get_strategy_repository)
) -> GetStrategyByIdUseCase:
    """Provide get strategy by ID use case instance."""
    return GetStrategyByIdUseCase(strategy_repo)


async def get_get_strategies_use_case(
    strategy_repo: StrategyRepository = Depends(get_strategy_repository)
) -> GetStrategiesUseCase:
    """Provide get strategies use case instance."""
    return GetStrategiesUseCase(strategy_repo)


async def get_update_strategy_use_case(
    strategy_repo: StrategyRepository = Depends(get_strategy_repository)
) -> UpdateStrategyUseCase:
    """Provide update strategy use case instance."""
    return UpdateStrategyUseCase(strategy_repo)


async def get_activate_strategy_use_case(
    strategy_repo: StrategyRepository = Depends(get_strategy_repository)
) -> ActivateStrategyUseCase:
    """Provide activate strategy use case instance."""
    return ActivateStrategyUseCase(strategy_repo)


async def get_deactivate_strategy_use_case(
    strategy_repo: StrategyRepository = Depends(get_strategy_repository)
) -> DeactivateStrategyUseCase:
    """Provide deactivate strategy use case instance."""
    return DeactivateStrategyUseCase(strategy_repo)


async def get_delete_strategy_use_case(
    strategy_repo: StrategyRepository = Depends(get_strategy_repository)
) -> DeleteStrategyUseCase:
    """Provide delete strategy use case instance."""
    return DeleteStrategyUseCase(strategy_repo)


# NOTE: GetStrategyPerformanceUseCase not yet implemented
# async def get_get_strategy_performance_use_case(
#     strategy_repo: StrategyRepository = Depends(get_strategy_repository)
# ) -> GetStrategyPerformanceUseCase:
#     """Provide get strategy performance use case instance."""
#     return GetStrategyPerformanceUseCase(strategy_repo)


# ============================================================================
# Market Data Use Case Dependencies
# ============================================================================

async def get_create_market_data_subscription_use_case(
    subscription_repo: MarketDataSubscriptionRepository = Depends(get_market_data_subscription_repository)
) -> CreateMarketDataSubscriptionUseCase:
    """Provide create market data subscription use case instance."""
    return CreateMarketDataSubscriptionUseCase(subscription_repo)


async def get_get_market_data_subscription_use_case(
    subscription_repo: MarketDataSubscriptionRepository = Depends(get_market_data_subscription_repository)
) -> GetMarketDataSubscriptionUseCase:
    """Provide get market data subscription use case instance."""
    return GetMarketDataSubscriptionUseCase(subscription_repo)


async def get_get_market_data_subscriptions_use_case(
    subscription_repo: MarketDataSubscriptionRepository = Depends(get_market_data_subscription_repository)
) -> GetMarketDataSubscriptionsUseCase:
    """Provide get market data subscriptions use case instance."""
    return GetMarketDataSubscriptionsUseCase(subscription_repo)


async def get_delete_market_data_subscription_use_case(
    subscription_repo: MarketDataSubscriptionRepository = Depends(get_market_data_subscription_repository)
) -> DeleteMarketDataSubscriptionUseCase:
    """Provide delete market data subscription use case instance."""
    return DeleteMarketDataSubscriptionUseCase(subscription_repo)


async def get_get_candle_data_use_case(
    market_data_service: MarketDataService = Depends(get_market_data_service)
) -> GetCandleDataUseCase:
    """Provide get candle data use case instance."""
    return GetCandleDataUseCase(market_data_service)


async def get_get_ohlc_data_use_case(
    candle_repo: CandleRepository = Depends(get_candle_repository)
) -> GetOHLCDataUseCase:
    """Provide get OHLC data use case instance."""
    return GetOHLCDataUseCase(candle_repo)


async def get_get_tick_data_use_case(
    tick_repo: TickRepository = Depends(get_tick_repository)
) -> GetTickDataUseCase:
    """Provide get tick data use case instance."""
    return GetTickDataUseCase(tick_repo)


async def get_get_latest_price_use_case(
    candle_repo: CandleRepository = Depends(get_candle_repository)
) -> GetLatestPriceUseCase:
    """Provide get latest price use case instance."""
    return GetLatestPriceUseCase(candle_repo)


async def get_get_trade_data_use_case(
    trade_repo: TradeRepository = Depends(get_trade_repository)
) -> GetTradeDataUseCase:
    """Provide get trade data use case instance."""
    return GetTradeDataUseCase(trade_repo)


async def get_get_order_book_use_case(
    order_book_repo: OrderBookRepository = Depends(get_order_book_repository)
) -> GetOrderBookUseCase:
    """Provide get order book use case instance."""
    return GetOrderBookUseCase(order_book_repo)


async def get_get_market_stats_use_case(
    market_stats_repo: MarketStatsRepository = Depends(get_market_stats_repository)
) -> GetMarketStatsUseCase:
    """Provide get market stats use case instance."""
    return GetMarketStatsUseCase(market_stats_repo)


async def get_get_market_overview_use_case(
    market_stats_repo: MarketStatsRepository = Depends(get_market_stats_repository)
) -> GetMarketOverviewUseCase:
    """Provide get market overview use case instance."""
    return GetMarketOverviewUseCase(market_stats_repo)


# ============================================================================
# Risk Management Use Case Dependencies
# ============================================================================

async def get_create_risk_limit_use_case(
    risk_limit_repo: SqlAlchemyRiskLimitRepository = Depends(get_risk_limit_repository)
) -> CreateRiskLimitUseCase:
    """Provide create risk limit use case instance."""
    return CreateRiskLimitUseCase(risk_limit_repo)


async def get_get_risk_limits_use_case(
    risk_limit_repo: SqlAlchemyRiskLimitRepository = Depends(get_risk_limit_repository)
) -> GetRiskLimitsUseCase:
    """Provide get risk limits use case instance."""
    return GetRiskLimitsUseCase(risk_limit_repo)


async def get_update_risk_limit_use_case(
    risk_limit_repo: SqlAlchemyRiskLimitRepository = Depends(get_risk_limit_repository)
) -> UpdateRiskLimitUseCase:
    """Provide update risk limit use case instance."""
    return UpdateRiskLimitUseCase(risk_limit_repo)


async def get_delete_risk_limit_use_case(
    risk_limit_repo: SqlAlchemyRiskLimitRepository = Depends(get_risk_limit_repository)
) -> DeleteRiskLimitUseCase:
    """Provide delete risk limit use case instance."""
    return DeleteRiskLimitUseCase(risk_limit_repo)


async def get_monitor_risk_use_case(
    risk_limit_repo: SqlAlchemyRiskLimitRepository = Depends(get_risk_limit_repository),
    risk_alert_repo: SqlAlchemyRiskAlertRepository = Depends(get_risk_alert_repository)
) -> MonitorRiskUseCase:
    """Provide monitor risk use case instance."""
    return MonitorRiskUseCase(risk_limit_repo, risk_alert_repo)


async def get_get_risk_alerts_use_case(
    risk_alert_repo: SqlAlchemyRiskAlertRepository = Depends(get_risk_alert_repository)
) -> GetRiskAlertsUseCase:
    """Provide get risk alerts use case instance."""
    return GetRiskAlertsUseCase(risk_alert_repo)


async def get_acknowledge_risk_alert_use_case(
    risk_alert_repo: SqlAlchemyRiskAlertRepository = Depends(get_risk_alert_repository)
) -> AcknowledgeRiskAlertUseCase:
    """Provide acknowledge risk alert use case instance."""
    return AcknowledgeRiskAlertUseCase(risk_alert_repo)