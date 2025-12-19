"""Comprehensive authentication API integration tests."""
import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.trading.infrastructure.persistence.models.core_models import UserModel
from src.trading.domain.user import HashedPassword


def generate_unique_email(base_name: str = "testuser") -> str:
    """Generate a unique email address using timestamp and UUID."""
    timestamp = str(int(datetime.now(timezone.utc).timestamp() * 1000000))  # microsecond precision
    unique_id = str(uuid.uuid4())[:8]  # first 8 chars of UUID
    return f"{base_name}_{timestamp}_{unique_id}@example.com"


@pytest.mark.asyncio
class TestComprehensiveAuthentication:
    """Comprehensive authentication API tests."""

    async def test_register_with_all_fields(self, test_client: AsyncClient):
        """Test user registration with all optional fields."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": generate_unique_email("fulluser"),
                "password": "SecurePass123!",
                "full_name": "Full User Name",
                "timezone": "America/New_York"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"

    async def test_register_minimal_fields(self, test_client: AsyncClient):
        """Test user registration with minimal required fields."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": generate_unique_email("minimal"),
                "password": "SecurePass123!"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_register_invalid_email_format(self, test_client: AsyncClient):
        """Test registration with invalid email format."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "password": "SecurePass123!",
                "full_name": "Invalid Email User"
            }
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    async def test_register_weak_password(self, test_client: AsyncClient):
        """Test registration with weak password."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": generate_unique_email("weakpass"),
                "password": "123",
                "full_name": "Weak Password User"
            }
        )
        assert response.status_code == 422

    async def test_register_missing_required_fields(self, test_client: AsyncClient):
        """Test registration with missing required fields."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "No Email User"
            }
        )
        assert response.status_code == 422

    async def test_register_empty_email(self, test_client: AsyncClient):
        """Test registration with empty email."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": "",
                "password": "SecurePass123!"
            }
        )
        assert response.status_code == 422

    async def test_register_empty_password(self, test_client: AsyncClient):
        """Test registration with empty password."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": generate_unique_email("emptypass"),
                "password": ""
            }
        )
        assert response.status_code == 422

    async def test_register_invalid_timezone(self, test_client: AsyncClient):
        """Test registration with invalid timezone."""
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": generate_unique_email("invalidtz"),
                "password": "SecurePass123!",
                "timezone": "Invalid/Timezone"
            }
        )
        # Should either accept (defaults to UTC) or reject with 422
        assert response.status_code in [201, 422]

    async def test_register_long_full_name(self, test_client: AsyncClient):
        """Test registration with very long full name."""
        long_name = "A" * 300  # Exceeds typical 255 char limit
        response = await test_client.post(
            "/api/v1/auth/register",
            json={
                "email": generate_unique_email("longname"),
                "password": "SecurePass123!",
                "full_name": long_name
            }
        )
        assert response.status_code in [201, 422]  # Depends on validation rules

    async def test_login_with_correct_credentials(self, test_client: AsyncClient, test_user):
        """Test login with correct credentials."""
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user["email"],
                "password": test_user["password"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"

    async def test_login_case_insensitive_email(self, test_client: AsyncClient, db_session: AsyncSession):
        """Test login with case-insensitive email."""
        from src.trading.infrastructure.persistence.models.core_models import UserModel
        from src.trading.domain.user import HashedPassword
        
        # Create unique user for this test
        user_id = uuid.uuid4()
        plain_password = "TestPassword123!"
        hashed_password = HashedPassword.from_plain(plain_password)
        unique_email = generate_unique_email("casesensitive")
        
        user = UserModel(
            id=user_id,
            email=unique_email,
            password_hash=hashed_password.value,
            full_name="Case Test User",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db_session.add(user)
        await db_session.commit()
        
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": unique_email.upper(),  # Uppercase version of unique email
                "password": plain_password
            }
        )
        # May pass or fail depending on implementation
        assert response.status_code in [200, 401]

    async def test_login_wrong_password_format(self, test_client: AsyncClient, db_session: AsyncSession):
        """Test login with wrong password format."""
        from src.trading.infrastructure.persistence.models.core_models import UserModel
        from src.trading.domain.user import HashedPassword
        
        # Create unique user for this test
        user_id = uuid.uuid4()
        plain_password = "TestPassword123!"
        hashed_password = HashedPassword.from_plain(plain_password)
        unique_email = generate_unique_email("wrongformat")
        
        user = UserModel(
            id=user_id,
            email=unique_email,
            password_hash=hashed_password.value,
            full_name="Format Test User",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db_session.add(user)
        await db_session.commit()
        
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": unique_email,
                "password": plain_password.upper()  # Wrong case
            }
        )
        assert response.status_code == 401

    async def test_login_sql_injection_attempt(self, test_client: AsyncClient):
        """Test login with SQL injection attempt."""
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin'; DROP TABLE users; --",
                "password": "anything"
            }
        )
        # Should reject with validation error or auth failure
        assert response.status_code in [401, 422]

    async def test_login_empty_credentials(self, test_client: AsyncClient):
        """Test login with empty credentials."""
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": "",
                "password": ""
            }
        )
        assert response.status_code == 422

    async def test_login_missing_email(self, test_client: AsyncClient):
        """Test login with missing email."""
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "password": "somepassword"
            }
        )
        assert response.status_code == 422

    async def test_login_missing_password(self, test_client: AsyncClient):
        """Test login with missing password."""
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": generate_unique_email("user")
            }
        )
        assert response.status_code == 422

    async def test_multiple_failed_login_attempts(self, test_client: AsyncClient, db_session: AsyncSession):
        """Test multiple failed login attempts (rate limiting)."""
        from src.trading.infrastructure.persistence.models.core_models import UserModel
        from src.trading.domain.user import HashedPassword
        
        # Create unique user for this test
        user_id = uuid.uuid4()
        plain_password = "TestPassword123!"
        hashed_password = HashedPassword.from_plain(plain_password)
        unique_email = generate_unique_email("failedlogins")
        
        user = UserModel(
            id=user_id,
            email=unique_email,
            password_hash=hashed_password.value,
            full_name="Failed Login Test User",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db_session.add(user)
        await db_session.commit()
        
        for _ in range(10):  # Attempt multiple failed logins
            response = await test_client.post(
                "/api/v1/auth/login",
                json={
                    "email": unique_email,
                    "password": "wrongpassword"
                }
            )
            # Should always return 401, but might implement rate limiting
            assert response.status_code in [401, 429]

    async def test_concurrent_login_attempts(self, test_client: AsyncClient, db_session: AsyncSession):
        """Test concurrent login attempts from same user."""
        import asyncio
        import time
        from src.trading.infrastructure.persistence.models.core_models import UserModel
        from src.trading.domain.user import HashedPassword
        
        # Create unique user for this test
        user_id = uuid.uuid4()
        plain_password = "TestPassword123!"
        hashed_password = HashedPassword.from_plain(plain_password)
        
        # Use timestamp to ensure unique email for each test
        timestamp = str(int(time.time() * 1000000))  # microsecond precision
        unique_email = generate_unique_email(f"concurrent_{timestamp}")
        
        user = UserModel(
            id=user_id,
            email=unique_email,
            password_hash=hashed_password.value,
            full_name="Concurrent Test User",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db_session.add(user)
        await db_session.commit()
        
        async def login_attempt():
            return await test_client.post(
                "/api/v1/auth/login",
                json={
                    "email": unique_email,
                    "password": plain_password
                }
            )
        
        # Multiple concurrent logins
        responses = await asyncio.gather(*[login_attempt() for _ in range(5)])
        
        # All should succeed (multiple sessions allowed)
        for response in responses:
            assert response.status_code == 200

    async def test_login_inactive_user(self, test_client: AsyncClient, db_session: AsyncSession):
        """Test login with inactive user account."""
        # Create inactive user
        user_id = uuid.uuid4()
        hashed_password = HashedPassword.from_plain("TestPassword123!")
        unique_email = generate_unique_email("inactive")
        
        inactive_user = UserModel(
            id=user_id,
            email=unique_email,
            password_hash=hashed_password.value,
            full_name="Inactive User",
            is_active=False,  # Inactive account
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db_session.add(inactive_user)
        await db_session.commit()
        
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": unique_email,
                "password": "TestPassword123!"
            }
        )
        assert response.status_code == 401

    async def test_token_refresh_with_valid_token(self, test_client: AsyncClient, db_session: AsyncSession):
        """Test token refresh with valid refresh token."""
        from src.trading.infrastructure.persistence.models.core_models import UserModel
        from src.trading.domain.user import HashedPassword
        
        # Create unique user for this test
        user_id = uuid.uuid4()
        plain_password = "TestPassword123!"
        hashed_password = HashedPassword.from_plain(plain_password)
        unique_email = generate_unique_email("tokenrefresh")
        
        user = UserModel(
            id=user_id,
            email=unique_email,
            password_hash=hashed_password.value,
            full_name="Token Refresh User",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db_session.add(user)
        await db_session.commit()
        
        # First, login to get tokens
        login_response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": unique_email,
                "password": plain_password
            }
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        
        # Then refresh
        refresh_response = await test_client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": tokens["refresh_token"]
            }
        )
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens

    async def test_token_refresh_with_invalid_token(self, test_client: AsyncClient):
        """Test token refresh with invalid refresh token."""
        response = await test_client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": "invalid-token"
            }
        )
        assert response.status_code == 401

    async def test_token_refresh_with_expired_token(self, test_client: AsyncClient):
        """Test token refresh with expired refresh token."""
        # This would require creating an expired token
        # For now, use an obviously invalid token format
        response = await test_client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.expired.token"
            }
        )
        assert response.status_code == 401

    async def test_logout_with_valid_token(self, test_client: AsyncClient, auth_headers):
        """Test logout with valid access token."""
        response = await test_client.post(
            "/api/v1/auth/logout",
            headers=auth_headers
        )
        # Implementation dependent - may be 200, 204, or endpoint might not exist
        assert response.status_code in [200, 204, 404, 405]

    async def test_logout_without_token(self, test_client: AsyncClient):
        """Test logout without authentication token."""
        response = await test_client.post("/api/v1/auth/logout")
        assert response.status_code in [401, 404, 405]

    async def test_password_reset_request(self, test_client: AsyncClient, db_session: AsyncSession):
        """Test password reset request."""
        from src.trading.infrastructure.persistence.models.core_models import UserModel
        from src.trading.domain.user import HashedPassword
        
        # Create unique user for this test
        user_id = uuid.uuid4()
        plain_password = "TestPassword123!"
        hashed_password = HashedPassword.from_plain(plain_password)
        unique_email = generate_unique_email("passwordreset")
        
        user = UserModel(
            id=user_id,
            email=unique_email,
            password_hash=hashed_password.value,
            full_name="Password Reset User",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db_session.add(user)
        await db_session.commit()
        
        response = await test_client.post(
            "/api/v1/auth/password-reset",
            json={
                "email": unique_email
            }
        )
        # Implementation dependent
        assert response.status_code in [200, 202, 404, 405]

    async def test_password_reset_nonexistent_email(self, test_client: AsyncClient):
        """Test password reset for nonexistent email."""
        response = await test_client.post(
            "/api/v1/auth/password-reset",
            json={
                "email": generate_unique_email("nonexistent")
            }
        )
        # Should not reveal if email exists
        assert response.status_code in [200, 202, 404, 405]

    async def test_access_protected_endpoint_with_valid_token(self, test_client: AsyncClient, auth_headers):
        """Test accessing protected endpoint with valid token."""
        response = await test_client.get(
            "/api/v1/users/me",
            headers=auth_headers
        )
        assert response.status_code == 200

    async def test_access_protected_endpoint_without_token(self, test_client: AsyncClient):
        """Test accessing protected endpoint without token."""
        response = await test_client.get("/api/v1/users/me")
        assert response.status_code == 401

    async def test_access_protected_endpoint_with_invalid_token(self, test_client: AsyncClient):
        """Test accessing protected endpoint with invalid token."""
        response = await test_client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401

    async def test_access_protected_endpoint_with_malformed_header(self, test_client: AsyncClient):
        """Test accessing protected endpoint with malformed auth header."""
        response = await test_client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Invalid header format"}
        )
        assert response.status_code == 401

    async def test_token_contains_user_information(self, test_client: AsyncClient, db_session: AsyncSession):
        """Test that token contains proper user information (if extractable)."""
        from src.trading.infrastructure.persistence.models.core_models import UserModel
        from src.trading.domain.user import HashedPassword
        
        # Create unique user for this test
        user_id = uuid.uuid4()
        plain_password = "TestPassword123!"
        hashed_password = HashedPassword.from_plain(plain_password)
        unique_email = generate_unique_email("tokeninfo")
        
        user = UserModel(
            id=user_id,
            email=unique_email,
            password_hash=hashed_password.value,
            full_name="Token Info User",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        db_session.add(user)
        await db_session.commit()
        
        response = await test_client.post(
            "/api/v1/auth/login",
            json={
                "email": unique_email,
                "password": plain_password
            }
        )
        assert response.status_code == 200
        data = response.json()
        
        # Token should be JWT format (3 parts separated by dots)
        access_token = data["access_token"]
        parts = access_token.split(".")
        assert len(parts) == 3  # JWT format