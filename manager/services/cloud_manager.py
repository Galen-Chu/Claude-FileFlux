"""
Cloud drive manager for handling cloud storage connections
"""
from typing import Optional, List
from django.utils import timezone

from .base import BaseStorage, FileInfo
from .exceptions import FileOperationError, StorageConnectionError


class CloudDriveManager:
    """
    Manager for cloud drive connections and operations
    Handles OneDrive and Google Drive connections
    """

    @staticmethod
    def connect_drive(user, provider: str, access_token: str, refresh_token: str = None,
                     expires_in: int = 3600) -> bool:
        """
        Connect a cloud drive for a user

        Args:
            user: Django User instance
            provider: 'onedrive' or 'googledrive'
            access_token: OAuth access token
            refresh_token: OAuth refresh token (optional)
            expires_in: Token expiration time in seconds

        Returns:
            True if successful
        """
        from ..models import CloudStorageToken

        expires_at = timezone.now() + timezone.timedelta(seconds=expires_in)

        token, created = CloudStorageToken.objects.update_or_create(
            user=user,
            provider=provider,
            defaults={
                'access_token': access_token,
                'refresh_token': refresh_token or '',
                'token_expires_at': expires_at,
            }
        )

        return True

    @staticmethod
    def disconnect_drive(user, provider: str) -> bool:
        """
        Disconnect a cloud drive for a user

        Args:
            user: Django User instance
            provider: 'onedrive' or 'googledrive'

        Returns:
            True if successful
        """
        from ..models import CloudStorageToken

        deleted_count, _ = CloudStorageToken.objects.filter(
            user=user,
            provider=provider
        ).delete()

        return deleted_count > 0

    @staticmethod
    def is_drive_connected(user, provider: str) -> bool:
        """
        Check if a cloud drive is connected for a user

        Args:
            user: Django User instance
            provider: 'onedrive' or 'googledrive'

        Returns:
            True if connected and token is valid
        """
        from ..models import CloudStorageToken

        try:
            token = CloudStorageToken.objects.get(user=user, provider=provider)
            return not token.is_expired()
        except CloudStorageToken.DoesNotExist:
            return False

    @staticmethod
    def get_connected_drives(user) -> List[dict]:
        """
        Get list of connected cloud drives for a user

        Args:
            user: Django User instance

        Returns:
            List of connected drive info
        """
        from ..models import CloudStorageToken

        tokens = CloudStorageToken.objects.filter(user=user)

        drives = []
        for token in tokens:
            drives.append({
                'provider': token.provider,
                'provider_display': token.get_provider_display(),
                'connected_at': token.created_at,
                'is_expired': token.is_expired(),
            })

        return drives
