"""Integration tests for backtesting use cases and repository.

These tests verify the integration between domain, application, and infrastructure layers.
"""

import pytest
from decimal import Decimal
from datetime import datetime
from uuid import uuid4

from src.trading.domain.backtesting import (
    BacktestRun,
    BacktestStatus,
    BacktestConfig,
    BacktestTrade,
    TradeDirection,
)


@pytest.fixture
def sample_user_id():
    """Sample user ID for tests."""
    return uuid4()


@pytest.fixture
def sample_strategy_id():
    """Sample strategy ID for tests."""
    return uuid4()


@pytest.fixture
def sample_backtest_config():
    """Sample backtest configuration."""
    return BacktestConfig(
        mode="event_driven",
        initial_capital=Decimal("10000"),
        slippage_model="fixed",
        slippage_percent=Decimal("0.001"),
        commission_model="fixed_rate",
        commission_percent=Decimal("0.001"),
    )


class TestBacktestDomainIntegration:
    """Test domain model integration."""
    
    def test_backtest_run_lifecycle(self, sample_user_id, sample_strategy_id, sample_backtest_config):
        """Test complete backtest run lifecycle."""
        
        # Create backtest run
        backtest_run = BacktestRun(
            user_id=sample_user_id,
            strategy_id=sample_strategy_id,
            name="Integration Test Backtest",
            symbol="BTCUSDT",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            timeframe="1h",
            config=sample_backtest_config,
        )
        
        assert backtest_run.status == BacktestStatus.PENDING
        assert backtest_run.progress_percent == Decimal("0")
        
        # Start backtest
        backtest_run.start()
        
        assert backtest_run.status == BacktestStatus.RUNNING
        assert backtest_run.started_at is not None
        assert backtest_run._current_equity == Decimal("10000")
        
        # Update progress
        backtest_run.update_progress(Decimal("50"))
        assert backtest_run.progress_percent == Decimal("50")
        
        # Complete backtest
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
        
        backtest_run.complete(results)
        
        assert backtest_run.status == BacktestStatus.COMPLETED
        assert backtest_run.completed_at is not None
        assert backtest_run.results is not None
        assert backtest_run.progress_percent == Decimal("100")
    
    def test_backtest_run_failure(self, sample_user_id, sample_strategy_id, sample_backtest_config):
        """Test backtest run failure handling."""
        
        backtest_run = BacktestRun(
            user_id=sample_user_id,
            strategy_id=sample_strategy_id,
            name="Failed Test",
            symbol="BTCUSDT",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            timeframe="1h",
            config=sample_backtest_config,
        )
        
        backtest_run.start()
        
        # Fail backtest
        error_message = "Insufficient market data"
        backtest_run.fail(error_message)
        
        assert backtest_run.status == BacktestStatus.FAILED
        assert backtest_run.error_message == error_message
        assert backtest_run.completed_at is not None
    
    def test_backtest_run_cancellation(self, sample_user_id, sample_strategy_id, sample_backtest_config):
        """Test backtest run cancellation."""
        
        backtest_run = BacktestRun(
            user_id=sample_user_id,
            strategy_id=sample_strategy_id,
            name="Cancelled Test",
            symbol="BTCUSDT",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            timeframe="1h",
            config=sample_backtest_config,
        )
        
        backtest_run.start()
        
        # Cancel backtest
        backtest_run.cancel()
        
        assert backtest_run.status == BacktestStatus.CANCELLED
        assert backtest_run.completed_at is not None
    
    def test_backtest_with_trades(self, sample_user_id, sample_strategy_id, sample_backtest_config):
        """Test backtest with trade execution."""
        
        backtest_run = BacktestRun(
            user_id=sample_user_id,
            strategy_id=sample_strategy_id,
            name="Trade Execution Test",
            symbol="BTCUSDT",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            timeframe="1h",
            config=sample_backtest_config,
        )
        
        backtest_run.start()
        
        # Create some trades
        trade1 = BacktestTrade(
            symbol="BTCUSDT",
            direction=TradeDirection.LONG,
            entry_price=Decimal("42000"),
            entry_quantity=Decimal("0.1"),
            entry_time=datetime(2024, 1, 1, 10, 0, 0),
        )
        trade1.close_trade(
            exit_time=datetime(2024, 1, 1, 14, 0, 0),
            exit_price=Decimal("43000"),
            commission=Decimal("8.5"),
            slippage=Decimal("1.5"),
        )
        
        trade2 = BacktestTrade(
            symbol="BTCUSDT",
            direction=TradeDirection.LONG,
            entry_price=Decimal("43000"),
            entry_quantity=Decimal("0.1"),
            entry_time=datetime(2024, 1, 2, 10, 0, 0),
        )
        trade2.close_trade(
            exit_time=datetime(2024, 1, 2, 14, 0, 0),
            exit_price=Decimal("42500"),
            commission=Decimal("8.5"),
            slippage=Decimal("1.5"),
        )
        
        from src.trading.domain.backtesting import BacktestResults
        
        results = BacktestResults(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            duration_days=365,
            initial_capital=Decimal("10000"),
            final_equity=Decimal("10080"),  # Small profit
            peak_equity=Decimal("10100"),
            trades=[trade1, trade2],
            equity_curve=[],
            metadata={},
        )
        
        backtest_run.complete(results)
        
        assert backtest_run.status == BacktestStatus.COMPLETED
        assert backtest_run.results.total_trades == 2
        assert backtest_run.results.winning_trades == 1
        assert backtest_run.results.losing_trades == 1


