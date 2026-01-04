from decimal import Decimal
from typing import Any, Dict
import logging
from ..base import StrategyBase

logger = logging.getLogger(__name__)

class HighFrequencyTestStrategy(StrategyBase):
    """
    High-Frequency Test Strategy
    
    Purpose: Generate maximum number of trades in minimum time for system testing.
    Logic: Alternate BUY/SELL every N ticks regardless of price movement.
    
    WARNING: This is NOT a profitable strategy. Only for testing infrastructure.
    """
    
    name = "HighFrequencyTest"
    description = "Test strategy that alternates BUY/SELL every few ticks to generate maximum trades quickly. FOR TESTING ONLY!"

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
        self.last_side = None  # Track last trade to alternate
        
        # Position tracking (simplified)
        self.position_qty = Decimal("0")  # Positive = LONG, Negative = SHORT
        self.max_position = Decimal(str(config.get("max_position", "0.01")))  # Max position size
        
        logger.info(f"[{self.name}] Initialized - will trade every {self.tick_interval} ticks")

    async def on_tick(self, market_data: Any):
        """
        Execute trades at fixed intervals alternating BUY/SELL.
        
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
        
        # Determine trade side using alternating logic
        side = self._determine_side()
        print(f"[{self.name}] Determined side: {side}, position_qty={self.position_qty}")
        
        if not side:
            print(f"[{self.name}] No side (position limit reached), waiting...")
            logger.info(f"[{self.name}] Position limit reached [{self.position_qty}], waiting...")
            return
        
        # Execute trade
        try:
            # Calculate price
            if self.use_market_orders:
                price = None
            else:
                # Grid/Maker Mode: Place order at spread
                spread = Decimal("0.0005") # 0.05% spread
                if side == "BUY":
                    price = current_price * (Decimal("1") - spread)
                else:
                    price = current_price * (Decimal("1") + spread)
                
                # Round to 1 decimal for BTC/USDT (Tick Size = 0.1)
                price = price.quantize(Decimal("0.1"))

            print(f"[{self.name}] Executing {side} order: qty={self.quantity}, price={price or 'MARKET'}")
            
            if side == "BUY":
                logger.info(f"[{self.name}] Trade #{self.trade_count + 1} - BUY {self.quantity} @ {price or 'MARKET'}")
                print(f"[{self.name}] Calling self.buy({symbol}, {self.quantity}, price={price})...")
                await self.buy(symbol, self.quantity, price=price)
                if self.use_market_orders:
                    self.position_qty += self.quantity # Only update position immediately if market order
                self.last_side = "BUY"
                print(f"[{self.name}] BUY order placed successfully!")
                
            else:  # SELL
                logger.info(f"[{self.name}] Trade #{self.trade_count + 1} - SELL {self.quantity} @ {price or 'MARKET'}")
                print(f"[{self.name}] Calling self.sell({symbol}, {self.quantity}, price={price})...")
                await self.sell(symbol, self.quantity, price=price)
                if self.use_market_orders:
                    self.position_qty -= self.quantity # Only update position immediately if market order
                self.last_side = "SELL"
                print(f"[{self.name}] SELL order placed successfully!")
            
            self.trade_count += 1
            
            print(f"[{self.name}] Trade #{self.trade_count} COMPLETE | Position: {self.position_qty}")
            logger.info(f"[{self.name}] Position: {self.position_qty} | Total Trades: {self.trade_count}")
            
        except Exception as e:
            print(f"[{self.name}] EXCEPTION during trade execution: {e}")
            logger.error(f"[{self.name}] Trade execution failed: {e}")
    
    def _determine_side(self) -> str:
        """
        Determine next trade side based on current position and alternating logic.
        
        Logic:
        1. If no position, start with BUY
        2. If position too long, force SELL
        3. If position too short, force BUY
        4. Otherwise, alternate from last trade
        
        Returns:
            "BUY", "SELL", or None if position limit reached
        """
        # Safety: Check position limits
        if self.position_qty >= self.max_position:
            # Too much LONG position, must SELL
            return "SELL"
        
        if self.position_qty <= -self.max_position:
            # Too much SHORT position, must BUY
            return "BUY"
        
        # Alternating logic
        if self.last_side is None or self.last_side == "SELL":
            return "BUY"
        else:
            return "SELL"
