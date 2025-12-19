# STRATEGY MANAGEMENT SYSTEM - COMPLETE SPECIFICATION

## Document Information
- **Version**: 1.0
- **Date**: December 18, 2025
- **Status**: Draft for Review
- **Project**: Trading Bot Platform - Strategy System

---

## 1. Executive Summary

### 1.1 Goal
Xây dựng **Strategy System** cho trading_bot_platform với các mục tiêu chính:

1. **Strategy = File-based Plugin**: Mỗi strategy là một file code Python độc lập
2. **Runtime Management**: Hệ thống có khả năng load, list, validate, và execute strategies động
3. **Architecture Compliance**: Strategy phải sử dụng các service/port có sẵn (OrderService, PositionService, RiskService, MarketData) - KHÔNG được gọi trực tiếp Exchange API
4. **Full Management**: Frontend cung cấp UI đầy đủ để quản lý strategies (CRUD, activate/deactivate, monitor performance)

### 1.2 Non-Goals
- ❌ Cho phép user upload code tùy ý (security risk - chưa có sandbox)
- ❌ Strategy tự thao tác DB/Exchange trực tiếp (phá vỡ architecture)
- ❌ Strategy tự tạo custom UI (chỉ cung cấp metadata + params schema)

### 1.3 Success Criteria
- ✅ Admin có thể thêm strategy mới bằng cách tạo file Python
- ✅ System tự động discover và register strategies khi khởi động
- ✅ User có thể xem danh sách strategies, configure params, và attach vào bot
- ✅ Bot có thể run strategy đã chọn với params đã config
- ✅ Strategy execution được monitor real-time (signals, orders, performance)

---

## 2. System Architecture

### 2.1 High-Level Flow
```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Strategy     │  │ Bot Config   │  │ Bot Monitor  │      │
│  │ Management   │  │ (attach      │  │ (signals,    │      │
│  │ (CRUD)       │  │ strategy)    │  │ orders)      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                           │ REST API
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Strategy Management Layer                │   │
│  │  - Strategy CRUD Use Cases                          │   │
│  │  - Strategy Registry (discover & load plugins)      │   │
│  │  - Strategy Validator                               │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Bot Execution Layer                      │   │
│  │  - BotEngine (run strategy with params)             │   │
│  │  - Strategy Executor (call strategy methods)        │   │
│  │  - Signal Handler                                    │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Service Layer (existing)                 │   │
│  │  - OrderService  - PositionService                   │   │
│  │  - RiskService   - MarketDataService                 │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                           │
┌─────────────────────────────────────────────────────────────┐
│                     STRATEGIES (Plugins)                     │
│  strategies/                                                 │
│    ├── grid_trading.py                                      │
│    ├── dca_strategy.py                                      │
│    ├── momentum_breakout.py                                 │
│    ├── mean_reversion.py                                    │
│    └── custom/                                              │
│        └── user_strategy_001.py                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Strategy Lifecycle
```
1. DEVELOPMENT PHASE
   - Developer writes strategy file following IStrategy interface
   - Strategy metadata defined (name, description, params schema)
   
2. REGISTRATION PHASE (Backend Startup)
   - StrategyRegistry scans strategies/ directory
   - Load & validate each strategy module
   - Register metadata to database
   
3. CONFIGURATION PHASE (Frontend)
   - User views available strategies
   - User creates/updates strategy with custom params
   - Params validated against schema
   
4. ATTACHMENT PHASE
   - User creates Bot and selects strategy_id
   - Bot.strategy_id links to strategies table
   
5. EXECUTION PHASE (Bot Running)
   - BotEngine loads strategy by strategy_id
   - Calls strategy.on_init(), on_tick(), on_signal()
   - Strategy uses injected services to place orders
   
6. MONITORING PHASE
   - Strategy emits signals/logs
   - Performance tracked (trades, PnL, win rate)
   - User monitors via dashboard
```

---

## 3. Database Schema

### 3.1 Existing Tables (Current State)
```sql
-- strategies table (already exists from migration f3595aea39b7)
CREATE TABLE strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Basic Info
    name VARCHAR(100) NOT NULL,
    strategy_type VARCHAR(20) NOT NULL,  -- GRID, DCA, MOMENTUM, MEAN_REVERSION, ARBITRAGE, CUSTOM
    description VARCHAR(1000) NOT NULL,
    parameters JSONB NOT NULL DEFAULT '{}',  -- User-configured params
    is_active BOOLEAN NOT NULL DEFAULT true,
    
    -- Performance Tracking
    backtest_results JSONB,  -- Backtest metrics
    live_performance JSONB NOT NULL DEFAULT '{}',  -- Live trading metrics
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    
    -- Indexes
    CONSTRAINT ck_strategies_type CHECK (strategy_type IN ('GRID', 'DCA', 'MARTINGALE', 'TREND_FOLLOWING', 'MEAN_REVERSION', 'ARBITRAGE', 'CUSTOM'))
);

CREATE INDEX idx_strategies_user_type ON strategies(user_id, strategy_type);
CREATE INDEX idx_strategies_is_active ON strategies(is_active);
CREATE INDEX idx_strategies_deleted_at ON strategies(deleted_at);

