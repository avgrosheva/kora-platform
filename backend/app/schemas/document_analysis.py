"""Pydantic schemas for AI-generated document analyses."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class DocumentAnalysisCreate(BaseModel):
    """Internal DTO for persisting an analysis, shaped for the database.

    Built by `DocumentAnalysisService` from a validated `AIAnalysisResult`
    (see `app.services.ai_service`), mapping the AI's field names to the
    database's field names. Not exposed directly as an API request body —
    `POST /documents/{id}/analyze` takes no body, since the input is the
    document's already-stored `text_content`, not user-supplied data.

    Attributes:
        summary: A brief natural-language summary of the document.
        company_name: The company's name, or `None` if not identifiable.
        industry: The company's industry, or `None` if not identifiable.
        business_model: The company's business model, or `None` if not
            identifiable.
        key_products: The company's key products or services, or `None`.
        risks: The company's main risks, or `None`.
        opportunities: Growth opportunities, or `None`.
        revenue_streams: The company's revenue streams, or `None`.
        customers: The company's target customers, or `None`.
        competitors: The company's competitors, or `None`.
        raw_json: The complete, validated AI response.
    """

    summary: str | None
    company_name: str | None
    industry: str | None
    business_model: str | None
    key_products: list[str] | None
    risks: list[str] | None
    opportunities: list[str] | None
    revenue_streams: list[str] | None
    customers: list[str] | None
    competitors: list[str] | None
    raw_json: dict[str, Any]


class DocumentAnalysisRead(BaseModel):
    """Public representation of a document's AI-generated analysis.

    Attributes:
        id: The analysis's unique identifier.
        document_id: The analyzed document's id.
        summary: A brief natural-language summary of the document.
        company_name: The company's name, or `None` if not identifiable.
        industry: The company's industry, or `None` if not identifiable.
        business_model: The company's business model, or `None` if not
            identifiable.
        key_products: The company's key products or services, or `None`.
        risks: The company's main risks, or `None`.
        opportunities: Growth opportunities, or `None`.
        revenue_streams: The company's revenue streams, or `None`.
        customers: The company's target customers, or `None`.
        competitors: The company's competitors, or `None`.
        created_at: Timestamp when the analysis was first created.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    summary: str | None
    company_name: str | None
    industry: str | None
    business_model: str | None
    key_products: list[str] | None
    risks: list[str] | None
    opportunities: list[str] | None
    revenue_streams: list[str] | None
    customers: list[str] | None
    competitors: list[str] | None
    created_at: datetime