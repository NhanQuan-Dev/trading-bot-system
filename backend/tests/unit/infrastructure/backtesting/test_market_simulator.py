"""Unit tests for market simulator."""

import pytest
from decimal import Decimal

from src.trading.infrastructure.backtesting.market_simulator import MarketSimulator
from src.trading.domain.backtesting import SlippageModel, CommissionModel


class TestMarketSimulator:
    """Test MarketSimulator."""
    
    def test_create_simulator(self):
        """Test creating market simulator."""
        simulator = MarketSimulator(
            slippage_model=SlippageModel.FIXED,
            slippage_percent=Decimal("1.0"),
            commission_model=CommissionModel.FIXED_RATE,
            commission_rate=Decimal("0.1"),
        )
        
        assert simulator.slippage_model == SlippageModel.FIXED
        assert simulator.commission_model == CommissionModel.FIXED_RATE
    
    def test_simulate_long_entry_no_costs(self):
        """Test simulating long entry with no costs."""
        simulator = MarketSimulator(
            slippage_model=SlippageModel.NONE,
            commission_model=CommissionModel.NONE,
        )
        
        fill = simulator.simulate_long_entry(
            symbol="BTCUSDT",
            quantity=Decimal("0.1"),
            current_price=Decimal("42000"),
            timestamp="2024-01-01T10:00:00Z",
        )
        
        assert fill.filled_price == Decimal("42000")
        assert fill.filled_quantity == Decimal("0.1")
        assert fill.commission == Decimal("0")
        assert fill.slippage == Decimal("0")
    
    def test_simulate_long_entry_with_percentage_slippage(self):
        """Test long entry with fixed slippage."""
        simulator = MarketSimulator(
            slippage_model=SlippageModel.FIXED,
            slippage_percent=Decimal("42"),  # $42 fixed
            commission_model=CommissionModel.NONE,
        )
        
        fill = simulator.simulate_long_entry(
            symbol="BTCUSDT",
            quantity=Decimal("0.1"),
            current_price=Decimal("42000"),
            timestamp="2024-01-01T10:00:00Z",
        )
        
        # Slippage = 42000 * 0.001 = 42
        # Filled price = 42000 + 42 = 42042
        expected_slippage = Decimal("42000") * (Decimal("0.1") / Decimal("100"))
        assert fill.slippage == expected_slippage
        assert fill.filled_price > Decimal("42000")
    
    def test_simulate_long_entry_with_commission(self):
        """Test long entry with percentage commission."""
        simulator = MarketSimulator(
            slippage_model=SlippageModel.NONE,
            commission_model=CommissionModel.FIXED_RATE,
            commission_rate=Decimal("0.1"),  # 0.1%
        )
        
        fill = simulator.simulate_long_entry(
            symbol="BTCUSDT",
            quantity=Decimal("0.1"),
            current_price=Decimal("42000"),
            timestamp="2024-01-01T10:00:00Z",
        )
        
        # Notional = 41958 * 0.1 = 4195.8 (if no cost model but there is taker fee override in engine)
        # However simulator directly calculates it.
        notional = fill.filled_price * Decimal("0.1")
        expected_commission = notional * (Decimal("0.1") / Decimal("100"))
        assert fill.commission == expected_commission
    
    def test_simulate_short_entry_no_costs(self):
        """Test simulating short entry with no costs."""
        simulator = MarketSimulator(
            slippage_model=SlippageModel.NONE,
            commission_model=CommissionModel.NONE,
        )
        
        fill = simulator.simulate_short_entry(
            symbol="BTCUSDT",
            quantity=Decimal("0.1"),
            current_price=Decimal("42000"),
            timestamp="2024-01-01T10:00:00Z",
        )
        
        assert fill.filled_price == Decimal("42000")
        assert fill.filled_quantity == Decimal("0.1")
        assert fill.commission == Decimal("0")
        assert fill.slippage == Decimal("0")
    
    def test_simulate_short_entry_with_bid_ask_spread(self):
        """Test short entry with bid-ask spread."""
        simulator = MarketSimulator(
            slippage_model=SlippageModel.NONE,
            commission_model=CommissionModel.NONE,
            use_bid_ask_spread=True,
            spread_percent=Decimal("0.05"),  # 0.05%
        )
        
        fill = simulator.simulate_short_entry(
            symbol="BTCUSDT",
            quantity=Decimal("0.1"),
            current_price=Decimal("42000"),
            timestamp="2024-01-01T10:00:00Z",
        )
        
        # Bid price = 42000 * (1 - 0.0005) = 41979
        expected_bid = Decimal("42000") * (Decimal("1") - Decimal("0.05") / Decimal("100"))
        assert fill.filled_price < Decimal("42000")
    
    def test_fixed_commission_model(self):
        """Test fixed commission model."""
        simulator = MarketSimulator(
            slippage_model=SlippageModel.NONE,
            commission_model="fixed",  # Use string for fixed fee
            commission_rate=Decimal("5"),  # $5 flat fee
        )
        
        fill = simulator.simulate_long_entry(
            symbol="BTCUSDT",
            quantity=Decimal("0.1"),
            current_price=Decimal("42000"),
            timestamp="2024-01-01T10:00:00Z",
        )
        
        assert fill.commission == Decimal("5")
    
    def test_tiered_commission_model(self):
        """Test tiered commission model."""
        simulator = MarketSimulator(
            slippage_model=SlippageModel.NONE,
            commission_model=CommissionModel.TIERED,
            commission_rate=Decimal("0.1"),
        )
        
        # Small order (< $1000)
        fill_small = simulator.simulate_long_entry(
            symbol="BTCUSDT",
            quantity=Decimal("0.01"),
            current_price=Decimal("42000"),
            timestamp="2024-01-01T10:00:00Z",
        )
        
        # Large order (> $10000)
        fill_large = simulator.simulate_long_entry(
            symbol="BTCUSDT",
            quantity=Decimal("0.5"),
            current_price=Decimal("42000"),
            timestamp="2024-01-01T10:00:00Z",
        )
        
        # Large orders should have lower commission rate
        notional_small = Decimal("42000") * Decimal("0.01")
        notional_large = Decimal("42000") * Decimal("0.5")
        
        # Commission as percentage of notional
        commission_pct_small = (fill_small.commission / notional_small) * Decimal("100")
        commission_pct_large = (fill_large.commission / notional_large) * Decimal("100")
        
        assert commission_pct_large < commission_pct_small
    
    def test_limit_order_validation(self):
        """Test limit order price validation."""
        simulator = MarketSimulator()
        
        # Long limit should only fill if price <= limit
        can_fill_buy = simulator.can_fill_order(
            order_price=Decimal("42500"),
            current_price=Decimal("42000"),
            is_long=True,
            is_limit=True,
        )
        assert can_fill_buy is True
        
        cannot_fill_buy = simulator.can_fill_order(
            order_price=Decimal("41500"),
            current_price=Decimal("42000"),
            is_long=True,
            is_limit=True,
        )
        assert cannot_fill_buy is False
        
        # Short limit should only fill if price >= limit
        can_fill_sell = simulator.can_fill_order(
            order_price=Decimal("41500"),
            current_price=Decimal("42000"),
            is_long=False,
            is_limit=True,
        )
        assert can_fill_sell is True
        
        cannot_fill_sell = simulator.can_fill_order(
            order_price=Decimal("42500"),
            current_price=Decimal("42000"),
            is_long=False,
            is_limit=True,
        )
        assert cannot_fill_sell is False
    
    def test_estimate_fill_price(self):
        """Test fill price estimation."""
        simulator = MarketSimulator(
            slippage_model=SlippageModel.FIXED,
            slippage_percent=Decimal("10"),
            use_bid_ask_spread=True,
            spread_percent=Decimal("0.05"),
        )
        
        # Long order - should be above current price
        buy_estimate = simulator.estimate_fill_price(
            current_price=Decimal("42000"),
            is_long=True,
        )
        assert buy_estimate > Decimal("42000")
        
        # Short order - should be below current price
        sell_estimate = simulator.estimate_fill_price(
            current_price=Decimal("42000"),
            is_long=False,
        )
        assert sell_estimate < Decimal("42000")
