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
_CHAT_MAX_ANSWER_TOKENS = 800

_DUE_DILIGENCE_SYSTEM_PROMPT = """You are a due diligence analyst producing a \
structured investment report from the evidence provided.

Return ONLY a single valid JSON object with exactly these keys, and no \
others, each a string containing the section's content:

{
  "executive_summary": string,
  "company_overview": string,
  "problem": string,
  "solution": string,
  "business_model": string,
  "market": string,
  "competition": string,
  "traction": string,
  "financial_analysis": string,
  "growth": string,
  "risks": string,
  "red_flags": string,
  "investment_thesis": string,
  "recommendation": string,
  "confidence_level": string,
  "open_questions": string
}

Rules:
- Base every statement strictly on the structured data and document \
excerpts provided in the user message. Never use outside knowledge, \
and never invent, assume, or estimate facts not present in the \
provided evidence.
- If information needed for a section is not available in the \
provided evidence, explicitly state "Information not available in the \
provided materials." for that section (or the relevant part of it) \
rather than guessing or leaving it vague.
- When you reference a specific document excerpt, cite it by number \
(e.g. "as stated in excerpt 2").
- "confidence_level" should describe how much of the analysis is \
grounded in solid evidence versus how much information was missing, \
referencing the provided investment-score confidence figure if \
available.
- "red_flags" should highlight any concerning patterns, contradictions, \
or high-risk indicators found in the evidence; if none are apparent, \
say so explicitly rather than fabricating a concern.
- Do not include markdown formatting, code fences, or any commentary \
outside the JSON object. Return the JSON object only."""

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

EXTRACTION_VERSION = "cited_extraction_v1"

_CITED_BUSINESS_SYSTEM_PROMPT = """You are a business analyst extracting structured, \
citation-backed information from company documents.

Return ONLY a single valid JSON object matching this exact shape. Every \
field is an object with "value", "quote", "page_number", and \
"confidence" keys (array fields are arrays of such objects):

{
  "company_name": {"value": string|null, "quote": string|null, "page_number": int|null, "confidence": float|null},
  "industry": {...same shape...},
  "business_model": {...same shape...},
  "summary": {...same shape...},
  "key_products": [{...same shape...}, ...],
  "revenue_streams": [{...same shape...}, ...],
  "target_customers": [{...same shape...}, ...],
  "competitors": [{...same shape...}, ...],
  "main_risks": [{...same shape...}, ...],
  "growth_opportunities": [{...same shape...}, ...],
  "qualitative_facts": [
    {
      "category": one of ["customer_risk", "legal_regulatory",
        "operational_dependency", "ip_ownership", "team_risk",
        "market_risk", "opportunity", "other"],
      "claim_text": string,
      "severity_hint": one of ["critical", "high", "medium", "low",
        "informational"] or null,
      "quote": string,
      "page_number": int|null,
      "confidence": float
    },
    ...
  ]
}

Rules:
- "quote" must be the EXACT, verbatim text from the document that supports \
"value" — never paraphrased. If you cannot find a verbatim supporting \
passage, set "value" to null and "quote" to null.
- Never invent, assume, or infer information not explicitly stated in the \
document. If information is missing, set "value" to null.
- "page_number" should reflect the page the quote appears on if the \
document text indicates page boundaries; otherwise null.
- "confidence" reflects your certainty in this specific extraction (1.0 = \
explicitly and unambiguously stated; lower for information that required \
interpretation).
- For array fields, each item is its own object with its own quote — do \
NOT combine multiple facts into one quote.
- "qualitative_facts" is a structured, categorized restatement of the same \
underlying claims as "main_risks"/"growth_opportunities" — extract every \
distinct risk, dependency, ownership question, or opportunity you find as \
its own entry here too, each with the category it best fits and (for \
risk-shaped claims) a severity_hint reflecting how serious it looks from \
the document alone. Every entry needs its own verbatim "quote" — never \
combine multiple claims into one entry.
- "severity_hint" is null for "opportunity" claims (severity does not \
apply to a positive claim) and for anything else where no risk is being \
described. For genuine risk claims, classify severity based only on what \
the document itself says — do not escalate or downplay based on outside \
knowledge of the industry.
- Do not include markdown formatting or commentary. Return the JSON object \
only."""

