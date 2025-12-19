"""Order API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import uuid

from .schemas.order import (
    CreateOrderRequest,
    OrderResponse,
    OrderListResponse,
    CancelOrderRequest,
    OrderStatsResponse,
)
from ....infrastructure.persistence.database import get_db
from ....infrastructure.repositories.order_repository import OrderRepository
from ....infrastructure.repositories.exchange_repository import ExchangeRepository
from ....infrastructure.exchange.exchange_manager import ExchangeManager
from ...dependencies.auth import get_current_active_user
from ....domain.user import User
from ....domain.order import (
    Order,
    OrderType,
    OrderStatus,
    OrderQuantity,
    OrderPrice,
)
from ....application.use_cases.order import (
    CreateOrderUseCase,
    CancelOrderUseCase,
    GetOrdersUseCase,
    GetOrderByIdUseCase,
)
from ....shared.exceptions.business import ValidationError, ExchangeConnectionError, NotFoundError

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: CreateOrderRequest,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """
    Create a new order.
    
    Creates a new trading order with the specified parameters.
    """
    try:
        # Initialize dependencies
        order_repository = OrderRepository(session)
        exchange_repository = ExchangeRepository(session)
        exchange_manager = ExchangeManager()
        
        # Initialize use case
        create_order_use_case = CreateOrderUseCase(
            order_repository=order_repository,
            exchange_repository=exchange_repository,
            exchange_manager=exchange_manager
        )
        
        # Execute use case
        created_order = await create_order_use_case.execute(
            user_id=user.id,
            exchange_connection_id=order_data.exchange_connection_id,
            symbol=order_data.symbol,
            side=order_data.side,
            order_type=order_data.order_type,
            quantity=order_data.quantity,
            price=order_data.price,
            stop_price=order_data.stop_price,
            position_side=order_data.position_side,
            time_in_force=order_data.time_in_force,
            reduce_only=order_data.reduce_only,
            leverage=order_data.leverage,
            client_order_id=order_data.client_order_id,
        )
        
        await session.commit()
        
        # Convert to response
        return _convert_to_response(created_order)
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ExchangeConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
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
    status_filter: Optional[OrderStatus] = Query(None, alias="status", description="Filter by status"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    bot_id: Optional[uuid.UUID] = Query(None, description="Filter by bot"),
    limit: int = Query(50, description="Number of orders", ge=1, le=1000),
    offset: int = Query(0, description="Offset for pagination", ge=0),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> OrderListResponse:
    """
    List orders for the current user.
    
    Returns a list of orders with optional filters.
    """
    try:
        # Initialize dependencies
        order_repository = OrderRepository(session)
        
        # Initialize use case
        get_orders_use_case = GetOrdersUseCase(order_repository=order_repository)
        
        # Execute use case
        result = await get_orders_use_case.execute(
            user_id=user.id,
            status=status_filter,
            symbol=symbol.upper() if symbol else None,
            bot_id=bot_id,
            limit=limit,
            offset=offset
        )
        
        # Convert to response models
        order_responses = [_convert_to_response(order) for order in result["orders"]]
        
        return OrderListResponse(
            orders=order_responses,
            total=result["total_count"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list orders: {str(e)}"
        )


@router.get("/active", response_model=List[OrderResponse])
async def list_active_orders(
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> List[OrderResponse]:
    """
    Get all active orders for the current user.
    
    Returns orders with status: PENDING, NEW, or PARTIALLY_FILLED.
    """
    try:
        repository = OrderRepository(session)
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
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> OrderStatsResponse:
    """
    Get order statistics for the current user.
    
    Returns various metrics about the user's trading activity.
    """
    try:
        repository = OrderRepository(session)
        
        # Get volume stats
        volume_stats = await repository.get_volume_stats(
            user_id=user.id,
            symbol=symbol.upper() if symbol else None
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
            total_commission=volume_stats["total_commission"]
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
    session: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """
    Get a specific order by ID.
    
    Returns the order details if it belongs to the current user.
    """
    try:
        # Initialize dependencies
        order_repository = OrderRepository(session)
        
        # Initialize use case
        get_order_use_case = GetOrderByIdUseCase(order_repository=order_repository)
        
        # Execute use case
        order = await get_order_use_case.execute(user_id=user.id, order_id=order_id)
        
        return _convert_to_response(order)
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get order: {str(e)}"
        )


@router.delete("/{order_id}", response_model=OrderResponse)
async def cancel_order(
    order_id: uuid.UUID,
    cancel_data: CancelOrderRequest = CancelOrderRequest(),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """
    Cancel an order.
    
    Cancels the order if it's still active.
    """
    try:
        # Initialize dependencies
        order_repository = OrderRepository(session)
        exchange_repository = ExchangeRepository(session)
        exchange_manager = ExchangeManager()
        
        # Initialize use case
        cancel_order_use_case = CancelOrderUseCase(
            order_repository=order_repository,
            exchange_repository=exchange_repository,
            exchange_manager=exchange_manager
        )
        
        # Execute use case
        cancelled_order = await cancel_order_use_case.execute(
            user_id=user.id,
            order_id=order_id,
            reason=cancel_data.reason
        )
        
        await session.commit()
        return _convert_to_response(cancelled_order)
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ExchangeConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel order: {str(e)}"
        )


def _convert_to_response(order: Order) -> OrderResponse:
    """Convert domain order to API response."""
    from .schemas.order import OrderQuantitySchema, OrderPriceSchema, OrderExecutionSchema
    
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
        position_side=order.position_side,
        time_in_force=order.time_in_force,
        reduce_only=order.reduce_only,
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
        error_message=order.error_message,
        created_at=order.created_at,
        updated_at=order.updated_at,
        submitted_at=order.submitted_at,
        filled_at=order.filled_at,
        cancelled_at=order.cancelled_at,
    )