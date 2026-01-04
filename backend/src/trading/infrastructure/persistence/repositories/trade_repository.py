"""Trade repository implementation."""
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from trading.domain.trade import Trade
from trading.domain.order import OrderSide
from ..models.trading_models import TradeModel

logger = logging.getLogger(__name__)

class TradeRepository:
    """Repository for managing Trade entities."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        
    def _to_domain(self, model: TradeModel) -> Trade:
        """Convert TradeModel to Trade domain entity."""
        return Trade(
            id=model.id,
            order_id=model.order_id,
            bot_id=model.bot_id,
            user_id=model.user_id,
            symbol=model.symbol,
            side=OrderSide(model.side),
            price=model.price,
            quantity=model.quantity,
            commission=model.commission,
            commission_asset=model.commission_asset,
            realized_pnl=model.realized_pnl,
            executed_at=model.created_at, # TradeModel uses created_at as execution time normally?
            exchange_trade_id=model.exchange_trade_id
        )

    async def create(self, trade: Trade) -> Trade:
        """Create a new trade."""
        # We need to fetch the order to get position_id and exchange_id
        # as they are required foreign keys in TradeModel but not present in Trade entity
        from ..models.trading_models import OrderModel
        stmt = select(OrderModel).where(OrderModel.id == trade.order_id)
        result = await self.session.execute(stmt)
        order_model = result.scalar_one_or_none()
        
        if not order_model:
            raise ValueError(f"Order {trade.order_id} not found for trade creation")
            
        model = TradeModel(
            id=trade.id,
            user_id=trade.user_id,
            bot_id=trade.bot_id,
            order_id=trade.order_id,
            position_id=order_model.position_id, # Required
            exchange_id=order_model.exchange_id, # Required
            symbol=trade.symbol,
            side=trade.side.value,
            price=trade.price,
            quantity=trade.quantity,
            # Map commission (Entity) -> fee (Model)
            fee=trade.commission,
            fee_currency=trade.commission_asset,
            pnl=trade.realized_pnl, # Map realized_pnl -> pnl? Model has pnl and realized_pnl columns?
            # Model has `pnl` (Total P&L?) and `realized_pnl` is on PositionModel. 
            # TradeModel has `pnl` column. Let's use that.
            status="SUCCESS",
            executed_at=trade.executed_at,
            exchange_trade_id=trade.exchange_trade_id
        )
        
        self.session.add(model)
        await self.session.commit()
        
        # === REAL-TIME STATS UPDATE ===
        # After trade is committed, recalculate stats and broadcast via WebSocket
        if trade.bot_id:
            try:
                # Use absolute imports to avoid path confusion
                from trading.application.services.bot_stats_service import BotStatsService
                from trading.infrastructure.websocket.websocket_manager import websocket_manager
                from decimal import Decimal
                
                # Recalculate stats (self-healing aggregation from trades table)
                stats_service = BotStatsService(self.session)
                await stats_service.update_stats_on_trade_close(
                    bot_id=str(trade.bot_id),
                    realized_pnl=trade.realized_pnl or Decimal("0")
                )
                
                # Broadcast updated stats via WebSocket
                stats = await stats_service.get_bot_stats(str(trade.bot_id))
                if stats:
                    await websocket_manager.broadcast_bot_stats_update(
                        user_id=str(trade.user_id),
                        bot_id=str(trade.bot_id),
                        stats=stats
                    )
                    logger.info(f"Real-time stats broadcasted for bot {trade.bot_id} after trade creation")
            except Exception as e:
                # Don't fail trade creation if stats update fails
                logger.error(f"Failed to update/broadcast stats after trade creation: {e}")
        
        return trade
        
    async def get_by_bot_id(self, bot_id: UUID) -> List[Trade]:
        """Get all trades for a bot."""
        stmt = select(TradeModel).where(TradeModel.bot_id == bot_id)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]
        
    async def get_by_order_id(self, order_id: UUID) -> List[Trade]:
        """Get all trades for an order."""
        stmt = select(TradeModel).where(TradeModel.order_id == order_id)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

