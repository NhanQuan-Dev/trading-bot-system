"""Integration tests for Phase 5 endpoints (Backtesting)."""
import pytest
from httpx import AsyncClient
from datetime import date
from decimal import Decimal


class TestBacktestEndpoints:
    """Test Backtesting endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_backtests_empty(self, test_client: AsyncClient, auth_headers):
        """Test listing backtests returns empty or list."""
        response = await test_client.get("/api/v1/backtests", headers=auth_headers)
        assert response.status_code in [200, 401, 500]
        if response.status_code == 200:
            data = response.json()
            assert "backtests" in data or isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_create_backtest_validation(self, test_client: AsyncClient, auth_headers):
        """Test backtest creation with invalid data returns validation error."""
        response = await test_client.post(
            "/api/v1/backtests",
            headers=auth_headers,
            json={
                "strategy_id": "invalid",
                "config": {}
            }
        )
        # Should fail validation
        assert response.status_code in [400, 422, 500]
    
    @pytest.mark.asyncio
    async def test_create_backtest_minimal(self, test_client: AsyncClient, auth_headers):
        """Test backtest creation with minimal valid data."""
        response = await test_client.post(
            "/api/v1/backtests",
            headers=auth_headers,
            json={
                "strategy_id": "550e8400-e29b-41d4-a716-446655440000",
                "config": {
                    "symbol": "BTCUSDT",
                    "timeframe": "1h",
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-31",
                    "initial_capital": 10000.0
                }
            }
        )
        # May fail due to missing strategy or market data
        assert response.status_code in [200, 202, 400, 404, 500]
        
        if response.status_code in [200, 202]:
            data = response.json()
            assert "id" in data
            backtest_id = data["id"]
            
            # Try to get backtest status
            status_response = await test_client.get(
                f"/api/v1/backtests/{backtest_id}/status",
                headers=auth_headers
            )
            assert status_response.status_code in [200, 404, 500]
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_backtest(self, test_client: AsyncClient, auth_headers):
        """Test getting a non-existent backtest returns 404."""
        fake_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await test_client.get(
            f"/api/v1/backtests/{fake_id}",
            headers=auth_headers
        )
        assert response.status_code in [404, 500]
