"""Strategy management API endpoints."""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from ...application.use_cases.strategy_use_cases import (
    CreateStrategyUseCase,
    GetStrategiesUseCase,
    GetStrategyByIdUseCase,
    UpdateStrategyUseCase,
    ActivateStrategyUseCase,
    DeactivateStrategyUseCase,
    DeleteStrategyUseCase,
)
from ...domain.bot import StrategyType
from ...shared.exceptions import NotFoundError, ValidationError, DuplicateError
from ...interfaces.dependencies.auth import get_current_user
from ...interfaces.dependencies.providers import (
    get_create_strategy_use_case,
    get_get_strategies_use_case,
    get_get_strategy_by_id_use_case,
    get_update_strategy_use_case,
    get_activate_strategy_use_case,
    get_deactivate_strategy_use_case,
    get_delete_strategy_use_case,
)
from ...infrastructure.persistence.database import get_db
from ...infrastructure.persistence.models.bot_models import BotModel
from ...infrastructure.persistence.models.trading_models import TradeModel


router = APIRouter(prefix="/strategies", tags=["strategies"])


# Request/Response Models
class CreateStrategyRequest(BaseModel):
    """Request model for creating a strategy."""
    model_config = ConfigDict(from_attributes=True)
    
    name: str = Field(..., min_length=1, max_length=100)
    strategy_type: StrategyType
    description: str = Field(default="", min_length=0, max_length=1000)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    code_content: Optional[str] = None


class UpdateStrategyRequest(BaseModel):
    """Request model for updating a strategy."""
    model_config = ConfigDict(from_attributes=True)
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, min_length=1, max_length=1000)
    parameters: Optional[Dict[str, Any]] = None
    code_content: Optional[str] = None


