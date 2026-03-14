"""Change embedding dimension from 384 to 768 (Google text-embedding-004).

Revision ID: 002
Revises: 001
Create Date: 2026-03-12
"""
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop HNSW index (cannot alter a column with an index on it)
    op.execute("DROP INDEX IF EXISTS idx_chunks_embedding_hnsw")

    # Change column type: 384 -> 768
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(768)")

    # Recreate HNSW index for 768-dim
    op.execute("""
        CREATE INDEX idx_chunks_embedding_hnsw
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

    # All existing 384-dim embeddings are now invalid — truncate chunks
    # (documents will need to be re-processed after this migration)
    op.execute("TRUNCATE TABLE document_chunks")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_chunks_embedding_hnsw")
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(384)")
    op.execute("""
        CREATE INDEX idx_chunks_embedding_hnsw
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    op.execute("TRUNCATE TABLE document_chunks")
