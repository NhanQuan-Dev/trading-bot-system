"""Portfolio Controller for portfolio management endpoints."""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from trading.infrastructure.persistence.database import get_db
from application.services.portfolio_service import PortfolioService
from trading.infrastructure.cache.price_cache import PriceCache
from trading.infrastructure.cache.redis_client import RedisClient
from trading.interfaces.dependencies.auth import get_current_user

router = APIRouter(prefix="/api/portfolio", tags=["Portfolio"])


def get_portfolio_service(
    db: AsyncSession = Depends(get_db),
    redis_client: Optional[RedisClient] = None
) -> PortfolioService:
    """Dependency to get portfolio service."""
    cache = PriceCache(redis_client) if redis_client else None
    return PortfolioService(db, cache)


@router.get("/summary")
async def get_portfolio_summary(
    current_user = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Get overall portfolio summary.
    
    Returns:
        - total_balance: Total balance across all bots
        - total_equity: Total equity (balance + unrealized P&L)
        - unrealized_pnl: Total unrealized profit/loss
        - realized_pnl: Total realized profit/loss
        - total_pnl: Total profit/loss
        - roi: Return on investment percentage
        - active_bots: Number of active bots
        - open_positions: Number of open positions
    """
    user_id = str(current_user.id)
    return await service.get_portfolio_summary(user_id)


@router.get("/balance")
async def get_portfolio_balance(
    current_user = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Get current balance across all exchanges.
    
    Returns list of balances:
        - exchange: Exchange name
        - asset: Asset symbol
        - free: Free balance
        - locked: Locked balance (in positions)
        - total: Total balance
    """
    user_id = str(current_user.id)
    return await service.get_portfolio_balance(user_id)


@router.get("/pnl/daily")
async def get_daily_pnl(
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    current_user = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Get daily P&L chart data.
    
    Query Params:
        - days: Number of days (1-365, default 30)
    
    Returns list of daily data:
        - date: Date
        - pnl: Daily profit/loss
        - cumulative_pnl: Cumulative profit/loss
        - trades_count: Number of trades that day
    """
    user_id = str(current_user.id)
    return await service.get_daily_pnl(user_id, days)


@router.get("/pnl/monthly")
async def get_monthly_pnl(
    months: int = Query(12, ge=1, le=24, description="Number of months"),
    current_user = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Get monthly P&L summary.
    
    Query Params:
        - months: Number of months (1-24, default 12)
    
    Returns list of monthly data:
        - month: Month (YYYY-MM)
        - total_pnl: Total profit/loss for month
        - total_trades: Total number of trades
        - win_trades: Number of winning trades
        - loss_trades: Number of losing trades
        - win_rate: Win rate percentage
    """
    user_id = str(current_user.id)
    return await service.get_monthly_pnl(user_id, months)


@router.get("/exposure")
async def get_portfolio_exposure(
    current_user = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Get current market exposure by asset.
    
    Returns list of asset exposures:
        - asset: Asset symbol (BTC, ETH, etc.)
        - value: Exposure value in USD
        - percentage: Percentage of total portfolio
        - positions_count: Number of open positions
    """
    user_id = str(current_user.id)
    return await service.get_portfolio_exposure(user_id)


@router.get("/equity-curve")
async def get_equity_curve(
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    current_user = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Get historical equity curve.
    
    Query Params:
        - days: Number of days (1-365, default 30)
    
    Returns list of equity points:
        - timestamp: Timestamp
        - equity: Equity value
        - drawdown: Drawdown percentage
    """
    user_id = str(current_user.id)
    return await service.get_equity_curve(user_id, days)


@router.get("/positions")
async def get_all_positions(
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    current_user = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Get all open positions summary.
    
    Query Params:
        - limit: Page limit (1-100, default 50)
        - offset: Page offset (default 0)
    
    Returns:
        - positions: List of position data
        - total: Total count
        - limit: Page limit
        - offset: Page offset
    """
    user_id = str(current_user.id)
    return await service.get_all_positions(user_id, limit, offset)


@router.get("/performance")
async def get_performance_metrics(
    current_user = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Get performance metrics.
    
    Returns:
        - sharpe_ratio: Sharpe ratio
        - sortino_ratio: Sortino ratio (downside deviation)
        - max_drawdown: Maximum drawdown percentage
        - win_rate: Win rate percentage
        - profit_factor: Profit factor (gross profit / gross loss)
    """
    user_id = str(current_user.id)
    return await service.get_performance_metrics(user_id)


@router.get("/metrics")
async def get_trading_metrics(
    current_user = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Get key trading metrics.
    
    Returns:
        - total_trades: Total number of trades
        - avg_profit: Average profit per winning trade
        - avg_loss: Average loss per losing trade
        - largest_win: Largest winning trade
        - largest_loss: Largest losing trade
    """
    user_id = str(current_user.id)
    return await service.get_trading_metrics(user_id)


@router.get("/trade-distribution")
async def get_trade_distribution(
    bins: int = Query(20, ge=10, le=50, description="Number of histogram bins"),
    current_user = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Get win/loss distribution chart data.
    
    Query Params:
        - bins: Number of histogram bins (10-50, default 20)
    
    Returns:
        - bins: List of bin centers (P&L values)
        - frequencies: List of frequencies (trade counts)
    """
    user_id = str(current_user.id)
    return await service.get_trade_distribution(user_id, bins)


@router.get("/drawdown-curve")
async def get_drawdown_curve(
    days: int = Query(90, ge=1, le=365, description="Number of days"),
    current_user = Depends(get_current_user),
    service: PortfolioService = Depends(get_portfolio_service)
):
    """
    Get drawdown over time.
    
    Query Params:
        - days: Number of days (1-365, default 90)
    
    Returns list of drawdown points:
        - date: Date
        - drawdown_pct: Drawdown percentage
        - underwater_days: Consecutive days in drawdown
    """
    user_id = str(current_user.id)
    return await service.get_drawdown_curve(user_id, days)
