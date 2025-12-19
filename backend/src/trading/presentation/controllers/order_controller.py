"""Order API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List
from datetime import datetime as dt
import uuid

from ...interfaces.dependencies.auth import get_current_active_user
from ...infrastructure.persistence.database import get_db
from ...domain.order import OrderStatus, OrderSide, OrderType
from ...application.schemas.order_schemas import (
    CreateOrderRequest,
    UpdateOrderRequest,
    CancelOrderRequest,
    OrderResponse,
    OrderListResponse,
    OrderStatsResponse,
    CancelAllOrdersRequest,
    CancelAllOrdersResponse,
    OrderFilterRequest,
)
from ...infrastructure.repositories.order_repository import OrderRepository
from ...domain.order import Order, OrderQuantity, OrderPrice
from ...domain.user import User
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(prefix="/orders", tags=["orders"])


async def get_order_repository(session: AsyncSession = Depends(get_db)) -> OrderRepository:
    """Get order repository dependency."""
    return OrderRepository(session)


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: CreateOrderRequest,
    user: User = Depends(get_current_active_user),
    repository: OrderRepository = Depends(get_order_repository),
    session: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """
    Create a new order.
    
    Creates a new trading order with the specified parameters.
    The order will be validated and submitted to the exchange.
    """
    try:
        # Create order domain entity based on type
        if order_data.order_type == OrderType.MARKET:
            order = Order.create_market_order(
                user_id=user.id,
                exchange_connection_id=order_data.exchange_connection_id,
                symbol=order_data.symbol,
                side=order_data.side,
                quantity=order_data.quantity,
                bot_id=order_data.bot_id,
                position_side=order_data.position_side,
                reduce_only=order_data.reduce_only,
                leverage=order_data.leverage,
            )
        elif order_data.order_type == OrderType.LIMIT:
            if order_data.price is None:
                raise ValueError("Price is required for limit orders")
            order = Order.create_limit_order(
                user_id=user.id,
                exchange_connection_id=order_data.exchange_connection_id,
                symbol=order_data.symbol,
                side=order_data.side,
                quantity=order_data.quantity,
                price=order_data.price,
                bot_id=order_data.bot_id,
                position_side=order_data.position_side,
                time_in_force=order_data.time_in_force,
                reduce_only=order_data.reduce_only,
                leverage=order_data.leverage,
            )
        elif order_data.order_type == OrderType.STOP_MARKET:
            if order_data.stop_price is None:
                raise ValueError("Stop price is required for stop market orders")
            order = Order.create_stop_market_order(
                user_id=user.id,
                exchange_connection_id=order_data.exchange_connection_id,
                symbol=order_data.symbol,
                side=order_data.side,
                quantity=order_data.quantity,
                stop_price=order_data.stop_price,
                bot_id=order_data.bot_id,
                position_side=order_data.position_side,
                working_type=order_data.working_type,
                reduce_only=order_data.reduce_only,
                leverage=order_data.leverage,
            )
        else:
            raise ValueError(f"Order type {order_data.order_type} not implemented yet")
        
        # Set optional fields
        if order_data.client_order_id:
            order.client_order_id = order_data.client_order_id
        if order_data.meta_data:
            order.meta_data = order_data.meta_data
        
        # Set advanced options
        order.close_position = order_data.close_position
        order.price_protect = order_data.price_protect
        order.margin_type = order_data.margin_type
        
        # Set callback rate for trailing stop
        if order_data.callback_rate:
            order.callback_rate = order_data.callback_rate
        
        # Save to database
        created_order = await repository.create(order)
        await session.commit()
        
        # Convert to response
        return _convert_to_response(created_order)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create order: {str(e)}"
        )


@router.get("/", response_model=OrderListResponse)
async def list_orders(
    status: Optional[OrderStatus] = Query(None, description="Filter by status"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    bot_id: Optional[uuid.UUID] = Query(None, description="Filter by bot"),
    side: Optional[OrderSide] = Query(None, description="Filter by side"),
    order_type: Optional[OrderType] = Query(None, description="Filter by type"),
    page: int = Query(1, description="Page number", ge=1),
    page_size: int = Query(50, description="Page size", ge=1, le=1000),
    user: User = Depends(get_current_active_user),
    repository: OrderRepository = Depends(get_order_repository),
) -> OrderListResponse:
    """
    List orders for the current user.
    
    Returns a paginated list of orders with optional filters.
    """
    try:
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get orders from repository
        orders = await repository.list_by_user(
            user_id=user.id,
            status=status,
            symbol=symbol.upper() if symbol else None,
            bot_id=bot_id,
            limit=page_size,
            offset=offset
        )
        
        # Get total count
        total = await repository.get_order_count(user.id, status)
        
        # Convert to response models
        order_responses = [_convert_to_response(order) for order in orders]
        
        return OrderListResponse(
            orders=order_responses,
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list orders: {str(e)}"
        )


@router.get("/active", response_model=List[OrderResponse])
async def list_active_orders(
    user: User = Depends(get_current_active_user),
    repository: OrderRepository = Depends(get_order_repository),
) -> List[OrderResponse]:
    """
    Get all active orders for the current user.
    
    Returns orders with status: PENDING, NEW, or PARTIALLY_FILLED.
    """
    try:
        orders = await repository.list_active_by_user(user.id)
        return [_convert_to_response(order) for order in orders]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active orders: {str(e)}"
        )


@router.get("/stats", response_model=OrderStatsResponse)
async def get_order_stats(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    start_date: Optional[dt] = Query(None, description="Start date filter"),
    end_date: Optional[dt] = Query(None, description="End date filter"),
    user: User = Depends(get_current_active_user),
    repository: OrderRepository = Depends(get_order_repository),
) -> OrderStatsResponse:
    """
    Get order statistics for the current user.
    
    Returns various metrics about the user's trading activity.
    """
    try:
        # Get volume stats
        volume_stats = await repository.get_volume_stats(
            user_id=user.id,
            symbol=symbol.upper() if symbol else None,
            start_date=start_date,
            end_date=end_date
        )
        
        # Get order counts by status
        total_orders = await repository.get_order_count(user.id)
        filled_orders = await repository.get_order_count(user.id, OrderStatus.FILLED)
        cancelled_orders = await repository.get_order_count(user.id, OrderStatus.CANCELLED)
        
        # Get active orders count
        active_orders = await repository.list_active_by_user(user.id)
        
        return OrderStatsResponse(
            total_orders=total_orders,
            active_orders=len(active_orders),
            filled_orders=filled_orders,
            cancelled_orders=cancelled_orders,
            total_volume=volume_stats["total_volume"],
            total_commission=volume_stats["total_commission"],
            avg_order_size=volume_stats["avg_order_size"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get order stats: {str(e)}"
        )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    repository: OrderRepository = Depends(get_order_repository),
) -> OrderResponse:
    """
    Get a specific order by ID.
    
    Returns the order details if it belongs to the current user.
    """
    try:
        order = await repository.get_by_id(order_id, user.id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        return _convert_to_response(order)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get order: {str(e)}"
        )


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: uuid.UUID,
    order_data: UpdateOrderRequest,
    user: User = Depends(get_current_active_user),
    repository: OrderRepository = Depends(get_order_repository),
    session: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """
    Update an existing order.
    
    Only certain fields can be updated for active orders.
    """
    try:
        # Get existing order
        order = await repository.get_by_id(order_id, user.id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        # Check if order can be updated
        if not order.is_active():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only active orders can be updated"
            )
        
        # Update allowed fields
        if order_data.quantity is not None:
            order.quantity = OrderQuantity(order_data.quantity)
        
        if order_data.price is not None:
            order.price = OrderPrice(order_data.price)
        
        if order_data.meta_data is not None:
            order.meta_data = order_data.meta_data
        
        # Update timestamps
        order.updated_at = dt.now()
        
        # Save changes
        updated_order = await repository.update(order)
        await session.commit()
        
        return _convert_to_response(updated_order)
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update order: {str(e)}"
        )


@router.delete("/{order_id}", response_model=OrderResponse)
async def cancel_order(
    order_id: uuid.UUID,
    cancel_data: CancelOrderRequest = CancelOrderRequest(),
    user: User = Depends(get_current_active_user),
    repository: OrderRepository = Depends(get_order_repository),
    session: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """
    Cancel an order.
    
    Cancels the order if it's still active.
    """
    try:
        # Cancel order
        cancelled_order = await repository.cancel_order(
            order_id=order_id,
            user_id=user.id,
            reason=cancel_data.reason
        )
        
        if not cancelled_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found or cannot be cancelled"
            )
        
        await session.commit()
        return _convert_to_response(cancelled_order)
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel order: {str(e)}"
        )


@router.delete("/", response_model=CancelAllOrdersResponse)
async def cancel_all_orders(
    cancel_data: CancelAllOrdersRequest = CancelAllOrdersRequest(),
    user: User = Depends(get_current_active_user),
    repository: OrderRepository = Depends(get_order_repository),
    session: AsyncSession = Depends(get_db),
) -> CancelAllOrdersResponse:
    """
    Cancel all orders.
    
    Cancels all active orders with optional filters.
    """
    try:
        cancelled_orders = []
        
        if cancel_data.bot_id:
            # Cancel all orders for specific bot
            cancelled_orders = await repository.cancel_all_by_bot(cancel_data.bot_id)
        elif cancel_data.symbol:
            # Cancel all orders for specific symbol
            cancelled_orders = await repository.cancel_all_by_symbol(
                user.id, 
                cancel_data.symbol.upper()
            )
        else:
            # Cancel all user's active orders
            active_orders = await repository.list_active_by_user(user.id)
            for order in active_orders:
                cancelled_order = await repository.cancel_order(
                    order.id, 
                    user.id, 
                    "Cancel all orders request"
                )
                if cancelled_order:
                    cancelled_orders.append(cancelled_order)
        
        await session.commit()
        
        return CancelAllOrdersResponse(
            cancelled_orders=[_convert_to_response(order) for order in cancelled_orders],
            total_cancelled=len(cancelled_orders)
        )
        
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel all orders: {str(e)}"
        )


def _convert_to_response(order: Order) -> OrderResponse:
    """Convert domain order to API response."""
    from ...application.schemas.order_schemas import OrderQuantitySchema, OrderPriceSchema, OrderExecutionSchema
    
    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        bot_id=order.bot_id,
        exchange_connection_id=order.exchange_connection_id,
        symbol=order.symbol,
        side=order.side,
        order_type=order.order_type,
        quantity=OrderQuantitySchema(value=order.quantity.value),
        price=OrderPriceSchema(value=order.price.value) if order.price else None,
        stop_price=OrderPriceSchema(value=order.stop_price.value) if order.stop_price else None,
        callback_rate=order.callback_rate,
        position_side=order.position_side,
        time_in_force=order.time_in_force,
        reduce_only=order.reduce_only,
        close_position=order.close_position,
        working_type=order.working_type,
        price_protect=order.price_protect,
        status=order.status,
        exchange_order_id=order.exchange_order_id,
        client_order_id=order.client_order_id,
        execution=OrderExecutionSchema(
            executed_quantity=order.execution.executed_quantity,
            executed_quote=order.execution.executed_quote,
            avg_price=order.execution.avg_price,
            commission=order.execution.commission,
            commission_asset=order.execution.commission_asset,
        ),
        leverage=order.leverage,
        margin_type=order.margin_type,
        error_message=order.error_message,
        meta_data=order.meta_data,
        created_at=order.created_at,
        updated_at=order.updated_at,
        submitted_at=order.submitted_at,
        filled_at=order.filled_at,
        cancelled_at=order.cancelled_at,
    )