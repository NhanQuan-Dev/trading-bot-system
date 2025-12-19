"""Order API schemas."""
from datetime import datetime as dt
from typing import Optional, Dict, Any, List
from decimal import Decimal
from pydantic import BaseModel, Field, validator, ConfigDict
import uuid

from ...domain.order import OrderSide, OrderType, TimeInForce, OrderStatus, PositionSide, WorkingType


class OrderPriceSchema(BaseModel):
    """Order price schema."""
    value: Decimal = Field(..., description="Price value", gt=0)
    
    @property
    def formatted(self) -> str:
        """Format price for display."""
        return f"{self.value:.8f}".rstrip('0').rstrip('.')


class OrderQuantitySchema(BaseModel):
    """Order quantity schema."""
    value: Decimal = Field(..., description="Quantity value", gt=0)
    
    @property
    def formatted(self) -> str:
        """Format quantity for display."""
        return f"{self.value:.8f}".rstrip('0').rstrip('.')


class OrderExecutionSchema(BaseModel):
    """Order execution details schema."""
    executed_quantity: Decimal = Field(default=Decimal("0"), description="Executed quantity")
    executed_quote: Decimal = Field(default=Decimal("0"), description="Executed quote amount")
    avg_price: Optional[Decimal] = Field(default=None, description="Average execution price")
    commission: Decimal = Field(default=Decimal("0"), description="Trading commission")
    commission_asset: str = Field(default="USDT", description="Commission asset")


class CreateOrderRequest(BaseModel):
    """Create order request schema."""
    exchange_connection_id: uuid.UUID = Field(..., description="Exchange connection ID")
    symbol: str = Field(..., description="Trading symbol", min_length=1)
    side: OrderSide = Field(..., description="Order side")
    order_type: OrderType = Field(..., description="Order type")
    quantity: Decimal = Field(..., description="Order quantity", gt=0)
    
    # Optional fields
    price: Optional[Decimal] = Field(default=None, description="Order price", gt=0)
    stop_price: Optional[Decimal] = Field(default=None, description="Stop price", gt=0)
    callback_rate: Optional[Decimal] = Field(default=None, description="Callback rate for trailing stop")
    
    # Futures specific
    position_side: PositionSide = Field(default=PositionSide.BOTH, description="Position side")
    time_in_force: TimeInForce = Field(default=TimeInForce.GTC, description="Time in force")
    reduce_only: bool = Field(default=False, description="Reduce only flag")
    close_position: bool = Field(default=False, description="Close position flag")
    
    # Advanced options
    working_type: WorkingType = Field(default=WorkingType.CONTRACT_PRICE, description="Working type")
    price_protect: bool = Field(default=False, description="Price protect flag")
    
    # Risk management
    leverage: int = Field(default=1, description="Leverage", ge=1, le=125)
    margin_type: str = Field(default="ISOLATED", description="Margin type")
    
    # Optional metadata
    client_order_id: Optional[str] = Field(default=None, description="Client order ID")
    meta_data: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    
    @validator("symbol")
    def validate_symbol(cls, v):
        """Validate symbol format."""
        return v.upper()
    
    @validator("price")
    def validate_price_for_limit(cls, v, values):
        """Validate price is provided for limit orders."""
        order_type = values.get("order_type")
        if order_type == OrderType.LIMIT and v is None:
            raise ValueError("Price is required for limit orders")
        return v
    
    @validator("stop_price")
    def validate_stop_price(cls, v, values):
        """Validate stop price for stop orders."""
        order_type = values.get("order_type")
        if order_type in [OrderType.STOP_MARKET, OrderType.TAKE_PROFIT_MARKET] and v is None:
            raise ValueError(f"Stop price is required for {order_type} orders")
        return v
    
    @validator("callback_rate")
    def validate_callback_rate(cls, v, values):
        """Validate callback rate for trailing stop orders."""
        order_type = values.get("order_type")
        if order_type == OrderType.TRAILING_STOP_MARKET:
            if v is None:
                raise ValueError("Callback rate is required for trailing stop orders")
            if not (0.1 <= v <= 5.0):
                raise ValueError("Callback rate must be between 0.1 and 5.0")
        return v


class UpdateOrderRequest(BaseModel):
    """Update order request schema."""
    quantity: Optional[Decimal] = Field(default=None, description="New order quantity", gt=0)
    price: Optional[Decimal] = Field(default=None, description="New order price", gt=0)
    meta_data: Optional[Dict[str, Any]] = Field(default=None, description="Updated metadata")


class CancelOrderRequest(BaseModel):
    """Cancel order request schema."""
    reason: Optional[str] = Field(default=None, description="Cancellation reason")


