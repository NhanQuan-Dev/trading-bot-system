
from typing import Dict, Any, Optional, Callable, List
from uuid import UUID
import logging
import asyncio
from datetime import datetime

# Import the registry to access dynamic strategies
from .registry import registry

logger = logging.getLogger(__name__)


# Strategy ID to class name mapping removed as per user request (legacy)



# ... (Original imports)



class BacktestStrategyAdapter:
    """
    Adapter that converts live trading strategies to backtest signal functions.
    """
    
    def __init__(self, strategy_name: str, config: Dict[str, Any] = None, code_content: str = None):
        self.strategy_name = strategy_name
        self.config = config or {}
        self.history: List[Dict] = []
        self.strategy_instance = None
        self._init_error = None
        
        # 1. Start with Dynamic Loading (Priority)
        if code_content:
            try:
                self._load_dynamic_strategy(code_content)
                if self.strategy_instance:
                    logger.info(f"Successfully loaded Custom Strategy from DB Code.")
                    self._setup_strategy()
                    return 
            except Exception as e:
                logger.error(f"Failed to load dynamic strategy: {e}")
                self._init_error = f"Dynamic Load Error: {e}"
                # Fallthrough to registry lookup
        
        # 2. Fallback to Registry Lookup (Legacy/File-based)
        try:
            cls = registry.get_strategy_class(strategy_name)
            if cls:
                # Minimal mock for exchange since backtest doesn't use it directly here
                # but strategies might store it
                class MockExchange:
                    id = "backtest_sim"
                
                self.strategy_instance = cls(MockExchange(), self.config)
                logger.info(f"Initialized Backtest Adapter with real strategy: {strategy_name}")
            else:
                msg = f"Strategy '{strategy_name}' not found. Available: {list(registry.strategies.keys())}"
                logger.error(msg)
                raise ValueError(msg)
        except Exception as e:
            logger.error(f"Could not instantiate strategy {strategy_name}: {e}")
            raise RuntimeError(f"Failed to initialize strategy {strategy_name}: {e}")

        self._setup_strategy()
    
    def _load_dynamic_strategy(self, code: str):
        """Load strategy class from code string."""
        import traceback
        
        # Try multiple import paths for StrategyBase (handles different execution contexts)
        StrategyBase = None
        try:
            from ..base import StrategyBase
        except ImportError:
            try:
                from trading.strategies.base import StrategyBase
            except ImportError:
                try:
                    from src.trading.strategies.base import StrategyBase
                except ImportError:
                    from backend.src.trading.strategies.base import StrategyBase
        
        logger.info(f"[DynamicLoader] Attempting to load strategy from code ({len(code)} chars)")
        
        # Create isolated namespace with necessary context
        namespace = {
            'StrategyBase': StrategyBase,
            'Decimal': __import__('decimal').Decimal,
            'pd': __import__('pandas'),
            'ta': __import__('pandas_ta'),
            'np': __import__('numpy'),
            'logging': __import__('logging'),
            'logger': __import__('logging').getLogger('dynamic_strategy'),
            'Optional': Optional,
            'Dict': Dict,
            'Any': Any,
            'List': List,
            'datetime': __import__('datetime').datetime,
            'timedelta': __import__('datetime').timedelta,
            'math': __import__('math'),
        }
        
        try:
            # Execute Code
            exec(code, namespace)
            exec(code, namespace)
            logger.info(f"[DynamicLoader] Code executed successfully. Namespace keys: {list(namespace.keys())}")
            
            # DEBUG: Print types of all objects in namespace
            for k, v in namespace.items():
                if not k.startswith("__"):
                    logger.info(f"DEBUG_NS: {k} -> Type: {type(v)} | Base: {v.__base__ if isinstance(v, type) else 'N/A'}")
        except Exception as exec_err:
            logger.error(f"[DynamicLoader] exec() failed: {exec_err}")
            logger.error(f"[DynamicLoader] Traceback: {traceback.format_exc()}")
            raise
        
        # Find Strategy Class
        target_cls = None
        for name, obj in namespace.items():
            # Check 1: Strict Subclass (if inheritance worked)
            is_valid = False
            # Fix: Explicitly skip StrategyBase by name to avoid Abstract Class Instantiation error
            if isinstance(obj, type) and name != "StrategyBase" and obj is not StrategyBase:
                if issubclass(obj, StrategyBase):
                    is_valid = True
                # Check 2: Name Heuristic (if inheritance failed due to reload/import issues)
                # Matches "MartingaleSmartMTF" or anything ending in "Strategy"
                elif "Strategy" in name or name == "MartingaleSmartMTF":
                    # Verify it has required methods
                    if hasattr(obj, 'on_tick') or hasattr(obj, 'calculate_signal'):
                        is_valid = True
            
            if is_valid:
                logger.info(f"[/DynamicLoader] Found strategy class: {name}")
                target_cls = obj
                break
                
        if target_cls:
            class MockExchange:
                id = "backtest_sim"
            self.strategy_instance = target_cls(MockExchange(), self.config)
            logger.info(f"[DynamicLoader] Strategy instantiated successfully: {target_cls.name}")
        else:
            raise ValueError("No class inheriting from StrategyBase found in code.")

    def _setup_strategy(self):
        """Initialize strategy-specific parameters."""
        if self.strategy_name == "HighFrequencyTest":
             # Initialize params from config or defaults
             self.tick_interval = 1
             self.max_position = float(self.config.get("max_position", 0.01))
             self.min_history = 1 # Needs very little history
        
        else:
            # Default generic strategy
            self.min_history = 20
    
    @property
    def timeframe_mode(self) -> str:
        if self.strategy_instance:
            return getattr(self.strategy_instance, 'timeframe_mode', 'single')
        return 'single'

    @property
    def required_timeframes(self) -> List[str]:
        if self.strategy_instance:
            return getattr(self.strategy_instance, 'required_timeframes', [])
        return []

    def pre_calculate(self, candles: List[Dict[str, Any]], htf_candles: Optional[Dict[str, List[Dict[str, Any]]]] = None) -> None:
        """Proxy pre_calculate call to the underlying strategy instance."""
        if self.strategy_instance and hasattr(self.strategy_instance, 'pre_calculate'):
            try:
                # Use inspection to handle different method signatures
                import inspect
                sig = inspect.signature(self.strategy_instance.pre_calculate)
                
                if 'htf_candles' in sig.parameters:
                    self.strategy_instance.pre_calculate(candles, htf_candles=htf_candles)
                else:
                    self.strategy_instance.pre_calculate(candles)
                
                logger.debug(f"Pre-calculation completed for strategy: {self.strategy_name}")
            except Exception as e:
                logger.error(f"Error in strategy pre_calculate: {e}")

    def __call__(self, *args, **kwargs) -> Optional[Dict]:
        """Allow the adapter itself to be called like a function."""
        return self.generate_signal(*args, **kwargs)

    def generate_signal(self, candle: Dict, idx: int, position: Optional[Dict], multi_tf_context: Optional[Any] = None) -> Optional[Dict]:
        """
        Generate trading signal.
        
        Args:
            candle: Current candle (execution timeframe)
            idx: Index in the execution timeframe
            position: Current position
            multi_tf_context: Optional MultiTimeframeContext for 'multi' strategies
        """
        # Add candle to history (Note: No longer capped, but only used if strategy uses it)
        self.history.append({
            "open": float(candle.get("open", 0)),
            "high": float(candle.get("high", 0)),
            "low": float(candle.get("low", 0)),
            "close": float(candle.get("close", 0)),
            "volume": float(candle.get("volume", 0)),
            "timestamp": candle.get("timestamp")
        })
        
        # Use Dynamic Strategy Logic if available
        if self.strategy_instance and hasattr(self.strategy_instance, 'calculate_signal'):
             if self.timeframe_mode == 'multi' and multi_tf_context:
                 return self.strategy_instance.calculate_signal(candle, idx, position, multi_tf_context=multi_tf_context)
             return self.strategy_instance.calculate_signal(candle, idx, position)

        # Legacy Hardcoded Logic Fallbacks
        
        # Need minimum history
        if len(self.history) < getattr(self, 'min_history', 20):
            return None
        
        # Route to logic
        if self.strategy_name == "HighFrequencyTest":
            return self._high_frequency_test_signal(position)
        else:
            return self._default_signal(idx, position)

    def _high_frequency_test_signal(self, position: Optional[Any]) -> Optional[Dict]:
        """
        High Frequency Test specific logic reimplemented for Backtester.
        Logic: Match high_frequency_test.py strictly (LONG/SHORT based).
        """
        # 1. Recover State (Mocking Strategy State)
        pos_qty = 0.0
        is_long = False
        is_short = False
        
        if position:
            try:
                # BacktestPosition uses strictly Uppercase LONG/SHORT now
                pos_qty = float(position.quantity)
                d_str = str(position.direction).upper() 
                
                if "LONG" in d_str:
                    pos_qty = pos_qty # Positive
                    is_long = True
                else:
                    pos_qty = -pos_qty # Negative
                    is_short = True
            except AttributeError:
                pass

        # Sync persistent state with strategy variable names
        if not hasattr(self, '_hft_last_side'):
             self._hft_last_side = None 

        logger.info(f"DEBUG_HFT: pos_qty={pos_qty}, max_pos={self.max_position}, last_side={self._hft_last_side}")

        # 2. Call Logic (Mirrors Strategy._determine_direction)
        # Returns "LONG" or "SHORT"
        direction = self._determine_direction(pos_qty)
        
        if not direction:
            return None
            
        # 3. Map Strategy "Direction" to Backtest "Signal Type"
        # IMPORTANT: Only update _hft_last_side when we actually OPEN a new position
        # NOT when we close an existing one!
        
        if direction == "LONG":
            if is_short: 
                # Closing SHORT - do NOT update last_side yet
                return {"type": "close_position"}
            if not is_long:
                # Actually opening LONG - NOW update last_side
                self._hft_last_side = "LONG"
                return {
                    "type": "open_long",
                    "metadata": {
                        "reason": "Alternating Logic: Last was SHORT",
                        "condition": "Position <= Max Limit",
                        "algo_state": self._hft_last_side
                    }
                }
            return None

        elif direction == "SHORT":
            if is_long:
                # Closing LONG - do NOT update last_side yet
                return {"type": "close_position"}
            if not is_short:
                # Actually opening SHORT - NOW update last_side
                self._hft_last_side = "SHORT"
                return {
                    "type": "open_short",
                    "metadata": {
                        "reason": "Alternating Logic: Last was LONG",
                        "condition": "Position >= Min Limit",
                        "algo_state": self._hft_last_side
                    }
                }
            return None
            
        return None

    def _determine_direction(self, current_pos_qty: float) -> Optional[str]:
        """
        Determine next trade direction based on current position and alternating logic.
        Matches high_frequency_test.py _determine_direction exactly.
        """
        # Safety: Check position limits
        if current_pos_qty >= self.max_position:
            # Too much LONG position, must go SHORT
            return "SHORT"
        
        if current_pos_qty <= -self.max_position:
            # Too much SHORT position, must go LONG
            return "LONG"
        
        # Alternating logic
        if self._hft_last_side is None or self._hft_last_side == "SHORT":
            return "LONG"
        else:
            return "SHORT"

    # ... (Keep existing methods)

    


    

    
    
    def _default_signal(self, idx: int, position: Optional[Dict]) -> Optional[Dict]:
        """Default fallback strategy."""
        # Simple periodic trading
        if idx % 20 == 0 and not position:
            metadata = {
                 "reason": "Fallback Strategy (Generic)",
                 "info": "The selected strategy failed to load or is not implemented."
            }
            if hasattr(self, '_init_error') and self._init_error:
                metadata['error'] = str(self._init_error)
                
            return {
                "type": "open_long",
                "metadata": metadata
            }
        elif idx % 25 == 0 and position:
            return {"type": "close_position"}
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


def get_strategy_function(strategy_id: str, strategy_name: str = None, config: Dict[str, Any] = None, code_content: str = None) -> Callable:
    """
    Factory function to get a backtest-compatible strategy function.
    
    Args:
        strategy_id: UUID string of the strategy
        strategy_name: Name of the strategy to load (overrides config)
        config: Optional strategy configuration
        
    Returns:
        Callable that accepts (candle, idx, position) and returns signal dict or None
    """
    
    result_strategy_name = "Unknown" 
    
    if strategy_name:
        result_strategy_name = strategy_name
    elif config and "strategy_name" in config:
        result_strategy_name = config["strategy_name"]
    
    # If the strategy is unknown, do not default to HighFrequencyTest.
    # It will fallback to _default_signal in the adapter if not found in registry.
    if result_strategy_name == "Unknown":
        logger.warning(f"Strategy name not found for ID: {strategy_id}. Using default generic strategy.")

    logger.info(f"Creating backtest strategy adapter for: {result_strategy_name} (ID: {strategy_id})")
    
    adapter = BacktestStrategyAdapter(result_strategy_name, config, code_content)
    
    return adapter
