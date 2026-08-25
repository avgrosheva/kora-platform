"""add investment_scores.assessment_status

Revision ID: n4i5j6k7l8m9
Revises: m3h4i5j6k7l8
Create Date: 2026-08-25 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "n4i5j6k7l8m9"
down_revision: Union[str, None] = "m3h4i5j6k7l8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the nullable `assessment_status` column (Evidence Layer plan,
    Step 8). Nullable and backfill-free: existing rows simply have
    `assessment_status=NULL` until the next `POST /{id}/score` recomputes
    them, consistent with how `methodology_version`/`category_breakdown`
    were added in l2g3h4i5j6k7.
    """
    op.add_column(
        "investment_scores",
        sa.Column("assessment_status", sa.String(length=30), nullable=True),
    )


def downgrade() -> None:
    """Drop `assessment_status`."""
    op.drop_column("investment_scores", "assessment_status")
