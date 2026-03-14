"""Tests for /api/v1/auth/* endpoints."""
import uuid
import pytest
from httpx import AsyncClient


REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
LOGOUT_URL = "/api/v1/auth/logout"
CHANGE_PW_URL = "/api/v1/auth/change-password"


def unique_email() -> str:
    return f"user_{uuid.uuid4().hex[:8]}@example.com"


# ── Register ──────────────────────────────────────────────────────────────────

class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        resp = await client.post(
            REGISTER_URL,
            json={"email": unique_email(), "password": "SecurePass1!", "full_name": "Alice"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] is not None
        assert "hashed_password" not in data
        assert data["full_name"] == "Alice"
        assert data["is_active"] is True

    async def test_register_auto_creates_agent(self, client: AsyncClient):
        """Registering should provision a private agent (tested via /agent/me)."""
        email = unique_email()
        await client.post(REGISTER_URL, json={"email": email, "password": "Pass123!"})
        login = await client.post(LOGIN_URL, json={"email": email, "password": "Pass123!"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        agent_resp = await client.get("/api/v1/agent/me", headers=headers)
        assert agent_resp.status_code == 200
        assert agent_resp.json()["id"] is not None

    async def test_register_duplicate_email(self, client: AsyncClient):
        email = unique_email()
        await client.post(REGISTER_URL, json={"email": email, "password": "Pass123!"})
        resp = await client.post(REGISTER_URL, json={"email": email, "password": "Other1!"})
        assert resp.status_code == 409
        assert "already registered" in resp.json()["detail"].lower()

    async def test_register_without_full_name(self, client: AsyncClient):
        resp = await client.post(
            REGISTER_URL, json={"email": unique_email(), "password": "Pass123!"}
        )
        assert resp.status_code == 201
        assert resp.json()["full_name"] is None

    async def test_register_invalid_email(self, client: AsyncClient):
        resp = await client.post(
            REGISTER_URL, json={"email": "not-an-email", "password": "Pass123!"}
        )
        assert resp.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────

class TestLogin:
    async def test_login_success(self, client: AsyncClient):
        email = unique_email()
        await client.post(REGISTER_URL, json={"email": email, "password": "Pass123!"})

        resp = await client.post(LOGIN_URL, json={"email": email, "password": "Pass123!"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient):
        email = unique_email()
        await client.post(REGISTER_URL, json={"email": email, "password": "Pass123!"})

        resp = await client.post(LOGIN_URL, json={"email": email, "password": "WrongPass!"})
        assert resp.status_code == 401

    async def test_login_unknown_email(self, client: AsyncClient):
        resp = await client.post(
            LOGIN_URL, json={"email": "nobody@example.com", "password": "Pass123!"}
        )
        assert resp.status_code == 401

    async def test_login_returns_valid_jwt(self, client: AsyncClient):
        email = unique_email()
        await client.post(REGISTER_URL, json={"email": email, "password": "Pass123!"})
        login = await client.post(LOGIN_URL, json={"email": email, "password": "Pass123!"})

        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        me = await client.get("/api/v1/users/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["email"] == email


# ── Token Refresh ─────────────────────────────────────────────────────────────

class TestRefresh:
    async def test_refresh_success(self, client: AsyncClient):
        email = unique_email()
        await client.post(REGISTER_URL, json={"email": email, "password": "Pass123!"})
        login = await client.post(LOGIN_URL, json={"email": email, "password": "Pass123!"})
        refresh_token = login.json()["refresh_token"]

        resp = await client.post(REFRESH_URL, json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # New refresh token should differ from old
        assert data["refresh_token"] != refresh_token

    async def test_refresh_token_rotates(self, client: AsyncClient):
        """Used refresh token should be invalidated (one-time use)."""
        email = unique_email()
        await client.post(REGISTER_URL, json={"email": email, "password": "Pass123!"})
        login = await client.post(LOGIN_URL, json={"email": email, "password": "Pass123!"})
        old_refresh = login.json()["refresh_token"]

        await client.post(REFRESH_URL, json={"refresh_token": old_refresh})

        # Second use of same token should fail
        resp = await client.post(REFRESH_URL, json={"refresh_token": old_refresh})
        assert resp.status_code == 401

    async def test_refresh_invalid_token(self, client: AsyncClient):
        resp = await client.post(REFRESH_URL, json={"refresh_token": "totally-fake-token"})
        assert resp.status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────────

class TestLogout:
    async def test_logout_revokes_refresh_token(self, client: AsyncClient):
        email = unique_email()
        await client.post(REGISTER_URL, json={"email": email, "password": "Pass123!"})
        login = await client.post(LOGIN_URL, json={"email": email, "password": "Pass123!"})
        refresh_token = login.json()["refresh_token"]

        resp = await client.post(LOGOUT_URL, json={"refresh_token": refresh_token})
        assert resp.status_code == 204

        # Refresh should now fail
        resp = await client.post(REFRESH_URL, json={"refresh_token": refresh_token})
        assert resp.status_code == 401

    async def test_logout_with_invalid_token_is_silent(self, client: AsyncClient):
        """Logout with unknown token should not error."""
        resp = await client.post(LOGOUT_URL, json={"refresh_token": "unknown-token"})
        assert resp.status_code == 204


# ── Change Password ───────────────────────────────────────────────────────────

class TestChangePassword:
    async def test_change_password_success(self, client: AsyncClient, auth_headers):
        headers, email, refresh_token = auth_headers

        resp = await client.post(
            CHANGE_PW_URL,
            json={"current_password": "TestPass123!", "new_password": "NewPass456!"},
            headers=headers,
        )
        assert resp.status_code == 204

        # Old password should now fail
        bad_login = await client.post(
            LOGIN_URL, json={"email": email, "password": "TestPass123!"}
        )
        assert bad_login.status_code == 401

        # New password should work
        new_login = await client.post(
            LOGIN_URL, json={"email": email, "password": "NewPass456!"}
        )
        assert new_login.status_code == 200

    async def test_change_password_wrong_current(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        resp = await client.post(
            CHANGE_PW_URL,
            json={"current_password": "WrongCurrentPass!", "new_password": "NewPass456!"},
            headers=headers,
        )
        assert resp.status_code == 401

    async def test_change_password_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            CHANGE_PW_URL,
            json={"current_password": "any", "new_password": "any"},
        )
        assert resp.status_code == 403

    async def test_change_password_revokes_all_refresh_tokens(
        self, client: AsyncClient, auth_headers
    ):
        headers, email, refresh_token = auth_headers

        await client.post(
            CHANGE_PW_URL,
            json={"current_password": "TestPass123!", "new_password": "NewPass456!"},
            headers=headers,
        )

        # Old refresh token should be invalid
        resp = await client.post(REFRESH_URL, json={"refresh_token": refresh_token})
        assert resp.status_code == 401
