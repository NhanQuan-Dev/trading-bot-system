"""
Unit tests for Performance Analytics Service.
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from typing import List

from application.services.performance_analytics_service import (
    PerformanceAnalyticsService,
    PerformanceOverview,
    DailyReturn,
    MonthlyPerformance,
    BotPerformance,
    StrategyPerformance,
    RiskMetrics
)
from trading.infrastructure.persistence.models.core_models import (
    TradeModel, BotModel, PositionModel
)


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    return AsyncMock()


@pytest.fixture
def performance_service(mock_db_session):
    """Create performance analytics service with mock database."""
    return PerformanceAnalyticsService(mock_db_session)


@pytest.fixture
def sample_trades():
    """Create sample trades for testing."""
    trades = []
    base_date = datetime.utcnow() - timedelta(days=30)
    
    for i in range(20):
        trade = Mock(spec=TradeModel)
        trade.id = i + 1
        trade.pnl = Decimal('100') if i % 2 == 0 else Decimal('-50')  # Alternating profits/losses
        trade.created_at = base_date + timedelta(days=i)
        trade.bot_id = 1
        trades.append(trade)
    
    return trades


@pytest.fixture
def sample_bots():
    """Create sample bots for testing."""
    bots = []
    for i in range(3):
        bot = Mock(spec=BotModel)
        bot.id = i + 1
        bot.name = f"Bot {i + 1}"
        bot.strategy_id = i + 1
        bot.trades = []
        bots.append(bot)
    
    return bots


class TestPerformanceOverview:
    """Test performance overview calculations."""
    
    @pytest.mark.asyncio
    async def test_get_performance_overview_success(self, performance_service, sample_trades):
        """Test successful performance overview calculation."""
        # Mock the private methods
        performance_service._get_user_trades = AsyncMock(return_value=sample_trades)
        performance_service._calculate_daily_returns = AsyncMock(return_value={
            datetime.utcnow() - timedelta(days=i): 1.0 if i % 2 == 0 else -0.5
            for i in range(10)
        })
        
        result = await performance_service.get_performance_overview(user_id=1)
        
        assert isinstance(result, PerformanceOverview)
        assert result.total_return_pct == 5.0  # Sum of daily returns
        assert result.win_rate == 50.0  # 50% win rate from sample trades
        assert result.profit_factor == 2.0  # 1000 profit / 500 loss
    
    @pytest.mark.asyncio
    async def test_get_performance_overview_no_trades(self, performance_service):
        """Test performance overview with no trades."""
        performance_service._get_user_trades = AsyncMock(return_value=[])
        
        result = await performance_service.get_performance_overview(user_id=1)
        
        assert isinstance(result, PerformanceOverview)
        assert result.total_return_pct == 0.0
        assert result.sharpe_ratio == 0.0
        assert result.win_rate == 0.0
    
    @pytest.mark.asyncio
    async def test_get_performance_overview_with_dates(self, performance_service, sample_trades):
        """Test performance overview with custom date range."""
        start_date = datetime.utcnow() - timedelta(days=10)
        end_date = datetime.utcnow()
        
        performance_service._get_user_trades = AsyncMock(return_value=sample_trades)
        performance_service._calculate_daily_returns = AsyncMock(return_value={})
        
        await performance_service.get_performance_overview(
            user_id=1, start_date=start_date, end_date=end_date
        )
        
        performance_service._get_user_trades.assert_called_once_with(1, start_date, end_date)


class TestDailyReturns:
    """Test daily returns calculations."""
    
    @pytest.mark.asyncio
    async def test_get_daily_returns_success(self, performance_service, sample_trades):
        """Test successful daily returns calculation."""
        daily_returns_data = {
            datetime(2024, 1, 1): 1.5,
            datetime(2024, 1, 2): -0.5,
            datetime(2024, 1, 3): 2.0
        }
        
        performance_service._get_user_trades = AsyncMock(return_value=sample_trades)
        performance_service._calculate_daily_returns = AsyncMock(return_value=daily_returns_data)
        
        result = await performance_service.get_daily_returns(user_id=1, days=30)
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(item, DailyReturn) for item in result)
        
        # Check cumulative calculation
        assert result[0].cumulative_return_pct == 1.5
        assert result[1].cumulative_return_pct == 1.0  # 1.5 + (-0.5)
        assert result[2].cumulative_return_pct == 3.0  # 1.0 + 2.0
    
    @pytest.mark.asyncio
    async def test_get_daily_returns_empty_data(self, performance_service):
        """Test daily returns with no trades."""
        performance_service._get_user_trades = AsyncMock(return_value=[])
        performance_service._calculate_daily_returns = AsyncMock(return_value={})
        
        result = await performance_service.get_daily_returns(user_id=1, days=30)
        
        assert isinstance(result, list)
        assert len(result) == 0


class TestMonthlyPerformance:
    """Test monthly performance calculations."""
    
    @pytest.mark.asyncio
    async def test_get_monthly_performance_success(self, performance_service, sample_trades):
        """Test successful monthly performance calculation."""
        performance_service._get_user_trades = AsyncMock(return_value=sample_trades)
        
        result = await performance_service.get_monthly_performance(user_id=1, months=12)
        
        assert isinstance(result, list)
        assert all(isinstance(item, MonthlyPerformance) for item in result)
        
        # Should group trades by month
        if result:
            assert result[0].trades_count > 0
            assert 0 <= result[0].win_rate <= 100
    
    @pytest.mark.asyncio
    async def test_get_monthly_performance_empty_data(self, performance_service):
        """Test monthly performance with no trades."""
        performance_service._get_user_trades = AsyncMock(return_value=[])
        
        result = await performance_service.get_monthly_performance(user_id=1, months=12)
        
        assert isinstance(result, list)
        assert len(result) == 0


class TestBotPerformance:
    """Test bot performance comparison."""
    
    @pytest.mark.asyncio
    async def test_get_bot_performance_comparison_success(self, performance_service, sample_bots, sample_trades):
        """Test successful bot performance comparison."""
        # Add trades to first bot
        sample_bots[0].trades = sample_trades[:10]
        sample_bots[1].trades = sample_trades[10:]
        sample_bots[2].trades = []
        
        # Mock database query
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = sample_bots
        performance_service.db.execute = AsyncMock(return_value=mock_result)
        
        # Mock daily returns calculation
        performance_service._calculate_daily_returns = AsyncMock(return_value={
            datetime.utcnow(): 1.0
        })
        
        result = await performance_service.get_bot_performance_comparison(user_id=1)
        
        assert isinstance(result, list)
        assert len(result) == 2  # Only bots with trades
        assert all(isinstance(item, BotPerformance) for item in result)
        
        # Should be sorted by total_pnl descending
        if len(result) > 1:
            assert result[0].total_pnl >= result[1].total_pnl
    
    @pytest.mark.asyncio
    async def test_get_bot_performance_comparison_no_bots(self, performance_service):
        """Test bot performance with no bots."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        performance_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await performance_service.get_bot_performance_comparison(user_id=1)
        
        assert isinstance(result, list)
        assert len(result) == 0


