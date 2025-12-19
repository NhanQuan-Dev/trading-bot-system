"""Unit tests for backtesting domain models."""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4

from src.trading.domain.backtesting import (
    BacktestStatus,
    BacktestMode,
    SlippageModel,
    CommissionModel,
    TradeDirection,
    BacktestConfig,
    BacktestTrade,
    BacktestPosition,
    BacktestResults,
    BacktestRun,
    PerformanceMetrics,
    EquityCurvePoint,
)


class TestBacktestConfig:
    """Test BacktestConfig value object."""
    
    def test_create_config(self):
        """Test creating backtest configuration."""
        config = BacktestConfig(
            mode="event_driven",
            initial_capital=Decimal("10000"),
            slippage_model="fixed",
            slippage_percent=Decimal("0.1"),
            commission_model="fixed_rate",
            commission_percent=Decimal("0.1"),
        )
        
        assert config.mode == "event_driven"
        assert config.initial_capital == Decimal("10000")
        assert config.slippage_model == "fixed"
        assert config.commission_model == "fixed_rate"
    
    def test_config_validation(self):
        """Test configuration validation."""
        # Should not raise for valid config
        config = BacktestConfig(
            mode="event_driven",
            initial_capital=Decimal("10000"),
        )
        
        assert config.initial_capital > 0


class TestBacktestTrade:
    """Test BacktestTrade entity."""
    
    def test_create_trade(self):
        """Test creating a trade."""
        trade = BacktestTrade(
            symbol="BTCUSDT",
            direction=TradeDirection.LONG,
            entry_price=Decimal("42000"),
            entry_quantity=Decimal("0.1"),
            exit_price=Decimal("43000"),
            exit_quantity=Decimal("0.1"),
            entry_time=datetime(2024, 1, 1, 10, 0, 0),
            exit_time=datetime(2024, 1, 1, 14, 0, 0),
            gross_pnl=Decimal("100"),
            entry_commission=Decimal("4.2"),
            exit_commission=Decimal("4.3"),
            entry_slippage=Decimal("0.5"),
            exit_slippage=Decimal("1.0"),
        )
        
        assert trade.symbol == "BTCUSDT"
        assert trade.direction == TradeDirection.LONG
        assert trade.entry_price == Decimal("42000")
        assert trade.exit_price == Decimal("43000")
    
    def test_close_trade(self):
        """Test closing a trade."""
        trade = BacktestTrade(
            symbol="BTCUSDT",
            direction=TradeDirection.LONG,
            entry_price=Decimal("42000"),
            entry_quantity=Decimal("0.1"),
            entry_time=datetime(2024, 1, 1, 10, 0, 0),
        )
        
        trade.close_trade(
            exit_time=datetime(2024, 1, 1, 14, 0, 0),
            exit_price=Decimal("43000"),
            commission=Decimal("8.5"),
            slippage=Decimal("1.5"),
        )
        
        assert trade.exit_price == Decimal("43000")
        assert trade.exit_time == datetime(2024, 1, 1, 14, 0, 0)
        assert trade.net_pnl == Decimal("90")  # 100 - 8.5 - 1.5
        assert trade.is_winner is True
    
    def test_trade_pnl_calculation(self):
        """Test P&L calculation."""
        # Long trade - winner
        long_trade = BacktestTrade(
            symbol="BTCUSDT",
            direction=TradeDirection.LONG,
            entry_price=Decimal("42000"),
            entry_quantity=Decimal("0.1"),
            entry_time=datetime(2024, 1, 1, 10, 0, 0),
        )
        long_trade.close_trade(
            exit_time=datetime(2024, 1, 1, 14, 0, 0),
            exit_price=Decimal("43000"),
            commission=Decimal("5"),
            slippage=Decimal("2.5"),
        )
        
        # Net P&L = Gross P&L - exit_commission - exit_slippage = 100 - 5 - 2.5 = 92.5
        assert long_trade.net_pnl == Decimal("92.5")
        assert long_trade.is_winner is True
        
        # Short trade - winner
        short_trade = BacktestTrade(
            symbol="BTCUSDT",
            direction=TradeDirection.SHORT,
            entry_price=Decimal("42000"),
            entry_quantity=Decimal("0.1"),
            entry_time=datetime(2024, 1, 1, 10, 0, 0),
        )
        short_trade.close_trade(
            exit_time=datetime(2024, 1, 1, 14, 0, 0),
            exit_price=Decimal("41000"),
            commission=Decimal("5"),
            slippage=Decimal("2.5"),
        )
        
        # Net P&L = Gross P&L - exit_commission - exit_slippage = 100 - 5 - 2.5 = 92.5
        assert short_trade.net_pnl == Decimal("92.5")
        assert short_trade.is_winner is True


