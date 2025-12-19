# Performance Module Documentation

## 📦 Overview

Module tối ưu hiệu năng cho Binance Futures Monitor, được tổ chức theo Clean Architecture với các công cụ performance tái sử dụng.

## 🏗️ Structure

```
shared/performance/
├── json/                   # Fast JSON parsers
│   ├── orjson_wrapper.py   # orjson (2-3x faster)
│   └── simdjson_wrapper.py # simdjson (4x faster parsing)
├── http/                   # HTTP optimizations
│   └── http_pool.py        # Connection pooling + retry
├── datastructures/         # High-performance data structures
│   ├── ring_buffer.py      # Circular buffer for time-series
│   ├── lockfree_queue.py   # Lock-free queue
│   └── fast_orderbook.py   # Optimized orderbook
├── concurrency/            # Async/threading utilities
│   ├── thread_pool.py      # Thread pool management
│   └── async_tools.py      # Async helpers
└── profiling/              # Performance measurement
    ├── latency_probe.py    # Latency tracking
    └── profiler.py         # Code profiling
```

## 🚀 Quick Start

### 1. JSON Performance

```python
# Use orjson for fast JSON
from shared.performance.json.orjson_wrapper import OrjsonSerializer

# Serialize (2-3x faster)
data = OrjsonSerializer.dumps({"price": 50000, "qty": 1.5})

# Deserialize
obj = OrjsonSerializer.loads(data)
```

### 2. HTTP Connection Pool

```python
from shared.performance.http.http_pool import HTTPPool

# Reuse connections, auto-retry
with HTTPPool(max_connections=100) as pool:
    response = pool.get("https://api.binance.com/fapi/v1/ticker/price")
    data = response.json()
```

### 3. Ring Buffer for Ticks

```python
from shared.performance.datastructures.ring_buffer import RingBuffer

# Store last 1000 price ticks
buffer = RingBuffer(capacity=1000, thread_safe=True)

# Add data
buffer.append({"price": 50000, "time": timestamp})

# Get latest 10
latest = buffer.get_latest(10)
```

### 4. Fast OrderBook

```python
from shared.performance.datastructures.fast_orderbook import FastOrderBook

ob = FastOrderBook()
ob.update_bid(50000.0, 1.5)
ob.update_ask(50100.0, 2.0)

best_bid = ob.get_best_bid()  # (50000.0, 1.5)
spread = ob.get_spread()       # 100.0
```

### 5. Concurrent Processing

```python
from shared.performance.concurrency.thread_pool import run_concurrent

# Process 100 items concurrently
results = run_concurrent(process_item, items, max_workers=10)
```

### 6. Async Utilities

```python
from shared.performance.concurrency.async_tools import run_parallel, timeout_after

# Run tasks in parallel
results = await run_parallel([fetch1(), fetch2(), fetch3()])

# With timeout
result = await timeout_after(slow_task(), timeout=5.0, default=None)
```

### 7. Latency Measurement

```python
from shared.performance.profiling.latency_probe import measure_latency, get_stats

@measure_latency("api_call")
async def fetch_data():
    # ... your code
    pass

# After many calls
get_stats().print_report()
```

## 📊 Use Cases in Project

### WebSocket JSON Parsing

```python
# Before (slow)
import json
data = json.loads(ws_message)

# After (fast)
from shared.performance.json.orjson_wrapper import OrjsonSerializer
data = OrjsonSerializer.loads(ws_message)
```

### REST API Calls

```python
# Before (no pooling)
import requests
response = requests.get(url)

# After (connection pooling)
from shared.performance.http.http_pool import HTTPPool
pool = HTTPPool()
response = pool.get(url)
```

### Price Tick Storage

```python
# Before (unlimited list)
prices = []
prices.append(new_price)  # Memory grows forever

# After (fixed-size ring buffer)
from shared.performance.datastructures.ring_buffer import RingBuffer
prices = RingBuffer(capacity=1000)
prices.append(new_price)  # Auto-removes oldest
```