_CITED_FINANCIAL_SYSTEM_PROMPT = """You are a financial analyst extracting \
time-series financial facts from company documents, with citations.

Return ONLY a single valid JSON object with this exact shape:

{
  "facts": [
    {
      "metric": one of ["revenue", "arr", "mrr", "gross_profit", "gross_margin",
        "ebitda", "net_income", "operating_expenses", "cash", "debt", "burn_rate",
        "cac", "ltv", "aov", "orders", "registered_customers",
        "monthly_active_users", "churn_rate", "retention_rate",
        "funding_amount", "valuation_pre_money", "valuation_post_money"],
      "value": number,
      "currency": string or null (ISO 4217 code, e.g. "USD"; null for counts),
      "period_type": one of ["month", "quarter", "year", "point_in_time", "unknown"],
      "period": string or null (e.g. "2025", "2025-Q2", "2025-06-30"),
      "value_type": one of ["actual", "forecast", "target", "estimate", "derived"],
      "quote": string (exact verbatim supporting text),
      "page_number": int or null,
      "confidence": float
    },
    ...
  ]
}

Rules:
- Extract EVERY distinct (metric, period) fact you can find. If revenue is \
stated for 2023, 2024, AND 2025, return THREE separate revenue facts, one \
per year — never collapse multiple periods into a single value.
- "registered_customers" and "monthly_active_users" (or similar active-user \
figures) must NEVER be merged into one fact, even if the document discusses \
them together. Extract them as separate facts.
- "arr" (Annual Recurring Revenue) and "mrr" (Monthly Recurring Revenue) are \
run-rate figures, not the same thing as "revenue". Never relabel a stated \
ARR or MRR figure as "revenue", and never relabel stated revenue as ARR or \
MRR — extract each exactly as the document names it.
- ONLY use one of the exact metric names listed above. If a figure does not \
clearly match one of these metrics (e.g. a growth rate or a customer count \
that is not "registered_customers" or "monthly_active_users"), omit it \
rather than inventing a new metric name.
- Classify "value_type" carefully: a stated projection or expectation for a \
future period is "forecast", not "actual". A number the source explicitly \
calls an estimate is "estimate". A stated goal is "target". Only use \
"actual" for realized, historical figures.
- Never extract a valuation or funding-round amount as "revenue", even if \
the numbers are similar in magnitude. These are structurally different \
metrics.
- "quote" must be exact, verbatim text — never paraphrased.
- Never invent a figure that is not explicitly stated. If you are unsure \
whether a number represents this metric, omit it rather than guess.
- "gross_margin", "churn_rate", and "retention_rate" are FRACTIONS, not \
plain percentages: a stated "42.5%" gross margin must be extracted as \
0.425, never as 42.5 or 42.5. A stated "3% monthly churn" must be extracted \
as 0.03, never as 3. This is the convention every downstream consumer of \
these three metrics assumes (plausible-range validation, gross-profit \
estimation) — extracting a plain percentage instead silently produces a \
value 100x too large everywhere it's used.
- Do not include markdown formatting or commentary. Return the JSON object \
only."""

def _create_openrouter_client() -> AsyncOpenAI:
    if not settings.OPENROUTER_API_KEY:
        raise AIServiceNotConfiguredError(
            "OPENROUTER_API_KEY is not configured."
        )

    default_headers = {
        "X-OpenRouter-Title": settings.OPENROUTER_APP_NAME,
    }

    if settings.OPENROUTER_SITE_URL:
        default_headers["HTTP-Referer"] = settings.OPENROUTER_SITE_URL

    client = AsyncOpenAI(
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
        timeout=REQUEST_TIMEOUT_SECONDS,
        default_headers=default_headers,
    )

    logger.warning(
        "Created OpenRouter client: configured_url=%r actual_url=%s",
        settings.OPENROUTER_BASE_URL,
        client.base_url,
    )

    return client

client = _create_openrouter_client()

logger.warning(
    "Actual AI client base URL: %s",
    client.base_url,
)



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


class DueDiligenceReportResult(BaseModel):
    """Strict schema for the AI's generated due diligence report.

    Field names correspond to the report sections specified in the due
    diligence milestone. Every field is free-text; the model is
    instructed to state explicitly when evidence for a section is
    missing, rather than fabricating content.

    Attributes:
        executive_summary: A high-level summary of the investment
            opportunity.
        company_overview: An overview of the company and what it does.
        problem: The problem the company addresses.
        solution: The company's solution to that problem.
        business_model: How the company generates revenue.
        market: The company's target market.
        competition: The company's competitive landscape.
        traction: Evidence of market traction (customers, growth, etc.).
        financial_analysis: Analysis of the company's financial metrics.
        growth: The company's growth trajectory and opportunities.
        risks: The company's main risks.
        red_flags: Concerning patterns or high-risk indicators found in
            the evidence, or an explicit statement that none were
            found.
        investment_thesis: The case for (or against) investing.
        recommendation: A recommendation based on the available
            evidence.
        confidence_level: How confident the analysis is, given the
            available evidence.
        open_questions: Questions that remain unanswered by the
            available evidence.
    """

    model_config = ConfigDict(extra="forbid")

    executive_summary: str
    company_overview: str
    problem: str
    solution: str
    business_model: str
    market: str
    competition: str
    traction: str
    financial_analysis: str
    growth: str
    risks: str
    red_flags: str
    investment_thesis: str
    recommendation: str
    confidence_level: str
    open_questions: str

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

    @staticmethod
    async def generate_chat_answer(system_prompt: str, user_message: str) -> str:
        """Generate a free-text chat answer, with no JSON schema enforced.

        Unlike `analyze_document_text` and `extract_financial_metrics`,
        this method does not force JSON-mode output or validate the
        response against a schema — chat answers are natural-language
        text. Shares the same retry/timeout/client machinery via
        `_call_openai_with_retry`.

        Args:
            system_prompt: The system prompt describing how to answer.
            user_message: The user message, typically containing the
                question and retrieved context.

        Returns:
            The model's free-text answer.

        Raises:
            AIServiceNotConfiguredError: If no OpenAI API key is
                configured, or the configured key is rejected as
                invalid.
            AIRequestFailedError: If the request fails after retrying
                once.
        """
        if not settings.OPENROUTER_API_KEY:
            raise AIServiceNotConfiguredError(
                "OPENROUTER_API_KEY is not configured. AI analysis is "
                "unavailable until an API key is set."
            )

        client = _create_openrouter_client()


        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        return await _call_openai_with_retry(client, messages)

    @staticmethod
    async def generate_due_diligence_report(
        user_message: str,
    ) -> DueDiligenceReportResult:
        """Generate a structured due diligence report.

        Reuses the same structured-completion machinery as
        `analyze_document_text` and `extract_financial_metrics` — only
        the prompt and target schema differ. This is not a separate AI
        pipeline.

        Args:
            user_message: The assembled context (structured data and
                retrieved document excerpts) and reporting instructions.

        Returns:
            The validated due diligence report.

        Raises:
            AIServiceNotConfiguredError: If no OpenAI API key is
                configured, or the configured key is rejected as
                invalid.
            AIRequestFailedError: If the request fails (timeout,
                connection error, or rate limit) even after one retry.
            InvalidAIResponseError: If the AI's response is not valid
                JSON, or does not conform to the expected schema.
        """
        return await _run_structured_completion(
            system_prompt=_DUE_DILIGENCE_SYSTEM_PROMPT,
            user_message=user_message,
            response_model=DueDiligenceReportResult,
        )

    @staticmethod
    async def generate_cited_business_analysis(text_content: str) -> "CitedBusinessAnalysisResult":
        """Analyze document text and return citation-backed business analysis.

        Args:
            text_content: The document's extracted plain text.

        Returns:
            The validated, citation-backed analysis result.

        Raises:
            AIServiceNotConfiguredError: If no OpenAI API key is configured.
            AIRequestFailedError: If the request fails after retrying once.
            InvalidAIResponseError: If the response is invalid even after
                one correction retry.
        """
        from app.schemas.cited_extraction import CitedBusinessAnalysisResult

        user_message = _build_user_message(
            "Extract structured, citation-backed business information from "
            "the following document:",
            text_content,
        )
        return await _run_structured_completion_with_correction(
            _CITED_BUSINESS_SYSTEM_PROMPT, user_message, CitedBusinessAnalysisResult
        )

    @staticmethod
    async def generate_cited_financial_facts(text_content: str) -> "CitedFinancialFactsResult":
        """Extract time-series financial facts with citations.

        Args:
            text_content: The document's extracted plain text.

        Returns:
            The validated, citation-backed financial facts result.

        Raises:
            AIServiceNotConfiguredError: If no OpenAI API key is configured.
            AIRequestFailedError: If the request fails after retrying once.
            InvalidAIResponseError: If the response is invalid even after
                one correction retry.
        """
        from app.schemas.cited_extraction import CitedFinancialFactsResult

        user_message = _build_user_message(
            "Extract all time-series financial facts, with citations, from "
            "the following document:",
            text_content,
        )
        return await _run_structured_completion_with_correction(
            _CITED_FINANCIAL_SYSTEM_PROMPT, user_message, CitedFinancialFactsResult
        )

    @staticmethod
    async def generate_chat_answer_with_tools(
        system_prompt: str, messages: list[dict], tools: list[dict]
    ) -> tuple[str | None, list]:
        """Run one tool-calling-capable chat completion turn.

        Args:
            system_prompt: The system prompt (only used if `messages`
                doesn't already start with a system message).
            messages: The running conversation, including any prior
                tool results appended by the caller's orchestration loop.
            tools: The `TOOL_SPECS`-shaped tool definitions to offer
                the model.

        Returns:
            A tuple of `(answer_text_or_none, tool_calls)`. If the
            model chose to call tools, `answer_text_or_none` is `None`
            and `tool_calls` is non-empty (the OpenAI SDK's tool_calls
            objects); otherwise `answer_text_or_none` holds the final
            answer and `tool_calls` is empty.

        Raises:
            AIServiceNotConfiguredError: If no OpenRouter API key is
                configured, or it is rejected as invalid.
            AIRequestFailedError: If the request fails after retrying
                once.
        """
        if not settings.OPENROUTER_API_KEY:
            raise AIServiceNotConfiguredError(
                "OPENROUTER_API_KEY is not configured. Chat is unavailable until an API key is set."
            )

        client = _create_openrouter_client()

        full_messages = messages if messages and messages[0].get("role") == "system" else (
            [{"role": "system", "content": system_prompt}] + messages
        )

        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = await client.chat.completions.create(
                    model=settings.OPENROUTER_CHAT_MODEL, messages=full_messages, tools=tools,
                )
                message = response.choices[0].message
                if message.tool_calls:
                    return None, message.tool_calls
                return message.content or "", []
            except AuthenticationError as exc:
                raise AIServiceNotConfiguredError("OpenAI rejected the configured API key as invalid.") from exc
            except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
                last_error = exc
                logger.warning("OpenAI tool-call request failed (attempt %d/2): %s", attempt + 1, exc)
                if attempt == 0:
                    await asyncio.sleep(_RETRY_DELAY_SECONDS)

        raise AIRequestFailedError(f"OpenAI request failed after retry: {last_error}") from last_error


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
    if not settings.OPENROUTER_API_KEY:
        raise AIServiceNotConfiguredError(
            "OPENROUTER_API_KEY is not configured. AI analysis is "
            "unavailable until an API key is set."
        )

    client = _create_openrouter_client()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    raw_content = await _call_openai_with_retry(
        client, messages, response_format={"type": "json_object"}
    )

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