class StrategyResponse(BaseModel):
    """Response model for strategy."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    name: str
    strategy_type: StrategyType
    description: str
    is_active: bool
    created_at: str
    updated_at: str
    code_content: Optional[str] = None
    
    # Parameters
    parameter_name: str
    parameter_description: str
    parameter_values: Dict[str, Any]
    
    # Performance (if available)
    backtest_results: Optional[Dict[str, Any]]
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_profit_loss: float
    total_fees: float
    net_profit_loss: float
    max_drawdown: float


def strategy_to_response(strategy) -> StrategyResponse:
    """Convert Strategy entity to response model."""
    return StrategyResponse(
        id=strategy.id,
        user_id=strategy.user_id,
        name=strategy.name,
        strategy_type=strategy.strategy_type,
        description=strategy.description,
        is_active=strategy.is_active,
        created_at=strategy.created_at.isoformat(),
        updated_at=strategy.updated_at.isoformat(),
        
        # Parameters
        parameter_name=strategy.parameters.name,
        parameter_description=strategy.parameters.description,
        parameter_values=strategy.parameters.parameters,
        
        # Performance
        backtest_results=strategy.backtest_results,
        total_trades=strategy.live_performance.total_trades,
        winning_trades=strategy.live_performance.winning_trades,
        losing_trades=strategy.live_performance.losing_trades,
        win_rate=strategy.live_performance.win_rate,
        total_profit_loss=float(strategy.live_performance.total_profit_loss),
        total_fees=float(strategy.live_performance.total_fees),
        net_profit_loss=float(strategy.live_performance.net_profit_loss),
        max_drawdown=float(strategy.live_performance.max_drawdown),
        code_content=strategy.code_content,
    )


@router.post("/", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    request: CreateStrategyRequest,
    current_user = Depends(get_current_user),
    create_strategy_use_case: CreateStrategyUseCase = Depends(get_create_strategy_use_case),
):
    """Create a new strategy."""
    try:
        strategy = await create_strategy_use_case.execute(
            user_id=current_user.id,
            name=request.name,
            strategy_type=request.strategy_type,
            description=request.description,
            parameters=request.parameters,
            code_content=request.code_content,
        )
        return strategy_to_response(strategy)
    
    except DuplicateError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=List[StrategyResponse])
async def get_strategies(
    strategy_type: Optional[StrategyType] = None,
    current_user = Depends(get_current_user),
    get_strategies_use_case: GetStrategiesUseCase = Depends(get_get_strategies_use_case),
):
    """Get user's strategies."""
    try:
        strategies = await get_strategies_use_case.execute(
            user_id=current_user.id,
            strategy_type=strategy_type
        )
        return [strategy_to_response(strategy) for strategy in strategies]
    
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: UUID,
    current_user = Depends(get_current_user),
    get_strategy_use_case: GetStrategyByIdUseCase = Depends(get_get_strategy_by_id_use_case),
):
    """Get a specific strategy."""
    try:
        strategy = await get_strategy_use_case.execute(
            user_id=current_user.id,
            strategy_id=strategy_id
        )
        return strategy_to_response(strategy)
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: UUID,
    request: UpdateStrategyRequest,
    current_user = Depends(get_current_user),
    update_strategy_use_case: UpdateStrategyUseCase = Depends(get_update_strategy_use_case),
):
    """Update a strategy."""
    try:
        strategy = await update_strategy_use_case.execute(
            user_id=current_user.id,
            strategy_id=strategy_id,
            name=request.name,
            description=request.description,
            parameters=request.parameters,
            code_content=request.code_content,
        )
        return strategy_to_response(strategy)
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (ValidationError, DuplicateError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{strategy_id}/activate", response_model=StrategyResponse)
async def activate_strategy(
    strategy_id: UUID,
    current_user = Depends(get_current_user),
    activate_strategy_use_case: ActivateStrategyUseCase = Depends(get_activate_strategy_use_case),
):
    """Activate a strategy."""
    try:
        strategy = await activate_strategy_use_case.execute(
            user_id=current_user.id,
            strategy_id=strategy_id
        )
        return strategy_to_response(strategy)
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{strategy_id}/deactivate", response_model=StrategyResponse)
async def deactivate_strategy(
    strategy_id: UUID,
    current_user = Depends(get_current_user),
    deactivate_strategy_use_case: DeactivateStrategyUseCase = Depends(get_deactivate_strategy_use_case),
):
    """Deactivate a strategy."""
    try:
        strategy = await deactivate_strategy_use_case.execute(
            user_id=current_user.id,
            strategy_id=strategy_id
        )
        return strategy_to_response(strategy)
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: UUID,
    current_user = Depends(get_current_user),
    delete_strategy_use_case: DeleteStrategyUseCase = Depends(get_delete_strategy_use_case),
):
    """Delete a strategy."""
    try:
        await delete_strategy_use_case.execute(
            user_id=current_user.id,
            strategy_id=strategy_id
        )
    
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/types/", response_model=List[dict])
async def get_strategy_types():
    """Get available strategy types with descriptions."""
    return [
        {
            "type": StrategyType.GRID,
            "name": "Grid Trading",
            "description": "Places buy and sell orders at regular price intervals to profit from market volatility",
            "parameters": {
                "grid_count": "Number of grid levels",
                "grid_spacing": "Percentage spacing between grid levels",
                "total_investment": "Total investment amount"
            }
        },
        {
            "type": StrategyType.DCA,
            "name": "Dollar Cost Averaging",
            "description": "Regularly buys assets regardless of price to reduce average cost basis over time",
            "parameters": {
                "investment_amount": "Amount to invest per interval",
                "interval_hours": "Hours between purchases",
                "max_orders": "Maximum number of orders"
            }
        },
        {
            "type": StrategyType.MARTINGALE,
            "name": "Martingale",
            "description": "Doubles position size after each loss to recover previous losses with one win",
            "parameters": {
                "base_amount": "Initial position size",
                "multiplier": "Multiplier after each loss",
                "max_orders": "Maximum number of orders"
            }
        },
        {
            "type": StrategyType.TREND_FOLLOWING,
            "name": "Trend Following",
            "description": "Follows market trends using technical indicators like moving averages",
            "parameters": {
                "short_ma_period": "Short moving average period",
                "long_ma_period": "Long moving average period",
                "position_size": "Position size percentage"
            }
        },
        {
            "type": StrategyType.MEAN_REVERSION,
            "name": "Mean Reversion",
            "description": "Trades on the assumption that prices will revert to their historical average",
            "parameters": {
                "lookback_period": "Period for calculating mean",
                "deviation_threshold": "Standard deviations from mean",
                "position_size": "Position size percentage"
            }
        },
        {
            "type": StrategyType.ARBITRAGE,
            "name": "Arbitrage",
            "description": "Exploits price differences between different exchanges or trading pairs",
            "parameters": {
                "min_profit_percentage": "Minimum profit percentage",
                "max_position_size": "Maximum position size",
                "exchanges": "List of exchanges to monitor"
            }
        },
        {
            "type": StrategyType.CUSTOM,
            "name": "Custom Strategy",
            "description": "User-defined custom trading strategy with flexible parameters",
            "parameters": {
                "custom_rules": "Custom trading rules",
                "entry_conditions": "Entry conditions",
                "exit_conditions": "Exit conditions"
            }
        },
    ]


# ===== PHASE 3 INTEGRATION ENDPOINTS =====

class StrategyPerformanceResponse(BaseModel):
    """Strategy performance metrics response."""
    model_config = ConfigDict(from_attributes=True)
    
    total_pnl: float
    total_trades: int
    win_rate: float
    avg_profit: float
    sharpe_ratio: float
    active_bots: int
    best_symbol: Optional[str]


class StrategyPerformanceHistoryResponse(BaseModel):
    """Strategy performance history response."""
    model_config = ConfigDict(from_attributes=True)
    
    month: str
    pnl: float
    trades_count: int
    win_rate: float


