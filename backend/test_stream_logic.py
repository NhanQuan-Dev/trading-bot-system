import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Mocking external dependencies before importing service
# We need to match the module name that binance_user_stream uses or receives
sys.modules['src.trading.infrastructure.websocket.websocket_manager'] = MagicMock()
sys.modules['src.trading.exchange.binance_adapter'] = MagicMock()
sys.modules['src.trading.infrastructure.config.settings'] = MagicMock()

# Import from src (which is in backend/)
from src.trading.infrastructure.websocket.binance_user_stream import BinanceUserStreamService, websocket_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_stream")

async def test_stream_logic():
    logger.info("--- Starting Test ---")
    
    # 1. Setup Service and Mocks
    service = BinanceUserStreamService()
    
    # Mock mocks
    mock_adapter = AsyncMock()
    mock_adapter._base_url = "https://testnet"
    mock_adapter.get_account_info.return_value = MagicMock(
        positions=[
            MagicMock(
                symbol="BTC/USDT", # ORIGINAL FORMAT from CCXT/Adapter
                quantity=0.1,
                entry_price=50000.0,
                mark_price=50000.0,
                unrealized_pnl=0.0,
                side="LONG",
                leverage=10,
                margin_type="cross",
                isolated_wallet=100.0
            )
        ]
    )
    
    # Mock websocket manager broadcast
    websocket_manager.broadcast_to_channel = AsyncMock()
    
    bot_id = "test_bot_123"
    user_id = "user_123"
    symbol = "BTC/USDT"
    
    # Manually setup active_bots dict (usually done in start_stream)
    service.active_bots[bot_id] = {
        "adapter": mock_adapter,
        "user_id": user_id,
        "symbol": "BTCUSDT", # Normalized in start_stream
        "is_testnet": True
    }
    
    # 2. Test Initial Fetch
    logger.info("Step 1: Testing _fetch_initial_positions")
    await service._fetch_initial_positions(bot_id, mock_adapter)
    
    # Verify Cache
    cached = service.cached_positions.get(bot_id, {})
    logger.info(f"Cached keys: {list(cached.keys())}")
    
    if "BTCUSDT" not in cached:
        logger.error("❌ FAILED: Position not cached with normalized key 'BTCUSDT'")
        return
    else:
        logger.info("✅ SUCCESS: Position cached with key 'BTCUSDT'")
        
    # Verify Broadcast
    websocket_manager.broadcast_to_channel.assert_called_with(
        f"positions:{bot_id}",
        {"type": "position_update", "data": list(cached.values())}
    )
    
    # 3. Test Mark Price Update
    logger.info("Step 2: Testing _handle_mark_price_update")
    websocket_manager.broadcast_to_channel.reset_mock()
    
    # Simulate Binance Mark Price Event (Raw format)
    mp_event = {
        "e": "markPriceUpdate",
        "E": 123456789,
        "s": "BTCUSDT", # Binance always sends no stash
        "p": "55000.00", # Price moved up 10%
        "P": "55000.00",
        "i": "55050.00",
        "r": "0.0003"
    }
    
    await service._handle_mark_price_update(bot_id, mp_event)
    
    # Verify Update
    updated_pos = service.cached_positions[bot_id]["BTCUSDT"]
    logger.info(f"Updated Mark Price: {updated_pos['mark_price']}")
    logger.info(f"Updated PnL: {updated_pos['unrealized_pnl']}")
    
    expected_pnl = (55000.0 - 50000.0) * 0.1 # 500
    if updated_pos['mark_price'] == 55000.0 and updated_pos['unrealized_pnl'] == expected_pnl:
         logger.info("✅ SUCCESS: Position updated correctly")
    else:
         logger.error(f"❌ FAILED: Expected Price 55000, got {updated_pos['mark_price']}")
         logger.error(f"❌ FAILED: Expected PnL {expected_pnl}, got {updated_pos['unrealized_pnl']}")

    # Verify Broadcast
    if websocket_manager.broadcast_to_channel.called:
        logger.info("✅ SUCCESS: Broadcast called after update")
    else:
        logger.error("❌ FAILED: No broadcast after update")

if __name__ == "__main__":
    asyncio.run(test_stream_logic())
