"""OpenAI integration for structured document and financial analysis.

Builds prompts, calls the OpenAI API, and validates responses against
strict JSON schemas. Contains no database access and no document,
organization, or financial-computation logic — those belong to
`DocumentAnalysisService` and `FinancialAnalysisService`, which consume
this module.
"""

import asyncio
import json
from typing import TypeVar

from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)
from pydantic import BaseModel, ConfigDict, ValidationError

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

REQUEST_TIMEOUT_SECONDS = 60.0
MAX_DOCUMENT_CHARACTERS = 15_000
_RETRY_DELAY_SECONDS = 1.0

_T = TypeVar("_T", bound=BaseModel)

_BUSINESS_SYSTEM_PROMPT = """You are a business analyst extracting structured \
information from company documents.

Return ONLY a single valid JSON object with exactly these keys, and no \
others:

{
  "company_name": string or null,
  "industry": string or null,
  "business_model": string or null,
  "summary": string or null,
  "key_products": array of strings or null,
  "revenue_streams": array of strings or null,
  "target_customers": array of strings or null,
  "competitors": array of strings or null,
  "main_risks": array of strings or null,
  "growth_opportunities": array of strings or null
}

Rules:
- If a piece of information is not present in the document, set that \
field to null. Never invent, assume, or infer information that is not \
actually stated in the text.
- Do not include markdown formatting, code fences, or any commentary. \
Return the JSON object only."""

_FINANCIAL_SYSTEM_PROMPT = """You are a financial analyst extracting \
structured financial metrics from company documents.

Return ONLY a single valid JSON object with exactly these keys, and no \
others:

{
  "currency": string or null,
  "revenue": number or null,
  "arr": number or null,
  "mrr": number or null,
  "gross_margin": number or null,
  "ebitda": number or null,
  "burn_rate": number or null,
  "cash": number or null,
  "customers": integer or null,
  "growth_rate": number or null,
  "cac": number or null,
  "ltv": number or null,
  "valuation": number or null
}

Rules:
- "currency" must be an ISO 4217 currency code (e.g. "USD", "EUR") if \
stated, otherwise null.
- All monetary fields are plain numbers with no currency symbols, \
commas, or units (e.g. 1500000, not "$1.5M").
- "gross_margin" and "growth_rate" are percentages expressed as plain \
numbers (e.g. 42.5 for 42.5%), not fractions.
- If a value is not explicitly stated in the document, set it to null. \
Never estimate, infer, or hallucinate a number that is not actually \
present in the text.
- Do not include markdown formatting, code fences, or any commentary. \
Return the JSON object only."""


class AIAnalysisResult(BaseModel):
    """Strict schema for the AI's structured business analysis output.

    Field names mirror the business-analysis prompt's requested JSON
    schema exactly. `DocumentAnalysisService` maps these onto the
    database's field names (e.g. `main_risks` -> `risks`) when
    persisting.

    Attributes:
        company_name: The company's name, or `None` if not stated.
        industry: The company's industry, or `None` if not stated.
        business_model: The company's business model, or `None` if not
            stated.
        summary: A brief natural-language summary, or `None`.
        key_products: The company's key products or services, or
            `None`.
        revenue_streams: The company's revenue streams, or `None`.
        target_customers: The company's target customers, or `None`.
        competitors: The company's competitors, or `None`.
        main_risks: The company's main risks, or `None`.
        growth_opportunities: Growth opportunities, or `None`.
    """

    model_config = ConfigDict(extra="forbid")

    company_name: str | None
    industry: str | None
    business_model: str | None
    summary: str | None
    key_products: list[str] | None
    revenue_streams: list[str] | None
    target_customers: list[str] | None
    competitors: list[str] | None
    main_risks: list[str] | None
    growth_opportunities: list[str] | None


class FinancialExtractionResult(BaseModel):
    """Strict schema for the AI's raw financial extraction output.

    This is the AI's direct output only — derived/computed values
    (`runway_months`, `confidence_score`) are intentionally excluded
    here and computed by `FinancialAnalysisService` instead, since
    letting the AI compute or estimate them risks hallucinated figures
    inconsistent with the other extracted values.

    Attributes:
        currency: The ISO 4217 currency code, or `None` if not stated.
        revenue: Total revenue, or `None` if not stated.
        arr: Annual recurring revenue, or `None` if not stated.
        mrr: Monthly recurring revenue, or `None` if not stated.
        gross_margin: Gross margin as a percentage, or `None`.
        ebitda: EBITDA, or `None`.
        burn_rate: Monthly cash burn rate, or `None`.
        cash: Cash on hand, or `None`.
        customers: Number of customers, or `None`.
        growth_rate: Growth rate as a percentage, or `None`.
        cac: Customer acquisition cost, or `None`.
        ltv: Customer lifetime value, or `None`.
        valuation: Company valuation, or `None`.
    """

    model_config = ConfigDict(extra="forbid")

    currency: str | None
    revenue: float | None
    arr: float | None
    mrr: float | None
    gross_margin: float | None
    ebitda: float | None
    burn_rate: float | None
    cash: float | None
    customers: int | None
    growth_rate: float | None
    cac: float | None
    ltv: float | None
    valuation: float | None


class AIServiceError(Exception):
    """Base exception for AI analysis failures."""


