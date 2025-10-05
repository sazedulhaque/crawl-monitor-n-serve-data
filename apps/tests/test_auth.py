"""
Tests for authentication endpoints
"""

import pytest
from fastapi import status


@pytest.mark.asyncio
class TestUserRegistration:
    """Test user registration endpoint"""

    async def test_register_new_user_success(self, test_client):
        """Test successful user registration"""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "securepass123",
            "full_name": "New User",
        }

        response = await test_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert data["full_name"] == user_data["full_name"]
        assert data["is_active"] is True
        assert data["is_admin"] is False
        # These fields should be excluded from response
        assert "password" not in data
        assert "created_at" not in data
        assert "updated_at" not in data
        assert "id" not in data

    async def test_register_duplicate_username(self, test_client, test_user):
        """Test registration with duplicate username"""
        user_data = {
            "email": "another@example.com",
            "username": "testuser",  # Already exists
            "password": "password123",
        }

        response = await test_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()

    async def test_register_duplicate_email(self, test_client, test_user):
        """Test registration with duplicate email"""
        user_data = {
            "email": "testuser@example.com",  # Already exists
            "username": "differentuser",
            "password": "password123",
        }

        response = await test_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()

    async def test_register_invalid_email(self, test_client):
        """Test registration with invalid email"""
        user_data = {
            "email": "invalid-email",
            "username": "newuser",
            "password": "password123",
        }

        response = await test_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_register_short_password(self, test_client):
        """Test registration with short password"""
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "123",  # Too short
        }

        response = await test_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
class TestUserLogin:
    """Test user login endpoints"""

    async def test_login_success(self, test_client, test_user):
        """Test successful login"""
        response = await test_client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "testpassword123"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data

    async def test_token_endpoint_success(self, test_client, test_user):
        """Test token endpoint (OAuth2 compatible)"""
        response = await test_client.post(
            "/api/v1/auth/token",
            data={"username": "testuser", "password": "testpassword123"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, test_client, test_user):
        """Test login with wrong password"""
        response = await test_client.post(
            "/api/v1/auth/login",
            data={"username": "testuser", "password": "wrongpassword"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_login_nonexistent_user(self, test_client):
        """Test login with nonexistent user"""
        response = await test_client.post(
            "/api/v1/auth/login",
            data={"username": "nonexistent", "password": "password123"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_login_missing_credentials(self, test_client):
        """Test login with missing credentials"""
        response = await test_client.post("/api/v1/auth/login", data={})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
class TestProtectedEndpoints:
    """Test protected endpoints"""

    async def test_get_current_user(self, test_client, auth_token):
        """Test getting current user with valid token"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await test_client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "testuser@example.com"
        assert data["is_active"] is True
        # These fields should be excluded from response
        assert "password" not in data
        assert "created_at" not in data
        assert "updated_at" not in data
        assert "id" not in data

    async def test_get_current_user_no_token(self, test_client):
        """Test getting current user without token"""
        response = await test_client.get("/api/v1/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_get_current_user_invalid_token(self, test_client):
        """Test getting current user with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = await test_client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestAdminEndpoints:
    """Test admin-only endpoints"""

    async def test_admin_user_login(self, test_client, admin_user):
        """Test admin user can login"""
        response = await test_client.post(
            "/api/v1/auth/token",
            data={"username": "adminuser", "password": "adminpassword123"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data

    async def test_admin_user_info(self, test_client, admin_token):
        """Test admin user info"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await test_client.get("/api/v1/auth/me", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "adminuser"
        assert data["is_admin"] is True
        assert data["is_active"] is True
        # These fields should be excluded from response
        assert "password" not in data
        assert "created_at" not in data
        assert "updated_at" not in data
        assert "id" not in data
