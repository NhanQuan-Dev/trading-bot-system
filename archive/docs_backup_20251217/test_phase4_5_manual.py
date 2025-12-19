#!/usr/bin/env python3
"""Manual testing script for Phase 4 and 5 endpoints."""
import httpx
import json
import sys
from typing import Dict, Any


BASE_URL = "http://localhost:8000"


def print_result(endpoint: str, response: httpx.Response):
    """Print test result."""
    status = "✅" if response.status_code < 400 else "❌"
    print(f"{status} {endpoint}: {response.status_code}")
    if response.status_code >= 400:
        try:
            print(f"   Error: {response.json()}")
        except:
            print(f"   Error: {response.text[:100]}")


def test_phase4_cache():
    """Test Cache endpoints."""
    print("\n=== CACHE ENDPOINTS ===")
    
    # Cache health
    response = httpx.get(f"{BASE_URL}/api/v1/cache/health", timeout=5)
    print_result("GET /api/v1/cache/health", response)
    
    # Cache stats
    response = httpx.get(f"{BASE_URL}/api/v1/cache/stats", timeout=5)
    print_result("GET /api/v1/cache/stats", response)


def test_phase4_jobs():
    """Test Jobs endpoints."""
    print("\n=== JOBS ENDPOINTS ===")
    
    # Jobs health
    response = httpx.get(f"{BASE_URL}/api/v1/jobs/health", timeout=5)
    print_result("GET /api/v1/jobs/health", response)
    if response.status_code == 200:
        print(f"   Data: {json.dumps(response.json(), indent=2)[:200]}")
    
    # Jobs stats
    response = httpx.get(f"{BASE_URL}/api/v1/jobs/stats", timeout=5)
    print_result("GET /api/v1/jobs/stats", response)


def test_phase4_risk():
    """Test Risk endpoints."""
    print("\n=== RISK ENDPOINTS ===")
    
    # List risk limits (requires auth)
    response = httpx.get(f"{BASE_URL}/api/v1/risk/limits", timeout=5)
    print_result("GET /api/v1/risk/limits", response)
    
    # Get risk alerts (requires auth)
    response = httpx.get(f"{BASE_URL}/api/v1/risk/alerts", timeout=5)
    print_result("GET /api/v1/risk/alerts", response)


def test_phase5_backtests():
    """Test Backtest endpoints."""
    print("\n=== BACKTEST ENDPOINTS ===")
    
    # List backtests (requires auth)
    response = httpx.get(f"{BASE_URL}/api/v1/backtests", timeout=5)
    print_result("GET /api/v1/backtests", response)
    
    # Try to create backtest (requires auth and valid data)
    response = httpx.post(
        f"{BASE_URL}/api/v1/backtests",
        json={
            "strategy_id": "550e8400-e29b-41d4-a716-446655440000",
            "config": {
                "symbol": "BTCUSDT",
                "timeframe": "1h",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "initial_capital": 10000.0
            }
        },
        timeout=5
    )
    print_result("POST /api/v1/backtests", response)


def test_health():
    """Test basic health endpoint."""
    print("\n=== HEALTH CHECK ===")
    response = httpx.get(f"{BASE_URL}/health", timeout=5)
    print_result("GET /health", response)


def main():
    """Run all tests."""
    print("🚀 Testing Phase 4 and 5 Endpoints")
    print(f"Base URL: {BASE_URL}")
    
    try:
        test_health()
        test_phase4_cache()
        test_phase4_jobs()
        test_phase4_risk()
        test_phase5_backtests()
        
        print("\n✅ Manual testing complete!")
        print("\nNote: Some endpoints require authentication (401) - this is expected.")
        print("Note: Some endpoints may return 500 if Redis/dependencies are not configured.")
        
    except httpx.ConnectError:
        print("\n❌ ERROR: Cannot connect to server. Is it running on port 8000?")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
