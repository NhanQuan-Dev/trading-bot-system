from decimal import Decimal
from typing import Any, Dict, Optional
import logging
from ..base import StrategyBase

logger = logging.getLogger(__name__)

class HighFrequencyTestStrategy(StrategyBase):
    """
    High-Frequency Test Strategy
    
    Purpose: Generate maximum number of trades in minimum time for system testing.
    Logic: Alternate LONG/SHORT every N ticks regardless of price movement.
    
    WARNING: This is NOT a profitable strategy. Only for testing infrastructure.
    """
    
    name = "HighFrequencyTest"
    description = "Test strategy that alternates LONG/SHORT every few ticks to generate maximum trades quickly. FOR TESTING ONLY!"

    def __init__(self, exchange, config: Dict[str, Any], on_order=None):
        super().__init__(exchange, config, on_order)
        
        # Configuration
        self.tick_interval = 1 # Force 1 tick for fast testing (ignore config)
        self.quantity = Decimal(str(config.get("quantity", "0.01")))
        self.use_market_orders = config.get("use_market_orders", True)  # Faster fills
        
        # Debug log
        print(f"[HighFrequencyTest] INIT: quantity={self.quantity}, tick_interval={self.tick_interval}, use_market_orders={self.use_market_orders}")
        
        # State tracking
        self.tick_count = 0
        self.trade_count = 0
        self.last_side = None  # Track last direction (LONG/SHORT) to alternate
        
        # Position tracking (simplified)
        self.position_qty = Decimal("0")  # Positive = LONG, Negative = SHORT
        self.max_position = Decimal(str(config.get("max_position", "0.01")))  # Max position size
        
        logger.info(f"[{self.name}] Initialized - will trade every {self.tick_interval} ticks")

    async def on_tick(self, market_data: Any):
        """
        Execute trades at fixed intervals alternating LONG/SHORT.
        
        Market Data Formats:
        - Dict: {"symbol": "BTCUSDT", "price": 43000.0, ...}
        - List of candles: [[timestamp, open, high, low, close, volume], ...]
        """
        # Increment tick counter
        self.tick_count += 1
        print(f"[{self.name}] on_tick() called - tick_count={self.tick_count}, tick_interval={self.tick_interval}")
        
        # Only trade every N ticks
        if self.tick_count % self.tick_interval != 0:
            print(f"[{self.name}] Skipping - not yet time to trade (tick {self.tick_count} % {self.tick_interval} != 0)")
            return
        
        print(f"[{self.name}] TIME TO TRADE! (tick {self.tick_count})")
        
        # Get current price and symbol
        symbol = None
        current_price = None
        
        try:
            if isinstance(market_data, dict):
                symbol = market_data.get("symbol")
                current_price = Decimal(str(market_data.get("price", 0)))
                print(f"[{self.name}] Market data is dict: symbol={symbol}, price={current_price}")
            elif isinstance(market_data, list) and len(market_data) > 0:
                # Candle format: [timestamp, open, high, low, close, volume]
                symbol = self.config.get("symbol", "BTCUSDT")
                current_price = Decimal(str(market_data[-1][4]))  # Close price
                print(f"[{self.name}] Market data is candles list: symbol={symbol}, price={current_price}, candle_count={len(market_data)}")
            else:
                print(f"[{self.name}] ERROR: Unknown market data format: {type(market_data)}")
                logger.warning(f"[{self.name}] Unknown market data format: {type(market_data)}")
                return
                
            if not symbol or current_price <= 0:
                print(f"[{self.name}] ERROR: Invalid data - symbol={symbol}, price={current_price}")
                logger.warning(f"[{self.name}] Invalid data - symbol: {symbol}, price: {current_price}")
                return
                
        except Exception as e:
            print(f"[{self.name}] EXCEPTION parsing market data: {e}")
            logger.error(f"[{self.name}] Error parsing market data: {e}")
            return
        
        # Determine trade direction (LONG/SHORT)
        direction = self._determine_direction()
        print(f"[{self.name}] Determined direction: {direction}, position_qty={self.position_qty}")
        
        if not direction:
            print(f"[{self.name}] No direction (position limit reached), waiting...")
            logger.info(f"[{self.name}] Position limit reached [{self.position_qty}], waiting...")
            return
        
        # Execute trade
        try:
            # Calculate price
            price = None
            if not self.use_market_orders:
                # Grid/Maker Mode: Place order at spread
                spread = Decimal("0.0005") # 0.05% spread
                if direction == "LONG":
                    price = current_price * (Decimal("1") - spread)
                else:
                    price = current_price * (Decimal("1") + spread)
                
                # Round to 1 decimal for BTC/USDT (Tick Size = 0.1)
                price = price.quantize(Decimal("0.1"))

            print(f"[{self.name}] Executing {direction} action: qty={self.quantity}, price={price or 'MARKET'}")
            
            if direction == "LONG":
                self.last_side = "LONG"
                await self._open_long(symbol, self.quantity, price=price)
                
            else:  # SHORT
                self.last_side = "SHORT"
                await self._open_short(symbol, self.quantity, price=price)
            
            self.trade_count += 1
            
            print(f"[{self.name}] Trade #{self.trade_count} COMPLETE | Position: {self.position_qty}")
            logger.info(f"[{self.name}] Position: {self.position_qty} | Total Trades: {self.trade_count}")
            
        except Exception as e:
            print(f"[{self.name}] EXCEPTION during trade execution: {e}")
            logger.error(f"[{self.name}] Trade execution failed: {e}")
            
    async def _open_long(self, symbol, quantity, price=None):
        """Execute Open LONG action."""
        logger.info(f"[{self.name}] Action: OPEN LONG {quantity} @ {price or 'MARKET'}")
        await self.buy(symbol, quantity, price=price)
        if self.use_market_orders:
            self.position_qty += quantity
            print(f"[{self.name}] OPEN LONG executed successfully!")

    async def _open_short(self, symbol, quantity, price=None):
        """Execute Open SHORT action."""
        logger.info(f"[{self.name}] Action: OPEN SHORT {quantity} @ {price or 'MARKET'}")
        await self.sell(symbol, quantity, price=price)
        if self.use_market_orders:
            self.position_qty -= quantity
            print(f"[{self.name}] OPEN SHORT executed successfully!")
    
    def _determine_direction(self) -> str:
        """
        Determine next trade direction based on current position and alternating logic.
        
        Logic:
        1. If no position, start with LONG
        2. If position too LONG, force SHORT
        3. If position too SHORT, force LONG
        4. Otherwise, alternate from last direction
        
        Returns:
            "LONG", "SHORT", or None if position limit reached
        """
        # Safety: Check position limits
        if self.position_qty >= self.max_position:
            # Too much LONG position, must go SHORT
            return "SHORT"
        
        if self.position_qty <= -self.max_position:
            # Too much SHORT position, must go LONG
            return "LONG"
        
        # Alternating logic
        if self.last_side is None or self.last_side == "SHORT":
            return "LONG"
        else:
            return "SHORT"

