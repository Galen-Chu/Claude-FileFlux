"""
Sync local storage with S3 (bi-directional, last-write-wins).

Intended for cron: e.g. `python manage.py sync_storage` every hour.
Use --dry-run to only print the plan.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from manager.models import SyncRun
from manager.services import get_unified_storage
from manager.services.sync_service import SyncService


class Command(BaseCommand):
    help = 'Sync local storage <-> S3 (bi-directional, last-write-wins)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            help='Print the plan without copying anything',
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get('dry_run'))
        run = SyncRun.objects.create(dry_run=dry_run)
        try:
            storage = get_unified_storage()
            service = SyncService(storage.local_storage, storage.s3_storage)
            plan = service.build_plan()

            pushes = sum(1 for a in plan['actions'] if a['direction'] == 'push')
            self.stdout.write(
                f"Plan: {pushes} to upload, {len(plan['actions']) - pushes} to download, "
                f"{plan['unchanged']} unchanged"
            )
            for a in plan['actions']:
                self.stdout.write(f"  [{a['direction']:>4}] {a['reason']:<12} {a['path']}")

            if dry_run:
                run.status = 'success'
                run.finished_at = timezone.now()
                run.save()
                self.stdout.write(self.style.SUCCESS('Dry run — nothing copied.'))
                return

            result = service.execute(plan)

            pushed = sum(1 for x in result['executed'] if x['direction'] == 'push')
            pulled = sum(1 for x in result['executed'] if x['direction'] == 'pull')
            run.pushed = pushed
            run.pulled = pulled
            run.failed_count = len(result['failed'])
            run.status = 'success'
            run.finished_at = timezone.now()
            run.save()

            for f in result['failed']:
                self.stdout.write(self.style.WARNING(f"  failed: {f['path']}: {f['error']}"))

            self.stdout.write(self.style.SUCCESS(
                f"Sync complete: pushed {pushed}, pulled {pulled}, "
                f"failed {len(result['failed'])} (run #{run.id})"
            ))
        except Exception as e:
            run.status = 'failed'
            run.error_message = str(e)[:2000]
            run.finished_at = timezone.now()
            run.save()
            raise
