"""add qualitative_facts table

Revision ID: m3h4i5j6k7l8
Revises: l2g3h4i5j6k7
Create Date: 2026-08-25 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "m3h4i5j6k7l8"
down_revision: Union[str, None] = "l2g3h4i5j6k7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create `qualitative_facts` — the non-numeric counterpart to
    `financial_facts` (Evidence Layer plan, Step 4).

    References `source_citations`, which already exists (added in
    j0e1f2g3h4i5), so no ordering concern here.
    """
    op.create_table(
        "qualitative_facts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("fact_type", sa.String(length=20), nullable=False),
        sa.Column("severity_hint", sa.String(length=20), nullable=True),
        sa.Column("source_citation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_qualitative_facts_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_citation_id"],
            ["source_citations.id"],
            name="fk_qualitative_facts_source_citation_id_source_citations",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_qualitative_facts"),
    )
    op.create_index(
        "ix_qualitative_facts_document_id", "qualitative_facts", ["document_id"]
    )
    op.create_index(
        "ix_qualitative_facts_category", "qualitative_facts", ["category"]
    )
    op.create_index(
        "ix_qualitative_facts_source_citation_id",
        "qualitative_facts",
        ["source_citation_id"],
    )
    # Composite index mirroring financial_facts' document+metric index:
    # the common access path is "all qualitative facts for this
    # document, this category" (e.g. EvidenceService.fields_found).
    op.create_index(
        "ix_qualitative_facts_document_category",
        "qualitative_facts",
        ["document_id", "category"],
    )


def downgrade() -> None:
    """Drop `qualitative_facts`."""
    op.drop_index(
        "ix_qualitative_facts_document_category", table_name="qualitative_facts"
    )
    op.drop_index(
        "ix_qualitative_facts_source_citation_id", table_name="qualitative_facts"
    )
    op.drop_index("ix_qualitative_facts_category", table_name="qualitative_facts")
    op.drop_index("ix_qualitative_facts_document_id", table_name="qualitative_facts")
    op.drop_table("qualitative_facts")
