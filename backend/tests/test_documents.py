"""Tests for /api/v1/documents/* endpoints."""
import io
import uuid
from unittest.mock import patch, AsyncMock

import pytest
from httpx import AsyncClient


DOCS_URL = "/api/v1/documents"


def make_pdf_file(name: str = "report.pdf") -> tuple[str, tuple]:
    """Create a minimal fake PDF for upload."""
    content = b"%PDF-1.4 fake pdf content for testing"
    return ("file", (name, io.BytesIO(content), "application/pdf"))


def make_text_file(name: str = "notes.txt") -> tuple[str, tuple]:
    content = b"Patient notes: blood pressure 120/80. Normal."
    return ("file", (name, io.BytesIO(content), "text/plain"))


class TestDocumentUpload:
    async def test_upload_pdf_success(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        with patch("app.api.v1.documents.process_document", new_callable=AsyncMock):
            resp = await client.post(
                f"{DOCS_URL}/upload",
                files=[make_pdf_file()],
                headers=headers,
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["original_name"] == "report.pdf"
        assert data["processing_status"] == "pending"
        assert "id" in data

    async def test_upload_text_file(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        with patch("app.api.v1.documents.process_document", new_callable=AsyncMock):
            resp = await client.post(
                f"{DOCS_URL}/upload",
                files=[make_text_file()],
                headers=headers,
            )

        assert resp.status_code == 201
        assert resp.json()["original_name"] == "notes.txt"

    async def test_upload_unsupported_mime_type(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers
        content = b"<html>fake</html>"

        resp = await client.post(
            f"{DOCS_URL}/upload",
            files=[("file", ("page.html", io.BytesIO(content), "text/html"))],
            headers=headers,
        )
        assert resp.status_code == 422

    async def test_upload_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            f"{DOCS_URL}/upload",
            files=[make_pdf_file()],
        )
        assert resp.status_code == 403

    async def test_upload_appears_in_list(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        with patch("app.api.v1.documents.process_document", new_callable=AsyncMock):
            await client.post(f"{DOCS_URL}/upload", files=[make_pdf_file("labs.pdf")], headers=headers)

        resp = await client.get(DOCS_URL, headers=headers)
        assert resp.status_code == 200
        names = [d["original_name"] for d in resp.json()["items"]]
        assert "labs.pdf" in names


class TestListDocuments:
    async def test_list_empty(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers
        resp = await client.get(DOCS_URL, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_list_pagination(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        with patch("app.api.v1.documents.process_document", new_callable=AsyncMock):
            for i in range(3):
                await client.post(
                    f"{DOCS_URL}/upload",
                    files=[make_text_file(f"doc{i}.txt")],
                    headers=headers,
                )

        resp = await client.get(f"{DOCS_URL}?page=1&page_size=2", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 2
        assert data["total"] >= 3

    async def test_list_only_returns_own_documents(self, client: AsyncClient, auth_headers):
        """User A should never see User B's documents."""
        headers_a, _, __ = auth_headers

        # Register User B
        email_b = f"b_{uuid.uuid4().hex[:6]}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={"email": email_b, "password": "Pass123!"},
        )
        login_b = await client.post(
            "/api/v1/auth/login", json={"email": email_b, "password": "Pass123!"}
        )
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        with patch("app.api.v1.documents.process_document", new_callable=AsyncMock):
            await client.post(
                f"{DOCS_URL}/upload",
                files=[make_text_file("user_b_secret.txt")],
                headers=headers_b,
            )

        resp = await client.get(DOCS_URL, headers=headers_a)
        names = [d["original_name"] for d in resp.json()["items"]]
        assert "user_b_secret.txt" not in names

    async def test_list_requires_auth(self, client: AsyncClient):
        resp = await client.get(DOCS_URL)
        assert resp.status_code == 403


class TestGetDocument:
    async def test_get_document_success(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        with patch("app.api.v1.documents.process_document", new_callable=AsyncMock):
            upload = await client.post(
                f"{DOCS_URL}/upload", files=[make_pdf_file()], headers=headers
            )
        doc_id = upload.json()["id"]

        resp = await client.get(f"{DOCS_URL}/{doc_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == doc_id

    async def test_get_nonexistent_document(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers
        resp = await client.get(f"{DOCS_URL}/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404

    async def test_cannot_get_other_users_document(self, client: AsyncClient, auth_headers):
        headers_a, _, __ = auth_headers

        email_b = f"b_{uuid.uuid4().hex[:6]}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email_b, "password": "Pass123!"})
        login_b = await client.post("/api/v1/auth/login", json={"email": email_b, "password": "Pass123!"})
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        with patch("app.api.v1.documents.process_document", new_callable=AsyncMock):
            upload = await client.post(
                f"{DOCS_URL}/upload", files=[make_text_file()], headers=headers_b
            )
        doc_id = upload.json()["id"]

        # User A tries to access User B's document
        resp = await client.get(f"{DOCS_URL}/{doc_id}", headers=headers_a)
        assert resp.status_code == 404


class TestDownloadUrl:
    async def test_download_url_success(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        with patch("app.api.v1.documents.process_document", new_callable=AsyncMock):
            upload = await client.post(
                f"{DOCS_URL}/upload", files=[make_pdf_file()], headers=headers
            )
        doc_id = upload.json()["id"]

        resp = await client.get(f"{DOCS_URL}/{doc_id}/download-url", headers=headers)
        assert resp.status_code == 200
        assert "url" in resp.json()
        assert "expires_in" in resp.json()


class TestDeleteDocument:
    async def test_delete_document_success(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers

        with patch("app.api.v1.documents.process_document", new_callable=AsyncMock):
            upload = await client.post(
                f"{DOCS_URL}/upload", files=[make_pdf_file()], headers=headers
            )
        doc_id = upload.json()["id"]

        resp = await client.delete(f"{DOCS_URL}/{doc_id}", headers=headers)
        assert resp.status_code == 204

        # Should no longer exist
        resp = await client.get(f"{DOCS_URL}/{doc_id}", headers=headers)
        assert resp.status_code == 404

    async def test_delete_nonexistent_document(self, client: AsyncClient, auth_headers):
        headers, _, __ = auth_headers
        resp = await client.delete(f"{DOCS_URL}/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404

    async def test_cannot_delete_other_users_document(self, client: AsyncClient, auth_headers):
        headers_a, _, __ = auth_headers

        email_b = f"b_{uuid.uuid4().hex[:6]}@example.com"
        await client.post("/api/v1/auth/register", json={"email": email_b, "password": "Pass123!"})
        login_b = await client.post("/api/v1/auth/login", json={"email": email_b, "password": "Pass123!"})
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        with patch("app.api.v1.documents.process_document", new_callable=AsyncMock):
            upload = await client.post(
                f"{DOCS_URL}/upload", files=[make_text_file()], headers=headers_b
            )
        doc_id = upload.json()["id"]

        resp = await client.delete(f"{DOCS_URL}/{doc_id}", headers=headers_a)
        assert resp.status_code == 404
