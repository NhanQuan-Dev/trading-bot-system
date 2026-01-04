from typing import List, Dict, Any, Optional
import uuid
import asyncio
from datetime import datetime
from decimal import Decimal
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from trading.infrastructure.persistence.models.trading_models import PositionModel, OrderModel
from trading.infrastructure.persistence.models.bot_models import BotModel
from trading.infrastructure.persistence.repositories.bot_repository import BotRepository
from trading.infrastructure.persistence.repositories.order_repository import OrderRepository
from src.application.services.connection_service import ConnectionService
from trading.infrastructure.exchange.binance_adapter import BinanceAdapter
from trading.domain.order import (
    Order, OrderSide, OrderType, OrderStatus, TimeInForce,
    PositionSide, OrderQuantity, OrderPrice, WorkingType
)

logger = logging.getLogger(__name__)

class PositionService:
    """Service for managing proper real-time position syncing."""
    
    def __init__(
        self, 
        session: AsyncSession,
        bot_repository: BotRepository,
        connection_service: ConnectionService,
        order_repository: OrderRepository,
        update_order_status_use_case: Any # Type hint handled by import or Any to avoid circular
    ):
        self.session = session
        self.bot_repository = bot_repository
        self.connection_service = connection_service
        self.order_repository = order_repository
        self.update_order_status_use_case = update_order_status_use_case

    async def get_live_positions(self, bot_id: uuid.UUID) -> Dict[str, Any]:
        """
        Fetch live positions from Exchange, sync to DB, and return.
        
        Args:
            bot_id: Bot UUID
            
        Returns:
            Dict with positions list and total count
        """
        # 1. Get Bot info
        bot = await self.bot_repository.find_by_id(bot_id)
        if not bot:
            raise ValueError(f"Bot {bot_id} not found")
            
        if not bot.exchange_connection_id:
            raise ValueError(f"Bot {bot_id} has no exchange connection")

        # 2. Get Credentials
        creds = await self.connection_service.get_connection_credentials(
            str(bot.exchange_connection_id), 
            bot.user_id
        )
        
        # 3. Fetch from Exchange
        positions_from_exchange = []
        try:
            # Determine base URL
            base_url = "https://demo-fapi.binance.com" if creds["is_testnet"] else "https://fapi.binance.com"
            
            adapter = BinanceAdapter(
                api_key=creds["api_key"],
                api_secret=creds["api_secret"],
                base_url=base_url,
                testnet=creds["is_testnet"]
            )
            
            # Fetch account info (positions included)
            account_info = await asyncio.wait_for(
                adapter.get_account_info(),
                timeout=10.0
            )
            await adapter.close()
            
            # Filter positions for this symbol (Bot usually runs on one symbol)
            # Or if Bot supports multi-symbol, filter by Bot's configuration?
            # Current BotModel has `configuration.symbol`.
            # We should only sync positions relevant to this bot.
            # Filter positions for this symbol
            # Normalize symbols to ensure matching (e.g. BTC/USDT -> BTCUSDT)
            target_symbol = bot.configuration.symbol.replace("/", "").upper()
            
            positions_from_exchange = [
                p for p in account_info.positions 
                if p.symbol.replace("/", "").upper() == target_symbol and p.quantity > 0
            ]
            
        except Exception as e:
            logger.error(f"Failed to fetch positions from exchange: {e}")
            # If exchange fails, fallback to DB but mark as 'stale'? 
            # Or re-raise? 
            # User wants "Always update from exchange". So we should allow failure to be visible.
            # But maybe return DB cache with proper error handling?
            # For now, let's log and re-raise or return empty with error?
            # Better: re-raise to show error in UI "Failed to sync".
            raise ValueError(f"Failed to sync with exchange: {str(e)}")

        # 4. Sync with DB
        # Get existing DB positions
        stmt = select(PositionModel).where(
            and_(
                PositionModel.bot_id == bot_id,
                PositionModel.status == "OPEN",
                PositionModel.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(stmt)
        db_positions = result.scalars().all()
        db_pos_map = {f"{p.symbol}_{p.side}": p for p in db_positions}
        
        # Track synced symbols to identify closed ones
        synced_keys = set()
        
        for ex_pos in positions_from_exchange:
            key = f"{ex_pos.symbol}_{ex_pos.side}"
            synced_keys.add(key)
            
            if key in db_pos_map:
                # Update existing
                db_pos = db_pos_map[key]
                
                # Check for significant changes before update (optimization)
                db_pos.mark_price = ex_pos.mark_price
                db_pos.unrealized_pnl = ex_pos.unrealized_pnl
                
                # Update Quantity/Entry Price if changed (Partial fill or average down)
                db_pos.quantity = ex_pos.quantity
                db_pos.entry_price = ex_pos.entry_price
                
                # Calculate PnL %
                if ex_pos.entry_price and ex_pos.entry_price > 0:
                     # For Long: (Mark - Entry) / Entry
                     # For Short: (Entry - Mark) / Entry
                     diff = ex_pos.mark_price - ex_pos.entry_price
                     if ex_pos.side == "SHORT":
                         diff = -diff
                     db_pos.pnl_percent = (diff / ex_pos.entry_price) * 100
                
                db_pos.updated_at = datetime.utcnow()
                
            else:
                # Create new
                new_pos = PositionModel(
                    id=uuid.uuid4(),
                    bot_id=bot_id,
                    user_id=bot.user_id,
                    exchange_id=creds["exchange_id"],
                    symbol=ex_pos.symbol,
                    side=ex_pos.side,
                    quantity=ex_pos.quantity,
                    entry_price=ex_pos.entry_price,
                    mark_price=ex_pos.mark_price,
                    leverage=ex_pos.leverage,
                    unrealized_pnl=ex_pos.unrealized_pnl,
                    status="OPEN",
                    opened_at=datetime.utcnow(),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                    # Note: pnl_percent default is 0, we can calculate it too if needed or leave for update
                )
                if ex_pos.entry_price and ex_pos.entry_price > 0:
                     diff = ex_pos.mark_price - ex_pos.entry_price
                     if ex_pos.side == "SHORT":
                         diff = -diff
                     new_pos.pnl_percent = (diff / ex_pos.entry_price) * 100
                     
                self.session.add(new_pos)
        
        # Close positions that are in DB but not in Exchange
        for key, db_pos in db_pos_map.items():
            if key not in synced_keys:
                # Position is gone from exchange -> Closed
                db_pos.status = "CLOSED"
                db_pos.closed_at = datetime.utcnow()
                db_pos.updated_at = datetime.utcnow()
                # We don't know the exact exit price/pnl here without Trade History
                # But we mark it closed to keep UI accurate.
        
        await self.session.commit()
        
        # 5. Return formatted data
        # Re-fetch active only
        # Actually we can construct the list from what we just synced
        
        # Let's re-query to be safe and consistent
        stmt = select(PositionModel).where(
            and_(
                PositionModel.bot_id == bot_id,
                PositionModel.status == "OPEN",
                PositionModel.deleted_at.is_(None)
            )
        )
        result = await self.session.execute(stmt)
        final_positions = result.scalars().all()
        
        positions_data = []
        for position in final_positions:
            positions_data.append({
                "id": str(position.id),
                "symbol": position.symbol,
                "side": position.side,
                "quantity": float(position.quantity),
                "entry_price": float(position.entry_price),
                # Frontend expects 'current_price', utilize 'mark_price' from DB
                "current_price": float(position.mark_price or position.entry_price),
                "mark_price": float(position.mark_price or position.entry_price), # Match WebSocket field
                "unrealized_pnl": float(position.unrealized_pnl or 0),
                "unrealized_pnl_pct": float(position.pnl_percent or 0),
                "opened_at": position.opened_at.isoformat()
            })
            
        return {
            "positions": positions_data,
            "total": len(positions_data)
        }

    async def close_position(self, bot_id: uuid.UUID, symbol: str, side: str) -> Dict[str, Any]:
        """Close a specific position by symbol and side."""
        # 1. Get Bot info
        bot = await self.bot_repository.find_by_id(bot_id)
        if not bot:
            raise ValueError(f"Bot {bot_id} not found")

        if not bot.exchange_connection_id:
            raise ValueError(f"Bot {bot_id} has no exchange connection")

        # 2. Get Credentials
        creds = await self.connection_service.get_connection_credentials(
            str(bot.exchange_connection_id),
            bot.user_id
        )

        # 2.5 Force Sync to ensure DB is up to date
        await self.get_live_positions(bot_id)

        # 3. Get existing position details
        stmt = select(PositionModel).where(
            and_(
                PositionModel.bot_id == bot_id,
                PositionModel.symbol == symbol,
                PositionModel.side == side,
                PositionModel.status == "OPEN"
            )
        )
        result = await self.session.execute(stmt)
        position = result.scalar_one_or_none()
        
        if not position:
            # Debugging: List all open positions for this bot to see mismatch
            debug_stmt = select(PositionModel).where(
                and_(PositionModel.bot_id == bot_id, PositionModel.status == "OPEN")
            )
            debug_res = await self.session.execute(debug_stmt)
            all_pos = debug_res.scalars().all()
            available = [f"{p.symbol} {p.side}" for p in all_pos]
            logger.error(f"Position lookup failed. Searching for: {symbol} {side}. Available in DB: {available}")
            
            raise ValueError(f"Position not found for {symbol} {side}. Available: {available}")

        # 4. Prepare Order Data
        # Hedge Mode: Close Long -> Sell Short; Close Short -> Buy Long
        order_side = OrderSide.SELL if side == "LONG" else OrderSide.BUY
        position_side = PositionSide.LONG if side == "LONG" else PositionSide.SHORT
        
        quantity = Decimal(str(position.quantity))
        
        # Create Domain Order (Pending)
        # Generate Order ID and Client Order ID upfront
        order_id = uuid.uuid4()
        client_order_id = str(order_id)
        
        # Create Domain Order (Pending)
        new_order = Order(
            id=order_id,
            user_id=bot.user_id,
            bot_id=bot_id,
            exchange_connection_id=bot.exchange_connection_id,
            exchange_id=creds["exchange_id"],
            symbol=symbol,
            side=order_side,
            order_type=OrderType.MARKET,
            quantity=OrderQuantity(quantity),
            position_side=position_side,
            reduce_only=True,
            close_position=True,
            position_id=position.id, # Link to Position
            status=OrderStatus.PENDING,
            time_in_force=TimeInForce.GTC,
            client_order_id=client_order_id, # Saved to DB
            # CRITICAL: Save entry price in metadata for PnL calculation later
            meta_data={
                "entry_price": float(position.entry_price),
                "close_position_reason": "Manual Close API"
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Save to DB
        saved_order = await self.order_repository.create(new_order)
        
        try:
            # 5. Execute on Exchange
            base_url = "https://demo-fapi.binance.com" if creds["is_testnet"] else "https://fapi.binance.com"
            adapter = BinanceAdapter(
                api_key=creds["api_key"],
                api_secret=creds["api_secret"],
                base_url=base_url,
                testnet=creds["is_testnet"]
            )
            
            # NOTE: adapter.create_order expects specific args. 
            # We use common args mapping.
            exchange_response = await adapter.create_order(
                symbol=symbol,
                side=order_side.value,
                type=OrderType.MARKET.value,
                quantity=float(quantity),
                newClientOrderId=client_order_id, # Passed to Exchange
                # Hedge Mode params (CamalCase for API)
                positionSide=position_side.value
            )
            

            await adapter.close()

            
            # 6. Update Order with Exchange Info
            saved_order.exchange_order_id = str(exchange_response.get("orderId"))
            
            logger.info(f"Close Position Response for {symbol}: status={exchange_response.get('status')} (Order ID: {saved_order.id})")

            # If filled immediately, use the use case to trigger side effects (stats, trade record)
            if exchange_response.get("status") == "FILLED":
                # Get execution details
                executed_qty = Decimal(str(exchange_response.get("executedQty", quantity)))
                # For market orders, price might be in 'cummulativeQuoteQty' / 'executedQty' or 'avgPrice'
                # Binance Futures: 'avgPrice' is usually available in order response
                avg_price = Decimal(str(exchange_response.get("avgPrice", "0")))
                if avg_price == 0 and float(quantity) > 0:
                     # Try to derive from cumQuote if valid
                     cum_quote = Decimal(str(exchange_response.get("cumQuote", "0")))
                     if cum_quote > 0:
                         avg_price = cum_quote / executed_qty

                # Use the USE CASE to handle status update, verification, and STATS updates
                await self.update_order_status_use_case.execute(
                    user_id=bot.user_id,
                    order_id=saved_order.id,
                    new_status=OrderStatus.FILLED,
                    executed_quantity=executed_qty,
                    executed_price=avg_price,
                    # Commission is tricky, might default to 0 if not in response
                    # Usually better to wait for stream, but for immediate UI feedback we try best effort
                    commission=Decimal("0"), 
                    commission_asset="USDT" 
                )
            else:
                saved_order.status = OrderStatus.NEW
                await self.order_repository.update(saved_order)
            
            return {
                "message": "Close order submitted",
                "order_id": str(saved_order.id),
                "exchange_order_id": saved_order.exchange_order_id
            }
            
        except Exception as e:
            logger.error(f"Failed to execute close order: {e}")
            saved_order.status = OrderStatus.REJECTED
            saved_order.error_message = str(e)
            await self.order_repository.update(saved_order)
            raise ValueError(f"Failed to close position: {e}")

    async def close_all_positions(self, bot_id: uuid.UUID) -> Dict[str, Any]:
        """Close all open positions for a bot."""
        # 1. Get Live Positions (to ensure we have latest)
        positions_data = await self.get_live_positions(bot_id)
        positions = positions_data["positions"]
        
        results = []
        errors = []
        
        for pos in positions:
            try:
                res = await self.close_position(
                    bot_id=bot_id,
                    symbol=pos["symbol"],
                    side=pos["side"]
                )
                results.append(res)
            except Exception as e:
                errors.append(f"Failed {pos['symbol']} {pos['side']}: {e}")
                
        return {
            "closed_count": len(results),
            "error_count": len(errors),
            "errors": errors,
            "results": results
        }
