"""SQLAlchemy repository implementation for backtests."""

import logging
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...domain.backtesting import (
    BacktestRun,
    BacktestStatus,
    IBacktestRepository,
)
from ..persistence.models.backtest_models import (
    BacktestRunModel, 
    BacktestResultModel, 
    BacktestTradeModel
)

logger = logging.getLogger(__name__)


class BacktestRepository(IBacktestRepository):
    """SQLAlchemy implementation of backtest repository."""
    
    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session
    
    async def save(self, backtest: BacktestRun) -> BacktestRun:
        """Save or update backtest run."""
        
        # Check if already exists
        result = await self.session.execute(
            select(BacktestRunModel).where(BacktestRunModel.id == backtest.id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing
            existing.status = backtest.status
            existing.progress_percent = backtest.progress_percent
            existing.start_time = backtest.start_time
            existing.end_time = backtest.end_time
            existing.final_equity = backtest.final_equity
            existing.total_trades = backtest.total_trades
            existing.win_rate = backtest.win_rate
            existing.total_return = backtest.total_return
            existing.error_message = backtest.error_message
        else:
            # Create new
            model = BacktestRunModel(
                id=backtest.id,
                user_id=backtest.user_id,
                strategy_id=backtest.strategy_id,
                symbol=backtest.config.symbol,
                timeframe=backtest.config.timeframe,
                start_date=backtest.config.start_date,
                end_date=backtest.config.end_date,
                initial_capital=backtest.config.initial_capital,
                config=backtest.config.model_dump(),
                status=backtest.status,
                progress_percent=backtest.progress_percent,
                start_time=backtest.start_time,
                end_time=backtest.end_time,
                final_equity=backtest.final_equity,
                total_trades=backtest.total_trades,
                win_rate=backtest.win_rate,
                total_return=backtest.total_return,
                error_message=backtest.error_message,
            )
            self.session.add(model)
        
        await self.session.commit()
        return backtest
    
    async def get_by_id(self, backtest_id: UUID) -> Optional[BacktestRun]:
        """Get backtest by ID."""
        
        result = await self.session.execute(
            select(BacktestRunModel).where(BacktestRunModel.id == backtest_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        return self._model_to_entity(model)
    
    async def get_by_user(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> List[BacktestRun]:
        """Get backtests for user."""
        
        result = await self.session.execute(
            select(BacktestRunModel)
            .where(BacktestRunModel.user_id == user_id)
            .order_by(BacktestRunModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        models = result.scalars().all()
        
        return [self._model_to_entity(m) for m in models]
    
    async def get_by_strategy(
        self,
        strategy_id: UUID,
        limit: int = 50,
    ) -> List[BacktestRun]:
        """Get backtests for strategy."""
        
        result = await self.session.execute(
            select(BacktestRunModel)
            .where(BacktestRunModel.strategy_id == strategy_id)
            .order_by(BacktestRunModel.created_at.desc())
            .limit(limit)
        )
        models = result.scalars().all()
        
        return [self._model_to_entity(m) for m in models]
    
    async def get_by_symbol(
        self,
        symbol: str,
        limit: int = 50,
    ) -> List[BacktestRun]:
        """Get backtests for symbol."""
        
        result = await self.session.execute(
            select(BacktestRunModel)
            .where(BacktestRunModel.symbol == symbol)
            .order_by(BacktestRunModel.created_at.desc())
            .limit(limit)
        )
        models = result.scalars().all()
        
        return [self._model_to_entity(m) for m in models]
    
    async def delete(self, backtest_id: UUID) -> bool:
        """Delete backtest."""
        
        result = await self.session.execute(
            select(BacktestRunModel).where(BacktestRunModel.id == backtest_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            return False
        
        await self.session.delete(model)
        await self.session.commit()
        return True
    
    async def count_by_user(self, user_id: UUID) -> int:
        """Count backtests for user."""
        
        result = await self.session.execute(
            select(func.count()).select_from(BacktestRunModel).where(BacktestRunModel.user_id == user_id)
        )
        return result.scalar_one()
    
    async def get_running_backtests(self, user_id: Optional[UUID] = None) -> List[BacktestRun]:
        """Get currently running backtests."""
        
        query = select(BacktestRunModel).where(
            BacktestRunModel.status.in_([BacktestStatus.PENDING, BacktestStatus.RUNNING])
        )
        
        if user_id:
            query = query.where(BacktestRunModel.user_id == user_id)
        
        result = await self.session.execute(query)
        models = result.scalars().all()
        
        return [self._model_to_entity(m) for m in models]
    
    def _model_to_entity(self, model: BacktestRunModel) -> BacktestRun:
        """Convert database model to domain entity."""
        
        from ...domain.backtesting import BacktestConfig
        
        config = BacktestConfig(**model.config)
        
        return BacktestRun(
            id=model.id,
            user_id=model.user_id,
            strategy_id=model.strategy_id,
            config=config,
            status=model.status,
            progress_percent=model.progress_percent,
            start_time=model.start_time,
            end_time=model.end_time,
            final_equity=model.final_equity,
            total_trades=model.total_trades,
            win_rate=model.win_rate,
            total_return=model.total_return,
            error_message=model.error_message,
        )

    # ===== PHASE 3 METHODS =====
    
    async def get_backtest_trades(
        self,
        backtest_id: UUID,
        page: int = 1,
        limit: int = 100,
        symbol: Optional[str] = None,
        side: Optional[str] = None,
        min_pnl: Optional[float] = None,
        max_pnl: Optional[float] = None,
    ) -> List[BacktestTradeModel]:
        """Get backtest trades with filtering and pagination."""
        
        # First get the result_id for this backtest
        result_query = select(BacktestResultModel.id).where(
            BacktestResultModel.run_id == backtest_id
        )
        result_result = await self.session.execute(result_query)
        result_id = result_result.scalar_one_or_none()
        
        if not result_id:
            return []
        
        # Build trades query with filters
        query = select(BacktestTradeModel).where(
            BacktestTradeModel.result_id == result_id
        )
        
        if symbol:
            query = query.where(BacktestTradeModel.symbol == symbol)
            
        if side:
            # Map side to direction
            direction = "LONG" if side.lower() == "buy" else "SHORT"
            query = query.where(BacktestTradeModel.direction == direction)
            
        if min_pnl is not None:
            query = query.where(BacktestTradeModel.net_pnl >= min_pnl)
            
        if max_pnl is not None:
            query = query.where(BacktestTradeModel.net_pnl <= max_pnl)
        
        # Add ordering and pagination
        query = query.order_by(desc(BacktestTradeModel.entry_time))
        query = query.limit(limit).offset((page - 1) * limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def count_backtest_trades(
        self,
        backtest_id: UUID,
        symbol: Optional[str] = None,
        side: Optional[str] = None,
        min_pnl: Optional[float] = None,
        max_pnl: Optional[float] = None,
    ) -> int:
        """Count backtest trades with filters."""
        
        # First get the result_id for this backtest
        result_query = select(BacktestResultModel.id).where(
            BacktestResultModel.run_id == backtest_id
        )
        result_result = await self.session.execute(result_query)
        result_id = result_result.scalar_one_or_none()
        
        if not result_id:
            return 0
        
        # Build count query with filters
        query = select(func.count()).select_from(BacktestTradeModel).where(
            BacktestTradeModel.result_id == result_id
        )
        
        if symbol:
            query = query.where(BacktestTradeModel.symbol == symbol)
            
        if side:
            direction = "LONG" if side.lower() == "buy" else "SHORT"
            query = query.where(BacktestTradeModel.direction == direction)
            
        if min_pnl is not None:
            query = query.where(BacktestTradeModel.net_pnl >= min_pnl)
            
        if max_pnl is not None:
            query = query.where(BacktestTradeModel.net_pnl <= max_pnl)
        
        result = await self.session.execute(query)
        return result.scalar_one()
    
    async def get_equity_curve(self, backtest_id: UUID) -> List[dict]:
        """Get equity curve points for backtest."""
        
        # Get result_id
        result_query = select(BacktestResultModel).where(
            BacktestResultModel.run_id == backtest_id
        )
        result_result = await self.session.execute(result_query)
        backtest_result = result_result.scalar_one_or_none()
        
        if not backtest_result or not backtest_result.equity_curve:
            return []
        
        # Parse equity curve from JSON stored data
        equity_data = backtest_result.equity_curve
        if isinstance(equity_data, str):
            import json
            equity_data = json.loads(equity_data)
        
        # Convert to standardized format
        equity_points = []
        for point in equity_data:
            # Create mock object with timestamp and equity
            mock_point = type('EquityPoint', (), {
                'timestamp': point.get('timestamp'),
                'equity': point.get('equity'),
                'drawdown_pct': point.get('drawdown', 0.0)
            })()
            equity_points.append(mock_point)
        
        return equity_points
    
    async def get_position_timeline(self, backtest_id: UUID) -> List[dict]:
        """Get position timeline data for backtest."""
        
        # Get trades and calculate position timeline
        trades = await self.get_backtest_trades(backtest_id, page=1, limit=10000)
        
        if not trades:
            return []
        
        # Calculate position timeline from trades
        position_timeline = []
        current_positions = 0
        current_exposure = 0.0
        
        # Group by time and calculate metrics
        for trade in sorted(trades, key=lambda t: t.entry_time):
            # Entry point
            if trade.direction == "LONG":
                current_positions += 1
            else:
                current_positions += 1  # Short position also counts as position
                
            exposure_value = float(trade.quantity) * float(trade.entry_price)
            current_exposure += exposure_value
            
            # Create mock timeline point
            mock_point = type('PositionTimelinePoint', (), {
                'timestamp': trade.entry_time,
                'open_positions_count': current_positions,
                'total_exposure': current_exposure,
                'margin_used': current_exposure * 0.1,  # Assume 10x leverage
                'unrealized_pnl': 0.0  # Would need real-time price data
            })()
            
            position_timeline.append(mock_point)
            
            # Exit point (if trade is closed)
            if trade.exit_time:
                current_positions -= 1
                current_exposure -= exposure_value
                
                exit_point = type('PositionTimelinePoint', (), {
                    'timestamp': trade.exit_time,
                    'open_positions_count': current_positions,
                    'total_exposure': current_exposure,
                    'margin_used': current_exposure * 0.1,
                    'unrealized_pnl': 0.0
                })()
                
                position_timeline.append(exit_point)
        
        return sorted(position_timeline, key=lambda p: p.timestamp)
