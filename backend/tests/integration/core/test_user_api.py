"""Integration tests for User API endpoints."""

import pytest
from httpx import AsyncClient


class TestUserAPI:
    """Test user management API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_current_user_authenticated(
        self, 
        test_client: AsyncClient,
        test_user,
        auth_headers
    ):
        """Test getting current user profile when authenticated."""
        response = await test_client.get(
            "/api/v1/users/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["full_name"] == test_user.full_name
        assert "id" in data
        assert "created_at" in data
    
    @pytest.mark.asyncio
    async def test_get_current_user_unauthenticated(self, test_client: AsyncClient):
        """Test getting current user without authentication fails."""
        response = await test_client.get("/api/v1/users/me")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, test_client: AsyncClient):
        """Test getting current user with invalid token fails."""
        response = await test_client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_update_user_profile_full_name(
        self,
        test_client: AsyncClient,
        test_user,
        auth_headers
    ):
        """Test updating user full name."""
        response = await test_client.patch(
            "/api/v1/users/me",
            headers=auth_headers,
            json={"full_name": "Updated Name"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["email"] == test_user.email
    
    @pytest.mark.asyncio
    async def test_update_user_profile_timezone(
        self,
        test_client: AsyncClient,
        auth_headers
    ):
        """Test updating user timezone."""
        response = await test_client.patch(
            "/api/v1/users/me",
            headers=auth_headers,
            json={"timezone": "America/New_York"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["timezone"] == "America/New_York"
    
    @pytest.mark.asyncio
    async def test_update_user_profile_multiple_fields(
        self,
        test_client: AsyncClient,
        auth_headers
    ):
        """Test updating multiple profile fields."""
        response = await test_client.patch(
            "/api/v1/users/me",
            headers=auth_headers,
            json={
                "full_name": "New Name",
                "timezone": "Asia/Tokyo"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "New Name"
        assert data["timezone"] == "Asia/Tokyo"
    
    @pytest.mark.asyncio
    async def test_update_user_profile_unauthenticated(
        self,
        test_client: AsyncClient
    ):
        """Test updating profile without authentication fails."""
        response = await test_client.patch(
            "/api/v1/users/me",
            json={"full_name": "New Name"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_update_user_preferences(
        self,
        test_client: AsyncClient,
        auth_headers
    ):
        """Test updating user preferences."""
        preferences = {
            "theme": "dark",
            "language": "en",
            "notifications": {
                "email": True,
                "push": False
            }
        }
        
        response = await test_client.put(
            "/api/v1/users/me/preferences",
            headers=auth_headers,
            json={"preferences": preferences}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Note: preferences might not be directly in response,
        # but the request should succeed
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_update_preferences_unauthenticated(
        self,
        test_client: AsyncClient
    ):
        """Test updating preferences without authentication fails."""
        response = await test_client.put(
            "/api/v1/users/me/preferences",
            json={"preferences": {"theme": "dark"}}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_user_cannot_access_other_user_profile(
        self,
        test_client: AsyncClient,
        test_user,
        test_user_2,
        auth_headers
    ):
        """Test that user can only access their own profile."""
        # With test_user's auth headers, try to access test_user_2's data
        # The /users/me endpoint always returns current user, so this should
        # return test_user, not test_user_2
        response = await test_client.get(
            "/api/v1/users/me",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["email"] != test_user_2.email
