from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, List, Optional, Any
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
            user_id = verify_access_token(token)
            user_id = payload.get("sub")
            
            if not user_id:
                return None
            
            # Verify user exists and is active
            user = await user_repository.get_by_id(user_id)
            if not user or not user.is_active:
                return None
            
            return str(user_id)
            
        except Exception as e:
            logger.error(f"WebSocket authentication error: {e}")
            return None


@router.websocket("/trading")
async def websocket_trading_endpoint(
    websocket: WebSocket,
    token: Optional[str] = None,
    user_repository: UserRepository = Depends(lambda: UserRepository())
):
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
    await websocket_manager.connect(websocket, user_id)
    
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
        await websocket_manager.disconnect(websocket, user_id)


@router.websocket("/market")
async def websocket_market_endpoint(websocket: WebSocket):
    """Public WebSocket endpoint for market data."""
    await websocket.accept()
    
    # Use public user ID for market data
    user_id = "public"
    await websocket_manager.connect(websocket, user_id)
    
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
        await websocket_manager.disconnect(websocket, user_id)


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