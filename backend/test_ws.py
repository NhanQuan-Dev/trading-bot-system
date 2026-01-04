#!/usr/bin/env python3
"""Test Binance Futures WebSocket connection."""

import asyncio
import websockets
import json

async def test_mark_price_stream():
    """Test Mark Price stream connection."""
    # Testnet URL
    symbol = "btcusdt"
    ws_url = f"wss://fstream.binancefuture.com/ws/{symbol}@markPrice@1s"
    
    print(f"Connecting to: {ws_url}")
    
    try:
        async with websockets.connect(ws_url) as ws:
            print("✅ Connected successfully!")
            
            # Receive 5 messages
            for i in range(5):
                message = await ws.recv()
                data = json.loads(message)
                print(f"[{i+1}] Mark Price: {data.get('p', 'N/A')} | Symbol: {data.get('s', 'N/A')}")
                
        print("✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mark_price_stream())
