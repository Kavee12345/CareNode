"""
Test infrastructure.

Strategy:
  - One test PostgreSQL database (medagent_test), created fresh per session.
  - Each test runs inside a transaction that is rolled back → no state leak.
  - External services (MinIO, embeddings, LLM/agent) are mocked.
  - The `get_db` FastAPI dependency is overridden to use the test session.
"""
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ── env must be set before app imports ───────────────────────────────────────
import os
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://medagent:medagent_secret@localhost:5432/medagent_test")
os.environ.setdefault("DATABASE_URL_SYNC", "postgresql://medagent:medagent_secret@localhost:5432/medagent_test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-32chars")
os.environ.setdefault("GOOGLE_API_KEY", "test-key")
os.environ.setdefault("MINIO_ACCESS_KEY", "test")
os.environ.setdefault("MINIO_SECRET_KEY", "test")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("CORS_ORIGINS", '["http://localhost:3000"]')
os.environ.setdefault("ALLOWED_EXTENSIONS", '["pdf","png","jpg","jpeg","txt","docx"]')

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Agent, User  # noqa: E402
from app.core.security import hash_password, create_access_token  # noqa: E402

# ── test engine (points at medagent_test database) ───────────────────────────
TEST_DB_URL = os.environ["DATABASE_URL"]

test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


# ── session-scoped: create all tables once ────────────────────────────────────
@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with test_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


# ── function-scoped: each test runs in a rolled-back transaction ──────────────
@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.connect() as conn:
        await conn.begin()
        # Also begin a savepoint so individual test commits don't commit to DB
        await conn.begin_nested()

        session = AsyncSession(bind=conn, expire_on_commit=False)

        # Re-open savepoint after each nested transaction commits
        @event.listens_for(session.sync_session, "after_transaction_end")
        def restart_savepoint(session_, transaction):
            if transaction.nested and not transaction._parent.nested:
                session_.begin_nested()

        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()


# ── override FastAPI DB dependency ───────────────────────────────────────────
@pytest_asyncio.fixture()
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Mock external services that make network calls
    with (
        patch("app.services.storage_service.get_minio_client", return_value=MagicMock()),
        patch("app.services.storage_service.ensure_bucket_exists", return_value=None),
        patch("app.services.storage_service.upload_file", return_value="test/key"),
        patch("app.services.storage_service.download_file", return_value=b"fake file content"),
        patch("app.services.storage_service.delete_file", return_value=None),
        patch("app.services.storage_service.get_presigned_url", return_value="http://minio/presigned"),
        patch("app.services.embedding_service.get_embedding_model"),
        patch("app.services.embedding_service.embed_texts", return_value=[[0.1] * 768]),
        patch("app.services.embedding_service.embed_query", return_value=[0.1] * 768),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


# ── helper: create a user + agent and return auth headers ────────────────────
@pytest_asyncio.fixture()
async def auth_headers(db_session: AsyncSession, client: AsyncClient):
    """Register a user and return (headers, user_id)."""
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "TestPass123!"

    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert resp.status_code == 201

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200
    tokens = resp.json()

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    return headers, email, tokens["refresh_token"]


@pytest_asyncio.fixture()
async def mock_agent_response():
    """Patch the medical agent so chat tests don't call Anthropic."""
    fake_response = {
        "answer": "Based on your records, this looks routine. Please consult your doctor.",
        "escalation_level": "none",
        "confidence": 0.85,
        "recommendations": ["Stay hydrated", "Monitor symptoms"],
        "disclaimer": "This is not medical advice.",
        "sources": [],
    }

    async def fake_stream(*args, **kwargs):
        import json
        yield "data: Based on your records\n\n"
        yield f"data: [DONE]{json.dumps(fake_response)}\n\n"

    with patch("app.api.v1.chat.stream_medical_agent", side_effect=fake_stream):
        yield fake_response
