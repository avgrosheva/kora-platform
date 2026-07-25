"""enable pgvector extension and create document_embeddings table

Revision ID: i9d0e1f2g3h4
Revises: h8c9d0e1f2g3
Create Date: 2026-07-25 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "i9d0e1f2g3h4"
down_revision: Union[str, None] = "h8c9d0e1f2g3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIMENSIONS = 1536


def upgrade() -> None:
    """Enable the pgvector extension and create `document_embeddings`.

    Creates a btree index on `document_id` (for efficient delete/reindex
    and organization-scoped joins) and an HNSW index on `embedding`
    using cosine distance (for fast approximate nearest-neighbor
    search).
    """
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "document_embeddings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_document_embeddings_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_embeddings"),
    )
    op.create_index(
        "ix_document_embeddings_document_id",
        "document_embeddings",
        ["document_id"],
    )
    op.create_index(
        "ix_document_embeddings_embedding_hnsw",
        "document_embeddings",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    """Drop `document_embeddings` and its indexes.

    The `vector` extension itself is intentionally left installed on
    downgrade, since dropping it would be destructive to any other
    future use of pgvector in the database and is not something a
    single table's migration should own.
    """
    op.drop_index(
        "ix_document_embeddings_embedding_hnsw", table_name="document_embeddings"
    )
    op.drop_index(
        "ix_document_embeddings_document_id", table_name="document_embeddings"
    )
    op.drop_table("document_embeddings")