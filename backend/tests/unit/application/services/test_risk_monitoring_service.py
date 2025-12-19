"""
Unit tests for Risk Monitoring Service.
"""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from typing import List

from application.services.risk_monitoring_service import (
    RiskMonitoringService,
    RiskOverview,
    ExposureBreakdown,
    RiskLimit,
    RiskAlert,
    RiskStatus,
    AlertSeverity,
    AlertType
)
from trading.infrastructure.persistence.models.core_models import (
    PositionModel, BotModel, RiskLimitModel, RiskAlertModel
)
from trading.domain.bot.enums import BotStatus


@pytest.fixture
def mock_db_session():
    """Create mock database session."""
    return AsyncMock()


@pytest.fixture
def risk_service(mock_db_session):
    """Create risk monitoring service with mock database."""
    return RiskMonitoringService(mock_db_session)


@pytest.fixture
def sample_positions():
    """Create sample positions for testing."""
    positions = []
    
    # BTC position
    btc_position = Mock(spec=PositionModel)
    btc_position.id = 1
    btc_position.symbol = "BTC/USDT"
    btc_position.size = Decimal('1.5')
    btc_position.entry_price = Decimal('50000')
    btc_position.current_price = Decimal('52000')
    btc_position.bot_id = 1
    positions.append(btc_position)
    
    # ETH position
    eth_position = Mock(spec=PositionModel)
    eth_position.id = 2
    eth_position.symbol = "ETH/USDT"
    eth_position.size = Decimal('10')
    eth_position.entry_price = Decimal('3000')
    eth_position.current_price = Decimal('3100')
    eth_position.bot_id = 2
    positions.append(eth_position)
    
    return positions


@pytest.fixture
def sample_bots():
    """Create sample bots for testing."""
    bots = []
    
    for i in range(3):
        bot = Mock(spec=BotModel)
        bot.id = i + 1
        bot.name = f"Bot {i + 1}"
        bot.status = BotStatus.RUNNING
        bot.user_id = 1
        bot.positions = []
        bots.append(bot)
    
    return bots


@pytest.fixture
def sample_risk_limits():
    """Create sample risk limits for testing."""
    limits = []
    
    # Position size limit
    position_limit = Mock(spec=RiskLimitModel)
    position_limit.id = 1
    position_limit.user_id = 1
    position_limit.limit_type = "position_size"
    position_limit.max_value = Decimal('100000')
    position_limit.updated_at = datetime.utcnow()
    limits.append(position_limit)
    
    # Daily loss limit
    daily_loss_limit = Mock(spec=RiskLimitModel)
    daily_loss_limit.id = 2
    daily_loss_limit.user_id = 1
    daily_loss_limit.limit_type = "daily_loss"
    daily_loss_limit.max_value = Decimal('1000')
    daily_loss_limit.updated_at = datetime.utcnow()
    limits.append(daily_loss_limit)
    
    return limits


@pytest.fixture
def sample_risk_alerts():
    """Create sample risk alerts for testing."""
    alerts = []
    
    # Active alert
    active_alert = Mock(spec=RiskAlertModel)
    active_alert.id = 1
    active_alert.user_id = 1
    active_alert.alert_type = AlertType.EXPOSURE.value
    active_alert.severity = AlertSeverity.HIGH.value
    active_alert.message = "High exposure detected"
    active_alert.triggered_at = datetime.utcnow() - timedelta(hours=1)
    active_alert.resolved_at = None
    alerts.append(active_alert)
    
    # Resolved alert
    resolved_alert = Mock(spec=RiskAlertModel)
    resolved_alert.id = 2
    resolved_alert.user_id = 1
    resolved_alert.alert_type = AlertType.POSITION_SIZE.value
    resolved_alert.severity = AlertSeverity.MEDIUM.value
    resolved_alert.message = "Position size limit exceeded"
    resolved_alert.triggered_at = datetime.utcnow() - timedelta(days=1)
    resolved_alert.resolved_at = datetime.utcnow() - timedelta(hours=12)
    alerts.append(resolved_alert)
    
    return alerts


