"""add source_citations, financial_facts tables and document_embeddings.page_number

Revision ID: j0e1f2g3h4i5
Revises: i9d0e1f2g3h4
Create Date: 2026-07-27 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "j0e1f2g3h4i5"
down_revision: Union[str, None] = "i9d0e1f2g3h4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create `source_citations` and `financial_facts`, and add
    `document_embeddings.page_number`.

    `source_citations` is created first since `financial_facts`
    references it via a nullable foreign key.
    """
    op.add_column(
        "document_embeddings",
        sa.Column("page_number", sa.Integer(), nullable=True),
    )

    op.create_table(
        "source_citations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("field_path", sa.String(length=255), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("extraction_version", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_source_citations_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["document_embeddings.id"],
            name="fk_source_citations_chunk_id_document_embeddings",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_source_citations"),
    )
    op.create_index(
        "ix_source_citations_document_id", "source_citations", ["document_id"]
    )
    op.create_index(
        "ix_source_citations_field_path", "source_citations", ["field_path"]
    )

    op.create_table(
        "financial_facts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("period_type", sa.String(length=20), nullable=False),
        sa.Column("period", sa.String(length=20), nullable=True),
        sa.Column("value_type", sa.String(length=20), nullable=False),
        sa.Column("source_citation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_financial_facts_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_citation_id"],
            ["source_citations.id"],
            name="fk_financial_facts_source_citation_id_source_citations",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_financial_facts"),
    )
    op.create_index(
        "ix_financial_facts_document_id", "financial_facts", ["document_id"]
    )
    op.create_index("ix_financial_facts_metric", "financial_facts", ["metric"])
    op.create_index(
        "ix_financial_facts_source_citation_id",
        "financial_facts",
        ["source_citation_id"],
    )
    # Composite index for the derived-metrics engine's most common query
    # shape: "all facts for this document, this metric, ordered by period".
    op.create_index(
        "ix_financial_facts_document_metric",
        "financial_facts",
        ["document_id", "metric"],
    )


def downgrade() -> None:
    """Drop `financial_facts`, `source_citations`, and
    `document_embeddings.page_number`, in dependency order."""
    op.drop_index("ix_financial_facts_document_metric", table_name="financial_facts")
    op.drop_index(
        "ix_financial_facts_source_citation_id", table_name="financial_facts"
    )
    op.drop_index("ix_financial_facts_metric", table_name="financial_facts")
    op.drop_index("ix_financial_facts_document_id", table_name="financial_facts")
    op.drop_table("financial_facts")

    op.drop_index("ix_source_citations_field_path", table_name="source_citations")
    op.drop_index("ix_source_citations_document_id", table_name="source_citations")
    op.drop_table("source_citations")

    op.drop_column("document_embeddings", "page_number")