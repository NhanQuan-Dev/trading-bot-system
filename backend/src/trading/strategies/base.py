"""
Strategy Abstract Base Class.

This module defines the interface that all trading strategies must implement.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from decimal import Decimal
import logging

from ..infrastructure.exchange.exchange_gateway import ExchangeGateway

logger = logging.getLogger(__name__)


class StrategyBase(ABC):
    """
    Abstract base class for trading strategies.
    
    All strategies must inherit from this class and implement:
    - name: Strategy display name
    - on_tick: Main logic called on market updates
    """
    
    def __init__(self, exchange: ExchangeGateway, config: Dict[str, Any], on_order=None):
        """
        Initialize strategy.
        
        Args:
            exchange: The exchange gateway instance
            config: Strategy configuration parameters
            on_order: Async callback function(order_dict) -> None
        """
        self.exchange = exchange
        self.config = config
        self.position = None
        self.orders = []
        self.on_order = on_order

    @property
    @abstractmethod
    def name(self) -> str:
        """Display name of the strategy"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """User-friendly description of strategy logic"""
        pass

    @abstractmethod
    async def on_tick(self, market_data: Any):
        """
        Called on every tick or candle update.
        
        Args:
            market_data: Ticker or candle data
        """
        pass
        
    async def buy(self, symbol: str, quantity: Decimal, price: Optional[Decimal] = None, **kwargs) -> Dict[str, Any]:
        """
        Execute a buy order.
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            price: Limit price (optional, if None triggers MARKET order)
            **kwargs: Extra parameters
            
        Returns:
            Order response
        """
        order_type = "LIMIT" if price else "MARKET"
        logger.info(f"[{self.name}] Placing BUY {order_type} on {symbol}: {quantity} @ {price or 'Market'}")
        
        response = await self.exchange.create_order(
            symbol=symbol,
            side="BUY",
            type=order_type,
            quantity=quantity,
            price=price,
            **kwargs
        )
        
        if self.on_order:
            try:
                # Add metadata to response for the callback
                await self.on_order({
                    **response,
                    "symbol": symbol,
                    "side": "BUY",
                    "type": order_type,
                    "quantity": quantity,
                    "price": price,
                    "status": response.get("status", "NEW")
                })
            except Exception as e:
                logger.error(f"Error in on_order callback: {e}")
                
        return response

    async def sell(self, symbol: str, quantity: Decimal, price: Optional[Decimal] = None, **kwargs) -> Dict[str, Any]:
        """
        Execute a sell order.
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            price: Limit price (optional, if None triggers MARKET order)
            **kwargs: Extra parameters
            
        Returns:
            Order response
        """
        order_type = "LIMIT" if price else "MARKET"
        logger.info(f"[{self.name}] Placing SELL {order_type} on {symbol}: {quantity} @ {price or 'Market'}")
        
        response = await self.exchange.create_order(
            symbol=symbol,
            side="SELL",
            type=order_type,
            quantity=quantity,
            price=price,
            **kwargs
        )

        if self.on_order:
            try:
                await self.on_order({
                    **response,
                    "symbol": symbol,
                    "side": "SELL",
                    "type": order_type,
                    "quantity": quantity,
                    "price": price,
                    "status": response.get("status", "NEW")
                })
            except Exception as e:
                logger.error(f"Error in on_order callback: {e}")

        return response
        
    async def cancel_all(self, symbol: str) -> None:
        """Cancel all open orders for symbol."""
        open_orders = await self.exchange.get_open_orders(symbol)
        for order in open_orders:
            await self.exchange.cancel_order(symbol, order['orderId'])
