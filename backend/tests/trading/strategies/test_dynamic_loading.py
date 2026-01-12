import pytest
import asyncio
from src.trading.strategies.registry import StrategyRegistry
from src.trading.strategies.base import StrategyBase
from src.trading.domain.bot import BotConfiguration

class MockExchange:
    pass

@pytest.mark.asyncio
async def test_dynamic_strategy_registration():
    registry = StrategyRegistry()
    
    # Python code for a dynamic strategy
    code = """
from src.trading.strategies.base import StrategyBase
import pandas as pd

class DynamicTestStrategy(StrategyBase):
    name = "DynamicTest"
    description = "A dynamically loaded test strategy"
    
    def __init__(self, exchange, config):
        super().__init__(exchange, config)
        self.tick_count = 0
        
    async def on_tick(self, market_data):
        self.tick_count += 1
        return {'action': 'hold'}
"""

    # 1. Register Dynamic Strategy
    success = registry.register_dynamic_strategy(code, "DynamicTest")
    assert success is True
    
    # 2. Retrieve Strategy Class
    strategy_cls = registry.get_strategy_class("DynamicTest")
    assert strategy_cls is not None
    assert strategy_cls.name == "DynamicTest"
    
    # 3. Instantiate and Run
    mock_exchange = MockExchange()
    mock_config = BotConfiguration(
        symbol="BTC/USD",
        base_quantity=1.0,
        quote_quantity=100.0,
        max_active_orders=5,
        risk_percentage=1.0,
        take_profit_percentage=2.0,
        stop_loss_percentage=1.0
    )
    
    strategy = strategy_cls(mock_exchange, mock_config)
    assert strategy.name == "DynamicTest"
    
    # 4. Execute Logic
    result = await strategy.on_tick({})
    assert result['action'] == 'hold'
    assert strategy.tick_count == 1
