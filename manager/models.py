from django.db import models
from django.utils import timezone
from datetime import timedelta

from .fields import EncryptedTextField


class FileOperation(models.Model):
    """Model for logging file operations"""

    OPERATION_CHOICES = [
        ('UPLOAD', 'Upload'),
        ('DOWNLOAD', 'Download'),
        ('RENAME', 'Rename'),
        ('DELETE', 'Delete'),
        ('MOVE', 'Move'),
    ]

    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='file_operations',
        null=True,
        blank=True,
        help_text='User who performed the operation (null for legacy/system rows)'
    )
    operation = models.CharField(
        max_length=20,
        choices=OPERATION_CHOICES,
        help_text='Type of file operation'
    )
    source = models.CharField(
        max_length=10,
        help_text='Storage source (local or s3)'
    )
    file_path = models.CharField(
        max_length=500,
        help_text='File path operated on'
    )
    old_path = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='Original path (for rename operations)'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text='When the operation occurred'
    )
    success = models.BooleanField(
        default=True,
        help_text='Whether the operation succeeded'
    )
    error_message = models.TextField(
        blank=True,
        default='',
        help_text='Error message if operation failed'
    )
    file_size = models.BigIntegerField(
        null=True,
        blank=True,
        help_text='File size in bytes (if applicable)'
    )

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['operation']),
            models.Index(fields=['source']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        status = '✓' if self.success else '✗'
        return f"{status} {self.get_operation_display()} - {self.file_path}"


class SyncRun(models.Model):
    """Summary record of one local <-> S3 sync execution"""

    STATUS_CHOICES = [
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]

    dry_run = models.BooleanField(
        default=False,
        help_text='True if the plan was only simulated'
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When the run started'
    )
    finished_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the run finished (null while running)'
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='running',
        help_text='Run status'
    )
    pushed = models.IntegerField(
        default=0,
        help_text='Files copied local -> S3'
    )
    pulled = models.IntegerField(
        default=0,
        help_text='Files copied S3 -> local'
    )
    failed_count = models.IntegerField(
        default=0,
        help_text='Files that failed to copy'
    )
    error_message = models.TextField(
        blank=True,
        default='',
        help_text='Fatal error message if the run failed'
    )

    def __str__(self):
        return f"Sync #{self.id} ({self.status}{', dry-run' if self.dry_run else ''})"


class CloudStorageToken(models.Model):
    """Store OAuth tokens for cloud storage providers"""

    PROVIDER_CHOICES = [
        ('onedrive', 'Microsoft OneDrive'),
        ('googledrive', 'Google Drive'),
    ]

    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='cloud_tokens'
    )
    provider = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES,
        help_text='Cloud storage provider'
    )
    access_token = EncryptedTextField(
        help_text='OAuth 2.0 access token (encrypted at rest)'
    )
    refresh_token = EncryptedTextField(
        blank=True,
        default='',
        help_text='OAuth 2.0 refresh token (encrypted at rest)'
    )
    token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Token expiration timestamp'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When the token was created'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='When the token was last updated'
    )

    class Meta:
        unique_together = ['user', 'provider']
        indexes = [
            models.Index(fields=['user', 'provider']),
        ]

    def is_expired(self):
        """Check if token is expired"""
        if not self.token_expires_at:
            return True
        return timezone.now() >= self.token_expires_at

    def __str__(self):
        return f"{self.user.username} - {self.get_provider_display()}"

