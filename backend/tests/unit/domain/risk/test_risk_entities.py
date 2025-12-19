"""Test cases for Risk domain entities."""
import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
import uuid

from src.trading.domain.risk import (
    RiskLimit,
    RiskAlert,
    RiskLimitType,
    RiskStatus,
    RiskThreshold,
    LimitViolation
)


class TestRiskLimit:
    """Test RiskLimit entity."""

    def test_create_risk_limit_global(self):
        """Test creating a global risk limit (no symbol)."""
        limit_id = uuid.uuid4()
        user_id = uuid.uuid4()
        created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        threshold = RiskThreshold(
            warning_threshold=Decimal("80.0"),
            critical_threshold=Decimal("95.0")
        )
        
        risk_limit = RiskLimit(
            id=limit_id,
            user_id=user_id,
            limit_type=RiskLimitType.DAILY_LOSS,
            limit_value=Decimal("1000.00"),
            symbol=None,
            enabled=True,
            threshold=threshold,
            created_at=created_at,
            updated_at=created_at
        )
        
        assert risk_limit.id == limit_id
        assert risk_limit.user_id == user_id
        assert risk_limit.limit_type == RiskLimitType.DAILY_LOSS
        assert risk_limit.limit_value == Decimal("1000.00")
        assert risk_limit.symbol is None
        assert risk_limit.enabled is True
        assert risk_limit.threshold == threshold
        assert risk_limit.violations == []

    def test_create_risk_limit_with_symbol(self):
        """Test creating a symbol-specific risk limit."""
        limit_id = uuid.uuid4()
        user_id = uuid.uuid4()
        created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        threshold = RiskThreshold(
            warning_threshold=Decimal("80.0"),
            critical_threshold=Decimal("95.0")
        )
        
        risk_limit = RiskLimit(
            id=limit_id,
            user_id=user_id,
            limit_type=RiskLimitType.POSITION_SIZE,
            limit_value=Decimal("10000.00"),
            symbol="BTCUSDT",
            enabled=True,
            threshold=threshold,
            created_at=created_at,
            updated_at=created_at
        )
        
        assert risk_limit.symbol == "BTCUSDT"
        assert risk_limit.limit_type == RiskLimitType.POSITION_SIZE

    def test_invalid_zero_limit_value(self):
        """Test that zero limit value raises ValueError."""
        with pytest.raises(ValueError, match="Limit value must be positive"):
            RiskLimit(
                id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                limit_type=RiskLimitType.DAILY_LOSS,
                limit_value=Decimal("0"),
                symbol=None,
                enabled=True,
                threshold=RiskThreshold(Decimal("80"), Decimal("95")),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

    def test_invalid_negative_limit_value(self):
        """Test that negative limit value raises ValueError."""
        with pytest.raises(ValueError, match="Limit value must be positive"):
            RiskLimit(
                id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                limit_type=RiskLimitType.DAILY_LOSS,
                limit_value=Decimal("-100.00"),
                symbol=None,
                enabled=True,
                threshold=RiskThreshold(Decimal("80"), Decimal("95")),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )

    def test_check_violation_no_violation(self):
        """Test checking violation when current value is below limit."""
        threshold = RiskThreshold(Decimal("80.0"), Decimal("95.0"))
        
        risk_limit = RiskLimit(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            limit_type=RiskLimitType.POSITION_SIZE,
            limit_value=Decimal("10000.00"),
            symbol="BTCUSDT",
            enabled=True,
            threshold=threshold,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Current value below limit
        violation = risk_limit.check_violation(Decimal("5000.00"))
        
        assert violation is None
        assert len(risk_limit.violations) == 0

    def test_check_violation_with_violation(self):
        """Test checking violation when current value exceeds limit."""
        threshold = RiskThreshold(Decimal("80.0"), Decimal("95.0"))
        
        risk_limit = RiskLimit(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            limit_type=RiskLimitType.POSITION_SIZE,
            limit_value=Decimal("10000.00"),
            symbol="BTCUSDT",
            enabled=True,
            threshold=threshold,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Current value exceeds limit
        violation = risk_limit.check_violation(Decimal("15000.00"))
        
        assert violation is not None
        assert violation.limit_type == "POSITION_SIZE"
        assert violation.current_value == Decimal("15000.00")
        assert violation.limit_value == Decimal("10000.00")
        assert violation.violation_percentage == Decimal("150.0")
        assert violation.symbol == "BTCUSDT"
        
        # Violation should be added to history
        assert len(risk_limit.violations) == 1
        assert risk_limit.violations[0] == violation

    def test_check_violation_when_disabled(self):
        """Test that disabled limits don't check violations."""
        threshold = RiskThreshold(Decimal("80.0"), Decimal("95.0"))
        
        risk_limit = RiskLimit(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            limit_type=RiskLimitType.POSITION_SIZE,
            limit_value=Decimal("10000.00"),
            symbol="BTCUSDT",
            enabled=False,  # Disabled
            threshold=threshold,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Even though value exceeds limit, no violation because disabled
        violation = risk_limit.check_violation(Decimal("15000.00"))
        
        assert violation is None
        assert len(risk_limit.violations) == 0

    def test_check_violation_exact_limit(self):
        """Test checking violation when current value equals limit."""
        threshold = RiskThreshold(Decimal("80.0"), Decimal("95.0"))
        
        risk_limit = RiskLimit(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            limit_type=RiskLimitType.POSITION_SIZE,
            limit_value=Decimal("10000.00"),
            symbol="BTCUSDT",
            enabled=True,
            threshold=threshold,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Current value equals limit - no violation (not exceeded)
        violation = risk_limit.check_violation(Decimal("10000.00"))
        
        assert violation is None

    def test_update_limit_valid(self):
        """Test updating limit value with valid value."""
        threshold = RiskThreshold(Decimal("80.0"), Decimal("95.0"))
        initial_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        risk_limit = RiskLimit(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            limit_type=RiskLimitType.POSITION_SIZE,
            limit_value=Decimal("10000.00"),
            symbol="BTCUSDT",
            enabled=True,
            threshold=threshold,
            created_at=initial_time,
            updated_at=initial_time
        )
        
        with patch('src.trading.domain.risk.entities.datetime') as mock_dt:
            mock_now = datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.utcnow.return_value = mock_now
            
            risk_limit.update_limit(Decimal("20000.00"))
        
        assert risk_limit.limit_value == Decimal("20000.00")
        assert risk_limit.updated_at == mock_now

    def test_update_limit_invalid_zero(self):
        """Test updating limit with zero value raises ValueError."""
        threshold = RiskThreshold(Decimal("80.0"), Decimal("95.0"))
        
        risk_limit = RiskLimit(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            limit_type=RiskLimitType.POSITION_SIZE,
            limit_value=Decimal("10000.00"),
            symbol="BTCUSDT",
            enabled=True,
            threshold=threshold,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        with pytest.raises(ValueError, match="Limit value must be positive"):
            risk_limit.update_limit(Decimal("0"))

    def test_enable_limit(self):
        """Test enabling a disabled risk limit."""
        threshold = RiskThreshold(Decimal("80.0"), Decimal("95.0"))
        initial_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        risk_limit = RiskLimit(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            limit_type=RiskLimitType.POSITION_SIZE,
            limit_value=Decimal("10000.00"),
            symbol="BTCUSDT",
            enabled=False,
            threshold=threshold,
            created_at=initial_time,
            updated_at=initial_time
        )
        
        with patch('src.trading.domain.risk.entities.datetime') as mock_dt:
            mock_now = datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.utcnow.return_value = mock_now
            
            risk_limit.enable()
        
        assert risk_limit.enabled is True
        assert risk_limit.updated_at == mock_now

    def test_disable_limit(self):
        """Test disabling an enabled risk limit."""
        threshold = RiskThreshold(Decimal("80.0"), Decimal("95.0"))
        initial_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        risk_limit = RiskLimit(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            limit_type=RiskLimitType.POSITION_SIZE,
            limit_value=Decimal("10000.00"),
            symbol="BTCUSDT",
            enabled=True,
            threshold=threshold,
            created_at=initial_time,
            updated_at=initial_time
        )
        
        with patch('src.trading.domain.risk.entities.datetime') as mock_dt:
            mock_now = datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.utcnow.return_value = mock_now
            
            risk_limit.disable()
        
        assert risk_limit.enabled is False
        assert risk_limit.updated_at == mock_now

    def test_update_threshold(self):
        """Test updating risk thresholds."""
        old_threshold = RiskThreshold(Decimal("80.0"), Decimal("95.0"))
        new_threshold = RiskThreshold(Decimal("70.0"), Decimal("90.0"))
        initial_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        risk_limit = RiskLimit(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            limit_type=RiskLimitType.POSITION_SIZE,
            limit_value=Decimal("10000.00"),
            symbol="BTCUSDT",
            enabled=True,
            threshold=old_threshold,
            created_at=initial_time,
            updated_at=initial_time
        )
        
        with patch('src.trading.domain.risk.entities.datetime') as mock_dt:
            mock_now = datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.utcnow.return_value = mock_now
            
            risk_limit.update_threshold(new_threshold)
        
        assert risk_limit.threshold == new_threshold
        assert risk_limit.threshold.warning_threshold == Decimal("70.0")
        assert risk_limit.threshold.critical_threshold == Decimal("90.0")
        assert risk_limit.updated_at == mock_now


class TestRiskAlert:
    """Test RiskAlert entity."""

    def test_create_risk_alert(self):
        """Test creating a risk alert."""
        alert_id = uuid.uuid4()
        user_id = uuid.uuid4()
        risk_limit_id = uuid.uuid4()
        created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        alert = RiskAlert(
            id=alert_id,
            user_id=user_id,
            risk_limit_id=risk_limit_id,
            alert_type="POSITION_LIMIT_EXCEEDED",
            message="Position size limit exceeded for BTCUSDT",
            severity=RiskStatus.CRITICAL,
            symbol="BTCUSDT",
            current_value=Decimal("15000.00"),
            limit_value=Decimal("10000.00"),
            violation_percentage=Decimal("150.0"),
            acknowledged=False,
            created_at=created_at
        )
        
        assert alert.id == alert_id
        assert alert.user_id == user_id
        assert alert.risk_limit_id == risk_limit_id
        assert alert.alert_type == "POSITION_LIMIT_EXCEEDED"
        assert alert.message == "Position size limit exceeded for BTCUSDT"
        assert alert.severity == RiskStatus.CRITICAL
        assert alert.symbol == "BTCUSDT"
        assert alert.current_value == Decimal("15000.00")
        assert alert.limit_value == Decimal("10000.00")
        assert alert.violation_percentage == Decimal("150.0")
        assert alert.acknowledged is False
        assert alert.acknowledged_at is None

    def test_create_global_risk_alert(self):
        """Test creating a global risk alert (no symbol)."""
        alert = RiskAlert(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            risk_limit_id=uuid.uuid4(),
            alert_type="DAILY_LOSS_LIMIT_EXCEEDED",
            message="Daily loss limit exceeded",
            severity=RiskStatus.BREACHED,
            symbol=None,  # Global limit
            current_value=Decimal("1500.00"),
            limit_value=Decimal("1000.00"),
            violation_percentage=Decimal("150.0"),
            acknowledged=False,
            created_at=datetime.now(timezone.utc)
        )
        
        assert alert.symbol is None
        assert alert.alert_type == "DAILY_LOSS_LIMIT_EXCEEDED"

    def test_acknowledge_alert(self):
        """Test acknowledging a risk alert."""
        alert = RiskAlert(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            risk_limit_id=uuid.uuid4(),
            alert_type="POSITION_LIMIT_EXCEEDED",
            message="Position size limit exceeded",
            severity=RiskStatus.CRITICAL,
            symbol="BTCUSDT",
            current_value=Decimal("15000.00"),
            limit_value=Decimal("10000.00"),
            violation_percentage=Decimal("150.0"),
            acknowledged=False,
            created_at=datetime.now(timezone.utc)
        )
        
        assert alert.acknowledged is False
        assert alert.acknowledged_at is None
        
        with patch('src.trading.domain.risk.entities.datetime') as mock_dt:
            mock_now = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
            mock_dt.utcnow.return_value = mock_now
            
            alert.acknowledge()
        
        assert alert.acknowledged is True
        assert alert.acknowledged_at == mock_now

    def test_is_critical_with_critical_severity(self):
        """Test is_critical property with CRITICAL severity."""
        alert = RiskAlert(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            risk_limit_id=uuid.uuid4(),
            alert_type="POSITION_LIMIT_EXCEEDED",
            message="Position size limit exceeded",
            severity=RiskStatus.CRITICAL,
            symbol="BTCUSDT",
            current_value=Decimal("15000.00"),
            limit_value=Decimal("10000.00"),
            violation_percentage=Decimal("150.0"),
            acknowledged=False,
            created_at=datetime.now(timezone.utc)
        )
        
        assert alert.is_critical is True

    def test_is_critical_with_breached_severity(self):
        """Test is_critical property with BREACHED severity."""
        alert = RiskAlert(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            risk_limit_id=uuid.uuid4(),
            alert_type="POSITION_LIMIT_EXCEEDED",
            message="Position size limit exceeded",
            severity=RiskStatus.BREACHED,
            symbol="BTCUSDT",
            current_value=Decimal("15000.00"),
            limit_value=Decimal("10000.00"),
            violation_percentage=Decimal("150.0"),
            acknowledged=False,
            created_at=datetime.now(timezone.utc)
        )
        
        assert alert.is_critical is True

    def test_is_critical_with_warning_severity(self):
        """Test is_critical property with WARNING severity."""
        alert = RiskAlert(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            risk_limit_id=uuid.uuid4(),
            alert_type="POSITION_LIMIT_APPROACHED",
            message="Position size limit approached",
            severity=RiskStatus.WARNING,
            symbol="BTCUSDT",
            current_value=Decimal("8500.00"),
            limit_value=Decimal("10000.00"),
            violation_percentage=Decimal("85.0"),
            acknowledged=False,
            created_at=datetime.now(timezone.utc)
        )
        
        assert alert.is_critical is False

    def test_is_critical_with_normal_severity(self):
        """Test is_critical property with NORMAL severity."""
        alert = RiskAlert(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            risk_limit_id=uuid.uuid4(),
            alert_type="POSITION_LIMIT_APPROACHED",
            message="Position size within normal limits",
            severity=RiskStatus.NORMAL,
            symbol="BTCUSDT",
            current_value=Decimal("5000.00"),
            limit_value=Decimal("10000.00"),
            violation_percentage=Decimal("50.0"),
            acknowledged=False,
            created_at=datetime.now(timezone.utc)
        )
        
        assert alert.is_critical is False
