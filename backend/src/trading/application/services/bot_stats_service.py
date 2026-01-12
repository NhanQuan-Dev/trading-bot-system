"""Bot Stats Service - Updates bot statistics on trade close events."""
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import uuid

from ...infrastructure.persistence.models.bot_models import BotModel



print("DEBUG: BotStatsService module LOADED (patched version)")
logger = logging.getLogger(__name__)



class BotStatsService:
    """
    Service to update bot cumulative statistics on trade close.
    
    Called when a position is closed (PositionClosedEvent).
    Updates:
        - total_pnl
        - total_trades
        - winning_trades / losing_trades
        - win/loss streaks
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def update_stats_on_trade_close(
        self, 
        bot_id: str, 
        realized_pnl: Decimal
    ) -> bool:
        """
        Update bot stats when a trade (position) is closed.
        
        Args:
            bot_id: Bot UUID as string
            realized_pnl: Realized P&L from the closed trade
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            # Find bot
            bot_uuid = uuid.UUID(bot_id)
            result = await self._session.execute(
                select(BotModel).where(BotModel.id == bot_uuid)
            )
            bot = result.scalar_one_or_none()
            
            if not bot:
                logger.warning(f"Bot not found for stats update: {bot_id}")
                return False
            
            # Determine if trade is winning or losing
            is_winning = realized_pnl > 0
            
            # --- SELF-HEALING: Recalculate from Trade History ---
            # Instead of incrementing, we re-aggregate to ensure consistency
            from ...infrastructure.persistence.models.trading_models import TradeModel
            from sqlalchemy import func, case
            
            stats_stmt = select(
                func.count(TradeModel.id).label("total_trades"),
                func.sum(TradeModel.pnl).label("total_pnl"),
                func.sum(case((TradeModel.pnl > 0, 1), else_=0)).label("winning_trades"),
                func.sum(case((TradeModel.pnl <= 0, 1), else_=0)).label("losing_trades")
            ).where(TradeModel.bot_id == bot_uuid)
            
            stats_result = await self._session.execute(stats_stmt)
            stats_row = stats_result.one()
            
            # Update cumulative stats with REAL values from DB
            bot.total_trades = stats_row.total_trades or 0
            bot.total_pnl = stats_row.total_pnl or Decimal("0")
            bot.winning_trades = stats_row.winning_trades or 0
            bot.losing_trades = stats_row.losing_trades or 0
            
            # --- CALCULATE STREAKS FROM TRADE HISTORY ---
            # Get all trades ordered by execution time to calculate accurate streaks
            trades_stmt = select(TradeModel.pnl).where(
                TradeModel.bot_id == bot_uuid
            ).order_by(TradeModel.executed_at.asc())
            
            trades_result = await self._session.execute(trades_stmt)
            all_trades = trades_result.scalars().all()
            
            # Calculate current and max streaks from trade history
            current_win_streak = 0
            current_loss_streak = 0
            max_win_streak = 0
            max_loss_streak = 0
            
            for pnl in all_trades:
                if pnl and pnl > 0:
                    # Winning trade
                    current_win_streak += 1
                    current_loss_streak = 0
                    if current_win_streak > max_win_streak:
                        max_win_streak = current_win_streak
                else:
                    # Losing trade (including zero)
                    current_loss_streak += 1
                    current_win_streak = 0
                    if current_loss_streak > max_loss_streak:
                        max_loss_streak = current_loss_streak
            
            # Update bot with calculated streaks
            bot.current_win_streak = current_win_streak
            bot.current_loss_streak = current_loss_streak
            bot.max_win_streak = max_win_streak
            bot.max_loss_streak = max_loss_streak
            
            # Flush changes
            await self._session.commit()
            
            logger.info(
                f"Updated bot stats for {bot_id} (Recalculated): "
                f"total_pnl={bot.total_pnl}, "
                f"total_trades={bot.total_trades}, "
                f"win_rate={self._calculate_win_rate(bot.winning_trades, bot.total_trades)}%, "
                f"streak={current_win_streak}W/{current_loss_streak}L"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update bot stats for {bot_id}: {e}")
            return False
    
    def _calculate_win_rate(self, winning_trades: int, total_trades: int) -> float:
        """Calculate win rate as percentage (0-100)."""
        if not total_trades or total_trades == 0:
            return 0.0
        return round((winning_trades / total_trades) * 100, 2)
    
    async def get_bot_stats(self, bot_id: str) -> Optional[dict]:
        """
        Get current bot stats for WebSocket broadcast.
        
        Returns dict compatible with WebSocket message format.
        """
        try:
            bot_uuid = uuid.UUID(bot_id)
            result = await self._session.execute(
                select(BotModel).where(BotModel.id == bot_uuid)
            )
            bot = result.scalar_one_or_none()
            
            if not bot:
                return None
            
            total_trades = bot.total_trades or 0
            winning_trades = bot.winning_trades or 0
            
            return {
                "bot_id": str(bot.id),
                "total_pnl": str(bot.total_pnl or Decimal("0")),  # String for Decimal
                "win_rate": self._calculate_win_rate(winning_trades, total_trades),  # Already 0-100
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": bot.losing_trades or 0,
                "current_win_streak": bot.current_win_streak or 0,
                "current_loss_streak": bot.current_loss_streak or 0,
                "max_win_streak": bot.max_win_streak or 0,
                "max_loss_streak": bot.max_loss_streak or 0,
            }
            
        except Exception as e:
            logger.error(f"Failed to get bot stats for {bot_id}: {e}")
            return None

    async def get_period_stats(self, bot_id: str) -> Optional[dict]:
        """
        Get stats for multiple time periods.
        
        Returns dict with period keys containing:
        - pnl: Total P&L for the period
        - trades: Number of trades
        - wins: Number of winning trades (P&L > 0)
        - losses: Number of losing trades (P&L <= 0)
        
        Periods: today, yesterday, this_week, last_week, this_month, last_month
        """
        from datetime import datetime, timedelta
        from sqlalchemy import func, case, and_
        from ...infrastructure.persistence.models.trading_models import TradeModel
        
        try:
            bot_uuid = uuid.UUID(bot_id)
            
            # Get current date boundaries (using UTC for consistency)
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            yesterday_start = today_start - timedelta(days=1)
            
            # Week boundaries (Monday = 0)
            days_since_monday = now.weekday()
            this_week_start = today_start - timedelta(days=days_since_monday)
            last_week_start = this_week_start - timedelta(days=7)
            last_week_end = this_week_start
            
            # Month boundaries
            this_month_start = today_start.replace(day=1)
            # Last month: go back to first of current month, then subtract 1 day to get last month, then get first of that month
            last_month_end = this_month_start
            last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
            
            # Define period boundaries
            periods = {
                "today": (today_start, now),
                "yesterday": (yesterday_start, today_start),
                "this_week": (this_week_start, now),
                "last_week": (last_week_start, last_week_end),
                "this_month": (this_month_start, now),
                "last_month": (last_month_start, last_month_end),
            }
            
            result = {}
            
            for period_name, (start_time, end_time) in periods.items():
                # Query trades for this period
                stmt = select(
                    func.coalesce(func.sum(TradeModel.pnl), 0).label("total_pnl"),
                    func.count(TradeModel.id).label("total_trades"),
                    func.coalesce(func.sum(case((TradeModel.pnl > 0, 1), else_=0)), 0).label("wins"),
                    func.coalesce(func.sum(case((TradeModel.pnl <= 0, 1), else_=0)), 0).label("losses"),
                ).where(
                    and_(
                        TradeModel.bot_id == bot_uuid,
                        TradeModel.executed_at >= start_time,
                        TradeModel.executed_at < end_time,
                    )
                )
                
                query_result = await self._session.execute(stmt)
                row = query_result.one()
                
                result[period_name] = {
                    "pnl": float(row.total_pnl or 0),
                    "trades": int(row.total_trades or 0),
                    "wins": int(row.wins or 0),
                    "losses": int(row.losses or 0),
                }
            
            logger.debug(f"Period stats for bot {bot_id}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get period stats for {bot_id}: {e}")
            return None

