import logging
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal

from .base_cache import BaseCache

logger = logging.getLogger(__name__)


class PriceCache(BaseCache):
    """Specialized cache for price data with time-series support."""
    
    def __init__(self):
        super().__init__(prefix="price", default_ttl=300)  # 5 minutes default
    
    async def set_current_price(
        self, 
        symbol: str, 
        price: float, 
        volume: Optional[float] = None, 
        timestamp: Optional[datetime] = None,
        ttl: int = 30
    ) -> bool:
        """Set current price for symbol."""
        key = f"current:{symbol}"
        
        price_data = {
            "symbol": symbol,
            "price": float(price),
            "volume": float(volume) if volume else None,
            "timestamp": (timestamp or datetime.utcnow()).isoformat()
        }
        
        success = await self.set(key, price_data, ttl)
        
        # Also update price history
        if success:
            await self._add_price_point(symbol, price, volume, timestamp)
        
        return success
    
    async def get_current_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current price for symbol."""
        key = f"current:{symbol}"
        return await self.get(key)
    
    async def get_current_prices(
        self, 
        symbols: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Get current prices for multiple symbols."""
        result = {}
        for symbol in symbols:
            price = await self.get_current_price(symbol)
            if price:
                result[symbol] = price
        return result
    
    async def _add_price_point(
        self, 
        symbol: str, 
        price: float, 
        volume: Optional[float] = None, 
        timestamp: Optional[datetime] = None
    ) -> bool:
        """Add price point to time series."""
        ts = timestamp or datetime.utcnow()
        score = ts.timestamp()  # Use timestamp as score for sorted set
        
        price_point = {
            "price": float(price),
            "volume": float(volume) if volume else None,
            "timestamp": ts.isoformat()
        }
        
        series_key = self._make_key(f"series:{symbol}")
        
        try:
            # Add to sorted set with timestamp as score
            point_data = self._serialize(price_point)
            await self.redis.zadd(series_key, {point_data: score})
            
            # Keep only last 1000 points
            await self.redis.zremrangebyrank(series_key, 0, -1001)
            
            # Set expiration
            await self.redis.expire(series_key, 3600)  # 1 hour
            
            return True
        except Exception as e:
            logger.error(f"Error adding price point for {symbol}: {e}")
            return False
    
    async def get_price_history(
        self, 
        symbol: str, 
        start_time: Optional[datetime] = None, 
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get price history for symbol."""
        series_key = self._make_key(f"series:{symbol}")
        
        try:
            if start_time and end_time:
                # Get range by timestamp
                start_score = start_time.timestamp()
                end_score = end_time.timestamp()
                data = await self.redis.zrangebyscore(
                    series_key, start_score, end_score, withscores=True
                )
            else:
                # Get latest points
                data = await self.redis.zrevrange(
                    series_key, 0, limit - 1, withscores=True
                )
            
            # Parse results
            history = []
            for point_data, score in data:
                try:
                    point = self._deserialize(point_data)
                    if isinstance(point, dict):
                        history.append(point)
                except Exception:
                    continue
            
            return history
        except Exception as e:
            logger.error(f"Error getting price history for {symbol}: {e}")
            return []
    
    async def get_price_change(
        self, 
        symbol: str, 
        period_minutes: int = 1440  # 24 hours default
    ) -> Optional[Dict[str, float]]:
        """Get price change over period."""
        current = await self.get_current_price(symbol)
        if not current:
            return None
        
        # Get historical price
        start_time = datetime.utcnow() - timedelta(minutes=period_minutes)
        history = await self.get_price_history(symbol, start_time=start_time, limit=1)
        
        if not history:
            return None
        
        old_price = history[0]["price"]
        current_price = current["price"]
        
        change = current_price - old_price
        change_percent = (change / old_price * 100) if old_price != 0 else 0
        
        return {
            "price_change": change,
            "price_change_percent": change_percent,
            "current_price": current_price,
            "previous_price": old_price
        }
    
    async def set_price_alert(
        self, 
        user_id: str, 
        symbol: str, 
        target_price: float, 
        condition: str,  # 'above' or 'below'
        ttl: int = 86400  # 24 hours
    ) -> str:
        """Set price alert for user."""
        alert_id = f"{user_id}:{symbol}:{condition}:{target_price}"
        key = f"alert:{alert_id}"
        
        alert_data = {
            "user_id": user_id,
            "symbol": symbol,
            "target_price": float(target_price),
            "condition": condition,
            "created_at": datetime.utcnow().isoformat(),
            "triggered": False
        }
        
        success = await self.set(key, alert_data, ttl)
        if success:
            # Add to user's alerts index
            user_alerts_key = self._make_key(f"user_alerts:{user_id}")
            await self.redis.sadd(user_alerts_key, alert_id)
            await self.redis.expire(user_alerts_key, ttl)
        
        return alert_id if success else None
    
    async def get_price_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Get price alert."""
        key = f"alert:{alert_id}"
        return await self.get(key)
    
    async def get_user_alerts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all alerts for user."""
        user_alerts_key = self._make_key(f"user_alerts:{user_id}")
        
        try:
            alert_ids = await self.redis.smembers(user_alerts_key)
            alerts = []
            
            for alert_id in alert_ids:
                alert = await self.get_price_alert(alert_id)
                if alert:
                    alert["alert_id"] = alert_id
                    alerts.append(alert)
            
            return alerts
        except Exception as e:
            logger.error(f"Error getting alerts for user {user_id}: {e}")
            return []
    
    async def check_price_alerts(self, symbol: str, current_price: float) -> List[str]:
        """Check and trigger price alerts for symbol."""
        pattern = self._make_key(f"alert:*:{symbol}:*")
        triggered_alerts = []
        
        try:
            alert_keys = await self.redis.keys(pattern)
            
            for key in alert_keys:
                alert_data = await self.redis.get(key)
                if not alert_data:
                    continue
                
                alert = self._deserialize(alert_data)
                if not isinstance(alert, dict) or alert.get("triggered"):
                    continue
                
                target_price = alert["target_price"]
                condition = alert["condition"]
                
                triggered = False
                if condition == "above" and current_price >= target_price:
                    triggered = True
                elif condition == "below" and current_price <= target_price:
                    triggered = True
                
                if triggered:
                    # Mark as triggered
                    alert["triggered"] = True
                    alert["triggered_at"] = datetime.utcnow().isoformat()
                    alert["triggered_price"] = current_price
                    
                    await self.redis.set(key, self._serialize(alert), ex=3600)
                    
                    # Extract alert ID from key
                    alert_id = key.replace(self._make_key("alert:"), "")
                    triggered_alerts.append(alert_id)
            
            return triggered_alerts
        except Exception as e:
            logger.error(f"Error checking price alerts for {symbol}: {e}")
            return []
    
    async def delete_price_alert(self, alert_id: str) -> bool:
        """Delete price alert."""
        alert = await self.get_price_alert(alert_id)
        if not alert:
            return False
        
        user_id = alert["user_id"]
        
        # Delete alert
        key = f"alert:{alert_id}"
        success = await self.delete(key)
        
        # Remove from user's alerts
        if success:
            user_alerts_key = self._make_key(f"user_alerts:{user_id}")
            await self.redis.srem(user_alerts_key, alert_id)
        
        return success
    
    async def get_ohlcv_data(
        self, 
        symbol: str, 
        interval: str,  # '1m', '5m', '1h', '1d'
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get OHLCV (candlestick) data."""
        key = f"ohlcv:{symbol}:{interval}"
        return await self.get(key) or []
    
    async def set_ohlcv_data(
        self, 
        symbol: str, 
        interval: str, 
        ohlcv_data: List[Dict[str, Any]], 
        ttl: int = 3600
    ) -> bool:
        """Set OHLCV data."""
        key = f"ohlcv:{symbol}:{interval}"
        
        data = {
            "symbol": symbol,
            "interval": interval,
            "data": ohlcv_data,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        return await self.set(key, data, ttl)
    
    async def cleanup_old_data(self, days: int = 7) -> Dict[str, int]:
        """Clean up old price data."""
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        cutoff_score = cutoff_time.timestamp()
        
        cleaned = {
            "series_points": 0,
            "alerts": 0,
            "ohlcv": 0
        }
        
        try:
            # Clean price series
            series_keys = await self.redis.keys(self._make_key("series:*"))
            for key in series_keys:
                removed = await self.redis.zremrangebyscore(key, 0, cutoff_score)
                cleaned["series_points"] += removed
            
            # Clean old alerts
            alert_keys = await self.redis.keys(self._make_key("alert:*"))
            for key in alert_keys:
                data = await self.redis.get(key)
                if data:
                    alert = self._deserialize(data)
                    if isinstance(alert, dict) and "created_at" in alert:
                        try:
                            created_time = datetime.fromisoformat(alert["created_at"])
                            if created_time < cutoff_time:
                                await self.redis.delete(key)
                                cleaned["alerts"] += 1
                        except (ValueError, TypeError):
                            continue
            
            return cleaned
        except Exception as e:
            logger.error(f"Error cleaning up price data: {e}")
            return cleaned


# Global price cache instance
price_cache = PriceCache()