from decimal import Decimal
from typing import Any, Dict, List, Optional
import logging
from ..base import StrategyBase

logger = logging.getLogger(__name__)

class GridTradingStrategy(StrategyBase):
    name = "Grid Trading"
    description = "Profits from volatility by placing a net of buy and sell orders at fixed price levels. Best for ranging markets."

    def __init__(self, exchange, config: Dict[str, Any], on_order=None):
        super().__init__(exchange, config, on_order)
        self.upper_price = Decimal(str(config.get("upper_price", "0")))
        self.lower_price = Decimal(str(config.get("lower_price", "0")))
        self.grid_levels = int(config.get("grid_levels", "10"))
        self.quantity_per_grid = Decimal(str(config.get("quantity_per_grid", "0")))
        
        # Grid State: List of {price: Decimal, order_id: str, side: str, status: str}
        # Status: IDLE, OPEN
        self.grids: List[Dict] = []
        self._initialize_grids()

    def _initialize_grids(self, current_price: Decimal = None):
        """Calculate grid price levels."""
        # Auto-config if defaults are 0 and we have a price
        if (self.upper_price <= 0 or self.lower_price <= 0) and current_price:
             self.upper_price = current_price * Decimal("1.1") # +10%
             self.lower_price = current_price * Decimal("0.9") # -10%
             logger.info(f"[Grid] Auto-configured levels: {self.lower_price} - {self.upper_price}")

        if self.upper_price <= self.lower_price or self.grid_levels <= 0:
            if current_price: # Only warn if we attempted to init with a price
                 logger.warning("[Grid] Invalid grid parameters (Upper <= Lower)")
            return

        step = (self.upper_price - self.lower_price) / self.grid_levels
        
        self.grids = [] # Reset
        for i in range(self.grid_levels + 1):
            price = self.lower_price + (step * i)
            self.grids.append({
                "id": i,
                "price": price,
                "order_id": None,
                "side": None,
                "status": "IDLE" 
            })
        logger.info(f"[Grid] Initialized {len(self.grids)} levels from {self.lower_price} to {self.upper_price}")

    async def on_tick(self, market_data: Any):
        """
        Main Grid Loop:
        1. Sync active orders.
        2. Detect Fills (Order missing from active but was OPEN).
        3. Rebalance (Place new orders).
        """
        if not market_data or not isinstance(market_data, list):
            return

        # 1. Parse Market Data
        try:
            current_price = Decimal(str(market_data[-1][4]))
        except Exception as e:
            logger.error(f"[Grid] Error parsing price: {e}")
            return
            
        symbol = self.config.get("symbol")
        
        # 2. Sync / Poll Orders (Crucial for state)
        # In a real event-driven system, we'd get updates pushed. Here we poll.
        try:
            open_orders = await self.exchange.get_open_orders(symbol)
            open_order_ids = {str(o["orderId"]) for o in open_orders}
        except Exception as e:
            logger.error(f"[Grid] Failed to fetch open orders: {e}")
            return

        # 3. Check for Fills and Update State
        for grid in self.grids:
            if grid["status"] == "OPEN" and grid["order_id"]:
                if grid["order_id"] not in open_order_ids:
                    # Order is gone -> Assume Filled (or Cancelled, but we assume Fill for MVP logic)
                    logger.info(f"[Grid] Order {grid['order_id']} filled at {grid['price']}")
                    grid["status"] = "IDLE"
                    grid["order_id"] = None
                    # TODO: If BUY filled, set next action to SELL one step higher?
                    # For simple accumulation, we just reset to IDLE and let logic decide.

        # 4. Place Orders
        for grid in self.grids:
            if grid["status"] == "IDLE":
                # Decision Logic
                if grid["price"] < current_price:
                    # Below Market -> Place BUY
                    # Only if not too close to current price (spread check usually needed)
                    # Simple check: 0.5% distance
                    if (current_price - grid["price"]) / grid["price"] > Decimal("0.005"):
                        await self._place_order(symbol, grid, "BUY")
                
                # elif grid["price"] > current_price:
                    # Above Market -> Place SELL
                    # Only if we have inventory? 
                    # For MVP, let's skip SELLs to avoid "Insufficient Funds" errors without balance tracking.
                    # logger.debug(f"[Grid] Level {grid['price']} above market, skipping SELL")
                    pass

    async def _place_order(self, symbol, grid, side):
        """Helper to place and track order."""
        try:
            res = await self.buy(symbol, self.quantity_per_grid, price=grid["price"])
            if res and "orderId" in res:
                grid["status"] = "OPEN"
                grid["side"] = side
                grid["order_id"] = str(res["orderId"])
                logger.info(f"[Grid] Placed {side} at {grid['price']}")
        except Exception as e:
            logger.error(f"[Grid] Failed to place {side} at {grid['price']}: {e}")

    def calculate_signal(self, candle: Dict, idx: int, position: Any) -> Optional[Dict]:
        """Backtest signal calculation."""
        current_price = Decimal(str(candle['close']))
        
        # 1. Check if we need to initialize grids
        if not self.grids:
            self._initialize_grids(current_price)
            
        # 2. Check for fills against virtual grid
        # In backtest, we don't have real open orders. We check price action.
        signal = None
        quantity = Decimal("0")
        reason = ""
        
        # Simple simulated grid logic:
        # If price drops to a lower grid level -> Buy
        # If price rises to a higher grid level -> Sell (if we have position)
        
        # Find closest grid level below current price
        active_level_idx = -1
        for i, grid in enumerate(self.grids):
            if current_price >= grid["price"]:
                active_level_idx = i
            else:
                break
                
        # If price crossed a level downwards (Buy zone)
        # This is simplified. Real grid needs state memory of "bought at level X".
        # For this template, we just buy if price is in lower half of grid.
        
        mid_price = (self.upper_price + self.lower_price) / 2
        
        if current_price < mid_price and not position:
            return {
                "type": "open_long",
                "quantity": float(self.quantity_per_grid * 5), # Simulate buying multiple grids
                "metadata": {
                    "strategy": "Grid Trading",
                    "reason": "Price in Buy Zone (Lower Half)",
                    "price": float(current_price)
                }
            }
        elif current_price > mid_price and position:
            return {
                "type": "close_position",
                "metadata": {
                    "strategy": "Grid Trading",
                    "reason": "Price in Sell Zone (Upper Half)",
                    "price": float(current_price)
                }
            }
            
        return None

