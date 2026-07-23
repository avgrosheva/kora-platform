"""create document_analyses table

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-23 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the `document_analyses` table with its indexes and
    constraints."""
    op.create_table(
        "document_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("company_name", sa.String(length=255), nullable=True),
        sa.Column("industry", sa.String(length=255), nullable=True),
        sa.Column("business_model", sa.Text(), nullable=True),
        sa.Column("key_products", postgresql.JSONB(), nullable=True),
        sa.Column("risks", postgresql.JSONB(), nullable=True),
        sa.Column("opportunities", postgresql.JSONB(), nullable=True),
        sa.Column("revenue_streams", postgresql.JSONB(), nullable=True),
        sa.Column("customers", postgresql.JSONB(), nullable=True),
        sa.Column("competitors", postgresql.JSONB(), nullable=True),
        sa.Column("raw_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_document_analyses_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_document_analyses"),
        sa.UniqueConstraint("document_id", name="uq_document_analyses_document_id"),
    )
    op.create_index(
        "ix_document_analyses_document_id",
        "document_analyses",
        ["document_id"],
        unique=True,
    )


def downgrade() -> None:
    """Drop the `document_analyses` table and its indexes."""
    op.drop_index(
        "ix_document_analyses_document_id", table_name="document_analyses"
    )
    op.drop_table("document_analyses")