class TestStrategyPerformance:
    """Test strategy performance comparison."""
    
    @pytest.mark.asyncio
    async def test_get_strategy_performance_comparison_success(self, performance_service):
        """Test successful strategy performance comparison."""
        # Mock aggregated database results
        mock_row_1 = Mock()
        mock_row_1.strategy_id = 1
        mock_row_1.trades_count = 100
        mock_row_1.total_pnl = Decimal('1000')
        mock_row_1.avg_profit = Decimal('10')
        mock_row_1.bots_count = 3
        
        mock_row_2 = Mock()
        mock_row_2.strategy_id = 2
        mock_row_2.trades_count = 50
        mock_row_2.total_pnl = Decimal('500')
        mock_row_2.avg_profit = Decimal('10')
        mock_row_2.bots_count = 1
        
        mock_result = Mock()
        mock_result.all.return_value = [mock_row_1, mock_row_2]
        performance_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await performance_service.get_strategy_performance_comparison(user_id=1)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, StrategyPerformance) for item in result)
        
        # Should be sorted by total_pnl descending
        assert result[0].total_pnl >= result[1].total_pnl
        assert result[0].strategy_id == 1
    
    @pytest.mark.asyncio
    async def test_get_strategy_performance_comparison_no_data(self, performance_service):
        """Test strategy performance with no data."""
        mock_result = Mock()
        mock_result.all.return_value = []
        performance_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await performance_service.get_strategy_performance_comparison(user_id=1)
        
        assert isinstance(result, list)
        assert len(result) == 0


class TestRiskMetrics:
    """Test risk metrics calculations."""
    
    @pytest.mark.asyncio
    async def test_get_risk_metrics_success(self, performance_service, sample_trades):
        """Test successful risk metrics calculation."""
        performance_service._get_user_trades = AsyncMock(return_value=sample_trades)
        performance_service._calculate_daily_returns = AsyncMock(return_value={
            datetime.utcnow() - timedelta(days=i): 1.0 if i % 2 == 0 else -1.0
            for i in range(10)
        })
        
        result = await performance_service.get_risk_metrics(user_id=1, days=30)
        
        assert isinstance(result, RiskMetrics)
        assert result.var_95 <= 0  # VaR should be negative
        assert result.cvar_95 <= result.var_95  # CVaR should be worse than VaR
        assert result.volatility >= 0  # Volatility should be positive
        assert result.beta == 1.0  # Placeholder value
    
    @pytest.mark.asyncio
    async def test_get_risk_metrics_no_trades(self, performance_service):
        """Test risk metrics with no trades."""
        performance_service._get_user_trades = AsyncMock(return_value=[])
        
        result = await performance_service.get_risk_metrics(user_id=1, days=30)
        
        assert isinstance(result, RiskMetrics)
        assert result.var_95 == 0.0
        assert result.cvar_95 == 0.0
        assert result.volatility == 0.0


