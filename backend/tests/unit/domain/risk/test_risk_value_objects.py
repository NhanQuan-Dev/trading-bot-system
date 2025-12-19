"""Test cases for Risk domain value objects."""
import pytest
from decimal import Decimal

from src.trading.domain.risk import (
    RiskMetrics,
    RiskThreshold,
    LimitViolation,
    RiskLevel,
    RiskLimitType,
    RiskStatus,
    AlertType
)


class TestRiskLevel:
    """Test RiskLevel enum."""

    def test_risk_level_values(self):
        """Test all risk level enum values."""
        assert RiskLevel.LOW == "LOW"
        assert RiskLevel.MEDIUM == "MEDIUM"
        assert RiskLevel.HIGH == "HIGH"
        assert RiskLevel.CRITICAL == "CRITICAL"

    def test_risk_level_string_representation(self):
        """Test risk level string conversion."""
        assert RiskLevel.LOW.value == "LOW"
        assert RiskLevel.CRITICAL.value == "CRITICAL"


class TestRiskLimitType:
    """Test RiskLimitType enum."""

    def test_risk_limit_type_values(self):
        """Test all risk limit type enum values."""
        assert RiskLimitType.POSITION_SIZE == "POSITION_SIZE"
        assert RiskLimitType.DAILY_LOSS == "DAILY_LOSS"
        assert RiskLimitType.DRAWDOWN == "DRAWDOWN"
        assert RiskLimitType.LEVERAGE == "LEVERAGE"
        assert RiskLimitType.EXPOSURE == "EXPOSURE"

    def test_risk_limit_type_string_representation(self):
        """Test risk limit type string conversion."""
        assert RiskLimitType.POSITION_SIZE.value == "POSITION_SIZE"
        assert RiskLimitType.DAILY_LOSS.value == "DAILY_LOSS"


class TestRiskStatus:
    """Test RiskStatus enum."""

    def test_risk_status_values(self):
        """Test all risk status enum values."""
        assert RiskStatus.NORMAL == "NORMAL"
        assert RiskStatus.WARNING == "WARNING"
        assert RiskStatus.CRITICAL == "CRITICAL"
        assert RiskStatus.BREACHED == "BREACHED"

    def test_risk_status_string_representation(self):
        """Test risk status string conversion."""
        assert RiskStatus.NORMAL.value == "NORMAL"
        assert RiskStatus.BREACHED.value == "BREACHED"


class TestAlertType:
    """Test AlertType enum."""

    def test_alert_type_values(self):
        """Test all alert type enum values."""
        assert AlertType.POSITION_LIMIT_APPROACHED == "POSITION_LIMIT_APPROACHED"
        assert AlertType.POSITION_LIMIT_EXCEEDED == "POSITION_LIMIT_EXCEEDED"
        assert AlertType.DAILY_LOSS_LIMIT_APPROACHED == "DAILY_LOSS_LIMIT_APPROACHED"
        assert AlertType.DAILY_LOSS_LIMIT_EXCEEDED == "DAILY_LOSS_LIMIT_EXCEEDED"
        assert AlertType.DRAWDOWN_LIMIT_APPROACHED == "DRAWDOWN_LIMIT_APPROACHED"
        assert AlertType.DRAWDOWN_LIMIT_EXCEEDED == "DRAWDOWN_LIMIT_EXCEEDED"
        assert AlertType.MARGIN_CALL == "MARGIN_CALL"
        assert AlertType.LIQUIDATION_WARNING == "LIQUIDATION_WARNING"