class TestRiskOverview:
    """Test risk overview calculations."""
    
    @pytest.mark.asyncio
    async def test_get_risk_overview_success(self, risk_service, sample_positions):
        """Test successful risk overview calculation."""
        # Mock private methods
        risk_service._get_user_positions = AsyncMock(return_value=sample_positions)
        risk_service._calculate_leverage_used = AsyncMock(return_value=2.5)
        risk_service._calculate_margin_level = AsyncMock(return_value=150.0)
        risk_service._calculate_risk_score = AsyncMock(return_value=45)
        risk_service._count_active_alerts = AsyncMock(return_value=2)
        
        result = await risk_service.get_risk_overview(user_id=1)
        
        assert isinstance(result, RiskOverview)
        assert result.current_exposure == 109000.0  # (1.5 * 52000) + (10 * 3100)
        assert result.leverage_used == 2.5
        assert result.margin_level == 150.0
        assert result.risk_score == 45
        assert result.active_alerts == 2
    
    @pytest.mark.asyncio
    async def test_get_risk_overview_no_positions(self, risk_service):
        """Test risk overview with no positions."""
        risk_service._get_user_positions = AsyncMock(return_value=[])
        risk_service._calculate_leverage_used = AsyncMock(return_value=0.0)
        risk_service._calculate_margin_level = AsyncMock(return_value=100.0)
        risk_service._calculate_risk_score = AsyncMock(return_value=10)
        risk_service._count_active_alerts = AsyncMock(return_value=0)
        
        result = await risk_service.get_risk_overview(user_id=1)
        
        assert isinstance(result, RiskOverview)
        assert result.current_exposure == 0.0
        assert result.risk_score == 10


class TestExposureBreakdown:
    """Test exposure breakdown calculations."""
    
    @pytest.mark.asyncio
    async def test_get_exposure_breakdown_success(self, risk_service, sample_positions):
        """Test successful exposure breakdown calculation."""
        risk_service._get_user_positions = AsyncMock(return_value=sample_positions)
        risk_service._get_portfolio_value = AsyncMock(return_value=200000.0)
        risk_service._get_asset_exposure_limit = AsyncMock(return_value=25.0)
        
        result = await risk_service.get_exposure_breakdown(user_id=1)
        
        assert isinstance(result, list)
        assert len(result) == 2  # BTC and ETH
        assert all(isinstance(item, ExposureBreakdown) for item in result)
        
        # Check BTC exposure (should be larger)
        btc_exposure = next(item for item in result if item.asset == "BTC")
        assert btc_exposure.exposure_value == 78000.0  # 1.5 * 52000
        assert btc_exposure.exposure_pct == 39.0  # 78000 / 200000 * 100
        assert btc_exposure.status == RiskStatus.DANGER  # Over 25% limit
        
        # Check ETH exposure
        eth_exposure = next(item for item in result if item.asset == "ETH")
        assert eth_exposure.exposure_value == 31000.0  # 10 * 3100
        assert eth_exposure.exposure_pct == 15.5  # 31000 / 200000 * 100
        assert eth_exposure.status == RiskStatus.SAFE  # Under 25% limit
    
    @pytest.mark.asyncio
    async def test_get_exposure_breakdown_no_positions(self, risk_service):
        """Test exposure breakdown with no positions."""
        risk_service._get_user_positions = AsyncMock(return_value=[])
        
        result = await risk_service.get_exposure_breakdown(user_id=1)
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_get_exposure_breakdown_zero_portfolio_value(self, risk_service, sample_positions):
        """Test exposure breakdown with zero portfolio value."""
        risk_service._get_user_positions = AsyncMock(return_value=sample_positions)
        risk_service._get_portfolio_value = AsyncMock(return_value=0.0)
        risk_service._get_asset_exposure_limit = AsyncMock(return_value=25.0)
        
        result = await risk_service.get_exposure_breakdown(user_id=1)
        
        assert isinstance(result, list)
        assert len(result) == 2
        
        # Should handle zero portfolio value gracefully
        for item in result:
            assert item.exposure_pct == 0.0