class TestBacktestPosition:
    """Test BacktestPosition entity."""
    
    def test_create_position(self):
        """Test creating a position."""
        position = BacktestPosition(
            symbol="BTCUSDT",
            direction=TradeDirection.LONG,
            quantity=Decimal("0.1"),
            avg_entry_price=Decimal("42000"),
        )
        
        assert position.direction == TradeDirection.LONG
        assert position.avg_entry_price == Decimal("42000")
        assert position.quantity == Decimal("0.1")
        assert position.unrealized_pnl == Decimal("0")
    
    def test_update_unrealized_pnl_long(self):
        """Test updating unrealized P&L for long position."""
        position = BacktestPosition(
            symbol="BTCUSDT",
            direction=TradeDirection.LONG,
            quantity=Decimal("0.1"),
            avg_entry_price=Decimal("42000"),
        )
        
        # Price goes up - profit
        position.update_unrealized_pnl(Decimal("43000"))
        assert position.unrealized_pnl == Decimal("100")  # (43000 - 42000) * 0.1
        
        # Price goes down - loss
        position.update_unrealized_pnl(Decimal("41000"))
        assert position.unrealized_pnl == Decimal("-100")  # (41000 - 42000) * 0.1
    
    def test_update_unrealized_pnl_short(self):
        """Test updating unrealized P&L for short position."""
        position = BacktestPosition(
            symbol="BTCUSDT",
            direction=TradeDirection.SHORT,
            quantity=Decimal("0.1"),
            avg_entry_price=Decimal("42000"),
        )
        
        # Price goes down - profit
        position.update_unrealized_pnl(Decimal("41000"))
        assert position.unrealized_pnl == Decimal("100")  # (42000 - 41000) * 0.1
        
        # Price goes up - loss
        position.update_unrealized_pnl(Decimal("43000"))
        assert position.unrealized_pnl == Decimal("-100")  # (42000 - 43000) * 0.1


