"""Performance metrics calculator for backtesting."""

import logging
from decimal import Decimal
from typing import List
from datetime import datetime
import math

from ...domain.backtesting import (
    BacktestTrade,
    PerformanceMetrics,
    DrawdownInfo,
    TradeStatistics,
    EquityCurvePoint,
)

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calculate comprehensive performance metrics from backtest results."""
    
    def calculate_performance_metrics(
        self,
        trades: List[BacktestTrade],
        equity_curve: List[EquityCurvePoint],
        initial_capital: Decimal,
        duration_days: int,
    ) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics."""
        
        if not trades:
            return self._empty_metrics()
        
        # Basic trade statistics
        total_trades = len(trades)
        winning_trades = [t for t in trades if t.is_winner]
        losing_trades = [t for t in trades if not t.is_winner]
        break_even_trades = [t for t in trades if t.net_pnl == 0]
        
        winning_count = len(winning_trades)
        losing_count = len(losing_trades)
        break_even_count = len(break_even_trades)
        
        # Returns
        total_return = self._calculate_total_return(equity_curve, initial_capital)
        annual_return = self._calculate_annual_return(total_return, duration_days)
        cagr = self._calculate_cagr(equity_curve, initial_capital, duration_days)
        
        # Risk metrics
        returns = [float(point.return_percent) for point in equity_curve]
        volatility = self._calculate_volatility(returns)
        downside_deviation = self._calculate_downside_deviation(returns)
        max_drawdown, max_dd_duration = self._calculate_max_drawdown(equity_curve)
        
        sharpe_ratio = self._calculate_sharpe_ratio(annual_return, volatility)
        sortino_ratio = self._calculate_sortino_ratio(annual_return, downside_deviation)
        calmar_ratio = self._calculate_calmar_ratio(annual_return, max_drawdown)
        
        # Win/Loss statistics
        win_rate = Decimal(winning_count) / Decimal(total_trades) * Decimal("100") if total_trades > 0 else Decimal("0")
        
        gross_profit = sum(t.gross_pnl for t in winning_trades)
        gross_loss = abs(sum(t.gross_pnl for t in losing_trades))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else Decimal("0")
        
        avg_win = sum(t.net_pnl for t in winning_trades) / Decimal(winning_count) if winning_count > 0 else Decimal("0")
        avg_loss = abs(sum(t.net_pnl for t in losing_trades) / Decimal(losing_count)) if losing_count > 0 else Decimal("0")
        payoff_ratio = avg_win / avg_loss if avg_loss > 0 else Decimal("0")
        
        # Trade amounts
        average_trade_pnl = sum(t.net_pnl for t in trades) / Decimal(total_trades)
        largest_win = max((t.net_pnl for t in winning_trades), default=Decimal("0"))
        largest_loss = min((t.net_pnl for t in losing_trades), default=Decimal("0"))
        
        # Expected value
        win_prob = float(win_rate) / 100
        loss_prob = 1 - win_prob
        expected_value = Decimal(str(win_prob * float(avg_win) - loss_prob * float(avg_loss)))
        
        # Consecutive trades
        max_consecutive_wins = self._calculate_max_consecutive_wins(trades)
        max_consecutive_losses = self._calculate_max_consecutive_losses(trades)
        
        # Exposure
        avg_exposure = self._calculate_average_exposure(trades, duration_days)
        
        # Risk of ruin (simplified Kelly criterion based)
        risk_of_ruin = self._calculate_risk_of_ruin(win_rate, payoff_ratio)
        
        return PerformanceMetrics(
            total_return=total_return,
            annual_return=annual_return,
            compound_annual_growth_rate=cagr,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_duration_days=max_dd_duration,
            volatility=volatility,
            downside_deviation=downside_deviation,
            win_rate=win_rate,
            profit_factor=profit_factor,
            payoff_ratio=payoff_ratio,
            expected_value=expected_value,
            total_trades=total_trades,
            winning_trades=winning_count,
            losing_trades=losing_count,
            break_even_trades=break_even_count,
            average_trade_pnl=average_trade_pnl,
            average_winning_trade=avg_win,
            average_losing_trade=avg_loss,
            largest_winning_trade=largest_win,
            largest_losing_trade=largest_loss,
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses,
            average_exposure_percent=avg_exposure,
            max_simultaneous_positions=1,  # Single position for now
            risk_of_ruin=risk_of_ruin,
        )
    
    def _empty_metrics(self) -> PerformanceMetrics:
        """Return empty metrics for no trades."""
        return PerformanceMetrics(
            total_return=Decimal("0"),
            annual_return=Decimal("0"),
            compound_annual_growth_rate=Decimal("0"),
            sharpe_ratio=Decimal("0"),
            sortino_ratio=Decimal("0"),
            calmar_ratio=Decimal("0"),
            max_drawdown=Decimal("0"),
            max_drawdown_duration_days=0,
            volatility=Decimal("0"),
            downside_deviation=Decimal("0"),
            win_rate=Decimal("0"),
            profit_factor=Decimal("0"),
            payoff_ratio=Decimal("0"),
            expected_value=Decimal("0"),
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            break_even_trades=0,
            average_trade_pnl=Decimal("0"),
            average_winning_trade=Decimal("0"),
            average_losing_trade=Decimal("0"),
            largest_winning_trade=Decimal("0"),
            largest_losing_trade=Decimal("0"),
            max_consecutive_wins=0,
            max_consecutive_losses=0,
            average_exposure_percent=Decimal("0"),
            max_simultaneous_positions=0,
            risk_of_ruin=Decimal("0"),
        )
    
    def _calculate_total_return(
        self,
        equity_curve: List[EquityCurvePoint],
        initial_capital: Decimal
    ) -> Decimal:
        """Calculate total return percentage."""
        if not equity_curve or initial_capital == 0:
            return Decimal("0")
        
        # EquityCurvePoint.equity is now float
        final_equity = Decimal(str(equity_curve[-1].equity))
        return ((final_equity - initial_capital) / initial_capital) * Decimal("100")
    
    def _calculate_annual_return(self, total_return: Decimal, duration_days: int) -> Decimal:
        """Calculate annualized return."""
        if duration_days <= 0:
            return Decimal("0")
        
        years = Decimal(duration_days) / Decimal("365.25")
        if years == 0:
            return total_return
        
        return total_return / years
    
    def _calculate_cagr(
        self,
        equity_curve: List[EquityCurvePoint],
        initial_capital: Decimal,
        duration_days: int
    ) -> Decimal:
        """Calculate Compound Annual Growth Rate."""
        if not equity_curve or duration_days <= 0 or initial_capital == 0:
            return Decimal("0")
        
        # Equity is float
        final_equity = equity_curve[-1].equity
        initial_capital_flt = float(initial_capital)
        years = duration_days / 365.25
        
        if years == 0:
            return Decimal("0")
        
        try:
            cagr = (pow(final_equity / initial_capital_flt, 1 / years) - 1) * 100
            return Decimal(str(cagr))
        except:
            return Decimal("0")
    
    def _calculate_volatility(self, returns: List[float]) -> Decimal:
        """Calculate volatility (standard deviation of returns)."""
        if len(returns) < 2:
            return Decimal("0")
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        volatility = math.sqrt(variance) * math.sqrt(252)  # Annualized
        
        return Decimal(str(volatility))
    
    def _calculate_downside_deviation(self, returns: List[float]) -> Decimal:
        """Calculate downside deviation (volatility of negative returns)."""
        negative_returns = [r for r in returns if r < 0]
        
        if len(negative_returns) < 2:
            return Decimal("0")
        
        mean_negative = sum(negative_returns) / len(negative_returns)
        variance = sum((r - mean_negative) ** 2 for r in negative_returns) / (len(negative_returns) - 1)
        downside_dev = math.sqrt(variance) * math.sqrt(252)
        
        return Decimal(str(downside_dev))
    
    def _calculate_max_drawdown(
        self,
        equity_curve: List[EquityCurvePoint]
    ) -> tuple[Decimal, int]:
        """Calculate maximum drawdown and its duration."""
        if not equity_curve:
            return Decimal("0"), 0
        
        max_dd = 0.0
        max_dd_duration = 0
        
        for point in equity_curve:
            # point.drawdown_percent is float
            if abs(point.drawdown_percent) > abs(max_dd):
                max_dd = point.drawdown_percent
            
            # Calculate drawdown duration
            # (simplified - would need start/end tracking for accuracy)
            if point.drawdown_percent < 0:
                max_dd_duration = max(max_dd_duration, 1)
        
        return Decimal(str(abs(max_dd))), max_dd_duration
    
    def _calculate_sharpe_ratio(
        self,
        annual_return: Decimal,
        volatility: Decimal,
        risk_free_rate: Decimal = Decimal("2.0")
    ) -> Decimal:
        """Calculate Sharpe ratio."""
        if volatility == 0:
            return Decimal("0")
        
        return (annual_return - risk_free_rate) / volatility
    
    def _calculate_sortino_ratio(
        self,
        annual_return: Decimal,
        downside_deviation: Decimal,
        risk_free_rate: Decimal = Decimal("2.0")
    ) -> Decimal:
        """Calculate Sortino ratio."""
        if downside_deviation == 0:
            return Decimal("0")
        
        return (annual_return - risk_free_rate) / downside_deviation
    
    def _calculate_calmar_ratio(
        self,
        annual_return: Decimal,
        max_drawdown: Decimal
    ) -> Decimal:
        """Calculate Calmar ratio."""
        if max_drawdown == 0:
            return Decimal("0")
        
        return annual_return / abs(max_drawdown)
    
    def _calculate_max_consecutive_wins(self, trades: List[BacktestTrade]) -> int:
        """Calculate maximum consecutive winning trades."""
        max_wins = 0
        current_wins = 0
        
        for trade in trades:
            if trade.is_winner:
                current_wins += 1
                max_wins = max(max_wins, current_wins)
            else:
                current_wins = 0
        
        return max_wins
    
    def _calculate_max_consecutive_losses(self, trades: List[BacktestTrade]) -> int:
        """Calculate maximum consecutive losing trades."""
        max_losses = 0
        current_losses = 0
        
        for trade in trades:
            if not trade.is_winner:
                current_losses += 1
                max_losses = max(max_losses, current_losses)
            else:
                current_losses = 0
        
        return max_losses
    
    def _calculate_average_exposure(
        self,
        trades: List[BacktestTrade],
        duration_days: int
    ) -> Decimal:
        """Calculate average market exposure percentage."""
        if duration_days == 0:
            return Decimal("0")
        
        total_seconds_in_market = sum(
            t.duration_seconds or 0 for t in trades
        )
        total_seconds = duration_days * 86400
        
        if total_seconds == 0:
            return Decimal("0")
        
        exposure = (total_seconds_in_market / total_seconds) * 100
        return Decimal(str(exposure))
    
    def _calculate_risk_of_ruin(
        self,
        win_rate: Decimal,
        payoff_ratio: Decimal
    ) -> Decimal:
        """Calculate risk of ruin (simplified)."""
        if win_rate == 0 or payoff_ratio == 0:
            return Decimal("100")
        
        win_prob = float(win_rate) / 100
        loss_prob = 1 - win_prob
        
        if payoff_ratio <= 1:
            return Decimal("50")  # Simplified
        
        # Simplified risk of ruin calculation
        ror = (loss_prob / win_prob) ** float(payoff_ratio)
        return Decimal(str(min(ror * 100, 100)))
