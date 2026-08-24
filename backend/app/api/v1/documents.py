"""Document ingestion API routes.

Routers stay thin: they parse requests, delegate to `DocumentService`,
and translate domain exceptions into HTTP responses. No business logic
lives here.
"""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_active_user
from app.config import get_settings
from app.core.storage import FileTooLargeError, StorageService, get_storage_service
from app.db.dependencies import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentListResponse, DocumentRead, DocumentUploadResponse

from app.services.document_service import (
    DocumentNotFoundError,
    DocumentService,
    InsufficientPermissionsError,
    OrganizationAccessDeniedError,
    UnsupportedFileTypeError,
)

from app.schemas.document_analysis import DocumentAnalysisRead
from app.services.ai_service import (
    AIRequestFailedError,
    AIServiceNotConfiguredError,
    InvalidAIResponseError,
)
from app.services.document_analysis_service import (
    AnalysisNotFoundError,
    DocumentAnalysisService,
    DocumentNotProcessedError,
    DocumentAnalysis,
)

from app.schemas.financial_metrics import FinancialMetricsRead
from app.services.financial_analysis_service import (
    BusinessAnalysisRequiredError,
    FinancialAnalysisService,
    FinancialMetricsNotFoundError,
)

from app.models.financial_metrics import FinancialMetrics

from app.schemas.investment_score import InvestmentScoreResponse
from app.services.investment_scoring_service import (
    InsufficientDataForScoringError,
    InvestmentScore,
    InvestmentScoreNotFoundError,
    InvestmentScoringService,
)

from app.schemas.rag import IndexResponse
from app.services.document_index_service import (
    DocumentIndexService,
    DocumentNotProcessedError as IndexDocumentNotProcessedError,
    NoIndexableContentError,
)
from app.services.embedding_service import (
    EmbeddingRequestFailedError,
    EmbeddingServiceNotConfiguredError,
    InvalidEmbeddingDimensionError,
)

from fastapi import Body
from app.schemas.due_diligence import DueDiligenceRequest, DueDiligenceResponse
from app.services.due_diligence_service import (
    DocumentNotProcessedError as DueDiligenceDocumentNotProcessedError,
    DueDiligenceService,
)

from fastapi import Response
from app.services.report_export_service import (
    ReportExportService,
    ReportRenderingFailedError,
)

from app.schemas.coverage import CoverageAssessmentRead
from app.schemas.derived_metrics import MetricsResponse
from app.schemas.validation import ValidationChecksResponse
from app.services.coverage_service import compute_coverage
from app.services.derived_metrics_service import calculate_all_derived_metrics, persist_derived_metrics
from app.services.financial_facts_service import FinancialFactsService
from app.services.validation_service import ValidationService, run_all_validations

from app.services.document_analysis_service import DocumentAnalysisService as DAService

from app.services.missing_information_service import compute_missing_information, facts_to_metric_set, MissingInformationService

from app.schemas.missing_information import MissingInformationResponse

from app.schemas.due_diligence_v2 import DueDiligenceV2Response
from app.services.due_diligence_v2_service import DueDiligenceV2Service

from app.schemas.derived_metrics import DerivedMetricRead
from app.schemas.validation import ValidationFindingRead

settings = get_settings()

