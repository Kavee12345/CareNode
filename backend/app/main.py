from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.v1.router import api_router
from app.core.exceptions import AppError, app_error_handler
from app.db.session import engine
from app.db.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables (Alembic handles migrations in prod)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Pre-warm embedding model
    from app.services.embedding_service import get_embedding_model
    get_embedding_model()

    # Ensure MinIO bucket exists
    from app.services.storage_service import ensure_bucket_exists
    try:
        ensure_bucket_exists()
    except Exception as e:
        print(f"Warning: MinIO setup failed: {e}")

    yield

    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="MedAgent API",
    description="Private AI health agent with zero-leak RAG",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(AppError, app_error_handler)

# Routes
app.include_router(api_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}
