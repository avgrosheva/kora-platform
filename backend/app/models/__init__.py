"""Database models package.

Importing this package ensures all ORM models are registered on
`Base.metadata`, which is required for Alembic autogeneration to detect
them.
"""

from app.models.document import Document
from app.models.document_analysis import DocumentAnalysis
from app.models.financial_metrics import FinancialMetrics
from app.models.investment_score import InvestmentScore
from app.models.organization import Membership, Organization, OrganizationInvitation
from app.models.user import User

__all__ = [
    "User",
    "Organization",
    "Membership",
    "OrganizationInvitation",
    "Document",
    "DocumentAnalysis",
    "FinancialMetrics",
    "InvestmentScore",
]