class TestBacktestRun:
    """Test BacktestRun entity."""
    
    def test_create_backtest_run(self, sample_user_id, sample_strategy_id, sample_backtest_config):
        """Test creating a backtest run."""
        run = BacktestRun(
            user_id=sample_user_id,
            strategy_id=sample_strategy_id,
            config=sample_backtest_config,
        )
        
        assert run.user_id == sample_user_id
        assert run.strategy_id == sample_strategy_id
        assert run.status == BacktestStatus.PENDING
        assert run.progress_percent == 0
    
    def test_start_backtest(self, sample_user_id, sample_strategy_id, sample_backtest_config):
        """Test starting a backtest."""
        run = BacktestRun(
            user_id=sample_user_id,
            strategy_id=sample_strategy_id,
            config=sample_backtest_config,
        )
        
        run.start()
        
        assert run.status == BacktestStatus.RUNNING
        assert run.started_at is not None
    
    def test_complete_backtest(self, sample_user_id, sample_strategy_id, sample_backtest_config):
        """Test completing a backtest."""
        run = BacktestRun(
            user_id=sample_user_id,
            strategy_id=sample_strategy_id,
            config=sample_backtest_config,
        )
        
        run.start()
        
        # Create BacktestResults
        from src.trading.domain.backtesting import BacktestResults
        results = BacktestResults(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            duration_days=365,
            initial_capital=Decimal("10000"),
            final_equity=Decimal("12000"),
            peak_equity=Decimal("13000"),
            trades=[],
            equity_curve=[],
            metadata={},
        )
        run.complete(results)
        
        assert run.status == BacktestStatus.COMPLETED
        assert run.completed_at is not None
        assert run.results is not None
        assert run.results.final_equity == Decimal("12000")
    
    def test_fail_backtest(self, sample_user_id, sample_strategy_id, sample_backtest_config):
        """Test failing a backtest."""
        run = BacktestRun(
            user_id=sample_user_id,
            strategy_id=sample_strategy_id,
            config=sample_backtest_config,
        )
        
        run.start()
        run.fail("Test error message")
        
        assert run.status == BacktestStatus.FAILED
        assert run.error_message == "Test error message"
    
    def test_cancel_backtest(self, sample_user_id, sample_strategy_id, sample_backtest_config):
        """Test cancelling a backtest."""
        run = BacktestRun(
            user_id=sample_user_id,
            strategy_id=sample_strategy_id,
            config=sample_backtest_config,
        )
        
        run.start()
        run.cancel()
        
        assert run.status == BacktestStatus.CANCELLED
    
    def test_update_progress(self, sample_user_id, sample_strategy_id, sample_backtest_config):
        """Test updating progress."""
        run = BacktestRun(
            user_id=sample_user_id,
            strategy_id=sample_strategy_id,
            config=sample_backtest_config,
        )
        
        run.start()
        run.update_progress(50)
        
        assert run.progress_percent == 50
        
        run.update_progress(100)
        assert run.progress_percent == 100


class TestPerformanceMetrics:
    """Test PerformanceMetrics value object."""
    
    def test_create_metrics(self):
        """Test creating performance metrics."""
        metrics = PerformanceMetrics(
            total_return=Decimal("20.5"),
            annual_return=Decimal("21.3"),
            compound_annual_growth_rate=Decimal("20.8"),
            sharpe_ratio=Decimal("1.85"),
            sortino_ratio=Decimal("2.34"),
            calmar_ratio=Decimal("1.45"),
            max_drawdown=Decimal("-15.23"),
            max_drawdown_duration_days=45,
            volatility=Decimal("12.45"),
            downside_deviation=Decimal("8.34"),
            win_rate=Decimal("62.5"),
            profit_factor=Decimal("2.15"),
            payoff_ratio=Decimal("1.85"),
            expected_value=Decimal("54.50"),
            total_trades=45,
            winning_trades=28,
            losing_trades=17,
            break_even_trades=0,
            average_trade_pnl=Decimal("54.50"),
            average_winning_trade=Decimal("125.30"),
            average_losing_trade=Decimal("-67.80"),
            largest_winning_trade=Decimal("450.00"),
            largest_losing_trade=Decimal("-230.00"),
            max_consecutive_wins=8,
            max_consecutive_losses=4,
            average_exposure_percent=Decimal("85.5"),
            max_simultaneous_positions=1,
            risk_of_ruin=Decimal("2.5"),
        )
        
        assert metrics.total_return == Decimal("20.5")
        assert metrics.sharpe_ratio == Decimal("1.85")
        assert metrics.win_rate == Decimal("62.5")
        assert metrics.total_trades == 45
        assert metrics.winning_trades == 28
        assert metrics.losing_trades == 17


class TestEquityCurvePoint:
    """Test EquityCurvePoint value object."""
    
    def test_create_equity_point(self):
        """Test creating equity curve point."""
        point = EquityCurvePoint(
            timestamp=datetime(2024, 1, 1, 10, 0, 0),
            equity=Decimal("10500"),
            cash=Decimal("5000"),
            positions_value=Decimal("5500"),
            drawdown=Decimal("500"),
            drawdown_percent=Decimal("-4.76"),
            return_percent=Decimal("5.0"),
        )
        
        assert point.timestamp == datetime(2024, 1, 1, 10, 0, 0)
        assert point.equity == Decimal("10500")
        assert point.drawdown_percent == Decimal("-4.76")
        assert point.return_percent == Decimal("5.0")
