"""Regression test for Evidence Layer Bug B.

Before this fix, `GET /documents/{id}/coverage` and
`GET /documents/{id}/missing-information` were two independent
reimplementations of the same "what fields did we find on this
document" computation: the coverage endpoint did a real (if
convoluted — see the removed `if False else None` dead code)
`DocumentAnalysis` lookup, while the missing-information endpoint
hardcoded `company_fields_found`/`market_fields_found` to empty sets
regardless of what was actually extracted. The result: a document with
a fully populated `DocumentAnalysis` could show "Company Overview: 8/8"
on Coverage while Missing Information simultaneously listed all 8 of
those same fields as missing.

This test drives both endpoint functions directly (not through HTTP —
these are plain async functions, and dependency-injected `db`/
`current_user` are simply passed explicitly) against one document with
a populated `DocumentAnalysis`, and asserts they report the identical
found/missing set for every company and market field. It must fail
against the pre-fix implementation and pass against
`EvidenceService`-backed one.
"""

import pytest

from app.api.v1.documents import get_document_coverage, get_document_missing_information
from app.models.document_analysis import DocumentAnalysis
from app.services.coverage_service import REQUIRED_COMPANY_FIELDS, REQUIRED_MARKET_FIELDS


@pytest.mark.asyncio(loop_scope="session")
class TestCoverageMissingInformationConsistency:
    async def test_populated_analysis_agrees_between_coverage_and_missing_information(
        self, db_session, marketgo_document, integration_user
    ):
        document_id = marketgo_document.id

        analysis = DocumentAnalysis(
            document_id=document_id,
            company_name="MarketGo",
            industry="E-commerce",
            business_model="Marketplace",
            summary="A growing e-commerce marketplace with strong revenue growth.",
            key_products=["Marketplace platform"],
            revenue_streams=["Transaction fees"],
            customers=["Online shoppers"],
            competitors=["Shopify", "BigCommerce"],
            risks=None,
            opportunities=None,
            raw_json={},
        )
        db_session.add(analysis)
        await db_session.commit()

        coverage = await get_document_coverage(document_id, db_session, integration_user)
        missing_info = await get_document_missing_information(document_id, db_session, integration_user)

        company_missing = next(c for c in missing_info.by_category if c.category == "company")
        market_missing = next(c for c in missing_info.by_category if c.category == "market")

        # All 8 REQUIRED_COMPANY_FIELDS were populated above, so Coverage
        # must show 8/8 found...
        assert coverage.coverage["company"].found == len(REQUIRED_COMPANY_FIELDS)
        assert coverage.coverage["company"].required == len(REQUIRED_COMPANY_FIELDS)
        # ...and Missing-Information must agree that NONE of those same
        # fields are missing. Against the pre-fix code, this failed:
        # company_missing.missing listed all 8 fields regardless of
        # coverage.coverage["company"].found == 8.
        assert company_missing.missing == []
        for field_name in REQUIRED_COMPANY_FIELDS:
            assert field_name not in company_missing.missing, (
                f"{field_name!r} found by Coverage but reported missing by Missing-Information"
            )

        # Market: no REQUIRED_MARKET_FIELDS-only data exists on this
        # document (only "competitors" is populated, and it resolves to
        # the "company" category — see evidence_service.py's
        # _ANALYSIS_FIELD_CATEGORY). Both endpoints must agree it's 0/4,
        # not just individually be internally consistent.
        assert coverage.coverage["market"].found == 0
        assert set(market_missing.missing) == set(REQUIRED_MARKET_FIELDS)

    async def test_document_with_no_analysis_agrees_everything_is_missing(
        self, db_session, marketgo_document, integration_user
    ):
        """No DocumentAnalysis row at all (e.g. a freshly processed,
        not-yet-analyzed document) must not be treated differently by
        the two endpoints either."""
        document_id = marketgo_document.id

        coverage = await get_document_coverage(document_id, db_session, integration_user)
        missing_info = await get_document_missing_information(document_id, db_session, integration_user)

        company_missing = next(c for c in missing_info.by_category if c.category == "company")

        assert coverage.coverage["company"].found == 0
        assert set(company_missing.missing) == set(REQUIRED_COMPANY_FIELDS)
