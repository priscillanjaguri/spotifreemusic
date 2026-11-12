"""Development default: files on the local disk under LIBRARY_STORAGE_DIR."""
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.storage.base import ObjectStorage, StorageError


class LocalFilesystemStorage(ObjectStorage):
    key = "local"

    def __init__(self, root: Path):
        self.root = root.resolve()

    def _path(self, object_key: str) -> Path:
        path = (self.root / object_key).resolve()
        if not path.is_relative_to(self.root):
            raise StorageError("Object key escapes the storage root")
        return path

    def put_file(self, object_key: str, source: Path, content_type: str) -> None:
        dest = self._path(object_key)
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
        except OSError as exc:
            raise StorageError(f"Could not write {object_key}") from exc

    def delete(self, object_key: str) -> None:
        self._path(object_key).unlink(missing_ok=True)

    @contextmanager
    def local_copy(self, object_key: str) -> Iterator[Path]:
        yield self._path(object_key)

    def local_path(self, object_key: str) -> Path | None:
        return self._path(object_key)
