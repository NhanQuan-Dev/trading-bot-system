"""
Unit tests for Phase 3 Backtest Detail APIs.
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

from trading.infrastructure.backtesting.repository import BacktestRepository
from trading.infrastructure.persistence.models.backtest_models import (
    BacktestTradeModel, 
    BacktestResultModel
)


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    return AsyncMock()


@pytest.fixture
def backtest_repository(mock_db_session):
    """Create backtest repository with mock database."""
    return BacktestRepository(mock_db_session)


@pytest.fixture
def sample_backtest_id():
    """Sample backtest ID for testing."""
    return uuid4()


@pytest.fixture
def sample_result_id():
    """Sample result ID for testing."""
    return uuid4()


@pytest.fixture
def sample_trades(sample_result_id):
    """Create sample backtest trades."""
    trades = []
    base_time = datetime.utcnow() - timedelta(days=10)
    
    for i in range(10):
        trade = Mock(spec=BacktestTradeModel)
        trade.id = uuid4()
        trade.result_id = sample_result_id
        trade.symbol = "BTC/USDT" if i % 2 == 0 else "ETH/USDT"
        trade.direction = "LONG" if i % 3 == 0 else "SHORT"
        trade.entry_price = Decimal('50000') + Decimal(str(i * 100))
        trade.exit_price = Decimal('50500') + Decimal(str(i * 100))
        trade.quantity = Decimal('1.0')
        trade.entry_time = base_time + timedelta(hours=i)
        trade.exit_time = base_time + timedelta(hours=i + 1)
        trade.duration_seconds = 3600
        trade.net_pnl = Decimal('500') if i % 2 == 0 else Decimal('-200')
        trade.pnl_percent = Decimal('1.0') if i % 2 == 0 else Decimal('-0.4')
        trades.append(trade)
    
    return trades


class TestGetBacktestTrades:
    """Test backtest trades retrieval."""
    
    @pytest.mark.asyncio
    async def test_get_backtest_trades_success(self, backtest_repository, sample_backtest_id, sample_result_id, sample_trades):
        """Test successful retrieval of backtest trades."""
        
        # Mock result ID lookup
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = sample_result_id
        backtest_repository.session.execute.side_effect = [result_mock, Mock()]
        
        # Mock trades query
        trades_mock = Mock()
        trades_mock.scalars.return_value.all.return_value = sample_trades[:5]  # Limit 5
        backtest_repository.session.execute.side_effect = [result_mock, trades_mock]
        
        result = await backtest_repository.get_backtest_trades(
            backtest_id=sample_backtest_id,
            page=1,
            limit=5
        )
        
        assert len(result) == 5
        assert all(isinstance(trade, Mock) for trade in result)
        assert result[0].symbol == "BTC/USDT"
    
    @pytest.mark.asyncio
    async def test_get_backtest_trades_with_filters(self, backtest_repository, sample_backtest_id, sample_result_id, sample_trades):
        """Test backtest trades retrieval with filters."""
        
        # Mock result ID lookup
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = sample_result_id
        
        # Mock filtered trades
        btc_trades = [t for t in sample_trades if t.symbol == "BTC/USDT"]
        trades_mock = Mock()
        trades_mock.scalars.return_value.all.return_value = btc_trades
        
        backtest_repository.session.execute.side_effect = [result_mock, trades_mock]
        
        result = await backtest_repository.get_backtest_trades(
            backtest_id=sample_backtest_id,
            symbol="BTC/USDT",
            side="buy",
            min_pnl=0
        )
        
        assert all(trade.symbol == "BTC/USDT" for trade in result)
    
    @pytest.mark.asyncio
    async def test_get_backtest_trades_no_result(self, backtest_repository, sample_backtest_id):
        """Test backtest trades when backtest has no results."""
        
        # Mock no result found
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        backtest_repository.session.execute.return_value = result_mock
        
        result = await backtest_repository.get_backtest_trades(sample_backtest_id)
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_get_backtest_trades_pagination(self, backtest_repository, sample_backtest_id, sample_result_id, sample_trades):
        """Test backtest trades pagination."""
        
        # Mock result ID lookup
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = sample_result_id
        
        # Mock page 2 results
        page_2_trades = sample_trades[3:6]  # Skip first 3, take next 3
        trades_mock = Mock()
        trades_mock.scalars.return_value.all.return_value = page_2_trades
        
        backtest_repository.session.execute.side_effect = [result_mock, trades_mock]
        
        result = await backtest_repository.get_backtest_trades(
            backtest_id=sample_backtest_id,
            page=2,
            limit=3
        )
        
        assert len(result) == 3


class TestCountBacktestTrades:
    """Test backtest trades counting."""
    
    @pytest.mark.asyncio
    async def test_count_backtest_trades_success(self, backtest_repository, sample_backtest_id, sample_result_id):
        """Test successful counting of backtest trades."""
        
        # Mock result ID lookup
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = sample_result_id
        
        # Mock count query
        count_mock = Mock()
        count_mock.scalar_one.return_value = 25
        
        backtest_repository.session.execute.side_effect = [result_mock, count_mock]
        
        count = await backtest_repository.count_backtest_trades(sample_backtest_id)
        
        assert count == 25
    
    @pytest.mark.asyncio
    async def test_count_backtest_trades_with_filters(self, backtest_repository, sample_backtest_id, sample_result_id):
        """Test counting backtest trades with filters."""
        
        # Mock result ID lookup and count
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = sample_result_id
        
        count_mock = Mock()
        count_mock.scalar_one.return_value = 10  # Fewer with filters
        
        backtest_repository.session.execute.side_effect = [result_mock, count_mock]
        
        count = await backtest_repository.count_backtest_trades(
            backtest_id=sample_backtest_id,
            symbol="BTC/USDT"
        )
        
        assert count == 10
    
    @pytest.mark.asyncio
    async def test_count_backtest_trades_no_result(self, backtest_repository, sample_backtest_id):
        """Test counting trades when backtest has no results."""
        
        # Mock no result found
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        backtest_repository.session.execute.return_value = result_mock
        
        count = await backtest_repository.count_backtest_trades(sample_backtest_id)
        
        assert count == 0


class TestGetEquityCurve:
    """Test equity curve retrieval."""
    
    @pytest.mark.asyncio
    async def test_get_equity_curve_success(self, backtest_repository, sample_backtest_id):
        """Test successful equity curve retrieval."""
        
        # Mock backtest result with equity curve data
        equity_data = [
            {"timestamp": "2024-01-01T00:00:00", "equity": 10000, "drawdown": 0},
            {"timestamp": "2024-01-02T00:00:00", "equity": 10500, "drawdown": 0},
            {"timestamp": "2024-01-03T00:00:00", "equity": 9800, "drawdown": 6.67},
        ]
        
        backtest_result = Mock(spec=BacktestResultModel)
        backtest_result.equity_curve = equity_data
        
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = backtest_result
        backtest_repository.session.execute.return_value = result_mock
        
        equity_curve = await backtest_repository.get_equity_curve(sample_backtest_id)
        
        assert len(equity_curve) == 3
        assert equity_curve[0].equity == 10000
        assert equity_curve[1].equity == 10500
        assert equity_curve[2].drawdown_pct == 6.67
    
    @pytest.mark.asyncio
    async def test_get_equity_curve_json_string(self, backtest_repository, sample_backtest_id):
        """Test equity curve retrieval when data is JSON string."""
        
        import json
        
        equity_data = [
            {"timestamp": "2024-01-01T00:00:00", "equity": 10000, "drawdown": 0},
        ]
        
        backtest_result = Mock(spec=BacktestResultModel)
        backtest_result.equity_curve = json.dumps(equity_data)  # JSON string
        
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = backtest_result
        backtest_repository.session.execute.return_value = result_mock
        
        equity_curve = await backtest_repository.get_equity_curve(sample_backtest_id)
        
        assert len(equity_curve) == 1
        assert equity_curve[0].equity == 10000
    
    @pytest.mark.asyncio
    async def test_get_equity_curve_no_data(self, backtest_repository, sample_backtest_id):
        """Test equity curve when no data available."""
        
        # Mock no result or no equity curve
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = None
        backtest_repository.session.execute.return_value = result_mock
        
        equity_curve = await backtest_repository.get_equity_curve(sample_backtest_id)
        
        assert equity_curve == []


class TestGetPositionTimeline:
    """Test position timeline retrieval."""
    
    @pytest.mark.asyncio
    async def test_get_position_timeline_success(self, backtest_repository, sample_backtest_id, sample_trades):
        """Test successful position timeline calculation."""
        
        # Mock get_backtest_trades call
        backtest_repository.get_backtest_trades = AsyncMock(return_value=sample_trades[:5])
        
        timeline = await backtest_repository.get_position_timeline(sample_backtest_id)
        
        assert len(timeline) > 0
        assert all(hasattr(point, 'timestamp') for point in timeline)
        assert all(hasattr(point, 'open_positions_count') for point in timeline)
        assert all(hasattr(point, 'total_exposure') for point in timeline)
    
    @pytest.mark.asyncio
    async def test_get_position_timeline_no_trades(self, backtest_repository, sample_backtest_id):
        """Test position timeline with no trades."""
        
        # Mock no trades
        backtest_repository.get_backtest_trades = AsyncMock(return_value=[])
        
        timeline = await backtest_repository.get_position_timeline(sample_backtest_id)
        
        assert timeline == []
    
    @pytest.mark.asyncio
    async def test_position_timeline_calculations(self, backtest_repository, sample_backtest_id):
        """Test position timeline calculations are correct."""
        
        # Create specific trades for calculation testing
        base_time = datetime.utcnow()
        
        trade1 = Mock(spec=BacktestTradeModel)
        trade1.direction = "LONG"
        trade1.quantity = Decimal('1.0')
        trade1.entry_price = Decimal('50000')
        trade1.entry_time = base_time
        trade1.exit_time = base_time + timedelta(hours=2)
        
        trade2 = Mock(spec=BacktestTradeModel)
        trade2.direction = "SHORT"
        trade2.quantity = Decimal('0.5')
        trade2.entry_price = Decimal('51000')
        trade2.entry_time = base_time + timedelta(hours=1)
        trade2.exit_time = base_time + timedelta(hours=3)
        
        backtest_repository.get_backtest_trades = AsyncMock(return_value=[trade1, trade2])
        
        timeline = await backtest_repository.get_position_timeline(sample_backtest_id)
        
        # Should have entry and exit points
        assert len(timeline) >= 2
        
        # First entry should increase position count
        first_entry = timeline[0]
        assert first_entry.open_positions_count >= 1
        assert first_entry.total_exposure > 0


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_get_backtest_trades_side_mapping(self, backtest_repository, sample_backtest_id, sample_result_id):
        """Test that side parameter is correctly mapped to direction."""
        
        # Mock result ID lookup
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = sample_result_id
        
        trades_mock = Mock()
        trades_mock.scalars.return_value.all.return_value = []
        
        backtest_repository.session.execute.side_effect = [result_mock, trades_mock]
        
        # Test buy -> LONG mapping
        await backtest_repository.get_backtest_trades(
            backtest_id=sample_backtest_id,
            side="buy"
        )
        
        # Test sell -> SHORT mapping
        await backtest_repository.get_backtest_trades(
            backtest_id=sample_backtest_id,
            side="sell"
        )
        
        # Should not raise any errors
    
    @pytest.mark.asyncio
    async def test_equity_curve_empty_data(self, backtest_repository, sample_backtest_id):
        """Test equity curve with empty equity data."""
        
        backtest_result = Mock(spec=BacktestResultModel)
        backtest_result.equity_curve = []
        
        result_mock = Mock()
        result_mock.scalar_one_or_none.return_value = backtest_result
        backtest_repository.session.execute.return_value = result_mock
        
        equity_curve = await backtest_repository.get_equity_curve(sample_backtest_id)
        
        assert equity_curve == []
    
    @pytest.mark.asyncio
    async def test_position_timeline_single_trade(self, backtest_repository, sample_backtest_id):
        """Test position timeline with single trade."""
        
        base_time = datetime.utcnow()
        
        single_trade = Mock(spec=BacktestTradeModel)
        single_trade.direction = "LONG"
        single_trade.quantity = Decimal('1.0')
        single_trade.entry_price = Decimal('50000')
        single_trade.entry_time = base_time
        single_trade.exit_time = base_time + timedelta(hours=1)
        
        backtest_repository.get_backtest_trades = AsyncMock(return_value=[single_trade])
        
        timeline = await backtest_repository.get_position_timeline(sample_backtest_id)
        
        assert len(timeline) == 2  # Entry and exit points
        assert timeline[0].open_positions_count == 1
        assert timeline[1].open_positions_count == 0