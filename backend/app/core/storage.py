"""Storage abstraction for uploaded files.

Defines the `StorageService` interface and a `LocalStorageService`
implementation that stores files on the local filesystem, organized by
organization id. Future backends (e.g. S3) can implement the same
interface without changing any calling code.
"""

import uuid
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

from fastapi import UploadFile

_READ_CHUNK_SIZE = 1024 * 1024  # 1 MiB
_MAX_UNIQUE_FILENAME_ATTEMPTS = 10


class StorageError(Exception):
    """Base exception for storage backend failures."""


class FileTooLargeError(StorageError):
    """Raised when an uploaded file exceeds the allowed maximum size."""


class StorageKeyGenerationError(StorageError):
    """Raised when a unique storage filename could not be generated."""


class StorageService(ABC):
    """Interface for storing, retrieving, and deleting uploaded files.

    Implementations are responsible for guaranteeing that each saved
    file receives a unique storage key and that existing files are
    never overwritten.
    """

    @abstractmethod
    async def save(
        self,
        organization_id: uuid.UUID,
        extension: str,
        file: UploadFile,
        max_size_bytes: int,
    ) -> tuple[str, int]:
        """Persist an uploaded file's contents.

        Args:
            organization_id: The organization the file belongs to, used
                to namespace storage.
            extension: The file extension to use for the stored file
                (e.g. `".pdf"`), determined server-side from the
                validated content type rather than trusted from the
                client's filename.
            file: The uploaded file to read and persist.
            max_size_bytes: The maximum allowed file size, in bytes.

        Returns:
            A tuple of `(storage_key, size_bytes)`, where `storage_key`
            uniquely identifies the stored file and `size_bytes` is the
            number of bytes written.

        Raises:
            FileTooLargeError: If the file exceeds `max_size_bytes`.
            StorageKeyGenerationError: If a unique storage location
                could not be generated.
        """

    @abstractmethod
    def get_path(self, storage_key: str) -> Path:
        """Resolve a storage key to an absolute filesystem path.

        Args:
            storage_key: The storage key previously returned by `save`.

        Returns:
            The absolute path to the stored file.
        """

    @abstractmethod
    async def delete(self, storage_key: str) -> None:
        """Delete a previously stored file.

        Args:
            storage_key: The storage key of the file to delete.

        Note:
            Implementations should treat deleting a already-missing
            file as a no-op rather than an error, since callers may
            invoke this as a best-effort cleanup step.
        """


class LocalStorageService(StorageService):
    """Stores files on the local filesystem under a `storage/` directory.

    Files are organized as `storage/<organization_id>/<unique_filename>`.
    Each saved file receives a randomly generated filename, so existing
    files are never overwritten.
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        """Initialize the local storage backend.

        Args:
            base_dir: The root directory under which files are stored.
                Defaults to a `storage/` directory at the project root.
        """
        self._base_dir = base_dir or (
            Path(__file__).resolve().parent.parent.parent / "storage"
        )
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _organization_dir(self, organization_id: uuid.UUID) -> Path:
        """Return (creating if needed) the directory for an organization.

        Args:
            organization_id: The organization's id.

        Returns:
            The absolute path to the organization's storage directory.
        """
        org_dir = self._base_dir / str(organization_id)
        org_dir.mkdir(parents=True, exist_ok=True)
        return org_dir

    def _generate_unique_filename(self, org_dir: Path, extension: str) -> str:
        """Generate a filename guaranteed not to collide within `org_dir`.

        Args:
            org_dir: The organization's storage directory.
            extension: The file extension to append (e.g. `".pdf"`).

        Returns:
            A unique filename, not currently present in `org_dir`.

        Raises:
            StorageKeyGenerationError: If a unique filename could not
                be generated after a reasonable number of attempts.
        """
        for _ in range(_MAX_UNIQUE_FILENAME_ATTEMPTS):
            candidate = f"{uuid.uuid4().hex}{extension}"
            if not (org_dir / candidate).exists():
                return candidate

        raise StorageKeyGenerationError(
            "Could not generate a unique storage filename."
        )

    async def save(
        self,
        organization_id: uuid.UUID,
        extension: str,
        file: UploadFile,
        max_size_bytes: int,
    ) -> tuple[str, int]:
        """Persist an uploaded file's contents to the local filesystem.

        Reads the upload in fixed-size chunks so the size limit is
        enforced without needing to buffer the entire file in memory
        first. If the limit is exceeded, the partially written file is
        removed before raising.

        Args:
            organization_id: The organization the file belongs to.
            extension: The file extension to use for the stored file.
            file: The uploaded file to read and persist.
            max_size_bytes: The maximum allowed file size, in bytes.

        Returns:
            A tuple of `(storage_key, size_bytes)`.

        Raises:
            FileTooLargeError: If the file exceeds `max_size_bytes`.
            StorageKeyGenerationError: If a unique storage location
                could not be generated.
        """
        org_dir = self._organization_dir(organization_id)
        stored_filename = self._generate_unique_filename(org_dir, extension)
        destination = org_dir / stored_filename

        size_bytes = 0
        try:
            with destination.open("wb") as buffer:
                while True:
                    chunk = await file.read(_READ_CHUNK_SIZE)
                    if not chunk:
                        break
                    size_bytes += len(chunk)
                    if size_bytes > max_size_bytes:
                        raise FileTooLargeError(
                            f"File exceeds the maximum allowed size of "
                            f"{max_size_bytes} bytes."
                        )
                    buffer.write(chunk)
        except FileTooLargeError:
            destination.unlink(missing_ok=True)
            raise
        except Exception:
            destination.unlink(missing_ok=True)
            raise

        storage_key = f"{organization_id}/{stored_filename}"
        return storage_key, size_bytes

    def get_path(self, storage_key: str) -> Path:
        """Resolve a storage key to an absolute filesystem path.

        Args:
            storage_key: The storage key previously returned by `save`.

        Returns:
            The absolute path to the stored file.
        """
        return self._base_dir / storage_key

    async def delete(self, storage_key: str) -> None:
        """Delete a stored file, ignoring the case where it is already gone.

        Args:
            storage_key: The storage key of the file to delete.
        """
        self.get_path(storage_key).unlink(missing_ok=True)


@lru_cache
def get_storage_service() -> StorageService:
    """Return a cached, singleton `StorageService` instance.

    Returns:
        A `LocalStorageService` instance, suitable for injection via
        FastAPI's `Depends`.
    """
    return LocalStorageService()