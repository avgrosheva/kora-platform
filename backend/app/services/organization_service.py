"""Organization domain business logic.

Implements organization lifecycle management, membership management, and
invitation handling. Services operate directly on `AsyncSession` — there
is no repository layer in this project's architecture.
"""

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import (
    Membership,
    MembershipRole,
    Organization,
    OrganizationInvitation,
    slugify,
)
from app.models.user import User

INVITATION_TOKEN_BYTES = 32
INVITATION_EXPIRE_DAYS = 7
_MAX_SLUG_GENERATION_ATTEMPTS = 10


class OrganizationServiceError(Exception):
    """Base exception for organization service failures."""


class OrganizationNotFoundError(OrganizationServiceError):
    """Raised when an organization does not exist or the actor is not a
    member of it.

    Deliberately raised for both cases (nonexistent organization, and
    existing organization the actor cannot see) to avoid confirming the
    existence of organizations the actor has no access to.
    """


class InsufficientPermissionsError(OrganizationServiceError):
    """Raised when an actor's role does not permit the requested action."""


class SlugAlreadyExistsError(OrganizationServiceError):
    """Raised when a requested slug is already in use."""


class NotAMemberError(OrganizationServiceError):
    """Raised when a target user is not a member of the organization."""


class LastOwnerError(OrganizationServiceError):
    """Raised when an action would leave an organization with no owners."""


class InvitationNotFoundError(OrganizationServiceError):
    """Raised when an invitation token does not match any invitation."""


class InvitationExpiredError(OrganizationServiceError):
    """Raised when an invitation's expiration date has passed."""


class InvitationAlreadyAcceptedError(OrganizationServiceError):
    """Raised when an invitation has already been accepted."""


class InvitationEmailMismatchError(OrganizationServiceError):
    """Raised when the accepting user's email does not match the
    invitation's target email."""


class UserAlreadyMemberError(OrganizationServiceError):
    """Raised when a user is already a member of the organization."""


class TargetUserNotFoundError(OrganizationServiceError):
    """Raised when a referenced target user does not exist."""


