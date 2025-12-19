"""Order domain models for trading execution."""
from dataclasses import dataclass
from datetime import datetime as dt, timezone as dt_timezone
from enum import Enum
from typing import Optional, Dict, Any
from decimal import Decimal
import uuid


class OrderSide(str, Enum):
    """Order side enumeration."""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order type enumeration."""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_MARKET = "STOP_MARKET"
    TAKE_PROFIT = "TAKE_PROFIT"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"
    TRAILING_STOP_MARKET = "TRAILING_STOP_MARKET"


class TimeInForce(str, Enum):
    """Time in force enumeration."""
    GTC = "GTC"  # Good Till Cancel
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill
    GTX = "GTX"  # Good Till Cross


class OrderStatus(str, Enum):
    """Order status enumeration."""
    PENDING = "PENDING"          # Created but not sent to exchange
    NEW = "NEW"                  # Accepted by exchange
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class PositionSide(str, Enum):
    """Position side for hedge mode."""
    BOTH = "BOTH"    # One-way position mode
    LONG = "LONG"    # Hedge mode long side
    SHORT = "SHORT"  # Hedge mode short side


class WorkingType(str, Enum):
    """Working type for stop orders."""
    MARK_PRICE = "MARK_PRICE"
    CONTRACT_PRICE = "CONTRACT_PRICE"


@dataclass(frozen=True)
class OrderPrice:
    """Order price value object."""
    value: Decimal
    
    def __post_init__(self):
        if self.value <= 0:
            raise ValueError("Order price must be positive")
    
    @property
    def formatted(self) -> str:
        """Format price for exchange API."""
        return f"{self.value:.8f}".rstrip('0').rstrip('.')


@dataclass(frozen=True)
class OrderQuantity:
    """Order quantity value object."""
    value: Decimal
    
    def __post_init__(self):
        if self.value <= 0:
            raise ValueError("Order quantity must be positive")
    
    @property
    def formatted(self) -> str:
        """Format quantity for exchange API."""
        return f"{self.value:.8f}".rstrip('0').rstrip('.')


@dataclass(frozen=True)
class OrderExecution:
    """Order execution details value object."""
    executed_quantity: Decimal = Decimal("0")
    executed_quote: Decimal = Decimal("0") 
    avg_price: Optional[Decimal] = None
    commission: Decimal = Decimal("0")
    commission_asset: str = "USDT"
    
    @property
    def remaining_quantity(self) -> Decimal:
        """Calculate remaining quantity to be executed."""
        # Note: This requires the original quantity which should be passed in
        # This is a simplified version
        return Decimal("0")  # Will be calculated in the Order entity
    
    @property
    def fill_percentage(self) -> float:
        """Calculate fill percentage."""
        # This also requires original quantity
        return 0.0  # Will be calculated in the Order entity


@dataclass
class Order:
    """Order entity - represents a trading order."""
    # Required fields (no defaults)
    id: uuid.UUID
    user_id: uuid.UUID
    exchange_connection_id: uuid.UUID
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: OrderQuantity
    status: OrderStatus
    created_at: dt
    updated_at: dt
    
    # Optional fields (with defaults)
    bot_id: Optional[uuid.UUID] = None
    price: Optional[OrderPrice] = None
    stop_price: Optional[OrderPrice] = None
    callback_rate: Optional[Decimal] = None  # For trailing stop
    
    # Futures specific
    position_side: PositionSide = PositionSide.BOTH
    time_in_force: TimeInForce = TimeInForce.GTC
    reduce_only: bool = False
    close_position: bool = False
    
    # Advanced options
    working_type: WorkingType = WorkingType.CONTRACT_PRICE
    price_protect: bool = False
    
    # Status and execution
    exchange_order_id: Optional[str] = None
    client_order_id: Optional[str] = None
    execution: OrderExecution = None
    
    # Risk management
    leverage: int = 1
    margin_type: str = "ISOLATED"  # ISOLATED or CROSS
    
    # Metadata
    error_message: Optional[str] = None
    meta_data: Dict[str, Any] = None
    
    # Timestamps
    submitted_at: Optional[dt] = None
    filled_at: Optional[dt] = None
    cancelled_at: Optional[dt] = None
    
    def __post_init__(self):
        if self.execution is None:
            self.execution = OrderExecution()
        if self.meta_data is None:
            self.meta_data = {}
    
    @classmethod
    def create_market_order(
        cls,
        user_id: uuid.UUID,
        exchange_connection_id: uuid.UUID,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        bot_id: Optional[uuid.UUID] = None,
        position_side: PositionSide = PositionSide.BOTH,
        reduce_only: bool = False,
        leverage: int = 1,
    ) -> "Order":
        """Create a market order."""
        now = dt.now(dt_timezone.utc)
        return cls(
            id=uuid.uuid4(),
            user_id=user_id,
            bot_id=bot_id,
            exchange_connection_id=exchange_connection_id,
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=OrderQuantity(quantity),
            position_side=position_side,
            reduce_only=reduce_only,
            leverage=leverage,
            status=OrderStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
    
    @classmethod
    def create_limit_order(
        cls,
        user_id: uuid.UUID,
        exchange_connection_id: uuid.UUID,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        price: Decimal,
        bot_id: Optional[uuid.UUID] = None,
        position_side: PositionSide = PositionSide.BOTH,
        time_in_force: TimeInForce = TimeInForce.GTC,
        reduce_only: bool = False,
        leverage: int = 1,
    ) -> "Order":
        """Create a limit order."""
        now = dt.now(dt_timezone.utc)
        return cls(
            id=uuid.uuid4(),
            user_id=user_id,
            bot_id=bot_id,
            exchange_connection_id=exchange_connection_id,
            symbol=symbol,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=OrderQuantity(quantity),
            price=OrderPrice(price),
            position_side=position_side,
            time_in_force=time_in_force,
            reduce_only=reduce_only,
            leverage=leverage,
            status=OrderStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
    
    @classmethod
    def create_stop_market_order(
        cls,
        user_id: uuid.UUID,
        exchange_connection_id: uuid.UUID,
        symbol: str,
        side: OrderSide,
        quantity: Decimal,
        stop_price: Decimal,
        bot_id: Optional[uuid.UUID] = None,
        position_side: PositionSide = PositionSide.BOTH,
        working_type: WorkingType = WorkingType.CONTRACT_PRICE,
        reduce_only: bool = False,
        leverage: int = 1,
    ) -> "Order":
        """Create a stop market order."""
        now = dt.now(dt_timezone.utc)
        return cls(
            id=uuid.uuid4(),
            user_id=user_id,
            bot_id=bot_id,
            exchange_connection_id=exchange_connection_id,
            symbol=symbol,
            side=side,
            order_type=OrderType.STOP_MARKET,
            quantity=OrderQuantity(quantity),
            stop_price=OrderPrice(stop_price),
            position_side=position_side,
            working_type=working_type,
            reduce_only=reduce_only,
            leverage=leverage,
            status=OrderStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
    
    def submit(self, exchange_order_id: str, client_order_id: Optional[str] = None) -> None:
        """Mark order as submitted to exchange."""
        self.status = OrderStatus.NEW
        self.exchange_order_id = exchange_order_id
        self.client_order_id = client_order_id
        self.submitted_at = dt.now(dt_timezone.utc)
        self.updated_at = dt.now(dt_timezone.utc)
    
    def fill(
        self, 
        executed_quantity: Decimal, 
        executed_price: Decimal,
        commission: Decimal = Decimal("0"),
        commission_asset: str = "USDT"
    ) -> None:
        """Update order with fill execution."""
        total_executed = self.execution.executed_quantity + executed_quantity
        total_quote = self.execution.executed_quote + (executed_quantity * executed_price)
        
        # Calculate new average price
        if total_executed > 0:
            avg_price = total_quote / total_executed
        else:
            avg_price = None
        
        self.execution = OrderExecution(
            executed_quantity=total_executed,
            executed_quote=total_quote,
            avg_price=avg_price,
            commission=self.execution.commission + commission,
            commission_asset=commission_asset,
        )
        
        # Update status
        if total_executed >= self.quantity.value:
            self.status = OrderStatus.FILLED
            self.filled_at = dt.now(dt_timezone.utc)
        else:
            self.status = OrderStatus.PARTIALLY_FILLED
        
        self.updated_at = dt.now(dt_timezone.utc)
    
    def cancel(self, reason: Optional[str] = None) -> None:
        """Cancel the order."""
        if self.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
            raise ValueError(f"Cannot cancel order in {self.status} status")
        
        self.status = OrderStatus.CANCELLED
        self.cancelled_at = dt.now(dt_timezone.utc)
        self.updated_at = dt.now(dt_timezone.utc)
        
        if reason:
            self.error_message = reason
    
    def reject(self, reason: str) -> None:
        """Reject the order."""
        self.status = OrderStatus.REJECTED
        self.error_message = reason
        self.updated_at = dt.now(dt_timezone.utc)
    
    def is_active(self) -> bool:
        """Check if order is active (can be cancelled)."""
        return self.status in [OrderStatus.PENDING, OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED]
    
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.status == OrderStatus.FILLED
    
    def get_remaining_quantity(self) -> Decimal:
        """Get remaining quantity to be executed."""
        return self.quantity.value - self.execution.executed_quantity
    
    def get_fill_percentage(self) -> float:
        """Get fill percentage."""
        if self.quantity.value == 0:
            return 0.0
        return float(self.execution.executed_quantity / self.quantity.value * 100)
    
    def to_exchange_params(self) -> Dict[str, Any]:
        """Convert to exchange API parameters."""
        params = {
            "symbol": self.symbol,
            "side": self.side.value,
            "type": self.order_type.value,
            "quantity": self.quantity.formatted,
            "positionSide": self.position_side.value,
            "reduceOnly": str(self.reduce_only).lower(),
        }
        
        if self.price:
            params["price"] = self.price.formatted
            params["timeInForce"] = self.time_in_force.value
        
        if self.stop_price:
            params["stopPrice"] = self.stop_price.formatted
            params["workingType"] = self.working_type.value
        
        if self.callback_rate:
            params["callbackRate"] = f"{self.callback_rate:.4f}"
        
        if self.close_position:
            params["closePosition"] = "true"
        
        if self.price_protect:
            params["priceProtect"] = "true"
        
        if self.client_order_id:
            params["newClientOrderId"] = self.client_order_id
        
        return params


__all__ = [
    "OrderSide",
    "OrderType", 
    "TimeInForce",
    "OrderStatus",
    "PositionSide",
    "WorkingType",
    "OrderPrice",
    "OrderQuantity",
    "OrderExecution",
    "Order",
]