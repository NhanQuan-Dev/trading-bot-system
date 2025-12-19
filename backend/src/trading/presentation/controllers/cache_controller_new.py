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
        raise HTTPException(status_code=500, detail=f"Failed to get price data: {str(e)}")
