"""Unit tests for Bot domain entities."""
import pytest
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from src.trading.domain.bot import (
    Bot,
    Strategy,
    BotStatus,
    StrategyType,
    RiskLevel,
    BotConfiguration,
    StrategyParameters,
    BotPerformance,
)


class TestStrategy:
    """Test Strategy entity."""
    
    def test_create_strategy(self):
        """Test creating a new strategy."""
        user_id = uuid.uuid4()
        parameters = {
            "grid_levels": 10,
            "grid_spacing": 0.5,
            "base_order_size": 100
        }
        
        with patch('src.trading.domain.bot.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            strategy = Strategy.create(
                user_id=user_id,
                name="Test Grid Strategy",
                strategy_type=StrategyType.GRID,
                description="A test grid trading strategy",
                parameters=parameters
            )
        
        assert isinstance(strategy.id, uuid.UUID)
        assert strategy.user_id == user_id
        assert strategy.name == "Test Grid Strategy"
        assert strategy.strategy_type == StrategyType.GRID
        assert strategy.description == "A test grid trading strategy"
        assert strategy.parameters.strategy_type == StrategyType.GRID
        assert strategy.parameters.name == "Test Grid Strategy"
        assert strategy.parameters.parameters == parameters
        assert strategy.is_active is True
        assert strategy.created_at == mock_now
        assert strategy.updated_at == mock_now
        assert strategy.backtest_results is None
        assert isinstance(strategy.live_performance, BotPerformance)
    
    def test_update_parameters(self):
        """Test updating strategy parameters."""
        strategy = Strategy.create(
            user_id=uuid.uuid4(),
            name="Test Strategy",
            strategy_type=StrategyType.DCA,
            description="Test description",
            parameters={"param1": "value1"}
        )
        
        new_parameters = {"param1": "new_value", "param2": "value2"}
        
        with patch('src.trading.domain.bot.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            strategy.update_parameters(new_parameters)
        
        assert strategy.parameters.parameters == new_parameters
        assert strategy.updated_at == mock_now
    
    def test_activate_strategy(self):
        """Test activating a strategy."""
        strategy = Strategy.create(
            user_id=uuid.uuid4(),
            name="Test Strategy",
            strategy_type=StrategyType.GRID,
            description="Test description",
            parameters={"param1": "value1"}
        )
        
        strategy.is_active = False
        
        with patch('src.trading.domain.bot.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            strategy.activate()
        
        assert strategy.is_active is True
        assert strategy.updated_at == mock_now
    
    def test_deactivate_strategy(self):
        """Test deactivating a strategy."""
        strategy = Strategy.create(
            user_id=uuid.uuid4(),
            name="Test Strategy",
            strategy_type=StrategyType.GRID,
            description="Test description",
            parameters={"param1": "value1"}
        )
        
        assert strategy.is_active is True
        
        with patch('src.trading.domain.bot.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 15, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            strategy.deactivate()
        
        assert strategy.is_active is False
        assert strategy.updated_at == mock_now


class TestBot:
    """Test Bot entity."""
    
    def test_create_bot(self):
        """Test creating a new bot."""
        user_id = uuid.uuid4()
        strategy_id = uuid.uuid4()
        exchange_connection_id = uuid.uuid4()
        
        configuration = BotConfiguration(
            symbol="BTCUSDT",
            base_quantity=Decimal("0.001"),
            quote_quantity=Decimal("100.00"),
            max_active_orders=5,
            risk_percentage=Decimal("2.5"),
            take_profit_percentage=Decimal("2.0"),
            stop_loss_percentage=Decimal("1.5")
        )
        
        with patch('src.trading.domain.bot.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            bot = Bot.create(
                user_id=user_id,
                name="Test Bot",
                strategy_id=strategy_id,
                exchange_connection_id=exchange_connection_id,
                configuration=configuration,
                description="A test trading bot",
                risk_level=RiskLevel.MODERATE
            )
        
        assert isinstance(bot.id, uuid.UUID)
        assert bot.user_id == user_id
        assert bot.name == "Test Bot"
        assert bot.strategy_id == strategy_id
        assert bot.exchange_connection_id == exchange_connection_id
        assert bot.status == BotStatus.STOPPED
        assert bot.configuration == configuration
        assert bot.description == "A test trading bot"
        assert bot.risk_level == RiskLevel.MODERATE
        assert bot.created_at == mock_now
        assert bot.updated_at == mock_now
        assert bot.start_time is None
        assert bot.stop_time is None
        assert bot.last_error is None
        assert isinstance(bot.performance, BotPerformance)
        assert bot.active_orders == []
        assert bot.daily_pnl == Decimal("0")
        assert bot.total_runtime_seconds == 0
        assert bot.metadata == {}
    
    def test_create_bot_minimal(self):
        """Test creating bot with minimal parameters."""
        bot = Bot.create(
            user_id=uuid.uuid4(),
            name="Minimal Bot",
            strategy_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            configuration=BotConfiguration(
                symbol="ETHUSDT",
                base_quantity=Decimal("0.1"),
                quote_quantity=Decimal("500.00"),
                max_active_orders=3,
                risk_percentage=Decimal("5.0"),
                take_profit_percentage=Decimal("3.0"),
                stop_loss_percentage=Decimal("2.0")
            )
        )
        
        assert bot.description is None
        assert bot.risk_level == RiskLevel.MODERATE  # Default
        assert bot.status == BotStatus.STOPPED
    
    def test_start_bot(self):
        """Test starting a bot."""
        bot = Bot.create(
            user_id=uuid.uuid4(),
            name="Test Bot",
            strategy_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            configuration=BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        )
        
        assert bot.status == BotStatus.STOPPED
        
        with patch('src.trading.domain.bot.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            bot.start()
        
        assert bot.status == BotStatus.STARTING
        assert bot.start_time == mock_now
        assert bot.updated_at == mock_now
        assert bot.last_error is None
    
    def test_start_bot_from_error(self):
        """Test starting bot from error status."""
        bot = Bot.create(
            user_id=uuid.uuid4(),
            name="Test Bot",
            strategy_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            configuration=BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        )
        
        bot.mark_error("Test error")
        assert bot.status == BotStatus.ERROR
        
        bot.start()
        assert bot.status == BotStatus.STARTING
    
    def test_start_bot_invalid_status(self):
        """Test that starting bot from invalid status raises error."""
        bot = Bot.create(
            user_id=uuid.uuid4(),
            name="Test Bot",
            strategy_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            configuration=BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        )
        
        bot.status = BotStatus.STARTING
        
        with pytest.raises(ValueError, match="Cannot start bot in BotStatus.STARTING status"):
            bot.start()
        
        bot.status = BotStatus.ACTIVE
        
        with pytest.raises(ValueError, match="Cannot start bot in BotStatus.ACTIVE status"):
            bot.start()
    
    def test_mark_active(self):
        """Test marking bot as active."""
        bot = Bot.create(
            user_id=uuid.uuid4(),
            name="Test Bot",
            strategy_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            configuration=BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        )
        
        bot.start()
        assert bot.status == BotStatus.STARTING
        
        with patch('src.trading.domain.bot.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            bot.mark_active()
        
        assert bot.status == BotStatus.ACTIVE
        assert bot.updated_at == mock_now
    
    def test_mark_active_invalid_status(self):
        """Test that marking active from invalid status raises error."""
        bot = Bot.create(
            user_id=uuid.uuid4(),
            name="Test Bot",
            strategy_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            configuration=BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        )
        
        # Bot is in STOPPED status initially
        with pytest.raises(ValueError, match="Cannot mark active from BotStatus.STOPPED status"):
            bot.mark_active()
    
    def test_pause_bot(self):
        """Test pausing an active bot."""
        bot = Bot.create(
            user_id=uuid.uuid4(),
            name="Test Bot",
            strategy_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            configuration=BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        )
        
        bot.start()
        bot.mark_active()
        assert bot.status == BotStatus.ACTIVE
        
        with patch('src.trading.domain.bot.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            bot.pause("Manual pause for testing")
        
        assert bot.status == BotStatus.PAUSED
        assert bot.updated_at == mock_now
        assert bot.metadata["pause_reason"] == "Manual pause for testing"
    
    def test_pause_bot_no_reason(self):
        """Test pausing bot without reason."""
        bot = Bot.create(
            user_id=uuid.uuid4(),
            name="Test Bot",
            strategy_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            configuration=BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        )
        
        bot.start()
        bot.mark_active()
        
        bot.pause()
        
        assert bot.status == BotStatus.PAUSED
        assert "pause_reason" not in bot.metadata
    
    def test_pause_bot_invalid_status(self):
        """Test that pausing bot from invalid status raises error."""
        bot = Bot.create(
            user_id=uuid.uuid4(),
            name="Test Bot",
            strategy_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            configuration=BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        )
        
        # Bot is in STOPPED status initially
        with pytest.raises(ValueError, match="Cannot pause bot in BotStatus.STOPPED status"):
            bot.pause()
    
    def test_resume_bot(self):
        """Test resuming a paused bot."""
        bot = Bot.create(
            user_id=uuid.uuid4(),
            name="Test Bot",
            strategy_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            configuration=BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        )
        
        bot.start()
        bot.mark_active()
        bot.pause("Test pause")
        assert bot.status == BotStatus.PAUSED
        assert "pause_reason" in bot.metadata
        
        with patch('src.trading.domain.bot.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            bot.resume()
        
        assert bot.status == BotStatus.ACTIVE
        assert bot.updated_at == mock_now
        assert "pause_reason" not in bot.metadata
    
    def test_resume_bot_invalid_status(self):
        """Test that resuming bot from invalid status raises error."""
        bot = Bot.create(
            user_id=uuid.uuid4(),
            name="Test Bot",
            strategy_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            configuration=BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        )
        
        # Bot is in STOPPED status initially
        with pytest.raises(ValueError, match="Cannot resume bot in BotStatus.STOPPED status"):
            bot.resume()
    
    def test_stop_bot(self):
        """Test stopping a bot."""
        bot = Bot.create(
            user_id=uuid.uuid4(),
            name="Test Bot",
            strategy_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            configuration=BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        )
        
        bot.start()
        bot.mark_active()
        assert bot.status == BotStatus.ACTIVE
        
        with patch('src.trading.domain.bot.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 15, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            bot.stop("Manual stop for testing")
        
        assert bot.status == BotStatus.STOPPING
        assert bot.stop_time == mock_now
        assert bot.updated_at == mock_now
        assert bot.metadata["stop_reason"] == "Manual stop for testing"
    
    def test_stop_bot_already_stopped(self):
        """Test that stopping already stopped bot raises error."""
        bot = Bot.create(
            user_id=uuid.uuid4(),
            name="Test Bot",
            strategy_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            configuration=BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        )
        
        # Bot is in STOPPED status initially
        with pytest.raises(ValueError, match="Bot is already BotStatus.STOPPED"):
            bot.stop()
    
    def test_mark_stopped(self):
        """Test marking bot as stopped."""
        bot = Bot.create(
            user_id=uuid.uuid4(),
            name="Test Bot",
            strategy_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            configuration=BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        )
        
        bot.start()
        bot.mark_active()
        bot.stop()
        assert bot.status == BotStatus.STOPPING
        
        # Add some active orders
        order_id = uuid.uuid4()
        bot.add_active_order(order_id)
        
        with patch('src.trading.domain.bot.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 15, 30, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            bot.mark_stopped()
        
        assert bot.status == BotStatus.STOPPED
        assert bot.active_orders == []  # Should be cleared
        assert bot.updated_at == mock_now
    
    def test_mark_error(self):
        """Test marking bot as error."""
        bot = Bot.create(
            user_id=uuid.uuid4(),
            name="Test Bot",
            strategy_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            configuration=BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        )
        
        bot.start()
        bot.mark_active()
        
        with patch('src.trading.domain.bot.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 16, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            bot.mark_error("Connection timeout")
        
        assert bot.status == BotStatus.ERROR
        assert bot.last_error == "Connection timeout"
        assert bot.stop_time == mock_now
        assert bot.updated_at == mock_now
    
    def test_update_configuration(self):
        """Test updating bot configuration when stopped."""
        bot = Bot.create(
            user_id=uuid.uuid4(),
            name="Test Bot",
            strategy_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            configuration=BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        )
        
        new_config = BotConfiguration(
            symbol="ETHUSDT",
            base_quantity=Decimal("0.1"),
            quote_quantity=Decimal("500.00"),
            max_active_orders=10,
            risk_percentage=Decimal("5.0"),
            take_profit_percentage=Decimal("3.0"),
            stop_loss_percentage=Decimal("2.5")
        )
        
        with patch('src.trading.domain.bot.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 17, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            bot.update_configuration(new_config)
        
        assert bot.configuration == new_config
        assert bot.updated_at == mock_now
    
    def test_update_configuration_not_stopped(self):
        """Test that updating configuration when not stopped raises error."""
        bot = Bot.create(
            user_id=uuid.uuid4(),
            name="Test Bot",
            strategy_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            configuration=BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        )
        
        bot.start()
        bot.mark_active()
        
        new_config = BotConfiguration(
            symbol="ETHUSDT",
            base_quantity=Decimal("0.1"),
            quote_quantity=Decimal("500.00"),
            max_active_orders=10,
            risk_percentage=Decimal("5.0"),
            take_profit_percentage=Decimal("3.0"),
            stop_loss_percentage=Decimal("2.5")
        )
        
        with pytest.raises(ValueError, match="Can only update configuration when bot is stopped"):
            bot.update_configuration(new_config)
    
    def test_add_active_order(self):
        """Test adding active orders."""
        bot = Bot.create(
            user_id=uuid.uuid4(),
            name="Test Bot",
            strategy_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            configuration=BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        )
        
        order_id_1 = uuid.uuid4()
        order_id_2 = uuid.uuid4()
        
        bot.add_active_order(order_id_1)
        assert order_id_1 in bot.active_orders
        assert len(bot.active_orders) == 1
        
        bot.add_active_order(order_id_2)
        assert order_id_2 in bot.active_orders
        assert len(bot.active_orders) == 2
        
        # Adding same order again should not duplicate
        bot.add_active_order(order_id_1)
        assert len(bot.active_orders) == 2
    
    def test_remove_active_order(self):
        """Test removing active orders."""
        bot = Bot.create(
            user_id=uuid.uuid4(),
            name="Test Bot",
            strategy_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            configuration=BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        )
        
        order_id_1 = uuid.uuid4()
        order_id_2 = uuid.uuid4()
        order_id_3 = uuid.uuid4()
        
        bot.add_active_order(order_id_1)
        bot.add_active_order(order_id_2)
        assert len(bot.active_orders) == 2
        
        bot.remove_active_order(order_id_1)
        assert order_id_1 not in bot.active_orders
        assert order_id_2 in bot.active_orders
        assert len(bot.active_orders) == 1
        
        # Removing non-existent order should not raise error
        bot.remove_active_order(order_id_3)
        assert len(bot.active_orders) == 1
    
    def test_update_performance(self):
        """Test updating bot performance."""
        bot = Bot.create(
            user_id=uuid.uuid4(),
            name="Test Bot",
            strategy_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            configuration=BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        )
        
        new_performance = BotPerformance(
            total_trades=50,
            winning_trades=35,
            losing_trades=15,
            total_profit_loss=Decimal("750.25"),
            total_fees=Decimal("75.50")
        )
        
        with patch('src.trading.domain.bot.dt') as mock_dt:
            mock_now = datetime(2024, 1, 1, 18, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = mock_now
            mock_dt.timezone.utc = timezone.utc
            
            bot.update_performance(new_performance)
        
        assert bot.performance == new_performance
        assert bot.updated_at == mock_now
    
    def test_bot_status_checks(self):
        """Test bot status check methods."""
        bot = Bot.create(
            user_id=uuid.uuid4(),
            name="Test Bot",
            strategy_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            configuration=BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        )
        
        # Initially stopped
        assert bot.is_stopped() is True
        assert bot.is_active() is False
        assert bot.can_be_started() is True
        assert bot.can_be_stopped() is False
        
        # After starting
        bot.start()
        bot.mark_active()
        assert bot.is_stopped() is False
        assert bot.is_active() is True
        assert bot.can_be_started() is False
        assert bot.can_be_stopped() is True
        
        # After pausing
        bot.pause()
        assert bot.is_stopped() is False
        assert bot.is_active() is False
        assert bot.can_be_started() is False
        assert bot.can_be_stopped() is True
        
        # After error
        bot.mark_error("Test error")
        assert bot.is_stopped() is False
        assert bot.is_active() is False
        assert bot.can_be_started() is True
        assert bot.can_be_stopped() is True
    
    def test_get_runtime_seconds(self):
        """Test runtime calculation."""
        bot = Bot.create(
            user_id=uuid.uuid4(),
            name="Test Bot",
            strategy_id=uuid.uuid4(),
            exchange_connection_id=uuid.uuid4(),
            configuration=BotConfiguration(
                symbol="BTCUSDT",
                base_quantity=Decimal("0.001"),
                quote_quantity=Decimal("100.00"),
                max_active_orders=5,
                risk_percentage=Decimal("2.5"),
                take_profit_percentage=Decimal("2.0"),
                stop_loss_percentage=Decimal("1.5")
            )
        )
        
        # No start time
        assert bot.get_runtime_seconds() == 0
        
        # Set start time
        with patch('src.trading.domain.bot.dt') as mock_dt:
            start_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.now.return_value = start_time
            mock_dt.timezone.utc = timezone.utc
            
            bot.start()
            assert bot.start_time == start_time
        
        # Bot is active - calculate from current time
        with patch('src.trading.domain.bot.dt') as mock_dt:
            current_time = datetime(2024, 1, 1, 13, 30, 0, tzinfo=timezone.utc)  # 1.5 hours later
            mock_dt.now.return_value = current_time
            mock_dt.timezone.utc = timezone.utc
            
            bot.mark_active()
            runtime = bot.get_runtime_seconds()
            assert runtime == 5400  # 1.5 hours = 5400 seconds
        
        # Bot is stopped - calculate from stop time
        with patch('src.trading.domain.bot.dt') as mock_dt:
            stop_time = datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc)  # 2 hours after start
            mock_dt.now.return_value = stop_time
            mock_dt.timezone.utc = timezone.utc
            
            bot.stop()
            bot.mark_stopped()
            runtime = bot.get_runtime_seconds()
            assert runtime == 7200  # 2 hours = 7200 seconds