class TestRiskMetrics:
    """Test RiskMetrics value object."""

    def test_valid_risk_metrics(self):
        """Test creating valid risk metrics."""
        metrics = RiskMetrics(
            current_equity=Decimal("10000.00"),
            daily_pnl=Decimal("500.00"),
            unrealized_pnl=Decimal("-200.00"),
            realized_pnl=Decimal("700.00"),
            drawdown_percentage=Decimal("5.5"),
            margin_ratio=Decimal("25.0"),
            exposure_percentage=Decimal("60.0")
        )
        
        assert metrics.current_equity == Decimal("10000.00")
        assert metrics.daily_pnl == Decimal("500.00")
        assert metrics.unrealized_pnl == Decimal("-200.00")
        assert metrics.realized_pnl == Decimal("700.00")
        assert metrics.drawdown_percentage == Decimal("5.5")
        assert metrics.margin_ratio == Decimal("25.0")
        assert metrics.exposure_percentage == Decimal("60.0")

    def test_total_pnl_calculation(self):
        """Test total P&L calculation."""
        metrics = RiskMetrics(
            current_equity=Decimal("10000.00"),
            daily_pnl=Decimal("500.00"),
            unrealized_pnl=Decimal("-200.00"),
            realized_pnl=Decimal("700.00"),
            drawdown_percentage=Decimal("5.5"),
            margin_ratio=Decimal("25.0"),
            exposure_percentage=Decimal("60.0")
        )
        
        # total_pnl = realized_pnl + unrealized_pnl = 700 + (-200) = 500
        assert metrics.total_pnl == Decimal("500.00")

    def test_equity_at_risk_positive_unrealized(self):
        """Test equity at risk when unrealized PnL is positive."""
        metrics = RiskMetrics(
            current_equity=Decimal("10000.00"),
            daily_pnl=Decimal("500.00"),
            unrealized_pnl=Decimal("200.00"),  # Positive
            realized_pnl=Decimal("300.00"),
            drawdown_percentage=Decimal("5.5"),
            margin_ratio=Decimal("25.0"),
            exposure_percentage=Decimal("60.0")
        )
        
        # No equity at risk when unrealized PnL is positive
        assert metrics.equity_at_risk == Decimal("0")

    def test_equity_at_risk_negative_unrealized(self):
        """Test equity at risk when unrealized PnL is negative."""
        metrics = RiskMetrics(
            current_equity=Decimal("10000.00"),
            daily_pnl=Decimal("500.00"),
            unrealized_pnl=Decimal("-200.00"),  # Negative
            realized_pnl=Decimal("700.00"),
            drawdown_percentage=Decimal("5.5"),
            margin_ratio=Decimal("25.0"),
            exposure_percentage=Decimal("60.0")
        )
        
        # Equity at risk = abs(unrealized_pnl)
        assert metrics.equity_at_risk == Decimal("200.00")

    def test_invalid_negative_equity(self):
        """Test that negative equity raises ValueError."""
        with pytest.raises(ValueError, match="Current equity cannot be negative"):
            RiskMetrics(
                current_equity=Decimal("-100.00"),
                daily_pnl=Decimal("0"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                drawdown_percentage=Decimal("0"),
                margin_ratio=Decimal("0"),
                exposure_percentage=Decimal("0")
            )

    def test_invalid_drawdown_percentage_over_100(self):
        """Test that drawdown percentage over 100 raises ValueError."""
        with pytest.raises(ValueError, match="Drawdown percentage must be between 0 and 100"):
            RiskMetrics(
                current_equity=Decimal("10000.00"),
                daily_pnl=Decimal("0"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                drawdown_percentage=Decimal("150.0"),
                margin_ratio=Decimal("25.0"),
                exposure_percentage=Decimal("60.0")
            )

    def test_invalid_margin_ratio_over_100(self):
        """Test that margin ratio over 100 raises ValueError."""
        with pytest.raises(ValueError, match="Margin ratio must be between 0 and 100"):
            RiskMetrics(
                current_equity=Decimal("10000.00"),
                daily_pnl=Decimal("0"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                drawdown_percentage=Decimal("5.0"),
                margin_ratio=Decimal("150.0"),
                exposure_percentage=Decimal("60.0")
            )

    def test_invalid_exposure_percentage_over_100(self):
        """Test that exposure percentage over 100 raises ValueError."""
        with pytest.raises(ValueError, match="Exposure percentage must be between 0 and 100"):
            RiskMetrics(
                current_equity=Decimal("10000.00"),
                daily_pnl=Decimal("0"),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                drawdown_percentage=Decimal("5.0"),
                margin_ratio=Decimal("25.0"),
                exposure_percentage=Decimal("150.0")
            )

    def test_risk_metrics_immutability(self):
        """Test that RiskMetrics is immutable (frozen)."""
        metrics = RiskMetrics(
            current_equity=Decimal("10000.00"),
            daily_pnl=Decimal("500.00"),
            unrealized_pnl=Decimal("-200.00"),
            realized_pnl=Decimal("700.00"),
            drawdown_percentage=Decimal("5.5"),
            margin_ratio=Decimal("25.0"),
            exposure_percentage=Decimal("60.0")
        )
        
        with pytest.raises(AttributeError):
            metrics.current_equity = Decimal("20000.00")


class TestRiskThreshold:
    """Test RiskThreshold value object."""

    def test_valid_risk_threshold(self):
        """Test creating valid risk threshold."""
        threshold = RiskThreshold(
            warning_threshold=Decimal("80.0"),
            critical_threshold=Decimal("95.0")
        )
        
        assert threshold.warning_threshold == Decimal("80.0")
        assert threshold.critical_threshold == Decimal("95.0")

    def test_invalid_warning_threshold_zero(self):
        """Test that warning threshold of 0 raises ValueError."""
        with pytest.raises(ValueError, match="Warning threshold must be between 0 and 100"):
            RiskThreshold(
                warning_threshold=Decimal("0"),
                critical_threshold=Decimal("95.0")
            )

    def test_invalid_critical_threshold_over_100(self):
        """Test that critical threshold over 100 raises ValueError."""
        with pytest.raises(ValueError, match="Critical threshold must be between 0 and 100"):
            RiskThreshold(
                warning_threshold=Decimal("80.0"),
                critical_threshold=Decimal("150.0")
            )

    def test_invalid_warning_greater_than_critical(self):
        """Test that warning >= critical raises ValueError."""
        with pytest.raises(ValueError, match="Warning threshold must be less than critical threshold"):
            RiskThreshold(
                warning_threshold=Decimal("95.0"),
                critical_threshold=Decimal("80.0")
            )

    def test_invalid_warning_equals_critical(self):
        """Test that warning == critical raises ValueError."""
        with pytest.raises(ValueError, match="Warning threshold must be less than critical threshold"):
            RiskThreshold(
                warning_threshold=Decimal("90.0"),
                critical_threshold=Decimal("90.0")
            )

    def test_risk_threshold_immutability(self):
        """Test that RiskThreshold is immutable (frozen)."""
        threshold = RiskThreshold(
            warning_threshold=Decimal("80.0"),
            critical_threshold=Decimal("95.0")
        )
        
        with pytest.raises(AttributeError):
            threshold.warning_threshold = Decimal("70.0")


class TestLimitViolation:
    """Test LimitViolation value object."""

    def test_valid_limit_violation_with_symbol(self):
        """Test creating valid limit violation with symbol."""
        violation = LimitViolation(
            limit_type="POSITION_SIZE",
            current_value=Decimal("15000.00"),
            limit_value=Decimal("10000.00"),
            violation_percentage=Decimal("150.0"),
            symbol="BTCUSDT"
        )
        
        assert violation.limit_type == "POSITION_SIZE"
        assert violation.current_value == Decimal("15000.00")
        assert violation.limit_value == Decimal("10000.00")
        assert violation.violation_percentage == Decimal("150.0")
        assert violation.symbol == "BTCUSDT"

    def test_valid_limit_violation_without_symbol(self):
        """Test creating valid limit violation without symbol (global limit)."""
        violation = LimitViolation(
            limit_type="DAILY_LOSS",
            current_value=Decimal("1500.00"),
            limit_value=Decimal("1000.00"),
            violation_percentage=Decimal("150.0")
        )
        
        assert violation.symbol is None

    def test_is_warning_at_80_percent(self):
        """Test is_warning property at warning threshold (80%)."""
        violation = LimitViolation(
            limit_type="POSITION_SIZE",
            current_value=Decimal("8000.00"),
            limit_value=Decimal("10000.00"),
            violation_percentage=Decimal("80.0")
        )
        
        assert violation.is_warning is True
        assert violation.is_critical is False
        assert violation.is_breached is False

    def test_is_critical_at_95_percent(self):
        """Test is_critical property at critical threshold (95%)."""
        violation = LimitViolation(
            limit_type="POSITION_SIZE",
            current_value=Decimal("9500.00"),
            limit_value=Decimal("10000.00"),
            violation_percentage=Decimal("95.0")
        )
        
        assert violation.is_warning is True
        assert violation.is_critical is True
        assert violation.is_breached is False

    def test_is_breached_at_100_percent(self):
        """Test is_breached property when limit is exceeded (100%)."""
        violation = LimitViolation(
            limit_type="POSITION_SIZE",
            current_value=Decimal("10000.00"),
            limit_value=Decimal("10000.00"),
            violation_percentage=Decimal("100.0")
        )
        
        assert violation.is_warning is True
        assert violation.is_critical is True
        assert violation.is_breached is True

    def test_is_breached_over_100_percent(self):
        """Test is_breached property when limit is significantly exceeded."""
        violation = LimitViolation(
            limit_type="POSITION_SIZE",
            current_value=Decimal("15000.00"),
            limit_value=Decimal("10000.00"),
            violation_percentage=Decimal("150.0")
        )
        
        assert violation.is_warning is True
        assert violation.is_critical is True
        assert violation.is_breached is True

    def test_no_violation_below_warning(self):
        """Test that low violation percentages don't trigger flags."""
        violation = LimitViolation(
            limit_type="POSITION_SIZE",
            current_value=Decimal("5000.00"),
            limit_value=Decimal("10000.00"),
            violation_percentage=Decimal("50.0")
        )
        
        assert violation.is_warning is False
        assert violation.is_critical is False
        assert violation.is_breached is False

    def test_limit_violation_immutability(self):
        """Test that LimitViolation is immutable (frozen)."""
        violation = LimitViolation(
            limit_type="POSITION_SIZE",
            current_value=Decimal("15000.00"),
            limit_value=Decimal("10000.00"),
            violation_percentage=Decimal("150.0")
        )
        
        with pytest.raises(AttributeError):
            violation.current_value = Decimal("20000.00")
