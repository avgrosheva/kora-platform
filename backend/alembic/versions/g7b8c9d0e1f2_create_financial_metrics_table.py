"""create financial_metrics table

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-23 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "g7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the `financial_metrics` table with its indexes and
    constraints."""
    op.create_table(
        "financial_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("revenue", sa.Float(), nullable=True),
        sa.Column("arr", sa.Float(), nullable=True),
        sa.Column("mrr", sa.Float(), nullable=True),
        sa.Column("gross_margin", sa.Float(), nullable=True),
        sa.Column("ebitda", sa.Float(), nullable=True),
        sa.Column("burn_rate", sa.Float(), nullable=True),
        sa.Column("runway_months", sa.Float(), nullable=True),
        sa.Column("cash", sa.Float(), nullable=True),
        sa.Column("customers", sa.Integer(), nullable=True),
        sa.Column("growth_rate", sa.Float(), nullable=True),
        sa.Column("cac", sa.Float(), nullable=True),
        sa.Column("ltv", sa.Float(), nullable=True),
        sa.Column("valuation", sa.Float(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_financial_metrics_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_financial_metrics"),
        sa.UniqueConstraint(
            "document_id", name="uq_financial_metrics_document_id"
        ),
    )
    op.create_index(
        "ix_financial_metrics_document_id",
        "financial_metrics",
        ["document_id"],
        unique=True,
    )


def downgrade() -> None:
    """Drop the `financial_metrics` table and its indexes."""
    op.drop_index(
        "ix_financial_metrics_document_id", table_name="financial_metrics"
    )
    op.drop_table("financial_metrics")