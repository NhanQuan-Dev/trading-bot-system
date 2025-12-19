"""
Portfolio Service - Tổng hợp và tính toán dữ liệu portfolio.

Mục đích:
- Tính toán summary portfolio: balance, equity, P&L, ROI.
- Aggregate data từ bots, positions, trades.

Liên quan đến file nào:
- Sử dụng models từ trading/infrastructure/persistence/models/ (BotModel, PositionModel, etc.).
- Sử dụng PriceCache từ trading/infrastructure/cache/price_cache.py.
- Khi gặp bug: Kiểm tra DB queries, verify calculations với Decimal, hoặc log trong shared/exceptions/.
"""

"""Portfolio Service for aggregating user portfolio data."""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload

from trading.infrastructure.persistence.models.bot_models import BotModel
from trading.infrastructure.persistence.models.trading_models import (
    PositionModel, TradeModel, OrderModel
)
from trading.infrastructure.cache.price_cache import PriceCache


class PortfolioService:
    """Service for portfolio data aggregation and calculations."""
    
    def __init__(self, session: AsyncSession, cache: Optional[PriceCache] = None):
        # Khởi tạo với DB session và cache (optional)
        self._session = session
        self._cache = cache
    
    async def get_portfolio_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get overall portfolio summary - Lấy tổng quan portfolio.
        
        Args:
            user_id: User UUID
            
        Returns:
            Portfolio summary with balance, equity, P&L, ROI
        """
        # Lấy tất cả bots active của user
        stmt = select(BotModel).where(
            and_(
                BotModel.user_id == user_id,
                BotModel.deleted_at.is_(None)
            )
        )
        result = await self._session.execute(stmt)
        bots = result.scalars().all()
        
        # Lấy tất cả positions mở
        positions_stmt = select(PositionModel).where(
            and_(
                PositionModel.user_id == user_id,
                PositionModel.status == "OPEN",
                PositionModel.deleted_at.is_(None)
            )
        )
        positions_result = await self._session.execute(positions_stmt)
        positions = positions_result.scalars().all()
        
        # Calculate total unrealized P&L from positions
        unrealized_pnl = Decimal("0")
        for position in positions:
            unrealized_pnl += position.unrealized_pnl or Decimal("0")
        
        # Get realized P&L from closed trades
        trades_stmt = select(
            func.sum(TradeModel.realized_pnl).label("total_realized_pnl")
        ).where(
            and_(
                TradeModel.user_id == user_id,
                TradeModel.deleted_at.is_(None)
            )
        )
        trades_result = await self._session.execute(trades_stmt)
        realized_pnl = trades_result.scalar() or Decimal("0")
        
        # Calculate total balance (simplified - sum from bot configs)
        total_balance = Decimal("0")
        for bot in bots:
            config = bot.configuration
            if config and "quote_quantity" in config:
                total_balance += Decimal(str(config["quote_quantity"]))
        
        # Calculate equity
        total_equity = total_balance + unrealized_pnl
        
        # Calculate ROI
        roi = Decimal("0")
        if total_balance > 0:
            roi = ((realized_pnl + unrealized_pnl) / total_balance * 100).quantize(Decimal("0.01"))
        
        return {
            "total_balance": float(total_balance),
            "total_equity": float(total_equity),
            "unrealized_pnl": float(unrealized_pnl),
            "realized_pnl": float(realized_pnl),
            "total_pnl": float(realized_pnl + unrealized_pnl),
            "roi": float(roi),
            "active_bots": len([b for b in bots if b.status == "ACTIVE"]),
            "open_positions": len(positions),
            "updated_at": datetime.utcnow().isoformat()
        }
    
    async def get_portfolio_balance(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get current balance across all exchanges.
        
        Args:
            user_id: User UUID
            
        Returns:
            List of balance by exchange and asset
        """
        # Get all open positions to calculate locked balance
        stmt = select(PositionModel).where(
            and_(
                PositionModel.user_id == user_id,
                PositionModel.status == "OPEN",
                PositionModel.deleted_at.is_(None)
            )
        ).options(selectinload(PositionModel.exchange))
        
        result = await self._session.execute(stmt)
        positions = result.scalars().all()
        
        # Aggregate by exchange and asset
        balance_map = {}
        for position in positions:
            exchange_name = position.exchange.name if position.exchange else "Unknown"
            # Extract base asset from symbol (e.g., BTC from BTCUSDT)
            symbol = position.symbol
            base_asset = symbol[:-4] if symbol.endswith("USDT") else symbol
            
            key = f"{exchange_name}_{base_asset}"
            if key not in balance_map:
                balance_map[key] = {
                    "exchange": exchange_name,
                    "asset": base_asset,
                    "free": Decimal("0"),
                    "locked": Decimal("0"),
                    "total": Decimal("0")
                }
            
            # Position quantity is locked
            locked = abs(position.quantity)
            balance_map[key]["locked"] += locked
            balance_map[key]["total"] += locked
        
        # Convert to list
        balances = []
        for balance in balance_map.values():
            balances.append({
                "exchange": balance["exchange"],
                "asset": balance["asset"],
                "free": float(balance["free"]),
                "locked": float(balance["locked"]),
                "total": float(balance["total"])
            })
        
        return balances
    
    async def get_daily_pnl(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get daily P&L chart data.
        
        Args:
            user_id: User UUID
            days: Number of days to retrieve (default 30)
            
        Returns:
            List of daily P&L data
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Query trades grouped by date
        stmt = select(
            func.date(TradeModel.created_at).label("date"),
            func.sum(TradeModel.realized_pnl).label("daily_pnl"),
            func.count(TradeModel.id).label("trades_count")
        ).where(
            and_(
                TradeModel.user_id == user_id,
                TradeModel.created_at >= start_date,
                TradeModel.deleted_at.is_(None)
            )
        ).group_by(
            func.date(TradeModel.created_at)
        ).order_by(
            func.date(TradeModel.created_at)
        )
        
        result = await self._session.execute(stmt)
        rows = result.all()
        
        # Calculate cumulative P&L
        cumulative_pnl = Decimal("0")
        daily_data = []
        for row in rows:
            daily_pnl = row.daily_pnl or Decimal("0")
            cumulative_pnl += daily_pnl
            
            daily_data.append({
                "date": row.date.isoformat(),
                "pnl": float(daily_pnl),
                "cumulative_pnl": float(cumulative_pnl),
                "trades_count": row.trades_count
            })
        
        return daily_data
    
    async def get_monthly_pnl(self, user_id: str, months: int = 12) -> List[Dict[str, Any]]:
        """
        Get monthly P&L summary.
        
        Args:
            user_id: User UUID
            months: Number of months to retrieve
            
        Returns:
            List of monthly P&L data
        """
        start_date = datetime.utcnow() - timedelta(days=months * 30)
        
        # Query trades grouped by month
        stmt = select(
            func.date_trunc('month', TradeModel.created_at).label("month"),
            func.sum(TradeModel.realized_pnl).label("total_pnl"),
            func.count(TradeModel.id).label("total_trades"),
            func.sum(
                func.case((TradeModel.realized_pnl > 0, 1), else_=0)
            ).label("win_trades"),
            func.sum(
                func.case((TradeModel.realized_pnl < 0, 1), else_=0)
            ).label("loss_trades")
        ).where(
            and_(
                TradeModel.user_id == user_id,
                TradeModel.created_at >= start_date,
                TradeModel.deleted_at.is_(None)
            )
        ).group_by(
            func.date_trunc('month', TradeModel.created_at)
        ).order_by(
            func.date_trunc('month', TradeModel.created_at)
        )
        
        result = await self._session.execute(stmt)
        rows = result.all()
        
        monthly_data = []
        for row in rows:
            total_pnl = row.total_pnl or Decimal("0")
            win_trades = row.win_trades or 0
            loss_trades = row.loss_trades or 0
            total_trades = row.total_trades or 0
            
            win_rate = Decimal("0")
            if total_trades > 0:
                win_rate = (Decimal(win_trades) / Decimal(total_trades) * 100).quantize(Decimal("0.01"))
            
            monthly_data.append({
                "month": row.month.strftime("%Y-%m"),
                "total_pnl": float(total_pnl),
                "total_trades": total_trades,
                "win_trades": win_trades,
                "loss_trades": loss_trades,
                "win_rate": float(win_rate)
            })
        
        return monthly_data
    
    async def get_portfolio_exposure(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get current market exposure by asset.
        
        Args:
            user_id: User UUID
            
        Returns:
            List of asset exposure data
        """
        # Get all open positions
        stmt = select(PositionModel).where(
            and_(
                PositionModel.user_id == user_id,
                PositionModel.status == "OPEN",
                PositionModel.deleted_at.is_(None)
            )
        )
        
        result = await self._session.execute(stmt)
        positions = result.scalars().all()
        
        # Calculate total exposure
        total_exposure = Decimal("0")
        asset_exposure = {}
        
        for position in positions:
            # Extract base asset
            symbol = position.symbol
            base_asset = symbol[:-4] if symbol.endswith("USDT") else symbol
            
            # Calculate position value
            position_value = abs(position.quantity * position.entry_price)
            total_exposure += position_value
            
            if base_asset not in asset_exposure:
                asset_exposure[base_asset] = {
                    "asset": base_asset,
                    "value": Decimal("0"),
                    "positions_count": 0
                }
            
            asset_exposure[base_asset]["value"] += position_value
            asset_exposure[base_asset]["positions_count"] += 1
        
        # Calculate percentages
        exposure_data = []
        for asset_data in asset_exposure.values():
            percentage = Decimal("0")
            if total_exposure > 0:
                percentage = (asset_data["value"] / total_exposure * 100).quantize(Decimal("0.01"))
            
            exposure_data.append({
                "asset": asset_data["asset"],
                "value": float(asset_data["value"]),
                "percentage": float(percentage),
                "positions_count": asset_data["positions_count"]
            })
        
        # Sort by value descending
        exposure_data.sort(key=lambda x: x["value"], reverse=True)
        
        return exposure_data
    
    async def get_equity_curve(self, user_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get historical equity curve.
        
        Args:
            user_id: User UUID
            days: Number of days
            
        Returns:
            List of equity curve data points
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Get trades ordered by time
        stmt = select(TradeModel).where(
            and_(
                TradeModel.user_id == user_id,
                TradeModel.created_at >= start_date,
                TradeModel.deleted_at.is_(None)
            )
        ).order_by(TradeModel.created_at)
        
        result = await self._session.execute(stmt)
        trades = result.scalars().all()
        
        # Get initial equity (from portfolio summary)
        summary = await self.get_portfolio_summary(user_id)
        initial_equity = Decimal(str(summary["total_balance"]))
        
        # Calculate equity at each trade
        equity_curve = []
        current_equity = initial_equity
        peak_equity = initial_equity
        
        for trade in trades:
            realized_pnl = trade.realized_pnl or Decimal("0")
            current_equity += realized_pnl
            
            # Track peak for drawdown calculation
            if current_equity > peak_equity:
                peak_equity = current_equity
            
            # Calculate drawdown
            drawdown = Decimal("0")
            if peak_equity > 0:
                drawdown = ((peak_equity - current_equity) / peak_equity * 100).quantize(Decimal("0.01"))
            
            equity_curve.append({
                "timestamp": trade.created_at.isoformat(),
                "equity": float(current_equity),
                "drawdown": float(drawdown)
            })
        
        return equity_curve
    
    async def get_all_positions(self, user_id: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """
        Get all open positions summary.
        
        Args:
            user_id: User UUID
            limit: Page limit
            offset: Page offset
            
        Returns:
            Paginated positions data
        """
        # Count total
        count_stmt = select(func.count(PositionModel.id)).where(
            and_(
                PositionModel.user_id == user_id,
                PositionModel.status == "OPEN",
                PositionModel.deleted_at.is_(None)
            )
        )
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar() or 0
        
        # Get positions
        stmt = select(PositionModel).where(
            and_(
                PositionModel.user_id == user_id,
                PositionModel.status == "OPEN",
                PositionModel.deleted_at.is_(None)
            )
        ).options(
            selectinload(PositionModel.bot),
            selectinload(PositionModel.exchange)
        ).order_by(
            desc(PositionModel.opened_at)
        ).limit(limit).offset(offset)
        
        result = await self._session.execute(stmt)
        positions = result.scalars().all()
        
        positions_data = []
        for position in positions:
            # Get current price (simplified - use entry price as placeholder)
            current_price = position.current_price or position.entry_price
            
            positions_data.append({
                "id": str(position.id),
                "bot_id": str(position.bot_id) if position.bot_id else None,
                "bot_name": position.bot.name if position.bot else None,
                "symbol": position.symbol,
                "side": position.side,
                "quantity": float(position.quantity),
                "entry_price": float(position.entry_price),
                "current_price": float(current_price),
                "unrealized_pnl": float(position.unrealized_pnl or Decimal("0")),
                "unrealized_pnl_pct": float(position.unrealized_pnl_pct or Decimal("0")),
                "opened_at": position.opened_at.isoformat()
            })
        
        return {
            "positions": positions_data,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    async def get_performance_metrics(self, user_id: str) -> Dict[str, Any]:
        """
        Get performance metrics.
        
        Args:
            user_id: User UUID
            
        Returns:
            Performance metrics (Sharpe, Sortino, max drawdown, win rate, profit factor)
        """
        # Get all trades
        stmt = select(TradeModel).where(
            and_(
                TradeModel.user_id == user_id,
                TradeModel.deleted_at.is_(None)
            )
        ).order_by(TradeModel.created_at)
        
        result = await self._session.execute(stmt)
        trades = result.scalars().all()
        
        if not trades:
            return {
                "sharpe_ratio": 0.0,
                "sortino_ratio": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0
            }
        
        # Calculate metrics
        returns = [float(t.realized_pnl or 0) for t in trades]
        positive_returns = [r for r in returns if r > 0]
        negative_returns = [r for r in returns if r < 0]
        
        # Win rate
        total_trades = len(trades)
        winning_trades = len(positive_returns)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Profit factor
        gross_profit = sum(positive_returns) if positive_returns else 0
        gross_loss = abs(sum(negative_returns)) if negative_returns else 0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
        
        # Sharpe ratio (simplified)
        if len(returns) > 1:
            import statistics
            mean_return = statistics.mean(returns)
            std_dev = statistics.stdev(returns)
            sharpe_ratio = (mean_return / std_dev) if std_dev > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Sortino ratio (downside deviation only)
        if negative_returns:
            import statistics
            mean_return = statistics.mean(returns)
            downside_dev = statistics.stdev(negative_returns)
            sortino_ratio = (mean_return / downside_dev) if downside_dev > 0 else 0
        else:
            sortino_ratio = 0
        
        # Max drawdown
        equity_curve = await self.get_equity_curve(user_id, days=365)
        max_drawdown = max([d["drawdown"] for d in equity_curve], default=0)
        
        return {
            "sharpe_ratio": round(sharpe_ratio, 2),
            "sortino_ratio": round(sortino_ratio, 2),
            "max_drawdown": round(max_drawdown, 2),
            "win_rate": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2)
        }
    
    async def get_trading_metrics(self, user_id: str) -> Dict[str, Any]:
        """
        Get key trading metrics.
        
        Args:
            user_id: User UUID
            
        Returns:
            Trading metrics
        """
        stmt = select(
            func.count(TradeModel.id).label("total_trades"),
            func.avg(
                func.case((TradeModel.realized_pnl > 0, TradeModel.realized_pnl), else_=None)
            ).label("avg_profit"),
            func.avg(
                func.case((TradeModel.realized_pnl < 0, TradeModel.realized_pnl), else_=None)
            ).label("avg_loss"),
            func.max(TradeModel.realized_pnl).label("largest_win"),
            func.min(TradeModel.realized_pnl).label("largest_loss")
        ).where(
            and_(
                TradeModel.user_id == user_id,
                TradeModel.deleted_at.is_(None)
            )
        )
        
        result = await self._session.execute(stmt)
        row = result.one()
        
        return {
            "total_trades": row.total_trades or 0,
            "avg_profit": float(row.avg_profit or 0),
            "avg_loss": float(row.avg_loss or 0),
            "largest_win": float(row.largest_win or 0),
            "largest_loss": float(row.largest_loss or 0)
        }
    
    async def get_trade_distribution(self, user_id: str, bins: int = 20) -> Dict[str, Any]:
        """
        Get win/loss distribution chart data.
        
        Args:
            user_id: User UUID
            bins: Number of histogram bins
            
        Returns:
            Distribution data
        """
        # Get all trade P&Ls
        stmt = select(TradeModel.realized_pnl).where(
            and_(
                TradeModel.user_id == user_id,
                TradeModel.deleted_at.is_(None),
                TradeModel.realized_pnl.isnot(None)
            )
        )
        
        result = await self._session.execute(stmt)
        pnls = [float(row[0]) for row in result.all()]
        
        if not pnls:
            return {"bins": [], "frequencies": []}
        
        # Create histogram
        import numpy as np
        frequencies, bin_edges = np.histogram(pnls, bins=bins)
        
        # Convert to lists
        bin_centers = [(bin_edges[i] + bin_edges[i+1]) / 2 for i in range(len(bin_edges)-1)]
        
        return {
            "bins": [round(b, 2) for b in bin_centers],
            "frequencies": frequencies.tolist()
        }
    
    async def get_drawdown_curve(self, user_id: str, days: int = 90) -> List[Dict[str, Any]]:
        """
        Get drawdown over time.
        
        Args:
            user_id: User UUID
            days: Number of days
            
        Returns:
            Drawdown curve data
        """
        equity_curve = await self.get_equity_curve(user_id, days=days)
        
        # Calculate underwater days
        drawdown_data = []
        underwater_days = 0
        
        for point in equity_curve:
            if point["drawdown"] > 0:
                underwater_days += 1
            else:
                underwater_days = 0
            
            drawdown_data.append({
                "date": point["timestamp"][:10],  # Extract date only
                "drawdown_pct": point["drawdown"],
                "underwater_days": underwater_days
            })
        
        return drawdown_data
