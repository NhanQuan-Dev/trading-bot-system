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
    fill_conditions_met: Optional[dict] = None  # Debug info for fill decision


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
        market_fill_policy: str = "close",  # close | low | high
        limit_fill_policy: str = "cross",  # touch | cross | cross_volume
    ):
        """Initialize market simulator."""
        self.slippage_model = slippage_model
        self.slippage_percent = Decimal(str(slippage_percent))
        self.commission_model = commission_model
        self.commission_rate = Decimal(str(commission_rate))
        self.use_bid_ask_spread = use_bid_ask_spread
        self.spread_percent = Decimal(str(spread_percent))
        self.market_fill_policy = market_fill_policy
        self.limit_fill_policy = limit_fill_policy
    
    def simulate_long_entry(
        self,
        symbol: str,
        quantity: Decimal,
        current_price: Decimal,
        timestamp: str,
        limit_price: Optional[Decimal] = None,
        candle_low: Optional[Decimal] = None,
        candle_high: Optional[Decimal] = None,
        candle_open: Optional[Decimal] = None,
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
            fill_conditions = {}
            # Use provided candle_open or fallback to current_price (usually Close)
            candle_open = Decimal(str(candle_open)) if candle_open is not None else current_price
            
            # Spec-required: Gap Detection
            # LONG Limit: Reject if open already gapped ABOVE limit (unfavorable)
            if candle_low is not None and candle_open > limit_price and candle_low > limit_price:
                # Price gapped past limit unfavorably (opened above and never came down)
                fill_conditions["gap_check"] = False
                fill_conditions["reason"] = f"Gap: open={candle_open} > limit={limit_price}, low={candle_low}"
                logger.debug(f"LONG Limit NOT filled (gap): {fill_conditions['reason']}")
                return OrderFill(
                    filled_price=Decimal("0"),
                    filled_quantity=Decimal("0"),
                    commission=Decimal("0"),
                    slippage=Decimal("0"),
                    fill_time=timestamp,
                    fill_conditions_met=fill_conditions,
                )
            
            # Check if price touched the limit
            price_touched_limit = candle_low is not None and candle_low <= limit_price
            fill_conditions["price_touched"] = price_touched_limit
            
            if not price_touched_limit:
                fill_conditions["reason"] = f"Price didn't touch: low={candle_low} > limit={limit_price}"
                logger.debug(f"LONG Limit not filled: {fill_conditions['reason']}")
                return OrderFill(
                    filled_price=Decimal("0"),
                    filled_quantity=Decimal("0"),
                    commission=Decimal("0"),
                    slippage=Decimal("0"),
                    fill_time=timestamp,
                    fill_conditions_met=fill_conditions,
                )
            
            # Apply Limit Fill Policy
            if self.limit_fill_policy in ("cross", "cross_volume"):
                # Spec-required: Cross policy
                # In backtesting, if price TOUCHES limit, it technically COULD fill (Maker).
                # To be conservative, "cross" usually means price must move THROUGH.
                # However, for TP/SL detection, "touching" is often the intended behavior
                # if we want to simulate realistic fills. 
                # We'll allow TOUCH (inclusive comparison) to prevent missing obvious TP hits.
                price_crossed = (candle_open >= limit_price and candle_low <= limit_price) or (candle_open <= limit_price)
                fill_conditions["price_crossed"] = price_crossed
                
                if not price_crossed:
                    fill_conditions["reason"] = f"Limit policy={self.limit_fill_policy}: No cross/touch detected (low={candle_low}, open={candle_open})"
                    logger.debug(f"LONG Limit not filled: {fill_conditions['reason']}")
                    return OrderFill(
                        filled_price=Decimal("0"),
                        filled_quantity=Decimal("0"),
                        commission=Decimal("0"),
                        slippage=Decimal("0"),
                        fill_time=timestamp,
                        fill_conditions_met=fill_conditions,
                    )
                
                # If it opened below the limit, we fill at OPEN price (better than limit)
                if candle_open < limit_price:
                    filled_price = candle_open
                    fill_conditions["fill_at_open"] = True
                else:
                    filled_price = limit_price
            else:
                # Touch: fill at limit price
                filled_price = limit_price
            
            # If we reach here: Fill is approved
            fill_conditions["filled"] = True
            fill_conditions["policy"] = self.limit_fill_policy
            slippage = Decimal("0")  # Limit orders have no slippage
            commission = self._calculate_commission(filled_price, quantity)
            logger.debug(f"LONG Limit filled: policy={self.limit_fill_policy}, price={filled_price}")
            return OrderFill(
                filled_price=filled_price,
                filled_quantity=quantity,
                commission=commission,
                slippage=slippage,
                fill_time=timestamp,
                fill_conditions_met=fill_conditions,
            )
        
        # For MARKET orders: Determine base price using Market Fill Policy
        if self.market_fill_policy == "low":
            execution_base_price = candle_low if candle_low is not None else current_price
        elif self.market_fill_policy == "high":
            execution_base_price = candle_high if candle_high is not None else current_price
        else: # Default: close
            execution_base_price = current_price

        # Apply spread to the base price
        if self.use_bid_ask_spread:
            ask_price = execution_base_price * (Decimal("1") + self.spread_percent / Decimal("100"))
        else:
            ask_price = execution_base_price
        
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
        candle_open: Optional[Decimal] = None,
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
            fill_conditions = {}
            # Use provided candle_open or fallback to current_price (usually Close)
            candle_open = Decimal(str(candle_open)) if candle_open is not None else current_price
            
            # Spec-required: Gap Detection
            # SHORT Limit: Reject if open already gapped BELOW limit (unfavorable)
            if candle_high is not None and candle_open < limit_price and candle_high < limit_price:
                # Price gapped past limit unfavorably (opened below and never came up)
                fill_conditions["gap_check"] = False
                fill_conditions["reason"] = f"Gap: open={candle_open} < limit={limit_price}, high={candle_high}"
                logger.debug(f"SHORT Limit NOT filled (gap): {fill_conditions['reason']}")
                return OrderFill(
                    filled_price=Decimal("0"),
                    filled_quantity=Decimal("0"),
                    commission=Decimal("0"),
                    slippage=Decimal("0"),
                    fill_time=timestamp,
                    fill_conditions_met=fill_conditions,
                )
            
            # Check if price touched the limit
            price_touched_limit = candle_high is not None and candle_high >= limit_price
            fill_conditions["price_touched"] = price_touched_limit
            
            if not price_touched_limit:
                fill_conditions["reason"] = f"Price didn't touch: high={candle_high} < limit={limit_price}"
                logger.debug(f"SHORT Limit not filled: {fill_conditions['reason']}")
                return OrderFill(
                    filled_price=Decimal("0"),
                    filled_quantity=Decimal("0"),
                    commission=Decimal("0"),
                    slippage=Decimal("0"),
                    fill_time=timestamp,
                    fill_conditions_met=fill_conditions,
                )
            
            # Apply Limit Fill Policy
            if self.limit_fill_policy in ("cross", "cross_volume"):
                # Cross: Require price to MOVE ABOVE limit (not just touch)
                # Valid Cross cases:
                # 1. Price opened below limit and moved above it during the candle
                # 2. Price opened already above the limit (gap up)
                price_crossed = (candle_open <= limit_price and candle_high >= limit_price) or (candle_open >= limit_price)
                fill_conditions["price_crossed"] = price_crossed
                
                if not price_crossed:
                    fill_conditions["reason"] = f"Limit policy={self.limit_fill_policy}: No cross/touch detected (high={candle_high}, open={candle_open})"
                    logger.debug(f"SHORT Limit not filled: {fill_conditions['reason']}")
                    return OrderFill(
                        filled_price=Decimal("0"),
                        filled_quantity=Decimal("0"),
                        commission=Decimal("0"),
                        slippage=Decimal("0"),
                        fill_time=timestamp,
                        fill_conditions_met=fill_conditions,
                    )
                
                # If it opened above the limit, we fill at OPEN price (better than limit for short)
                if candle_open > limit_price:
                    filled_price = candle_open
                    fill_conditions["fill_at_open"] = True
                else:
                    filled_price = limit_price
            else:
                # Touch: fill at limit price
                filled_price = limit_price
            
            # If we reach here: Fill is approved
            fill_conditions["filled"] = True
            fill_conditions["policy"] = self.limit_fill_policy
            slippage = Decimal("0")  # Limit orders have no slippage
            commission = self._calculate_commission(filled_price, quantity)
            logger.debug(f"SHORT Limit filled: policy={self.limit_fill_policy}, price={filled_price}")
            return OrderFill(
                filled_price=filled_price,
                filled_quantity=quantity,
                commission=commission,
                slippage=slippage,
                fill_time=timestamp,
                fill_conditions_met=fill_conditions,
            )
        
        # For MARKET orders: Determine base price using Market Fill Policy
        if self.market_fill_policy == "low":
            execution_base_price = candle_low if candle_low is not None else current_price
        elif self.market_fill_policy == "high":
            execution_base_price = candle_high if candle_high is not None else current_price
        else: # Default: close
            execution_base_price = current_price

        # Apply spread to the base price
        if self.use_bid_ask_spread:
            bid_price = execution_base_price * (Decimal("1") - self.spread_percent / Decimal("100"))
        else:
            bid_price = execution_base_price
        
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
