"""
Test suite for FileFlux.

Covers models, at-rest encryption, local-storage logic, the cloud-service
interface, API auth/routing, and OAuth state CSRF handling. No network access
is required: cloud providers are exercised only through their offline helpers
(_format_item), the interface contract (instantiation), and the view-layer
routing/error paths.
"""
import os
import tempfile
import time
from datetime import datetime, timezone as dt_timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase, Client, override_settings

from rest_framework.test import APIClient

from .models import FileOperation, CloudStorageToken, SyncRun
from .services.base import FileInfo
from .services.local_storage import LocalStorage
from .services.google_drive_service import GoogleDriveService
from .services.onedrive_service import OneDriveService
from .services.cloud_manager import CloudDriveManager
from .services.cloud_base import CloudStorageService
from .services.sync_service import SyncService


def make_info(path, epoch, source='s3'):
    """Build a FileInfo with a tz-aware mtime that maps exactly to `epoch`."""
    return FileInfo(
        name=path.split('/')[-1], path=path, size=10,
        modified_time=datetime.fromtimestamp(epoch, tz=dt_timezone.utc),
        source=source,
    )


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class FileOperationModelTest(TestCase):
    def test_user_link(self):
        user = User.objects.create_user('fo', password='x')
        op = FileOperation.objects.create(operation='RENAME', user=user, source='local', file_path='a.txt')
        self.assertEqual(op.user, user)
        self.assertTrue(op.success)  # default True

    def test_legacy_null_user_allowed(self):
        op = FileOperation.objects.create(operation='UPLOAD', source='s3', file_path='a')
        self.assertIsNone(op.user)  # nullable for legacy/system rows


class CloudStorageTokenModelTest(TestCase):
    def test_is_expired_when_no_expiry(self):
        user = User.objects.create_user('tk', password='x')
        tok = CloudStorageToken.objects.create(user=user, provider='googledrive', access_token='a')
        self.assertTrue(tok.is_expired())  # no expiry -> treated as expired


# ---------------------------------------------------------------------------
# Encryption at rest
# ---------------------------------------------------------------------------
class EncryptionTest(TestCase):
    def test_token_encrypted_at_rest(self):
        user = User.objects.create_user('enc', password='x')
        CloudDriveManager.connect_drive(
            user=user, provider='googledrive',
            access_token='plaintext-secret', refresh_token='refresh-secret', expires_in=3600,
        )
        # Raw DB value must be ciphertext, not the plaintext
        with connection.cursor() as c:
            c.execute(
                "SELECT access_token, refresh_token FROM manager_cloudstoragetoken WHERE user_id=%s",
                [user.id],
            )
            raw_access, raw_refresh = c.fetchone()
        self.assertNotIn('plaintext-secret', raw_access)
        self.assertNotIn('refresh-secret', raw_refresh)
        self.assertTrue(raw_access.startswith('gAAAAA'))  # Fernet token prefix

        # ORM read transparently decrypts back to plaintext
        tok = CloudStorageToken.objects.get(user=user, provider='googledrive')
        self.assertEqual(tok.access_token, 'plaintext-secret')
        self.assertEqual(tok.refresh_token, 'refresh-secret')


