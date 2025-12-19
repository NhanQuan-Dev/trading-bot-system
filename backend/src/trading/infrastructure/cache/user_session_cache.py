import logging
import uuid
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta

from .base_cache import BaseCache

logger = logging.getLogger(__name__)


class UserSessionCache(BaseCache):
    """Cache for user sessions and authentication data."""
    
    def __init__(self):
        super().__init__(prefix="session", default_ttl=3600)  # 1 hour default
    
    async def set_user_session(
        self, 
        user_id: str, 
        session_data: Dict[str, Any], 
        ttl: int = 3600
    ) -> str:
        """Create new user session."""
        session_id = str(uuid.uuid4())
        session_key = f"user:{user_id}:{session_id}"
        
        session_info = {
            "user_id": user_id,
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            **session_data
        }
        
        success = await self.set(session_key, session_info, ttl)
        if success:
            # Also store session ID mapping
            await self.set(f"session_id:{session_id}", user_id, ttl)
            
            # Add to user's active sessions
            user_sessions_key = f"active:{user_id}"
            await self.redis.sadd(self._make_key(user_sessions_key), session_id)
            await self.redis.expire(self._make_key(user_sessions_key), ttl)
            
            return session_id
        
        raise Exception("Failed to create session")
    
    async def get_user_session(
        self, 
        user_id: str, 
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get user session data."""
        session_key = f"user:{user_id}:{session_id}"
        return await self.get(session_key)
    
    async def get_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by session ID."""
        user_id = await self.get(f"session_id:{session_id}")
        if user_id:
            return await self.get_user_session(user_id, session_id)
        return None
    
    async def update_session_activity(
        self, 
        user_id: str, 
        session_id: str, 
        activity_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update session last activity."""
        session = await self.get_user_session(user_id, session_id)
        if not session:
            return False
        
        session["last_activity"] = datetime.utcnow().isoformat()
        if activity_data:
            session.update(activity_data)
        
        session_key = f"user:{user_id}:{session_id}"
        return await self.set(session_key, session, ttl=3600)
    
    async def delete_user_session(
        self, 
        user_id: str, 
        session_id: str
    ) -> bool:
        """Delete user session."""
        session_key = f"user:{user_id}:{session_id}"
        session_id_key = f"session_id:{session_id}"
        user_sessions_key = f"active:{user_id}"
        
        # Delete session data
        success1 = await self.delete(session_key)
        success2 = await self.delete(session_id_key)
        
        # Remove from active sessions
        try:
            await self.redis.srem(self._make_key(user_sessions_key), session_id)
        except Exception as e:
            logger.error(f"Error removing session from active set: {e}")
        
        return success1 and success2
    
    async def get_user_active_sessions(self, user_id: str) -> List[str]:
        """Get list of active session IDs for user."""
        user_sessions_key = f"active:{user_id}"
        try:
            sessions = await self.redis.smembers(self._make_key(user_sessions_key))
            return list(sessions)
        except Exception as e:
            logger.error(f"Error getting active sessions for user {user_id}: {e}")
            return []
    
    async def delete_all_user_sessions(self, user_id: str) -> int:
        """Delete all sessions for a user."""
        active_sessions = await self.get_user_active_sessions(user_id)
        deleted_count = 0
        
        for session_id in active_sessions:
            if await self.delete_user_session(user_id, session_id):
                deleted_count += 1
        
        return deleted_count
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        try:
            # Get all session keys
            pattern = self._make_key("user:*:*")
            session_keys = await self.redis.keys(pattern)
            
            cleaned_count = 0
            cutoff_time = datetime.utcnow() - timedelta(hours=24)  # 24 hours
            
            for key in session_keys:
                data = await self.redis.get(key)
                if data:
                    session_data = self._deserialize(data)
                    if isinstance(session_data, dict) and "last_activity" in session_data:
                        try:
                            last_activity = datetime.fromisoformat(session_data["last_activity"])
                            if last_activity < cutoff_time:
                                await self.redis.delete(key)
                                cleaned_count += 1
                        except (ValueError, TypeError):
                            # Invalid timestamp, delete
                            await self.redis.delete(key)
                            cleaned_count += 1
            
            return cleaned_count
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
            return 0
    
    async def set_user_preferences(
        self, 
        user_id: str, 
        preferences: Dict[str, Any], 
        ttl: int = 7200
    ) -> bool:
        """Set user preferences."""
        key = f"prefs:{user_id}"
        
        prefs_data = {
            "user_id": user_id,
            "preferences": preferences,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        return await self.set(key, prefs_data, ttl)
    
    async def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user preferences."""
        key = f"prefs:{user_id}"
        data = await self.get(key)
        if data and isinstance(data, dict):
            return data.get("preferences")
        return None
    
    async def set_user_subscription(
        self, 
        user_id: str, 
        subscription_type: str, 
        subscription_data: Dict[str, Any], 
        ttl: int = 3600
    ) -> bool:
        """Set user WebSocket subscription."""
        key = f"subscription:{user_id}:{subscription_type}"
        
        sub_data = {
            "user_id": user_id,
            "type": subscription_type,
            "data": subscription_data,
            "created_at": datetime.utcnow().isoformat()
        }
        
        return await self.set(key, sub_data, ttl)
    
    async def get_user_subscription(
        self, 
        user_id: str, 
        subscription_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get user WebSocket subscription."""
        key = f"subscription:{user_id}:{subscription_type}"
        return await self.get(key)
    
    async def get_user_subscriptions(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        """Get all user subscriptions."""
        pattern = self._make_key(f"subscription:{user_id}:*")
        try:
            keys = await self.redis.keys(pattern)
            subscriptions = {}
            
            for key in keys:
                # Extract subscription type from key
                sub_type = key.split(":")[-1]
                data = await self.redis.get(key)
                if data:
                    subscriptions[sub_type] = self._deserialize(data)
            
            return subscriptions
        except Exception as e:
            logger.error(f"Error getting user subscriptions for {user_id}: {e}")
            return {}
    
    async def delete_user_subscription(
        self, 
        user_id: str, 
        subscription_type: str
    ) -> bool:
        """Delete user subscription."""
        key = f"subscription:{user_id}:{subscription_type}"
        return await self.delete(key)
    
    async def set_rate_limit(
        self, 
        user_id: str, 
        action: str, 
        count: int = 1, 
        window: int = 60
    ) -> int:
        """Set rate limit counter for user action."""
        key = f"rate_limit:{user_id}:{action}"
        cache_key = self._make_key(key)
        
        try:
            # Increment counter
            current = await self.redis.incr(cache_key)
            
            # Set expiration on first increment
            if current == 1:
                await self.redis.expire(cache_key, window)
            
            return current
        except Exception as e:
            logger.error(f"Error setting rate limit for {user_id}:{action}: {e}")
            return 0
    
    async def get_rate_limit(
        self, 
        user_id: str, 
        action: str
    ) -> int:
        """Get current rate limit count."""
        key = f"rate_limit:{user_id}:{action}"
        try:
            count = await self.get(key)
            return int(count) if count else 0
        except (ValueError, TypeError):
            return 0
    
    async def is_rate_limited(
        self, 
        user_id: str, 
        action: str, 
        limit: int
    ) -> bool:
        """Check if user is rate limited for action."""
        current_count = await self.get_rate_limit(user_id, action)
        return current_count >= limit


# Global user session cache instance
user_session_cache = UserSessionCache()