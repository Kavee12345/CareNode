"""Tests for /api/v1/users/* endpoints."""
import pytest
from httpx import AsyncClient


ME_URL = "/api/v1/users/me"


class TestGetMe:
    async def test_get_me_success(self, client: AsyncClient, auth_headers):
        headers, email, _ = auth_headers
        resp = await client.get(ME_URL, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == email
        assert data["is_active"] is True
        assert "hashed_password" not in data
        assert "id" in data
        assert "created_at" in data

    async def test_get_me_unauthenticated(self, client: AsyncClient):
        resp = await client.get(ME_URL)
        assert resp.status_code == 403

    async def test_get_me_invalid_token(self, client: AsyncClient):
        resp = await client.get(ME_URL, headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401


class TestUpdateMe:
    async def test_update_full_name(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers
        resp = await client.patch(ME_URL, json={"full_name": "Updated Name"}, headers=headers)

        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Updated Name"

    async def test_update_gender(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers
        resp = await client.patch(ME_URL, json={"gender": "female"}, headers=headers)

        assert resp.status_code == 200
        assert resp.json()["gender"] == "female"

    async def test_update_date_of_birth(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers
        resp = await client.patch(ME_URL, json={"date_of_birth": "1990-05-15"}, headers=headers)

        assert resp.status_code == 200
        assert resp.json()["date_of_birth"] == "1990-05-15"

    async def test_update_multiple_fields(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers
        resp = await client.patch(
            ME_URL,
            json={"full_name": "John Doe", "gender": "male", "date_of_birth": "1985-03-20"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["full_name"] == "John Doe"
        assert data["gender"] == "male"
        assert data["date_of_birth"] == "1985-03-20"

    async def test_update_partial_fields(self, client: AsyncClient, auth_headers):
        """Empty body should not change anything."""
        headers, email, _ = auth_headers
        resp = await client.patch(ME_URL, json={}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == email

    async def test_update_me_unauthenticated(self, client: AsyncClient):
        resp = await client.patch(ME_URL, json={"full_name": "Hacker"})
        assert resp.status_code == 403


class TestDeleteMe:
    async def test_delete_me_success(self, client: AsyncClient, auth_headers):
        headers, email, _ = auth_headers
        resp = await client.delete(ME_URL, headers=headers)
        assert resp.status_code == 204

        # Token should no longer work
        resp2 = await client.get(ME_URL, headers=headers)
        assert resp2.status_code == 401

    async def test_delete_me_unauthenticated(self, client: AsyncClient):
        resp = await client.delete(ME_URL)
        assert resp.status_code == 403
