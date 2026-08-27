"""Regression test for the portfolio-widening added for the visual
redesign: `GET /portfolio` now also returns `documents` (every company
profile, with per-document score/coverage/open-findings) and
`summary.average_coverage`.

The open-findings count is the sensitive part -- it re-derives
`FindingsService.get_findings`'s three-source, per-document logic as
aggregate SQL so it scales with an org's document list. This test seeds
one document with a finding from each of the three sources (a
deterministic `ValidationFinding`, a document-stated `QualitativeFact`
with a severity_hint, and a `QualitativeFact` in a category with a
registered inference rule) and checks the collapsed high/medium/low
counts match what `FindingsService.get_findings` would produce for the
same document, one finding at a time.
"""

import uuid

import pytest

from app.models.coverage_assessment import CoverageAssessment
from app.models.document_analysis import DocumentAnalysis
from app.models.investment_score import InvestmentScore
from app.models.qualitative_fact import (
    QualitativeFact,
    QualitativeFactCategory,
    QualitativeFactType,
)
from app.models.validation_finding import FindingSeverity as ValidationSeverity
from app.models.validation_finding import ValidationFinding
from app.services.portfolio_service import PortfolioService


@pytest.mark.asyncio(loop_scope="session")
class TestPortfolioDocumentsAndFindings:
    async def test_document_row_and_open_findings_across_all_three_sources(
        self, db_session, integration_org, integration_user, marketgo_document
    ):
        document_id = marketgo_document.id

        db_session.add(
            DocumentAnalysis(
                document_id=document_id,
                company_name="MarketGo",
                raw_json={},
            )
        )
        db_session.add(
            InvestmentScore(document_id=document_id, overall_score=72.0)
        )
        db_session.add(
            CoverageAssessment(
                document_id=document_id,
                overall_confidence=0.815,
                coverage={},
                source_coverage=0.5,
            )
        )
        # Source 1: deterministic -- CRITICAL collapses to "high".
        db_session.add(
            ValidationFinding(
                document_id=document_id,
                severity=ValidationSeverity.CRITICAL.value,
                category="financial_consistency",
                title="EBITDA exceeds revenue",
                description="test",
            )
        )
        # Source 2: document-stated -- severity_hint "medium", category
        # with NO registered inference rule, so this contributes only
        # to the document-stated count, not a second AI-inferred one.
        db_session.add(
            QualitativeFact(
                document_id=document_id,
                category=QualitativeFactCategory.CUSTOMER_RISK.value,
                claim_text="Top customer is 40% of revenue.",
                fact_type=QualitativeFactType.DOCUMENT_STATED.value,
                severity_hint="medium",
            )
        )
        # Source 3: AI-inferred -- category has a registered rule
        # (team_risk), severity_hint "low" -> the rule's finding is
        # ALSO "low", and this same fact independently produces a
        # document-stated "low" finding too (both sources read the
        # same row).
        db_session.add(
            QualitativeFact(
                document_id=document_id,
                category=QualitativeFactCategory.TEAM_RISK.value,
                claim_text="Founder is the sole engineer.",
                fact_type=QualitativeFactType.DOCUMENT_STATED.value,
                severity_hint="low",
            )
        )
        await db_session.commit()

        response = await PortfolioService.get_portfolio(db_session, integration_org.id, integration_user.id)

        assert response.summary.average_coverage == pytest.approx(81.5)

        assert len(response.documents) == 1
        row = response.documents[0]
        assert row.document_id == document_id
        assert row.company_name == "MarketGo"
        assert row.overall_score == 72.0
        assert row.coverage_percent == 82  # round(0.815 * 100)

        # high: 1 deterministic critical.
        # medium: 1 document-stated (customer_risk, no inference rule).
        # low: 1 document-stated (team_risk) + 1 AI-inferred (team_risk rule) = 2.
        assert row.open_findings == {"high": 1, "medium": 1, "low": 2}

    async def test_document_with_no_findings_is_absent_from_the_mapping(
        self, db_session, integration_org, integration_user, marketgo_document
    ):
        db_session.add(
            DocumentAnalysis(document_id=marketgo_document.id, raw_json={})
        )
        await db_session.commit()

        response = await PortfolioService.get_portfolio(db_session, integration_org.id, integration_user.id)

        assert len(response.documents) == 1
        assert response.documents[0].open_findings == {}
        assert response.documents[0].coverage_percent is None
        assert response.documents[0].overall_score is None

    async def test_a_second_organizations_findings_never_leak_in(
        self, db_session, integration_user, integration_org, marketgo_document
    ):
        """Guards the JOIN-through-Document scoping in
        _fetch_open_findings_by_document -- a finding on a document in
        a different org must never count toward this org's rows."""
        from app.models.document import Document, DocumentStatus
        from app.models.organization import Membership, MembershipRole, Organization

        db_session.add(DocumentAnalysis(document_id=marketgo_document.id, raw_json={}))
        await db_session.commit()

        other_org = Organization(name=f"Other org {uuid.uuid4().hex[:8]}", slug=f"other-org-{uuid.uuid4().hex[:8]}")
        db_session.add(other_org)
        await db_session.flush()
        db_session.add(Membership(organization_id=other_org.id, user_id=integration_user.id, role=MembershipRole.OWNER))
        other_document = Document(
            organization_id=other_org.id,
            uploaded_by=integration_user.id,
            filename="other.txt",
            original_filename="other.pdf",
            content_type="text/plain",
            size_bytes=10,
            storage_key=f"integration-test/{uuid.uuid4().hex}.txt",
            status=DocumentStatus.COMPLETED,
            text_content="Other org's document.",
        )
        db_session.add(other_document)
        await db_session.flush()
        db_session.add(DocumentAnalysis(document_id=other_document.id, raw_json={}))
        db_session.add(
            ValidationFinding(
                document_id=other_document.id,
                severity=ValidationSeverity.CRITICAL.value,
                category="financial_consistency",
                title="Should not leak",
                description="test",
            )
        )
        await db_session.commit()

        response = await PortfolioService.get_portfolio(db_session, integration_org.id, integration_user.id)

        assert len(response.documents) == 1
        assert response.documents[0].document_id != other_document.id
        assert response.documents[0].open_findings == {}

        await db_session.delete(other_document)
        await db_session.delete(other_org)
        await db_session.commit()
