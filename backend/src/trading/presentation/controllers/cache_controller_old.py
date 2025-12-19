"""Cache monitoring and management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional, Any
import logging

from ...infrastructure.cache import cache_service
from ...interfaces.dependencies.auth import get_current_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cache", tags=["cache"])


@router.get("/health")
async def cache_health():
    """Get cache service health status."""
    try:
        health_data = await cache_service.health_check()
        
        status_code = 200 if health_data.get("status") == "healthy" else 503
        return health_data
        
    except Exception as e:
        logger.error(f"Error checking cache health: {e}")
        raise HTTPException(status_code=503, detail=f"Cache health check failed: {str(e)}")


@router.get("/stats")
async def cache_stats():
    """Get cache statistics and summary."""
    try:
        summary = await cache_service.get_cache_summary()
        return {
            "status": "success",
            "data": summary
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")


@router.get("/market-data/{symbol}")
async def get_cached_market_data(symbol: str):
    """Get cached market data for a symbol."""
    try:
        market_cache = cache_service.get_market_cache()
        
        data = {
            "symbol": symbol,
            "price": await market_cache.get_symbol_price(symbol),
            "order_book": await market_cache.get_order_book(symbol),
            "trade": await market_cache.get_trade(symbol),
            "stats_24h": await market_cache.get_24h_stats(symbol),
            "symbol_info": await market_cache.get_symbol_info(symbol)
        }
        
        return {
            "status": "success",
            "data": data
        }
        
    except Exception as e:
        logger.error(f"Error getting cached market data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get market data: {str(e)}")


@router.get("/price/{symbol}")
async def get_cached_price(symbol: str):
    """Get cached price data for a symbol."""
    try:
        price_cache = cache_service.get_price_cache()
        
        data = {
            "symbol": symbol,
            "current_price": await price_cache.get_current_price(symbol),
            "price_change": await price_cache.get_price_change(symbol, period_minutes=1440),
            "price_history": await price_cache.get_price_history(symbol, limit=50),
            "ohlcv_1h": await price_cache.get_ohlcv_data(symbol, "1h"),
            "ohlcv_1d": await price_cache.get_ohlcv_data(symbol, "1d")
        }
        
        return {
            "status": "success",
            "data": data
        }
        
    except Exception as e:
        logger.error(f"Error getting cached price for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get price data: {str(e)}")\n\n\n@router.get(\"/symbols\")\nasync def get_cached_symbols():\n    \"\"\"Get list of all cached symbols.\"\"\"\n    try:\n        market_cache = cache_service.get_market_cache()\n        symbols = await market_cache.get_all_symbols()\n        \n        return {\n            \"status\": \"success\",\n            \"data\": {\n                \"symbols\": symbols,\n                \"count\": len(symbols)\n            }\n        }\n        \n    except Exception as e:\n        logger.error(f\"Error getting cached symbols: {e}\")\n        raise HTTPException(status_code=500, detail=f\"Failed to get symbols: {str(e)}\")\n\n\n@router.get(\"/sessions/{user_id}\")\nasync def get_user_sessions(\n    user_id: str,\n    current_user_id: str = Depends(get_current_user_id)\n):\n    \"\"\"Get user session information.\"\"\"\n    # Only allow users to see their own sessions or admins\n    if str(current_user_id) != user_id:\n        raise HTTPException(status_code=403, detail=\"Access denied\")\n    \n    try:\n        session_cache = cache_service.get_session_cache()\n        \n        data = {\n            \"user_id\": user_id,\n            \"active_sessions\": await session_cache.get_user_active_sessions(user_id),\n            \"preferences\": await session_cache.get_user_preferences(user_id),\n            \"subscriptions\": await session_cache.get_user_subscriptions(user_id)\n        }\n        \n        return {\n            \"status\": \"success\",\n            \"data\": data\n        }\n        \n    except Exception as e:\n        logger.error(f\"Error getting user sessions for {user_id}: {e}\")\n        raise HTTPException(status_code=500, detail=f\"Failed to get user sessions: {str(e)}\")\n\n\n@router.post(\"/cleanup\")\nasync def cleanup_cache():\n    \"\"\"Clean up expired cache data.\"\"\"\n    try:\n        results = await cache_service.cleanup_expired_data()\n        \n        return {\n            \"status\": \"success\",\n            \"message\": \"Cache cleanup completed\",\n            \"data\": results\n        }\n        \n    except Exception as e:\n        logger.error(f\"Error during cache cleanup: {e}\")\n        raise HTTPException(status_code=500, detail=f\"Cache cleanup failed: {str(e)}\")\n\n\n@router.delete(\"/clear\")\nasync def clear_cache(\n    confirm: bool = Query(False, description=\"Confirmation required to clear all cache\")\n):\n    \"\"\"Clear all cache data (use with extreme caution).\"\"\"\n    if not confirm:\n        raise HTTPException(\n            status_code=400, \n            detail=\"Confirmation required. Set confirm=true to clear all cache data.\"\n        )\n    \n    try:\n        results = await cache_service.clear_all_cache()\n        \n        return {\n            \"status\": \"success\",\n            \"message\": \"All cache data cleared\",\n            \"data\": results\n        }\n        \n    except Exception as e:\n        logger.error(f\"Error clearing cache: {e}\")\n        raise HTTPException(status_code=500, detail=f\"Failed to clear cache: {str(e)}\")\n\n\n@router.post(\"/price-alert\")\nasync def create_price_alert(\n    symbol: str,\n    target_price: float,\n    condition: str,  # 'above' or 'below'\n    ttl: int = 86400,  # 24 hours\n    current_user_id: str = Depends(get_current_user_id)\n):\n    \"\"\"Create a price alert.\"\"\"\n    if condition not in ['above', 'below']:\n        raise HTTPException(status_code=400, detail=\"Condition must be 'above' or 'below'\")\n    \n    try:\n        price_cache = cache_service.get_price_cache()\n        \n        alert_id = await price_cache.set_price_alert(\n            user_id=str(current_user_id),\n            symbol=symbol,\n            target_price=target_price,\n            condition=condition,\n            ttl=ttl\n        )\n        \n        if not alert_id:\n            raise HTTPException(status_code=500, detail=\"Failed to create price alert\")\n        \n        return {\n            \"status\": \"success\",\n            \"message\": \"Price alert created\",\n            \"data\": {\n                \"alert_id\": alert_id,\n                \"symbol\": symbol,\n                \"target_price\": target_price,\n                \"condition\": condition,\n                \"ttl\": ttl\n            }\n        }\n        \n    except Exception as e:\n        logger.error(f\"Error creating price alert: {e}\")\n        raise HTTPException(status_code=500, detail=f\"Failed to create price alert: {str(e)}\")\n\n\n@router.get(\"/price-alerts\")\nasync def get_user_price_alerts(\n    current_user_id: str = Depends(get_current_user_id)\n):\n    \"\"\"Get user's price alerts.\"\"\"\n    try:\n        price_cache = cache_service.get_price_cache()\n        alerts = await price_cache.get_user_alerts(str(current_user_id))\n        \n        return {\n            \"status\": \"success\",\n            \"data\": {\n                \"alerts\": alerts,\n                \"count\": len(alerts)\n            }\n        }\n        \n    except Exception as e:\n        logger.error(f\"Error getting price alerts: {e}\")\n        raise HTTPException(status_code=500, detail=f\"Failed to get price alerts: {str(e)}\")\n\n\n@router.delete(\"/price-alert/{alert_id}\")\nasync def delete_price_alert(\n    alert_id: str,\n    current_user_id: str = Depends(get_current_user_id)\n):\n    \"\"\"Delete a price alert.\"\"\"\n    try:\n        price_cache = cache_service.get_price_cache()\n        \n        # Verify alert belongs to user\n        alert = await price_cache.get_price_alert(alert_id)\n        if not alert:\n            raise HTTPException(status_code=404, detail=\"Price alert not found\")\n        \n        if alert.get(\"user_id\") != str(current_user_id):\n            raise HTTPException(status_code=403, detail=\"Access denied\")\n        \n        success = await price_cache.delete_price_alert(alert_id)\n        if not success:\n            raise HTTPException(status_code=500, detail=\"Failed to delete price alert\")\n        \n        return {\n            \"status\": \"success\",\n            \"message\": \"Price alert deleted\"\n        }\n        \n    except HTTPException:\n        raise\n    except Exception as e:\n        logger.error(f\"Error deleting price alert {alert_id}: {e}\")\n        raise HTTPException(status_code=500, detail=f\"Failed to delete price alert: {str(e)}\")