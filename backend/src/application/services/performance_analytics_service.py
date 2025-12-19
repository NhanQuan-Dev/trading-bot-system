"""
Performance Analytics Service - Phân tích hiệu suất giao dịch và rủi ro.

Mục đích:
- Tính toán metrics hiệu suất như Sharpe ratio, drawdown, win rate.
- Phân tích returns hàng ngày/tháng, portfolio insights.

Liên quan đến file nào:
- Sử dụng models từ trading/infrastructure/persistence/models/core_models.py (BotModel, TradeModel, etc.).
- Khi gặp bug: Kiểm tra data trong DB, verify calculations với pandas/numpy, hoặc log trong shared/exceptions/.
"""

"""
Performance Analytics Service for trading platform.

Provides comprehensive performance metrics, risk analysis, and portfolio insights
for trading strategies and portfolios.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload

from trading.infrastructure.persistence.models.core_models import (
    BotModel, TradeModel, PositionModel, UserModel
)


@dataclass
class PerformanceOverview:
    """Performance overview data transfer object - DTO cho tổng quan hiệu suất."""
    total_return_pct: float  # Tổng return %
    sharpe_ratio: float  # Sharpe ratio (rủi ro điều chỉnh)
    sortino_ratio: float  # Sortino ratio (chỉ downside risk)
    max_drawdown: float  # Max drawdown %
    calmar_ratio: float  # Calmar ratio (return/drawdown)
    win_rate: float  # Tỷ lệ thắng %
    profit_factor: float  # Profit factor (profit/loss ratio)


@dataclass
class DailyReturn:
    """Daily return data transfer object - DTO cho return hàng ngày."""
    date: str  # Ngày
    return_pct: float  # Return %
    cumulative_return_pct: float  # Return tích lũy %


@dataclass
class MonthlyPerformance:
    """Monthly performance data transfer object - DTO cho hiệu suất tháng."""
    month: str  # Tháng
    return_pct: float  # Return %
    trades_count: int  # Số trades
    win_rate: float  # Win rate %


@dataclass
class BotPerformance:
    """Bot performance comparison data."""
    bot_id: int
    bot_name: str
    total_pnl: float
    win_rate: float
    sharpe_ratio: float
    trades_count: int


@dataclass
class StrategyPerformance:
    """Strategy performance comparison data."""
    strategy_id: int
    strategy_name: str
    total_pnl: float
    trades_count: int
    avg_profit: float
    bots_count: int


@dataclass
class RiskMetrics:
    """Risk analysis metrics."""
    var_95: float  # Value at Risk (95%)
    cvar_95: float  # Conditional VaR (95%)
    volatility: float
    beta: float
    correlation_btc: Optional[float]


class PerformanceAnalyticsService:
    """Service for performance analytics and portfolio insights."""
    
    def __init__(self, db_session: AsyncSession):
        """Initialize the performance analytics service."""
        self.db = db_session
    
    async def get_performance_overview(
        self, 
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> PerformanceOverview:
        """
        Get comprehensive performance overview for user's portfolio.
        
        Args:
            user_id: User ID to analyze
            start_date: Start date for analysis (default: 30 days ago)
            end_date: End date for analysis (default: now)
            
        Returns:
            PerformanceOverview with key metrics
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Get all trades for the period
        trades = await self._get_user_trades(user_id, start_date, end_date)
        
        if not trades:
            return PerformanceOverview(
                total_return_pct=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                max_drawdown=0.0,
                calmar_ratio=0.0,
                win_rate=0.0,
                profit_factor=0.0
            )
        
        # Calculate daily returns
        daily_returns = await self._calculate_daily_returns(trades)
        
        # Calculate individual metrics
        total_return_pct = self._calculate_total_return(daily_returns)
        sharpe_ratio = self._calculate_sharpe_ratio(daily_returns)
        sortino_ratio = self._calculate_sortino_ratio(daily_returns)
        max_drawdown = self._calculate_max_drawdown(daily_returns)
        calmar_ratio = self._calculate_calmar_ratio(daily_returns, max_drawdown)
        win_rate = self._calculate_win_rate(trades)
        profit_factor = self._calculate_profit_factor(trades)
        
        return PerformanceOverview(
            total_return_pct=total_return_pct,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            calmar_ratio=calmar_ratio,
            win_rate=win_rate,
            profit_factor=profit_factor
        )
    
    async def get_daily_returns(
        self, 
        user_id: int,
        days: int = 90
    ) -> List[DailyReturn]:
        """
        Get daily returns chart data.
        
        Args:
            user_id: User ID to analyze
            days: Number of days to analyze (default: 90)
            
        Returns:
            List of DailyReturn objects
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        end_date = datetime.utcnow()
        
        trades = await self._get_user_trades(user_id, start_date, end_date)
        daily_returns = await self._calculate_daily_returns(trades)
        
        result = []
        cumulative_return = 0.0
        
        for date, return_pct in daily_returns.items():
            cumulative_return += return_pct
            result.append(DailyReturn(
                date=date.strftime('%Y-%m-%d'),
                return_pct=round(return_pct, 4),
                cumulative_return_pct=round(cumulative_return, 4)
            ))
        
        return sorted(result, key=lambda x: x.date)
    
    async def get_monthly_performance(
        self, 
        user_id: int,
        months: int = 12
    ) -> List[MonthlyPerformance]:
        """
        Get monthly performance breakdown.
        
        Args:
            user_id: User ID to analyze
            months: Number of months to analyze (default: 12)
            
        Returns:
            List of MonthlyPerformance objects
        """
        start_date = datetime.utcnow() - timedelta(days=months * 30)
        end_date = datetime.utcnow()
        
        trades = await self._get_user_trades(user_id, start_date, end_date)
        
        # Group trades by month
        monthly_data = {}
        for trade in trades:
            month_key = trade.created_at.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = []
            monthly_data[month_key].append(trade)
        
        result = []
        for month, month_trades in monthly_data.items():
            total_pnl = sum(float(trade.pnl) for trade in month_trades if trade.pnl)
            trades_count = len(month_trades)
            win_trades = len([t for t in month_trades if t.pnl and t.pnl > 0])
            win_rate = (win_trades / trades_count * 100) if trades_count > 0 else 0
            
            # Calculate return percentage (simplified)
            return_pct = (total_pnl / 10000) * 100 if total_pnl else 0  # Assuming 10k base
            
            result.append(MonthlyPerformance(
                month=month,
                return_pct=round(return_pct, 2),
                trades_count=trades_count,
                win_rate=round(win_rate, 1)
            ))
        
        return sorted(result, key=lambda x: x.month)
    
    async def get_bot_performance_comparison(
        self, 
        user_id: int
    ) -> List[BotPerformance]:
        """
        Get performance comparison across all user's bots.
        
        Args:
            user_id: User ID to analyze
            
        Returns:
            List of BotPerformance objects
        """
        # Get all user's bots with their trades
        stmt = (
            select(BotModel)
            .where(BotModel.user_id == user_id)
            .options(selectinload(BotModel.trades))
        )
        result = await self.db.execute(stmt)
        bots = result.scalars().all()
        
        performance_list = []
        for bot in bots:
            trades = bot.trades
            
            if not trades:
                continue
            
            total_pnl = sum(float(trade.pnl) for trade in trades if trade.pnl)
            trades_count = len(trades)
            win_trades = len([t for t in trades if t.pnl and t.pnl > 0])
            win_rate = (win_trades / trades_count * 100) if trades_count > 0 else 0
            
            # Calculate daily returns for Sharpe ratio
            daily_returns = await self._calculate_daily_returns(trades)
            sharpe_ratio = self._calculate_sharpe_ratio(daily_returns)
            
            performance_list.append(BotPerformance(
                bot_id=bot.id,
                bot_name=bot.name,
                total_pnl=round(total_pnl, 2),
                win_rate=round(win_rate, 1),
                sharpe_ratio=round(sharpe_ratio, 3),
                trades_count=trades_count
            ))
        
        return sorted(performance_list, key=lambda x: x.total_pnl, reverse=True)
    
    async def get_strategy_performance_comparison(
        self, 
        user_id: int
    ) -> List[StrategyPerformance]:
        """
        Get performance comparison by strategy.
        
        Args:
            user_id: User ID to analyze
            
        Returns:
            List of StrategyPerformance objects
        """
        # Get aggregated data by strategy
        stmt = (
            select(
                BotModel.strategy_id,
                func.count(TradeModel.id).label('trades_count'),
                func.sum(TradeModel.pnl).label('total_pnl'),
                func.avg(TradeModel.pnl).label('avg_profit'),
                func.count(BotModel.id.distinct()).label('bots_count')
            )
            .select_from(BotModel)
            .join(TradeModel, BotModel.id == TradeModel.bot_id)
            .where(BotModel.user_id == user_id)
            .group_by(BotModel.strategy_id)
        )
        
        result = await self.db.execute(stmt)
        strategy_data = result.all()
        
        performance_list = []
        for row in strategy_data:
            performance_list.append(StrategyPerformance(
                strategy_id=row.strategy_id,
                strategy_name=f"Strategy {row.strategy_id}",  # Could join with strategy table
                total_pnl=float(row.total_pnl or 0),
                trades_count=row.trades_count,
                avg_profit=float(row.avg_profit or 0),
                bots_count=row.bots_count
            ))
        
        return sorted(performance_list, key=lambda x: x.total_pnl, reverse=True)
    
    async def get_risk_metrics(
        self, 
        user_id: int,
        days: int = 30
    ) -> RiskMetrics:
        """
        Calculate risk metrics for user's portfolio.
        
        Args:
            user_id: User ID to analyze
            days: Number of days for analysis
            
        Returns:
            RiskMetrics object with risk analysis
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        trades = await self._get_user_trades(user_id, start_date)
        
        if not trades:
            return RiskMetrics(
                var_95=0.0,
                cvar_95=0.0,
                volatility=0.0,
                beta=0.0,
                correlation_btc=None
            )
        
        daily_returns = await self._calculate_daily_returns(trades)
        returns_array = np.array(list(daily_returns.values()))
        
        # Calculate Value at Risk (95%)
        var_95 = float(np.percentile(returns_array, 5))
        
        # Calculate Conditional VaR (95%) - average of losses below VaR
        tail_returns = returns_array[returns_array <= var_95]
        cvar_95 = float(np.mean(tail_returns)) if len(tail_returns) > 0 else 0.0
        
        # Calculate volatility (standard deviation)
        volatility = float(np.std(returns_array))
        
        # Beta and correlation would require market data (placeholder)
        beta = 1.0  # Would need market index data
        correlation_btc = None  # Would need BTC price data
        
        return RiskMetrics(
            var_95=round(var_95, 4),
            cvar_95=round(cvar_95, 4),
            volatility=round(volatility, 4),
            beta=round(beta, 3),
            correlation_btc=correlation_btc
        )
    
    # Private helper methods
    
    async def _get_user_trades(
        self, 
        user_id: int, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[TradeModel]:
        """Get all trades for user in date range."""
        conditions = [BotModel.user_id == user_id]
        
        if start_date:
            conditions.append(TradeModel.created_at >= start_date)
        if end_date:
            conditions.append(TradeModel.created_at <= end_date)
        
        stmt = (
            select(TradeModel)
            .join(BotModel, TradeModel.bot_id == BotModel.id)
            .where(and_(*conditions))
            .order_by(TradeModel.created_at)
        )
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def _calculate_daily_returns(self, trades: List[TradeModel]) -> Dict[datetime, float]:
        """Calculate daily returns from trades."""
        daily_pnl = {}
        
        # Group trades by day
        for trade in trades:
            if not trade.pnl:
                continue
                
            day = trade.created_at.date()
            if day not in daily_pnl:
                daily_pnl[day] = 0.0
            daily_pnl[day] += float(trade.pnl)
        
        # Convert P&L to returns (simplified - assuming fixed capital)
        base_capital = 10000.0  # Assuming $10,000 base
        daily_returns = {}
        
        for day, pnl in daily_pnl.items():
            return_pct = (pnl / base_capital) * 100
            daily_returns[datetime.combine(day, datetime.min.time())] = return_pct
        
        return daily_returns
    
    def _calculate_total_return(self, daily_returns: Dict[datetime, float]) -> float:
        """Calculate total return percentage."""
        return sum(daily_returns.values())
    
    def _calculate_sharpe_ratio(
        self, 
        daily_returns: Dict[datetime, float], 
        risk_free_rate: float = 0.02
    ) -> float:
        """Calculate Sharpe ratio."""
        if not daily_returns:
            return 0.0
        
        returns_array = np.array(list(daily_returns.values()))
        mean_return = np.mean(returns_array)
        std_return = np.std(returns_array)
        
        if std_return == 0:
            return 0.0
        
        # Annualized Sharpe ratio
        daily_rf_rate = risk_free_rate / 365
        sharpe = (mean_return - daily_rf_rate) / std_return * np.sqrt(365)
        
        return float(sharpe)
    
    def _calculate_sortino_ratio(self, daily_returns: Dict[datetime, float]) -> float:
        """Calculate Sortino ratio (downside deviation only)."""
        if not daily_returns:
            return 0.0
        
        returns_array = np.array(list(daily_returns.values()))
        mean_return = np.mean(returns_array)
        
        # Only consider negative returns for downside deviation
        negative_returns = returns_array[returns_array < 0]
        if len(negative_returns) == 0:
            return float('inf') if mean_return > 0 else 0.0
        
        downside_std = np.std(negative_returns)
        if downside_std == 0:
            return 0.0
        
        sortino = mean_return / downside_std * np.sqrt(365)
        return float(sortino)
    
    def _calculate_max_drawdown(self, daily_returns: Dict[datetime, float]) -> float:
        """Calculate maximum drawdown."""
        if not daily_returns:
            return 0.0
        
        sorted_dates = sorted(daily_returns.keys())
        equity_curve = []
        cumulative = 0.0
        
        for date in sorted_dates:
            cumulative += daily_returns[date]
            equity_curve.append(cumulative)
        
        # Calculate drawdown at each point
        running_max = equity_curve[0]
        max_drawdown = 0.0
        
        for value in equity_curve:
            if value > running_max:
                running_max = value
            
            drawdown = (running_max - value) / running_max if running_max != 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
        
        return float(max_drawdown * 100)  # Return as percentage
    
    def _calculate_calmar_ratio(self, daily_returns: Dict[datetime, float], max_drawdown: float) -> float:
        """Calculate Calmar ratio (annual return / max drawdown)."""
        if not daily_returns or max_drawdown == 0:
            return 0.0
        
        annual_return = sum(daily_returns.values()) * 365 / len(daily_returns)
        calmar = annual_return / (max_drawdown / 100)  # Convert drawdown back to decimal
        
        return float(calmar)
    
    def _calculate_win_rate(self, trades: List[TradeModel]) -> float:
        """Calculate win rate percentage."""
        if not trades:
            return 0.0
        
        profitable_trades = len([t for t in trades if t.pnl and t.pnl > 0])
        total_trades = len([t for t in trades if t.pnl is not None])
        
        if total_trades == 0:
            return 0.0
        
        return (profitable_trades / total_trades) * 100
    
    def _calculate_profit_factor(self, trades: List[TradeModel]) -> float:
        """Calculate profit factor (gross profit / gross loss)."""
        if not trades:
            return 0.0
        
        gross_profit = sum(float(t.pnl) for t in trades if t.pnl and t.pnl > 0)
        gross_loss = sum(abs(float(t.pnl)) for t in trades if t.pnl and t.pnl < 0)
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        
        return gross_profit / gross_loss