class TestRiskLimits:
    """Test risk limits management."""
    
    @pytest.mark.asyncio
    async def test_get_risk_limits_success(self, risk_service, sample_risk_limits):
        """Test successful risk limits retrieval."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = sample_risk_limits
        risk_service.db.execute = AsyncMock(return_value=mock_result)
        
        # Mock current values calculation
        risk_service._calculate_current_limit_value = AsyncMock(return_value=50000.0)
        
        result = await risk_service.get_risk_limits(user_id=1)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, RiskLimit) for item in result)
        
        # Check position size limit
        position_limit = next(item for item in result if item.type == "position_size")
        assert position_limit.value == 100000.0
        assert position_limit.current == 50000.0
        assert position_limit.status == RiskStatus.SAFE
    
    @pytest.mark.asyncio
    async def test_get_risk_limits_no_limits(self, risk_service):
        """Test risk limits with no configured limits."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        risk_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await risk_service.get_risk_limits(user_id=1)
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    @pytest.mark.asyncio
    async def test_update_risk_limits_new_limits(self, risk_service):
        """Test updating risk limits with new values."""
        # Mock no existing limits
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = None
        risk_service.db.execute = AsyncMock(return_value=mock_result)
        risk_service.db.commit = AsyncMock()
        
        # Mock the get_risk_limits call at the end
        risk_service.get_risk_limits = AsyncMock(return_value=[])
        
        result = await risk_service.update_risk_limits(
            user_id=1,
            position_size_limit=50000.0,
            daily_loss_limit=1000.0
        )
        
        assert isinstance(result, list)
        # Should have added new limits to database
        risk_service.db.add.assert_called()
        risk_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_risk_limits_existing_limits(self, risk_service, sample_risk_limits):
        """Test updating existing risk limits."""
        # Mock existing limit
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = sample_risk_limits[0]
        risk_service.db.execute = AsyncMock(return_value=mock_result)
        risk_service.db.commit = AsyncMock()
        
        # Mock the get_risk_limits call at the end
        risk_service.get_risk_limits = AsyncMock(return_value=sample_risk_limits)
        
        result = await risk_service.update_risk_limits(
            user_id=1,
            position_size_limit=75000.0
        )
        
        assert isinstance(result, list)
        risk_service.db.commit.assert_called_once()