class TestBacktestResultsCalculations:
    """Test backtest results calculations."""
    
    def test_total_return_calculation(self):
        """Test total return percentage calculation."""
        
        from src.trading.domain.backtesting import BacktestResults
        
        results = BacktestResults(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            duration_days=365,
            initial_capital=Decimal("10000"),
            final_equity=Decimal("12000"),  # 20% profit
            peak_equity=Decimal("13000"),
            trades=[],
            equity_curve=[],
            metadata={},
        )
        
        total_return = results.total_return
        
        assert total_return == Decimal("20.00")
    
    def test_win_rate_calculation(self):
        """Test win rate calculation from trades."""
        
        # Create winning and losing trades
        winning_trade = BacktestTrade(
            symbol="BTCUSDT",
            direction=TradeDirection.LONG,
            entry_price=Decimal("42000"),
            entry_quantity=Decimal("0.1"),
            entry_time=datetime(2024, 1, 1, 10, 0, 0),
        )
        winning_trade.close_trade(
            exit_time=datetime(2024, 1, 1, 14, 0, 0),
            exit_price=Decimal("43000"),
            commission=Decimal("8.5"),
            slippage=Decimal("1.5"),
        )
        
        losing_trade = BacktestTrade(
            symbol="BTCUSDT",
            direction=TradeDirection.LONG,
            entry_price=Decimal("43000"),
            entry_quantity=Decimal("0.1"),
            entry_time=datetime(2024, 1, 2, 10, 0, 0),
        )
        losing_trade.close_trade(
            exit_time=datetime(2024, 1, 2, 14, 0, 0),
            exit_price=Decimal("42500"),
            commission=Decimal("8.5"),
            slippage=Decimal("1.5"),
        )
        
        from src.trading.domain.backtesting import BacktestResults
        
        results = BacktestResults(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            duration_days=365,
            initial_capital=Decimal("10000"),
            final_equity=Decimal("10080"),
            peak_equity=Decimal("10100"),
            trades=[winning_trade, losing_trade],
            equity_curve=[],
            metadata={},
        )
        
        # 1 winner out of 2 trades = 50%
        assert results.win_rate == Decimal("50.00")
        assert results.winning_trades == 1
        assert results.losing_trades == 1
        assert results.total_trades == 2


class TestBacktestValidation:
    """Test backtest configuration validation."""
    
    def test_invalid_state_transitions(self, sample_user_id, sample_strategy_id, sample_backtest_config):
        """Test invalid state transitions are prevented."""
        
        backtest_run = BacktestRun(
            user_id=sample_user_id,
            strategy_id=sample_strategy_id,
            name="State Transition Test",
            symbol="BTCUSDT",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            timeframe="1h",
            config=sample_backtest_config,
        )
        
        # Cannot complete without starting
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
        
        with pytest.raises(ValueError):
            backtest_run.complete(results)
    
    def test_cannot_start_twice(self, sample_user_id, sample_strategy_id, sample_backtest_config):
        """Test backtest cannot be started twice."""
        
        backtest_run = BacktestRun(
            user_id=sample_user_id,
            strategy_id=sample_strategy_id,
            name="Double Start Test",
            symbol="BTCUSDT",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            timeframe="1h",
            config=sample_backtest_config,
        )
        
        backtest_run.start()
        
        # Cannot start again
        with pytest.raises(ValueError):
            backtest_run.start()
    
    def test_cannot_cancel_completed_backtest(self, sample_user_id, sample_strategy_id, sample_backtest_config):
        """Test cannot cancel already completed backtest."""
        
        backtest_run = BacktestRun(
            user_id=sample_user_id,
            strategy_id=sample_strategy_id,
            name="Cancel After Complete Test",
            symbol="BTCUSDT",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            timeframe="1h",
            config=sample_backtest_config,
        )
        
        backtest_run.start()
        
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
        
        backtest_run.complete(results)
        
        # Cannot cancel completed backtest
        with pytest.raises(ValueError):
            backtest_run.cancel()
