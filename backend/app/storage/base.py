"""Where uploaded music files live. Nothing outside `app.storage` knows which backend is active."""
from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class StorageError(Exception):
    """The storage backend failed (disk, network or credentials)."""


class ObjectStorage(ABC):
    key: str  # stored in library_uploads.storage_backend

    @abstractmethod
    def put_file(self, object_key: str, source: Path, content_type: str) -> None:
        """Store the file at `source` under `object_key` (overwrites)."""

    @abstractmethod
    def delete(self, object_key: str) -> None:
        """Remove an object. Missing objects are not an error."""

    @abstractmethod
    @contextmanager
    def local_copy(self, object_key: str) -> Iterator[Path]:
        """A local path to the object for the duration of the block (for audio analysis)."""

    def local_path(self, object_key: str) -> Path | None:
        """Path on this machine, when the backend is the local disk; None otherwise."""
        return None

    def presigned_url(self, object_key: str, content_type: str, expires_seconds: int) -> str | None:
        """A short-lived direct URL, when the backend supports it; None otherwise."""
        return None