async def _get_membership(
    db: AsyncSession, organization_id, user_id
) -> Membership | None:
    """Fetch a membership row, if one exists.

    Args:
        db: The active database session.
        organization_id: The organization's id.
        user_id: The user's id.

    Returns:
        The `Membership` if found, otherwise `None`.
    """
    result = await db.execute(
        select(Membership).where(
            Membership.organization_id == organization_id,
            Membership.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def _require_membership(
    db: AsyncSession, organization_id, user_id
) -> Membership:
    """Fetch a membership row, raising if the actor has no access.

    Args:
        db: The active database session.
        organization_id: The organization's id.
        user_id: The user's id.

    Returns:
        The actor's `Membership`.

    Raises:
        OrganizationNotFoundError: If no membership exists, meaning
            either the organization does not exist or the user is not a
            member of it.
    """
    membership = await _get_membership(db, organization_id, user_id)
    if membership is None:
        raise OrganizationNotFoundError("Organization not found.")
    return membership


def _require_role(membership: Membership, allowed_roles: set[MembershipRole]) -> None:
    """Assert that a membership's role is one of the allowed roles.

    Args:
        membership: The membership to check.
        allowed_roles: The set of roles permitted to perform the action.

    Raises:
        InsufficientPermissionsError: If the membership's role is not in
            `allowed_roles`.
    """
    if membership.role not in allowed_roles:
        raise InsufficientPermissionsError(
            "You do not have permission to perform this action."
        )


async def _get_organization_or_raise(db: AsyncSession, organization_id) -> Organization:
    """Fetch an organization by id, raising if it does not exist.

    Args:
        db: The active database session.
        organization_id: The organization's id.

    Returns:
        The `Organization`.

    Raises:
        OrganizationNotFoundError: If no organization exists with this
            id.
    """
    organization = await db.get(Organization, organization_id)
    if organization is None:
        raise OrganizationNotFoundError("Organization not found.")
    return organization


async def _slug_exists(
    db: AsyncSession, slug: str, exclude_organization_id=None
) -> bool:
    """Check whether a slug is already in use.

    Args:
        db: The active database session.
        slug: The slug to check.
        exclude_organization_id: An organization id to exclude from the
            check (used when updating an organization's own slug).

    Returns:
        True if the slug is already in use by a different organization.
    """
    stmt = select(Organization.id).where(Organization.slug == slug)
    if exclude_organization_id is not None:
        stmt = stmt.where(Organization.id != exclude_organization_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def _generate_unique_slug(db: AsyncSession, base_slug: str) -> str:
    """Generate a unique slug, appending a random suffix on collision.

    Args:
        db: The active database session.
        base_slug: The preferred slug, typically derived from a name.

    Returns:
        A slug guaranteed not to collide with an existing organization.

    Raises:
        SlugAlreadyExistsError: If a unique slug could not be generated
            after a reasonable number of attempts.
    """
    candidate = base_slug
    for _ in range(_MAX_SLUG_GENERATION_ATTEMPTS):
        if not await _slug_exists(db, candidate):
            return candidate
        candidate = f"{base_slug}-{secrets.token_hex(3)}"

    raise SlugAlreadyExistsError("Could not generate a unique organization slug.")


async def _count_owners(db: AsyncSession, organization_id) -> int:
    """Count the number of owners in an organization.

    Args:
        db: The active database session.
        organization_id: The organization's id.

    Returns:
        The number of memberships with the `OWNER` role.
    """
    result = await db.execute(
        select(func.count())
        .select_from(Membership)
        .where(
            Membership.organization_id == organization_id,
            Membership.role == MembershipRole.OWNER,
        )
    )
    return result.scalar_one()


class OrganizationService:
    """Organization use cases: lifecycle, membership, and invitations.

    All methods are stateless and take an `AsyncSession` explicitly,
    rather than holding a session as instance state.
    """

    @staticmethod
    async def create_organization(
        db: AsyncSession,
        owner_id,
        name: str,
        slug: str | None,
    ) -> Organization:
        """Create a new organization with the creator as its owner.

        Args:
            db: The active database session.
            owner_id: The id of the user creating (and owning) the
                organization.
            name: The organization's display name.
            slug: An explicit slug, or `None` to auto-generate one from
                `name`.

        Returns:
            The newly created `Organization`.

        Raises:
            SlugAlreadyExistsError: If an explicit slug is already in
                use.
        """
        if slug is not None:
            normalized_slug = slug.strip().lower()
            if await _slug_exists(db, normalized_slug):
                raise SlugAlreadyExistsError(
                    "This organization slug is already in use."
                )
        else:
            normalized_slug = await _generate_unique_slug(db, slugify(name))

        organization = Organization(name=name.strip(), slug=normalized_slug)
        db.add(organization)
        await db.flush()

        membership = Membership(
            organization_id=organization.id,
            user_id=owner_id,
            role=MembershipRole.OWNER,
        )
        db.add(membership)

        await db.commit()
        await db.refresh(organization)
        return organization

    @staticmethod
    async def update_organization(
        db: AsyncSession,
        organization_id,
        actor_id,
        name: str | None,
        slug: str | None,
    ) -> Organization:
        """Update an organization's name and/or slug.

        Args:
            db: The active database session.
            organization_id: The organization's id.
            actor_id: The id of the user performing the update.
            name: The new name, or `None` to leave unchanged.
            slug: The new slug, or `None` to leave unchanged.

        Returns:
            The updated `Organization`.

        Raises:
            OrganizationNotFoundError: If the organization does not
                exist or the actor is not a member.
            InsufficientPermissionsError: If the actor is not an owner
                or admin.
            SlugAlreadyExistsError: If the new slug is already in use
                by a different organization.
        """
        membership = await _require_membership(db, organization_id, actor_id)
        _require_role(membership, {MembershipRole.OWNER, MembershipRole.ADMIN})

        organization = await _get_organization_or_raise(db, organization_id)

        if slug is not None:
            normalized_slug = slug.strip().lower()
            if normalized_slug != organization.slug and await _slug_exists(
                db, normalized_slug, exclude_organization_id=organization_id
            ):
                raise SlugAlreadyExistsError(
                    "This organization slug is already in use."
                )
            organization.slug = normalized_slug

        if name is not None:
            organization.name = name.strip()

        await db.commit()
        await db.refresh(organization)
        return organization

    @staticmethod
    async def delete_organization(db: AsyncSession, organization_id, actor_id) -> None:
        """Delete an organization and all its memberships/invitations.

        Args:
            db: The active database session.
            organization_id: The organization's id.
            actor_id: The id of the user performing the deletion.

        Raises:
            OrganizationNotFoundError: If the organization does not
                exist or the actor is not a member.
            InsufficientPermissionsError: If the actor is not an owner.
        """
        membership = await _require_membership(db, organization_id, actor_id)
        _require_role(membership, {MembershipRole.OWNER})

        organization = await _get_organization_or_raise(db, organization_id)
        await db.delete(organization)
        await db.commit()

    @staticmethod
    async def get_organization(
        db: AsyncSession, organization_id, actor_id
    ) -> Organization:
        """Fetch an organization the actor is a member of.

        Args:
            db: The active database session.
            organization_id: The organization's id.
            actor_id: The id of the requesting user.

        Returns:
            The `Organization`.

        Raises:
            OrganizationNotFoundError: If the organization does not
                exist or the actor is not a member.
        """
        await _require_membership(db, organization_id, actor_id)
        return await _get_organization_or_raise(db, organization_id)

    @staticmethod
    async def list_user_organizations(db: AsyncSession, user_id) -> list[Organization]:
        """List all organizations a user is a member of.

        Args:
            db: The active database session.
            user_id: The user's id.

        Returns:
            A list of `Organization` instances, ordered by creation
            time.
        """
        result = await db.execute(
            select(Organization)
            .join(Membership, Membership.organization_id == Organization.id)
            .where(Membership.user_id == user_id)
            .order_by(Organization.created_at)
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_members(
        db: AsyncSession, organization_id, actor_id
    ) -> list[Membership]:
        """List all members of an organization.

        Args:
            db: The active database session.
            organization_id: The organization's id.
            actor_id: The id of the requesting user.

        Returns:
            A list of `Membership` instances, ordered by creation time.

        Raises:
            OrganizationNotFoundError: If the organization does not
                exist or the actor is not a member.
        """
        await _require_membership(db, organization_id, actor_id)

        result = await db.execute(
            select(Membership)
            .where(Membership.organization_id == organization_id)
            .order_by(Membership.created_at)
        )
        return list(result.scalars().all())

    @staticmethod
    async def add_member(
        db: AsyncSession,
        organization_id,
        actor_id,
        target_user_id,
        role: MembershipRole,
    ) -> Membership:
        """Directly add an existing user to an organization.

        Args:
            db: The active database session.
            organization_id: The organization's id.
            actor_id: The id of the user performing the action.
            target_user_id: The id of the user to add.
            role: The role to grant the new member.

        Returns:
            The newly created `Membership`.

        Raises:
            OrganizationNotFoundError: If the organization does not
                exist or the actor is not a member.
            InsufficientPermissionsError: If the actor is not an owner
                or admin.
            TargetUserNotFoundError: If the target user does not exist.
            UserAlreadyMemberError: If the target user is already a
                member.
        """
        membership = await _require_membership(db, organization_id, actor_id)
        _require_role(membership, {MembershipRole.OWNER, MembershipRole.ADMIN})

        target_user = await db.get(User, target_user_id)
        if target_user is None:
            raise TargetUserNotFoundError("User not found.")

        existing = await _get_membership(db, organization_id, target_user_id)
        if existing is not None:
            raise UserAlreadyMemberError(
                "This user is already a member of the organization."
            )

        new_membership = Membership(
            organization_id=organization_id,
            user_id=target_user_id,
            role=role,
        )
        db.add(new_membership)
        await db.commit()
        await db.refresh(new_membership)
        return new_membership

    @staticmethod
    async def remove_member(
        db: AsyncSession, organization_id, actor_id, target_user_id
    ) -> None:
        """Remove a member from an organization.

        A member may always remove themselves (leave the organization).
        Removing a different member requires owner or admin privileges.
        The last remaining owner can never be removed.

        Args:
            db: The active database session.
            organization_id: The organization's id.
            actor_id: The id of the user performing the removal.
            target_user_id: The id of the user to remove.

        Raises:
            OrganizationNotFoundError: If the organization does not
                exist or the actor is not a member.
            InsufficientPermissionsError: If the actor is neither the
                target nor an owner/admin.
            NotAMemberError: If the target user is not a member of the
                organization.
            LastOwnerError: If the target is the organization's last
                remaining owner.
        """
        actor_membership = await _require_membership(db, organization_id, actor_id)

        if actor_id != target_user_id:
            _require_role(actor_membership, {MembershipRole.OWNER, MembershipRole.ADMIN})
            target_membership = await _get_membership(db, organization_id, target_user_id)
            if target_membership is None:
                raise NotAMemberError("This user is not a member of the organization.")
        else:
            target_membership = actor_membership

        if target_membership.role == MembershipRole.OWNER:
            owner_count = await _count_owners(db, organization_id)
            if owner_count <= 1:
                raise LastOwnerError(
                    "Cannot remove the organization's last remaining owner."
                )

        await db.delete(target_membership)
        await db.commit()

    @staticmethod
    async def change_role(
        db: AsyncSession,
        organization_id,
        actor_id,
        target_user_id,
        new_role: MembershipRole,
    ) -> Membership:
        """Change a member's role within an organization.

        Only owners may change roles, to prevent privilege escalation
        by admins. The last remaining owner cannot be demoted.

        Args:
            db: The active database session.
            organization_id: The organization's id.
            actor_id: The id of the user performing the change.
            target_user_id: The id of the member whose role is changing.
            new_role: The role to assign.

        Returns:
            The updated `Membership`.

        Raises:
            OrganizationNotFoundError: If the organization does not
                exist or the actor is not a member.
            InsufficientPermissionsError: If the actor is not an owner.
            NotAMemberError: If the target user is not a member of the
                organization.
            LastOwnerError: If the change would demote the
                organization's last remaining owner.
        """
        actor_membership = await _require_membership(db, organization_id, actor_id)
        _require_role(actor_membership, {MembershipRole.OWNER})

        target_membership = await _get_membership(db, organization_id, target_user_id)
        if target_membership is None:
            raise NotAMemberError("This user is not a member of the organization.")

        if (
            target_membership.role == MembershipRole.OWNER
            and new_role != MembershipRole.OWNER
        ):
            owner_count = await _count_owners(db, organization_id)
            if owner_count <= 1:
                raise LastOwnerError(
                    "Cannot change the role of the organization's last "
                    "remaining owner."
                )

        target_membership.role = new_role
        await db.commit()
        await db.refresh(target_membership)
        return target_membership

    @staticmethod
    async def invite_member(
        db: AsyncSession,
        organization_id,
        actor_id,
        email: str,
        role: MembershipRole,
    ) -> OrganizationInvitation:
        """Create an invitation for an email to join an organization.

        Args:
            db: The active database session.
            organization_id: The organization's id.
            actor_id: The id of the user issuing the invitation.
            email: The email address to invite.
            role: The role the invitee will receive upon acceptance.

        Returns:
            The newly created `OrganizationInvitation`.

        Raises:
            OrganizationNotFoundError: If the organization does not
                exist or the actor is not a member.
            InsufficientPermissionsError: If the actor is not an owner
                or admin.
        """
        membership = await _require_membership(db, organization_id, actor_id)
        _require_role(membership, {MembershipRole.OWNER, MembershipRole.ADMIN})

        invitation = OrganizationInvitation(
            organization_id=organization_id,
            email=email.strip().lower(),
            role=role,
            token=secrets.token_urlsafe(INVITATION_TOKEN_BYTES),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=INVITATION_EXPIRE_DAYS),
        )
        db.add(invitation)
        await db.commit()
        await db.refresh(invitation)
        return invitation

    @staticmethod
    async def list_invitations(
        db: AsyncSession, organization_id, actor_id
    ) -> list[OrganizationInvitation]:
        """List all invitations issued by an organization.

        Args:
            db: The active database session.
            organization_id: The organization's id.
            actor_id: The id of the requesting user.

        Returns:
            A list of `OrganizationInvitation` instances, most recent
            first.

        Raises:
            OrganizationNotFoundError: If the organization does not
                exist or the actor is not a member.
            InsufficientPermissionsError: If the actor is not an owner
                or admin.
        """
        membership = await _require_membership(db, organization_id, actor_id)
        _require_role(membership, {MembershipRole.OWNER, MembershipRole.ADMIN})

        result = await db.execute(
            select(OrganizationInvitation)
            .where(OrganizationInvitation.organization_id == organization_id)
            .order_by(OrganizationInvitation.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def accept_invitation(
        db: AsyncSession, token: str, current_user: User
    ) -> Membership:
        """Accept an organization invitation on behalf of the current user.

        Args:
            db: The active database session.
            token: The invitation token being redeemed.
            current_user: The authenticated user accepting the
                invitation.

        Returns:
            The newly created `Membership`.

        Raises:
            InvitationNotFoundError: If no invitation matches the token.
            InvitationAlreadyAcceptedError: If the invitation has
                already been accepted.
            InvitationExpiredError: If the invitation has expired.
            InvitationEmailMismatchError: If the current user's email
                does not match the invitation's target email.
            UserAlreadyMemberError: If the current user is already a
                member of the organization.
        """
        result = await db.execute(
            select(OrganizationInvitation).where(OrganizationInvitation.token == token)
        )
        invitation = result.scalar_one_or_none()

        if invitation is None:
            raise InvitationNotFoundError("Invitation not found.")

        if invitation.accepted_at is not None:
            raise InvitationAlreadyAcceptedError(
                "This invitation has already been accepted."
            )

        if invitation.expires_at < datetime.now(timezone.utc):
            raise InvitationExpiredError("This invitation has expired.")

        if invitation.email != current_user.email.strip().lower():
            raise InvitationEmailMismatchError(
                "This invitation was issued to a different email address."
            )

        existing = await _get_membership(
            db, invitation.organization_id, current_user.id
        )
        if existing is not None:
            raise UserAlreadyMemberError(
                "You are already a member of this organization."
            )

        membership = Membership(
            organization_id=invitation.organization_id,
            user_id=current_user.id,
            role=invitation.role,
        )
        db.add(membership)
        invitation.accepted_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(membership)
        return membership