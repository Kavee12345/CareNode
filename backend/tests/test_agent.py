"""Tests for /api/v1/agent/* endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

AGENT_URL = "/api/v1/agent/me"


class TestGetAgent:
    async def test_get_agent_success(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        resp = await client.get(AGENT_URL, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "name" in data
        assert "created_at" in data

    async def test_get_agent_auto_created_on_register(self, client: AsyncClient):
        """Each new user should have an agent automatically provisioned."""
        import uuid

        email = f"new_{uuid.uuid4().hex[:8]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "Pass123!"},
        )
        login = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "Pass123!"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        resp = await client.get(AGENT_URL, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] is not None

    async def test_get_agent_requires_auth(self, client: AsyncClient):
        resp = await client.get(AGENT_URL)
        assert resp.status_code == 403


class TestUpdateAgent:
    async def test_update_agent_name(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        resp = await client.patch(AGENT_URL, json={"name": "Dr. Alex"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Dr. Alex"

    async def test_update_agent_system_prompt(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        custom_prompt = (
            "You are a concise medical assistant. Keep answers under 3 sentences."
        )
        resp = await client.patch(
            AGENT_URL, json={"system_prompt_override": custom_prompt}, headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["system_prompt_override"] == custom_prompt

    async def test_update_agent_partial(self, client: AsyncClient, auth_headers):
        """Updating only name should not clear system_prompt_override."""
        headers, _, __ = auth_headers

        # First set both fields
        await client.patch(
            AGENT_URL,
            json={"name": "Initial", "system_prompt_override": "Custom prompt"},
            headers=headers,
        )

        # Then update only the name
        resp = await client.patch(AGENT_URL, json={"name": "Updated"}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Updated"
        assert data["system_prompt_override"] == "Custom prompt"

    async def test_update_agent_clear_prompt_override(
        self, client: AsyncClient, auth_headers
    ):
        headers, _, __ = auth_headers

        await client.patch(
            AGENT_URL,
            json={"system_prompt_override": "Some override"},
            headers=headers,
        )

        resp = await client.patch(
            AGENT_URL, json={"system_prompt_override": None}, headers=headers
        )
        assert resp.status_code == 200
        assert resp.json()["system_prompt_override"] is None

    async def test_update_agent_requires_auth(self, client: AsyncClient):
        resp = await client.patch(AGENT_URL, json={"name": "Hacker"})
        assert resp.status_code == 403


class TestResetAgentEmbeddings:
    async def test_reset_embeddings_success(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        with patch(
            "app.api.v1.agent.delete_all_user_chunks", new_callable=AsyncMock
        ) as mock_delete:
            resp = await client.post(f"{AGENT_URL}/reset", headers=headers)

        assert resp.status_code == 204
        mock_delete.assert_called_once()

    async def test_reset_embeddings_requires_auth(self, client: AsyncClient):
        resp = await client.post(f"{AGENT_URL}/reset")
        assert resp.status_code == 403

    async def test_reset_does_not_affect_agent_config(
        self, client: AsyncClient, auth_headers
    ):
        """Reset should only clear vector data, not agent settings."""
        headers, _, __ = auth_headers

        await client.patch(AGENT_URL, json={"name": "My Agent"}, headers=headers)

        with patch("app.api.v1.agent.delete_all_user_chunks", new_callable=AsyncMock):
            await client.post(f"{AGENT_URL}/reset", headers=headers)

        resp = await client.get(AGENT_URL, headers=headers)
        assert resp.json()["name"] == "My Agent"
