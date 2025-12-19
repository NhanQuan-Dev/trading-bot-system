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
    
    def simulate_buy_order(
        self,
        symbol: str,
        quantity: Decimal,
        current_price: Decimal,
        timestamp: str,
        limit_price: Optional[Decimal] = None,
    ) -> OrderFill:
        """Simulate market buy order execution."""
        
        # Apply bid-ask spread
        if self.use_bid_ask_spread:
            ask_price = current_price * (Decimal("1") + self.spread_percent / Decimal("100"))
        else:
            ask_price = current_price
        
        # Apply slippage
        slippage = self._calculate_slippage(ask_price, is_buy=True)
        filled_price = ask_price + slippage
        
        # Check limit price
        if limit_price and filled_price > limit_price:
            logger.warning(f"Buy order not filled: price {filled_price} > limit {limit_price}")
            return OrderFill(
                filled_price=Decimal("0"),
                filled_quantity=Decimal("0"),
                commission=Decimal("0"),
                slippage=Decimal("0"),
                fill_time=timestamp,
            )
        
        # Calculate commission
        commission = self._calculate_commission(filled_price, quantity)
        
        return OrderFill(
            filled_price=filled_price,
            filled_quantity=quantity,
            commission=commission,
            slippage=slippage,
            fill_time=timestamp,
        )
    
    def simulate_sell_order(
        self,
        symbol: str,
        quantity: Decimal,
        current_price: Decimal,
        timestamp: str,
        limit_price: Optional[Decimal] = None,
    ) -> OrderFill:
        """Simulate market sell order execution."""
        
        # Apply bid-ask spread
        if self.use_bid_ask_spread:
            bid_price = current_price * (Decimal("1") - self.spread_percent / Decimal("100"))
        else:
            bid_price = current_price
        
        # Apply slippage
        slippage = self._calculate_slippage(bid_price, is_buy=False)
        filled_price = bid_price - slippage
        
        # Check limit price
        if limit_price and filled_price < limit_price:
            logger.warning(f"Sell order not filled: price {filled_price} < limit {limit_price}")
            return OrderFill(
                filled_price=Decimal("0"),
                filled_quantity=Decimal("0"),
                commission=Decimal("0"),
                slippage=Decimal("0"),
                fill_time=timestamp,
            )
        
        # Calculate commission
        commission = self._calculate_commission(filled_price, quantity)
        
        return OrderFill(
            filled_price=filled_price,
            filled_quantity=quantity,
            commission=commission,
            slippage=slippage,
            fill_time=timestamp,
        )
    
    def _calculate_slippage(self, price: Decimal, is_buy: bool) -> Decimal:
        """Calculate slippage based on configured model."""
        
        if self.slippage_model == SlippageModel.NONE:
            return Decimal("0")
        
        elif self.slippage_model == SlippageModel.FIXED:
            return self.slippage_percent  # Used as fixed amount
        
        elif self.slippage_model == SlippageModel.PERCENTAGE:
            slippage_amount = price * (self.slippage_percent / Decimal("100"))
            return slippage_amount if is_buy else -slippage_amount
        
        elif self.slippage_model == SlippageModel.VOLUME_BASED:
            # Simplified volume-based slippage
            # In real implementation, would factor in actual volume
            base_slippage = price * (self.slippage_percent / Decimal("100"))
            volume_factor = Decimal(str(random.uniform(0.5, 1.5)))
            return base_slippage * volume_factor
        
        elif self.slippage_model == SlippageModel.RANDOM:
            # Random slippage within configured range
            random_factor = Decimal(str(random.uniform(0, float(self.slippage_percent))))
            return price * (random_factor / Decimal("100"))
        
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
        is_buy: bool,
        is_limit: bool = False,
    ) -> bool:
        """Check if order can be filled at current price."""
        
        if not is_limit:
            return True  # Market orders always fill
        
        if is_buy:
            return current_price <= order_price
        else:
            return current_price >= order_price
    
    def estimate_fill_price(
        self,
        current_price: Decimal,
        is_buy: bool,
    ) -> Decimal:
        """Estimate fill price including spread and slippage."""
        
        # Apply spread
        if self.use_bid_ask_spread:
            if is_buy:
                price = current_price * (Decimal("1") + self.spread_percent / Decimal("100"))
            else:
                price = current_price * (Decimal("1") - self.spread_percent / Decimal("100"))
        else:
            price = current_price
        
        # Add slippage estimate
        slippage = self._calculate_slippage(price, is_buy)
        
        if is_buy:
            return price + slippage
        else:
            return price - abs(slippage)
