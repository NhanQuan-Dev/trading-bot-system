"""Unit tests for metrics calculator."""

import pytest
from decimal import Decimal
from datetime import datetime

from src.trading.infrastructure.backtesting.metrics_calculator import MetricsCalculator
from src.trading.domain.backtesting import (
    BacktestTrade,
    TradeDirection,
    EquityCurvePoint,
)


class TestMetricsCalculator:
    """Test MetricsCalculator."""
    
    @pytest.fixture
    def calculator(self):
        """Create metrics calculator."""
        return MetricsCalculator()
    
    @pytest.fixture
    def sample_trades(self):
        """Create sample trades."""
        trades = []
        
        # 3 winning trades
        for i in range(3):
            trade = BacktestTrade(
                symbol="BTCUSDT",
                direction=TradeDirection.LONG,
                entry_price=Decimal("42000"),
                entry_quantity=Decimal("0.1"),
                entry_time=datetime(2024, 1, i+1, 10, 0, 0),
            )
            trade.close_trade(
                exit_time=datetime(2024, 1, i+1, 14, 0, 0),
                exit_price=Decimal("43000"),
                commission=Decimal("10"),
                slippage=Decimal("5")
            )
            trades.append(trade)
        
        # 2 losing trades
        for i in range(2):
            trade = BacktestTrade(
                symbol="BTCUSDT",
                direction=TradeDirection.LONG,
                entry_price=Decimal("42000"),
                entry_quantity=Decimal("0.1"),
                entry_time=datetime(2024, 1, i+4, 10, 0, 0),
            )
            trade.close_trade(
                exit_time=datetime(2024, 1, i+4, 14, 0, 0),
                exit_price=Decimal("41500"),
                commission=Decimal("10"),
                slippage=Decimal("5")
            )
            trades.append(trade)
        
        return trades
    
    @pytest.fixture
    def sample_equity_curve(self):
        """Create sample equity curve."""
        curve = []
        equity = Decimal("10000")
        
        for i in range(100):
            equity += Decimal(str((i % 10 - 5) * 10))
            return_pct = ((equity - Decimal("10000")) / Decimal("10000") * Decimal("100"))
            point = EquityCurvePoint(
                timestamp=datetime(2024, 1, 1, i % 24, 0, 0),
                equity=equity,
                cash=equity * Decimal("0.5"),
                positions_value=equity * Decimal("0.5"),
                drawdown=Decimal("0"),
                drawdown_percent=Decimal("0"),
                return_percent=return_pct,
            )
            curve.append(point)
        
        return curve
    
    def test_calculate_empty_metrics(self, calculator):
        """Test calculating metrics with no trades."""
        metrics = calculator.calculate_performance_metrics(
            trades=[],
            equity_curve=[],
            initial_capital=Decimal("10000"),
            duration_days=365,
        )
        
        assert metrics.total_trades == 0
        assert metrics.total_return == Decimal("0")
        assert metrics.win_rate == Decimal("0")
    
    def test_calculate_basic_metrics(self, calculator, sample_trades, sample_equity_curve):
        """Test calculating basic metrics."""
        metrics = calculator.calculate_performance_metrics(
            trades=sample_trades,
            equity_curve=sample_equity_curve,
            initial_capital=Decimal("10000"),
            duration_days=365,
        )
        
        # Basic stats
        assert metrics.total_trades == 5
        assert metrics.winning_trades == 3
        assert metrics.losing_trades == 2
        
        # Win rate should be 60%
        assert metrics.win_rate == Decimal("60")
        
        # Profit factor = gross profit / gross loss
        assert metrics.profit_factor > 0
    
    def test_win_rate_calculation(self, calculator, sample_trades, sample_equity_curve):
        """Test win rate calculation."""
        metrics = calculator.calculate_performance_metrics(
            trades=sample_trades,
            equity_curve=sample_equity_curve,
            initial_capital=Decimal("10000"),
            duration_days=365,
        )
        
        # 3 winners out of 5 trades = 60%
        assert metrics.win_rate == Decimal("60")
    
    def test_profit_factor_calculation(self, calculator, sample_trades, sample_equity_curve):
        """Test profit factor calculation."""
        metrics = calculator.calculate_performance_metrics(
            trades=sample_trades,
            equity_curve=sample_equity_curve,
            initial_capital=Decimal("10000"),
            duration_days=365,
        )
        
        # Profit factor = gross profit / gross loss
        # Gross profit = 3 * 100 = 300
        # Gross loss = 2 * 50 = 100
        # Profit factor = 300 / 100 = 3.0
        assert metrics.profit_factor == Decimal("3")
    
    def test_payoff_ratio_calculation(self, calculator, sample_trades, sample_equity_curve):
        """Test payoff ratio calculation."""
        metrics = calculator.calculate_performance_metrics(
            trades=sample_trades,
            equity_curve=sample_equity_curve,
            initial_capital=Decimal("10000"),
            duration_days=365,
        )
        
        # Average win = (100-10-5) = 85
        # Average loss = abs((-50-10-5)) = 65
        # Payoff ratio = 85 / 65 ≈ 1.31
        assert metrics.payoff_ratio > Decimal("1")
    
    def test_volatility_calculation(self, calculator):
        """Test volatility calculation."""
        # Create returns with known volatility
        returns = [1.0, -1.0, 2.0, -2.0, 0.5, -0.5] * 10
        
        volatility = calculator._calculate_volatility(returns)
        
        assert volatility > Decimal("0")
    
    def test_sharpe_ratio_calculation(self, calculator):
        """Test Sharpe ratio calculation."""
        annual_return = Decimal("20")
        volatility = Decimal("15")
        
        sharpe = calculator._calculate_sharpe_ratio(annual_return, volatility)
        
        # Sharpe = (20 - 2) / 15 = 1.2 (assuming 2% risk-free rate)
        assert sharpe > Decimal("1")
    
    def test_max_consecutive_wins(self, calculator):
        """Test max consecutive wins calculation."""
        trades = []
        
        # Create pattern: W W W L W W L
        win_pattern = [True, True, True, False, True, True, False]
        
        for i, is_win in enumerate(win_pattern):
            trade = BacktestTrade(
                symbol="BTCUSDT",
                direction=TradeDirection.LONG,
                entry_price=Decimal("42000"),
                entry_quantity=Decimal("0.1"),
                entry_time=datetime(2024, 1, i+1, 10, 0, 0),
            )
            trade.close_trade(
                exit_time=datetime(2024, 1, i+1, 14, 0, 0),
                exit_price=Decimal("43000") if is_win else Decimal("41500"),
                commission=Decimal("10"),
                slippage=Decimal("5")
            )
            trades.append(trade)
        
        max_wins = calculator._calculate_max_consecutive_wins(trades)
        
        # Pattern has max 3 consecutive wins
        assert max_wins == 3
    
    def test_max_consecutive_losses(self, calculator):
        """Test max consecutive losses calculation."""
        trades = []
        
        # Create pattern: L L W L L L W
        loss_pattern = [False, False, True, False, False, False, True]
        
        for i, is_loss in enumerate(loss_pattern):
            trade = BacktestTrade(
                symbol="BTCUSDT",
                direction=TradeDirection.LONG,
                entry_price=Decimal("42000"),
                entry_quantity=Decimal("0.1"),
                entry_time=datetime(2024, 1, i+1, 10, 0, 0),
            )
            trade.close_trade(
                exit_time=datetime(2024, 1, i+1, 14, 0, 0),
                exit_price=Decimal("41500") if not is_loss else Decimal("43000"),
                commission=Decimal("10"),
                slippage=Decimal("5")
            )
            trades.append(trade)
        
        max_losses = calculator._calculate_max_consecutive_losses(trades)
        
        # Pattern has max 3 consecutive losses
        assert max_losses == 3
