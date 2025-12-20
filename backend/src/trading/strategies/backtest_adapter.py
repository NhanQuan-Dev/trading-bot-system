"""
Backtest Strategy Adapter.

This module provides an adapter to convert strategy implementations
into the signal function format required by the BacktestEngine.
"""
from typing import Dict, Any, Optional, Callable, List
from uuid import UUID
import logging

logger = logging.getLogger(__name__)


# Strategy ID to class name mapping (matches seed_strategies.py)
STRATEGY_ID_TO_NAME = {
    "00000000-0000-0000-0000-000000000001": "Grid Trading",
    "00000000-0000-0000-0000-000000000002": "Momentum Strategy",
    "00000000-0000-0000-0000-000000000003": "Mean Reversion",
    "00000000-0000-0000-0000-000000000004": "Arbitrage",
    "00000000-0000-0000-0000-000000000005": "Scalping",
}


class BacktestStrategyAdapter:
    """
    Adapter that converts live trading strategies to backtest signal functions.
    
    Since live strategies use async on_tick with exchange gateway,
    we need a simplified synchronous version for backtesting.
    """
    
    def __init__(self, strategy_name: str, config: Dict[str, Any] = None):
        self.strategy_name = strategy_name
        self.config = config or {}
        self.history: List[Dict] = []
        self._setup_strategy()
    
    def _setup_strategy(self):
        """Initialize strategy-specific parameters."""
        if self.strategy_name == "Scalping":
            self.ema_fast = int(self.config.get("ema_fast", 5))
            self.ema_slow = int(self.config.get("ema_slow", 13))
            self.min_history = self.ema_slow + 5
            
        elif self.strategy_name == "Grid Trading":
            self.grid_levels = int(self.config.get("grid_levels", 10))
            self.grid_step_pct = float(self.config.get("grid_step", 1.0))
            self.last_grid_level = None
            
        elif self.strategy_name == "Mean Reversion":
            self.bb_period = int(self.config.get("period", 20))
            self.bb_std = float(self.config.get("std_dev", 2.0))
            self.min_history = self.bb_period + 5
            
        elif self.strategy_name == "Momentum Strategy" or self.strategy_name == "Trend Following":
            self.rsi_period = int(self.config.get("period", 14))
            self.threshold = float(self.config.get("threshold", 2.0))
            self.min_history = self.rsi_period + 5
            
        elif self.strategy_name == "Arbitrage":
            # Arbitrage looks for price spreads - simplified for single symbol
            self.min_spread = float(self.config.get("min_spread", 0.5))
            self.min_history = 10
            
        else:
            # Default generic strategy
            self.min_history = 20
    
    def generate_signal(self, candle: Dict, idx: int, position: Optional[Dict]) -> Optional[Dict]:
        """
        Generate trading signal based on strategy logic.
        
        Args:
            candle: Current candle data (open, high, low, close, volume, timestamp)
            idx: Candle index in the sequence
            position: Current open position or None
            
        Returns:
            Signal dict {"type": "buy"|"sell"|"close"} or None
        """
        # Add candle to history
        self.history.append({
            "open": float(candle.get("open", 0)),
            "high": float(candle.get("high", 0)),
            "low": float(candle.get("low", 0)),
            "close": float(candle.get("close", 0)),
            "volume": float(candle.get("volume", 0)),
        })
        
        # Limit history size
        if len(self.history) > 200:
            self.history.pop(0)
        
        # Need minimum history
        if len(self.history) < getattr(self, 'min_history', 20):
            return None
        
        # Route to strategy-specific logic
        if self.strategy_name == "Scalping":
            return self._scalping_signal(position)
        elif self.strategy_name == "Grid Trading":
            return self._grid_trading_signal(position)
        elif self.strategy_name == "Mean Reversion":
            return self._mean_reversion_signal(position)
        elif self.strategy_name in ("Momentum Strategy", "Trend Following"):
            return self._momentum_signal(position)
        elif self.strategy_name == "Arbitrage":
            return self._arbitrage_signal(position)
        else:
            return self._default_signal(idx, position)
    
    def _scalping_signal(self, position: Optional[Dict]) -> Optional[Dict]:
        """Scalping: EMA crossover strategy."""
        closes = [c["close"] for c in self.history]
        
        # Calculate EMAs
        ema_fast = self._ema(closes, self.ema_fast)
        ema_slow = self._ema(closes, self.ema_slow)
        
        if len(ema_fast) < 2 or len(ema_slow) < 2:
            return None
        
        # Crossover detection
        prev_fast, curr_fast = ema_fast[-2], ema_fast[-1]
        prev_slow, curr_slow = ema_slow[-2], ema_slow[-1]
        
        # Fast crosses above slow -> BUY
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            if not position:
                return {"type": "buy"}
        
        # Fast crosses below slow -> CLOSE/SELL
        elif prev_fast >= prev_slow and curr_fast < curr_slow:
            if position:
                return {"type": "close"}
        
        return None
    
    def _grid_trading_signal(self, position: Optional[Dict]) -> Optional[Dict]:
        """Grid Trading: Buy/sell at price levels."""
        if len(self.history) < 2:
            return None
            
        current_price = self.history[-1]["close"]
        prev_price = self.history[-2]["close"]
        
        # Calculate grid level (simplified: based on percentage from starting price)
        base_price = self.history[0]["close"]
        step = base_price * (self.grid_step_pct / 100)
        
        current_level = int((current_price - base_price) / step) if step > 0 else 0
        prev_level = int((prev_price - base_price) / step) if step > 0 else 0
        
        # Price crossed up a level -> SELL
        if current_level > prev_level:
            if position:
                return {"type": "close"}
        
        # Price crossed down a level -> BUY
        elif current_level < prev_level:
            if not position:
                return {"type": "buy"}
        
        return None
    
    def _mean_reversion_signal(self, position: Optional[Dict]) -> Optional[Dict]:
        """Mean Reversion: Buy at lower BB, sell at upper BB."""
        closes = [c["close"] for c in self.history]
        
        if len(closes) < self.bb_period:
            return None
        
        # Calculate Bollinger Bands
        sma = sum(closes[-self.bb_period:]) / self.bb_period
        variance = sum((c - sma) ** 2 for c in closes[-self.bb_period:]) / self.bb_period
        std_dev = variance ** 0.5
        
        upper_band = sma + (self.bb_std * std_dev)
        lower_band = sma - (self.bb_std * std_dev)
        
        current_price = closes[-1]
        
        # Price below lower band -> BUY
        if current_price <= lower_band:
            if not position:
                return {"type": "buy"}
        
        # Price above upper band -> CLOSE
        elif current_price >= upper_band:
            if position:
                return {"type": "close"}
        
        return None
    
    def _momentum_signal(self, position: Optional[Dict]) -> Optional[Dict]:
        """Momentum/Trend Following: RSI-based signals."""
        closes = [c["close"] for c in self.history]
        
        if len(closes) < self.rsi_period + 1:
            return None
        
        # Calculate RSI
        rsi = self._rsi(closes, self.rsi_period)
        
        if rsi is None:
            return None
        
        # RSI below 30 -> oversold -> BUY
        if rsi < 30:
            if not position:
                return {"type": "buy"}
        
        # RSI above 70 -> overbought -> CLOSE
        elif rsi > 70:
            if position:
                return {"type": "close"}
        
        return None
    
    def _arbitrage_signal(self, position: Optional[Dict]) -> Optional[Dict]:
        """Arbitrage: Look for price volatility (simplified for single symbol)."""
        if len(self.history) < 10:
            return None
        
        # Calculate recent volatility
        closes = [c["close"] for c in self.history[-10:]]
        avg_price = sum(closes) / len(closes)
        current_price = closes[-1]
        
        deviation_pct = abs((current_price - avg_price) / avg_price) * 100
        
        # Large deviation from average -> take position
        if deviation_pct > self.min_spread:
            if current_price < avg_price and not position:
                return {"type": "buy"}  # Buy the dip
            elif current_price > avg_price and position:
                return {"type": "close"}  # Sell the spike
        
        return None
    
    def _default_signal(self, idx: int, position: Optional[Dict]) -> Optional[Dict]:
        """Default fallback strategy."""
        # Simple periodic trading
        if idx % 20 == 0 and not position:
            return {"type": "buy"}
        elif idx % 25 == 0 and position:
            return {"type": "close"}
        return None
    
    def _ema(self, data: List[float], period: int) -> List[float]:
        """Calculate Exponential Moving Average."""
        if len(data) < period:
            return []
        
        multiplier = 2 / (period + 1)
        ema = [sum(data[:period]) / period]  # Start with SMA
        
        for price in data[period:]:
            ema.append((price - ema[-1]) * multiplier + ema[-1])
        
        return ema
    
    def _rsi(self, closes: List[float], period: int) -> Optional[float]:
        """Calculate Relative Strength Index."""
        if len(closes) < period + 1:
            return None
        
        gains = []
        losses = []
        
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            gains.append(max(0, change))
            losses.append(max(0, -change))
        
        if len(gains) < period:
            return None
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))


def get_strategy_function(strategy_id: str, config: Dict[str, Any] = None) -> Callable:
    """
    Factory function to get a backtest-compatible strategy function.
    
    Args:
        strategy_id: UUID string of the strategy
        config: Optional strategy configuration
        
    Returns:
        Callable that accepts (candle, idx, position) and returns signal dict or None
    """
    strategy_name = STRATEGY_ID_TO_NAME.get(str(strategy_id), "Unknown")
    logger.info(f"Creating backtest strategy adapter for: {strategy_name} (ID: {strategy_id})")
    
    adapter = BacktestStrategyAdapter(strategy_name, config)
    
    return adapter.generate_signal
