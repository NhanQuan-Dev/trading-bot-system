import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import websockets
from decimal import Decimal

from .websocket_manager import websocket_manager
from ..config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class BinanceWebSocketClient:
    """Binance WebSocket client for real-time market data."""
    
    def __init__(self):
        self.connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.subscriptions: Dict[str, List[str]] = {}  # stream_name -> symbols
        self.running = False
        
    async def start(self):
        """Start the Binance WebSocket client."""
        if self.running:
            return
            
        self.running = True
        logger.info("Starting Binance WebSocket client...")
        
        # Start price streams for popular pairs
        popular_symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "SOLUSDT"]
        await self.subscribe_ticker_streams(popular_symbols)
    
    async def stop(self):
        """Stop the Binance WebSocket client."""
        self.running = False
        logger.info("Stopping Binance WebSocket client...")
        
        # Close all connections
        for connection in self.connections.values():
            await connection.close()
        
        self.connections.clear()
        self.subscriptions.clear()
    
    async def subscribe_ticker_streams(self, symbols: List[str]):
        """Subscribe to ticker streams for multiple symbols."""
        try:
            # Create stream names
            streams = [f"{symbol.lower()}@ticker" for symbol in symbols]
            stream_url = self._build_stream_url(streams)
            
            # Connect to WebSocket
            connection = await websockets.connect(stream_url)
            stream_key = "ticker_" + "_".join([s.lower() for s in symbols])
            
            self.connections[stream_key] = connection
            self.subscriptions[stream_key] = symbols
            
            # Start listening
            asyncio.create_task(self._listen_ticker_stream(connection, symbols))
            
            logger.info(f"Subscribed to ticker streams for {len(symbols)} symbols")
            
        except Exception as e:
            logger.error(f"Error subscribing to ticker streams: {e}")
    
    async def subscribe_trades_stream(self, symbol: str):
        """Subscribe to trade stream for a symbol."""
        try:
            stream_name = f"{symbol.lower()}@trade"
            stream_url = self._build_stream_url([stream_name])
            
            connection = await websockets.connect(stream_url)
            stream_key = f"trade_{symbol.lower()}"
            
            self.connections[stream_key] = connection
            self.subscriptions[stream_key] = [symbol]
            
            # Start listening
            asyncio.create_task(self._listen_trade_stream(connection, symbol))
            
            logger.info(f"Subscribed to trade stream for {symbol}")
            
        except Exception as e:
            logger.error(f"Error subscribing to trade stream for {symbol}: {e}")
    
    async def subscribe_depth_stream(self, symbol: str, speed: str = "100ms"):
        """Subscribe to order book depth stream for a symbol."""
        try:
            stream_name = f"{symbol.lower()}@depth@{speed}"
            stream_url = self._build_stream_url([stream_name])
            
            connection = await websockets.connect(stream_url)
            stream_key = f"depth_{symbol.lower()}"
            
            self.connections[stream_key] = connection
            self.subscriptions[stream_key] = [symbol]
            
            # Start listening
            asyncio.create_task(self._listen_depth_stream(connection, symbol))
            
            logger.info(f"Subscribed to depth stream for {symbol}")
            
        except Exception as e:
            logger.error(f"Error subscribing to depth stream for {symbol}: {e}")
    
    def _build_stream_url(self, streams: List[str]) -> str:
        """Build Binance WebSocket stream URL."""
        base_url = "wss://stream.binance.com:9443"
        
        if len(streams) == 1:
            return f"{base_url}/ws/{streams[0]}"
        else:
            stream_list = "/".join(streams)
            return f"{base_url}/stream?streams={stream_list}"
    
    async def _listen_ticker_stream(self, connection: websockets.WebSocketServerProtocol, symbols: List[str]):
        """Listen to ticker stream and broadcast updates."""
        try:
            while self.running:
                message = await connection.recv()
                data = json.loads(message)
                
                # Handle individual ticker or combined stream
                if "stream" in data:
                    # Combined stream format
                    stream_data = data["data"]
                    symbol = stream_data["s"]
                else:
                    # Individual stream format
                    stream_data = data
                    symbol = stream_data["s"]
                
                # Process ticker data
                ticker_data = self._process_ticker_data(stream_data)
                
                # Broadcast to subscribers
                await websocket_manager.broadcast_price_update(symbol, ticker_data)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info("Binance ticker stream connection closed")
        except Exception as e:
            logger.error(f"Error in ticker stream: {e}")
    
    async def _listen_trade_stream(self, connection: websockets.WebSocketServerProtocol, symbol: str):
        """Listen to trade stream and broadcast updates."""
        try:
            while self.running:
                message = await connection.recv()
                data = json.loads(message)
                
                # Process trade data
                trade_data = self._process_trade_data(data)
                
                # Broadcast to subscribers
                await websocket_manager.broadcast_price_update(symbol, {
                    "type": "trade",
                    **trade_data
                })
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Binance trade stream connection closed for {symbol}")
        except Exception as e:
            logger.error(f"Error in trade stream for {symbol}: {e}")
    
    async def _listen_depth_stream(self, connection: websockets.WebSocketServerProtocol, symbol: str):
        """Listen to depth stream and broadcast updates."""
        try:
            while self.running:
                message = await connection.recv()
                data = json.loads(message)
                
                # Process depth data
                depth_data = self._process_depth_data(data)
                
                # Broadcast to subscribers
                await websocket_manager.broadcast_price_update(symbol, {
                    "type": "orderbook",
                    **depth_data
                })
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Binance depth stream connection closed for {symbol}")
        except Exception as e:
            logger.error(f"Error in depth stream for {symbol}: {e}")
    
    def _process_ticker_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process ticker data from Binance."""
        return {
            "type": "ticker",
            "symbol": data["s"],
            "price": Decimal(data["c"]),
            "price_change": Decimal(data["P"]),
            "price_change_percent": Decimal(data["P"]),
            "high_price": Decimal(data["h"]),
            "low_price": Decimal(data["l"]),
            "volume": Decimal(data["v"]),
            "quote_volume": Decimal(data["q"]),
            "open_time": int(data["O"]),
            "close_time": int(data["C"]),
            "count": int(data["n"]),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _process_trade_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process trade data from Binance."""
        return {
            "symbol": data["s"],
            "trade_id": int(data["t"]),
            "price": Decimal(data["p"]),
            "quantity": Decimal(data["q"]),
            "trade_time": int(data["T"]),
            "is_buyer_maker": data["m"],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _process_depth_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process depth data from Binance."""
        return {
            "symbol": data["s"],
            "first_update_id": int(data["U"]),
            "final_update_id": int(data["u"]),
            "bids": [[Decimal(price), Decimal(qty)] for price, qty in data["b"]],
            "asks": [[Decimal(price), Decimal(qty)] for price, qty in data["a"]],
            "timestamp": datetime.utcnow().isoformat()
        }


# Global Binance WebSocket client instance
binance_ws_client = BinanceWebSocketClient()