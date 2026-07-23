"""Document ingestion business logic.

Implements document upload, retrieval, listing, and deletion. This
milestone covers ingestion only: no parsing, OCR, embeddings, or AI
processing is performed. Services operate directly on `AsyncSession` —
there is no repository layer in this project's architecture.
"""

import uuid

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import StorageService
from app.models.document import Document, DocumentStatus
from app.models.organization import Membership, MembershipRole

from app.services.document_processor import DocumentProcessorService

from app.core.storage import StorageService

ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
}

MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


class DocumentServiceError(Exception):
    """Base exception for document service failures."""


class OrganizationAccessDeniedError(DocumentServiceError):
    """Raised when the actor is not a member of the target organization.

    Raised identically whether the organization does not exist or the
    actor simply isn't a member of it, to avoid confirming the
    existence of organizations the actor has no access to.
    """


class DocumentNotFoundError(DocumentServiceError):
    """Raised when a document does not exist or the actor cannot access it.

    Raised identically for both cases, for the same reason as
    `OrganizationAccessDeniedError`.
    """


class UnsupportedFileTypeError(DocumentServiceError):
    """Raised when an uploaded file's content type is not permitted."""


class InsufficientPermissionsError(DocumentServiceError):
    """Raised when an actor lacks permission to perform the requested
    action on a document."""