router = APIRouter(prefix=f"{settings.API_V1_PREFIX}/documents", tags=["documents"])


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document to an organization",
)
async def upload_document(
    organization_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
    current_user: User = Depends(get_current_active_user),
) -> Document:
    """Upload a new document to an organization.

    Args:
        organization_id: The organization to upload the document to,
            supplied as a multipart form field.
        file: The uploaded file. Only PDF, DOCX, and TXT files up to
            20 MB are accepted.
        db: The request-scoped database session.
        storage: The storage backend to persist the file to.
        current_user: The authenticated user performing the upload.

    Returns:
        The newly created document's metadata.

    Raises:
        HTTPException: With status 404 if the user is not a member of
            the organization; 415 if the file type is not accepted; 413
            if the file exceeds the maximum allowed size.
    """
    try:
        return await DocumentService.upload_document(
            db=db,
            storage=storage,
            organization_id=organization_id,
            actor_id=current_user.id,
            upload_file=file,
        )
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from exc
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        ) from exc


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List an organization's documents",
)
async def list_documents(
    organization_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DocumentListResponse:
    """List all documents belonging to an organization.

    Args:
        organization_id: The organization whose documents to list.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The organization's documents, most recently uploaded first.

    Raises:
        HTTPException: With status 404 if the user is not a member of
            the organization.
    """
    try:
        documents = await DocumentService.list_documents(
            db=db, organization_id=organization_id, actor_id=current_user.id
        )
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return DocumentListResponse(items=documents, total=len(documents))


@router.get(
    "/{document_id}",
    response_model=DocumentRead,
    summary="Get a document's metadata",
)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Document:
    """Fetch a single document's metadata.

    Args:
        document_id: The document's id.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The requested document's metadata.

    Raises:
        HTTPException: With status 404 if the document does not exist
            or the user is not a member of its organization.
    """
    try:
        return await DocumentService.get_document(
            db=db, document_id=document_id, actor_id=current_user.id
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

@router.post(
    "/{document_id}/process",
    response_model=DocumentRead,
    summary="Run text extraction for an uploaded document",
)
async def process_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
    current_user: User = Depends(get_current_active_user),
) -> Document:
    """Trigger the text-extraction pipeline for a document.

    Runs synchronously: the response reflects the final outcome
    (`COMPLETED` or `FAILED`) of this processing attempt. There is no
    background queue in this milestone.

    Args:
        document_id: The document's id.
        db: The request-scoped database session.
        storage: The storage backend the file is persisted in.
        current_user: The authenticated user.

    Returns:
        The document's updated metadata, including its new status and
        (on success) page count, or (on failure) an error message.

    Raises:
        HTTPException: With status 404 if the document does not exist
            or the user is not a member of its organization.
    """
    try:
        return await DocumentService.process_document(
            db=db,
            storage=storage,
            document_id=document_id,
            actor_id=current_user.id,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

@router.post(
    "/{document_id}/analyze",
    response_model=DocumentAnalysisRead,
    summary="Run AI analysis on a processed document",
)
async def analyze_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DocumentAnalysis:
    """Analyze a processed document and produce structured business
    information using AI.

    Runs synchronously; the response reflects the completed analysis.
    Re-running this endpoint overwrites the document's existing
    analysis, since each document has at most one.

    Args:
        document_id: The document's id.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The resulting structured analysis.

    Raises:
        HTTPException: With status 404 if the document does not exist
            or the user is not a member of its organization; 409 if the
            document's text has not finished processing; 503 if the AI
            service is not configured; 502 if the AI request fails or
            returns an invalid response.
    """
    try:
        return await DocumentAnalysisService.analyze_document(
            db=db, document_id=document_id, actor_id=current_user.id
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except DocumentNotProcessedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except AIServiceNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except (InvalidAIResponseError, AIRequestFailedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc


@router.get(
    "/{document_id}/analysis",
    response_model=DocumentAnalysisRead,
    summary="Get a document's AI analysis",
)
async def get_document_analysis(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DocumentAnalysis:
    """Fetch a document's previously generated AI analysis.

    Args:
        document_id: The document's id.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The document's structured analysis.

    Raises:
        HTTPException: With status 404 if the document does not exist,
            the user is not a member of its organization, or the
            document has not been analyzed yet.
    """
    try:
        return await DocumentAnalysisService.get_analysis(
            db=db, document_id=document_id, actor_id=current_user.id
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except AnalysisNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

@router.post(
    "/{document_id}/financial-analysis",
    response_model=FinancialMetricsRead,
    summary="Run AI financial extraction on an analyzed document",
)
async def analyze_financial_metrics(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FinancialMetrics:
    """Extract structured financial KPIs from a document using AI.

    Requires that the document's business analysis
    (`POST /documents/{id}/analyze`) has already been run. Runs
    synchronously; re-running this endpoint overwrites the document's
    existing financial metrics, since each document has at most one.

    Args:
        document_id: The document's id.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The resulting structured financial metrics.

    Raises:
        HTTPException: With status 404 if the document does not exist
            or the user is not a member of its organization; 409 if the
            document's business analysis has not been run yet; 503 if
            the AI service is not configured; 502 if the AI request
            fails or returns an invalid response.
    """
    try:
        return await FinancialAnalysisService.analyze_financial_metrics(
            db=db, document_id=document_id, actor_id=current_user.id
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except BusinessAnalysisRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except AIServiceNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except (InvalidAIResponseError, AIRequestFailedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc


@router.get(
    "/{document_id}/financial-analysis",
    response_model=FinancialMetricsRead,
    summary="Get a document's financial metrics",
)
async def get_financial_metrics(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> FinancialMetrics:
    """Fetch a document's previously extracted financial metrics.

    Args:
        document_id: The document's id.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The document's structured financial metrics.

    Raises:
        HTTPException: With status 404 if the document does not exist,
            the user is not a member of its organization, or financial
            analysis has not been run yet.
    """
    try:
        return await FinancialAnalysisService.get_financial_metrics(
            db=db, document_id=document_id, actor_id=current_user.id
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except FinancialMetricsNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)

async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
    current_user: User = Depends(get_current_active_user),
) -> None:
    """Delete a document and its underlying stored file.

    Args:
        document_id: The document's id.
        db: The request-scoped database session.
        storage: The storage backend the file is persisted in.
        current_user: The authenticated user.

    Raises:
        HTTPException: With status 404 if the document does not exist
            or the user is not a member of its organization; 403 if the
            user lacks permission to delete it.
    """
    try:
        await DocumentService.delete_document(
            db=db,
            storage=storage,
            document_id=document_id,
            actor_id=current_user.id,
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except InsufficientPermissionsError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)
        ) from exc

@router.post(
    "/{document_id}/score",
    response_model=InvestmentScoreResponse,
    summary="Calculate or recalculate a document's investment score",
)
async def calculate_investment_score(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> InvestmentScore:
    """Calculate (or recalculate) a document's investment score.

    Uses only already-persisted financial metrics and business
    analysis; makes no external or AI calls. Re-running this endpoint
    overwrites the document's existing score, since each document has
    at most one.

    Args:
        document_id: The document's id.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The resulting investment score.

    Raises:
        HTTPException: With status 404 if the document does not exist
            or the user is not a member of its organization; 409 if the
            document has neither financial metrics nor a business
            analysis to score from.
    """
    try:
        return await InvestmentScoringService.calculate_score(
            db=db, document_id=document_id, actor_id=current_user.id
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except InsufficientDataForScoringError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc


@router.get(
    "/{document_id}/score",
    response_model=InvestmentScoreResponse,
    summary="Get a document's investment score",
)
async def get_investment_score(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> InvestmentScore:
    """Fetch a document's previously calculated investment score.

    Args:
        document_id: The document's id.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The document's investment score.

    Raises:
        HTTPException: With status 404 if the document does not exist,
            the user is not a member of its organization, or the
            document has not been scored yet.
    """
    try:
        return await InvestmentScoringService.get_score(
            db=db, document_id=document_id, actor_id=current_user.id
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except InvestmentScoreNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

@router.post(
    "/{document_id}/due-diligence",
    response_model=DueDiligenceResponse,
    summary="Generate a complete due diligence report for a document",
)
async def generate_due_diligence_report(
    document_id: uuid.UUID,
    payload: DueDiligenceRequest | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DueDiligenceResponse:
    """Generate a complete, evidence-grounded due diligence report.

    Reuses existing business analysis, financial metrics, and
    investment score data if available, plus additional retrieved
    document excerpts. Does not re-run analysis, financial extraction,
    or scoring — only reads what has already been computed. Runs
    synchronously; no report is stored.

    Args:
        document_id: The document's id.
        payload: Optional parameters (currently just `top_k`). If
            omitted, defaults are used.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The complete due diligence report.

    Raises:
        HTTPException: With status 404 if the document does not exist
            or the user is not a member of its organization; 409 if the
            document is not fully processed; 503 if the AI or embedding
            service is not configured; 502 if the AI or embedding
            request fails or returns an invalid response.
    """
    top_k = payload.top_k if payload is not None else DueDiligenceRequest().top_k

    try:
        return await DueDiligenceService.generate_report(
            db=db, document_id=document_id, actor_id=current_user.id, top_k=top_k
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except DueDiligenceDocumentNotProcessedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (AIServiceNotConfiguredError, EmbeddingServiceNotConfiguredError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except (
        AIRequestFailedError,
        InvalidAIResponseError,
        EmbeddingRequestFailedError,
        InvalidEmbeddingDimensionError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

@router.get(
    "/{document_id}/metrics",
    response_model=MetricsResponse,
    summary="Get a document's time-series financial facts and derived metrics",
)
async def get_document_metrics(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MetricsResponse:
    """Return raw financial facts and computed derived metrics for a document.

    Recomputes derived metrics from currently-stored facts each time
    (cheap, pure-Python, no AI call) and persists the refreshed result,
    so this endpoint always reflects the latest facts even if new ones
    were added since the last computation.

    Args:
        document_id: The document's id.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The document's facts and derived metrics.

    Raises:
        HTTPException: With status 404 if the document does not exist
            or the user is not a member of its organization.
    """
    try:
        await DocumentService.get_document(db, document_id, current_user.id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    fact_points = await FinancialFactsService.get_fact_points(db, document_id)
    results = calculate_all_derived_metrics(fact_points)
    persisted = await persist_derived_metrics(db, document_id, results)
    raw_facts = await FinancialFactsService.list_facts(db, document_id)

    return MetricsResponse(
        financial_facts=[
            {
                "metric": f.metric, "value": f.value, "currency": f.currency,
                "period_type": f.period_type, "period": f.period, "value_type": f.value_type,
            }
            for f in raw_facts
        ],
        derived_metrics=[DerivedMetricRead.model_validate(row) for row in persisted],
    )


@router.get(
    "/{document_id}/checks",
    response_model=ValidationChecksResponse,
    summary="Get a document's deterministic consistency and anomaly findings",
)
async def get_document_checks(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ValidationChecksResponse:
    """Return validation findings for a document, recomputing from current facts.

    Args:
        document_id: The document's id.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The document's validation findings, most severe first, with
        per-severity counts.

    Raises:
        HTTPException: With status 404 if the document does not exist
            or the user is not a member of its organization.
    """
    try:
        await DocumentService.get_document(db, document_id, current_user.id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    fact_points = await FinancialFactsService.get_fact_points(db, document_id)
    findings = run_all_validations(fact_points)
    persisted = await ValidationService.persist_findings(db, document_id, findings)

    return ValidationChecksResponse(
        findings=[ValidationFindingRead.model_validate(f) for f in persisted],
        critical_count=sum(1 for f in findings if f.severity.value == "critical"),
        warning_count=sum(1 for f in findings if f.severity.value == "warning"),
        info_count=sum(1 for f in findings if f.severity.value == "info"),
    )


@router.get(
    "/{document_id}/coverage",
    response_model=CoverageAssessmentRead,
    summary="Get a document's explainable analysis-coverage assessment",
)
async def get_document_coverage(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CoverageAssessmentRead:
    """Return an explainable coverage assessment for a document.

    As a side effect, also recomputes and persists the missing-
    information checklist, since both are derived from the same
    underlying found/missing field data.
    """
    try:
        await DocumentService.get_document(db, document_id, current_user.id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    fact_points = await FinancialFactsService.get_fact_points(db, document_id)
    financial_metrics_found = facts_to_metric_set(fact_points)

    analysis = await DocumentAnalysisService.get_analysis(db, document_id, current_user.id) if False else None
    try:
        from app.services.document_analysis_service import AnalysisNotFoundError as _ANF
        analysis = await DocumentAnalysisService.get_analysis(db, document_id, current_user.id)
    except Exception:
        analysis = None

    company_fields_found = set()
    market_fields_found = set()
    if analysis is not None:
        field_map = {
            "company_name": analysis.company_name, "industry": analysis.industry,
            "business_model": analysis.business_model, "summary": analysis.summary,
            "key_products": analysis.key_products, "revenue_streams": analysis.revenue_streams,
            "customers": analysis.customers, "competitors": analysis.competitors,
        }
        company_fields_found = {k for k, v in field_map.items() if v}
        market_fields_found = {"competitors"} if analysis.competitors else set()

    missing_info_result = compute_missing_information(
        financial_metrics_found=financial_metrics_found,
        company_fields_found=company_fields_found,
        market_fields_found=market_fields_found,
        team_fields_found=set(),
    )
    await MissingInformationService.persist_items(db, document_id, missing_info_result)

    coverage_result = compute_coverage(
        financial_metrics_found=financial_metrics_found,
        company_fields_found=company_fields_found,
        market_fields_found=market_fields_found,
        team_fields_found=set(),
        citations_count=0,
        total_extracted_fields=len(fact_points) + len(company_fields_found),
    )

    return CoverageAssessmentRead(document_id=str(document_id), **coverage_result.model_dump())

@router.get(
    "/{document_id}/missing-information",
    response_model=MissingInformationResponse,
    summary="Get a document's missing-information checklist",
)
async def get_document_missing_information(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MissingInformationResponse:
    """Return the full checklist grouped by category, recomputed from current data."""
    try:
        await DocumentService.get_document(db, document_id, current_user.id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    fact_points = await FinancialFactsService.get_fact_points(db, document_id)
    result = compute_missing_information(
        financial_metrics_found=facts_to_metric_set(fact_points),
        company_fields_found=set(),
        market_fields_found=set(),
        team_fields_found=set(),
    )
    await MissingInformationService.persist_items(db, document_id, result)
    return result

@router.get(
    "/{document_id}/report.md",
    summary="Export a document's due diligence report as Markdown",
    response_class=Response,
)
async def export_report_markdown(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Response:
    """Generate and download a due diligence report as Markdown.

    Calls the same report generation used by
    `POST /documents/{id}/due-diligence` exactly once; no separate AI
    pipeline, no additional OpenAI calls beyond that single generation,
    and nothing is persisted.

    Args:
        document_id: The document's id.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The Markdown file as a downloadable attachment.

    Raises:
        HTTPException: With status 404 if the document does not exist
            or the user is not a member of its organization; 409 if the
            document is not fully processed; 503 if the AI or embedding
            service is not configured; 502 if the AI or embedding
            request fails, returns an invalid response, or PDF/Markdown
            rendering fails.
    """
    try:
        filename, content = await ReportExportService.export_markdown(
            db, document_id, current_user.id
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except DueDiligenceDocumentNotProcessedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (AIServiceNotConfiguredError, EmbeddingServiceNotConfiguredError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except (
        AIRequestFailedError,
        InvalidAIResponseError,
        EmbeddingRequestFailedError,
        InvalidEmbeddingDimensionError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{document_id}/report.pdf",
    summary="Export a document's due diligence report as PDF",
    response_class=Response,
)
async def export_report_pdf(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Response:
    """Generate and download a due diligence report as a PDF.

    Calls the same report generation used by
    `POST /documents/{id}/due-diligence` exactly once; no separate AI
    pipeline, no additional OpenAI calls beyond that single generation,
    and nothing is persisted.

    Args:
        document_id: The document's id.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The PDF file as a downloadable attachment.

    Raises:
        HTTPException: With status 404 if the document does not exist
            or the user is not a member of its organization; 409 if the
            document is not fully processed; 503 if the AI or embedding
            service is not configured; 502 if the AI or embedding
            request fails, returns an invalid response, or PDF
            rendering fails.
    """
    try:
        filename, pdf_bytes = await ReportExportService.export_pdf(
            db, document_id, current_user.id
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except DueDiligenceDocumentNotProcessedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except OrganizationAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except (AIServiceNotConfiguredError, EmbeddingServiceNotConfiguredError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except (
        AIRequestFailedError,
        InvalidAIResponseError,
        EmbeddingRequestFailedError,
        InvalidEmbeddingDimensionError,
        ReportRenderingFailedError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@router.post(
    "/{document_id}/index",
    response_model=IndexResponse,
    summary="Index (or reindex) a document for semantic search",
)
async def index_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> IndexResponse:
    """Chunk, embed, and index a document's text for semantic search.

    Re-running this endpoint replaces the document's existing index
    entirely (old chunks/embeddings are deleted first), so it is safe
    to call repeatedly, e.g. after content changes upstream.

    Args:
        document_id: The document's id.
        db: The request-scoped database session.
        current_user: The authenticated user.

    Returns:
        The number of chunks indexed.

    Raises:
        HTTPException: With status 404 if the document does not exist
            or the user is not a member of its organization; 409 if the
            document is not fully processed, or produced no indexable
            content; 503 if the embedding service is not configured; 502
            if the embeddings request fails or returns an invalid
            response.
    """
    try:
        chunks_indexed = await DocumentIndexService.index_document(
            db=db, document_id=document_id, actor_id=current_user.id
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except IndexDocumentNotProcessedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except NoIndexableContentError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
    except EmbeddingServiceNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except (EmbeddingRequestFailedError, InvalidEmbeddingDimensionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc

    return IndexResponse(document_id=document_id, chunks_indexed=chunks_indexed)

@router.post(
    "/{document_id}/analyze-with-citations",
    response_model=DocumentAnalysisRead,
    summary="Run citation-backed AI analysis on a processed document",
)
async def analyze_document_with_citations(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DocumentAnalysis:
    """Analyze a document and persist per-field source citations.

    Response shape is identical to `POST /{id}/analyze` for backward
    compatibility; the additional citations are retrievable via the
    `/coverage` endpoint's field-found data and future citation-lookup
    endpoints.
    """
    try:
        return await DAService.analyze_document_with_citations(db, document_id, current_user.id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DocumentNotProcessedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AIServiceNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except (AIRequestFailedError, InvalidAIResponseError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post(
    "/{document_id}/extract-financial-facts",
    summary="Extract time-series financial facts with citations",
)
async def extract_financial_facts(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Extract and persist citation-backed time-series financial facts.

    Populates `financial_facts` (consumed by `/metrics` and `/checks`)
    without touching the existing flat `FinancialMetrics` row.
    """
    try:
        facts = await FinancialAnalysisService.extract_financial_facts(db, document_id, current_user.id)
        return {"document_id": str(document_id), "facts_extracted": len(facts)}
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AIServiceNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except (AIRequestFailedError, InvalidAIResponseError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post(
    "/{document_id}/due-diligence-v2",
    response_model=DueDiligenceV2Response,
    summary="Generate the upgraded, evidence-grounded due diligence report",
)
async def generate_due_diligence_report_v2(
    document_id: uuid.UUID,
    payload: DueDiligenceRequest | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> DueDiligenceV2Response:
    """Generate the upgraded report: verified facts, red flags from
    validation findings, deterministic founder questions, and a
    structured recommendation status — on top of the same narrative
    sections and AI call as the original endpoint."""
    top_k = payload.top_k if payload is not None else DueDiligenceRequest().top_k
    try:
        return await DueDiligenceV2Service.generate_report_v2(db, document_id, current_user.id, top_k)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DueDiligenceDocumentNotProcessedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AIServiceNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except (AIRequestFailedError, InvalidAIResponseError, EmbeddingRequestFailedError, InvalidEmbeddingDimensionError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc