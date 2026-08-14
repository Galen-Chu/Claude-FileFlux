"""
One-time setup: enable versioning on the configured S3 bucket.

Requires bucket owner permissions. After this, every overwrite/delete keeps
prior versions, which /api/files/versions/ can list and restore.
"""
from django.core.management.base import BaseCommand

from manager.services import get_s3_storage


class Command(BaseCommand):
    help = 'Enable versioning on the configured S3 bucket (one-time setup)'

    def handle(self, *args, **options):
        s3 = get_s3_storage()
        s3.client.put_bucket_versioning(
            Bucket=s3.bucket_name,
            VersioningConfiguration={'Status': 'Enabled'},
        )
        self.stdout.write(self.style.SUCCESS(
            f"Versioning enabled for bucket '{s3.bucket_name}'"
        ))
