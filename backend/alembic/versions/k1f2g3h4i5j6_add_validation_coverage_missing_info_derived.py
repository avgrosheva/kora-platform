"""add validation_findings, coverage_assessments, missing_information_items, derived_metrics tables

Revision ID: k1f2g3h4i5j6
Revises: j0e1f2g3h4i5
Create Date: 2026-08-03 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "k1f2g3h4i5j6"
down_revision: Union[str, None] = "j0e1f2g3h4i5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create `validation_findings`, `coverage_assessments`,
    `missing_information_items`, and `derived_metrics` tables."""
    op.create_table(
        "validation_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("affected_metrics", postgresql.JSONB(), nullable=False),
        sa.Column("sources", postgresql.JSONB(), nullable=False),
        sa.Column("suggested_question", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_validation_findings_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_validation_findings"),
    )
    op.create_index(
        "ix_validation_findings_document_id", "validation_findings", ["document_id"]
    )
    op.create_index("ix_validation_findings_severity", "validation_findings", ["severity"])
    op.create_index("ix_validation_findings_category", "validation_findings", ["category"])

    op.create_table(
        "coverage_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("overall_confidence", sa.Float(), nullable=False),
        sa.Column("coverage", postgresql.JSONB(), nullable=False),
        sa.Column("source_coverage", sa.Float(), nullable=False),
        sa.Column("ambiguities_count", sa.Integer(), nullable=False),
        sa.Column("critical_missing_fields", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_coverage_assessments_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_coverage_assessments"),
        sa.UniqueConstraint("document_id", name="uq_coverage_assessments_document_id"),
    )
    op.create_index(
        "ix_coverage_assessments_document_id",
        "coverage_assessments",
        ["document_id"],
        unique=True,
    )

    op.create_table(
        "missing_information_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("field_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_missing_information_items_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_missing_information_items"),
    )
    op.create_index(
        "ix_missing_information_items_document_id",
        "missing_information_items",
        ["document_id"],
    )
    op.create_index(
        "ix_missing_information_items_category",
        "missing_information_items",
        ["category"],
    )

    op.create_table(
        "derived_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column("period", sa.String(length=20), nullable=True),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("display_value", sa.String(length=64), nullable=True),
        sa.Column("formula", sa.Text(), nullable=False),
        sa.Column("inputs", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "calculation_version",
            sa.String(length=50),
            nullable=False,
            server_default="v1",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_derived_metrics_document_id_documents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_derived_metrics"),
    )
    op.create_index("ix_derived_metrics_document_id", "derived_metrics", ["document_id"])
    op.create_index("ix_derived_metrics_metric", "derived_metrics", ["metric"])
    op.create_index(
        "ix_derived_metrics_document_metric", "derived_metrics", ["document_id", "metric"]
    )


def downgrade() -> None:
    """Drop all four tables, in dependency order."""
    op.drop_index("ix_derived_metrics_document_metric", table_name="derived_metrics")
    op.drop_index("ix_derived_metrics_metric", table_name="derived_metrics")
    op.drop_index("ix_derived_metrics_document_id", table_name="derived_metrics")
    op.drop_table("derived_metrics")

    op.drop_index(
        "ix_missing_information_items_category", table_name="missing_information_items"
    )
    op.drop_index(
        "ix_missing_information_items_document_id", table_name="missing_information_items"
    )
    op.drop_table("missing_information_items")

    op.drop_index("ix_coverage_assessments_document_id", table_name="coverage_assessments")
    op.drop_table("coverage_assessments")

    op.drop_index("ix_validation_findings_category", table_name="validation_findings")
    op.drop_index("ix_validation_findings_severity", table_name="validation_findings")
    op.drop_index("ix_validation_findings_document_id", table_name="validation_findings")
    op.drop_table("validation_findings")