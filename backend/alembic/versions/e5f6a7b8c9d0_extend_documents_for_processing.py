"""extend documents table for text-extraction processing

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-23 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_CHECK_NAME = "ck_documents_document_status"


def upgrade() -> None:
    """Add processing columns and update the status check constraint.

    Renames the `processed` status value to `completed` (updating any
    existing rows first) and adds `text_content`, `page_count`,
    `processing_error`, and `processed_at` columns.
    """
    op.add_column("documents", sa.Column("text_content", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("page_count", sa.Integer(), nullable=True))
    op.add_column(
        "documents", sa.Column("processing_error", sa.Text(), nullable=True)
    )
    op.add_column(
        "documents",
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(
        "UPDATE documents SET status = 'completed' WHERE status = 'processed'"
    )

    op.drop_constraint(op.f(_OLD_CHECK_NAME), "documents", type_="check")
    op.create_check_constraint(
        "document_status",
        "documents",
        "status IN ('uploaded', 'processing', 'completed', 'failed')",
    )


def downgrade() -> None:
    """Revert the status check constraint and drop processing columns."""
    op.execute(
        "UPDATE documents SET status = 'processed' WHERE status = 'completed'"
    )

    op.drop_constraint(op.f("ck_documents_document_status"), "documents", type_="check")
    op.create_check_constraint(
        "document_status",
        "documents",
        "status IN ('uploaded', 'processing', 'processed', 'failed')",
    )

    op.drop_column("documents", "processed_at")
    op.drop_column("documents", "processing_error")
    op.drop_column("documents", "page_count")
    op.drop_column("documents", "text_content")