# ---------------------------------------------------------------------------
# Local storage logic (isolated temp dir, no network)
# ---------------------------------------------------------------------------
class LocalStorageTest(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.storage = LocalStorage(base_path=self.tmp.name)
        for name in ('a.txt', 'b.txt', 'c.txt'):
            (Path(self.tmp.name) / name).write_text('x')

    def tearDown(self):
        self.tmp.cleanup()

    def test_list_files(self):
        files = sorted(f.name for f in self.storage.list_files())
        self.assertEqual(files, ['a.txt', 'b.txt', 'c.txt'])

    def test_rename_prefix(self):
        result = self.storage.rename_files(['a.txt'], 'pre_', mode='prefix')
        self.assertEqual(result['success'][0]['new_path'], 'pre_a.txt')
        self.assertTrue((Path(self.tmp.name) / 'pre_a.txt').exists())

    def test_rename_replace(self):
        result = self.storage.rename_files(['a.txt'], 'NEW', mode='replace', find_text='a')
        self.assertEqual(result['success'][0]['new_path'], 'NEW.txt')

    def test_rename_sequence(self):
        result = self.storage.rename_files(
            ['a.txt', 'b.txt'], 'img_', mode='prefix', add_sequence=True, start_number=1
        )
        new_paths = sorted(s['new_path'] for s in result['success'])
        self.assertEqual(new_paths, ['img_a_001.txt', 'img_b_002.txt'])

    def test_delete_files(self):
        result = self.storage.delete_files(['a.txt'])
        self.assertIn('a.txt', result['success'])
        self.assertFalse((Path(self.tmp.name) / 'a.txt').exists())

    def test_path_traversal_blocked(self):
        result = self.storage.rename_files(['../evil.txt'], 'x', mode='prefix')
        self.assertEqual(len(result['failed']), 1)
        self.assertEqual(len(result['success']), 0)


# ---------------------------------------------------------------------------
# Cloud service interface + offline formatter
# ---------------------------------------------------------------------------
class CloudServiceInterfaceTest(TestCase):
    def test_services_instantiate_and_conform(self):
        user = User.objects.create_user('sv', password='x')
        CloudDriveManager.connect_drive(user=user, provider='googledrive', access_token='a', refresh_token='r', expires_in=3600)
        CloudDriveManager.connect_drive(user=user, provider='onedrive', access_token='a', refresh_token='r', expires_in=3600)

        gtok = CloudStorageToken.objects.get(user=user, provider='googledrive')
        otok = CloudStorageToken.objects.get(user=user, provider='onedrive')
        # Instantiation succeeds only if every abstract method is implemented
        self.assertIsInstance(GoogleDriveService(gtok), CloudStorageService)
        self.assertIsInstance(OneDriveService(otok), CloudStorageService)


class OneDriveServiceFormatTest(TestCase):
    def test_format_file(self):
        item = {
            'id': '1', 'name': 'f.pdf', 'size': 10,
            'lastModifiedDateTime': '2026-01-01T00:00:00Z',
            'file': {'mimeType': 'application/pdf'},
            'parentReference': {'id': 'root'}, 'webUrl': 'u',
        }
        d = OneDriveService._format_item(item)
        self.assertEqual(d['type'], 'file')
        self.assertEqual(d['source'], 'onedrive')
        self.assertEqual(d['mime_type'], 'application/pdf')

    def test_format_folder(self):
        item = {
            'id': '2', 'name': 'Folder', 'size': 0,
            'lastModifiedDateTime': '2026-01-01T00:00:00Z',
            'folder': {'childCount': 1},
            'parentReference': {'id': 'root'}, 'webUrl': 'u',
        }
        d = OneDriveService._format_item(item)
        self.assertEqual(d['type'], 'folder')
        self.assertEqual(d['mime_type'], '')


class CloudDriveManagerTest(TestCase):
    def test_connect_disconnect(self):
        user = User.objects.create_user('cm', password='x')
        self.assertFalse(CloudDriveManager.is_drive_connected(user, 'googledrive'))
        CloudDriveManager.connect_drive(user=user, provider='googledrive', access_token='a', refresh_token='r', expires_in=3600)
        self.assertTrue(CloudDriveManager.is_drive_connected(user, 'googledrive'))
        drives = CloudDriveManager.get_connected_drives(user)
        self.assertEqual(len(drives), 1)
        CloudDriveManager.disconnect_drive(user, 'googledrive')
        self.assertFalse(CloudDriveManager.is_drive_connected(user, 'googledrive'))


# ---------------------------------------------------------------------------
# API: auth + routing
# ---------------------------------------------------------------------------
class FileManagementAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('api', password='x')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_anon_blocked(self):
        c = APIClient()
        r = c.get('/api/files/')
        self.assertIn(r.status_code, (401, 403))

    def test_authed_local_list(self):
        r = self.client.get('/api/files/?source=local')
        self.assertEqual(r.status_code, 200)
        self.assertIn('files', r.data)

    def test_logs_endpoint(self):
        r = self.client.get('/api/files/logs/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('logs', r.data)


class FileSearchAPITest(TestCase):
    """Server-side filename search over local/S3 listings."""

    def setUp(self):
        import manager.services as svc
        self._svc = svc
        self.tmp = tempfile.TemporaryDirectory()
        for name in ('invoice_jan.txt', 'invoice_feb.txt', 'photo.jpg'):
            (Path(self.tmp.name) / name).write_text('x')
        self.user = User.objects.create_user('search', password='x')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        # Drop cached storage singletons so other tests get fresh instances.
        self._svc._local_storage_instance = None
        self._svc._s3_storage_instance = None
        self._svc._unified_storage_instance = None
        self.tmp.cleanup()

    def test_search_filters_by_name(self):
        self._svc._local_storage_instance = None
        self._svc._unified_storage_instance = None
        with override_settings(LOCAL_STORAGE_PATH=self.tmp.name):
            r = self.client.get('/api/files/?source=local&search=invoice')
            self.assertEqual(r.status_code, 200)
            names = sorted(f['name'] for f in r.data['files'])
            self.assertEqual(names, ['invoice_feb.txt', 'invoice_jan.txt'])

            # Case-insensitive
            r2 = self.client.get('/api/files/?source=local&search=INVOICE')
            self.assertEqual(len(r2.data['files']), 2)

            # No match -> empty list, still 200
            r3 = self.client.get('/api/files/?source=local&search=zzznomatch')
            self.assertEqual(r3.status_code, 200)
            self.assertEqual(r3.data['count'], 0)


class FilePaginationAPITest(TestCase):
    """Page-number pagination of local/S3 listings."""

    def setUp(self):
        import manager.services as svc
        self._svc = svc
        self.tmp = tempfile.TemporaryDirectory()
        for i in range(60):  # two pages at page_size=50
            (Path(self.tmp.name) / f'file_{i:03d}.txt').write_text('x')
        self.user = User.objects.create_user('page', password='x')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        self._svc._local_storage_instance = None
        self._svc._s3_storage_instance = None
        self._svc._unified_storage_instance = None
        self.tmp.cleanup()

    def _reset(self):
        self._svc._local_storage_instance = None
        self._svc._s3_storage_instance = None
        self._svc._unified_storage_instance = None

    def test_first_page(self):
        self._reset()
        with override_settings(LOCAL_STORAGE_PATH=self.tmp.name):
            r = self.client.get('/api/files/?source=local&page=1&page_size=50')
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.data['total'], 60)
            self.assertEqual(r.data['page'], 1)
            self.assertTrue(r.data['has_next'])
            self.assertEqual(r.data['next_page'], 2)
            self.assertEqual(len(r.data['files']), 50)

    def test_last_page(self):
        self._reset()
        with override_settings(LOCAL_STORAGE_PATH=self.tmp.name):
            r = self.client.get('/api/files/?source=local&page=2&page_size=50')
            self.assertEqual(r.status_code, 200)
            self.assertEqual(len(r.data['files']), 10)
            self.assertFalse(r.data['has_next'])
            self.assertIsNone(r.data['next_page'])


class DownloadFileAPITest(TestCase):
    """Browser streaming download of a local file."""

    def setUp(self):
        import manager.services as svc
        self._svc = svc
        self.tmp = tempfile.TemporaryDirectory()
        (Path(self.tmp.name) / 'doc.txt').write_text('hello world')
        self.user = User.objects.create_user('dl', password='x')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        self._svc._local_storage_instance = None
        self._svc._s3_storage_instance = None
        self._svc._unified_storage_instance = None
        self.tmp.cleanup()

    def _reset(self):
        self._svc._local_storage_instance = None
        self._svc._s3_storage_instance = None
        self._svc._unified_storage_instance = None

    def test_download_local_file(self):
        self._reset()
        with override_settings(LOCAL_STORAGE_PATH=self.tmp.name):
            r = self.client.get('/api/files/download-file/?source=local&path=doc.txt')
            self.assertEqual(r.status_code, 200)
            self.assertIn('attachment', r['Content-Disposition'])
            self.assertIn('doc.txt', r['Content-Disposition'])
            content = b''.join(r.streaming_content)
            self.assertEqual(content, b'hello world')
            r.close()  # release the file handle so tearDown can clean up (Windows)

    def test_download_not_found(self):
        self._reset()
        with override_settings(LOCAL_STORAGE_PATH=self.tmp.name):
            r = self.client.get('/api/files/download-file/?source=local&path=missing.txt')
            self.assertEqual(r.status_code, 404)

    def test_download_inline_for_preview(self):
        self._reset()
        with override_settings(LOCAL_STORAGE_PATH=self.tmp.name):
            r = self.client.get('/api/files/download-file/?source=local&path=doc.txt&inline=1')
            self.assertEqual(r.status_code, 200)
            # inline (preview) -> no attachment disposition
            self.assertNotIn('attachment', r['Content-Disposition'] or '')
            r.close()  # release the file handle so tearDown can clean up (Windows)


class ShareLinkAPITest(TestCase):
    """S3 presigned share-link generation (boto3 is mocked)."""

    def setUp(self):
        self.user = User.objects.create_user('share', password='x')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @patch('manager.api_views.get_s3_storage')
    def test_share_generates_presigned_url(self, mock_get):
        mock_s3 = MagicMock()
        mock_s3.bucket_name = 'test-bucket'
        mock_s3.client.generate_presigned_url.return_value = 'https://s3.example.com/signed'
        mock_get.return_value = mock_s3

        r = self.client.post('/api/files/share/', {'source': 's3', 'path': 'docs/report.pdf'}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['url'], 'https://s3.example.com/signed')
        self.assertEqual(r.data['expires_in'], 3600)
        kwargs = mock_s3.client.generate_presigned_url.call_args.kwargs
        self.assertEqual(kwargs['Params']['Bucket'], 'test-bucket')
        self.assertEqual(kwargs['Params']['Key'], 'docs/report.pdf')

    @patch('manager.api_views.get_s3_storage')
    def test_share_clamps_expiry(self, mock_get):
        mock_s3 = MagicMock()
        mock_s3.bucket_name = 'b'
        mock_s3.client.generate_presigned_url.return_value = 'https://x'
        mock_get.return_value = mock_s3

        r = self.client.post('/api/files/share/', {'path': 'a', 'expires_in': 10}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['expires_in'], 60)  # clamped up to the 60s minimum
        self.assertEqual(mock_s3.client.generate_presigned_url.call_args.kwargs['ExpiresIn'], 60)

    def test_share_requires_path(self):
        r = self.client.post('/api/files/share/', {'source': 's3'}, format='json')
        self.assertEqual(r.status_code, 400)


class CloudDriveAPITest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('cloud', password='x')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_onedrive_not_connected(self):
        r = self.client.get('/api/cloud/files/?provider=onedrive')
        self.assertEqual(r.status_code, 400)
        self.assertIn('not connected', str(r.data['error']))

    def test_unsupported_provider(self):
        r = self.client.get('/api/cloud/files/?provider=dropbox')
        self.assertEqual(r.status_code, 400)
        self.assertIn('not supported', str(r.data['error']))


# ---------------------------------------------------------------------------
# OAuth state CSRF handling (function views -> plain Client)
# ---------------------------------------------------------------------------
class MoveFilesAPITest(TestCase):
    """Cross-source move (local <-> S3). S3 is mocked."""

    def setUp(self):
        import manager.services as svc
        self._svc = svc
        self.tmp = tempfile.TemporaryDirectory()
        (Path(self.tmp.name) / 'a.txt').write_text('AAA')
        self.user = User.objects.create_user('mv', password='x')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        self._svc._local_storage_instance = None
        self._svc._s3_storage_instance = None
        self._svc._unified_storage_instance = None
        self.tmp.cleanup()

    def _reset_local(self):
        self._svc._local_storage_instance = None
        self._svc._unified_storage_instance = None

    @patch('manager.api_views.get_s3_storage')
    def test_move_local_to_s3(self, mock_get):
        mock_s3 = MagicMock()
        mock_s3.upload_file.return_value = True
        mock_get.return_value = mock_s3

        self._reset_local()
        with override_settings(LOCAL_STORAGE_PATH=self.tmp.name):
            r = self.client.post('/api/files/move/', {
                'files': ['a.txt'], 'source': 'local', 'dest_source': 's3',
            }, format='json')

        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['success']), 1)
        mock_s3.upload_file.assert_called_once()
        # uploaded from the temp file, then the local copy is removed
        self.assertFalse((Path(self.tmp.name) / 'a.txt').exists())
        self.assertTrue(FileOperation.objects.filter(operation='MOVE', user=self.user).exists())

    @patch('manager.api_views.get_s3_storage')
    def test_move_s3_to_local(self, mock_get):
        mock_s3 = MagicMock()

        def fake_download(key, dest):
            Path(dest).write_text('downloaded-content')

        mock_s3.download_file.side_effect = fake_download
        mock_s3.delete_files.return_value = {'success': ['cloud/a.txt'], 'failed': []}
        mock_get.return_value = mock_s3

        self._reset_local()
        with override_settings(LOCAL_STORAGE_PATH=self.tmp.name):
            r = self.client.post('/api/files/move/', {
                'files': ['cloud/a.txt'], 'source': 's3', 'dest_source': 'local',
            }, format='json')

        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['success']), 1)
        # file landed in local storage with the original basename
        moved = Path(self.tmp.name) / 'a.txt'
        self.assertTrue(moved.exists())
        self.assertEqual(moved.read_text(), 'downloaded-content')
        mock_s3.delete_files.assert_called_once()

    def test_move_rejects_same_source(self):
        r = self.client.post('/api/files/move/', {
            'files': ['a'], 'source': 's3', 'dest_source': 's3',
        }, format='json')
        self.assertEqual(r.status_code, 400)


class OAuthStateTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('oauth', password='x')
        self.client = Client()
        self.client.force_login(self.user)

    def test_connect_sets_session_state(self):
        r = self.client.get('/cloud/connect/googledrive/')
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r['Location'].startswith('https://accounts.google.com/'))
        state = self.client.session.get('oauth_state')
        self.assertIsNotNone(state)
        self.assertTrue(state.startswith('googledrive:'))

    def test_forged_callback_rejected(self):
        self.client.get('/cloud/connect/googledrive/')  # seed session nonce
        r = self.client.get('/oauth/callback/?code=fake&state=googledrive:WRONG')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, '/profile/')
        # State consumed and no token stored -> rejection, not progression
        self.assertIsNone(self.client.session.get('oauth_state'))
        self.assertFalse(CloudStorageToken.objects.filter(user=self.user).exists())


class SyncServiceTest(TestCase):
    """Plan/execute math with a real LocalStorage temp dir and a mocked S3 backend."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.local = LocalStorage(base_path=self.tmp.name)
        now = time.time()
        self.now = now

        (Path(self.tmp.name) / 'local_only.txt').write_text('L')
        (Path(self.tmp.name) / 'local_newer.txt').write_text('LN')
        os.utime(Path(self.tmp.name) / 'local_newer.txt', (now, now))
        (Path(self.tmp.name) / 's3_newer.txt').write_text('SN-old')
        os.utime(Path(self.tmp.name) / 's3_newer.txt', (now - 200, now - 200))
        (Path(self.tmp.name) / 'unchanged.txt').write_text('U')
        os.utime(Path(self.tmp.name) / 'unchanged.txt', (now, now))

        self.s3 = MagicMock()
        self.s3.list_files.return_value = [
            make_info('s3_only.txt', now),
            make_info('local_newer.txt', now - 100),
            make_info('s3_newer.txt', now + 100),
            make_info('unchanged.txt', now),
        ]
        self.service = SyncService(self.local, self.s3)

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_plan(self):
        plan = self.service.build_plan()
        by_path = {a['path']: a for a in plan['actions']}
        self.assertEqual(by_path['local_only.txt']['direction'], 'push')
        self.assertEqual(by_path['local_only.txt']['reason'], 'local_only')
        self.assertEqual(by_path['s3_only.txt']['direction'], 'pull')
        self.assertEqual(by_path['local_newer.txt']['direction'], 'push')
        self.assertEqual(by_path['local_newer.txt']['reason'], 'local_newer')
        self.assertEqual(by_path['s3_newer.txt']['direction'], 'pull')
        self.assertEqual(by_path['s3_newer.txt']['reason'], 's3_newer')
        self.assertEqual(plan['unchanged'], 1)
        self.assertEqual(len(plan['actions']), 4)

    def test_execute_push_converges_mtime(self):
        plan = {'actions': [{'path': 'local_only.txt', 'direction': 'push',
                             'reason': 'local_only', 's3_ts': None}]}
        result = self.service.execute(plan)
        self.assertEqual(len(result['executed']), 1)
        self.assertEqual(len(result['failed']), 0)
        self.s3.upload_file.assert_called_once()
        # local mtime stamped to ~now so the next sync sees the pair unchanged
        self.assertAlmostEqual(
            (Path(self.tmp.name) / 'local_only.txt').stat().st_mtime,
            time.time(), delta=5,
        )

    def test_execute_pull_converges_mtime(self):
        s3_ts = self.now - 50

        def fake_download(key, dest):
            Path(dest).write_text('from s3')

        self.s3.download_file.side_effect = fake_download
        plan = {'actions': [{'path': 's3_only.txt', 'direction': 'pull',
                             'reason': 's3_only', 's3_ts': s3_ts}]}
        result = self.service.execute(plan)
        self.assertEqual(len(result['executed']), 1)
        pulled = Path(self.tmp.name) / 's3_only.txt'
        self.assertTrue(pulled.exists())
        # local mtime stamped with the S3 LastModified carried in the plan
        self.assertAlmostEqual(pulled.stat().st_mtime, s3_ts, delta=2)

    def test_execute_dry_run_copies_nothing(self):
        plan = self.service.build_plan()
        result = self.service.execute(plan, dry_run=True)
        self.assertEqual(len(result['executed']), len(plan['actions']))
        self.s3.upload_file.assert_not_called()
        self.s3.download_file.assert_not_called()


class SyncAPITest(TestCase):
    """Sync preview/run endpoints with an injected mocked S3 singleton."""

    def setUp(self):
        import manager.services as svc
        self._svc = svc
        self.tmp = tempfile.TemporaryDirectory()
        (Path(self.tmp.name) / 'one.txt').write_text('1')
        self.user = User.objects.create_user('syncapi', password='x')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        self._svc._local_storage_instance = None
        self._svc._s3_storage_instance = None
        self._svc._unified_storage_instance = None
        self.tmp.cleanup()

    def _inject_mock_s3(self, files=None):
        mock_s3 = MagicMock()
        mock_s3.list_files.return_value = files or []
        self._svc._local_storage_instance = None
        self._svc._unified_storage_instance = None
        self._svc._s3_storage_instance = mock_s3

    def test_preview(self):
        self._inject_mock_s3()
        with override_settings(LOCAL_STORAGE_PATH=self.tmp.name):
            r = self.client.get('/api/files/sync-preview/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['to_upload'], 1)
        self.assertEqual(r.data['to_download'], 0)
        self.assertEqual(r.data['unchanged'], 0)

    def test_run(self):
        self._inject_mock_s3()
        with override_settings(LOCAL_STORAGE_PATH=self.tmp.name):
            r = self.client.post('/api/files/sync-run/', {}, format='json')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['pushed'], 1)
        self.assertEqual(r.data['pulled'], 0)
        self.assertTrue(SyncRun.objects.filter(status='success', dry_run=False).exists())
        self.assertTrue(
            FileOperation.objects.filter(operation='UPLOAD', user=self.user, file_path='one.txt').exists()
        )


class VersioningAPITest(TestCase):
    """S3 version listing / restore / versioned download (boto3 mocked)."""

    def setUp(self):
        self.user = User.objects.create_user('ver', password='x')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _mock_s3(self):
        mock_s3 = MagicMock()
        mock_s3.bucket_name = 'b'
        return mock_s3

    @patch('manager.api_views.get_s3_storage')
    def test_versions_list(self, mock_get):
        mock_s3 = self._mock_s3()
        t1 = datetime(2026, 8, 13, 10, 0, tzinfo=dt_timezone.utc)
        t2 = datetime(2026, 8, 13, 11, 0, tzinfo=dt_timezone.utc)
        mock_s3.client.list_object_versions.return_value = {
            'Versions': [
                {'Key': 'a.txt', 'VersionId': 'v2', 'LastModified': t2, 'Size': 20, 'IsLatest': True},
                {'Key': 'a.txt', 'VersionId': 'v1', 'LastModified': t1, 'Size': 10, 'IsLatest': False},
                {'Key': 'a.txt.bak', 'VersionId': 'v9', 'LastModified': t1, 'Size': 5, 'IsLatest': True},
            ]
        }
        mock_get.return_value = mock_s3

        r = self.client.get('/api/files/versions/?path=a.txt')
        self.assertEqual(r.status_code, 200)
        # the a.txt.bak entry (prefix match, different key) must be filtered out
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(r.data['versions'][0]['version_id'], 'v2')
        self.assertTrue(r.data['versions'][0]['is_latest'])
        self.assertEqual(r.data['versions'][1]['version_id'], 'v1')

    @patch('manager.api_views.get_s3_storage')
    def test_restore_uses_versioned_copy_source(self, mock_get):
        mock_s3 = self._mock_s3()
        mock_get.return_value = mock_s3

        r = self.client.post('/api/files/versions/restore/',
                             {'path': 'a.txt', 'version_id': 'v1'}, format='json')
        self.assertEqual(r.status_code, 200)
        kwargs = mock_s3.client.copy_object.call_args.kwargs
        self.assertEqual(kwargs['CopySource'], {'Bucket': 'b', 'Key': 'a.txt', 'VersionId': 'v1'})
        self.assertEqual(kwargs['Key'], 'a.txt')

    @patch('manager.api_views.get_s3_storage')
    def test_restore_null_version(self, mock_get):
        mock_s3 = self._mock_s3()
        mock_get.return_value = mock_s3

        r = self.client.post('/api/files/versions/restore/',
                             {'path': 'a.txt', 'version_id': 'null'}, format='json')
        self.assertEqual(r.status_code, 200)
        kwargs = mock_s3.client.copy_object.call_args.kwargs
        self.assertEqual(kwargs['CopySource'], {'Bucket': 'b', 'Key': 'a.txt'})

    @patch('manager.api_views.get_s3_storage')
    def test_download_file_passes_version_id(self, mock_get):
        mock_s3 = self._mock_s3()
        body = MagicMock()
        body.iter_chunks.return_value = iter([b'version-bytes'])
        mock_s3.client.head_object.return_value = {'ContentLength': 13}
        mock_s3.client.get_object.return_value = {
            'Body': body, 'ContentType': 'text/plain', 'ContentLength': 13,
        }
        mock_get.return_value = mock_s3

        r = self.client.get('/api/files/download-file/?source=s3&path=a.txt&version_id=v1')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(mock_s3.client.get_object.call_args.kwargs['VersionId'], 'v1')
        self.assertEqual(mock_s3.client.head_object.call_args.kwargs['VersionId'], 'v1')
        content = b''.join(r.streaming_content)
        self.assertEqual(content, b'version-bytes')
