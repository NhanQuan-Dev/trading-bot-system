"""Performance testing script for critical endpoints."""

import asyncio
import time
import statistics
from typing import List, Dict, Any
import httpx


BASE_URL = "http://localhost:8000"
TEST_ITERATIONS = 50


async def measure_endpoint(client: httpx.AsyncClient, method: str, url: str, **kwargs) -> float:
    """Measure single request latency."""
    start = time.perf_counter()
    response = await client.request(method, url, **kwargs)
    end = time.perf_counter()
    
    if response.status_code not in [200, 201, 404]:
        raise Exception(f"{method} {url} returned {response.status_code}")
    
    return (end - start) * 1000  # Convert to ms


async def benchmark_endpoint(name: str, method: str, path: str, iterations: int = TEST_ITERATIONS, **kwargs) -> Dict[str, Any]:
    """Benchmark an endpoint."""
    url = f"{BASE_URL}{path}"
    latencies: List[float] = []
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Warmup
        for _ in range(5):
            try:
                await measure_endpoint(client, method, url, **kwargs)
            except Exception:
                pass
        
        # Actual measurement
        for _ in range(iterations):
            try:
                latency = await measure_endpoint(client, method, url, **kwargs)
                latencies.append(latency)
            except Exception as e:
                print(f"  ⚠️ Error: {e}")
                break
        
        if not latencies:
            return {"name": name, "error": "No successful requests"}
        
        return {
            "name": name,
            "method": method,
            "path": path,
            "iterations": len(latencies),
            "min_ms": round(min(latencies), 2),
            "max_ms": round(max(latencies), 2),
            "mean_ms": round(statistics.mean(latencies), 2),
            "median_ms": round(statistics.median(latencies), 2),
            "p95_ms": round(statistics.quantiles(latencies, n=20)[18], 2) if len(latencies) >= 20 else None,
            "p99_ms": round(statistics.quantiles(latencies, n=100)[98], 2) if len(latencies) >= 100 else None,
        }


async def run_performance_tests():
    """Run performance tests on critical endpoints."""
    print("🚀 Starting Performance Tests...\n")
    
    tests = [
        ("Health Check", "GET", "/health"),
        ("API V1 Health", "GET", "/api/v1/health"),
        ("Cache Health", "GET", "/api/v1/cache/health"),
        ("Cache Stats", "GET", "/api/v1/cache/stats"),
        ("Jobs Health", "GET", "/api/v1/jobs/health"),
        ("Jobs Stats", "GET", "/api/v1/jobs/stats"),
        ("Risk Limits", "GET", "/api/v1/risk/limits"),
    ]
    
    results = []
    
    for name, method, path in tests:
        print(f"📊 Testing: {name} ({method} {path})")
        result = await benchmark_endpoint(name, method, path)
        results.append(result)
        
        if "error" in result:
            print(f"  ❌ {result['error']}\n")
        else:
            print(f"  ✓ Mean: {result['mean_ms']}ms | Median: {result['median_ms']}ms | Max: {result['max_ms']}ms")
            if result['p95_ms']:
                print(f"  ✓ P95: {result['p95_ms']}ms | P99: {result['p99_ms']}ms")
            print()
    
    # Summary
    print("\n" + "=" * 70)
    print("📈 PERFORMANCE SUMMARY")
    print("=" * 70)
    
    successful = [r for r in results if "error" not in r]
    
    if successful:
        fastest = min(successful, key=lambda x: x['mean_ms'])
        slowest = max(successful, key=lambda x: x['mean_ms'])
        
        print(f"\n🏆 Fastest: {fastest['name']}")
        print(f"   Mean: {fastest['mean_ms']}ms | Median: {fastest['median_ms']}ms")
        
        print(f"\n🐌 Slowest: {slowest['name']}")
        print(f"   Mean: {slowest['mean_ms']}ms | Median: {slowest['median_ms']}ms")
        
        print(f"\n📊 Overall Statistics:")
        print(f"   Total Tests: {len(results)}")
        print(f"   Successful: {len(successful)}")
        print(f"   Failed: {len(results) - len(successful)}")
        
        avg_mean = statistics.mean([r['mean_ms'] for r in successful])
        print(f"   Average Mean Latency: {round(avg_mean, 2)}ms")
    else:
        print("\n❌ No successful tests!")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(run_performance_tests())
