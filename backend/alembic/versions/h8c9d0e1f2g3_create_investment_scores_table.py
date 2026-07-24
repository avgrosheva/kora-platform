"""create investment_scores table

Revision ID: h8c9d0e1f2g3
Revises: g7b8c9d0e1f2
Create Date: 2026-07-24 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "h8c9d0e1f2g3"
down_revision: Union[str, None] = "g7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the `investment_scores` table with its indexes and
    constraints."""
    op.create_table(
        "investment_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("financial_score", sa.Float(), nullable=True),
        sa.Column("growth_score", sa.Float(), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True),
        sa.Column("market_score", sa.Float(), nullable=True),
        sa.Column("team_score", sa.Float(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_investment_scores_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_investment_scores"),
        sa.UniqueConstraint(
            "document_id", name="uq_investment_scores_document_id"
        ),
    )
    op.create_index(
        "ix_investment_scores_document_id",
        "investment_scores",
        ["document_id"],
        unique=True,
    )


def downgrade() -> None:
    """Drop the `investment_scores` table and its indexes."""
    op.drop_index(
        "ix_investment_scores_document_id", table_name="investment_scores"
    )
    op.drop_table("investment_scores")