@router.get("/{strategy_id}/performance", response_model=StrategyPerformanceResponse)
async def get_strategy_performance(
    strategy_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive performance metrics for a specific strategy.
    
    Returns aggregated performance data from all bots using this strategy,
    including P&L, trade statistics, and risk metrics.
    """
    
    try:
        # Get all bots using this strategy for the current user
        bots_query = select(BotModel).where(
            and_(
                BotModel.strategy_id == strategy_id,
                BotModel.user_id == current_user.id
            )
        )
        bots_result = await db.execute(bots_query)
        bots = bots_result.scalars().all()
        
        if not bots:
            return StrategyPerformanceResponse(
                total_pnl=0.0,
                total_trades=0,
                win_rate=0.0,
                avg_profit=0.0,
                sharpe_ratio=0.0,
                active_bots=0,
                best_symbol=None
            )
        
        # Get bot IDs
        bot_ids = [bot.id for bot in bots]
        
        # Get aggregated trade statistics
        trades_query = select(
            func.count(TradeModel.id).label('total_trades'),
            func.sum(TradeModel.pnl).label('total_pnl'),
            func.avg(TradeModel.pnl).label('avg_profit'),
            func.count().filter(TradeModel.pnl > 0).label('winning_trades'),
        ).where(TradeModel.bot_id.in_(bot_ids))
        
        trades_result = await db.execute(trades_query)
        trade_stats = trades_result.first()
        
        # Calculate metrics
        total_trades = trade_stats.total_trades or 0
        total_pnl = float(trade_stats.total_pnl or 0)
        avg_profit = float(trade_stats.avg_profit or 0)
        winning_trades = trade_stats.winning_trades or 0
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Calculate Sharpe ratio (simplified)
        sharpe_ratio = 0.0
        if total_trades > 10:
            # Get daily returns for Sharpe calculation
            daily_pnl_query = select(
                func.date(TradeModel.created_at).label('trade_date'),
                func.sum(TradeModel.pnl).label('daily_pnl')
            ).where(
                TradeModel.bot_id.in_(bot_ids)
            ).group_by(func.date(TradeModel.created_at))
            
            daily_result = await db.execute(daily_pnl_query)
            daily_returns = [float(row.daily_pnl) for row in daily_result]
            
            if len(daily_returns) > 1:
                import numpy as np
                returns_array = np.array(daily_returns)
                mean_return = np.mean(returns_array)
                std_return = np.std(returns_array)
                if std_return > 0:
                    sharpe_ratio = (mean_return / std_return) * np.sqrt(252)  # Annualized
        
        # Get most profitable symbol
        best_symbol_query = select(
            TradeModel.symbol,
            func.sum(TradeModel.pnl).label('symbol_pnl')
        ).where(
            TradeModel.bot_id.in_(bot_ids)
        ).group_by(TradeModel.symbol).order_by(func.sum(TradeModel.pnl).desc()).limit(1)
        
        symbol_result = await db.execute(best_symbol_query)
        best_symbol_row = symbol_result.first()
        best_symbol = best_symbol_row.symbol if best_symbol_row else None
        
        # Count active bots
        from ...domain.bot.enums import BotStatus
        active_bots = len([bot for bot in bots if bot.status == BotStatus.RUNNING])
        
        return StrategyPerformanceResponse(
            total_pnl=round(total_pnl, 2),
            total_trades=total_trades,
            win_rate=round(win_rate, 1),
            avg_profit=round(avg_profit, 2),
            sharpe_ratio=round(float(sharpe_ratio), 3),
            active_bots=active_bots,
            best_symbol=best_symbol
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get strategy performance: {str(e)}"
        )


@router.get("/{strategy_id}/performance-history", response_model=List[StrategyPerformanceHistoryResponse])
async def get_strategy_performance_history(
    strategy_id: UUID,
    months: int = Query(12, ge=1, le=24, description="Number of months to analyze"),
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get historical performance breakdown by month for a strategy.
    
    Returns monthly P&L, trade counts, and win rates for the specified period.
    Useful for analyzing strategy consistency and seasonal patterns.
    """
    
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=months * 30)
        
        # Get all bots using this strategy for the current user
        bots_query = select(BotModel.id).where(
            and_(
                BotModel.strategy_id == strategy_id,
                BotModel.user_id == current_user.id
            )
        )
        bots_result = await db.execute(bots_query)
        bot_ids = [row.id for row in bots_result]
        
        if not bot_ids:
            return []
        
        # Get monthly performance data
        monthly_query = select(
            func.date_format(TradeModel.created_at, '%Y-%m').label('month'),
            func.sum(TradeModel.pnl).label('monthly_pnl'),
            func.count(TradeModel.id).label('trades_count'),
            func.count().filter(TradeModel.pnl > 0).label('winning_trades'),
        ).where(
            and_(
                TradeModel.bot_id.in_(bot_ids),
                TradeModel.created_at >= start_date,
                TradeModel.created_at <= end_date
            )
        ).group_by(func.date_format(TradeModel.created_at, '%Y-%m')).order_by('month')
        
        monthly_result = await db.execute(monthly_query)
        monthly_data = monthly_result.all()
        
        performance_history = []
        for row in monthly_data:
            trades_count = row.trades_count or 0
            winning_trades = row.winning_trades or 0
            win_rate = (winning_trades / trades_count * 100) if trades_count > 0 else 0
            
            performance_history.append(StrategyPerformanceHistoryResponse(
                month=row.month,
                pnl=round(float(row.monthly_pnl or 0), 2),
                trades_count=trades_count,
                win_rate=round(win_rate, 1)
            ))
        
        return performance_history
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get strategy performance history: {str(e)}"
        )