class OrderResponse(BaseModel):
    """Order response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID = Field(..., description="Order ID")
    user_id: uuid.UUID = Field(..., description="User ID")
    bot_id: Optional[uuid.UUID] = Field(default=None, description="Bot ID")
    exchange_connection_id: uuid.UUID = Field(..., description="Exchange connection ID")
    symbol: str = Field(..., description="Trading symbol")
    
    # Order details
    side: OrderSide = Field(..., description="Order side")
    order_type: OrderType = Field(..., description="Order type")
    quantity: OrderQuantitySchema = Field(..., description="Order quantity")
    price: Optional[OrderPriceSchema] = Field(default=None, description="Order price")
    stop_price: Optional[OrderPriceSchema] = Field(default=None, description="Stop price")
    callback_rate: Optional[Decimal] = Field(default=None, description="Callback rate")
    
    # Futures specific
    position_side: PositionSide = Field(..., description="Position side")
    time_in_force: TimeInForce = Field(..., description="Time in force")
    reduce_only: bool = Field(..., description="Reduce only flag")
    close_position: bool = Field(..., description="Close position flag")
    
    # Advanced options
    working_type: WorkingType = Field(..., description="Working type")
    price_protect: bool = Field(..., description="Price protect flag")
    
    # Status and execution
    status: OrderStatus = Field(..., description="Order status")
    exchange_order_id: Optional[str] = Field(default=None, description="Exchange order ID")
    client_order_id: Optional[str] = Field(default=None, description="Client order ID")
    execution: OrderExecutionSchema = Field(..., description="Execution details")
    
    # Risk management
    leverage: int = Field(..., description="Leverage")
    margin_type: str = Field(..., description="Margin type")
    
    # Metadata
    error_message: Optional[str] = Field(default=None, description="Error message")
    meta_data: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    
    # Timestamps
    created_at: dt = Field(..., description="Creation timestamp")
    updated_at: dt = Field(..., description="Last update timestamp")
    submitted_at: Optional[dt] = Field(default=None, description="Submission timestamp")
    filled_at: Optional[dt] = Field(default=None, description="Fill timestamp")
    cancelled_at: Optional[dt] = Field(default=None, description="Cancellation timestamp")
    
    # Computed properties
    @property
    def is_active(self) -> bool:
        """Check if order is active."""
        return self.status in [OrderStatus.PENDING, OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED]
    
    @property
    def is_filled(self) -> bool:
        """Check if order is filled."""
        return self.status == OrderStatus.FILLED
    
    @property
    def remaining_quantity(self) -> Decimal:
        """Get remaining quantity."""
        return self.quantity.value - self.execution.executed_quantity
    
    @property
    def fill_percentage(self) -> float:
        """Get fill percentage."""
        if self.quantity.value == 0:
            return 0.0
        return float(self.execution.executed_quantity / self.quantity.value * 100)


class OrderListResponse(BaseModel):
    """Order list response schema."""
    orders: List[OrderResponse] = Field(..., description="List of orders")
    total: int = Field(..., description="Total number of orders")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")


class OrderStatsResponse(BaseModel):
    """Order statistics response schema."""
    total_orders: int = Field(..., description="Total number of orders")
    active_orders: int = Field(..., description="Number of active orders")
    filled_orders: int = Field(..., description="Number of filled orders")
    cancelled_orders: int = Field(..., description="Number of cancelled orders")
    total_volume: Decimal = Field(..., description="Total trading volume")
    total_commission: Decimal = Field(..., description="Total commission paid")
    avg_order_size: Decimal = Field(..., description="Average order size")


class CancelAllOrdersRequest(BaseModel):
    """Cancel all orders request schema."""
    symbol: Optional[str] = Field(default=None, description="Filter by symbol")
    bot_id: Optional[uuid.UUID] = Field(default=None, description="Filter by bot")
    
    @validator("symbol")
    def validate_symbol(cls, v):
        """Validate symbol format."""
        return v.upper() if v else v


class CancelAllOrdersResponse(BaseModel):
    """Cancel all orders response schema."""
    cancelled_orders: List[OrderResponse] = Field(..., description="Cancelled orders")
    total_cancelled: int = Field(..., description="Total orders cancelled")


class OrderFilterRequest(BaseModel):
    """Order filter request schema."""
    status: Optional[OrderStatus] = Field(default=None, description="Filter by status")
    symbol: Optional[str] = Field(default=None, description="Filter by symbol")
    bot_id: Optional[uuid.UUID] = Field(default=None, description="Filter by bot")
    side: Optional[OrderSide] = Field(default=None, description="Filter by side")
    order_type: Optional[OrderType] = Field(default=None, description="Filter by type")
    start_date: Optional[dt] = Field(default=None, description="Filter from date")
    end_date: Optional[dt] = Field(default=None, description="Filter to date")
    page: int = Field(default=1, description="Page number", ge=1)
    page_size: int = Field(default=50, description="Page size", ge=1, le=1000)
    
    @validator("symbol")
    def validate_symbol(cls, v):
        """Validate symbol format."""
        return v.upper() if v else v