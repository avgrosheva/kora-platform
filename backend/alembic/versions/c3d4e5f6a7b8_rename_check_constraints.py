"""rename check constraints to fix naming convention double-prefix

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-23 00:00:00.000000

"""
from typing import Sequence, Union

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


def upgrade() -> None:
    """Rename the doubled-prefix check constraint names to clean names."""
    op.execute(
        f'ALTER TABLE memberships '
        f'RENAME CONSTRAINT "{_OLD_MEMBERSHIP_CK}" TO "{_NEW_MEMBERSHIP_CK}"'
    )
    op.execute(
        f'ALTER TABLE organization_invitations '
        f'RENAME CONSTRAINT "{_OLD_INVITATION_CK}" TO "{_NEW_INVITATION_CK}"'
    )


def downgrade() -> None:
    """Revert the check constraint names back to their doubled-prefix form."""
    op.execute(
        f'ALTER TABLE memberships '
        f'RENAME CONSTRAINT "{_NEW_MEMBERSHIP_CK}" TO "{_OLD_MEMBERSHIP_CK}"'
    )
    op.execute(
        f'ALTER TABLE organization_invitations '
        f'RENAME CONSTRAINT "{_NEW_INVITATION_CK}" TO "{_OLD_INVITATION_CK}"'
    )