-- bots table (link to strategy)
CREATE TABLE bots (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    strategy_id UUID NOT NULL REFERENCES strategies(id),
    exchange_connection_id UUID REFERENCES api_connections(id),
    
    name VARCHAR(100) NOT NULL,
    description VARCHAR(500),
    status VARCHAR(20) NOT NULL,  -- ACTIVE, PAUSED, STOPPED, ERROR
    
    -- Bot configuration will override/extend strategy params
    configuration JSONB NOT NULL,
    
    -- Runtime state
    start_time TIMESTAMPTZ,
    stop_time TIMESTAMPTZ,
    last_error VARCHAR(1000),
    active_orders JSONB DEFAULT '[]',
    
    -- Performance
    performance JSONB DEFAULT '{}',
    daily_pnl DECIMAL(20, 8) DEFAULT 0,
    total_runtime_seconds INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    deleted_at TIMESTAMPTZ
);
```

### 3.2 New Table Required: strategy_files
```sql
-- Maps strategy_type to actual Python file path
CREATE TABLE strategy_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Strategy Identity
    strategy_type VARCHAR(20) UNIQUE NOT NULL,  -- GRID, DCA, CUSTOM, etc.
    file_path VARCHAR(500) NOT NULL,  -- strategies/grid_trading.py
    module_name VARCHAR(200) NOT NULL,  -- strategies.grid_trading
    class_name VARCHAR(100) NOT NULL,  -- GridTradingStrategy
    
    -- Metadata (auto-extracted from file)
    display_name VARCHAR(100) NOT NULL,  -- "Grid Trading Strategy"
    description TEXT,
    author VARCHAR(100),
    version VARCHAR(20) DEFAULT '1.0.0',
    
    -- Parameters Schema (JSON Schema format)
    parameters_schema JSONB NOT NULL,  -- Defines required/optional params
    
    -- Status
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    is_builtin BOOLEAN NOT NULL DEFAULT true,  -- true for system strategies
    
    -- Validation
    last_validated_at TIMESTAMPTZ,
    validation_errors JSONB,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_strategy_files_type ON strategy_files(strategy_type);
CREATE INDEX idx_strategy_files_enabled ON strategy_files(is_enabled);
```

---

## 4. Backend Implementation

### 4.1 Directory Structure
```
backend/src/trading/
├── domain/
│   └── strategy/
│       ├── __init__.py
│       ├── base.py              # IStrategy interface
│       ├── context.py           # StrategyContext dataclass
│       └── signal.py            # StrategySignal dataclass
├── application/
│   ├── services/
│   │   └── bot_engine.py        # BotEngine (execute strategy)
│   └── use_cases/
│       └── strategy_use_cases.py  # Strategy CRUD use cases
├── infrastructure/
│   ├── strategy/
│   │   └── registry.py          # StrategyRegistry
│   └── persistence/
│       └── models/
│           └── strategy_models.py  # StrategyFileModel
├── strategies/                   # Strategy plugins directory
│   ├── __init__.py
│   ├── grid_trading.py
│   ├── dca_strategy.py
│   ├── momentum_breakout.py
│   └── mean_reversion.py
└── interfaces/
    └── api/
        └── v1/
            └── strategies.py     # Strategy API endpoints
```

### 4.2 Strategy Interface (Contract)
**File**: `backend/src/trading/domain/strategy/base.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

@dataclass
class StrategyContext:
    """Context provided to strategy during execution."""
    bot_id: str
    symbol: str
    timeframe: str
    capital: Decimal
    leverage: int
    position_size: Decimal
    current_position: Optional[Dict[str, Any]]
    active_orders: List[Dict[str, Any]]
    params: Dict[str, Any]  # User-configured parameters

@dataclass
class StrategySignal:
    """Signal emitted by strategy."""
    action: str  # BUY, SELL, CLOSE, HOLD
    quantity: Optional[Decimal]
    price: Optional[Decimal]
    stop_loss: Optional[Decimal]
    take_profit: Optional[Decimal]
    reason: str
    confidence: float  # 0.0 - 1.0
    metadata: Dict[str, Any]

class IStrategy(ABC):
    """Base interface that all strategies must implement."""
    
    # Metadata (class attributes)
    STRATEGY_TYPE: str
    DISPLAY_NAME: str
    DESCRIPTION: str
    VERSION: str
    AUTHOR: str
    
    @classmethod
    @abstractmethod
    def get_parameters_schema(cls) -> Dict[str, Any]:
        """Return JSON Schema for strategy parameters.
        
        Example:
        {
            "type": "object",
            "properties": {
                "grid_levels": {"type": "integer", "minimum": 2, "maximum": 20},
                "grid_spacing": {"type": "number", "minimum": 0.1, "maximum": 10}
            },
            "required": ["grid_levels", "grid_spacing"]
        }
        """
        pass
    
    def __init__(self, context: StrategyContext):
        """Initialize strategy with context."""
        self.context = context
        self.params = context.params
        
    @abstractmethod
    async def on_init(self) -> None:
        """Called once when strategy starts."""
        pass
    
    @abstractmethod
    async def on_tick(self, market_data: Dict[str, Any]) -> Optional[StrategySignal]:
        """Called on each market data update.
        
        Args:
            market_data: {
                "symbol": "BTCUSDT",
                "price": 50000.0,
                "timestamp": "2025-12-18T10:00:00Z",
                "volume": 1000.0,
                "bid": 49999.0,
                "ask": 50001.0
            }
            
        Returns:
            StrategySignal if action needed, None otherwise
        """
        pass
    
    @abstractmethod
    async def on_order_filled(self, order: Dict[str, Any]) -> None:
        """Called when order is filled."""
        pass
    
    @abstractmethod
    async def on_stop(self) -> None:
        """Called when strategy stops."""
        pass
    
    # Services injected by BotEngine
    async def place_order(self, signal: StrategySignal) -> Dict[str, Any]:
        """Place order via OrderService (injected by engine)."""
        raise NotImplementedError("OrderService not injected")
    
    async def get_position(self) -> Optional[Dict[str, Any]]:
        """Get current position via PositionService."""
        raise NotImplementedError("PositionService not injected")
    
    async def get_market_data(self, symbol: str, timeframe: str, limit: int = 100) -> List[Dict]:
        """Get historical market data via MarketDataService."""
        raise NotImplementedError("MarketDataService not injected")
    
    async def check_risk(self, order_params: Dict) -> bool:
        """Check if order passes risk checks via RiskService."""
        raise NotImplementedError("RiskService not injected")
```

### 4.3 Example Strategy Implementation
**File**: `backend/src/trading/strategies/grid_trading.py`

```python
from ..domain.strategy.base import IStrategy, StrategyContext, StrategySignal
from typing import Dict, Any, Optional
from decimal import Decimal

