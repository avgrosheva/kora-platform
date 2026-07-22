"""SQLAlchemy ORM models for the organization domain.

Defines `Organization`, `Membership`, and `OrganizationInvitation`. An
organization is a tenant-like container; a user's relationship to an
organization is represented by a `Membership` with a role; an
`OrganizationInvitation` represents a pending invite for someone (by
email) to join an organization with a given role.
"""

import enum
import re
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User

_SLUG_SANITIZE_PATTERN = re.compile(r"[^a-z0-9]+")


class MembershipRole(str, enum.Enum):
    """Role a user holds within an organization.

    Attributes:
        OWNER: Full control, including deleting the organization and
            changing other members' roles. Every organization must
            retain at least one owner.
        ADMIN: Can manage organization settings, members, and
            invitations, but cannot delete the organization or change
            roles.
        MEMBER: Basic membership with no administrative privileges.
    """

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


def slugify(name: str) -> str:
    """Convert a display name into a URL-safe slug.

    Args:
        name: The human-readable name to convert.

    Returns:
        A lowercase, hyphen-separated slug derived from `name`. Falls
        back to `"organization"` if the name contains no usable
        alphanumeric characters.
    """
    normalized = _SLUG_SANITIZE_PATTERN.sub("-", name.strip().lower()).strip("-")
    return normalized or "organization"


class Organization(Base):
    """A tenant-like container that users belong to via `Membership`.

    Attributes:
        id: Primary key, a randomly generated UUID.
        name: The organization's display name.
        slug: A unique, URL-safe identifier for the organization.
        created_at: Timezone-aware timestamp when the record was
            created.
        updated_at: Timezone-aware timestamp when the record was last
            updated.
        memberships: All memberships belonging to this organization.
        invitations: All invitations issued by this organization.
    """

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    invitations: Mapped[list["OrganizationInvitation"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """Return a debug-friendly representation of the organization.

        Returns:
            A string identifying the organization by id and slug.
        """
        return f"<Organization id={self.id} slug={self.slug!r}>"


class Membership(Base):
    """Represents a user's membership and role within an organization.

    Attributes:
        id: Primary key, a randomly generated UUID.
        organization_id: The organization this membership belongs to.
        user_id: The user this membership belongs to.
        role: The user's role within the organization.
        created_at: Timezone-aware timestamp when the membership was
            created.
        organization: The related `Organization`.
        user: The related `User`.
    """

    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "organization_id",
            name="uq_memberships_user_organization",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[MembershipRole] = mapped_column(
        Enum(
            MembershipRole,
            name="membership_role",
            native_enum=False,
            validate_strings=True,
            length=20,
        ),
        nullable=False,
        default=MembershipRole.MEMBER,
        server_default=MembershipRole.MEMBER.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    organization: Mapped["Organization"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        """Return a debug-friendly representation of the membership.

        Returns:
            A string identifying the membership by user, organization,
            and role.
        """
        return (
            f"<Membership user_id={self.user_id} "
            f"organization_id={self.organization_id} role={self.role}>"
        )


class OrganizationInvitation(Base):
    """Represents a pending invitation for an email to join an organization.

    Attributes:
        id: Primary key, a randomly generated UUID.
        organization_id: The organization the invitation is for.
        email: The email address invited to join.
        role: The role the invitee will receive upon acceptance.
        token: A unique, unguessable token used to accept the
            invitation.
        expires_at: Timezone-aware timestamp after which the invitation
            is no longer valid.
        accepted_at: Timezone-aware timestamp when the invitation was
            accepted, or `None` if still pending.
        created_at: Timezone-aware timestamp when the invitation was
            created.
        organization: The related `Organization`.
    """

    __tablename__ = "organization_invitations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    role: Mapped[MembershipRole] = mapped_column(
        Enum(
            MembershipRole,
            name="invitation_role",
            native_enum=False,
            validate_strings=True,
            length=20,
        ),
        nullable=False,
        default=MembershipRole.MEMBER,
        server_default=MembershipRole.MEMBER.value,
    )
    token: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    organization: Mapped["Organization"] = relationship(back_populates="invitations")

    def __repr__(self) -> str:
        """Return a debug-friendly representation of the invitation.

        Returns:
            A string identifying the invitation by organization and
            email (never includes the token).
        """
        return (
            f"<OrganizationInvitation organization_id={self.organization_id} "
            f"email={self.email!r}>"
        )