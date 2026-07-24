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