"""rename check constraints to fix naming convention double-prefix

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-23 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_MEMBERSHIP_CK = "ck_memberships_ck_memberships_membership_role"
_NEW_MEMBERSHIP_CK = "ck_memberships_membership_role"

_OLD_INVITATION_CK = "ck_organization_invitations_ck_organization_invitations_0c1f"
_NEW_INVITATION_CK = "ck_organization_invitations_invitation_role"


def _rename_constraint_if_present(table: str, old_names: Sequence[str], new_name: str) -> None:
    """Rename whichever of `old_names` currently exists on `table` to `new_name`.

    The constraint name actually produced by earlier migrations has drifted
    from what this migration originally assumed, so a plain unconditional
    RENAME CONSTRAINT fails on a fresh database. Only rename when a matching
    source name is found, and skip entirely if `new_name` is already in place.
    """
    conn = op.get_bind()
    current = conn.execute(
        sa.text(
            "SELECT conname FROM pg_constraint WHERE conrelid = CAST(:table AS regclass)"
        ),
        {"table": table},
    ).scalars().all()
    if new_name in current:
        return
    for old_name in old_names:
        if old_name in current:
            op.execute(f'ALTER TABLE {table} RENAME CONSTRAINT "{old_name}" TO "{new_name}"')
            return


def upgrade() -> None:
    """Rename the doubled-prefix check constraint names to clean names."""
    _rename_constraint_if_present("memberships", [_OLD_MEMBERSHIP_CK], _NEW_MEMBERSHIP_CK)
    _rename_constraint_if_present(
        "organization_invitations",
        [_OLD_INVITATION_CK, "invitation_role"],
        _NEW_INVITATION_CK,
    )


def downgrade() -> None:
    """Revert the check constraint names back to their doubled-prefix form."""
    _rename_constraint_if_present("memberships", [_NEW_MEMBERSHIP_CK], _OLD_MEMBERSHIP_CK)
    _rename_constraint_if_present(
        "organization_invitations", [_NEW_INVITATION_CK], _OLD_INVITATION_CK
    )