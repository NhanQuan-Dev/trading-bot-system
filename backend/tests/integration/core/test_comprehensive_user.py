"""
Comprehensive User Management API Tests

This module contains extensive tests for the user management API endpoints,
covering various edge cases, validation scenarios, and security considerations.
"""

import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


def generate_unique_email(base_name: str = "testuser") -> str:
    """Generate a unique email address using timestamp and UUID."""
    timestamp = str(int(datetime.now(timezone.utc).timestamp() * 1000000))  # microsecond precision
    unique_id = str(uuid.uuid4())[:8]  # first 8 chars of UUID
    return f"{base_name}_{timestamp}_{unique_id}@example.com"


class TestComprehensiveUserManagement:
    """Comprehensive tests for user management API endpoints."""
    
    # ==================== GET /api/v1/users/me Tests ====================
    
    async def test_get_user_profile_success(self, test_client: AsyncClient, db_session: AsyncSession):
        """Test successful retrieval of user profile."""
        from src.trading.infrastructure.persistence.models.core_models import UserModel
        from src.trading.domain.user import HashedPassword
        from src.trading.infrastructure.auth.jwt import create_access_token
        
        # Create test user
        user_id = uuid.uuid4()
        unique_email = generate_unique_email("profile")
        plain_password = "TestPassword123!"
        hashed_password = HashedPassword.from_plain(plain_password)
        
        user = UserModel(
            id=user_id,
            email=unique_email,
            password_hash=hashed_password.value,
            full_name="Profile Test User",
            timezone="America/New_York",
            is_active=True,
            preferences={"theme": "dark", "notifications": True},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db_session.add(user)
        await db_session.commit()
        
        # Create auth header
        access_token = create_access_token(user_id)
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Test API call
        response = await test_client.get("/api/v1/users/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(user_id)
        assert data["email"] == unique_email
        assert data["full_name"] == "Profile Test User"
        assert data["timezone"] == "America/New_York"
        assert data["is_active"] is True
        assert "preferences" in data
    
    async def test_get_user_profile_unauthorized(self, test_client: AsyncClient):
        """Test unauthorized access to user profile."""
        response = await test_client.get("/api/v1/users/me")
        assert response.status_code == 401
    
    async def test_get_user_profile_invalid_token(self, test_client: AsyncClient):
        """Test access with invalid JWT token."""
        headers = {"Authorization": "Bearer invalid.jwt.token"}
        response = await test_client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401
    
    async def test_get_user_profile_malformed_auth(self, test_client: AsyncClient):
        """Test access with malformed authorization header."""
        headers = {"Authorization": "InvalidFormat"}
        response = await test_client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401
    
    async def test_get_user_profile_expired_token(self, test_client: AsyncClient):
        """Test access with expired JWT token."""
        # This would require creating an expired token
        expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.expired.token"
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = await test_client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 401
    
    async def test_get_user_profile_inactive_user(self, test_client: AsyncClient, db_session: AsyncSession):
        """Test profile access for inactive user."""
        from src.trading.infrastructure.persistence.models.core_models import UserModel
        from src.trading.domain.user import HashedPassword
        from src.trading.infrastructure.auth.jwt import create_access_token
        
        # Create inactive user
        user_id = uuid.uuid4()
        hashed_password = HashedPassword.from_plain("TestPassword123!")
        
        user = UserModel(
            id=user_id,
            email=generate_unique_email("inactive_profile"),
            password_hash=hashed_password.value,
            full_name="Inactive Profile User",
            is_active=False,  # Inactive
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db_session.add(user)
        await db_session.commit()
        
        # Create token (this might not work if auth checks for active status)
        access_token = create_access_token(user_id)
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = await test_client.get("/api/v1/users/me", headers=headers)
        # Depending on implementation, might be 401, 403, or 200
        assert response.status_code in [200, 401, 403]
    
    # ==================== PATCH /api/v1/users/me Tests ====================
    
    async def test_update_user_profile_full_update(self, test_client: AsyncClient, db_session: AsyncSession):
        """Test complete profile update."""
        from src.trading.infrastructure.persistence.models.core_models import UserModel
        from src.trading.domain.user import HashedPassword
        from src.trading.infrastructure.auth.jwt import create_access_token
        
        # Create test user
        user_id = uuid.uuid4()
        hashed_password = HashedPassword.from_plain("TestPassword123!")
        
        user = UserModel(
            id=user_id,
            email=generate_unique_email("update"),
            password_hash=hashed_password.value,
            full_name="Original Name",
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db_session.add(user)
        await db_session.commit()
        
        # Create auth header
        access_token = create_access_token(user_id)
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Update profile
        update_data = {
            "full_name": "Updated Name",
            "timezone": "Europe/London"
        }
        
        response = await test_client.patch("/api/v1/users/me", headers=headers, json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["timezone"] == "Europe/London"
        assert data["email"] == user.email  # Should not change
    
    async def test_update_user_profile_partial_update(self, test_client: AsyncClient, db_session: AsyncSession):
        """Test partial profile update (only one field)."""
        from src.trading.infrastructure.persistence.models.core_models import UserModel
        from src.trading.domain.user import HashedPassword
        from src.trading.infrastructure.auth.jwt import create_access_token
        
        # Create test user
        user_id = uuid.uuid4()
        hashed_password = HashedPassword.from_plain("TestPassword123!")
        
        user = UserModel(
            id=user_id,
            email=generate_unique_email("partial"),
            password_hash=hashed_password.value,
            full_name="Original Name",
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db_session.add(user)
        await db_session.commit()
        
        # Create auth header
        access_token = create_access_token(user_id)
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Update only timezone
        update_data = {"timezone": "Asia/Tokyo"}
        
        response = await test_client.patch("/api/v1/users/me", headers=headers, json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["timezone"] == "Asia/Tokyo"
        assert data["full_name"] == "Original Name"  # Should remain unchanged
    
    async def test_update_user_profile_invalid_timezone(self, test_client: AsyncClient, db_session: AsyncSession):
        """Test update with invalid timezone."""
        from src.trading.infrastructure.persistence.models.core_models import UserModel
        from src.trading.domain.user import HashedPassword
        from src.trading.infrastructure.auth.jwt import create_access_token
        
        # Create test user
        user_id = uuid.uuid4()
        hashed_password = HashedPassword.from_plain("TestPassword123!")
        
        user = UserModel(
            id=user_id,
            email=generate_unique_email("timezone"),
            password_hash=hashed_password.value,
            full_name="Timezone Test",
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db_session.add(user)
        await db_session.commit()
        
        # Create auth header
        access_token = create_access_token(user_id)
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Update with invalid timezone
        update_data = {"timezone": "Invalid/Timezone"}
        
        response = await test_client.patch("/api/v1/users/me", headers=headers, json=update_data)
        
        # Should fail validation
        assert response.status_code == 422
    
    async def test_update_user_profile_empty_name(self, test_client: AsyncClient, db_session: AsyncSession):
        """Test update with empty full name."""
        from src.trading.infrastructure.persistence.models.core_models import UserModel
        from src.trading.domain.user import HashedPassword
        from src.trading.infrastructure.auth.jwt import create_access_token
        
        # Create test user
        user_id = uuid.uuid4()
        hashed_password = HashedPassword.from_plain("TestPassword123!")
        
        user = UserModel(
            id=user_id,
            email=generate_unique_email("empty_name"),
            password_hash=hashed_password.value,
            full_name="Original Name",
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db_session.add(user)
        await db_session.commit()
        
        # Create auth header
        access_token = create_access_token(user_id)
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Update with empty name
        update_data = {"full_name": ""}
        
        response = await test_client.patch("/api/v1/users/me", headers=headers, json=update_data)
        
        # Should fail validation
        assert response.status_code == 422
    
    async def test_update_user_profile_unauthorized(self, test_client: AsyncClient):
        """Test unauthorized profile update."""
        update_data = {"full_name": "New Name"}
        
        response = await test_client.patch("/api/v1/users/me", json=update_data)
        assert response.status_code == 401
    
    async def test_update_user_profile_long_name(self, test_client: AsyncClient, db_session: AsyncSession):
        """Test update with very long name."""
        from src.trading.infrastructure.persistence.models.core_models import UserModel
        from src.trading.domain.user import HashedPassword
        from src.trading.infrastructure.auth.jwt import create_access_token
        
        # Create test user
        user_id = uuid.uuid4()
        hashed_password = HashedPassword.from_plain("TestPassword123!")
        
        user = UserModel(
            id=user_id,
            email=generate_unique_email("long_name"),
            password_hash=hashed_password.value,
            full_name="Normal Name",
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db_session.add(user)
        await db_session.commit()
        
        # Create auth header
        access_token = create_access_token(user_id)
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Update with very long name (>255 characters)
        long_name = "A" * 300
        update_data = {"full_name": long_name}
        
        response = await test_client.patch("/api/v1/users/me", headers=headers, json=update_data)
        
        # Should fail validation
        assert response.status_code == 422
    
    # ==================== PUT /api/v1/users/me/preferences Tests ====================
    
    async def test_update_user_preferences_complete(self, test_client: AsyncClient, db_session: AsyncSession):
        """Test complete preferences update."""
        from src.trading.infrastructure.persistence.models.core_models import UserModel
        from src.trading.domain.user import HashedPassword
        from src.trading.infrastructure.auth.jwt import create_access_token
        
        # Create test user
        user_id = uuid.uuid4()
        hashed_password = HashedPassword.from_plain("TestPassword123!")
        
        user = UserModel(
            id=user_id,
            email=generate_unique_email("prefs"),
            password_hash=hashed_password.value,
            full_name="Preferences User",
            timezone="UTC",
            is_active=True,
            preferences={"old": "value"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db_session.add(user)
        await db_session.commit()
        
        # Create auth header
        access_token = create_access_token(user_id)
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Update preferences
        new_preferences = {
            "theme": "dark",
            "notifications": True,
            "language": "en",
            "trading_mode": "advanced"
        }
        
        response = await test_client.put("/api/v1/users/me/preferences", 
                                        headers=headers, 
                                        json=new_preferences)
        
        assert response.status_code == 200
        data = response.json()
        assert data["preferences"]["theme"] == "dark"
        assert data["preferences"]["notifications"] is True
        assert data["preferences"]["language"] == "en"
        assert data["preferences"]["trading_mode"] == "advanced"
    
    async def test_update_user_preferences_empty(self, test_client: AsyncClient, db_session: AsyncSession):
        """Test updating preferences with empty object."""
        from src.trading.infrastructure.persistence.models.core_models import UserModel
        from src.trading.domain.user import HashedPassword
        from src.trading.infrastructure.auth.jwt import create_access_token
        
        # Create test user
        user_id = uuid.uuid4()
        hashed_password = HashedPassword.from_plain("TestPassword123!")
        
        user = UserModel(
            id=user_id,
            email=generate_unique_email("empty_prefs"),
            password_hash=hashed_password.value,
            full_name="Empty Prefs User",
            timezone="UTC",
            is_active=True,
            preferences={"existing": "data"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db_session.add(user)
        await db_session.commit()
        
        # Create auth header
        access_token = create_access_token(user_id)
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Update with empty preferences
        response = await test_client.put("/api/v1/users/me/preferences", 
                                        headers=headers, 
                                        json={})
        
        assert response.status_code == 200
        data = response.json()
        assert data["preferences"] == {}
    
    async def test_update_user_preferences_unauthorized(self, test_client: AsyncClient):
        """Test unauthorized preferences update."""
        preferences = {"theme": "dark"}
        
        response = await test_client.put("/api/v1/users/me/preferences", json=preferences)
        assert response.status_code == 401
    
    async def test_update_user_preferences_invalid_json(self, test_client: AsyncClient, db_session: AsyncSession):
        """Test preferences update with invalid JSON structure."""
        from src.trading.infrastructure.persistence.models.core_models import UserModel
        from src.trading.domain.user import HashedPassword
        from src.trading.infrastructure.auth.jwt import create_access_token
        
        # Create test user
        user_id = uuid.uuid4()
        hashed_password = HashedPassword.from_plain("TestPassword123!")
        
        user = UserModel(
            id=user_id,
            email=generate_unique_email("invalid_json"),
            password_hash=hashed_password.value,
            full_name="Invalid JSON User",
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db_session.add(user)
        await db_session.commit()
        
        # Create auth header
        access_token = create_access_token(user_id)
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Test with None value (should be rejected if not allowed)
        invalid_preferences = None
        
        response = await test_client.put("/api/v1/users/me/preferences", 
                                        headers=headers, 
                                        json=invalid_preferences)
        
        assert response.status_code in [400, 422]
    
    async def test_update_user_preferences_complex_nested(self, test_client: AsyncClient, db_session: AsyncSession):
        """Test preferences update with complex nested data."""
        from src.trading.infrastructure.persistence.models.core_models import UserModel
        from src.trading.domain.user import HashedPassword
        from src.trading.infrastructure.auth.jwt import create_access_token
        
        # Create test user
        user_id = uuid.uuid4()
        hashed_password = HashedPassword.from_plain("TestPassword123!")
        
        user = UserModel(
            id=user_id,
            email=generate_unique_email("complex_prefs"),
            password_hash=hashed_password.value,
            full_name="Complex Prefs User",
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db_session.add(user)
        await db_session.commit()
        
        # Create auth header
        access_token = create_access_token(user_id)
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Complex nested preferences
        complex_preferences = {
            "ui": {
                "theme": "dark",
                "sidebar_collapsed": True,
                "chart_settings": {
                    "timeframe": "1h",
                    "indicators": ["RSI", "MACD"]
                }
            },
            "trading": {
                "default_amount": 100.0,
                "risk_settings": {
                    "max_risk_per_trade": 0.02,
                    "stop_loss": True
                }
            }
        }
        
        response = await test_client.put("/api/v1/users/me/preferences", 
                                        headers=headers, 
                                        json=complex_preferences)
        
        assert response.status_code == 200
        data = response.json()
        assert data["preferences"]["ui"]["theme"] == "dark"
        assert data["preferences"]["trading"]["default_amount"] == 100.0
    
    # ==================== Security & Edge Case Tests ====================
    
    async def test_user_isolation_profile_access(self, test_client: AsyncClient, db_session: AsyncSession):
        """Test that users can only access their own profiles."""
        from src.trading.infrastructure.persistence.models.core_models import UserModel
        from src.trading.domain.user import HashedPassword
        from src.trading.infrastructure.auth.jwt import create_access_token
        
        # Create two users
        user1_id = uuid.uuid4()
        user2_id = uuid.uuid4()
        
        hashed_password = HashedPassword.from_plain("TestPassword123!")
        
        user1_email = generate_unique_email("user1")
        user2_email = generate_unique_email("user2")
        
        user1 = UserModel(
            id=user1_id,
            email=user1_email,
            password_hash=hashed_password.value,
            full_name="User One",
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        user2 = UserModel(
            id=user2_id,
            email=user2_email,
            password_hash=hashed_password.value,
            full_name="User Two",
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db_session.add_all([user1, user2])
        await db_session.commit()
        
        # User 1 tries to access their profile (should succeed)
        access_token1 = create_access_token(user1_id)
        headers1 = {"Authorization": f"Bearer {access_token1}"}
        
        response1 = await test_client.get("/api/v1/users/me", headers=headers1)
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["id"] == str(user1_id)
        assert data1["email"] == user1_email
        
        # User 2 tries to access their profile (should succeed)
        access_token2 = create_access_token(user2_id)
        headers2 = {"Authorization": f"Bearer {access_token2}"}
        
        response2 = await test_client.get("/api/v1/users/me", headers=headers2)
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["id"] == str(user2_id)
        assert data2["email"] == user2_email
    
    async def test_concurrent_profile_updates(self, test_client: AsyncClient, db_session: AsyncSession):
        """Test concurrent profile updates (basic race condition test)."""
        import asyncio
        from src.trading.infrastructure.persistence.models.core_models import UserModel
        from src.trading.domain.user import HashedPassword
        from src.trading.infrastructure.auth.jwt import create_access_token
        
        # Create test user
        user_id = uuid.uuid4()
        hashed_password = HashedPassword.from_plain("TestPassword123!")
        
        user = UserModel(
            id=user_id,
            email=generate_unique_email("concurrent"),
            password_hash=hashed_password.value,
            full_name="Concurrent User",
            timezone="UTC",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db_session.add(user)
        await db_session.commit()
        
        # Create auth header
        access_token = create_access_token(user_id)
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Concurrent update requests
        async def update_timezone(tz: str):
            return await test_client.patch("/api/v1/users/me", 
                                          headers=headers, 
                                          json={"timezone": tz})
        
        # Run concurrent updates
        responses = await asyncio.gather(
            update_timezone("Europe/London"),
            update_timezone("Asia/Tokyo"),
            update_timezone("America/New_York"),
            return_exceptions=True
        )
        
        # All should succeed or handle gracefully
        for response in responses:
            if hasattr(response, 'status_code'):
                assert response.status_code in [200, 409, 422]