class GridTradingStrategy(IStrategy):
    """Grid trading strategy implementation."""
    
    STRATEGY_TYPE = "GRID"
    DISPLAY_NAME = "Grid Trading"
    DESCRIPTION = "Places buy and sell orders at predefined price levels"
    VERSION = "1.0.0"
    AUTHOR = "System"
    
    @classmethod
    def get_parameters_schema(cls) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "grid_levels": {
                    "type": "integer",
                    "minimum": 2,
                    "maximum": 20,
                    "default": 10,
                    "description": "Number of grid levels"
                },
                "grid_spacing_pct": {
                    "type": "number",
                    "minimum": 0.1,
                    "maximum": 10.0,
                    "default": 1.0,
                    "description": "Spacing between grid levels (%)"
                },
                "upper_price": {
                    "type": "number",
                    "description": "Upper bound price"
                },
                "lower_price": {
                    "type": "number",
                    "description": "Lower bound price"
                }
            },
            "required": ["grid_levels", "grid_spacing_pct"]
        }
    
    def __init__(self, context: StrategyContext):
        super().__init__(context)
        self.grid_orders = []
        self.upper_price = None
        self.lower_price = None
    
    async def on_init(self) -> None:
        """Initialize grid levels and place initial orders."""
        market_data = await self.get_market_data(self.context.symbol, "1m", limit=1)
        current_price = Decimal(str(market_data[0]["close"]))
        
        grid_levels = self.params["grid_levels"]
        spacing_pct = Decimal(str(self.params["grid_spacing_pct"])) / 100
        
        self.upper_price = self.params.get("upper_price") or current_price * (1 + spacing_pct * grid_levels / 2)
        self.lower_price = self.params.get("lower_price") or current_price * (1 - spacing_pct * grid_levels / 2)
        
        await self._setup_grid()
    
    async def on_tick(self, market_data: Dict[str, Any]) -> Optional[StrategySignal]:
        """Check if grid needs rebalancing."""
        current_price = Decimal(str(market_data["price"]))
        
        for level_price in self._calculate_grid_levels():
            if not self._has_order_at_level(level_price):
                if level_price < current_price:
                    return StrategySignal(
                        action="BUY",
                        quantity=self.context.position_size,
                        price=level_price,
                        stop_loss=None,
                        take_profit=level_price * (1 + self.params["grid_spacing_pct"] / 100),
                        reason=f"Grid buy order at {level_price}",
                        confidence=0.8,
                        metadata={"grid_level": str(level_price)}
                    )
        return None
    
    async def on_order_filled(self, order: Dict[str, Any]) -> None:
        """Handle filled order."""
        pass
    
    async def on_stop(self) -> None:
        """Cancel all grid orders."""
        pass
    
    def _calculate_grid_levels(self) -> list[Decimal]:
        levels = []
        grid_levels = self.params["grid_levels"]
        price_range = self.upper_price - self.lower_price
        level_spacing = price_range / (grid_levels - 1)
        
        for i in range(grid_levels):
            levels.append(self.lower_price + level_spacing * i)
        
        return levels
    
    def _has_order_at_level(self, price: Decimal) -> bool:
        tolerance = Decimal("0.0001")
        for order in self.context.active_orders:
            order_price = Decimal(str(order["price"]))
            if abs(order_price - price) / price < tolerance:
                return True
        return False
    
    async def _setup_grid(self) -> None:
        """Place initial grid orders."""
        pass
```

### 4.4 Strategy Registry
**File**: `backend/src/trading/infrastructure/strategy/registry.py`

```python
import importlib
import inspect
from pathlib import Path
from typing import Dict, Type, List
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from ...domain.strategy.base import IStrategy