### OrderBook Management

```python
# Before (dict operations)
bids = {}
bids[price] = qty

# After (optimized SortedDict)
from shared.performance.datastructures.fast_orderbook import FastOrderBook
ob = FastOrderBook()
ob.update_bid(price, qty)
best = ob.get_best_bid()  # O(1)
```

### Concurrent API Calls

```python
# Before (sequential)
for symbol in symbols:
    data = fetch_price(symbol)

# After (parallel)
from shared.performance.concurrency.thread_pool import run_concurrent
results = run_concurrent(fetch_price, symbols)
```

### Performance Monitoring

```python
# Measure critical paths
from shared.performance.profiling.latency_probe import measure_latency

@measure_latency("order_placement")
async def place_order(symbol, side, qty):
    # ... order logic
    pass

# Print stats periodically
get_stats().print_report()
```

## 🔧 Installation

Optional dependencies for maximum performance:

```bash
# Fast JSON (recommended)
pip install orjson

# Ultra-fast JSON parsing (optional)
pip install pysimdjson

# Fast ordered dict (for FastOrderBook)
pip install sortedcontainers

# Memory profiling (optional)
pip install pympler
```

## 📈 Performance Benefits

| Component | Improvement | Use Case |
|-----------|-------------|----------|
| orjson | 2-3x faster | JSON parsing WebSocket data |
| simdjson | 4x faster | Large JSON documents |
| HTTPPool | 10x reuse | REST API calls |
| RingBuffer | O(1) ops | Time-series data |
| FastOrderBook | O(log n) | OrderBook updates |
| ThreadPool | N-x faster | Concurrent operations |

## 🎯 Best Practices

### 1. Use Appropriate Tools
- **orjson**: WebSocket messages, API responses
- **HTTPPool**: All REST API calls
- **RingBuffer**: Tick data, candle history
- **FastOrderBook**: Real-time orderbook
- **ThreadPool**: Parallel data processing

### 2. Profile Before Optimize
```python
from shared.performance.profiling.latency_probe import measure_latency

@measure_latency("critical_function")
def my_function():
    pass

# Run many times, then check stats
get_stats().print_report()
```

### 3. Monitor Memory
```python
from shared.performance.profiling.profiler import MemoryTracker

tracker = MemoryTracker()
tracker.start()
# ... code to profile
tracker.stop()
```

## 🔌 Integration Examples

### In WebSocket Client

```python
from shared.performance.json.orjson_wrapper import OrjsonSerializer
from shared.performance.profiling.latency_probe import measure_latency

class WebSocketClient:
    @measure_latency("ws_parse")
    async def on_message(self, message):
        # Fast JSON parsing
        data = OrjsonSerializer.loads(message)
        await self.handle_data(data)
```

### In REST Client

```python
from shared.performance.http.http_pool import HTTPPool

class RestClient:
    def __init__(self):
        self.pool = HTTPPool(max_connections=100, max_retries=3)
    
    def get(self, endpoint):
        return self.pool.get(f"{self.base_url}{endpoint}")
```

### In Market Data Service

```python
from shared.performance.datastructures.ring_buffer import RingBuffer

class MarketDataService:
    def __init__(self):
        self.price_history = RingBuffer(capacity=1000)
    
    def on_price_update(self, price):
        self.price_history.append(price)
        # Auto-maintains last 1000 prices
```

## 📝 Notes

- **Tách bạch hoàn toàn**: Performance tools không depend vào domain logic
- **Reusable**: Có thể dùng cho bất kỳ project Python nào
- **Optional**: App vẫn chạy được nếu không cài optional deps
- **Tested**: Mỗi module có docstring và examples
- **Clean**: Follow SOLID principles

## 🚀 Future Enhancements

- [ ] Cython extensions cho critical paths
- [ ] Redis caching layer
- [ ] Database connection pooling
- [ ] Message queue optimization
- [ ] GPU acceleration cho calculations
