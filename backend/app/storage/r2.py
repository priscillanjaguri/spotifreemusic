"""Cloudflare R2 through its S3-compatible API (boto3).

Playback never proxies audio through our server: the stream endpoint checks ownership,
then redirects to a presigned GET URL that expires after R2_PRESIGN_SECONDS.
"""
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.storage.base import ObjectStorage, StorageError


class R2Storage(ObjectStorage):
    key = "r2"

    def __init__(self, account_id: str, access_key_id: str, secret_access_key: str, bucket: str, client=None):
        self.bucket = bucket
        if client is None:
            import boto3
            from botocore.config import Config

            client = boto3.client(
                "s3",
                endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                region_name="auto",
                config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
            )
        self.client = client

    def put_file(self, object_key: str, source: Path, content_type: str) -> None:
        from botocore.exceptions import BotoCoreError, ClientError

        try:
            with source.open("rb") as fh:
                self.client.put_object(Bucket=self.bucket, Key=object_key, Body=fh, ContentType=content_type)
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(f"R2 upload failed: {exc.__class__.__name__}") from exc

    def delete(self, object_key: str) -> None:
        from botocore.exceptions import BotoCoreError, ClientError

        try:
            self.client.delete_object(Bucket=self.bucket, Key=object_key)
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(f"R2 delete failed: {exc.__class__.__name__}") from exc

    @contextmanager
    def local_copy(self, object_key: str) -> Iterator[Path]:
        from botocore.exceptions import BotoCoreError, ClientError

        with tempfile.TemporaryDirectory(prefix="spotifree-r2-") as tmp:
            path = Path(tmp) / Path(object_key).name
            try:
                self.client.download_file(self.bucket, object_key, str(path))
            except (BotoCoreError, ClientError) as exc:
                raise StorageError(f"R2 download failed: {exc.__class__.__name__}") from exc
            yield path

    def presigned_url(self, object_key: str, content_type: str, expires_seconds: int) -> str | None:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": object_key, "ResponseContentType": content_type},
            ExpiresIn=expires_seconds,
        )
