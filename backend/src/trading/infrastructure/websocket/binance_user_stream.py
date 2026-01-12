import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from decimal import Decimal
import uuid
import websockets

from .websocket_manager import websocket_manager
from ..exchange.binance_adapter import BinanceAdapter
from ..config.settings import get_settings
from ..persistence.database import get_db_context
from ..persistence.repositories.order_repository import OrderRepository
from ..persistence.repositories.trade_repository import TradeRepository
from ...application.services.bot_stats_service import BotStatsService
from ...application.use_cases.order.update_order_status import UpdateOrderStatusUseCase
from ...domain.order import OrderStatus

logger = logging.getLogger(__name__)
settings = get_settings()

class BinanceUserStreamService:
    """
    Manages Binance User Data Stream for real-time account updates.
    Handles 'listenKey' lifecycle (creation, keep-alive) and WebSocket connection.
    Also subscribes to Mark Price stream for real-time PnL updates.
    """
    
    def __init__(self):
        self.connections: Dict[str, websockets.WebSocketServerProtocol] = {} # bot_id -> ws_connection (User Data)
        self.mark_price_connections: Dict[str, websockets.WebSocketServerProtocol] = {} # bot_id -> ws_connection (Mark Price)
        self.listen_keys: Dict[str, str] = {} # bot_id -> listen_key
        self.active_bots: Dict[str, Dict] = {} # bot_id -> {adapter, user_id, symbol, is_testnet} 
        self.keep_alive_tasks: Dict[str, asyncio.Task] = {}
        self.running = False
        
        # Position tracking for real-time PnL calculation
        self.cached_positions: Dict[str, Dict] = {} # bot_id -> {symbol: position_data}
        self.lifecycle_tasks: Dict[str, List[asyncio.Task]] = {} # bot_id -> [user_task, mark_price_task]
        
    async def start(self):
        """Start the service."""
        logger.info("Starting Binance User Stream Service...")
        self.running = True
        
    async def stop(self):
        """Stop the service and close all streams."""
        logger.info("Stopping Binance User Stream Service...")
        self.running = False
        
        # Cancel all lifecycle tasks
        for tasks in self.lifecycle_tasks.values():
            for task in tasks:
                task.cancel()
        self.lifecycle_tasks.clear()

        # Cancel all keep-alive tasks
        for task in self.keep_alive_tasks.values():
            task.cancel()
        self.keep_alive_tasks.clear()
            
        # Close all User Data connections
        for bot_id, connection in self.connections.items():
            try:
                await connection.close()
            except Exception as e:
                logger.error(f"Error closing user stream for bot {bot_id}: {e}")
                
        # Close all Mark Price connections
        for bot_id, connection in self.mark_price_connections.items():
            try:
                await connection.close()
            except Exception as e:
                logger.error(f"Error closing mark price stream for bot {bot_id}: {e}")
        
        self.connections.clear()
        self.mark_price_connections.clear()
        self.listen_keys.clear()
        self.active_bots.clear()
        self.cached_positions.clear()

    async def start_stream_for_bot(self, bot_id: str, adapter: BinanceAdapter, user_id: str, symbol: str):
        """
        Start individual user stream for a bot.
        """
        if bot_id in self.active_bots:
            logger.info(f"Stream for bot {bot_id} already exists/active")
            return

        try:
            # Determine if testnet
            is_testnet = "testnet" in adapter._base_url or "demo" in adapter._base_url
            
            # Save context
            self.active_bots[bot_id] = {
                "adapter": adapter,
                "user_id": user_id,
                "symbol": symbol.replace("/", "").upper(),
                "is_testnet": is_testnet
            }
            
            # Start maintenance tasks
            user_stream_task = asyncio.create_task(self._maintain_user_stream(bot_id))
            mark_price_task = asyncio.create_task(self._maintain_mark_price_stream(bot_id))
            
            self.lifecycle_tasks[bot_id] = [user_stream_task, mark_price_task]
            
            # Fetch initial positions immediately (parallel to stream startup)
            asyncio.create_task(self._fetch_initial_positions(bot_id, adapter))
            # logger.info(f"Skipping initial position fetch for bot {bot_id} (Debugging)")
            
        except Exception as e:
            logger.error(f"Failed to initiate stream for bot {bot_id}: {e}")
            if bot_id in self.active_bots:
                del self.active_bots[bot_id]

    async def _maintain_user_stream(self, bot_id: str):
        """
        Permanent loop to maintain User Data Stream connection.
        Handles initial connection and automatic reconnection.
        """
        logger.info(f"Starting User Stream maintenance loop for bot {bot_id}")
        
        while self.running and bot_id in self.active_bots:
            try:
                bot_info = self.active_bots[bot_id]
                adapter = bot_info["adapter"]
                is_testnet = bot_info["is_testnet"]
                
                # 1. Get Listen Key
                try:
                    listen_key = await adapter.start_user_data_stream()
                    self.listen_keys[bot_id] = listen_key
                    logger.info(f"Obtained listenKey for bot {bot_id}: {listen_key[:6]}...")
                except Exception as e:
                    logger.error(f"Failed to get listenKey for bot {bot_id}: {e}. Retrying in 5s...")
                    await asyncio.sleep(5)
                    continue

                # 2. Connect WebSocket
                if is_testnet:
                    base_ws_url = "wss://fstream.binancefuture.com/ws"
                else:
                    base_ws_url = "wss://fstream.binance.com/ws"
                ws_url = f"{base_ws_url}/{listen_key}"
                
                logger.info(f"Connecting to User Data Stream: {ws_url[:50]}...")
                
                async with websockets.connect(ws_url) as connection:
                    self.connections[bot_id] = connection
                    logger.info(f"User Data Stream connected for bot {bot_id}")
                    
                    # 3. Start Keep-Alive (Managed within this connection scope)
                    keep_alive_task = asyncio.create_task(self._keep_alive_loop(bot_id, adapter, listen_key))
                    self.keep_alive_tasks[bot_id] = keep_alive_task
                    
                    try:
                        # 4. Listen Loop
                        while self.running:
                            message = await connection.recv()
                            data = json.loads(message)
                            
                            event_type = data.get("e")
                            if event_type == "ACCOUNT_UPDATE":
                                await self._handle_account_update(bot_id, data, adapter)
                            elif event_type == "ORDER_TRADE_UPDATE":
                                await self._handle_order_update(bot_id, data)
                            elif event_type == "ACCOUNT_CONFIG_UPDATE":
                                await self._handle_account_config_update(bot_id, data)
                            elif event_type == "listenKeyExpired":
                                logger.warning(f"ListenKey expired for bot {bot_id}, reconnecting...")
                                break # Break inner loop to reconnect
                                
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning(f"User stream connection closed for bot {bot_id}")
                    except Exception as e:
                        logger.error(f"Error in user stream loop for bot {bot_id}: {e}")
                    finally:
                        # Cleanup before reconnect/exit
                        keep_alive_task.cancel()
                        if bot_id in self.connections:
                            del self.connections[bot_id]
                            
            except asyncio.CancelledError:
                logger.info(f"User stream maintenance cancelled for bot {bot_id}")
                break
            except Exception as outer_e:
                logger.error(f"Unexpected error in maintenance loop for bot {bot_id}: {outer_e}")
                
            # Wait before reconnecting to avoid spam
            if self.running and bot_id in self.active_bots:
                logger.info(f"Reconnecting User Stream for bot {bot_id} in 5s...")
                await asyncio.sleep(5)

    async def _maintain_mark_price_stream(self, bot_id: str):
        """
        Permanent loop to maintain Mark Price Stream connection.
        """
        logger.info(f"Starting Mark Price Stream maintenance loop for bot {bot_id}")
        
        while self.running and bot_id in self.active_bots:
            try:
                bot_info = self.active_bots[bot_id]
                symbol = bot_info["symbol"]
                is_testnet = bot_info["is_testnet"]
                
                normalized_symbol = symbol.replace("/", "").lower()
                if is_testnet:
                    ws_url = f"wss://fstream.binancefuture.com/ws/{normalized_symbol}@markPrice@1s"
                else:
                    ws_url = f"wss://fstream.binance.com/ws/{normalized_symbol}@markPrice@1s"
                
                logger.info(f"Connecting to Mark Price stream: {ws_url}")
                
                async with websockets.connect(ws_url) as connection:
                    self.mark_price_connections[bot_id] = connection
                    logger.info(f"Mark Price Stream CONNECTED for bot {bot_id}")
                    
                    try:
                        while self.running:
                            message = await connection.recv()
                            # logger.info(f"[TRACE] MP Msg") 
                            data = json.loads(message)
                            
                            if data.get("e") == "markPriceUpdate":
                                await self._handle_mark_price_update(bot_id, data)
                                
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning(f"Mark Price stream connection closed for bot {bot_id}")
                    except Exception as e:
                        logger.error(f"Error in Mark Price stream loop for bot {bot_id}: {e}")
                    finally:
                        if bot_id in self.mark_price_connections:
                            del self.mark_price_connections[bot_id]
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in mark price loop: {e}")
            
            if self.running and bot_id in self.active_bots:
                logger.info(f"Reconnecting Mark Price stream for bot {bot_id} in 5s...")
                await asyncio.sleep(5)

    async def _fetch_initial_positions(self, bot_id: str, adapter: BinanceAdapter):
        """Fetch initial positions from exchange to cache."""
        try:
            bot_info = self.active_bots.get(bot_id)
            if not bot_info:
                return
                
            account_info = await adapter.get_account_info()
            target_symbol = bot_info["symbol"]
            
            # Cache positions
            self.cached_positions[bot_id] = {}
            
            for pos in account_info.positions:
                # Normalize symbol to match WebSocket format (BTC/USDT -> BTCUSDT)
                normalized_s = pos.symbol.replace("/", "").upper()
                
                if normalized_s == target_symbol and pos.quantity > 0:
                    qty = Decimal(str(pos.quantity))
                    entry_price = Decimal(str(pos.entry_price))
                    
                    # Use unique key combining symbol and side to support Hedge Mode
                    cache_key = f"{normalized_s}_{pos.side}"
                    self.cached_positions[bot_id][cache_key] = {
                        "id": str(uuid.uuid4()), # Frontend needs unique ID for key
                        "symbol": normalized_s, 
                        "side": pos.side,
                        "quantity": float(abs(qty)),
                        "entry_price": float(entry_price),
                        "mark_price": float(pos.mark_price or entry_price),
                        "unrealized_pnl": float(pos.unrealized_pnl or 0),
                        "unrealized_pnl_pct": 0.0, # Will be calculated in update
                        "leverage": pos.leverage or 1,
                        "margin_type": pos.margin_type,
                        "isolated_wallet": float(getattr(pos, 'isolated_wallet', 0) or 0),
                        # === NEW FIELDS ===
                        "break_even_price": float(getattr(pos, 'break_even_price', 0) or 0),
                        "liquidation_price": float(getattr(pos, 'liquidation_price', 0) or 0),
                        "position_initial_margin": float(getattr(pos, 'position_initial_margin', 0) or 0),
                        "maint_margin": float(getattr(pos, 'maint_margin', 0) or 0),
                        "margin_asset": "USDT",
                    }
                    
                    # Trigger risk data fetch for liquidation price, etc.
                    asyncio.create_task(self._refresh_position_risk_data(bot_id, normalized_s, pos.side, adapter))
                    
            logger.info(f"Cached {len(self.cached_positions.get(bot_id, {}))} positions for bot {bot_id}")
            
            # Push initial positions to frontend
            if self.cached_positions.get(bot_id):
                await self._push_positions_update(bot_id)
                
        except Exception as e:
            logger.error(f"Failed to fetch initial positions for bot {bot_id}: {e}")

    async def _handle_mark_price_update(self, bot_id: str, data: Dict):
        """Handle mark price update and recalculate PnL for cached positions."""
        symbol = data.get("s")  # Symbol
        mark_price = Decimal(data.get("p", "0"))  # Mark Price
        
        bot_positions = self.cached_positions.get(bot_id, {})
        
        if not bot_positions:
            return
            
        # Iterate over all positions to find matches (Hedge mode means multiple positions per symbol)
        for position in bot_positions.values():
            if position["symbol"] != symbol:
                continue
                
            # Update mark price
            # Update mark price
            # Update mark price
            position["mark_price"] = float(mark_price)
        
            # Recalculate Unrealized PnL based on live Mark Price
            # Note: ACCOUNT_UPDATE only sends PnL on trade/balance events, not for price fluctuations.
            # To show real-time PnL, we must calculate it here.
            entry_price = Decimal(str(position["entry_price"]))
            quantity = Decimal(str(position["quantity"]))
            side = position["side"]
            
            if side in ["LONG", "BUY"]:
                unrealized_pnl = (mark_price - entry_price) * quantity
            else:  # SHORT/SELL
                unrealized_pnl = (entry_price - mark_price) * quantity
                
            position["unrealized_pnl"] = float(unrealized_pnl)
            
            # Calculate ROI %
            isolated_wallet = Decimal(str(position.get("isolated_wallet", 0)))
            if isolated_wallet > 0:
                position["unrealized_pnl_pct"] = float((unrealized_pnl / isolated_wallet) * 100)
            elif entry_price > 0:
                leverage = position.get("leverage", 1)
                # ROI = (PnL / Initial Margin) * 100 = diff/entry * leverage * 100
                diff_pct = ((mark_price - entry_price) / entry_price) * 100
                if side in ["SHORT", "SELL"]:
                    diff_pct = -diff_pct
                position["unrealized_pnl_pct"] = float(diff_pct * leverage)
            
            # Update timestamp
            position["timestamp"] = datetime.utcnow().isoformat()
            
            position["timestamp"] = datetime.utcnow().isoformat()
            
        # Push update to frontend (once after all updates)
        await self._push_positions_update(bot_id)

    async def _handle_account_config_update(self, bot_id: str, data: Dict):
        """Handle ACCOUNT_CONFIG_UPDATE (Leverage/Margin changes)."""
        config = data.get("ac", {})
        symbol = config.get("s")
        leverage = config.get("l")
        
        if not symbol or not leverage:
            return
            
        bot_positions = self.cached_positions.get(bot_id, {})
        updated = False
        
        # Update leverage for ALL positions of this symbol (Long/Short)
        for position in bot_positions.values():
            if position["symbol"] == symbol:
                position["leverage"] = int(leverage)
                updated = True
                
        if updated:
            await self._push_positions_update(bot_id)

    async def _refresh_position_leverage(self, bot_id: str, symbol: str, adapter: BinanceAdapter):
        """Fetch fresh position risk to update leverage for new positions."""
        try:
            # Wait a moment for position to be fully established on exchange
            await asyncio.sleep(1) 
            risk_data = await adapter.get_position_risk(symbol)
            
            if not risk_data:
                return
                
            bot_positions = self.cached_positions.get(bot_id, {})
            updated = False
            
            # Position risk returns list (Hedge mode: both LONG and SHORT entries)
            for risk in risk_data:
                # Map positionSide (usually LONG/SHORT/BOTH)
                # Note: adapter.get_position_risk returns raw list from Binance
                # Binance keys: symbol, positionSide, leverage, marginType...
                
                # We need to match with our cached keys (Symbol_Side)
                # Binance positionSide is "LONG", "SHORT", "BOTH"
                # Our cache uses "LONG", "SHORT"
                
                side = risk.get("positionSide")
                if side == "BOTH":
                    # Determine side based on amt? No, in Hedge Mode it is explicit.
                    # But if One-Way mode, it is BOTH.
                    # Our cache logic maps "BOTH" to LONG/SHORT based on quantity in _handle_account_update
                    # This is tricky. Let's look up by Symbol and compare side.
                    pass

                leverage = int(risk.get("leverage", 1))
                margin_type = risk.get("marginType")
                
                # Iterate our cache to find matches
                for position in bot_positions.values():
                    if position["symbol"] == symbol:
                        # If cached side matches risk side (or generic update)
                        # Given api returns [LONG, SHORT] risk, we can match exactly.
                        if position["side"] == side or (side=="BOTH" and position["side"] in ["LONG","SHORT"]):
                             position["leverage"] = leverage
                             if margin_type:
                                 position["margin_type"] = margin_type
                             updated = True
            
            if updated:
                logger.info(f"Refreshed leverage/margin for {symbol} on bot {bot_id}")
                await self._push_positions_update(bot_id)
                
        except Exception as e:
            logger.error(f"Failed to refresh leverage for {symbol}: {e}")

    async def _refresh_position_risk_data(self, bot_id: str, symbol: str, side: str, adapter: BinanceAdapter):
        """Fetch position risk data to get liquidation price, maint margin, and break-even price."""
        try:
            # Wait a moment for position to be fully established on exchange
            await asyncio.sleep(0.5)
            risk_data = await adapter.get_position_risk(symbol)
            
            if not risk_data:
                return
                
            bot_positions = self.cached_positions.get(bot_id, {})
            cache_key = f"{symbol}_{side}"
            
            if cache_key not in bot_positions:
                return
                
            position = bot_positions[cache_key]
            updated = False
            
            # Position risk API returns list with entries for each position side
            for risk in risk_data:
                risk_side = risk.get("positionSide", "BOTH")
                
                # Log raw risk data for debugging
                logger.info(f"Raw Position Risk data for {symbol}: {risk}")
                
                # Match side (BOTH maps to our side)
                if risk_side == side or (risk_side == "BOTH" and side in ["LONG", "SHORT"]):
                    # Update liquidation price
                    liq_price = float(risk.get("liquidationPrice", 0) or 0)
                    if liq_price > 0:
                        position["liquidation_price"] = liq_price
                        updated = True
                    
                    # Update maint margin
                    maint_margin = float(risk.get("maintMargin", 0) or 0)
                    position["maint_margin"] = maint_margin
                    
                    # Update position initial margin - Use 'isolatedWallet' (11.74) not 'isolatedMargin' (11.32)
                    isolated_wallet = float(risk.get("isolatedWallet", 0) or risk.get("isolatedMargin", 0) or 0)
                    if isolated_wallet > 0:
                        position["position_initial_margin"] = isolated_wallet
                        position["isolated_wallet"] = isolated_wallet
                    
                    # Update break-even price if available
                    break_even = float(risk.get("breakEvenPrice", 0) or 0)
                    if break_even > 0:
                        position["break_even_price"] = break_even
                    
                    # Update leverage and margin type
                    position["leverage"] = int(risk.get("leverage", position.get("leverage", 1)))
                    position["margin_type"] = risk.get("marginType", position.get("margin_type"))
                    
                    updated = True
                    break
            
            if updated:
                logger.info(f"Refreshed risk data for {cache_key} on bot {bot_id}: liq={position.get('liquidation_price')}, bep={position.get('break_even_price')}, maint={position.get('maint_margin')}, initMargin={position.get('position_initial_margin')}")
                await self._push_positions_update(bot_id)
                
        except Exception as e:
            logger.error(f"Failed to refresh position risk data for {symbol}: {e}")

    async def _push_positions_update(self, bot_id: str):
        """Push current cached positions to frontend via WebSocket."""
        bot_positions = self.cached_positions.get(bot_id, {})
        positions_list = list(bot_positions.values())

        await websocket_manager.broadcast_to_channel(
            f"positions:{bot_id}",
            {
                "type": "position_update",
                "data": positions_list
            }
        )

    async def _keep_alive_loop(self, bot_id: str, adapter: BinanceAdapter, listen_key: str):
        """Send keep-alive request every 50 minutes."""
        try:
            while self.running:
                await asyncio.sleep(50 * 60) # 50 minutes
                logger.info(f"Sending keep-alive for bot {bot_id}")
                await adapter.keep_alive_user_data_stream(listen_key)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Keep-alive failed for bot {bot_id}: {e}")

    async def _handle_account_update(self, bot_id: str, data: Dict, adapter: BinanceAdapter):
        """
        Handle ACCOUNT_UPDATE event.
        Updates cached positions and pushes to Frontend.
        """
        update_data = data.get("a", {})
        positions = update_data.get("P", []) # List of updated positions
        
        bot_info = self.active_bots.get(bot_id)
        if not bot_info:
            return
            
        target_symbol = bot_info["symbol"]
        
        # Initialize cache if needed
        if bot_id not in self.cached_positions:
            self.cached_positions[bot_id] = {}
        
        for p in positions:
            if p["s"] != target_symbol:
                continue
                
            logger.info(f"ACCOUNT_UPDATE for {p['s']}: qty={p.get('pa')}, entry={p.get('ep')}, pnl={p.get('up')}")
                
            qty = Decimal(p["pa"])
            entry_price = Decimal(p["ep"])
            unrealized_pnl = Decimal(p["up"])
            isolated_wallet = Decimal(p.get("iw", "0"))
            
            # Determine side
            side = p.get("ps")
            if side == "BOTH":
                side = "LONG" if qty > 0 else "SHORT" if qty < 0 else "FLAT"
            
            if abs(qty) > 0:
                # Update/Add position to cache
                roi_pct = 0.0
                if isolated_wallet > 0:
                    roi_pct = float((unrealized_pnl / isolated_wallet) * 100)
                
                cache_key = f"{p['s']}_{side}"
                existing_pos = self.cached_positions[bot_id].get(cache_key, {})
                
                # Preserve existing ID if updating
                pos_id = existing_pos.get("id", str(uuid.uuid4()))
                
                # ACCOUNT_UPDATE often lacks leverage ('l'), so preserve existing.
                # If NEW position and 'l' missing, schedule refresh.
                leverage = 1
                if p.get("l"):
                    leverage = int(p["l"])
                elif existing_pos:
                    leverage = existing_pos.get("leverage", 1)
                else:
                    # NEW position and leverage missing -> Trigger fetch
                    asyncio.create_task(self._refresh_position_leverage(bot_id, p["s"], adapter))
                
                self.cached_positions[bot_id][cache_key] = {
                    "id": pos_id,
                    "symbol": p["s"],
                    "side": side,
                    "quantity": float(abs(qty)),
                    "entry_price": float(entry_price),
                    "mark_price": float(entry_price),  # Will be updated by mark price stream
                    "unrealized_pnl": float(unrealized_pnl),
                    "unrealized_pnl_pct": roi_pct,
                    "leverage": leverage,
                    "margin_type": p.get("mt"),
                    "isolated_wallet": float(isolated_wallet),
                    # === NEW FIELDS ===
                    "break_even_price": float(Decimal(p.get("bep", "0"))),  # Break-even price
                    "position_initial_margin": float(Decimal(p.get("iw", "0"))),  # Initial margin (same as isolated_wallet for isolated)
                    "maint_margin": existing_pos.get("maint_margin", 0.0),  # Will be fetched from Position Risk
                    "liquidation_price": existing_pos.get("liquidation_price", 0.0),  # Will be fetched from Position Risk
                    "margin_asset": "USDT",  # Default, can be updated
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # If new position or missing liquidation data, fetch from Position Risk API
                if not existing_pos.get("liquidation_price"):
                    asyncio.create_task(self._refresh_position_risk_data(bot_id, p["s"], side, adapter))
            else:
                # Position closed - remove from cache
                # We need to know side to remove specific position in Hedge Mode
                side = p.get("ps")
                if side == "BOTH":
                     # Fallback logic if side is ambiguous? Usually 'ps' is reliable in ACCOUNT_UPDATE
                     pass 
                
                cache_key = f"{p['s']}_{side}"
                
                if cache_key in self.cached_positions[bot_id]:
                    del self.cached_positions[bot_id][cache_key]
                    logger.info(f"Position closed for {cache_key} on bot {bot_id}")
                elif p['s'] in self.cached_positions[bot_id]:
                     # Fallback for old keys?
                     del self.cached_positions[bot_id][p['s']]
        # Push update to frontend
        await self._push_positions_update(bot_id)

    async def _handle_order_update(self, bot_id: str, data: Dict):
        """Handle ORDER_TRADE_UPDATE event (Order status changes)."""
        order_data = data.get("o", {})
        
        # Broadcast first
        await websocket_manager.broadcast_to_channel(
            f"orders:{bot_id}",
            {
                "type": "order_update",
                "data": order_data
            }
        )
        
        # Update DB and PnL Logic
        try:
            client_order_id = order_data.get("c")
            exchange_order_id = str(order_data.get("i"))
            status_raw = order_data.get("X")
            
            # Map status
            status_map = {
                "NEW": OrderStatus.NEW,
                "PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
                "FILLED": OrderStatus.FILLED,
                "CANCELED": OrderStatus.CANCELLED,
                "REJECTED": OrderStatus.REJECTED,
                "EXPIRED": OrderStatus.CANCELLED
            }
            new_status = status_map.get(status_raw)
            
            if not new_status:
                logger.warning(f"Unknown order status: {status_raw}")
                return

            async with get_db_context() as session:
                order_repository = OrderRepository(session)
                trade_repository = TradeRepository(session)
                bot_stats_service = BotStatsService(session)
                use_case = UpdateOrderStatusUseCase(order_repository, trade_repository, bot_stats_service)
                
                # We need to find the order ID (UUID) from Client Order ID or Exchange Order ID
                # The use case requires UUID.
                # So we lookup first.
                bot_uuid = uuid.UUID(bot_id)
                
                # RETRY LOGIC: Race condition handler
                # If WS arrives before PositionService commits the order, we wait and retry.
                retry_count = 0
                max_retries = 3
                order = None
                
                # Fetch user_id from active bots cache
                user_id_str = self.active_bots.get(bot_id, {}).get("user_id")

                while retry_count < max_retries:
                    if client_order_id and user_id_str:
                         user_id = uuid.UUID(user_id_str)
                         order = await order_repository.get_by_client_order_id(client_order_id, user_id)
                    
                    if not order and exchange_order_id and user_id_str:
                         user_id = uuid.UUID(user_id_str)
                         order = await order_repository.get_by_exchange_order_id(exchange_order_id, user_id)
                    
                    if order:
                        break
                        
                    # If not found, wait and retry
                    retry_count += 1
                    if retry_count < max_retries:
                        delay = 0.5 * retry_count # 0.5s, 1.0s, 1.5s
                        logger.warning(f"DEBUG: Order {client_order_id} not found, retrying {retry_count}/{max_retries} in {delay}s...")
                        await asyncio.sleep(delay)
                        # Refresh session? No, session is fresh per call, but we need to ensure we don't hold stale state?
                        # get_db_context creates a session for the scope. 
                        # We might need to expire/refresh if we were inside a transaction, but here we are just reading.
                        # Actually, if we are in a transaction (session), repeated reads might return snapshot?
                        # SQLAlchemy AsyncSession with default isolation might see committed changes if we re-execute query.
                        # Let's ensure we expire all to force fresh read
                        session.expire_all()

                if order:
                    logger.info(f"Processing order update for {order.id} status={new_status}")
                    await use_case.execute(
                        user_id=order.user_id,
                        order_id=order.id,
                        new_status=new_status,
                        executed_quantity=Decimal(order_data.get("l", "0")), # Last filled qty
                        executed_price=Decimal(order_data.get("L", "0")),    # Last filled price
                        commission=Decimal(order_data.get("n", "0")),
                        commission_asset=order_data.get("N", "USDT"),
                        reason=None
                    )
                    # Trigger cache update if filled/closed?
                    # The `_push_positions_update` is called regularly, but maybe force one now?
                    if new_status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED]:
                         # Wait a bit for exchange position to update then push?
                         # Or rely on ACCOUNT_UPDATE which usually follows ORDER_UPDATE
                         pass
                else:
                    # Order not found in our DB (External/Manual trade?)
                    logger.warning(f"DEBUG: Order update for unknown order: {client_order_id} (ExchID: {exchange_order_id})")
                    pass
                    
        except Exception as e:
            logger.error(f"Failed to process order update persistence: {e}")

# Global Instance
binance_user_stream = BinanceUserStreamService()