class TestCalculationMethods:
    """Test private calculation methods."""
    
    def test_calculate_sharpe_ratio(self, performance_service):
        """Test Sharpe ratio calculation."""
        daily_returns = {
            datetime(2024, 1, 1): 1.0,
            datetime(2024, 1, 2): 2.0,
            datetime(2024, 1, 3): -0.5,
            datetime(2024, 1, 4): 1.5,
        }
        
        sharpe = performance_service._calculate_sharpe_ratio(daily_returns)
        
        assert isinstance(sharpe, float)
        # With positive average return and volatility, Sharpe should be calculated
    
    def test_calculate_sharpe_ratio_no_returns(self, performance_service):
        """Test Sharpe ratio with no returns."""
        sharpe = performance_service._calculate_sharpe_ratio({})
        assert sharpe == 0.0
    
    def test_calculate_sortino_ratio(self, performance_service):
        """Test Sortino ratio calculation."""
        daily_returns = {
            datetime(2024, 1, 1): 1.0,
            datetime(2024, 1, 2): 2.0,
            datetime(2024, 1, 3): -0.5,
            datetime(2024, 1, 4): -1.0,
        }
        
        sortino = performance_service._calculate_sortino_ratio(daily_returns)
        
        assert isinstance(sortino, float)
        # With negative returns present, should calculate downside deviation
    
    def test_calculate_max_drawdown(self, performance_service):
        """Test maximum drawdown calculation."""
        daily_returns = {
            datetime(2024, 1, 1): 1.0,   # +1.0 cumulative
            datetime(2024, 1, 2): 2.0,   # +3.0 cumulative (peak)
            datetime(2024, 1, 3): -1.0,  # +2.0 cumulative
            datetime(2024, 1, 4): -1.5,  # +0.5 cumulative (trough)
        }
        
        max_dd = performance_service._calculate_max_drawdown(daily_returns)
        
        assert isinstance(max_dd, float)
        assert max_dd >= 0  # Drawdown should be positive percentage
    
    def test_calculate_win_rate(self, performance_service, sample_trades):
        """Test win rate calculation."""
        win_rate = performance_service._calculate_win_rate(sample_trades)
        
        assert isinstance(win_rate, float)
        assert 0 <= win_rate <= 100
        assert win_rate == 50.0  # 50% of sample trades are profitable
    
    def test_calculate_profit_factor(self, performance_service, sample_trades):
        """Test profit factor calculation."""
        profit_factor = performance_service._calculate_profit_factor(sample_trades)
        
        assert isinstance(profit_factor, float)
        assert profit_factor == 2.0  # 1000 profit / 500 loss from sample trades
    
    def test_calculate_profit_factor_no_losses(self, performance_service):
        """Test profit factor with only profitable trades."""
        profitable_trades = []
        for i in range(5):
            trade = Mock(spec=TradeModel)
            trade.pnl = Decimal('100')
            profitable_trades.append(trade)
        
        profit_factor = performance_service._calculate_profit_factor(profitable_trades)
        
        assert profit_factor == float('inf')
    
    def test_calculate_profit_factor_no_profits(self, performance_service):
        """Test profit factor with only losing trades."""
        losing_trades = []
        for i in range(5):
            trade = Mock(spec=TradeModel)
            trade.pnl = Decimal('-100')
            losing_trades.append(trade)
        
        profit_factor = performance_service._calculate_profit_factor(losing_trades)
        
        assert profit_factor == 0.0


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_performance_overview_with_none_pnl(self, performance_service):
        """Test handling of trades with None P&L values."""
        trades_with_none = []
        for i in range(5):
            trade = Mock(spec=TradeModel)
            trade.pnl = None if i % 2 == 0 else Decimal('100')
            trade.created_at = datetime.utcnow() - timedelta(days=i)
            trades_with_none.append(trade)
        
        performance_service._get_user_trades = AsyncMock(return_value=trades_with_none)
        
        # Should handle None values gracefully
        result = await performance_service.get_performance_overview(user_id=1)
        assert isinstance(result, PerformanceOverview)
    
    def test_division_by_zero_handling(self, performance_service):
        """Test handling of division by zero in calculations."""
        # Test with zero standard deviation
        daily_returns = {
            datetime(2024, 1, 1): 1.0,
            datetime(2024, 1, 2): 1.0,
            datetime(2024, 1, 3): 1.0,
        }
        
        sharpe = performance_service._calculate_sharpe_ratio(daily_returns)
        assert sharpe == 0.0  # Should handle zero std dev
        
        # Test max drawdown with zero running max
        daily_returns_zero = {datetime(2024, 1, 1): 0.0}
        max_dd = performance_service._calculate_max_drawdown(daily_returns_zero)
        assert max_dd == 0.0