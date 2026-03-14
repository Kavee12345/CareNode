from google import genai
from google.genai import types
from app.config import settings

_client = genai.Client(api_key=settings.google_api_key)
_EMBEDDING_MODEL = "gemini-embedding-001"


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of document chunks for storage."""
    result = _client.models.embed_content(
        model=_EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=768,
        ),
    )
    return [e.values for e in result.embeddings]


def embed_query(query: str) -> list[float]:
    """Embed a single search query."""
    result = _client.models.embed_content(
        model=_EMBEDDING_MODEL,
        contents=query,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=768,
        ),
    )
    return result.embeddings[0].values


# Kept for backwards-compat with conftest mock patches
def get_embedding_model():
    return None