class AIServiceNotConfiguredError(AIServiceError):
    """Raised when no OpenAI API key is configured, or the configured
    key is rejected as invalid by OpenAI."""


class AIRequestFailedError(AIServiceError):
    """Raised when the OpenAI request fails after the allowed retry,
    due to a timeout, connection error, or rate limiting."""


class InvalidAIResponseError(AIServiceError):
    """Raised when the AI's response is not valid JSON, or does not
    conform to the expected schema."""


def _build_user_message(instruction: str, text_content: str) -> str:
    """Build a user message containing an instruction and document text.

    The text is truncated to `MAX_DOCUMENT_CHARACTERS` to bound token
    usage and cost.

    Args:
        instruction: A short instruction describing the analysis task.
        text_content: The document's extracted plain text (and/or prior
            analysis context).

    Returns:
        The formatted user message.
    """
    truncated = text_content[:MAX_DOCUMENT_CHARACTERS]
    return f"{instruction}\n\n{truncated}"


class AIService:
    """Calls OpenAI to produce structured analyses of document text."""

    @staticmethod
    async def analyze_document_text(text_content: str) -> AIAnalysisResult:
        """Analyze document text and return a validated business analysis.

        Args:
            text_content: The document's extracted plain text.

        Returns:
            The validated AI business-analysis result.

        Raises:
            AIServiceNotConfiguredError: If no OpenAI API key is
                configured, or the configured key is rejected as
                invalid.
            AIRequestFailedError: If the request fails (timeout,
                connection error, or rate limit) even after one retry.
            InvalidAIResponseError: If the AI's response is not valid
                JSON, or does not conform to the expected schema.
        """
        user_message = _build_user_message(
            "Analyze the following document:", text_content
        )
        return await _run_structured_completion(
            system_prompt=_BUSINESS_SYSTEM_PROMPT,
            user_message=user_message,
            response_model=AIAnalysisResult,
        )

    @staticmethod
    async def extract_financial_metrics(
        text_content: str,
    ) -> FinancialExtractionResult:
        """Extract raw financial metrics from document text.

        Args:
            text_content: The document's extracted plain text, optionally
                prefixed with prior business-analysis context by the
                caller.

        Returns:
            The validated raw financial extraction result.

        Raises:
            AIServiceNotConfiguredError: If no OpenAI API key is
                configured, or the configured key is rejected as
                invalid.
            AIRequestFailedError: If the request fails (timeout,
                connection error, or rate limit) even after one retry.
            InvalidAIResponseError: If the AI's response is not valid
                JSON, or does not conform to the expected schema.
        """
        user_message = _build_user_message(
            "Extract financial metrics from the following document:",
            text_content,
        )
        return await _run_structured_completion(
            system_prompt=_FINANCIAL_SYSTEM_PROMPT,
            user_message=user_message,
            response_model=FinancialExtractionResult,
        )


async def _run_structured_completion(
    system_prompt: str, user_message: str, response_model: type[_T]
) -> _T:
    """Call OpenAI and validate the response against a given schema.

    Shared by both business and financial analysis, since the call,
    JSON-parsing, and validation flow is identical; only the prompt and
    target schema differ.

    Args:
        system_prompt: The system prompt describing the extraction task
            and required JSON shape.
        user_message: The user message containing the document text.
        response_model: The Pydantic model to validate the response
            against.

    Returns:
        A validated instance of `response_model`.

    Raises:
        AIServiceNotConfiguredError: If no OpenAI API key is configured,
            or the configured key is rejected as invalid.
        AIRequestFailedError: If the request fails after one retry.
        InvalidAIResponseError: If the response is not valid JSON, or
            does not conform to `response_model`.
    """
    if not settings.OPENAI_API_KEY:
        raise AIServiceNotConfiguredError(
            "OPENAI_API_KEY is not configured. AI analysis is "
            "unavailable until an API key is set."
        )

    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    raw_content = await _call_openai_with_retry(client, messages)

    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise InvalidAIResponseError(
            f"AI response was not valid JSON: {exc}"
        ) from exc

    try:
        return response_model(**parsed)
    except ValidationError as exc:
        raise InvalidAIResponseError(
            f"AI response did not match the expected schema: {exc}"
        ) from exc


async def _call_openai_with_retry(client: AsyncOpenAI, messages: list[dict]) -> str:
    """Call the OpenAI chat completions API, retrying once on transient errors.

    Args:
        client: The configured OpenAI async client.
        messages: The chat messages to send.

    Returns:
        The raw text content of the model's response.

    Raises:
        AIServiceNotConfiguredError: If the API key is rejected as
            invalid.
        AIRequestFailedError: If the request fails on both the initial
            attempt and the single retry.
    """
    last_error: Exception | None = None

    for attempt in range(2):
        try:
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content or ""
        except AuthenticationError as exc:
            raise AIServiceNotConfiguredError(
                "OpenAI rejected the configured API key as invalid."
            ) from exc
        except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
            last_error = exc
            logger.warning(
                "OpenAI request failed (attempt %d/2): %s", attempt + 1, exc
            )
            if attempt == 0:
                await asyncio.sleep(_RETRY_DELAY_SECONDS)

    raise AIRequestFailedError(
        f"OpenAI request failed after retry: {last_error}"
    ) from last_error