"""Database models package.

Importing this package ensures all ORM models are registered on
`Base.metadata`, which is required for Alembic autogeneration to detect
them.
"""

from app.models.coverage_assessment import CoverageAssessment
from app.models.derived_metric import DerivedMetric
from app.models.document import Document
from app.models.document_analysis import DocumentAnalysis
from app.models.document_embedding import DocumentEmbedding
from app.models.financial_fact import FinancialFact
from app.models.financial_metrics import FinancialMetrics
from app.models.investment_score import InvestmentScore
from app.models.missing_information_item import MissingInformationItem
from app.models.organization import Membership, Organization, OrganizationInvitation
from app.models.source_citation import SourceCitation
from app.models.user import User
from app.models.validation_finding import ValidationFinding

__all__ = [
    "User",
    "Organization",
    "Membership",
    "OrganizationInvitation",
    "Document",
    "DocumentAnalysis",
    "FinancialMetrics",
    "InvestmentScore",
    "DocumentEmbedding",
    "FinancialFact",
    "SourceCitation",
    "ValidationFinding",
    "CoverageAssessment",
    "MissingInformationItem",
    "DerivedMetric",
]