"""Pydantic schemas for the AI due diligence copilot."""

import uuid

from pydantic import BaseModel, Field

from app.schemas.chat import ChatSource

__all__ = ["DueDiligenceRequest", "DueDiligenceSection", "DueDiligenceResponse"]


class DueDiligenceRequest(BaseModel):
    """Optional parameters for generating a due diligence report.

    Attributes:
        top_k: The maximum number of retrieved document excerpts to use
            as additional context (1-20). Defaults to 8 — higher than
            chat's default of 5, since a full report benefits from
            broader coverage of the source document.
    """

    top_k: int = Field(default=8, ge=1, le=20)


class DueDiligenceSection(BaseModel):
    """A single named section of a due diligence report.

    Attributes:
        title: The section's display name (e.g. "Executive Summary").
        content: The section's generated content. States explicitly
            when supporting evidence was not available, rather than
            being left blank or fabricated.
    """

    title: str
    content: str


class DueDiligenceResponse(BaseModel):
    """Complete due diligence report for a single document.

    Attributes:
        document_id: The id of the analyzed document.
        sections: The report's sections, in a fixed, consistent order.
        sources: The document excerpts retrieved and used as
            supporting evidence. Reuses `ChatSource` from the chat
            layer, since it already models exactly what's needed here:
            document id, chunk index, similarity score, and snippet.
        model_used: The identifier of the model that generated the
            report.
    """

    document_id: uuid.UUID
    sections: list[DueDiligenceSection]
    sources: list[ChatSource]
    model_used: str