async def _get_membership(
    db: AsyncSession, organization_id: uuid.UUID, user_id: uuid.UUID
) -> Membership | None:
    """Fetch a membership row, if one exists.

    Args:
        db: The active database session.
        organization_id: The organization's id.
        user_id: The user's id.

    Returns:
        The `Membership` if found, otherwise `None`.
    """
    result = await db.execute(
        select(Membership).where(
            Membership.organization_id == organization_id,
            Membership.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


class DocumentService:
    """Document use cases: upload, retrieval, listing, and deletion.

    All methods are stateless and take `AsyncSession`/`StorageService`
    explicitly, rather than holding either as instance state.
    """

    @staticmethod
    async def upload_document(
        db: AsyncSession,
        storage: StorageService,
        organization_id: uuid.UUID,
        actor_id: uuid.UUID,
        upload_file: UploadFile,
    ) -> Document:
        """Validate, store, and record a new document upload.

        Args:
            db: The active database session.
            storage: The storage backend to persist the file to.
            organization_id: The organization to upload the document to.
            actor_id: The id of the user performing the upload.
            upload_file: The incoming file upload.

        Returns:
            The newly created `Document` record.

        Raises:
            OrganizationAccessDeniedError: If the actor is not a member
                of the target organization.
            UnsupportedFileTypeError: If the file's content type is not
                one of the accepted types (PDF, DOCX, TXT).
            FileTooLargeError: If the file exceeds the maximum allowed
                size (re-raised from the storage layer).
        """
        membership = await _get_membership(db, organization_id, actor_id)
        if membership is None:
            raise OrganizationAccessDeniedError("Organization not found.")

        content_type = upload_file.content_type or ""
        extension = ALLOWED_CONTENT_TYPES.get(content_type)
        if extension is None:
            raise UnsupportedFileTypeError(
                "Unsupported file type. Only PDF, DOCX, and TXT files "
                "are accepted."
            )

        storage_key, size_bytes = await storage.save(
            organization_id=organization_id,
            extension=extension,
            file=upload_file,
            max_size_bytes=MAX_UPLOAD_SIZE_BYTES,
        )

        document = Document(
            organization_id=organization_id,
            uploaded_by=actor_id,
            filename=storage_key.rsplit("/", maxsplit=1)[-1],
            original_filename=upload_file.filename or "unnamed",
            content_type=content_type,
            size_bytes=size_bytes,
            storage_key=storage_key,
            status=DocumentStatus.UPLOADED,
        )

        try:
            db.add(document)
            await db.commit()
        except Exception:
            await storage.delete(storage_key)
            raise

        await db.refresh(document)
        return document

    @staticmethod
    async def get_document(
        db: AsyncSession, document_id: uuid.UUID, actor_id: uuid.UUID
    ) -> Document:
        """Fetch a document the actor has access to.

        Args:
            db: The active database session.
            document_id: The document's id.
            actor_id: The id of the requesting user.

        Returns:
            The requested `Document`.

        Raises:
            DocumentNotFoundError: If the document does not exist, or
                the actor is not a member of the document's
                organization.
        """
        document = await db.get(Document, document_id)
        if document is None:
            raise DocumentNotFoundError("Document not found.")

        membership = await _get_membership(db, document.organization_id, actor_id)
        if membership is None:
            raise DocumentNotFoundError("Document not found.")

        return document

    @staticmethod
    async def process_document(
        db: AsyncSession,
        storage: StorageService,
        document_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> Document:
        """Run the text-extraction pipeline for a document the actor can access.

        Args:
            db: The active database session.
            storage: The storage backend the file is persisted in.
            document_id: The document's id.
            actor_id: The id of the user triggering processing.

        Returns:
            The updated `Document`, with `status` set to `COMPLETED` or
            `FAILED` depending on the outcome. This method does not
            raise on extraction failure; only access-control failures
            raise here.

        Raises:
            DocumentNotFoundError: If the document does not exist, or
                the actor is not a member of the document's
                organization.
        """
        document = await DocumentService.get_document(db, document_id, actor_id)
        return await DocumentProcessorService.process_document(db, storage, document)

    @staticmethod
    async def list_documents(
        db: AsyncSession, organization_id: uuid.UUID, actor_id: uuid.UUID
    ) -> list[Document]:
        """List all documents belonging to an organization.

        Args:
            db: The active database session.
            organization_id: The organization's id.
            actor_id: The id of the requesting user.

        Returns:
            A list of `Document` instances, most recently uploaded
            first.

        Raises:
            OrganizationAccessDeniedError: If the actor is not a member
                of the organization.
        """
        membership = await _get_membership(db, organization_id, actor_id)
        if membership is None:
            raise OrganizationAccessDeniedError("Organization not found.")

        result = await db.execute(
            select(Document)
            .where(Document.organization_id == organization_id)
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def delete_document(
        db: AsyncSession,
        storage: StorageService,
        document_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        """Delete a document and its underlying stored file.

        Only the original uploader, or an organization owner/admin, may
        delete a document.

        Args:
            db: The active database session.
            storage: The storage backend the file is persisted in.
            document_id: The document's id.
            actor_id: The id of the user performing the deletion.

        Raises:
            DocumentNotFoundError: If the document does not exist, or
                the actor is not a member of the document's
                organization.
            InsufficientPermissionsError: If the actor is neither the
                uploader nor an owner/admin of the organization.
        """
        document = await db.get(Document, document_id)
        if document is None:
            raise DocumentNotFoundError("Document not found.")

        membership = await _get_membership(db, document.organization_id, actor_id)
        if membership is None:
            raise DocumentNotFoundError("Document not found.")

        is_uploader = document.uploaded_by == actor_id
        is_privileged = membership.role in {MembershipRole.OWNER, MembershipRole.ADMIN}
        if not is_uploader and not is_privileged:
            raise InsufficientPermissionsError(
                "You do not have permission to delete this document."
            )

        await db.delete(document)
        await db.commit()
        await storage.delete(document.storage_key)

    @staticmethod
    async def download_document_path(
        db: AsyncSession,
        storage: StorageService,
        document_id: uuid.UUID,
        actor_id: uuid.UUID,
    ):
        """Resolve the filesystem path for a document's stored file.

        Provided for future use by a file-download endpoint; no route
        currently exposes this method (see scope confirmation).

        Args:
            db: The active database session.
            storage: The storage backend the file is persisted in.
            document_id: The document's id.
            actor_id: The id of the requesting user.

        Returns:
            The absolute path to the document's stored file.

        Raises:
            DocumentNotFoundError: If the document does not exist, or
                the actor is not a member of the document's
                organization.
        """
        document = await DocumentService.get_document(db, document_id, actor_id)
        return storage.get_path(document.storage_key)