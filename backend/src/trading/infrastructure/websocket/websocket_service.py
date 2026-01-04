import asyncio
import logging
from typing import Optional
from fastapi import FastAPI

from .binance_stream import binance_ws_client
from .binance_user_stream import binance_user_stream
from .websocket_manager import websocket_manager

logger = logging.getLogger(__name__)


class WebSocketService:
    """Service for managing WebSocket operations."""
    
    def __init__(self):
        self.binance_client = binance_ws_client
        self.user_stream = binance_user_stream
        self.websocket_manager = websocket_manager
        self.running = False
    
    async def start(self):
        """Start all WebSocket services."""
        if self.running:
            return
        
        self.running = True
        logger.info("Starting WebSocket services...")
        
        try:
            # Start Binance WebSocket client (Market Data)
            await self.binance_client.start()
            logger.info("Binance Market WebSocket client started")
            
            # Start User Data Stream Service
            await self.user_stream.start()
            logger.info("Binance User Data Stream service started")
            
            # Initialize WebSocket manager
            await self.websocket_manager.initialize()
            logger.info("WebSocket manager initialized")
            
            logger.info("All WebSocket services started successfully")
            
        except Exception as e:
            logger.error(f"Error starting WebSocket services: {e}")
            raise
    
    async def stop(self):
        """Stop all WebSocket services."""
        if not self.running:
            return
        
        self.running = False
        logger.info("Stopping WebSocket services...")
        
        try:
            # Stop Binance WebSocket client
            await self.binance_client.stop()
            logger.info("Binance Market WebSocket client stopped")
            
            # Stop User Data Stream
            await self.user_stream.stop()
            logger.info("Binance User Data Stream service stopped")
            
            # Cleanup WebSocket manager
            await self.websocket_manager.cleanup()
            logger.info("WebSocket manager cleaned up")
            
            logger.info("All WebSocket services stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping WebSocket services: {e}")
    
    async def restart(self):
        """Restart all WebSocket services."""
        logger.info("Restarting WebSocket services...")
        await self.stop()
        await asyncio.sleep(1)  # Brief pause
        await self.start()
    
    def is_running(self) -> bool:
        """Check if WebSocket services are running."""
        return self.running
    
    def get_status(self) -> dict:
        """Get status of WebSocket services."""
        return {
            "running": self.running,
            "binance_connections": len(self.binance_client.connections),
            "active_websocket_connections": len(self.websocket_manager.active_connections),
            "user_connections": len(self.websocket_manager.user_connections),
            "subscriptions": {
                user_id: len(subs) 
                for user_id, subs in self.websocket_manager.user_subscriptions.items()
            }
        }


# Global WebSocket service instance
websocket_service = WebSocketService()


# Lifespan events for FastAPI
async def websocket_lifespan_startup():
    """Startup event handler for WebSocket services."""
    try:
        await websocket_service.start()
    except Exception as e:
        logger.error(f"Failed to start WebSocket services: {e}")
        raise


async def websocket_lifespan_shutdown():
    """Shutdown event handler for WebSocket services."""
    try:
        await websocket_service.stop()
    except Exception as e:
        logger.error(f"Error during WebSocket shutdown: {e}")


# FastAPI lifespan context manager
from contextlib import asynccontextmanager

@asynccontextmanager
async def websocket_lifespan(app: FastAPI):
    """FastAPI lifespan context manager for WebSocket services."""
    # Startup
    await websocket_lifespan_startup()
    
    yield
    
    # Shutdown
    await websocket_lifespan_shutdown()