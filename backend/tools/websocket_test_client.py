#!/usr/bin/env python3
"""WebSocket client test utility."""

import asyncio
import json
import logging
import websockets
from typing import Optional
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WebSocketTestClient:
    """Test client for WebSocket endpoints."""
    
    def __init__(self, base_url: str = "ws://localhost:8000"):
        self.base_url = base_url
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
    
    async def connect(self, endpoint: str, token: Optional[str] = None):
        """Connect to WebSocket endpoint."""
        url = f"{self.base_url}{endpoint}"
        if token:
            url += f"?token={token}"
        
        try:
            logger.info(f"Connecting to {url}")
            self.websocket = await websockets.connect(url)
            logger.info("Connected successfully")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            logger.info("Disconnected")
    
    async def send_message(self, message: dict):
        """Send message to WebSocket."""
        if not self.websocket:
            logger.error("Not connected to WebSocket")
            return
        
        try:
            await self.websocket.send(json.dumps(message))
            logger.info(f"Sent: {message}")
        except Exception as e:
            logger.error(f"Error sending message: {e}")
    
    async def receive_message(self) -> Optional[dict]:
        """Receive message from WebSocket."""
        if not self.websocket:
            logger.error("Not connected to WebSocket")
            return None
        
        try:
            message = await self.websocket.recv()
            data = json.loads(message)
            logger.info(f"Received: {data}")
            return data
        except Exception as e:
            logger.error(f"Error receiving message: {e}")
            return None
    
    async def listen_messages(self, duration: int = 30):
        """Listen for messages for a specified duration."""
        if not self.websocket:
            logger.error("Not connected to WebSocket")
            return
        
        logger.info(f"Listening for messages for {duration} seconds...")
        
        try:
            # Listen for messages with timeout
            end_time = asyncio.get_event_loop().time() + duration
            
            while asyncio.get_event_loop().time() < end_time:
                try:
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    logger.info(f"Received: {data}")
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error receiving message: {e}")
                    break
        
        except Exception as e:
            logger.error(f"Error in listen loop: {e}")
    
    async def test_trading_websocket(self, token: str):
        """Test trading WebSocket endpoint."""
        logger.info("=== Testing Trading WebSocket ===")
        
        # Connect
        if not await self.connect("/ws/trading", token):
            return
        
        try:
            # Test ping
            await self.send_message({"type": "ping"})
            await self.receive_message()
            
            # Test subscription
            await self.send_message({
                "type": "subscribe",
                "channels": ["orders", "risk_alerts", "bot_status"]
            })
            await self.receive_message()
            
            # Test symbol subscription
            await self.send_message({
                "type": "subscribe_symbol",
                "symbols": ["BTCUSDT", "ETHUSDT"]
            })
            await self.receive_message()
            
            # Listen for updates
            await self.listen_messages(30)
            
        finally:
            await self.disconnect()
    
    async def test_market_websocket(self):
        """Test market data WebSocket endpoint."""
        logger.info("=== Testing Market WebSocket ===")
        
        # Connect (no auth required)
        if not await self.connect("/ws/market"):
            return
        
        try:
            # Test ticker subscription
            await self.send_message({
                "type": "subscribe_ticker",
                "symbols": ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
            })
            await self.receive_message()
            
            # Test trades subscription
            await self.send_message({
                "type": "subscribe_trades",
                "symbols": ["BTCUSDT"]
            })
            await self.receive_message()
            
            # Test orderbook subscription
            await self.send_message({
                "type": "subscribe_orderbook",
                "symbols": ["BTCUSDT"]
            })
            await self.receive_message()
            
            # Listen for market updates
            await self.listen_messages(60)
            
        finally:
            await self.disconnect()
    
    async def test_connection_health(self):
        """Test WebSocket connection health."""
        logger.info("=== Testing Connection Health ===")
        
        if not await self.connect("/ws/market"):
            return
        
        try:
            # Send ping every 5 seconds for 30 seconds
            for i in range(6):
                await self.send_message({"type": "ping"})
                response = await self.receive_message()
                
                if response and response.get("type") == "pong":
                    logger.info(f"Ping {i+1}/6 successful")
                else:
                    logger.warning(f"Ping {i+1}/6 failed")
                
                if i < 5:  # Don't sleep after last ping
                    await asyncio.sleep(5)
        
        finally:
            await self.disconnect()


async def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description="WebSocket Test Client")
    parser.add_argument("--url", default="ws://localhost:8000", help="WebSocket base URL")
    parser.add_argument("--token", help="JWT token for authentication")
    parser.add_argument("--test", choices=["trading", "market", "health", "all"], 
                       default="all", help="Test to run")
    
    args = parser.parse_args()
    
    client = WebSocketTestClient(args.url)
    
    try:
        if args.test in ["trading", "all"]:
            if not args.token:
                logger.warning("Skipping trading test - no token provided")
                logger.info("To test trading WebSocket, provide --token argument")
            else:
                await client.test_trading_websocket(args.token)
        
        if args.test in ["market", "all"]:
            await client.test_market_websocket()
        
        if args.test in ["health", "all"]:
            await client.test_connection_health()
    
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())