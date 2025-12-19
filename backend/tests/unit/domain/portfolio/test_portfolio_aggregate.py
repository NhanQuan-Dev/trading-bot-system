"""Unit tests for PortfolioAggregate"""
import pytest
from decimal import Decimal
from datetime import datetime

from src.trading.domain.portfolio.aggregates.portfolio_aggregate import PortfolioAggregate
from src.trading.domain.portfolio.value_objects.asset_balance import AssetBalance
from src.trading.domain.portfolio.entities.asset_position import PositionSide
from src.trading.shared.types.symbol import Symbol
from src.trading.shared.errors.domain_errors import InsufficientBalanceError
from src.trading.domain.portfolio.events import (
    BalanceUpdatedEvent,
    PositionOpenedEvent,
    PositionClosedEvent
)


class TestPortfolioAggregate:
    """Test suite for PortfolioAggregate"""
    
    def test_create_portfolio_with_account_id(self):
        """Test: Can create portfolio with account ID"""
        portfolio = PortfolioAggregate("test_account")
        
        assert portfolio.account_id == "test_account"
        assert len(portfolio.balances) == 0
        assert len(portfolio.positions) == 0
    
    def test_reject_empty_account_id(self):
        """Test: Raises error when account_id is empty"""
        with pytest.raises(ValueError, match="account_id cannot be empty"):
            PortfolioAggregate("")
    
    def test_update_balance_successfully(self):
        """Test: Can update balance"""
        portfolio = PortfolioAggregate("test_account")
        
        portfolio.update_balance("USDT", Decimal("1000"), Decimal("200"))
        
        balances = portfolio.balances
        assert "USDT" in balances
        assert balances["USDT"].free == Decimal("1000")
        assert balances["USDT"].locked == Decimal("200")
    
    def test_update_balance_emits_event(self):
        """Test: Updating balance emits BalanceUpdatedEvent"""
        portfolio = PortfolioAggregate("test_account")
        
        portfolio.update_balance("USDT", Decimal("1000"), Decimal("0"))
        
        events = portfolio.domain_events
        assert len(events) == 1
        assert isinstance(events[0], BalanceUpdatedEvent)
        assert events[0].account_id == "test_account"
        assert events[0].asset == "USDT"
        assert events[0].free == Decimal("1000")
    
    def test_open_position_successfully(self):
        """Test: Can open position with sufficient balance"""
        portfolio = PortfolioAggregate("test_account")
        portfolio.update_balance("USDT", Decimal("1000"), Decimal("0"))
        
        symbol = Symbol("BTC", "USDT")
        position_id = portfolio.open_position(
            symbol=symbol,
            quantity=Decimal("0.1"),
            side=PositionSide.LONG,
            entry_price=Decimal("50000"),
            leverage=10
        )
        
        assert position_id is not None
        assert portfolio.has_position("BTCUSDT")
        
        position = portfolio.get_position("BTCUSDT")
        assert position.quantity == Decimal("0.1")
        assert position.entry_price == Decimal("50000")
        assert position.leverage == 10
    
    def test_open_position_locks_margin(self):
        """Test: Opening position locks required margin"""
        portfolio = PortfolioAggregate("test_account")
        portfolio.update_balance("USDT", Decimal("1000"), Decimal("0"))
        
        symbol = Symbol("BTC", "USDT")
        portfolio.open_position(
            symbol=symbol,
            quantity=Decimal("0.1"),
            side=PositionSide.LONG,
            entry_price=Decimal("50000"),
            leverage=10
        )
        
        # Margin = (0.1 * 50000) / 10 = 500
        balances = portfolio.balances
        assert balances["USDT"].free == Decimal("500")
        assert balances["USDT"].locked == Decimal("500")
    
    def test_open_position_emits_event(self):
        """Test: Opening position emits PositionOpenedEvent"""
        portfolio = PortfolioAggregate("test_account")
        portfolio.update_balance("USDT", Decimal("1000"), Decimal("0"))
        portfolio.clear_domain_events()  # Clear balance event
        
        symbol = Symbol("BTC", "USDT")
        portfolio.open_position(
            symbol=symbol,
            quantity=Decimal("0.1"),
            side=PositionSide.LONG,
            entry_price=Decimal("50000"),
            leverage=10
        )
        
        events = portfolio.domain_events
        assert any(isinstance(e, PositionOpenedEvent) for e in events)
        
        position_event = next(e for e in events if isinstance(e, PositionOpenedEvent))
        assert position_event.symbol == "BTCUSDT"
        assert position_event.quantity == Decimal("0.1")
    
    def test_open_position_fails_with_insufficient_balance(self):
        """Test: Cannot open position without sufficient balance"""
        portfolio = PortfolioAggregate("test_account")
        portfolio.update_balance("USDT", Decimal("100"), Decimal("0"))
        
        symbol = Symbol("BTC", "USDT")
        
        with pytest.raises(InsufficientBalanceError):
            portfolio.open_position(
                symbol=symbol,
                quantity=Decimal("1.0"),  # Needs 5000 USDT margin
                side=PositionSide.LONG,
                entry_price=Decimal("50000"),
                leverage=10
            )
    
    def test_open_position_fails_when_position_exists(self):
        """Test: Cannot open duplicate position for same symbol"""
        portfolio = PortfolioAggregate("test_account")
        portfolio.update_balance("USDT", Decimal("2000"), Decimal("0"))
        
        symbol = Symbol("BTC", "USDT")
        portfolio.open_position(
            symbol=symbol,
            quantity=Decimal("0.1"),
            side=PositionSide.LONG,
            entry_price=Decimal("50000"),
            leverage=10
        )
        
        with pytest.raises(ValueError, match="Position already exists"):
            portfolio.open_position(
                symbol=symbol,
                quantity=Decimal("0.1"),
                side=PositionSide.LONG,
                entry_price=Decimal("50000"),
                leverage=10
            )
    
    def test_close_position_successfully(self):
        """Test: Can close position"""
        portfolio = PortfolioAggregate("test_account")
        portfolio.update_balance("USDT", Decimal("1000"), Decimal("0"))
        
        symbol = Symbol("BTC", "USDT")
        portfolio.open_position(
            symbol=symbol,
            quantity=Decimal("0.1"),
            side=PositionSide.LONG,
            entry_price=Decimal("50000"),
            leverage=10
        )
        
        realized_pnl = portfolio.close_position("BTCUSDT", Decimal("51000"))
        
        assert not portfolio.has_position("BTCUSDT")
        assert realized_pnl == Decimal("100")  # (51000 - 50000) * 0.1
    
    def test_close_position_releases_margin(self):
        """Test: Closing position releases margin and adds P&L"""
        portfolio = PortfolioAggregate("test_account")
        portfolio.update_balance("USDT", Decimal("1000"), Decimal("0"))
        
        symbol = Symbol("BTC", "USDT")
        portfolio.open_position(
            symbol=symbol,
            quantity=Decimal("0.1"),
            side=PositionSide.LONG,
            entry_price=Decimal("50000"),
            leverage=10
        )
        
        portfolio.close_position("BTCUSDT", Decimal("51000"))
        
        balances = portfolio.balances
        # Should have 1000 + 100 (profit) = 1100 free
        assert balances["USDT"].free == Decimal("1100")
        assert balances["USDT"].locked == Decimal("0")
    
    def test_close_position_emits_event(self):
        """Test: Closing position emits PositionClosedEvent"""
        portfolio = PortfolioAggregate("test_account")
        portfolio.update_balance("USDT", Decimal("1000"), Decimal("0"))
        
        symbol = Symbol("BTC", "USDT")
        portfolio.open_position(
            symbol=symbol,
            quantity=Decimal("0.1"),
            side=PositionSide.LONG,
            entry_price=Decimal("50000"),
            leverage=10
        )
        portfolio.clear_domain_events()  # Clear previous events
        
        portfolio.close_position("BTCUSDT", Decimal("51000"))
        
        events = portfolio.domain_events
        assert any(isinstance(e, PositionClosedEvent) for e in events)
        
        close_event = next(e for e in events if isinstance(e, PositionClosedEvent))
        assert close_event.symbol == "BTCUSDT"
        assert close_event.realized_pnl == Decimal("100")
    
    def test_close_position_fails_when_not_exists(self):
        """Test: Cannot close non-existent position"""
        portfolio = PortfolioAggregate("test_account")
        
        with pytest.raises(ValueError, match="No position found"):
            portfolio.close_position("BTCUSDT", Decimal("50000"))
    
    def test_calculate_total_equity(self):
        """Test: Can calculate total equity"""
        portfolio = PortfolioAggregate("test_account")
        portfolio.update_balance("USDT", Decimal("1000"), Decimal("200"))
        
        equity = portfolio.calculate_total_equity()
        
        assert equity.amount == Decimal("1200")
        assert equity.currency == "USDT"
    
    def test_calculate_total_equity_with_positions(self):
        """Test: Equity includes unrealized P&L from positions"""
        portfolio = PortfolioAggregate("test_account")
        portfolio.update_balance("USDT", Decimal("1000"), Decimal("0"))
        
        symbol = Symbol("BTC", "USDT")
        portfolio.open_position(
            symbol=symbol,
            quantity=Decimal("0.1"),
            side=PositionSide.LONG,
            entry_price=Decimal("50000"),
            leverage=10
        )
        
        # Update P&L with market price
        market_prices = {"BTCUSDT": Decimal("51000")}
        equity = portfolio.calculate_total_equity(market_prices)
        
        # 1000 balance + 100 unrealized P&L = 1100
        assert equity.amount == Decimal("1100")
    
    def test_get_available_balance(self):
        """Test: Can get available balance"""
        portfolio = PortfolioAggregate("test_account")
        portfolio.update_balance("USDT", Decimal("1000"), Decimal("200"))
        
        available = portfolio.get_available_balance("USDT")
        
        assert available == Decimal("1000")
    
    def test_get_available_balance_returns_zero_if_not_exists(self):
        """Test: Returns zero for non-existent asset"""
        portfolio = PortfolioAggregate("test_account")
        
        available = portfolio.get_available_balance("BTC")
        
        assert available == Decimal("0")
    
    def test_get_total_margin_used(self):
        """Test: Can calculate total margin used"""
        portfolio = PortfolioAggregate("test_account")
        portfolio.update_balance("USDT", Decimal("2000"), Decimal("0"))
        
        # Open two positions
        symbol1 = Symbol("BTC", "USDT")
        portfolio.open_position(
            symbol=symbol1,
            quantity=Decimal("0.1"),
            side=PositionSide.LONG,
            entry_price=Decimal("50000"),
            leverage=10
        )
        
        symbol2 = Symbol("ETH", "USDT")
        portfolio.open_position(
            symbol=symbol2,
            quantity=Decimal("1.0"),
            side=PositionSide.LONG,
            entry_price=Decimal("3000"),
            leverage=5
        )
        
        total_margin = portfolio.get_total_margin_used()
        
        # BTC: 500, ETH: 600, Total: 1100
        assert total_margin == Decimal("1100")
