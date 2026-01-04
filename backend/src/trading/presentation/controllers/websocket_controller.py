from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import logging

from ...infrastructure.auth.jwt import verify_access_token
from ...infrastructure.repositories.user_repository import UserRepository
from ...infrastructure.websocket.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter(prefix="/ws", tags=["websocket"])


class WebSocketAuth:
    """WebSocket authentication helper."""
    
    @staticmethod
    async def authenticate_websocket(token: str, user_repository: UserRepository) -> Optional[str]:
        """Authenticate WebSocket connection using JWT token."""
        try:
            # verify_access_token returns UUID directly
            user_id = verify_access_token(token)
            
            if not user_id:
                return None
            
            # Verify user exists and is active
            user = await user_repository.find_by_id(user_id)
            if not user or not user.is_active:
                return None
            
            return str(user_id)
            
        except Exception as e:
            logger.error(f"WebSocket authentication error: {e}")
            return None


@router.websocket("")
async def websocket_general_endpoint(
    websocket: WebSocket,
    token: Optional[str] = None,
):
    """
    General WebSocket endpoint for all real-time updates.
    Supports bot_stats, trading, and other subscriptions.
    Connect to: ws://host/api/v1/ws?token=<jwt>
    """
    # Accept connection first (for better error messages)
    await websocket.accept()
    
    # Authenticate if token provided
    user_id = None
    if token:
        try:
            payload = verify_access_token(token)
            user_id = payload.get("sub") if isinstance(payload, dict) else str(payload)
        except Exception as e:
            logger.warning(f"WebSocket auth failed: {e}")
    
    # Use anonymous ID if no auth
    if not user_id:
        import uuid as uuid_module
        user_id = f"anon_{uuid_module.uuid4().hex[:8]}"
        logger.info(f"Anonymous WebSocket connection: {user_id}")
    
    # CRITICAL: Register with websocket_manager so broadcasts can reach this connection
    connection_id = await websocket_manager.connect(websocket, user_id)
    if not connection_id:
        logger.error(f"Failed to register WebSocket connection for user {user_id}")
        return
    
    try:
        # Send connection confirmation
        await websocket.send_text(json.dumps({
            "type": "connected",
            "user_id": user_id,
            "connection_id": connection_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }))
        
        while True:
            # Listen for client messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            await handle_general_message(websocket, user_id, message)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        # CRITICAL: Unregister from websocket_manager on disconnect
        await websocket_manager.disconnect(connection_id)


async def handle_general_message(websocket: WebSocket, user_id: str, message: Dict[str, Any]):
    """Handle general WebSocket messages including bot_stats subscriptions."""
    message_type = message.get("type")
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    if message_type == "subscribe":
        stream_type = message.get("stream_type")
        
        if stream_type == "BOT_STATS":
            bot_id = message.get("bot_id")
            
            await websocket.send_text(json.dumps({
                "type": "subscription_confirmed",
                "stream_type": "BOT_STATS",
                "bot_id": bot_id,
                "timestamp": timestamp
            }))
        else:
            # Generic subscription
            channels = message.get("channels", [])
            
            await websocket.send_text(json.dumps({
                "type": "subscription_confirmed",
                "channels": channels,
                "timestamp": timestamp
            }))
    


    elif message_type == "ping":
        await websocket.send_text(json.dumps({
            "type": "pong",
            "timestamp": timestamp
        }))
    
    else:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Unknown message type: {message_type}",
            "timestamp": timestamp
        }))


from ...infrastructure.persistence.database import get_db
# ...

@router.websocket("/trading")
async def websocket_trading_endpoint(
    websocket: WebSocket,
    token: Optional[str] = None,
    db = Depends(get_db)
):
    """Main WebSocket endpoint for trading updates."""
    user_repository = UserRepository(db)

    """Main WebSocket endpoint for trading updates."""
    if not token:
        await websocket.close(code=4001, reason="Authentication token required")
        return
    
    # Authenticate user
    user_id = await WebSocketAuth.authenticate_websocket(token, user_repository)
    if not user_id:
        await websocket.close(code=4001, reason="Invalid authentication token")
        return
    
    await websocket.accept()
    
    # Add connection to manager
    connection_id = await websocket_manager.connect(websocket, user_id)
    if not connection_id:
        return

    try:
        while True:
            # Listen for client messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            await handle_websocket_message(websocket, user_id, message)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        await websocket_manager.disconnect(connection_id)