async def _run_structured_completion_with_correction(
    system_prompt: str, user_message: str, response_model: type
):
    """Run a structured completion, retrying once with a correction prompt
    if the response fails Pydantic validation.

    This is distinct from `_call_openai_with_retry`'s transient-failure
    retry (network timeouts, rate limits) — this retry specifically
    targets schema-validation failures (Section 11): if the model's JSON
    doesn't match the expected shape, we tell it exactly what went wrong
    and ask it to correct itself, rather than silently failing or saving
    a partially-invalid result.

    Args:
        system_prompt: The system prompt for the extraction task.
        user_message: The user message containing the document text.
        response_model: The Pydantic model to validate against.

    Returns:
        A validated instance of `response_model`.

    Raises:
        AIServiceNotConfiguredError: If no OpenAI API key is configured.
        AIRequestFailedError: If the underlying request fails after its
            own retry.
        InvalidAIResponseError: If validation still fails after the
            correction retry.
    """
    try:
        return await _run_structured_completion(system_prompt, user_message, response_model)
    except InvalidAIResponseError as first_error:
        logger.warning(
            "Structured extraction failed validation, retrying with correction: %s",
            first_error,
        )
        correction_message = (
            f"{user_message}\n\n"
            f"Your previous response was invalid: {first_error}\n"
            f"Return ONLY a corrected JSON object matching the required schema exactly."
        )
        try:
            return await _run_structured_completion(system_prompt, correction_message, response_model)
        except InvalidAIResponseError as second_error:
            logger.error(
                "Structured extraction failed validation after correction retry: %s",
                second_error,
            )
            raise


async def _call_openai_with_retry(
    client: AsyncOpenAI,
    messages: list[dict],
    response_format: dict | None = None,
) -> str:
    """Call the OpenAI chat completions API, retrying once on transient errors.

    Args:
        client: The configured OpenAI async client.
        messages: The chat messages to send.
        response_format: An optional OpenAI response-format directive
            (e.g. `{"type": "json_object"}`). Passed through unchanged
            when provided; omitted entirely for free-text completions
            such as chat answers.

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
            kwargs: dict = {
                "model": settings.OPENROUTER_CHAT_MODEL,
                "messages": messages,
                }
            if response_format is not None:
                kwargs["response_format"] = response_format
            response = await client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except AuthenticationError as exc:
            logger.exception(
                "OpenRouter authentication error: status=%r body=%r message=%s",
                getattr(exc, "status_code", None),
                getattr(exc, "body", None),
                exc,
            )
            raise AIServiceNotConfiguredError(
                f"OpenRouter authentication failed: {exc}"
            ) from exc
        except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
            last_error = exc
            logger.warning(
                "OpenRouter request failed (attempt %d/2): %s", attempt + 1, exc
            )
            if attempt == 0:
                await asyncio.sleep(_RETRY_DELAY_SECONDS)

    raise AIRequestFailedError(
        f"OpenAI request failed after retry: {last_error}"
    ) from last_error