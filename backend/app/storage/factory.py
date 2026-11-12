from functools import lru_cache

from app.core.config import get_settings
from app.storage.base import ObjectStorage
from app.storage.local import LocalFilesystemStorage


@lru_cache
def _r2(account_id: str, access_key_id: str, secret_access_key: str, bucket: str) -> ObjectStorage:
    from app.storage.r2 import R2Storage

    return R2Storage(account_id, access_key_id, secret_access_key, bucket)


def get_storage() -> ObjectStorage:
    """FastAPI dependency: R2 when all four R2_* settings are present, otherwise the local disk."""
    s = get_settings()
    if s.r2_enabled:
        return _r2(s.r2_account_id, s.r2_access_key_id, s.r2_secret_access_key, s.r2_bucket)  # type: ignore[arg-type]
    return LocalFilesystemStorage(s.library_storage_dir)
