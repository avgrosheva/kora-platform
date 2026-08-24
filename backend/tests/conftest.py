"""Shared pytest fixtures for integration tests.

Provides a real async database session against the configured dev
database, plus helper fixtures to create and tear down a throwaway
user/organization/document for each integration test — never touching
existing data, and always cleaned up via fixture teardown regardless
of test outcome.
"""

import uuid

import pytest_asyncio

from app.core.security import hash_password
from app.db.session import get_sessionmaker
from app.models.document import Document, DocumentStatus
from app.models.organization import Membership, MembershipRole, Organization
from app.models.user import User


@pytest_asyncio.fixture(loop_scope="session")
async def db_session():
    """Yield a real AsyncSession against the configured database."""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        yield session


@pytest_asyncio.fixture(loop_scope="session")
async def integration_user(db_session):
    """Create a throwaway user, deleted after the test."""
    user = User(
        email=f"integration-test-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=hash_password("integration-test-password"),
        full_name="Integration Test User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    yield user

    await db_session.delete(user)
    await db_session.commit()


@pytest_asyncio.fixture(loop_scope="session")
async def integration_org(db_session, integration_user):
    """Create a throwaway organization owned by `integration_user`."""
    org = Organization(name=f"MarketGo Test Org {uuid.uuid4().hex[:8]}", slug=f"marketgo-test-{uuid.uuid4().hex[:8]}")
    db_session.add(org)
    await db_session.flush()

    membership = Membership(organization_id=org.id, user_id=integration_user.id, role=MembershipRole.OWNER)
    db_session.add(membership)
    await db_session.commit()
    await db_session.refresh(org)

    yield org

    await db_session.delete(org)
    await db_session.commit()


@pytest_asyncio.fixture(loop_scope="session")
async def marketgo_document(db_session, integration_org, integration_user):
    """Create a throwaway, already-processed document seeded with MarketGo text."""
    document = Document(
        organization_id=integration_org.id,
        uploaded_by=integration_user.id,
        filename="marketgo-integration-test.txt",
        original_filename="marketgo.pdf",
        content_type="text/plain",
        size_bytes=1000,
        storage_key=f"integration-test/{uuid.uuid4().hex}.txt",
        status=DocumentStatus.COMPLETED,
        text_content=(
            "MarketGo is an e-commerce marketplace. Revenue grew from $24M in 2023 "
            "to $58M in 2024 to $96M in 2025. Gross margin improved from 22$%$ in 2024 "
            "to 29$%$ in 2025. EBITDA moved from -$6M in 2024 to +$8M in 2025. Net "
            "income was $3.5M in 2025. Cash on hand is $18M. Operating expenses were "
            "$88M in 2025. CAC improved from $27 to $21. LTV is estimated at around "
            "$170, giving an LTV/CAC ratio of 8.1x. Orders grew from 8.7M to 14.5M. "
            "AOV rose from $31 to $34. The platform has 2.8M registered customers "
            "and 620K monthly active users. MarketGo raised $45M in its Series B at "
            "a $280M post-money valuation."
        ),
    )
    db_session.add(document)
    await db_session.commit()
    await db_session.refresh(document)

    yield document

    await db_session.delete(document)
    await db_session.commit()