@router.websocket("/market")
async def websocket_market_endpoint(websocket: WebSocket):
    """Public WebSocket endpoint for market data."""
    await websocket.accept()
    
    # Use public user ID for market data
    user_id = "public"
    connection_id = await websocket_manager.connect(websocket, user_id)
    if not connection_id:
        return
    
    try:
        while True:
            # Listen for subscription requests
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle market data subscriptions
            await handle_market_message(websocket, user_id, message)
            
    except WebSocketDisconnect:
        logger.info("Public market WebSocket disconnected")
    except Exception as e:
        logger.error(f"Market WebSocket error: {e}")
    finally:
        await websocket_manager.disconnect(connection_id)


async def handle_websocket_message(websocket: WebSocket, user_id: str, message: Dict[str, Any]):
    """Handle WebSocket messages from authenticated users."""
    message_type = message.get("type")
    
    if message_type == "subscribe":
        # Subscribe to specific channels
        channels = message.get("channels", [])
        await websocket_manager.subscribe_user(user_id, channels)
        
        # Send confirmation
        await websocket.send_text(json.dumps({
            "type": "subscription_confirmed",
            "channels": channels,
            "timestamp": websocket_manager._get_timestamp()
        }))
    
    elif message_type == "unsubscribe":
        # Unsubscribe from channels
        channels = message.get("channels", [])
        await websocket_manager.unsubscribe_user(user_id, channels)
        
        # Send confirmation
        await websocket.send_text(json.dumps({
            "type": "unsubscription_confirmed",
            "channels": channels,
            "timestamp": websocket_manager._get_timestamp()
        }))
    
    elif message_type == "ping":
        # Handle ping/pong for connection health
        await websocket.send_text(json.dumps({
            "type": "pong",
            "timestamp": websocket_manager._get_timestamp()
        }))
    
    elif message_type == "subscribe_symbol":
        # Subscribe to specific symbol price updates
        symbols = message.get("symbols", [])
        for symbol in symbols:
            await websocket_manager.subscribe_to_price_updates(user_id, symbol)
        
        
        # Send confirmation
        await websocket.send_text(json.dumps({
            "type": "symbol_subscription_confirmed",
            "symbols": symbols,
            "timestamp": websocket_manager._get_timestamp()
        }))
    
    elif message_type == "start_bot_stream":
        """
        Explicitly start User Data Stream for a bot.
        """
        bot_id = message.get("bot_id")
        if bot_id:
            try:
                from ...infrastructure.persistence.database import get_db_context
                from ...infrastructure.persistence.repositories.bot_repository import BotRepository
                # Absolute import for sibling package 'application'
                from application.services.connection_service import ConnectionService
                from ...infrastructure.websocket.binance_user_stream import binance_user_stream
                from ...infrastructure.exchange.binance_adapter import BinanceAdapter
                
                # Collect data from DB first
                bot_data = None
                creds = None
                
                async with get_db_context() as session:
                    bot_repo = BotRepository(session)
                    conn_service = ConnectionService(session)
                    
                    bot = await bot_repo.find_by_id(bot_id)
                    logger.info(f"[DEBUG] Bot found: {bot is not None}, bot_id: {bot_id}")
                    
                    if bot:
                        logger.info(f"[DEBUG] Bot user_id: {bot.user_id}, request user_id: {user_id}")
                        logger.info(f"[DEBUG] Bot exchange_connection_id: {bot.exchange_connection_id}")
                        
                    # Verify user owns the bot!
                    if bot and str(bot.user_id) == str(user_id) and bot.exchange_connection_id:
                        creds = await conn_service.get_connection_credentials(str(bot.exchange_connection_id), bot.user_id)
                        logger.info(f"[DEBUG] Credentials obtained: {creds is not None}")
                        bot_data = {
                            "id": str(bot.id),
                            "user_id": str(bot.user_id),
                            "symbol": bot.configuration.symbol,
                            "is_testnet": creds["is_testnet"]
                        }
                        logger.info(f"[DEBUG] bot_data prepared: {bot_data}")
                    else:
                        logger.warning(f"Unauthorized stream start attempt for bot {bot_id} by user {user_id}")
                
                # Start stream OUTSIDE db context to avoid async task termination
                if bot_data and creds:
                    base_url = "https://demo-fapi.binance.com" if creds["is_testnet"] else "https://fapi.binance.com"
                    adapter = BinanceAdapter(
                        api_key=creds["api_key"],
                        api_secret=creds["api_secret"],
                        base_url=base_url,
                        testnet=creds["is_testnet"]
                    )
                    
                    logger.info(f"Starting stream for bot {bot_data['id']} on {bot_data['symbol']}")
                    
                    await binance_user_stream.start_stream_for_bot(
                        bot_id=bot_data["id"],
                        adapter=adapter,
                        user_id=bot_data["user_id"],
                        symbol=bot_data["symbol"]
                    )
                    
                    await websocket.send_text(json.dumps({
                        "type": "stream_started",
                        "bot_id": bot_id,
                        "timestamp": websocket_manager._get_timestamp()
                    }))
                    
            except Exception as e:
                import traceback
                logger.error(f"Failed to start bot stream: {e}")
                logger.error(traceback.format_exc())
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Failed to start stream: {str(e)}",
                    "timestamp": websocket_manager._get_timestamp()
                }))
    
    else:
        # Unknown message type
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Unknown message type: {message_type}",
            "timestamp": websocket_manager._get_timestamp()
        }))


async def handle_market_message(websocket: WebSocket, user_id: str, message: Dict[str, Any]):
    """Handle WebSocket messages for public market data."""
    message_type = message.get("type")
    
    if message_type == "subscribe_ticker":
        # Subscribe to ticker updates for symbols
        symbols = message.get("symbols", [])
        for symbol in symbols:
            await websocket_manager.subscribe_to_price_updates(user_id, symbol)
        
        # Send confirmation
        await websocket.send_text(json.dumps({
            "type": "ticker_subscription_confirmed",
            "symbols": symbols,
            "timestamp": websocket_manager._get_timestamp()
        }))
    
    elif message_type == "subscribe_trades":
        # Subscribe to trade updates for symbols
        symbols = message.get("symbols", [])
        channels = [f"trades:{symbol}" for symbol in symbols]
        await websocket_manager.subscribe_user(user_id, channels)
        
        # Send confirmation
        await websocket.send_text(json.dumps({
            "type": "trades_subscription_confirmed",
            "symbols": symbols,
            "timestamp": websocket_manager._get_timestamp()
        }))
    
    elif message_type == "subscribe_orderbook":
        # Subscribe to orderbook updates for symbols
        symbols = message.get("symbols", [])
        channels = [f"orderbook:{symbol}" for symbol in symbols]
        await websocket_manager.subscribe_user(user_id, channels)
        
        # Send confirmation
        await websocket.send_text(json.dumps({
            "type": "orderbook_subscription_confirmed",
            "symbols": symbols,
            "timestamp": websocket_manager._get_timestamp()
        }))
    
    elif message_type == "ping":
        # Handle ping/pong
        await websocket.send_text(json.dumps({
            "type": "pong",
            "timestamp": websocket_manager._get_timestamp()
        }))
    
    else:
        # Unknown message type
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Unknown message type: {message_type}",
            "timestamp": websocket_manager._get_timestamp()
        }))


@router.get("/status")
async def websocket_status():
    """Get WebSocket server status."""
    return {
        "status": "active",
        "active_connections": len(websocket_manager.active_connections),
        "user_connections": {
            user_id: len(connections) 
            for user_id, connections in websocket_manager.user_connections.items()
        },
        "total_subscriptions": sum(
            len(subs) for subs in websocket_manager.user_subscriptions.values()
        )
    }