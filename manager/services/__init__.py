"""
Services package for FileFlux
"""

from django.conf import settings

from .base import BaseStorage, FileInfo
from .local_storage import LocalStorage
from .s3_storage import S3Storage
from .unified_storage import UnifiedStorage
from .google_drive_service import GoogleDriveService
from .onedrive_service import OneDriveService
from .exceptions import (
    FileOperationError,
    FileNotFoundError,
    PermissionDeniedError,
    StorageConnectionError,
    InvalidPathError,
    FileSizeExceededError,
)

__all__ = [
    'BaseStorage',
    'FileInfo',
    'LocalStorage',
    'S3Storage',
    'UnifiedStorage',
    'GoogleDriveService',
    'OneDriveService',
    'FileOperationError',
    'FileNotFoundError',
    'PermissionDeniedError',
    'StorageConnectionError',
    'InvalidPathError',
    'FileSizeExceededError',
    'get_local_storage',
    'get_s3_storage',
    'get_unified_storage',
]


# Factory functions
_local_storage_instance = None
_s3_storage_instance = None
_unified_storage_instance = None


def get_local_storage() -> LocalStorage:
    """
    Get or create local storage instance

    Returns:
        LocalStorage instance
    """
    global _local_storage_instance

    if _local_storage_instance is None:
        _local_storage_instance = LocalStorage(
            base_path=settings.LOCAL_STORAGE_PATH
        )

    return _local_storage_instance


def get_s3_storage() -> S3Storage:
    """
    Get or create S3 storage instance

    Returns:
        S3Storage instance
    """
    global _s3_storage_instance

    if _s3_storage_instance is None:
        _s3_storage_instance = S3Storage(
            bucket_name=settings.AWS_STORAGE_BUCKET_NAME,
            region=settings.AWS_REGION,
            access_key=settings.AWS_ACCESS_KEY_ID,
            secret_key=settings.AWS_SECRET_ACCESS_KEY,
        )

    return _s3_storage_instance


def get_unified_storage() -> UnifiedStorage:
    """
    Get or create unified storage instance

    Returns:
        UnifiedStorage instance
    """
    global _unified_storage_instance

    if _unified_storage_instance is None:
        _unified_storage_instance = UnifiedStorage(
            local_storage=get_local_storage(),
            s3_storage=get_s3_storage(),
        )

    return _unified_storage_instance
