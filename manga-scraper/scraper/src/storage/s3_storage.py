"""
S3 Storage
==========

Handles S3 storage operations for images and files.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)


class S3Storage:
    """
    Handles S3 storage operations for manga images

    Features:
    - Upload images with metadata
    - Generate pre-signed URLs
    - Check file existence
    - Delete files
    - Batch operations
    - Automatic content type detection
    """

    def __init__(
        self,
        bucket_name: str,
        region: str = 'eu-west-3',
        cache_control: str = 'max-age=2592000'  # 30 days
    ):
        """
        Initialize S3 storage handler

        Args:
            bucket_name: S3 bucket name
            region: AWS region
            cache_control: Cache-Control header value
        """
        self.bucket_name = bucket_name
        self.region = region
        self.cache_control = cache_control

        # Initialize S3 client
        self.s3_client = boto3.client('s3', region_name=region)

        logger.info(f"Initialized S3Storage for bucket: {bucket_name}")

    def upload_image(
        self,
        image_data: bytes,
        key: str,
        metadata: Optional[Dict[str, str]] = None,
        content_type: str = 'image/webp',
        make_public: bool = False
    ) -> bool:
        """
        Upload image to S3

        Args:
            image_data: Image bytes
            key: S3 object key (path)
            metadata: Optional metadata dict
            content_type: MIME type
            make_public: Whether to make object publicly readable

        Returns:
            True if successful, False otherwise
        """
        try:
            extra_args = {
                'ContentType': content_type,
                'CacheControl': self.cache_control,
            }

            if metadata:
                extra_args['Metadata'] = metadata

            if make_public:
                extra_args['ACL'] = 'public-read'

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=image_data,
                **extra_args
            )

            logger.info(f"Uploaded to S3: s3://{self.bucket_name}/{key}")
            return True

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error uploading to S3: {e}")
            return False

    def upload_file(
        self,
        file_path: str,
        key: str,
        metadata: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None
    ) -> bool:
        """
        Upload file from filesystem to S3

        Args:
            file_path: Local file path
            key: S3 object key
            metadata: Optional metadata dict
            content_type: Optional MIME type (auto-detected if not provided)

        Returns:
            True if successful
        """
        try:
            extra_args = {
                'CacheControl': self.cache_control,
            }

            if metadata:
                extra_args['Metadata'] = metadata

            if content_type:
                extra_args['ContentType'] = content_type

            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                key,
                ExtraArgs=extra_args
            )

            logger.info(f"Uploaded file to S3: {key}")
            return True

        except (ClientError, BotoCoreError, FileNotFoundError) as e:
            logger.error(f"Error uploading file to S3: {e}")
            return False

    def download_file(self, key: str, local_path: str) -> bool:
        """
        Download file from S3 to local filesystem

        Args:
            key: S3 object key
            local_path: Local file path to save

        Returns:
            True if successful
        """
        try:
            self.s3_client.download_file(
                self.bucket_name,
                key,
                local_path
            )

            logger.info(f"Downloaded from S3: {key} -> {local_path}")
            return True

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error downloading from S3: {e}")
            return False

    def get_object(self, key: str) -> Optional[bytes]:
        """
        Get object data from S3

        Args:
            key: S3 object key

        Returns:
            Object bytes or None if not found
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return response['Body'].read()

        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"Object not found in S3: {key}")
            else:
                logger.error(f"Error getting object from S3: {e}")
            return None

    def exists(self, key: str) -> bool:
        """
        Check if object exists in S3

        Args:
            key: S3 object key

        Returns:
            True if object exists
        """
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True

        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking S3 object existence: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete object from S3

        Args:
            key: S3 object key

        Returns:
            True if successful
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )

            logger.info(f"Deleted from S3: {key}")
            return True

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error deleting from S3: {e}")
            return False

    def delete_multiple(self, keys: List[str]) -> int:
        """
        Delete multiple objects from S3

        Args:
            keys: List of S3 object keys

        Returns:
            Number of successfully deleted objects
        """
        if not keys:
            return 0

        try:
            # S3 delete_objects accepts up to 1000 keys at a time
            deleted_count = 0

            for i in range(0, len(keys), 1000):
                batch = keys[i:i + 1000]
                response = self.s3_client.delete_objects(
                    Bucket=self.bucket_name,
                    Delete={
                        'Objects': [{'Key': key} for key in batch],
                        'Quiet': True
                    }
                )

                deleted = response.get('Deleted', [])
                deleted_count += len(deleted)

            logger.info(f"Deleted {deleted_count} objects from S3")
            return deleted_count

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error deleting multiple objects: {e}")
            return 0

    def list_objects(
        self,
        prefix: str = '',
        max_keys: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        List objects in S3 bucket

        Args:
            prefix: Key prefix to filter
            max_keys: Maximum number of keys to return

        Returns:
            List of object metadata dicts
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )

            objects = []
            for obj in response.get('Contents', []):
                objects.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj['ETag'].strip('"'),
                })

            return objects

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error listing S3 objects: {e}")
            return []

    def generate_presigned_url(
        self,
        key: str,
        expiration: int = 3600
    ) -> Optional[str]:
        """
        Generate pre-signed URL for temporary access

        Args:
            key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)

        Returns:
            Pre-signed URL or None if generation failed
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key
                },
                ExpiresIn=expiration
            )

            logger.debug(f"Generated presigned URL for: {key}")
            return url

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None

    def get_object_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get object metadata

        Args:
            key: S3 object key

        Returns:
            Metadata dict or None
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )

            return {
                'content_type': response.get('ContentType'),
                'content_length': response.get('ContentLength'),
                'last_modified': response.get('LastModified'),
                'etag': response.get('ETag', '').strip('"'),
                'metadata': response.get('Metadata', {}),
                'cache_control': response.get('CacheControl'),
            }

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error getting object metadata: {e}")
            return None

    def copy_object(
        self,
        source_key: str,
        dest_key: str,
        source_bucket: Optional[str] = None
    ) -> bool:
        """
        Copy object within or between buckets

        Args:
            source_key: Source object key
            dest_key: Destination object key
            source_bucket: Source bucket (uses self.bucket_name if not provided)

        Returns:
            True if successful
        """
        try:
            source_bucket = source_bucket or self.bucket_name
            copy_source = {
                'Bucket': source_bucket,
                'Key': source_key
            }

            self.s3_client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket_name,
                Key=dest_key
            )

            logger.info(f"Copied S3 object: {source_key} -> {dest_key}")
            return True

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error copying S3 object: {e}")
            return False

    def get_bucket_size(self, prefix: str = '') -> int:
        """
        Calculate total size of objects with given prefix

        Args:
            prefix: Key prefix to filter

        Returns:
            Total size in bytes
        """
        try:
            total_size = 0
            continuation_token = None

            while True:
                list_kwargs = {
                    'Bucket': self.bucket_name,
                    'Prefix': prefix,
                }

                if continuation_token:
                    list_kwargs['ContinuationToken'] = continuation_token

                response = self.s3_client.list_objects_v2(**list_kwargs)

                for obj in response.get('Contents', []):
                    total_size += obj['Size']

                if not response.get('IsTruncated'):
                    break

                continuation_token = response.get('NextContinuationToken')

            return total_size

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error calculating bucket size: {e}")
            return 0
