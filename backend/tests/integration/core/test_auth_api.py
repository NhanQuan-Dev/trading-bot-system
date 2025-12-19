"""Integration tests for Authentication API endpoints."""

import pytest
from httpx import AsyncClient
from datetime import datetime, UTC


class TestAuthAPI:
    """Test authentication API endpoints."""
    
    @pytest.mark.asyncio
    async def test_register_user_success(self, test_client: AsyncClient):
        """Test successful user registration."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123",
                "full_name": "New User",
                "timezone": "UTC"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, test_client: AsyncClient, test_user):
        """Test registration with duplicate email fails."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,  # Duplicate
                "password": "SecurePass123",
                "full_name": "Duplicate User"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "email" in data["detail"].lower() or "already" in data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_register_invalid_email(self, test_client: AsyncClient):
        """Test registration with invalid email format."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123",
                "full_name": "Test User"
            }
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_short_password(self, test_client: AsyncClient):
        """Test registration with password too short."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "short",
                "full_name": "Test User"
            }
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_login_success(self, test_client: AsyncClient, test_user):
        """Test successful user login."""
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPassword123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
    
    @pytest.mark.asyncio
    async def test_login_invalid_email(self, test_client: AsyncClient):
        """Test login with non-existent email."""
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "TestPassword123"
            }
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_login_invalid_password(self, test_client: AsyncClient, test_user):
        """Test login with incorrect password."""
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "WrongPassword"
            }
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_login_inactive_user(self, test_client: AsyncClient, db_session):
        """Test login with inactive user account."""
        from src.trading.infrastructure.persistence.models.core_models import UserModel
        from src.trading.domain.user import HashedPassword
        from uuid import uuid4
        
        # Create inactive user with unique email to avoid constraint conflicts
        inactive_email = f"inactive_{uuid4().hex}@example.com"
        inactive_user = UserModel(
            id=uuid4(),
            email=inactive_email,
            password_hash=HashedPassword.from_plain("TestPassword123").value,
            full_name="Inactive User",
            timezone="UTC",
            is_active=False,
            created_at=datetime.now(UTC),
        )
        db_session.add(inactive_user)
        await db_session.commit()
        
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": inactive_email,
                "password": "TestPassword123"
            }
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, test_client: AsyncClient, test_user):
        """Test refreshing access token with valid refresh token."""
        # First login to get refresh token
        login_response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "TestPassword123"
            }
        )
        
        refresh_token = login_response.json()["refresh_token"]
        
        # Use refresh token to get new access token
        response = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, test_client: AsyncClient):
        """Test refresh with invalid token."""
        response = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_refresh_token_expired(self, test_client: AsyncClient):
        """Test refresh with expired token."""
        # This would require generating an expired token
        # For now, we'll use an invalid token format
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjB9.invalid"
        
        response = await test_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": expired_token}
        )
        
        assert response.status_code == 401
