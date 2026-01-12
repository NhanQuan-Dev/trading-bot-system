"""Market simulator for realistic backtest execution."""

import logging
import random
from decimal import Decimal
from typing import Optional
from dataclasses import dataclass

from ...domain.backtesting import SlippageModel, CommissionModel

logger = logging.getLogger(__name__)


@dataclass
class OrderFill:
    """Result of order execution."""
    filled_price: Decimal
    filled_quantity: Decimal
    commission: Decimal
    slippage: Decimal
    fill_time: str


class MarketSimulator:
    """Simulate realistic market conditions for backtesting."""
    
    def __init__(
        self,
        slippage_model: SlippageModel = SlippageModel.FIXED,
        slippage_percent: Decimal = Decimal("0.001"),
        commission_model: CommissionModel = CommissionModel.FIXED_RATE,
        commission_rate: Decimal = Decimal("0.001"),
        use_bid_ask_spread: bool = False,
        spread_percent: Decimal = Decimal("0.05"),
    ):
        """Initialize market simulator."""
        self.slippage_model = slippage_model
        self.slippage_percent = slippage_percent
        self.commission_model = commission_model
        self.commission_rate = commission_rate
        self.use_bid_ask_spread = use_bid_ask_spread
        self.spread_percent = spread_percent
    
    def simulate_long_entry(
        self,
        symbol: str,
        quantity: Decimal,
        current_price: Decimal,
        timestamp: str,
        limit_price: Optional[Decimal] = None,
        candle_low: Optional[Decimal] = None,
        candle_high: Optional[Decimal] = None,
    ) -> OrderFill:
        """Simulate LONG position entry (buying).
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            current_price: Current/Close price
            timestamp: Order timestamp
            limit_price: Optional limit price for limit orders
            candle_low: Low price of candle (for limit order fill detection)
            candle_high: High price of candle (for limit order fill detection)
        """
        # Ensure Decimals
        current_price = Decimal(str(current_price))
        if limit_price is not None: limit_price = Decimal(str(limit_price))
        if candle_low is not None: candle_low = Decimal(str(candle_low))
        if candle_high is not None: candle_high = Decimal(str(candle_high))
        quantity = Decimal(str(quantity))
        
        # For LIMIT orders: Check if price reached the limit during candle
        if limit_price:
            # LONG Limit: Fill if price went DOWN to limit (Low <= limit_price)
            if candle_low is not None and candle_low <= limit_price:
                # Limit order filled at limit price
                filled_price = limit_price
                slippage = Decimal("0")  # Limit orders have no slippage
                commission = self._calculate_commission(filled_price, quantity)
                logger.debug(f"LONG Limit filled: low={candle_low} <= limit={limit_price}")
                return OrderFill(
                    filled_price=filled_price,
                    filled_quantity=quantity,
                    commission=commission,
                    slippage=slippage,
                    fill_time=timestamp,
                )
            else:
                # Limit not reached
                logger.debug(f"LONG Limit not filled: low={candle_low} > limit={limit_price}")
                return OrderFill(
                    filled_price=Decimal("0"),
                    filled_quantity=Decimal("0"),
                    commission=Decimal("0"),
                    slippage=Decimal("0"),
                    fill_time=timestamp,
                )
        
        # For MARKET orders: Use current price with spread and slippage
        if self.use_bid_ask_spread:
            ask_price = current_price * (Decimal("1") + self.spread_percent / Decimal("100"))
        else:
            ask_price = current_price
        
        slippage = self._calculate_slippage(ask_price, is_long=True)
        filled_price = ask_price + slippage
        commission = self._calculate_commission(filled_price, quantity)
        
        return OrderFill(
            filled_price=filled_price,
            filled_quantity=quantity,
            commission=commission,
            slippage=slippage,
            fill_time=timestamp,
        )
    
    def simulate_short_entry(
        self,
        symbol: str,
        quantity: Decimal,
        current_price: Decimal,
        timestamp: str,
        limit_price: Optional[Decimal] = None,
        candle_low: Optional[Decimal] = None,
        candle_high: Optional[Decimal] = None,
    ) -> OrderFill:
        """Simulate SHORT position entry (selling).
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            current_price: Current/Close price
            timestamp: Order timestamp
            limit_price: Optional limit price for limit orders
            candle_low: Low price of candle (for limit order fill detection)
            candle_high: High price of candle (for limit order fill detection)
        """
        # Ensure Decimals
        current_price = Decimal(str(current_price))
        if limit_price is not None: limit_price = Decimal(str(limit_price))
        if candle_low is not None: candle_low = Decimal(str(candle_low))
        if candle_high is not None: candle_high = Decimal(str(candle_high))
        quantity = Decimal(str(quantity))
        
        # For LIMIT orders: Check if price reached the limit during candle
        if limit_price:
            # SHORT Limit: Fill if price went UP to limit (High >= limit_price)
            if candle_high is not None and candle_high >= limit_price:
                # Limit order filled at limit price
                filled_price = limit_price
                slippage = Decimal("0")  # Limit orders have no slippage
                commission = self._calculate_commission(filled_price, quantity)
                logger.debug(f"SHORT Limit filled: high={candle_high} >= limit={limit_price}")
                return OrderFill(
                    filled_price=filled_price,
                    filled_quantity=quantity,
                    commission=commission,
                    slippage=slippage,
                    fill_time=timestamp,
                )
            else:
                # Limit not reached
                logger.debug(f"SHORT Limit not filled: high={candle_high} < limit={limit_price}")
                return OrderFill(
                    filled_price=Decimal("0"),
                    filled_quantity=Decimal("0"),
                    commission=Decimal("0"),
                    slippage=Decimal("0"),
                    fill_time=timestamp,
                )
        
        # For MARKET orders: Use current price with spread and slippage
        if self.use_bid_ask_spread:
            bid_price = current_price * (Decimal("1") - self.spread_percent / Decimal("100"))
        else:
            bid_price = current_price
        
        slippage = self._calculate_slippage(bid_price, is_long=False)
        filled_price = bid_price - slippage
        commission = self._calculate_commission(filled_price, quantity)
        
        return OrderFill(
            filled_price=filled_price,
            filled_quantity=quantity,
            commission=commission,
            slippage=slippage,
            fill_time=timestamp,
        )
    
    def _calculate_slippage(self, price: Decimal, is_long: bool) -> Decimal:
        """Calculate slippage based on configured model.
        
        Args:
            price: Current price
            is_long: True for LONG entry, False for SHORT entry
        """
        
        if self.slippage_model == SlippageModel.NONE:
            return Decimal("0")
        
        elif self.slippage_model == SlippageModel.FIXED:
            return self.slippage_percent  # Used as fixed amount
        
        if self.slippage_model == SlippageModel.PERCENTAGE:
            # Slippage is always a POSITIVE magnitude of price movement against the trader
            # simulate_long_entry adds this (Price + Slippage = Higher Buy Price)
            # simulate_short_entry subtracts this (Price - Slippage = Lower Sell Price)
            slippage_amount = price * (self.slippage_percent / Decimal("100"))
            return abs(slippage_amount)
        
        elif self.slippage_model == SlippageModel.VOLUME_BASED:
            # Simplistic volume based
            base_slippage = price * (self.slippage_percent / Decimal("100"))
            volume_factor = Decimal(str(random.uniform(0.5, 1.5)))
            return abs(base_slippage * volume_factor)
        
        elif self.slippage_model == SlippageModel.RANDOM:
            # Random slippage
            random_factor = Decimal(str(random.uniform(0, float(self.slippage_percent))))
            return abs(price * (random_factor / Decimal("100")))
        
        return Decimal("0")
    
    def _calculate_commission(self, price: Decimal, quantity: Decimal) -> Decimal:
        """Calculate commission based on configured model."""
        
        if self.commission_model == CommissionModel.NONE:
            return Decimal("0")
        
        elif self.commission_model == "fixed":
            return self.commission_rate  # Used as fixed fee
        
        elif self.commission_model == CommissionModel.FIXED_RATE:
            notional = price * quantity
            return notional * (self.commission_rate / Decimal("100"))
        
        elif self.commission_model == CommissionModel.TIERED:
            # Simplified tiered commission
            notional = price * quantity
            if notional < Decimal("1000"):
                rate = self.commission_rate * Decimal("1.5")
            elif notional < Decimal("10000"):
                rate = self.commission_rate
            else:
                rate = self.commission_rate * Decimal("0.75")
            
            return notional * (rate / Decimal("100"))
        
        return Decimal("0")
    
    def can_fill_order(
        self,
        order_price: Decimal,
        current_price: Decimal,
        is_long: bool,
        is_limit: bool = False,
    ) -> bool:
        """Check if order can be filled at current price.
        
        Args:
            is_long: True for LONG position, False for SHORT position
        """
        
        if not is_limit:
            return True  # Market orders always fill
        
        if is_long:
            return current_price <= order_price
        else:
            return current_price >= order_price
    
    def estimate_fill_price(
        self,
        current_price: Decimal,
        is_long: bool,
    ) -> Decimal:
        """Estimate fill price including spread and slippage.
        
        Args:
            is_long: True for LONG position, False for SHORT position
        """
        
        # Apply spread
        if self.use_bid_ask_spread:
            if is_long:
                price = current_price * (Decimal("1") + self.spread_percent / Decimal("100"))
            else:
                price = current_price * (Decimal("1") - self.spread_percent / Decimal("100"))
        else:
            price = current_price
        
        # Add slippage estimate
        slippage = self._calculate_slippage(price, is_long)
        
        if is_long:
            return price + slippage
        else:
            return price - abs(slippage)
