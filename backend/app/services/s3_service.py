import logging
from typing import Optional, Set
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings

logger = logging.getLogger(__name__)


class S3Service:
    def __init__(self):
        self.bucket = settings.AWS_S3_BUCKET
        self.is_configured = bool(
            settings.AWS_ACCESS_KEY_ID
            and settings.AWS_SECRET_ACCESS_KEY
            and settings.AWS_ACCESS_KEY_ID != "mock-access-key-id"
        )
        self._mock_objects: Set[str] = set()

        if self.is_configured:
            self.client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
        else:
            self.client = None

    def generate_presigned_upload_url(
        self,
        storage_key: str,
        mime_type: str,
        expires_in: int = 300
    ) -> str:
        """Generate presigned PUT upload URL."""
        if self.is_configured and self.client:
            try:
                url = self.client.generate_presigned_url(
                    ClientMethod="put_object",
                    Params={
                        "Bucket": self.bucket,
                        "Key": storage_key,
                        "ContentType": mime_type
                    },
                    ExpiresIn=expires_in
                )
                return url
            except ClientError as e:
                logger.error(f"S3 presigned upload URL error: {e}")
                raise

        # Mock fallback for development and automated tests
        self._mock_objects.add(storage_key)
        return f"https://{self.bucket}.s3.{settings.AWS_REGION}.amazonaws.com/{storage_key}?mock_presigned_upload=true&expires={expires_in}"

    def generate_presigned_download_url(
        self,
        storage_key: str,
        expires_in: int = 120
    ) -> str:
        """Generate presigned GET download URL."""
        if self.is_configured and self.client:
            try:
                url = self.client.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={
                        "Bucket": self.bucket,
                        "Key": storage_key
                    },
                    ExpiresIn=expires_in
                )
                return url
            except ClientError as e:
                logger.error(f"S3 presigned download URL error: {e}")
                raise

        # Mock fallback for development and automated tests
        return f"https://{self.bucket}.s3.{settings.AWS_REGION}.amazonaws.com/{storage_key}?mock_presigned_download=true&expires={expires_in}"

    def check_object_exists(self, storage_key: str) -> bool:
        """Verify that the object exists in S3."""
        if self.is_configured and self.client:
            try:
                self.client.head_object(Bucket=self.bucket, Key=storage_key)
                return True
            except ClientError:
                return False

        # In mock mode, if registered or simulated, returns True
        return storage_key in self._mock_objects or True

    def delete_object(self, storage_key: str) -> bool:
        """Delete object from S3."""
        if self.is_configured and self.client:
            try:
                self.client.delete_object(Bucket=self.bucket, Key=storage_key)
                return True
            except ClientError as e:
                logger.error(f"Failed to delete S3 object {storage_key}: {e}")
                return False

        if storage_key in self._mock_objects:
            self._mock_objects.remove(storage_key)
        return True


s3_service = S3Service()
