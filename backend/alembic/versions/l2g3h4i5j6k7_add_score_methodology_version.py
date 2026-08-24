"""add methodology_version and category_breakdown to investment_scores

Revision ID: l2g3h4i5j6k7
Revises: k1f2g3h4i5j6
Create Date: 2026-08-06 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "l2g3h4i5j6k7"
down_revision: Union[str, None] = "k1f2g3h4i5j6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("investment_scores", sa.Column("methodology_version", sa.String(length=50), nullable=True))
    op.add_column("investment_scores", sa.Column("category_breakdown", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("investment_scores", "category_breakdown")
    op.drop_column("investment_scores", "methodology_version")