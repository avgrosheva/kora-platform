"""Pydantic schemas for the organization domain."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.organization import MembershipRole

_SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class OrganizationCreate(BaseModel):
    """Payload for creating a new organization.

    Attributes:
        name: The organization's display name.
        slug: Optional URL-safe unique identifier. If omitted, a slug
            is automatically generated from `name`.
    """

    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(
        default=None,
        max_length=255,
        pattern=_SLUG_PATTERN,
        description=(
            "Lowercase, hyphen-separated identifier. Auto-generated "
            "from name if omitted."
        ),
    )

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        """Strip surrounding whitespace and reject blank names.

        Args:
            value: The raw `name` value.

        Returns:
            The trimmed name.

        Raises:
            ValueError: If the name is blank after trimming.
        """
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Organization name must not be blank.")
        return trimmed


class OrganizationUpdate(BaseModel):
    """Payload for updating an existing organization.

    Attributes:
        name: The organization's new display name, if changing.
        slug: The organization's new slug, if changing.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=255, pattern=_SLUG_PATTERN)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        """Strip surrounding whitespace and reject blank names.

        Args:
            value: The raw `name` value, or `None`.

        Returns:
            The trimmed name, or `None`.

        Raises:
            ValueError: If a provided name is blank after trimming.
        """
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Organization name must not be blank.")
        return trimmed


class OrganizationRead(BaseModel):
    """Public representation of an organization.

    Attributes:
        id: The organization's unique identifier.
        name: The organization's display name.
        slug: The organization's unique, URL-safe identifier.
        created_at: Timestamp when the organization was created.
        updated_at: Timestamp when the organization was last updated.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime


class MembershipRead(BaseModel):
    """Public representation of a membership.

    Attributes:
        id: The membership's unique identifier.
        organization_id: The organization this membership belongs to.
        user_id: The user this membership belongs to.
        role: The user's role within the organization.
        created_at: Timestamp when the membership was created.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    role: MembershipRole
    created_at: datetime


class InvitationCreate(BaseModel):
    """Payload for inviting a new member to an organization.

    Attributes:
        email: The email address to invite.
        role: The role the invitee will receive upon acceptance.
    """

    email: EmailStr
    role: MembershipRole = MembershipRole.MEMBER


class InvitationRead(BaseModel):
    """Public representation of an organization invitation.

    Note:
        `token` is included here because the platform does not yet send
        invitation emails; the inviter must currently relay the token to
        the invitee manually (e.g. by copying it from this response).
        Once transactional email delivery is implemented, `token`
        should be removed from this schema.

    Attributes:
        id: The invitation's unique identifier.
        organization_id: The organization the invitation is for.
        email: The invited email address.
        role: The role to be granted upon acceptance.
        token: The unique token used to accept the invitation.
        expires_at: Timestamp after which the invitation is no longer
            valid.
        accepted_at: Timestamp when the invitation was accepted, or
            `None` if still pending.
        created_at: Timestamp when the invitation was created.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    email: EmailStr
    role: MembershipRole
    token: str
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime


class AddMemberRequest(BaseModel):
    """Payload for directly adding an existing user to an organization.

    Attributes:
        user_id: The id of the existing user to add.
        role: The role to grant the new member.
    """

    user_id: uuid.UUID
    role: MembershipRole = MembershipRole.MEMBER


class ChangeRoleRequest(BaseModel):
    """Payload for changing a member's role.

    Attributes:
        role: The new role to assign to the member.
    """

    role: MembershipRole