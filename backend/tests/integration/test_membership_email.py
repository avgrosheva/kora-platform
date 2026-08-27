"""Regression test: the Members page showed a truncated user_id (UUID)
instead of an email, because `MembershipRead` had no `email` field at
all. The fix adds `email` to `MembershipRead`, derived from
`Membership.user.email` via a `model_validator`, and makes sure every
service method that returns a `Membership` destined to become a
`MembershipRead` has `.user` already populated -- either through a
real SQL join (`list_members`) or by assigning an already-fetched
`User` onto the relationship (`add_member`, `accept_invitation`), or a
targeted refresh (`change_role`).

This is a case where a mocked test proves nothing: the bug this
guards against is `.user` not being loaded, which only manifests as a
real `MissingGreenlet` error under SQLAlchemy's async engine when a
relationship is lazy-loaded outside an awaited context. These tests
run against the real (throwaway) database for that reason.
"""

import uuid

import pytest
import pytest_asyncio

from app.core.security import hash_password
from app.models.organization import MembershipRole
from app.models.user import User
from app.schemas.organization import MembershipRead
from app.services.organization_service import OrganizationService


@pytest_asyncio.fixture(loop_scope="session")
async def second_user(db_session):
    """A second throwaway user, distinct from `integration_user`, to
    add/mutate as a member of `integration_org`."""
    user = User(
        email=f"integration-test-member-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=hash_password("integration-test-password"),
        full_name="Second Integration Test User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    yield user

    await db_session.delete(user)
    await db_session.commit()


@pytest.mark.asyncio(loop_scope="session")
class TestMembershipReadHasEmail:
    async def test_list_members_returns_correct_emails_via_a_single_join(
        self, db_session, integration_org, integration_user, second_user
    ):
        await OrganizationService.add_member(
            db_session, integration_org.id, integration_user.id, second_user.id, MembershipRole.MEMBER
        )

        members = await OrganizationService.list_members(db_session, integration_org.id, integration_user.id)
        assert len(members) == 2

        # Must not raise MissingGreenlet -- .user is eager-loaded by the join.
        reads = {m.user_id: MembershipRead.model_validate(m) for m in members}
        assert reads[integration_user.id].email == integration_user.email
        assert reads[second_user.id].email == second_user.email

    async def test_add_member_response_has_the_new_members_email(
        self, db_session, integration_org, integration_user, second_user
    ):
        membership = await OrganizationService.add_member(
            db_session, integration_org.id, integration_user.id, second_user.id, MembershipRole.MEMBER
        )
        read = MembershipRead.model_validate(membership)
        assert read.email == second_user.email

    async def test_change_role_response_has_the_targets_email(
        self, db_session, integration_org, integration_user, second_user
    ):
        await OrganizationService.add_member(
            db_session, integration_org.id, integration_user.id, second_user.id, MembershipRole.MEMBER
        )
        membership = await OrganizationService.change_role(
            db_session, integration_org.id, integration_user.id, second_user.id, MembershipRole.ADMIN
        )
        read = MembershipRead.model_validate(membership)
        assert read.email == second_user.email
        assert read.role == MembershipRole.ADMIN
