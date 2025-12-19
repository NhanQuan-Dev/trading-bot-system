"""Unit tests for Bot domain value objects."""
import pytest
from decimal import Decimal
from typing import Dict, Any

from src.trading.domain.bot import (
    BotStatus,
    StrategyType,
    RiskLevel,
    BotConfiguration,
    StrategyParameters,
    BotPerformance,
)


class TestBotStatus:
    """Test BotStatus enum."""
    
    def test_bot_status_values(self):
        """Test that bot status enum has correct values."""
        assert BotStatus.ACTIVE == "ACTIVE"
        assert BotStatus.PAUSED == "PAUSED"
        assert BotStatus.STOPPED == "STOPPED"
        assert BotStatus.ERROR == "ERROR"
        assert BotStatus.STARTING == "STARTING"
        assert BotStatus.STOPPING == "STOPPING"
    
    def test_bot_status_enum_comparison(self):
        """Test bot status enum comparison."""
        status = BotStatus.ACTIVE
        assert status == BotStatus.ACTIVE
        assert status != BotStatus.STOPPED
        assert status.value == "ACTIVE"


class TestStrategyType:
    """Test StrategyType enum."""
    
    def test_strategy_type_values(self):
        """Test that strategy type enum has correct values."""
        assert StrategyType.GRID == "GRID"
        assert StrategyType.DCA == "DCA"
        assert StrategyType.MARTINGALE == "MARTINGALE"
        assert StrategyType.TREND_FOLLOWING == "TREND_FOLLOWING"
        assert StrategyType.MEAN_REVERSION == "MEAN_REVERSION"
        assert StrategyType.ARBITRAGE == "ARBITRAGE"
        assert StrategyType.CUSTOM == "CUSTOM"
    
    def test_strategy_type_enum_comparison(self):
        """Test strategy type enum comparison."""
        strategy = StrategyType.GRID
        assert strategy == StrategyType.GRID
        assert strategy != StrategyType.DCA
        assert strategy.value == "GRID"


class TestRiskLevel:
    """Test RiskLevel enum."""
    
    def test_risk_level_values(self):
        """Test that risk level enum has correct values."""
        assert RiskLevel.CONSERVATIVE == "CONSERVATIVE"
        assert RiskLevel.MODERATE == "MODERATE"
        assert RiskLevel.AGGRESSIVE == "AGGRESSIVE"
        assert RiskLevel.EXTREME == "EXTREME"


class TestBotConfiguration:
    """Test BotConfiguration value object."""
    
    def test_valid_bot_configuration(self):
        """Test creating valid bot configuration."""
        config = BotConfiguration(
            symbol="BTCUSDT",
            base_quantity=Decimal("0.001"),
            quote_quantity=Decimal("100.00"),
            max_active_orders=5,
            risk_percentage=Decimal("2.5"),
            take_profit_percentage=Decimal("2.0"),
            stop_loss_percentage=Decimal("1.5"),
            strategy_settings={"grid_levels": 10},
            max_daily_loss=Decimal("50.00"),
            max_drawdown=Decimal("10.00")
        )
        
        assert config.symbol == "BTCUSDT"
        assert config.base_quantity == Decimal("0.001")
        assert config.quote_quantity == Decimal("100.00")
        assert config.max_active_orders == 5
        assert config.risk_percentage == Decimal("2.5")
        assert config.take_profit_percentage == Decimal("2.0")
        assert config.stop_loss_percentage == Decimal("1.5")
        assert config.strategy_settings == {"grid_levels": 10}
        assert config.max_daily_loss == Decimal("50.00")
        assert config.max_drawdown == Decimal("10.00")
    
    def test_minimal_bot_configuration(self):
        """Test creating minimal bot configuration with defaults."""
        config = BotConfiguration(
            symbol="ETHUSDT",
            base_quantity=Decimal("0.1"),
            quote_quantity=Decimal("500.00"),
            max_active_orders=3,
            risk_percentage=Decimal("5.0"),
            take_profit_percentage=Decimal("3.0"),
            stop_loss_percentage=Decimal("2.0")
        )
        
        assert config.symbol == "ETHUSDT"
        assert config.strategy_settings == {}
        assert config.max_daily_loss is None
        assert config.max_drawdown is None
    
    def test_invalid_base_quantity(self):
        """Test that negative or zero base quantity raises ValueError."""
        with pytest.raises(ValueError, match="Base quantity must be positive"):
            BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        
        with pytest.raises(ValueError, match="Base quantity must be positive"):
            BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("-0.1"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
    
    def test_invalid_quote_quantity(self):
        """Test that negative or zero quote quantity raises ValueError."""
        with pytest.raises(ValueError, match="Quote quantity must be positive"):
            BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("0"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
    
    def test_invalid_max_active_orders(self):
        """Test that negative or zero max active orders raises ValueError."""
        with pytest.raises(ValueError, match="Max active orders must be positive"):
            BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=0,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
    
    def test_invalid_risk_percentage(self):
        """Test that invalid risk percentage raises ValueError."""
        with pytest.raises(ValueError, match="Risk percentage must be between 0 and 100"):
            BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("0"),  # Must be > 0
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        
        with pytest.raises(ValueError, match="Risk percentage must be between 0 and 100"):
            BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("101"),  # Must be <= 100
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
    
    def test_invalid_take_profit_percentage(self):
        """Test that negative or zero take profit percentage raises ValueError."""
        with pytest.raises(ValueError, match="Take profit percentage must be positive"):
            BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("0"),
                stop_loss_percentage=Decimal("1.5")
            )
    
    def test_invalid_stop_loss_percentage(self):
        """Test that negative or zero stop loss percentage raises ValueError."""
        with pytest.raises(ValueError, match="Stop loss percentage must be positive"):
            BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("0")
            )
    
    def test_bot_configuration_immutability(self):
        """Test that BotConfiguration is immutable (frozen)."""
        config = BotConfiguration(
            symbol="BTCUSDT",
            base_quantity=Decimal("0.001"),
            quote_quantity=Decimal("100.00"),
            max_active_orders=5,
            risk_percentage=Decimal("2.5"),
            take_profit_percentage=Decimal("2.0"),
            stop_loss_percentage=Decimal("1.5")
        )
        
        with pytest.raises(AttributeError):
            config.symbol = "ETHUSDT"


class TestStrategyParameters:
    """Test StrategyParameters value object."""
    
    def test_valid_strategy_parameters(self):
        """Test creating valid strategy parameters."""
        params = StrategyParameters(
            strategy_type=StrategyType.GRID,
            name="Grid Trading Strategy",
            description="Basic grid trading with 10 levels",
            parameters={
                "grid_levels": 10,
                "grid_spacing": 0.5,
                "rebalance_threshold": 0.1
            }
        )
        
        assert params.strategy_type == StrategyType.GRID
        assert params.name == "Grid Trading Strategy"
        assert params.description == "Basic grid trading with 10 levels"
        assert params.parameters["grid_levels"] == 10
        assert params.parameters["grid_spacing"] == 0.5
        assert params.parameters["rebalance_threshold"] == 0.1
    
    def test_empty_strategy_name(self):
        """Test that empty strategy name raises ValueError."""
        with pytest.raises(ValueError, match="Strategy name cannot be empty"):
            StrategyParameters(
                strategy_type=StrategyType.DCA,
                name="",
                description="Test",
                parameters={"param1": "value1"}
            )
        
        with pytest.raises(ValueError, match="Strategy name cannot be empty"):
            StrategyParameters(
                strategy_type=StrategyType.DCA,
                name="   ",  # Whitespace only
                description="Test",
                parameters={"param1": "value1"}
            )
    
    def test_empty_strategy_parameters(self):
        """Test that empty strategy parameters raises ValueError."""
        with pytest.raises(ValueError, match="Strategy parameters cannot be empty"):
            StrategyParameters(
                strategy_type=StrategyType.DCA,
                name="Test Strategy",
                description="Test description",
                parameters={}
            )
    
    def test_strategy_parameters_immutability(self):
        """Test that StrategyParameters is immutable (frozen)."""
        params = StrategyParameters(
            strategy_type=StrategyType.GRID,
            name="Grid Strategy",
            description="Test",
            parameters={"levels": 5}
        )
        
        with pytest.raises(AttributeError):
            params.name = "New Name"


class TestBotPerformance:
    """Test BotPerformance value object."""
    
    def test_default_bot_performance(self):
        """Test creating bot performance with default values."""
        performance = BotPerformance()
        
        assert performance.total_trades == 0
        assert performance.winning_trades == 0
        assert performance.losing_trades == 0
        assert performance.total_profit_loss == Decimal("0")
        assert performance.total_fees == Decimal("0")
        assert performance.max_drawdown == Decimal("0")
        assert performance.sharpe_ratio is None
    
    def test_bot_performance_with_values(self):
        """Test creating bot performance with specific values."""
        performance = BotPerformance(
            total_trades=100,
            winning_trades=65,
            losing_trades=35,
            total_profit_loss=Decimal("1250.50"),
            total_fees=Decimal("125.25"),
            max_drawdown=Decimal("150.00"),
            sharpe_ratio=Decimal("1.85")
        )
        
        assert performance.total_trades == 100
        assert performance.winning_trades == 65
        assert performance.losing_trades == 35
        assert performance.total_profit_loss == Decimal("1250.50")
        assert performance.total_fees == Decimal("125.25")
        assert performance.max_drawdown == Decimal("150.00")
        assert performance.sharpe_ratio == Decimal("1.85")
    
    def test_win_rate_calculation(self):
        """Test win rate percentage calculation."""
        # No trades
        performance = BotPerformance()
        assert performance.win_rate == 0.0
        
        # With trades
        performance = BotPerformance(
            total_trades=100,
            winning_trades=65,
            losing_trades=35
        )
        assert performance.win_rate == 65.0
        
        # Perfect win rate
        performance = BotPerformance(
            total_trades=10,
            winning_trades=10,
            losing_trades=0
        )
        assert performance.win_rate == 100.0
    
    def test_net_profit_loss_calculation(self):
        """Test net profit/loss calculation after fees."""
        performance = BotPerformance(
            total_profit_loss=Decimal("1000.00"),
            total_fees=Decimal("50.00")
        )
        assert performance.net_profit_loss == Decimal("950.00")
        
        # Loss scenario
        performance = BotPerformance(
            total_profit_loss=Decimal("-200.00"),
            total_fees=Decimal("30.00")
        )
        assert performance.net_profit_loss == Decimal("-230.00")
    
    def test_average_profit_per_trade_calculation(self):
        """Test average profit per trade calculation."""
        # No trades
        performance = BotPerformance()
        assert performance.average_profit_per_trade == Decimal("0")
        
        # With trades
        performance = BotPerformance(
            total_trades=10,
            total_profit_loss=Decimal("500.00"),
            total_fees=Decimal("50.00")
        )
        # Net profit = 500 - 50 = 450, average = 450/10 = 45
        assert performance.average_profit_per_trade == Decimal("45.0")
    
    def test_bot_performance_immutability(self):
        """Test that BotPerformance is immutable (frozen)."""
        performance = BotPerformance(total_trades=10)
        
        with pytest.raises(AttributeError):
            performance.total_trades = 20