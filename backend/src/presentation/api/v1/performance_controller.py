"""
Performance Analytics Controller for trading platform API.

Provides REST endpoints for comprehensive performance metrics, risk analysis,
and portfolio insights.
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from trading.infrastructure.persistence.database import get_db
from trading.interfaces.dependencies.auth import get_current_user
from trading.infrastructure.persistence.models.core_models import UserModel
from application.services.performance_analytics_service import (
    PerformanceAnalyticsService,
    PerformanceOverview,
    DailyReturn,
    MonthlyPerformance,
    BotPerformance,
    StrategyPerformance,
    RiskMetrics
)


router = APIRouter(prefix="/api/performance", tags=["performance"])


@router.get("/overview", response_model=PerformanceOverview)
async def get_performance_overview(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> PerformanceOverview:
    """
    Get comprehensive performance overview for user's portfolio.
    
    Returns key performance metrics including:
    - Total return percentage
    - Sharpe ratio (risk-adjusted return)
    - Sortino ratio (downside risk-adjusted return)
    - Maximum drawdown
    - Calmar ratio (return/max drawdown)
    - Win rate
    - Profit factor
    """
    service = PerformanceAnalyticsService(db)
    
    # Parse optional date parameters
    start_dt = None
    end_dt = None
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
    
    try:
        overview = await service.get_performance_overview(
            user_id=current_user.id,
            start_date=start_dt,
            end_date=end_dt
        )
        return overview
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate performance overview: {str(e)}")


@router.get("/returns/daily", response_model=List[DailyReturn])
async def get_daily_returns(
    days: int = Query(90, ge=1, le=365, description="Number of days to analyze"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[DailyReturn]:
    """
    Get daily returns chart data.
    
    Returns daily return percentages and cumulative returns for the specified period.
    Useful for creating equity curve charts and analyzing day-to-day performance.
    """
    service = PerformanceAnalyticsService(db)
    
    try:
        daily_returns = await service.get_daily_returns(
            user_id=current_user.id,
            days=days
        )
        return daily_returns
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate daily returns: {str(e)}")


@router.get("/returns/monthly", response_model=List[MonthlyPerformance])
async def get_monthly_performance(
    months: int = Query(12, ge=1, le=24, description="Number of months to analyze"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[MonthlyPerformance]:
    """
    Get monthly performance breakdown.
    
    Returns monthly return percentages, trade counts, and win rates.
    Useful for analyzing seasonal patterns and monthly consistency.
    """
    service = PerformanceAnalyticsService(db)
    
    try:
        monthly_performance = await service.get_monthly_performance(
            user_id=current_user.id,
            months=months
        )
        return monthly_performance
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate monthly performance: {str(e)}")


@router.get("/metrics/by-bot", response_model=List[BotPerformance])
async def get_bot_performance_comparison(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[BotPerformance]:
    """
    Get performance comparison across all user's bots.
    
    Returns performance metrics for each bot including:
    - Total P&L
    - Win rate
    - Sharpe ratio
    - Trade count
    
    Sorted by total P&L (best performing first).
    """
    service = PerformanceAnalyticsService(db)
    
    try:
        bot_performance = await service.get_bot_performance_comparison(
            user_id=current_user.id
        )
        return bot_performance
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate bot performance: {str(e)}")


@router.get("/metrics/by-strategy", response_model=List[StrategyPerformance])
async def get_strategy_performance_comparison(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[StrategyPerformance]:
    """
    Get performance comparison by strategy.
    
    Returns aggregated performance metrics for each strategy including:
    - Total P&L across all bots using this strategy
    - Trade count
    - Average profit per trade
    - Number of bots using this strategy
    
    Sorted by total P&L (best performing first).
    """
    service = PerformanceAnalyticsService(db)
    
    try:
        strategy_performance = await service.get_strategy_performance_comparison(
            user_id=current_user.id
        )
        return strategy_performance
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate strategy performance: {str(e)}")


@router.get("/risk-metrics", response_model=RiskMetrics)
async def get_risk_metrics(
    days: int = Query(30, ge=7, le=90, description="Number of days for risk analysis"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> RiskMetrics:
    """
    Get comprehensive risk analysis metrics.
    
    Returns advanced risk metrics including:
    - Value at Risk (VaR) at 95% confidence level
    - Conditional Value at Risk (CVaR) - expected loss beyond VaR
    - Volatility (standard deviation of returns)
    - Beta (market sensitivity, placeholder)
    - Correlation with BTC (if market data available)
    
    These metrics help assess portfolio risk and compare risk-adjusted returns.
    """
    service = PerformanceAnalyticsService(db)
    
    try:
        risk_metrics = await service.get_risk_metrics(
            user_id=current_user.id,
            days=days
        )
        return risk_metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate risk metrics: {str(e)}")