class StrategyRegistry:
    """Manages strategy discovery, loading, and registration."""
    
    def __init__(self):
        self._strategies: Dict[str, Type[IStrategy]] = {}
        self._strategy_dir = Path("src/trading/strategies")
    
    async def discover_and_register(self, db: AsyncSession) -> None:
        """Scan strategies directory and register all valid strategies."""
        strategy_files = self._scan_directory()
        
        for file_path in strategy_files:
            try:
                strategy_class = self._load_strategy(file_path)
                await self._register_strategy(strategy_class, file_path, db)
            except Exception as e:
                print(f"Failed to load strategy from {file_path}: {e}")
    
    def _scan_directory(self) -> List[Path]:
        """Scan strategies directory for Python files."""
        return [f for f in self._strategy_dir.glob("**/*.py") if f.name != "__init__.py"]
    
    def _load_strategy(self, file_path: Path) -> Type[IStrategy]:
        """Dynamically load strategy class from file."""
        relative_path = file_path.relative_to("src")
        module_name = str(relative_path.with_suffix("")).replace("/", ".")
        
        module = importlib.import_module(module_name)
        
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, IStrategy) and obj != IStrategy:
                return obj
        
        raise ValueError(f"No IStrategy implementation found in {file_path}")
    
    async def _register_strategy(
        self, 
        strategy_class: Type[IStrategy], 
        file_path: Path,
        db: AsyncSession
    ) -> None:
        """Register strategy metadata to database."""
        from sqlalchemy import select
        from ...infrastructure.persistence.models.strategy_models import StrategyFileModel
        
        metadata = {
            "strategy_type": strategy_class.STRATEGY_TYPE,
            "file_path": str(file_path),
            "module_name": strategy_class.__module__,
            "class_name": strategy_class.__name__,
            "display_name": strategy_class.DISPLAY_NAME,
            "description": strategy_class.DESCRIPTION,
            "version": strategy_class.VERSION,
            "author": strategy_class.AUTHOR,
            "parameters_schema": strategy_class.get_parameters_schema()
        }
        
        stmt = select(StrategyFileModel).where(
            StrategyFileModel.strategy_type == metadata["strategy_type"]
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            for key, value in metadata.items():
                setattr(existing, key, value)
            existing.last_validated_at = datetime.utcnow()
        else:
            strategy_file = StrategyFileModel(**metadata)
            db.add(strategy_file)
        
        await db.commit()
        self._strategies[metadata["strategy_type"]] = strategy_class
    
    def get_strategy_class(self, strategy_type: str) -> Type[IStrategy]:
        """Get strategy class by type."""
        if strategy_type not in self._strategies:
            raise ValueError(f"Strategy type {strategy_type} not registered")
        return self._strategies[strategy_type]
    
    def list_strategies(self) -> List[str]:
        """List all registered strategy types."""
        return list(self._strategies.keys())
```

### 4.5 Bot Engine with Strategy Execution
**File**: `backend/src/trading/application/services/bot_engine.py`

```python
from typing import Optional
from uuid import UUID
from decimal import Decimal

from ...domain.strategy.base import IStrategy, StrategyContext, StrategySignal
from ...infrastructure.strategy.registry import StrategyRegistry

class BotEngine:
    """Executes bot with configured strategy."""
    
    def __init__(
        self,
        bot_id: UUID,
        strategy_registry: StrategyRegistry,
        order_service,
        position_service,
        risk_service,
        market_data_service
    ):
        self.bot_id = bot_id
        self.strategy_registry = strategy_registry
        self.order_service = order_service
        self.position_service = position_service
        self.risk_service = risk_service
        self.market_data_service = market_data_service
        
        self.strategy: Optional[IStrategy] = None
        self.is_running = False
    
    async def start(self, bot_config: dict) -> None:
        """Start bot with strategy."""
        strategy_type = bot_config["strategy_type"]
        strategy_class = self.strategy_registry.get_strategy_class(strategy_type)
        
        context = StrategyContext(
            bot_id=str(self.bot_id),
            symbol=bot_config["symbol"],
            timeframe=bot_config.get("timeframe", "1m"),
            capital=Decimal(str(bot_config["capital"])),
            leverage=bot_config["leverage"],
            position_size=Decimal(str(bot_config["position_size"])),
            current_position=None,
            active_orders=[],
            params=bot_config["strategy_params"]
        )
        
        self.strategy = strategy_class(context)
        
        # Inject services
        self.strategy.place_order = self._place_order_wrapper
        self.strategy.get_position = self._get_position_wrapper
        self.strategy.get_market_data = self._get_market_data_wrapper
        self.strategy.check_risk = self._check_risk_wrapper
        
        await self.strategy.on_init()
        self.is_running = True
    
    async def on_market_data(self, market_data: dict) -> None:
        """Handle market data update."""
        if not self.is_running or not self.strategy:
            return
        
        signal = await self.strategy.on_tick(market_data)
        
        if signal:
            await self._execute_signal(signal)
    
    async def _execute_signal(self, signal: StrategySignal) -> None:
        """Execute strategy signal."""
        is_allowed = await self.risk_service.check_order(
            bot_id=self.bot_id,
            action=signal.action,
            quantity=signal.quantity
        )
        
        if is_allowed:
            await self.order_service.create_order(
                bot_id=self.bot_id,
                symbol=self.strategy.context.symbol,
                side=signal.action,
                quantity=float(signal.quantity),
                price=float(signal.price) if signal.price else None
            )
    
    async def _place_order_wrapper(self, signal: StrategySignal) -> dict:
        await self._execute_signal(signal)
        return {"status": "submitted"}
    
    async def _get_position_wrapper(self) -> Optional[dict]:
        return await self.position_service.get_position(
            self.bot_id, self.strategy.context.symbol
        )
    
    async def _get_market_data_wrapper(self, symbol: str, timeframe: str, limit: int) -> list:
        return await self.market_data_service.get_candles(symbol, timeframe, limit)
    
    async def _check_risk_wrapper(self, order_params: dict) -> bool:
        return await self.risk_service.check_order(bot_id=self.bot_id, **order_params)
```

### 4.6 API Endpoints
**File**: `backend/src/trading/interfaces/api/v1/strategies.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from uuid import UUID
from pydantic import BaseModel

router = APIRouter(prefix="/strategies", tags=["strategies"])

class StrategyFileResponse(BaseModel):
    id: str
    strategy_type: str
    display_name: str
    description: str
    version: str
    parameters_schema: dict

class CreateStrategyRequest(BaseModel):
    name: str
    strategy_type: str
    description: str
    parameters: dict

@router.get("/files", response_model=List[StrategyFileResponse])
async def list_strategy_files():
    """List available strategy files."""
    pass

@router.get("/", response_model=List[dict])
async def list_strategies():
    """List user's strategies."""
    pass

@router.post("/", response_model=dict)
async def create_strategy(request: CreateStrategyRequest):
    """Create new strategy."""
    pass

@router.get("/{strategy_id}")
async def get_strategy(strategy_id: UUID):
    """Get strategy details."""
    pass

@router.patch("/{strategy_id}")
async def update_strategy(strategy_id: UUID, request: dict):
    """Update strategy."""
    pass

@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: UUID):
    """Delete strategy."""
    pass

@router.post("/{strategy_id}/activate")
async def activate_strategy(strategy_id: UUID):
    """Activate strategy."""
    pass

@router.post("/{strategy_id}/deactivate")
async def deactivate_strategy(strategy_id: UUID):
    """Deactivate strategy."""
    pass
```

---

## 5. Frontend Implementation

### 5.1 Types
**File**: `frontend/src/lib/types/strategy.ts`

```typescript
export interface StrategyFile {
  id: string;
  strategy_type: string;
  display_name: string;
  description: string;
  version: string;
  author: string;
  parameters_schema: Record<string, any>;
  is_enabled: boolean;
}

export interface Strategy {
  id: string;
  user_id: string;
  name: string;
  strategy_type: string;
  description: string;
  parameters: Record<string, any>;
  is_active: boolean;
  backtest_results?: Record<string, any>;
  live_performance: {
    total_trades: number;
    winning_trades: number;
    total_profit: number;
    win_rate: number;
  };
  created_at: string;
  updated_at: string;
}

export interface CreateStrategyRequest {
  name: string;
  strategy_type: string;
  description: string;
  parameters: Record<string, any>;
}
```

### 5.2 API Client
**File**: `frontend/src/lib/api/strategies.ts`

```typescript
import { apiClient } from './client';
import { Strategy, StrategyFile, CreateStrategyRequest } from '../types/strategy';

