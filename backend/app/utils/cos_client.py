"""
utils/cos_client.py — IBM Cloud Object Storage Client
======================================================
Wraps the ibm-cos-sdk to upload and retrieve resume files.

IBM Cloud Object Storage (COS) is S3-compatible, so the API looks
similar to AWS S3 but uses IBM-specific authentication.

Why store files in COS instead of on disk?
  - The server disk is wiped on every IBM Cloud deployment
  - COS persists forever and is accessible from any instance
  - Supports large files with automatic redundancy

Graceful fallback:
  If COS credentials are not configured (e.g., local development
  before IBM account setup), files are kept on local disk and a
  warning is logged. Zero code changes needed when you add COS later.

Usage:
    from app.utils.cos_client import cos_client
    url = cos_client.upload_file(local_path, object_name)
"""

import os
from app.config import settings
from app.utils.logger import logger


class COSClient:
    """
    IBM Cloud Object Storage client wrapper.
    Initialises lazily — only connects when first used.
    """

    def __init__(self):
        self._client = None   # lazy init — only created when needed

    def _get_client(self):
        """
        Create the COS client on first use.
        Returns None if credentials are not configured.
        """
        if self._client is not None:
            return self._client

        # Check if credentials are configured
        if not settings.cos_api_key or settings.cos_api_key == "your-cos-api-key-here":
            logger.warning(
                "COS credentials not configured. "
                "Files will be stored locally only. "
                "Set COS_API_KEY and COS_INSTANCE_CRN in .env to enable cloud storage."
            )
            return None

        try:
            import ibm_boto3
            from ibm_botocore.client import Config, IBMApiKeyCredentials

            self._client = ibm_boto3.client(
                "s3",
                ibm_api_key_id=settings.cos_api_key,
                ibm_service_instance_id=settings.cos_instance_crn,
                config=Config(signature_version="oauth"),
                endpoint_url=settings.cos_endpoint,
            )
            logger.info("IBM Cloud Object Storage client initialised.")
            return self._client

        except ImportError:
            logger.warning("ibm-cos-sdk not installed. Using local storage.")
            return None
        except Exception as e:
            logger.error(f"COS client init failed: {e}. Using local storage.")
            return None

    def upload_file(self, local_path: str, object_name: str) -> str:
        """
        Upload a file to IBM Cloud Object Storage.

        Args:
            local_path  : path to the file on disk
            object_name : the key/name to store it as in COS

        Returns:
            COS URL string if upload succeeded,
            local file path as fallback if COS is unavailable.
        """
        client = self._get_client()

        if client is None:
            # Fallback: return local path as the "URL"
            logger.info(f"COS unavailable — file kept locally: {local_path}")
            return f"local://{local_path}"

        try:
            # Ensure the bucket exists
            self._ensure_bucket(client)

            # Upload the file
            with open(local_path, "rb") as f:
                client.upload_fileobj(
                    f,
                    settings.cos_bucket_name,
                    object_name,
                )

            # Build the public URL
            cos_url = (
                f"{settings.cos_endpoint}/{settings.cos_bucket_name}/{object_name}"
            )
            logger.info(f"File uploaded to COS: {cos_url}")
            return cos_url

        except Exception as e:
            logger.error(f"COS upload failed: {e}. File kept locally.")
            return f"local://{local_path}"

    def _ensure_bucket(self, client) -> None:
        """Create the COS bucket if it does not already exist."""
        try:
            client.head_bucket(Bucket=settings.cos_bucket_name)
        except Exception:
            try:
                client.create_bucket(Bucket=settings.cos_bucket_name)
                logger.info(f"COS bucket created: {settings.cos_bucket_name}")
            except Exception as e:
                logger.warning(f"Could not create COS bucket: {e}")

    def delete_file(self, object_name: str) -> bool:
        """Delete a file from COS. Returns True if successful."""
        client = self._get_client()
        if client is None:
            return False
        try:
            client.delete_object(
                Bucket=settings.cos_bucket_name,
                Key=object_name,
            )
            return True
        except Exception as e:
            logger.error(f"COS delete failed: {e}")
            return False


# Module-level singleton — import this everywhere
# from app.utils.cos_client import cos_client
cos_client = COSClient()
