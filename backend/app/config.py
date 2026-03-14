import json
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_env: str = "development"
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:3000"]

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")
    database_url_sync: str = Field(..., alias="DATABASE_URL_SYNC")

    # Auth
    secret_key: str = Field(..., alias="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Google Gemini
    google_api_key: str = Field(..., alias="GOOGLE_API_KEY")
    llm_model: str = "gemini-2.0-flash"
    llm_max_tokens: int = 2048
    llm_temperature: float = 0.1

    # Embeddings (Google text-embedding-004 = 768-dim)
    embedding_dimension: int = 768

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = Field(..., alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(..., alias="MINIO_SECRET_KEY")
    minio_bucket: str = "medagent-documents"
    minio_secure: bool = False

    # Upload
    max_upload_size_mb: int = 50
    allowed_extensions: list[str] = ["pdf", "png", "jpg", "jpeg", "txt", "docx"]

    # RAG
    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 64
    rag_top_k: int = 5
    rag_fetch_k: int = 10
    rag_similarity_threshold: float = 0.35

    @field_validator("cors_origins", "allowed_extensions", mode="before")
    @classmethod
    def parse_list_field(cls, v: object) -> object:
        """Accept both JSON arrays and comma-separated strings from .env."""
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    model_config = {"env_file": ".env", "extra": "ignore", "populate_by_name": True}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