export const strategiesApi = {
  listFiles: async (): Promise<StrategyFile[]> => {
    const { data } = await apiClient.get('/api/v1/strategies/files');
    return data;
  },

  list: async (): Promise<Strategy[]> => {
    const { data } = await apiClient.get('/api/v1/strategies');
    return data;
  },

  get: async (id: string): Promise<Strategy> => {
    const { data } = await apiClient.get(`/api/v1/strategies/${id}`);
    return data;
  },

  create: async (request: CreateStrategyRequest): Promise<Strategy> => {
    const { data } = await apiClient.post('/api/v1/strategies', request);
    return data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/v1/strategies/${id}`);
  },

  activate: async (id: string): Promise<Strategy> => {
    const { data } = await apiClient.post(`/api/v1/strategies/${id}/activate`);
    return data;
  },

  deactivate: async (id: string): Promise<Strategy> => {
    const { data } = await apiClient.post(`/api/v1/strategies/${id}/deactivate`);
    return data;
  }
};
```

### 5.3 Store Integration
**File**: `frontend/src/lib/store.ts` (add to existing store)

```typescript
// Add to interface
strategies: Strategy[];
strategyFiles: StrategyFile[];
strategiesLoading: boolean;

fetchStrategyFiles: () => Promise<void>;
fetchStrategies: () => Promise<void>;
createStrategy: (data: CreateStrategyRequest) => Promise<void>;
deleteStrategy: (id: string) => Promise<void>;
activateStrategy: (id: string) => Promise<void>;
deactivateStrategy: (id: string) => Promise<void>;

// Implementation
fetchStrategyFiles: async () => {
  try {
    set({ strategiesLoading: true });
    const files = await strategiesApi.listFiles();
    set({ strategyFiles: files });
  } finally {
    set({ strategiesLoading: false });
  }
},

fetchStrategies: async () => {
  try {
    set({ strategiesLoading: true });
    const strategies = await strategiesApi.list();
    set({ strategies });
  } finally {
    set({ strategiesLoading: false });
  }
},

createStrategy: async (data: CreateStrategyRequest) => {
  const newStrategy = await strategiesApi.create(data);
  set(state => ({
    strategies: [...state.strategies, newStrategy]
  }));
},
```

### 5.4 UI Page
**File**: `frontend/src/pages/Strategies.tsx`

```tsx
import React, { useEffect, useState } from 'react';
import { useStore } from '@/lib/store';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Plus, Play, Pause, Trash2 } from 'lucide-react';

export default function Strategies() {
  const { 
    strategies, 
    strategyFiles,
    fetchStrategies, 
    fetchStrategyFiles,
    deleteStrategy,
    activateStrategy,
    deactivateStrategy
  } = useStore();
  
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  useEffect(() => {
    fetchStrategies();
    fetchStrategyFiles();
  }, []);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold">Strategies</h1>
            <p className="text-muted-foreground">
              Manage your trading strategies
            </p>
          </div>
          <Button onClick={() => setIsCreateOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Create Strategy
          </Button>
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {strategies.map(strategy => (
            <Card key={strategy.id} className="p-6">
              <div className="flex justify-between mb-4">
                <div>
                  <h3 className="font-semibold">{strategy.name}</h3>
                  <Badge variant="outline">{strategy.strategy_type}</Badge>
                </div>
                <Badge variant={strategy.is_active ? "success" : "secondary"}>
                  {strategy.is_active ? "Active" : "Inactive"}
                </Badge>
              </div>
              
              <p className="text-sm text-muted-foreground mb-4">
                {strategy.description}
              </p>

              <div className="grid grid-cols-2 gap-2 mb-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Trades</p>
                  <p className="font-semibold">{strategy.live_performance.total_trades}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Win Rate</p>
                  <p className="font-semibold">{strategy.live_performance.win_rate?.toFixed(1)}%</p>
                </div>
              </div>

              <div className="flex gap-2">
                <Button 
                  size="sm" 
                  variant="outline"
                  onClick={() => strategy.is_active 
                    ? deactivateStrategy(strategy.id) 
                    : activateStrategy(strategy.id)}
                >
                  {strategy.is_active ? <Pause className="h-3 w-3" /> : <Play className="h-3 w-3" />}
                </Button>
                <Button 
                  size="sm" 
                  variant="destructive"
                  onClick={() => deleteStrategy(strategy.id)}
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </DashboardLayout>
  );
}
```

---

## 6. Integration with Bot Management

### 6.1 Bot-Strategy Relationship
- Bot table có `strategy_id` foreign key → strategies table
- Khi tạo bot, user chọn strategy từ dropdown
- Bot config có thể override strategy params
- Một strategy có thể được dùng bởi nhiều bots

### 6.2 Bot Creation Flow
1. User chọn "Create Bot"
2. Form hiển thị dropdown "Select Strategy" (list từ `/api/v1/strategies`)
3. Khi chọn strategy, form auto-fill default params từ `parameters_schema`
4. User có thể customize params
5. Submit bot với `strategy_id` và `configuration`

### 6.3 Bot Execution Flow
1. User click "Start Bot"
2. Backend BotEngine load strategy từ `strategy_id`
3. BotEngine instantiate strategy class với bot config
4. Strategy chạy `on_init()` → setup initial state
5. Market data stream → `on_tick()` → emit signals
6. BotEngine execute signals qua OrderService
7. Order filled → `on_order_filled()` callback

---

## 7. Implementation Roadmap

### Phase 1: Foundation (Week 1)
- [ ] Tạo database migration cho `strategy_files` table
- [ ] Implement `IStrategy` base interface
- [ ] Implement `StrategyRegistry` (scan & register)
- [ ] Tạo example `GridTradingStrategy`
- [ ] API endpoint: `GET /api/v1/strategies/files`

### Phase 2: Strategy Management (Week 2)
- [ ] Strategy Use Cases (Create, Read, Update, Delete)
- [ ] API endpoints: CRUD strategies
- [ ] Frontend types, API client, store
- [ ] Strategies page UI (list, create, configure)
- [ ] Dynamic form generator từ JSON Schema

### Phase 3: Bot Integration (Week 3)
- [ ] Update Bot model: add `strategy_id` field
- [ ] Bot creation form: strategy selection dropdown
- [ ] Implement `BotEngine` với strategy execution
- [ ] Service injection (OrderService, PositionService, etc.)
- [ ] Signal handling & order placement

### Phase 4: Monitoring & Testing (Week 4)
- [ ] Strategy signals logging
- [ ] Performance tracking (live_performance JSON)
- [ ] Bot detail page: hiển thị strategy activity
- [ ] Unit tests cho StrategyRegistry, BotEngine
- [ ] E2E test: Create strategy → Create bot → Run → Monitor

---

## 8. Technical Notes

### 8.1 Strategy Validation
- Validate Python syntax khi load file
- Check interface compliance (có đủ methods không)
- Validate parameters_schema (must be valid JSON Schema)
- Runtime validation: params phải match schema

### 8.2 Security Considerations
- Strategy file chỉ admin mới được add (không cho user upload)
- Sandboxing: consider giới hạn Python features (no eval, exec, import os)
- Timeout: strategy methods phải return trong 5s
- Rate limiting: giới hạn số lượng orders/minute

### 8.3 Error Handling
- Strategy error không được crash bot
- Log all exceptions với stack trace
- Auto-pause bot sau 3 consecutive errors
- Notify user qua alerts

---

## 9. Future Enhancements

- **Strategy Marketplace**: User có thể share/clone strategies
- **Backtesting Integration**: Run strategy trên historical data
- **Strategy Versioning**: Track changes, rollback
- **Visual Builder**: No-code strategy creation
- **ML Strategies**: Support machine learning models
- **Multi-timeframe**: Strategy có thể dùng multiple timeframes
- **Strategy Combos**: Combine nhiều strategies trong 1 bot

---

## 10. Architectural Decisions & Answers

### 10.1 Original Planning Questions

1. **Database Schema**: ✅ YES - Add `strategy_signals` table (see Q7) and extend `strategy_files` with compatibility metadata (see Q10)
2. **Service Injection**: ✅ TYPED SERVICES OBJECT - Use `StrategyServices` dataclass instead of monkey-patching (see Q6)
3. **Strategy Parameters**: ✅ YES - Support complex types via JSON Schema Draft 7 (nested objects, arrays, enums) (see Q9)
4. **Performance**: ✅ YES - Strategy registry cached in-memory after startup discovery
5. **Testing**: ✅ YES - Mock services via `StrategyServices` interface for unit tests
6. **Deployment**: ❌ NO - Keep strategies in main repo, auto-discover on startup (see Q3)

GPT-5.2 question: Hiện BE đang expose strategies qua `backend/src/trading/presentation/controllers/strategies.py` (đã được include trong `backend/src/trading/interfaces/api/v1/__init__.py`). Vậy mình chốt **contract API** theo controller hiện tại hay theo spec mới? (đặc biệt là shape của `StrategyResponse` và các endpoint `/strategies/{id}/performance`, `/strategies/{id}/history`, ... nếu FE cần)

GPT-5.2 question: “Strategy = 1 file code” đang map vào DB như thế nào? Chốt 1 trong 2 hướng:
- (A) **File = Strategy Type** (global catalog), còn bảng `strategies` là “strategy instance/config” per-user
- (B) **File = Strategy Instance** (mỗi file tương ứng 1 row `strategies`)
Vì hiện tại `bots.strategy_id` là UUID FK → `strategies.id`, nên để bot chạy được thì tối thiểu phải có “strategy instance” trong DB.

GPT-5.2 question: Ai là người “đăng ký” strategy file vào system? (CI/CD deploy code, admin-only action, hoặc auto-discover lúc startup). Nếu auto-discover, có cần **management command**/job để sync DB (insert/update `strategy_files`) hay làm trong startup hook?

GPT-5.2 question: Runtime chạy bot/strategy ở đâu cho production? (FastAPI process background task vs worker riêng). Repo hiện có `jobs_controller` và docs về jobs/redis—mình chốt kiến trúc chạy bot theo:
- in-process (đơn giản nhưng rủi ro restart, scale)
- out-of-process worker (bền vững, scale)
Và cơ chế “resume bot after restart” sẽ như thế nào?

GPT-5.2 question: Nguồn event `on_tick` lấy từ đâu? (market data websocket/subscription, polling, hay job scheduler). Cần chốt:
- tick cadence (per trade / per candle close / fixed interval)
- per-symbol subscription multiplexing (nhiều bot cùng symbol)
- backpressure khi nhiều bot chạy

GPT-5.2 question: Spec đang dùng kiểu “monkey-patch” inject methods (`strategy.place_order = ...`). Mình có muốn thay bằng một `Services` object (typed) truyền vào strategy (vd `StrategyServices(order, risk, market_data, position)`), để test/mocking và type-safety tốt hơn?

GPT-5.2 question: Strategy được phép “emit” gì để FE quan sát? Cần chốt chuẩn hoá event/log:
- `strategy_signals` (BUY/SELL/CLOSE/HOLD + confidence + reason)
- `strategy_logs` (level, message)
- `strategy_metrics` (PnL, win_rate, drawdown)
Những thứ này lưu DB hay stream qua websocket? Retention bao lâu?

GPT-5.2 question: FE hiện tại `frontend/src/pages/Strategies.tsx` đang dùng mock data. Mình muốn UX tối thiểu cho “quy trình khép kín” gồm những màn nào?
- Strategy Catalog (file/plugins) list
- Strategy Instance list (của user)
- Create instance (dynamic form từ schema)
- Attach strategy instance vào Bot Create
Chốt để không làm thừa UI.

GPT-5.2 question: Validation của `parameters_schema` dùng JSON Schema bản nào (Draft 7/2019-09/2020-12)? Backend sẽ validate bằng lib nào và FE render form hỗ trợ tới mức nào (enum, oneOf, arrays, nested objects)?

GPT-5.2 question: Strategy compatibility: mỗi strategy có ràng buộc gì theo exchange / market (spot vs futures) / symbol format (BTCUSDT vs BTC/USDT)? Cần metadata như `supported_exchanges`, `market_type`, `supported_symbols` hay không?

GPT-5.2 question: Versioning: khi strategy file update (v1 → v2), bot đang chạy có hot-reload không hay chỉ áp dụng cho bot restart? Strategy instance trong DB có pin version không?

GPT-5.2 question: Quyền truy cập: `strategies.user_id` hiện là per-user. Có cần “built-in strategies” share cho mọi user không? Nếu có, cách represent trong DB (user_id null? system user? `is_builtin` + ownership rules)?

GPT-5.2 question: Backtest integration: repo đã có backtest controller. Strategy params/schema dùng chung giữa backtest và live không? Backtest result lưu vào `strategies.backtest_results` hay bảng riêng? Và FE cần flow “backtest → save as strategy instance → attach bot” không?

---

**END OF SPECIFICATION**

## 11. COMPREHENSIVE ANSWERS TO GPT-5.2 QUESTIONS

### Q1: API Contract - Existing vs New Spec?

**✅ DECISION: Extend Existing Controller**

**Action**: Keep current `strategies.py` controller structure, add only 2 new endpoints:
- `GET /strategies/files` - List strategy catalog
- `GET /strategies/types/{type}/schema` - Get param schema

**Rationale**: Existing StrategyResponse already has all needed fields (performance, backtest_results). No breaking changes needed.

---

### Q2: File-to-DB Mapping?

**✅ DECISION: Model A - File = Type Catalog**

**Architecture**:
```
strategy_files (catalog) → strategies (user instances) → bots (execution)
     GRID file          →   uuid1 (10 levels)       →   bot1
                        →   uuid2 (20 levels)       →   bot2
```

User can create multiple strategy instances from same file with different params.

---

### Q3: Strategy Registration?

**✅ DECISION: Auto-discover on Startup + Manual Command**

**Implementation**:
- Primary: FastAPI `lifespan` event → auto-discover all files
- Secondary: `scripts/sync_strategies.py` for manual admin control

**Flow**: New file → Deploy → Restart → Auto-sync → Available to users

---

### Q4: Runtime Architecture?

**✅ DECISION: Hybrid (In-process MVP → Worker Scale)**

**Phase 1**: FastAPI `BackgroundTasks` (simple, fast MVP)  
**Phase 2**: Redis worker (when scaling needed)

**Resume Logic**: On startup, query `bots WHERE status='ACTIVE'` and auto-restart.

**Design Principle**: Keep BotEngine stateless for easy migration.

---

### Q5: on_tick Event Source?

**✅ DECISION: WebSocket with Symbol Multiplexing**

**Architecture**:
```python
class MarketDataStreamer:
    subscriptions: Dict[symbol, List[BotEngine]]
    
    # When new bot starts
    async def subscribe_bot(bot, symbol):
        if symbol not in subscriptions:
            await binance_ws.subscribe(symbol)  # Use existing WS
        subscriptions[symbol].append(bot)
    
    # On WS message
    async def on_message(symbol, data):
        for bot in subscriptions[symbol]:
            asyncio.create_task(bot.on_market_data(data))  # Non-blocking
```

**Tick Cadence**: Real-time trades (every WS update) or 1s aggregated candles (configurable per bot)

**Backpressure**: Queue with max size, drop ticks if bot can't keep up (log warning)

---

### Q6: Service Injection Pattern?

**✅ DECISION: Typed StrategyServices Object**

**New Design**:
```python
@dataclass
class StrategyServices:
    order: OrderService
    position: PositionService
    risk: RiskService
    market_data: MarketDataService

class IStrategy(ABC):
    def __init__(self, context: StrategyContext, services: StrategyServices):
        self.services = services  # ✅ Clean, typed, testable
    
    # Usage in strategy:
    await self.services.order.create_order(...)
    await self.services.risk.check_order(...)
```

**Benefits**: Type safety, easy mocking, no monkey-patching magic.

---

### Q7: Observable Events - Signals/Logs/Metrics?

**✅ DECISION: Dual Storage (DB + Redis)**

**Event Types**:
1. **Signals** (BUY/SELL decisions) → PostgreSQL `strategy_signals` table (90 days retention)
2. **Logs** (debug messages) → Redis Stream (24 hours, ephemeral)
3. **Metrics** (PnL, win rate) → PostgreSQL `strategies.live_performance` JSONB (permanent)

**New Table**:
```sql
CREATE TABLE strategy_signals (
    id UUID PRIMARY KEY,
    bot_id UUID NOT NULL,
    signal_type VARCHAR(10),  -- BUY/SELL/CLOSE/HOLD
    symbol VARCHAR(20),
    price DECIMAL,
    confidence FLOAT,
    reason TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Real-time**: Publish to Redis → WebSocket → Frontend updates live

---

### Q8: Frontend UX Scope?

**✅ DECISION: 3 Core Screens + 1 Integration**

**Minimal Viable UI**:
1. **/strategies/catalog** - List available strategy files (GRID, DCA, etc.)
2. **/strategies** - List user's strategy instances (existing page, connect to real API)
3. **Strategy Form Modal** - Dynamic form from JSON Schema (react-jsonschema-form)
4. **/bots/new** - Add strategy dropdown (modify existing page)

**User Journey**:
```
Catalog → Create Instance (fill params) → My Strategies → 
→ Create Bot (select strategy) → Start Bot
```

**Skip for MVP**: Visual builder, marketplace, strategy cloning

---

### Q9: JSON Schema Version?

**✅ DECISION: Draft 7 (Best Library Support)**

**Backend**: `jsonschema==4.20.0` (Python validator)  
**Frontend**: `@rjsf/core` + `@rjsf/validator-ajv8` (React form renderer)

**Supported Features**:
- ✅ Basic types, constraints (min/max), enums, required fields
- ✅ Nested objects, arrays
- ⚠️ oneOf/anyOf (basic cases only)
- ❌ $ref (skip for MVP)

**Example Schema**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "grid_levels": {"type": "integer", "minimum": 2, "maximum": 50}
  },
  "required": ["grid_levels"]
}
```

---

### Q10: Strategy Compatibility Metadata?

**✅ DECISION: Add Compatibility Field**

**Schema Extension**:
```sql
ALTER TABLE strategy_files ADD COLUMN compatibility JSONB DEFAULT '{}';

-- Example:
{
  "exchanges": ["binance"],
  "market_types": ["spot", "futures"],
  "symbol_patterns": ["*USDT"],
  "min_capital": 100
}
```

**Usage**: Validate on bot creation - if strategy requires futures but bot is spot, show error.

**UI**: Display badges on strategy cards ("Binance Only", "USDT Pairs")

---

### Q11: Versioning & Hot-Reload?

**✅ DECISION: No Hot-Reload, Restart Required**

**Approach**:
- Track version in `strategy_files.version` field
- On update: Developer commits → Deploy → Restart → Auto-discover updates version
- Running bots: Continue with old code until manually restarted
- New bots: Use latest version automatically

**For MVP**: Skip version pinning (future: allow `strategies.pinned_version`)

**Rationale**: Hot-reload too risky (runtime crashes), restart is predictable and safe.

---

### Q12: Permission Model?

**✅ DECISION: Builtin Strategies (System) + Per-User Instances**

**Design**:
- `strategy_files.is_builtin=true` → All users can see and use
- `strategies.user_id` → Always set (every instance has owner)
- User can only edit/delete their own instances
- Cannot delete strategy if active bots using it

**Access Control**:
```python
def can_delete_strategy(user, strategy):
    if strategy.user_id != user.id:
        return False
    if bot_count(strategy_id=strategy.id, status="ACTIVE") > 0:
        raise ValidationError("Active bots using this strategy")
    return True
```

**MVP**: All strategies are builtin, users create private configs.  
**Future**: Admin can mark instances as "templates" (shareable).

---

### Q13: Backtest Integration?

**✅ DECISION: Shared Params Schema + Results in strategies.backtest_results**

**Flow**:
1. User creates strategy instance (with params)
2. Runs backtest → selects instance, date range, symbol
3. Results saved to `strategies.backtest_results` JSONB
4. User reviews chart + metrics
5. Can attach strategy to bot (already tested params)

**Data Structure**:
```json
// strategies.backtest_results
{
  "period": "2024-01-01 to 2024-12-31",
  "symbol": "BTCUSDT",
  "total_trades": 150,
  "win_rate": 0.62,
  "total_pnl": 1250.50,
  "sharpe_ratio": 1.8
}
```

**API Integration**:
```python
@router.post("/backtest")
async def run_backtest(request: BacktestRequest):
    strategy = await get_strategy(request.strategy_id)
    results = await backtest_engine.run(
        strategy_type=strategy.strategy_type,  # ✅ Same schema
        params=strategy.parameters,            # ✅ Exact same params
        symbol=request.symbol,
        period=request.period
    )
    strategy.backtest_results = results
    await save(strategy)
```

**Frontend**: Show backtest results on strategy detail page, button "Attach to Bot" goes to bot creation with strategy pre-selected.

---

## 12. UPDATED IMPLEMENTATION SUMMARY

### Key Decisions Applied:

1. **Architecture**: File-based plugins (catalog) → User configs (instances) → Bot execution
2. **API**: Extend existing controller (+2 endpoints), no redesign
3. **Registration**: Auto-discover on startup (FastAPI lifespan)
4. **Runtime**: Hybrid (BackgroundTasks MVP, Redis worker for scale)
5. **Events**: WebSocket market data, multiplexed by symbol
6. **Services**: Typed `StrategyServices` object (no monkey-patching)
7. **Observability**: Signals → DB (90d), Logs → Redis (24h), Metrics → DB JSONB
8. **Frontend**: 3 pages (Catalog, My Strategies, Bot integration)
9. **Validation**: JSON Schema Draft 7, `@rjsf/core` forms
10. **Compatibility**: Metadata field for exchange/market constraints
11. **Versioning**: Track version, no hot-reload, restart-based updates
12. **Permissions**: Builtin catalog, per-user instances
13. **Backtest**: Shared schema, results in `backtest_results` JSONB

### New Tables Required:

```sql
-- 1. strategy_files (catalog)
CREATE TABLE strategy_files (
    id UUID PRIMARY KEY,
    strategy_type VARCHAR(20) UNIQUE NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    class_name VARCHAR(100) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    version VARCHAR(20) DEFAULT '1.0.0',
    parameters_schema JSONB NOT NULL,
    compatibility JSONB DEFAULT '{}',
    is_builtin BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. strategy_signals (audit trail)
CREATE TABLE strategy_signals (
    id UUID PRIMARY KEY,
    bot_id UUID NOT NULL REFERENCES bots(id),
    strategy_id UUID NOT NULL REFERENCES strategies(id),
    signal_type VARCHAR(10) NOT NULL,
    symbol VARCHAR(20),
    price DECIMAL(20, 8),
    confidence FLOAT,
    reason TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Updated Roadmap (With Decisions Applied):

**Phase 1 (Week 1)**: Core Infrastructure
- Implement `IStrategy` with `StrategyServices` injection
- Create `StrategyRegistry` with auto-discover
- Add `strategy_files` migration + compatibility field
- Example `GridTradingStrategy` implementation
- API: `GET /strategies/files`, `GET /strategies/types/{type}/schema`

**Phase 2 (Week 2)**: Strategy CRUD
- Strategy Use Cases (aligned with existing controller)
- Frontend types + API client
- Strategy catalog page + instance list
- Dynamic form with `@rjsf/core`
- Bot dropdown integration

**Phase 3 (Week 3)**: Execution Engine
- `BotEngine` with typed services
- `MarketDataStreamer` (WebSocket multiplexing)
- Signal handling + order execution
- `strategy_signals` table + logging
- FastAPI BackgroundTasks runner

**Phase 4 (Week 4)**: Testing & Polish
- Unit tests (with mocked services)
- E2E test: Create strategy → Create bot → Start → Monitor
- Real-time signal WebSocket
- Bot detail page signal history
- Resume active bots on restart

**Post-MVP Enhancements**:
- Redis worker migration (Phase 2 scaling)
- Version pinning
- Strategy templates/marketplace
- Advanced backtest integration

---

**SPECIFICATION STATUS: ✅ READY FOR IMPLEMENTATION**

All architectural decisions made. Clear implementation path defined. MVP scope locked.
