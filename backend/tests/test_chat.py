"""Tests for /api/v1/chat/* endpoints."""
import uuid
import pytest
from httpx import AsyncClient


CONV_URL = "/api/v1/chat/conversations"


class TestCreateConversation:
    async def test_create_conversation_success(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        resp = await client.post(CONV_URL, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["title"] == "New Conversation"

    async def test_create_conversation_requires_auth(self, client: AsyncClient):
        resp = await client.post(CONV_URL)
        assert resp.status_code == 403


class TestListConversations:
    async def test_list_empty(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        resp = await client.get(CONV_URL, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_list_shows_created_conversations(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        await client.post(CONV_URL, headers=headers)
        await client.post(CONV_URL, headers=headers)

        resp = await client.get(CONV_URL, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 2

    async def test_list_pagination(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        for _ in range(3):
            await client.post(CONV_URL, headers=headers)

        resp = await client.get(f"{CONV_URL}?page=1&page_size=2", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 2
        assert data["total"] >= 3

    async def test_list_only_own_conversations(self, client: AsyncClient, auth_headers):
        headers_a, _, __ = auth_headers

        email_b = f"b_{uuid.uuid4().hex[:6]}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email_b, "password": "Pass123!"})
        login_b = await client.post("/api/v1/auth/login", json={"email": email_b, "password": "Pass123!"})
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        await client.post(CONV_URL, headers=headers_b)

        resp_a = await client.get(CONV_URL, headers=headers_a)
        conv_ids_a = [c["id"] for c in resp_a.json()["items"]]

        resp_b = await client.get(CONV_URL, headers=headers_b)
        conv_ids_b = [c["id"] for c in resp_b.json()["items"]]

        # No overlap
        assert not set(conv_ids_a) & set(conv_ids_b)

    async def test_list_requires_auth(self, client: AsyncClient):
        resp = await client.get(CONV_URL)
        assert resp.status_code == 403


class TestGetConversation:
    async def test_get_conversation_success(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        create_resp = await client.post(CONV_URL, headers=headers)
        conv_id = create_resp.json()["id"]

        resp = await client.get(f"{CONV_URL}/{conv_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == conv_id
        assert "messages" in data

    async def test_get_nonexistent_conversation(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers
        resp = await client.get(f"{CONV_URL}/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404

    async def test_cannot_get_other_users_conversation(self, client: AsyncClient, auth_headers):
        headers_a, _, __ = auth_headers

        email_b = f"b_{uuid.uuid4().hex[:6]}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email_b, "password": "Pass123!"})
        login_b = await client.post("/api/v1/auth/login", json={"email": email_b, "password": "Pass123!"})
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        create_resp = await client.post(CONV_URL, headers=headers_b)
        conv_id = create_resp.json()["id"]

        resp = await client.get(f"{CONV_URL}/{conv_id}", headers=headers_a)
        assert resp.status_code == 404


class TestDeleteConversation:
    async def test_delete_conversation_success(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        create_resp = await client.post(CONV_URL, headers=headers)
        conv_id = create_resp.json()["id"]

        resp = await client.delete(f"{CONV_URL}/{conv_id}", headers=headers)
        assert resp.status_code == 204

        resp = await client.get(f"{CONV_URL}/{conv_id}", headers=headers)
        assert resp.status_code == 404

    async def test_delete_nonexistent_conversation(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers
        resp = await client.delete(f"{CONV_URL}/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404

    async def test_cannot_delete_other_users_conversation(self, client: AsyncClient, auth_headers):
        headers_a, _, __ = auth_headers

        email_b = f"b_{uuid.uuid4().hex[:6]}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email_b, "password": "Pass123!"})
        login_b = await client.post("/api/v1/auth/login", json={"email": email_b, "password": "Pass123!"})
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        create_resp = await client.post(CONV_URL, headers=headers_b)
        conv_id = create_resp.json()["id"]

        resp = await client.delete(f"{CONV_URL}/{conv_id}", headers=headers_a)
        assert resp.status_code == 404


class TestSendMessage:
    async def test_send_message_streams_response(
        self, client: AsyncClient, auth_headers, mock_agent_response
    ):
        headers, _, __ = auth_headers

        create_resp = await client.post(CONV_URL, headers=headers)
        conv_id = create_resp.json()["id"]

        resp = await client.post(
            f"{CONV_URL}/{conv_id}/messages",
            json={"message": "What does my blood pressure reading mean?"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

    async def test_send_message_updates_conversation_title(
        self, client: AsyncClient, auth_headers, mock_agent_response
    ):
        headers, _, __ = auth_headers

        create_resp = await client.post(CONV_URL, headers=headers)
        conv_id = create_resp.json()["id"]

        await client.post(
            f"{CONV_URL}/{conv_id}/messages",
            json={"message": "My question about medications"},
            headers=headers,
        )

        detail_resp = await client.get(f"{CONV_URL}/{conv_id}", headers=headers)
        assert detail_resp.json()["title"] != "New Conversation"

    async def test_send_message_to_nonexistent_conversation(
        self, client: AsyncClient, auth_headers
    ):
        headers, _, __ = auth_headers
        resp = await client.post(
            f"{CONV_URL}/{uuid.uuid4()}/messages",
            json={"message": "Hello"},
            headers=headers,
        )
        assert resp.status_code == 404

    async def test_send_message_to_other_users_conversation(
        self, client: AsyncClient, auth_headers
    ):
        headers_a, _, __ = auth_headers

        email_b = f"b_{uuid.uuid4().hex[:6]}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email_b, "password": "Pass123!"})
        login_b = await client.post("/api/v1/auth/login", json={"email": email_b, "password": "Pass123!"})
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        create_resp = await client.post(CONV_URL, headers=headers_b)
        conv_id = create_resp.json()["id"]

        resp = await client.post(
            f"{CONV_URL}/{conv_id}/messages",
            json={"message": "Trying to snoop"},
            headers=headers_a,
        )
        assert resp.status_code == 404

    async def test_send_message_requires_auth(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers
        create_resp = await client.post(CONV_URL, headers=headers)
        conv_id = create_resp.json()["id"]

        resp = await client.post(
            f"{CONV_URL}/{conv_id}/messages",
            json={"message": "Hello"},
        )
        assert resp.status_code == 403

    async def test_messages_appear_in_conversation_detail(
        self, client: AsyncClient, auth_headers, mock_agent_response
    ):
        headers, _, __ = auth_headers

        create_resp = await client.post(CONV_URL, headers=headers)
        conv_id = create_resp.json()["id"]

        await client.post(
            f"{CONV_URL}/{conv_id}/messages",
            json={"message": "Check my lab results"},
            headers=headers,
        )

        detail_resp = await client.get(f"{CONV_URL}/{conv_id}", headers=headers)
        assert detail_resp.status_code == 200
        messages = detail_resp.json()["messages"]
        assert len(messages) >= 1
        roles = [m["role"] for m in messages]
        assert "user" in roles
