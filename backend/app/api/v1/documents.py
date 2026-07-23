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