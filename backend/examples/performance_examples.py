"""
Performance module examples and tests

Run this file to test all performance utilities
"""

import asyncio
import time


def test_json_performance():
    """Test JSON serialization performance"""
    print("\n" + "="*60)
    print("JSON PERFORMANCE TEST")
    print("="*60)
    
    from shared.performance.json.orjson_wrapper import OrjsonSerializer, is_available
    
    if not is_available():
        print("⚠ orjson not installed. Skipping test.")
        return
    
    # Test data
    data = {
        "symbol": "BTCUSDT",
        "price": 50000.5,
        "quantity": 1.5,
        "orders": [{"price": 49999, "qty": 1.0} for _ in range(100)]
    }
    
    # Benchmark
    iterations = 10000
    
    # Standard json
    import json
    start = time.perf_counter()
    for _ in range(iterations):
        json_str = json.dumps(data)
        json.loads(json_str)
    std_time = time.perf_counter() - start
    
    # orjson
    start = time.perf_counter()
    for _ in range(iterations):
        json_bytes = OrjsonSerializer.dumps(data)
        OrjsonSerializer.loads(json_bytes)
    orjson_time = time.perf_counter() - start
    
    print(f"Standard json: {std_time*1000:.2f}ms")
    print(f"orjson:        {orjson_time*1000:.2f}ms")
    print(f"Speedup:       {std_time/orjson_time:.2f}x faster")


def test_ring_buffer():
    """Test ring buffer"""
    print("\n" + "="*60)
    print("RING BUFFER TEST")
    print("="*60)
    
    from shared.performance.datastructures.ring_buffer import RingBuffer
    
    buffer = RingBuffer(capacity=5)
    
    # Add items
    for i in range(10):
        buffer.append(i)
        print(f"After append {i}: {buffer.get_all()}")
    
    print(f"\nFinal buffer (size={len(buffer)}): {buffer.get_all()}")
    print(f"Latest 3: {buffer.get_latest(3)}")


def test_fast_orderbook():
    """Test fast orderbook"""
    print("\n" + "="*60)
    print("FAST ORDERBOOK TEST")
    print("="*60)
    
    from shared.performance.datastructures.fast_orderbook import FastOrderBook
    
    ob = FastOrderBook()
    
    # Add bids
    ob.update_bid(50000.0, 1.5)
    ob.update_bid(49999.0, 2.0)
    ob.update_bid(49998.0, 1.0)
    
    # Add asks
    ob.update_ask(50100.0, 1.0)
    ob.update_ask(50101.0, 2.0)
    ob.update_ask(50102.0, 1.5)
    
    print(f"Best bid: {ob.get_best_bid()}")
    print(f"Best ask: {ob.get_best_ask()}")
    print(f"Spread:   {ob.get_spread()}")
    print(f"\nDepth (2 levels):")
    depth = ob.get_depth(levels=2)
    print(f"Bids: {depth['bids']}")
    print(f"Asks: {depth['asks']}")


async def test_async_tools():
    """Test async utilities"""
    print("\n" + "="*60)
    print("ASYNC TOOLS TEST")
    print("="*60)
    
    from shared.performance.concurrency.async_tools import (
        run_parallel, timeout_after, retry_async
    )
    
    # Parallel execution
    async def task(n):
        await asyncio.sleep(0.1)
        return n * 2
    
    print("Running 3 tasks in parallel...")
    start = time.perf_counter()
    results = await run_parallel([task(1), task(2), task(3)])
    elapsed = time.perf_counter() - start
    print(f"Results: {results}")
    print(f"Time: {elapsed:.2f}s (should be ~0.1s, not 0.3s)")
    
    # Timeout
    async def slow_task():
        await asyncio.sleep(5)
        return "done"
    
    print("\nTesting timeout (1s limit on 5s task)...")
    result = await timeout_after(slow_task(), timeout=1.0, default="timeout")
    print(f"Result: {result}")


def test_latency_probe():
    """Test latency measurement"""
    print("\n" + "="*60)
    print("LATENCY PROBE TEST")
    print("="*60)
    
    from shared.performance.profiling.latency_probe import (
        measure_latency, get_stats, LatencyProbe
    )
    
    @measure_latency("test_function")
    def slow_function():
        time.sleep(0.01)
        return "done"
    
    # Run function multiple times
    print("Running function 10 times...")
    for _ in range(10):
        slow_function()
    
    # Print stats
    get_stats().print_report()
    
    # Manual measurement
    print("\nManual measurement:")
    with LatencyProbe("manual_test", print_result=True):
        time.sleep(0.02)


def test_thread_pool():
    """Test thread pool"""
    print("\n" + "="*60)
    print("THREAD POOL TEST")
    print("="*60)
    
    from shared.performance.concurrency.thread_pool import ThreadPool
    
    def process_item(n):
        time.sleep(0.1)
        return n * 2
    
    items = list(range(10))
    
    # Sequential
    print("Sequential processing...")
    start = time.perf_counter()
    seq_results = [process_item(i) for i in items]
    seq_time = time.perf_counter() - start
    
    # Parallel
    print("Parallel processing (4 workers)...")
    start = time.perf_counter()
    with ThreadPool(max_workers=4) as pool:
        par_results = list(pool.map(process_item, items))
    par_time = time.perf_counter() - start
    
    print(f"\nSequential: {seq_time:.2f}s")
    print(f"Parallel:   {par_time:.2f}s")
    print(f"Speedup:    {seq_time/par_time:.2f}x")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("PERFORMANCE MODULE TESTS")
    print("="*60)
    
    test_json_performance()
    test_ring_buffer()
    test_fast_orderbook()
    test_thread_pool()
    test_latency_probe()
    
    # Async tests
    asyncio.run(test_async_tools())
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
