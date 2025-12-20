"""SQLAlchemy repository implementation for backtests."""

import logging
from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime
import dataclasses
from dataclasses import asdict
from sqlalchemy import select, and_, func, desc, delete
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


from decimal import Decimal

def _convert_decimals(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _convert_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_decimals(i) for i in obj]
    return obj


class BacktestRepository(IBacktestRepository):
    """SQLAlchemy implementation of backtest repository."""
    
    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session
    
    def _clamp_decimal(self, value, max_val: float = 999999.9999, min_val: float = -999999.9999) -> Decimal:
        """Clamp decimal value to prevent DECIMAL(10,4) overflow.
        
        Database columns with DECIMAL(10,4) can only store values between -999999.9999 and 999999.9999.
        Values outside this range cause NumericValueOutOfRangeError.
        """
        if value is None:
            return Decimal("0")
        try:
            float_val = float(value)
            # Handle infinity and NaN
            if float_val != float_val or abs(float_val) == float('inf'):  # NaN or Inf
                return Decimal("0")
            clamped = max(min_val, min(max_val, float_val))
            return Decimal(str(round(clamped, 4)))
        except (ValueError, TypeError, OverflowError):
            return Decimal("0")
    
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
            existing.start_time = backtest.started_at
            existing.end_time = backtest.completed_at
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
                symbol=backtest.symbol,
                timeframe=backtest.timeframe,
                start_date=backtest.start_date,
                end_date=backtest.end_date,
                initial_capital=backtest.config.initial_capital,
                config=_convert_decimals(asdict(backtest.config)),
                status=backtest.status,
                progress_percent=backtest.progress_percent,
                start_time=backtest.started_at,
                end_time=backtest.completed_at,
                final_equity=backtest.final_equity,
                total_trades=backtest.total_trades,
                win_rate=backtest.win_rate,
                total_return=backtest.total_return,
                error_message=backtest.error_message,
            )
            self.session.add(model)
        
        # Save results if available
        if backtest.results:
            await self._save_results(backtest)
            
            # Update summary fields on run model from results
            if existing:
                existing.final_equity = backtest.results.final_equity
                existing.total_trades = backtest.results.total_trades
                existing.win_rate = backtest.results.win_rate
                existing.total_return = backtest.results.total_return
            elif self.session.new:
                # If we just added the model (it's new), update it
                for obj in self.session.new:
                    if isinstance(obj, BacktestRunModel) and obj.id == backtest.id:
                        obj.final_equity = backtest.results.final_equity
                        obj.total_trades = backtest.results.total_trades
                        obj.win_rate = backtest.results.win_rate
                        obj.total_return = backtest.results.total_return
        
        await self.session.commit()
        return backtest
    
    async def _save_results(self, backtest: BacktestRun) -> None:
        """Save backtest results and trades."""
        results = backtest.results
        if not results:
            return

        # Check for existing result
        result_query = select(BacktestResultModel).where(
            BacktestResultModel.backtest_run_id == backtest.id
        )
        res = await self.session.execute(result_query)
        result_model = res.scalar_one_or_none()
        
        # Helper to serialize JSON fields safely
        def to_json(obj):
            if isinstance(obj, BacktestTrade):
                d = _convert_decimals(dataclasses.asdict(obj))
                # Add calculated fields required by schema
                d['quantity'] = d.get('entry_quantity')
                d['commission'] = float(obj.entry_commission + obj.exit_commission)
                d['slippage'] = float(obj.entry_slippage + obj.exit_slippage)
                d['is_winner'] = obj.is_winner
                d['duration_seconds'] = int(obj.duration_seconds) if obj.duration_seconds is not None else None
                return d
                
            if hasattr(obj, 'to_dict'):
                return _convert_decimals(obj.to_dict())
            if dataclasses.is_dataclass(obj):
                return _convert_decimals(dataclasses.asdict(obj))
            return _convert_decimals(obj)
            
        from ...domain.backtesting import BacktestTrade
            
        # Serialize complex fields
        equity_curve_json = [to_json(p) for p in results.equity_curve]
        trades_json = [to_json(t) for t in results.trades] # Summary list
        
        metrics = results.metrics
        
        if result_model:
            # Update existing
            result_model.initial_capital = results.initial_capital
            result_model.final_equity = results.final_equity
            result_model.peak_equity = results.peak_equity
            result_model.total_trades = results.total_trades
            result_model.winning_trades = results.winning_trades
            result_model.losing_trades = results.losing_trades
            result_model.total_return = results.total_return
            
            # Metrics
            if metrics:
                result_model.sharpe_ratio = metrics.sharpe_ratio
                result_model.sortino_ratio = metrics.sortino_ratio
                result_model.max_drawdown = metrics.max_drawdown
                result_model.win_rate = metrics.win_rate
                result_model.profit_factor = metrics.profit_factor
            
            result_model.equity_curve = equity_curve_json
            result_model.trades = trades_json
            
        else:
            # Create new result
            result_model = BacktestResultModel(
                backtest_run_id=backtest.id,
                initial_capital=results.initial_capital,
                final_equity=results.final_equity,
                peak_equity=results.peak_equity,
                total_trades=results.total_trades,
                winning_trades=results.winning_trades,
                losing_trades=results.losing_trades,
                total_return=self._clamp_decimal(results.total_return),
                equity_curve=equity_curve_json,
                trades=trades_json,
                
                # Default mandatory fields (clamped to prevent DECIMAL(10,4) overflow)
                annual_return=0,
                cagr=0,
                sharpe_ratio=0,
                sortino_ratio=0,
                calmar_ratio=0,
                max_drawdown=0,
                max_drawdown_duration_days=0,
                volatility=0,
                downside_deviation=0,
                win_rate=0,
                profit_factor=0,
                payoff_ratio=0,
                expected_value=0,
                average_trade_pnl=0,
                average_winning_trade=0,
                average_losing_trade=0,
                largest_winning_trade=0,
                largest_losing_trade=0,
                average_exposure_percent=0,
                risk_of_ruin=0
            )
            
            # Populate from metrics if available (all clamped to max DECIMAL(10,4))
            if metrics:
                result_model.sharpe_ratio = self._clamp_decimal(metrics.sharpe_ratio)
                result_model.sortino_ratio = self._clamp_decimal(metrics.sortino_ratio)
                result_model.calmar_ratio = self._clamp_decimal(metrics.calmar_ratio)
                result_model.max_drawdown = self._clamp_decimal(metrics.max_drawdown)
                result_model.win_rate = self._clamp_decimal(metrics.win_rate, max_val=99.99)  # DECIMAL(5,2)
                result_model.profit_factor = self._clamp_decimal(metrics.profit_factor)
                result_model.cagr = self._clamp_decimal(metrics.compound_annual_growth_rate)
                result_model.volatility = self._clamp_decimal(metrics.volatility)
            
            self.session.add(result_model)
            await self.session.flush() # Get ID
            
        # Save individual trades
        # First delete existing trades to avoid duplicates/updates complexity
        if result_model.id:
            await self.session.execute(
                delete(BacktestTradeModel).where(BacktestTradeModel.result_id == result_model.id)
            )
            
        # Create trade models
        for trade in results.trades:
            trade_model = BacktestTradeModel(
                result_id=result_model.id,
                id=trade.id,
                symbol=trade.symbol,
                direction=trade.direction.value if hasattr(trade.direction, 'value') else str(trade.direction),
                entry_price=trade.entry_price,
                exit_price=trade.exit_price or 0,
                quantity=trade.entry_quantity,
                entry_time=trade.entry_time,
                exit_time=trade.exit_time or trade.entry_time,
                gross_pnl=trade.gross_pnl,
                commission=trade.entry_commission + trade.exit_commission,
                slippage=trade.entry_slippage + trade.exit_slippage,
                net_pnl=trade.net_pnl,
                pnl_percent=trade.pnl_percent
            )
            self.session.add(trade_model)
    
    async def get_by_id(self, backtest_id: UUID) -> Optional[BacktestRun]:
        """Get backtest by ID."""
        
        result = await self.session.execute(
            select(BacktestRunModel)
            .options(selectinload(BacktestRunModel.strategy))
            .where(BacktestRunModel.id == backtest_id)
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
            .options(selectinload(BacktestRunModel.strategy))
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
            .options(selectinload(BacktestRunModel.strategy))
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
            .options(selectinload(BacktestRunModel.strategy))
            .where(BacktestRunModel.symbol == symbol)
            .order_by(BacktestRunModel.created_at.desc())
            .limit(limit)
        )
        models = result.scalars().all()
        
        return [self._model_to_entity(m) for m in models]

    async def get_results(self, backtest_id: UUID) -> Optional[Dict]:
        """Get detailed backtest results."""
        stmt = select(BacktestResultModel).where(BacktestResultModel.backtest_run_id == backtest_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        
        if not model:
            return None
            
        # Construct metrics from flattened columns
        metrics = {
            "total_return": model.total_return,
            "annual_return": model.annual_return,
            "compound_annual_growth_rate": model.cagr,
            "sharpe_ratio": model.sharpe_ratio or 0,
            "sortino_ratio": model.sortino_ratio or 0,
            "calmar_ratio": getattr(model, 'calmar_ratio', 0) or 0,
            "max_drawdown": model.max_drawdown,
            "max_drawdown_duration_days": model.max_drawdown_duration_days,
            "volatility": model.volatility,
            "downside_deviation": model.downside_deviation,
            "win_rate": model.win_rate,
            "profit_factor": model.profit_factor,
            "payoff_ratio": model.payoff_ratio,
            "expected_value": model.expected_value,
            "total_trades": model.total_trades,
            "winning_trades": model.winning_trades,
            "losing_trades": model.losing_trades,
            "break_even_trades": getattr(model, 'break_even_trades', 0),
            "average_trade_pnl": model.average_trade_pnl,
            "average_winning_trade": model.average_winning_trade,
            "average_losing_trade": model.average_losing_trade,
            "largest_winning_trade": model.largest_winning_trade,
            "largest_losing_trade": model.largest_losing_trade,
            "max_consecutive_wins": getattr(model, 'max_consecutive_wins', 0),
            "max_consecutive_losses": getattr(model, 'max_consecutive_losses', 0),
            "average_exposure_percent": model.average_exposure_percent,
            "max_simultaneous_positions": getattr(model, 'max_simultaneous_positions', 1),
            "risk_of_ruin": model.risk_of_ruin,
        }
        
        return {
            "initial_capital": model.initial_capital,
            "final_equity": model.final_equity,
            "peak_equity": model.peak_equity,
            "total_trades": model.total_trades,
            "performance_metrics": metrics,
            "equity_curve": model.equity_curve,
            "trades": model.trades
        }
    
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
        
        query = select(BacktestRunModel).options(selectinload(BacktestRunModel.strategy)).where(
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
            strategy_name=model.strategy.name if model.strategy else None,
            symbol=model.symbol,
            timeframe=model.timeframe,
            config=config,
            status=model.status,
            progress_percent=model.progress_percent,
            start_date=model.start_date,
            end_date=model.end_date,
            started_at=model.start_time,
            completed_at=model.end_time,
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
            BacktestResultModel.backtest_run_id == backtest_id
        )
        result_result = await self.session.execute(result_query)
        result_id = result_result.scalar_one_or_none()
        
        if not result_id:
            return []
        
        # Build trades query with filters
        
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
            BacktestResultModel.backtest_run_id == backtest_id
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
            BacktestResultModel.backtest_run_id == backtest_id
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
