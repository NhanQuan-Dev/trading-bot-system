"""Simple load testing script for API endpoints."""

import asyncio
import time
import statistics
from typing import List, Dict, Any
import httpx
from concurrent.futures import ThreadPoolExecutor


BASE_URL = "http://localhost:8000"
CONCURRENT_REQUESTS = 10
TOTAL_REQUESTS = 100


async def make_request(client: httpx.AsyncClient, method: str, url: str, **kwargs) -> Dict[str, Any]:
    """Make a single HTTP request and measure latency."""
    start = time.perf_counter()
    try:
        response = await client.request(method, url, **kwargs)
        end = time.perf_counter()
        
        return {
            "success": True,
            "status_code": response.status_code,
            "latency_ms": (end - start) * 1000,
        }
    except Exception as e:
        end = time.perf_counter()
        return {
            "success": False,
            "error": str(e),
            "latency_ms": (end - start) * 1000,
        }


async def load_test_endpoint(
    name: str,
    method: str,
    path: str,
    concurrent: int = CONCURRENT_REQUESTS,
    total: int = TOTAL_REQUESTS,
    **kwargs
) -> Dict[str, Any]:
    """Load test a single endpoint."""
    url = f"{BASE_URL}{path}"
    results: List[Dict[str, Any]] = []
    
    print(f"\n🔥 Load Testing: {name}")
    print(f"   URL: {method} {path}")
    print(f"   Concurrent: {concurrent} | Total: {total}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create batches of concurrent requests
        for batch_start in range(0, total, concurrent):
            batch_size = min(concurrent, total - batch_start)
            tasks = [
                make_request(client, method, url, **kwargs)
                for _ in range(batch_size)
            ]
            
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)
            
            # Progress indicator
            progress = (batch_start + batch_size) / total * 100
            print(f"   Progress: {progress:.1f}%", end="\r")
    
    # Analyze results
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    if not successful:
        print(f"\n   ❌ All requests failed!")
        return {"name": name, "success": False}
    
    latencies = [r["latency_ms"] for r in successful]
    
    analysis = {
        "name": name,
        "method": method,
        "path": path,
        "total_requests": total,
        "concurrent_requests": concurrent,
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": len(successful) / total * 100,
        "min_ms": round(min(latencies), 2),
        "max_ms": round(max(latencies), 2),
        "mean_ms": round(statistics.mean(latencies), 2),
        "median_ms": round(statistics.median(latencies), 2),
        "stdev_ms": round(statistics.stdev(latencies), 2) if len(latencies) > 1 else 0,
        "p95_ms": round(statistics.quantiles(latencies, n=20)[18], 2) if len(latencies) >= 20 else None,
        "p99_ms": round(statistics.quantiles(latencies, n=100)[98], 2) if len(latencies) >= 100 else None,
    }
    
    # Calculate requests per second
    total_time = sum(latencies) / 1000  # Convert to seconds
    analysis["requests_per_second"] = round(len(successful) / (total_time / concurrent), 2)
    
    print(f"\n   ✓ Success Rate: {analysis['success_rate']:.1f}%")
    print(f"   ✓ Mean Latency: {analysis['mean_ms']}ms | P95: {analysis['p95_ms']}ms")
    print(f"   ✓ Throughput: ~{analysis['requests_per_second']} req/s")
    
    return analysis


async def run_load_tests():
    """Run load tests on critical endpoints."""
    print("\n" + "="*70)
    print("🚀 API LOAD TESTING")
    print("="*70)
    
    tests = [
        ("Health Check", "GET", "/health"),
        ("API Health", "GET", "/api/v1/health"),
        ("Cache Health", "GET", "/api/v1/cache/health"),
        ("Cache Stats", "GET", "/api/v1/cache/stats"),
        ("Jobs Health", "GET", "/api/v1/jobs/health"),
    ]
    
    results = []
    
    for name, method, path in tests:
        result = await load_test_endpoint(
            name, method, path,
            concurrent=CONCURRENT_REQUESTS,
            total=TOTAL_REQUESTS
        )
        results.append(result)
        await asyncio.sleep(0.5)  # Brief pause between tests
    
    # Print summary
    print("\n" + "="*70)
    print("📊 LOAD TEST SUMMARY")
    print("="*70)
    
    successful_tests = [r for r in results if r.get("success_rate", 0) > 0]
    
    if successful_tests:
        print(f"\nTotal Requests: {TOTAL_REQUESTS * len(tests)}")
        print(f"Concurrent: {CONCURRENT_REQUESTS}")
        
        avg_success_rate = statistics.mean([r["success_rate"] for r in successful_tests])
        avg_latency = statistics.mean([r["mean_ms"] for r in successful_tests])
        
        print(f"\nAverage Success Rate: {avg_success_rate:.2f}%")
        print(f"Average Latency: {avg_latency:.2f}ms")
        
        # Find best and worst
        fastest = min(successful_tests, key=lambda x: x["mean_ms"])
        slowest = max(successful_tests, key=lambda x: x["mean_ms"])
        
        print(f"\n🏆 Fastest: {fastest['name']} ({fastest['mean_ms']}ms)")
        print(f"🐌 Slowest: {slowest['name']} ({slowest['mean_ms']}ms)")
        
        # Check for any failures
        failed_tests = [r for r in results if r.get("failed", 0) > 0]
        if failed_tests:
            print(f"\n⚠️  {len(failed_tests)} endpoint(s) had failures")
            for test in failed_tests:
                print(f"   - {test['name']}: {test['failed']} failures")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    print(f"\nConfiguration:")
    print(f"  Base URL: {BASE_URL}")
    print(f"  Concurrent Requests: {CONCURRENT_REQUESTS}")
    print(f"  Total Requests per Endpoint: {TOTAL_REQUESTS}")
    
    asyncio.run(run_load_tests())
