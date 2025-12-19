# Performance Module - Quick Reference

## 📦 Modules

| Module | Purpose | Key Features |
|--------|---------|--------------|
| `json/` | Fast JSON | orjson (3x faster), simdjson (4x) |
| `http/` | HTTP pool | Connection reuse, auto-retry |
| `datastructures/` | Fast DS | RingBuffer, FastOrderBook |
| `concurrency/` | Async/Thread | Thread pools, async helpers |
| `profiling/` | Measurement | Latency tracking, profiling |

## 🚀 Quick Examples

### JSON (3x faster)
```python
from shared.performance.json.orjson_wrapper import OrjsonSerializer
data = OrjsonSerializer.loads(ws_message)
```

### HTTP Pool
```python
from shared.performance.http.http_pool import HTTPPool
pool = HTTPPool(max_connections=100)
response = pool.get(url)
```

### Ring Buffer
```python
from shared.performance.datastructures.ring_buffer import RingBuffer
buffer = RingBuffer(capacity=1000)
buffer.append(price_tick)
```

### Latency Tracking
```python
from shared.performance.profiling.latency_probe import measure_latency

@measure_latency("api_call")
async def fetch(): ...
```

## 📚 Full Documentation

See `docs/PERFORMANCE_MODULE.md` for complete guide.

## 🧪 Test Examples

Run `python examples/performance_examples.py` to see all features in action.

## 📦 Optional Dependencies

```bash
pip install orjson sortedcontainers  # Recommended
pip install pysimdjson pympler       # Optional
```
