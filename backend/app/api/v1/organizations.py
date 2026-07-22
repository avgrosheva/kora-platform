"""Organization API routes.

Routers stay thin: they parse requests, delegate to `OrganizationService`,
and translate domain exceptions into HTTP responses. No business logic
lives here.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_active_user
from app.config import get_settings
from app.db.dependencies import get_db
from app.models.organization import Membership, Organization, OrganizationInvitation
from app.models.user import User
from app.schemas.organization import (
    AddMemberRequest,
    ChangeRoleRequest,
    InvitationCreate,
    InvitationRead,
    MembershipRead,
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)
from app.services.organization_service import (
    InsufficientPermissionsError,
    InvitationAlreadyAcceptedError,
    InvitationEmailMismatchError,
    InvitationExpiredError,
    InvitationNotFoundError,
    LastOwnerError,
    NotAMemberError,
    OrganizationNotFoundError,
    OrganizationService,
    SlugAlreadyExistsError,
    TargetUserNotFoundError,
    UserAlreadyMemberError,
)

settings = get_settings()

router = APIRouter(
    prefix=f"{settings.API_V1_PREFIX}/organizations",
    tags=["organizations"],
)


@router.post(
    "",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new organization",
)
async def create_organization(
    payload: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Organization:
    """Create a new organization owned by the current user.

    Args:
        payload: The organization's name and optional slug.
        db: The request-scoped database session.
        current_user: The authenticated user, who becomes the owner.

    Returns:
        The newly created organization.

    Raises:
        HTTPException: With status 409 if the requested slug is already
            in use.
    """
    try:
        return await OrganizationService.create_organization(
            db=db,
            owner_id=current_user.id,
            name=payload.name,
            slug=payload.slug,
        )
    except SlugAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.get(
    "",
    response_model=list[OrganizationRead],
    summary="List the current user's organizations",
)
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[Organization]:
    """List all organizations the current user is a member of.

    Args:
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The user's organizations.
    """
    return await OrganizationService.list_user_organizations(
        db=db, user_id=current_user.id
    )


@router.get(
    "/{organization_id}",
    response_model=OrganizationRead,
    summary="Get an organization by id",
)
async def get_organization(
    organization_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Organization:
    """Fetch a single organization the current user belongs to.

    Args:
        organization_id: The organization's id.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The requested organization.

    Raises:
        HTTPException: With status 404 if the organization does not
            exist or the user is not a member of it.
    """
    try:
        return await OrganizationService.get_organization(
            db=db, organization_id=organization_id, actor_id=current_user.id
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.patch(
    "/{organization_id}",
    response_model=OrganizationRead,
    summary="Update an organization",
)
async def update_organization(
    organization_id: str,
    payload: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Organization:
    """Update an organization's name and/or slug.

    Args:
        organization_id: The organization's id.
        payload: The fields to update.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The updated organization.

    Raises:
        HTTPException: With status 404 if the organization does not
            exist or the user is not a member; 403 if the user is not
            an owner or admin; 409 if the new slug is already in use.
    """
    try:
        return await OrganizationService.update_organization(
            db=db,
            organization_id=organization_id,
            actor_id=current_user.id,
            name=payload.name,
            slug=payload.slug,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except InsufficientPermissionsError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except SlugAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.delete(
    "/{organization_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an organization",
)
async def delete_organization(
    organization_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Delete an organization. Only an owner may perform this action.

    Args:
        organization_id: The organization's id.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Raises:
        HTTPException: With status 404 if the organization does not
            exist or the user is not a member; 403 if the user is not
            an owner.
    """
    try:
        await OrganizationService.delete_organization(
            db=db, organization_id=organization_id, actor_id=current_user.id
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except InsufficientPermissionsError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc


@router.get(
    "/{organization_id}/members",
    response_model=list[MembershipRead],
    summary="List an organization's members",
)
async def list_members(
    organization_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[Membership]:
    """List all members of an organization.

    Args:
        organization_id: The organization's id.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The organization's memberships.

    Raises:
        HTTPException: With status 404 if the organization does not
            exist or the user is not a member.
    """
    try:
        return await OrganizationService.list_members(
            db=db, organization_id=organization_id, actor_id=current_user.id
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.post(
    "/{organization_id}/members",
    response_model=MembershipRead,
    status_code=status.HTTP_201_CREATED,
    summary="Directly add an existing user to an organization",
)
async def add_member(
    organization_id: str,
    payload: AddMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Membership:
    """Add an existing user directly to an organization.

    Args:
        organization_id: The organization's id.
        payload: The target user's id and role.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The newly created membership.

    Raises:
        HTTPException: With status 404 if the organization does not
            exist, the user is not a member, or the target user does
            not exist; 403 if the user is not an owner or admin; 409 if
            the target user is already a member.
    """
    try:
        return await OrganizationService.add_member(
            db=db,
            organization_id=organization_id,
            actor_id=current_user.id,
            target_user_id=payload.user_id,
            role=payload.role,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except InsufficientPermissionsError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except TargetUserNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except UserAlreadyMemberError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.delete(
    "/{organization_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a member from an organization",
)
async def remove_member(
    organization_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Remove a member from an organization, or leave it yourself.

    Args:
        organization_id: The organization's id.
        user_id: The id of the member to remove.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Raises:
        HTTPException: With status 404 if the organization does not
            exist, the actor is not a member, or the target is not a
            member; 403 if the actor lacks permission; 409 if this
            would remove the organization's last owner.
    """
    try:
        await OrganizationService.remove_member(
            db=db,
            organization_id=organization_id,
            actor_id=current_user.id,
            target_user_id=user_id,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except InsufficientPermissionsError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except NotAMemberError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except LastOwnerError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.patch(
    "/{organization_id}/members/{user_id}",
    response_model=MembershipRead,
    summary="Change a member's role",
)
async def change_role(
    organization_id: str,
    user_id: str,
    payload: ChangeRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Membership:
    """Change a member's role within an organization.

    Only an owner may perform this action.

    Args:
        organization_id: The organization's id.
        user_id: The id of the member whose role is changing.
        payload: The new role.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The updated membership.

    Raises:
        HTTPException: With status 404 if the organization does not
            exist, the actor is not a member, or the target is not a
            member; 403 if the actor is not an owner; 409 if this would
            demote the organization's last owner.
    """
    try:
        return await OrganizationService.change_role(
            db=db,
            organization_id=organization_id,
            actor_id=current_user.id,
            target_user_id=user_id,
            new_role=payload.role,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except InsufficientPermissionsError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except NotAMemberError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except LastOwnerError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.post(
    "/{organization_id}/invitations",
    response_model=InvitationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a new member by email",
)
async def invite_member(
    organization_id: str,
    payload: InvitationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> OrganizationInvitation:
    """Invite an email address to join an organization.

    Args:
        organization_id: The organization's id.
        payload: The invitee's email and intended role.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The newly created invitation.

    Raises:
        HTTPException: With status 404 if the organization does not
            exist or the user is not a member; 403 if the user is not
            an owner or admin.
    """
    try:
        return await OrganizationService.invite_member(
            db=db,
            organization_id=organization_id,
            actor_id=current_user.id,
            email=payload.email,
            role=payload.role,
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except InsufficientPermissionsError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc


@router.get(
    "/{organization_id}/invitations",
    response_model=list[InvitationRead],
    summary="List an organization's pending invitations",
)
async def list_invitations(
    organization_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[OrganizationInvitation]:
    """List all invitations issued by an organization.

    Args:
        organization_id: The organization's id.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The organization's invitations, most recent first.

    Raises:
        HTTPException: With status 404 if the organization does not
            exist or the user is not a member; 403 if the user is not
            an owner or admin.
    """
    try:
        return await OrganizationService.list_invitations(
            db=db, organization_id=organization_id, actor_id=current_user.id
        )
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except InsufficientPermissionsError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc


@router.post(
    "/invitations/{token}/accept",
    response_model=MembershipRead,
    summary="Accept an organization invitation",
)
async def accept_invitation(
    token: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Membership:
    """Accept an invitation on behalf of the current user.

    Args:
        token: The invitation token.
        db: The request-scoped database session.
        current_user: The authenticated user accepting the invitation.

    Returns:
        The newly created membership.

    Raises:
        HTTPException: With status 404 if the token does not match any
            invitation; 410 if the invitation has expired; 409 if the
            invitation was already accepted or the user is already a
            member; 403 if the invitation was issued to a different
            email address.
    """
    try:
        return await OrganizationService.accept_invitation(
            db=db, token=token, current_user=current_user
        )
    except InvitationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except InvitationExpiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_410_GONE, detail=str(exc)
        ) from exc
    except InvitationAlreadyAcceptedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except InvitationEmailMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc
    except UserAlreadyMemberError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc