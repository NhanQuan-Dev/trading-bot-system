import importlib
import inspect
import pkgutil
import logging
from typing import Dict, List, Type, Any
from pathlib import Path
from .base import StrategyBase

logger = logging.getLogger(__name__)

class StrategyRegistry:
    def __init__(self, strategies_dir: str = "implementations"):
        """
        Initialize the registry.
        
        Args:
            strategies_dir: Directory containing strategy implementations (relative to this file)
        """
        self.strategies: Dict[str, Type[StrategyBase]] = {}
        self._strategies_dir = strategies_dir
        self._discover_strategies()

    def _discover_strategies(self):
        """Dynamically discover strategy classes in the implementations directory."""
        current_dir = Path(__file__).parent
        impl_dir = current_dir / self._strategies_dir
        
        if not impl_dir.exists():
            print(f"DEBUG: Strategies directory {impl_dir} not found")
            return

        print(f"DEBUG: Scanning strategies in {impl_dir}")
        # Import all modules in the directory
        for item in impl_dir.iterdir():
            if item.is_file() and item.suffix == ".py" and item.name != "__init__.py":
                module_name = f"{__package__}.{self._strategies_dir}.{item.stem}"
                # module_name = f"trading.strategies.{self._strategies_dir}.{item.stem}"
                print(f"DEBUG: Loading module {module_name}")
                try:
                    module = importlib.import_module(module_name)
                    # Scan for StrategyBase subclasses
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, StrategyBase) and 
                            obj is not StrategyBase):
                            
                            print(f"DEBUG: Registering {name}")
                            self.register(obj)
                except Exception as e:
                    print(f"DEBUG: Failed to load strategy from {item.name}: {e}")
                    logger.error(f"Failed to load strategy from {item.name}: {e}")

    def register(self, strategy_cls: Type[StrategyBase]):
        """Register a strategy class."""
        if hasattr(strategy_cls, 'name'):
            logger.info(f"Registered strategy: {strategy_cls.name}")
            self.strategies[strategy_cls.name] = strategy_cls
        else:
            logger.warning(f"Strategy class {strategy_cls} missing 'name' attribute")

    def list_strategies(self) -> List[Dict[str, Any]]:
        """List all available strategies with their metadata."""
        return [
            {
                "id": name, # using name as ID for now
                "name": name,
                "type": name, # Type is same as name
                "description": getattr(cls, 'description', 'No description available'),
                # Add mock stats for now until true stats are implemented
                "status": "inactive",
                "activeBots": 0,
                "totalTrades": 0,
                "winRate": 0,
                "avgPnl": 0,
                "totalPnl": 0,
                "sharpeRatio": 0,
                "maxDrawdown": 0,
                "profitFactor": 0,
                "avgHoldTime": "-"
            }
            for name, cls in self.strategies.items()
        ]

    def get_strategy_class(self, name: str) -> Type[StrategyBase]:
        return self.strategies.get(name)

    def register_dynamic_strategy(self, code: str, strategy_name: str = None) -> bool:
        """
        Dynamically run the code and register the Strategy class found within.
        
        Args:
            code: Python source code string
            strategy_name: Optional expected name of the strategy
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # 1. Prepare Execution Environment
            import pandas as pd
            import numpy as np
            from decimal import Decimal
            from datetime import datetime
            import math
            
            # Dependencies available to the strategy code
            # Note: For security in production, this should be restricted.
            exec_globals = {
                "pd": pd,
                "np": np,
                "Decimal": Decimal,
                "datetime": datetime,
                "math": math,
                "StrategyBase": StrategyBase,
                "logger": logging.getLogger(f"strategy.{strategy_name or 'dynamic'}"),
                # __builtins__ is included by default unless explicitly set
            }
            exec_locals = {}
            
            # 2. Execute Code
            print(f"DEBUG: Compiling dynamic strategy code...")
            exec(code, exec_globals, exec_locals)
            
            # 3. Find and Register Strategy Class
            found = False
            for name, obj in exec_locals.items():
                if (inspect.isclass(obj) and 
                    issubclass(obj, StrategyBase) and 
                    obj is not StrategyBase):
                    
                    found_name = getattr(obj, 'name', name)
                    
                    # If we expect a specific name, ensure it matches or force it?
                    # Ideally, strategy code defines correct name.
                    print(f"DEBUG: Found dynamic strategy class: {name} (Name={found_name})")
                    
                    self.register(obj)
                    found = True
            
            if not found:
                logger.warning("No valid StrategyBase subclass found in dynamic code")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to register dynamic strategy: {e}", exc_info=True)
            print(f"ERROR: Dynamic Strategy Compilation Failed: {e}")
            return False

# Global registry instance
registry = StrategyRegistry()