class TestRiskAlerts:
    """Test risk alerts management."""
    
    @pytest.mark.asyncio
    async def test_get_risk_alerts_success(self, risk_service, sample_risk_alerts):
        """Test successful risk alerts retrieval."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = sample_risk_alerts
        risk_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await risk_service.get_risk_alerts(user_id=1, limit=50, offset=0)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(item, RiskAlert) for item in result)
        
        # Check active alert
        active_alert = next(item for item in result if item.id == 1)
        assert active_alert.is_active is True
        assert active_alert.resolved_at is None
        assert active_alert.type == AlertType.EXPOSURE
        
        # Check resolved alert
        resolved_alert = next(item for item in result if item.id == 2)
        assert resolved_alert.is_active is False
        assert resolved_alert.resolved_at is not None
    
    @pytest.mark.asyncio
    async def test_get_risk_alerts_with_pagination(self, risk_service, sample_risk_alerts):
        """Test risk alerts with pagination parameters."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = sample_risk_alerts[1:]  # Skip first
        risk_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await risk_service.get_risk_alerts(user_id=1, limit=1, offset=1)
        
        assert isinstance(result, list)
        assert len(result) == 1
    
    @pytest.mark.asyncio
    async def test_get_risk_alerts_no_alerts(self, risk_service):
        """Test risk alerts with no alerts."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        risk_service.db.execute = AsyncMock(return_value=mock_result)
        
        result = await risk_service.get_risk_alerts(user_id=1)
        
        assert isinstance(result, list)
        assert len(result) == 0


class TestEmergencyStop:
    """Test emergency stop functionality."""
    
    @pytest.mark.asyncio
    async def test_emergency_stop_all_bots_success(self, risk_service, sample_bots, sample_positions):
        """Test successful emergency stop of all bots."""
        # Add positions to bots
        sample_bots[0].positions = sample_positions[:1]
        sample_bots[1].positions = sample_positions[1:]
        sample_bots[2].positions = []
        
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = sample_bots
        risk_service.db.execute = AsyncMock(return_value=mock_result)
        risk_service.db.commit = AsyncMock()
        
        result = await risk_service.emergency_stop_all_bots(
            user_id=1,
            reason="Market crash detected"
        )
        
        assert isinstance(result, dict)
        assert result["stopped_bots"] == 3
        assert result["closed_positions"] == 2
        assert result["reason"] == "Market crash detected"
        assert "timestamp" in result
        
        # Should have updated bot statuses and closed positions
        risk_service.db.execute.assert_called()
        risk_service.db.add.assert_called_once()  # Emergency alert
        risk_service.db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_emergency_stop_no_active_bots(self, risk_service):
        """Test emergency stop with no active bots."""
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        risk_service.db.execute = AsyncMock(return_value=mock_result)
        risk_service.db.commit = AsyncMock()
        
        result = await risk_service.emergency_stop_all_bots(
            user_id=1,
            reason="Test emergency stop"
        )
        
        assert isinstance(result, dict)
        assert result["stopped_bots"] == 0
        assert result["closed_positions"] == 0


class TestCalculationMethods:
    """Test private calculation methods."""
    
    def test_calculate_total_exposure(self, risk_service, sample_positions):
        """Test total exposure calculation."""
        total_exposure = risk_service._calculate_total_exposure(sample_positions)
        
        # BTC: 1.5 * 52000 = 78000
        # ETH: 10 * 3100 = 31000
        # Total: 109000
        assert total_exposure == 109000.0
    
    def test_calculate_total_exposure_empty_positions(self, risk_service):
        """Test total exposure with no positions."""
        total_exposure = risk_service._calculate_total_exposure([])
        assert total_exposure == 0.0
    
    def test_determine_exposure_status(self, risk_service):
        """Test exposure status determination."""
        # Safe status
        status = risk_service._determine_exposure_status(10.0, 25.0)
        assert status == RiskStatus.SAFE
        
        # Warning status
        status = risk_service._determine_exposure_status(22.0, 25.0)
        assert status == RiskStatus.WARNING
        
        # Danger status
        status = risk_service._determine_exposure_status(30.0, 25.0)
        assert status == RiskStatus.DANGER
    
    @pytest.mark.asyncio
    async def test_calculate_current_limit_value_position_size(self, risk_service, sample_positions):
        """Test current limit value calculation for position size."""
        risk_service._get_user_positions = AsyncMock(return_value=sample_positions)
        
        current_value = await risk_service._calculate_current_limit_value(1, "position_size")
        
        # Should return the largest position value
        # BTC: 1.5 * 52000 = 78000 (larger)
        # ETH: 10 * 3100 = 31000
        assert current_value == 78000.0
    
    @pytest.mark.asyncio
    async def test_calculate_current_limit_value_exposure(self, risk_service, sample_positions):
        """Test current limit value calculation for exposure."""
        risk_service._get_user_positions = AsyncMock(return_value=sample_positions)
        
        current_value = await risk_service._calculate_current_limit_value(1, "exposure")
        
        # Should return total exposure
        assert current_value == 109000.0
    
    @pytest.mark.asyncio
    async def test_calculate_current_limit_value_unknown_type(self, risk_service):
        """Test current limit value calculation for unknown type."""
        current_value = await risk_service._calculate_current_limit_value(1, "unknown_type")
        assert current_value == 0.0


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_calculate_total_exposure_with_none_values(self, risk_service):
        """Test total exposure calculation with None values."""
        position = Mock(spec=PositionModel)
        position.size = None
        position.current_price = None
        position.entry_price = Decimal('1000')
        
        # Should handle None values gracefully
        total_exposure = risk_service._calculate_total_exposure([position])
        assert total_exposure == 0.0
    
    @pytest.mark.asyncio
    async def test_calculate_leverage_with_zero_portfolio_value(self, risk_service, sample_positions):
        """Test leverage calculation with zero portfolio value."""
        risk_service._get_user_positions = AsyncMock(return_value=sample_positions)
        risk_service._get_portfolio_value = AsyncMock(return_value=0.0)
        
        leverage = await risk_service._calculate_leverage_used(user_id=1)
        assert leverage == 0.0
    
    @pytest.mark.asyncio
    async def test_count_active_alerts_database_error(self, risk_service):
        """Test active alerts count when database returns None."""
        mock_result = Mock()
        mock_result.scalar.return_value = None
        risk_service.db.execute = AsyncMock(return_value=mock_result)
        
        count = await risk_service._count_active_alerts(user_id=1)
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_get_asset_exposure_limit_no_custom_limit(self, risk_service):
        """Test asset exposure limit with no custom limit set."""
        mock_result = Mock()
        mock_result.scalars.return_value.first.return_value = None
        risk_service.db.execute = AsyncMock(return_value=mock_result)
        
        limit = await risk_service._get_asset_exposure_limit(user_id=1, asset="BTC")
        assert limit == 25.0  # Default limit