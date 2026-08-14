"""
API views for file management
"""
import mimetypes
import os
import tempfile
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, StreamingHttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import FileOperation, SyncRun
from .serializers import (
    FileInfoSerializer,
    FileListRequestSerializer,
    BulkRenameRequestSerializer,
    FileDeleteRequestSerializer,
    FileUploadRequestSerializer,
    FileDownloadRequestSerializer,
    OperationResultSerializer,
)
from .services import get_local_storage, get_s3_storage, get_unified_storage
from .services.sync_service import SyncService
from .services.exceptions import FileOperationError


class FileManagementViewSet(viewsets.ViewSet):
    """ViewSet for file management operations"""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        """
        List files from storage backends

        Query params:
            - source: 'local', 's3', or omit for all
            - path: path to list files from (default: root)
        """
        # Validate query parameters
        query_serializer = FileListRequestSerializer(data=request.query_params)
        if not query_serializer.is_valid():
            return Response(
                query_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        data = query_serializer.validated_data
        source = data.get('source')
        path = data.get('path', '')
        search = data.get('search')

        try:
            storage = get_unified_storage()
            files = storage.list_files(source=source, path=path)

            # Optional case-insensitive filename search (local & S3 listings)
            if search:
                needle = search.lower()
                files = [f for f in files if needle in f.name.lower()]

            # Pagination (page-number offset over the full result set)
            total = len(files)
            page = data.get('page') or 1
            page_size = data.get('page_size') or 50
            start = (page - 1) * page_size
            page_files = files[start:start + page_size]
            has_next = start + page_size < total

            # Serialize results
            serializer = FileInfoSerializer(page_files, many=True)

            return Response({
                'count': len(page_files),
                'total': total,
                'page': page,
                'page_size': page_size,
                'has_next': has_next,
                'next_page': page + 1 if has_next else None,
                'source': source or 'all',
                'path': path,
                'files': serializer.data
            })

        except FileOperationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to list files: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def rename(self, request):
        """
        Bulk rename files by adding prefix/suffix or replacing text

        Request body:
            - files: list of file paths
            - text: text to add as prefix/suffix or replacement text
            - mode: 'prefix', 'suffix', or 'replace' (default: 'prefix')
            - add_sequence: boolean to add sequential numbering (default: false)
            - start_number: starting number for sequence (default: 1)
            - source: 'local' or 's3'

            Replace mode specific:
            - find_text: text to find and replace (required for replace mode)
            - case_sensitive: case-sensitive matching (default: false)
            - use_regex: treat find_text as regex (default: false)
            - replace_all: replace all occurrences or just first (default: true)
        """
        serializer = BulkRenameRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        files = data['files']
        text = data['text']
        mode = data['mode']
        add_sequence = data['add_sequence']
        start_number = data['start_number']
        source = data['source']

        # Get replace mode specific parameters
        find_text = data.get('find_text')
        case_sensitive = data.get('case_sensitive', False)
        use_regex = data.get('use_regex', False)
        replace_all = data.get('replace_all', True)

        try:
            storage = get_unified_storage()
            result = storage.rename_files(
                files, text, source, mode, add_sequence, start_number,
                find_text, case_sensitive, use_regex, replace_all
            )

            # Log operations
            for success_item in result['success']:
                FileOperation.objects.create(
                    operation='RENAME',
                    user=request.user,
                    source=source,
                    file_path=success_item['new_path'],
                    old_path=success_item['old_path'],
                    success=True
                )

            for failed_item in result['failed']:
                FileOperation.objects.create(
                    operation='RENAME',
                    user=request.user,
                    source=source,
                    file_path=failed_item['file'],
                    success=False,
                    error_message=failed_item['error']
                )

            return Response(result, status=status.HTTP_200_OK)

        except FileOperationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def delete(self, request):
        """
        Bulk delete files

        Request body:
            - files: list of file paths
            - source: 'local' or 's3'
        """
        serializer = FileDeleteRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        files = data['files']
        source = data['source']

        try:
            storage = get_unified_storage()
            result = storage.delete_files(files, source)

            # Log operations
            for file_path in result['success']:
                FileOperation.objects.create(
                    operation='DELETE',
                    user=request.user,
                    source=source,
                    file_path=file_path,
                    success=True
                )

            for failed_item in result['failed']:
                FileOperation.objects.create(
                    operation='DELETE',
                    user=request.user,
                    source=source,
                    file_path=failed_item['file'],
                    success=False,
                    error_message=failed_item['error']
                )

            return Response(result, status=status.HTTP_200_OK)

        except FileOperationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def upload(self, request):
        """
        Upload file to S3

        Request body (multipart/form-data):
            - file: file to upload
            - dest_path: destination path in S3 (optional)
        """
        serializer = FileUploadRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        uploaded_file = data['file']
        dest_path = data.get('dest_path') or uploaded_file.name

        temp_file = None
        try:
            # Save uploaded file to temporary location
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            temp_file.close()

            # Check file size
            file_size = os.path.getsize(temp_file.name)
            max_size = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
            if file_size > max_size:
                return Response(
                    {'error': f'File size exceeds maximum ({settings.MAX_UPLOAD_SIZE_MB}MB)'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Upload to S3
            storage = get_unified_storage()
            storage.upload_file(temp_file.name, dest_path)

            # Log operation
            FileOperation.objects.create(
                operation='UPLOAD',
                user=request.user,
                source='s3',
                file_path=dest_path,
                success=True,
                file_size=file_size
            )

            return Response({
                'success': True,
                'path': dest_path,
                'size': file_size
            }, status=status.HTTP_201_CREATED)

        except FileOperationError as e:
            # Log failed operation
            FileOperation.objects.create(
                operation='UPLOAD',
                user=request.user,
                source='s3',
                file_path=dest_path,
                success=False,
                error_message=str(e)
            )
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            # Clean up temp file
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)

    @action(detail=False, methods=['post'])
    def download(self, request):
        """
        Download file from S3 to local storage

        Request body:
            - source_path: source path in S3
            - dest_path: local destination path (optional)
        """
        serializer = FileDownloadRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        data = serializer.validated_data
        source_path = data['source_path']
        dest_path = data.get('dest_path')

        # If no dest_path, use local storage directory + filename
        if not dest_path:
            filename = source_path.split('/')[-1]
            dest_path = os.path.join(settings.LOCAL_STORAGE_PATH, filename)

        try:
            storage = get_unified_storage()
            storage.download_file(source_path, dest_path)

            # Get file size
            file_size = os.path.getsize(dest_path)

            # Log operation
            FileOperation.objects.create(
                operation='DOWNLOAD',
                user=request.user,
                source='s3',
                file_path=source_path,
                success=True,
                file_size=file_size
            )

            return Response({
                'success': True,
                'source_path': source_path,
                'dest_path': dest_path,
                'size': file_size
            }, status=status.HTTP_200_OK)

        except FileOperationError as e:
            # Log failed operation
            FileOperation.objects.create(
                operation='DOWNLOAD',
                user=request.user,
                source='s3',
                file_path=source_path,
                success=False,
                error_message=str(e)
            )
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='download-file')
    def download_file(self, request):
        """
        Stream a local or S3 file to the browser for download (with progress).

        Query params:
            - source: 'local' or 's3'
            - path: file path (local) or object key (S3)
        """
        source = request.query_params.get('source')
        path = request.query_params.get('path')
        if not source or not path:
            return Response(
                {'error': 'source and path are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        filename = os.path.basename(path) or path.split('/')[-1]
        inline = request.query_params.get('inline')  # serve inline for preview

        try:
            if source == 'local':
                local = get_local_storage()
                full_path = local._validate_path(path)  # reuse traversal protection
                if not full_path.exists() or not full_path.is_file():
                    return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)

                content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                return FileResponse(
                    open(full_path, 'rb'),
                    content_type=content_type,
                    as_attachment=not inline,
                    filename=filename,
                )

            elif source == 's3':
                s3 = get_s3_storage()
                version_id = request.query_params.get('version_id')
                key_params = {'Bucket': s3.bucket_name, 'Key': path}
                if version_id:
                    key_params['VersionId'] = version_id  # 'null' is a valid version id
                try:
                    head = s3.client.head_object(**key_params)
                except Exception:
                    return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)

                obj = s3.client.get_object(**key_params)
                response = StreamingHttpResponse(
                    obj['Body'].iter_chunks(chunk_size=8192),
                    content_type=obj.get('ContentType', 'application/octet-stream'),
                )
                disposition = 'inline' if inline else 'attachment'
                response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
                content_length = obj.get('ContentLength') or head.get('ContentLength')
                if content_length is not None:
                    response['Content-Length'] = str(content_length)
                return response

            else:
                return Response(
                    {'error': "source must be 'local' or 's3'"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except FileOperationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {'error': f'Download failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['get'], url_path='sync-preview')
    def sync_preview(self, request):
        """
        Preview a local <-> S3 sync (dry run; no writes).
        Returns the action list plus summary counts.
        """
        try:
            storage = get_unified_storage()
            service = SyncService(storage.local_storage, storage.s3_storage)
            plan = service.build_plan()
            pushes = sum(1 for a in plan['actions'] if a['direction'] == 'push')
            return Response({
                'actions': plan['actions'],
                'unchanged': plan['unchanged'],
                'to_upload': pushes,
                'to_download': len(plan['actions']) - pushes,
            })
        except Exception as e:
            return Response(
                {'error': f'Failed to build sync plan: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['post'], url_path='sync-run')
    def sync_run(self, request):
        """
        Execute a local <-> S3 sync (last-write-wins). Body: {'dry_run': bool}.
        """
        dry_run = request.data.get('dry_run', False) is True
        run = SyncRun.objects.create(dry_run=dry_run)
        try:
            storage = get_unified_storage()
            service = SyncService(storage.local_storage, storage.s3_storage)
            plan = service.build_plan()
            result = service.execute(plan, dry_run=dry_run)

            pushed = sum(1 for x in result['executed'] if x['direction'] == 'push')
            pulled = sum(1 for x in result['executed'] if x['direction'] == 'pull')
            run.pushed = pushed
            run.pulled = pulled
            run.failed_count = len(result['failed'])
            run.status = 'success'
            run.finished_at = timezone.now()
            run.save()

            for x in result['executed']:
                if x['direction'] == 'push':
                    FileOperation.objects.create(
                        operation='UPLOAD', user=request.user, source='local',
                        file_path=x['path'], success=True,
                    )
                else:
                    FileOperation.objects.create(
                        operation='DOWNLOAD', user=request.user, source='s3',
                        file_path=x['path'], success=True,
                    )

            return Response({
                'executed': result['executed'],
                'failed': result['failed'],
                'pushed': pushed,
                'pulled': pulled,
                'unchanged': plan['unchanged'],
                'run_id': run.id,
            })
        except Exception as e:
            run.status = 'failed'
            run.error_message = str(e)[:2000]
            run.finished_at = timezone.now()
            run.save()
            return Response(
                {'error': f'Sync failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['get'], url_path='versions')
    def versions(self, request):
        """
        List versions of an S3 object (requires bucket versioning enabled).

        Query params:
            - path: S3 object key
        """
        path = request.query_params.get('path')
        if not path:
            return Response({'error': 'path is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            s3 = get_s3_storage()
            resp = s3.client.list_object_versions(Bucket=s3.bucket_name, Prefix=path)
            versions = []
            for v in resp.get('Versions', []):
                if v.get('Key') != path:
                    continue  # Prefix match can include other keys
                versions.append({
                    'version_id': v.get('VersionId') or 'null',
                    'last_modified': v['LastModified'].isoformat() if v.get('LastModified') else None,
                    'size': v.get('Size', 0),
                    'is_latest': v.get('IsLatest', False),
                })
            return Response({'path': path, 'versions': versions, 'count': len(versions)})
        except Exception as e:
            return Response(
                {'error': f'Failed to list versions: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['post'], url_path='versions/restore')
    def versions_restore(self, request):
        """
        Restore an old S3 version as the latest (server-side copy over the key).

        Request body (JSON):
            - path: S3 object key
            - version_id: version to restore ('null' for the null version)
        """
        path = request.data.get('path')
        version_id = request.data.get('version_id')
        if not path or not version_id:
            return Response(
                {'error': 'path and version_id are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            s3 = get_s3_storage()
            copy_source = {'Bucket': s3.bucket_name, 'Key': path}
            if version_id != 'null':
                copy_source['VersionId'] = version_id
            s3.client.copy_object(Bucket=s3.bucket_name, CopySource=copy_source, Key=path)
            FileOperation.objects.create(
                operation='UPLOAD', user=request.user, source='s3',
                file_path=path, success=True,
            )
            return Response({'success': True, 'message': 'Version restored as latest'})
        except Exception as e:
            return Response(
                {'error': f'Restore failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['post'])
    def move(self, request):
        """
        Move files across storage backends (local <-> S3) via copy + delete.

        Request body (JSON):
            - files: list of file paths/keys
            - source: 'local' or 's3'
            - dest_source: 'local' or 's3' (must differ from source)
            - dest_path: optional destination filename/subpath (defaults to original name)
        """
        files = request.data.get('files', [])
        source = request.data.get('source')
        dest_source = request.data.get('dest_source')
        dest_path = request.data.get('dest_path') or ''

        if not files or not source or not dest_source:
            return Response(
                {'error': 'files, source, and dest_source are required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if source not in ('local', 's3') or dest_source not in ('local', 's3'):
            return Response(
                {'error': "source and dest_source must be 'local' or 's3'"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if source == dest_source:
            return Response(
                {'error': 'source and dest_source must differ (use rename for same-source moves)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        local = get_local_storage()
        s3 = get_s3_storage()
        success, failed = [], []

        for f in files:
            base = os.path.basename(f) or f.split('/')[-1]
            # dest_path is treated as a destination directory/prefix so that
            # moving multiple files does not collide them into one name
            filename = (dest_path.rstrip('/') + '/' + base) if dest_path else base
            try:
                if source == 'local' and dest_source == 's3':
                    abs_local = local._validate_path(f)  # traversal-safe absolute path
                    if not abs_local.exists() or not abs_local.is_file():
                        failed.append({'file': f, 'error': 'File not found'})
                        continue
                    s3.upload_file(str(abs_local), filename)  # local -> S3
                    local.delete_files([f])                  # then remove local
                elif source == 's3' and dest_source == 'local':
                    local_dest = str(local._validate_path(filename))  # within LOCAL_STORAGE_PATH
                    os.makedirs(os.path.dirname(local_dest) or '.', exist_ok=True)
                    s3.download_file(f, local_dest)  # S3 -> local
                    s3.delete_files([f])             # then remove S3
                else:
                    failed.append({'file': f, 'error': 'Unsupported move'})
                    continue

                FileOperation.objects.create(
                    operation='MOVE', user=request.user, source=source,
                    file_path=filename, old_path=f, success=True,
                )
                success.append({'file': f, 'dest': f'{dest_source}:{filename}'})
            except FileOperationError as e:
                failed.append({'file': f, 'error': str(e)})
            except Exception as e:
                failed.append({'file': f, 'error': str(e)})

        return Response({'success': success, 'failed': failed}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def share(self, request):
        """
        Generate a time-limited presigned URL to share an S3 object.

        Request body (JSON):
            - path: S3 object key
            - expires_in: validity in seconds (default 3600, clamped to 60..604800)
        """
        path = request.data.get('path')
        if not path:
            return Response(
                {'error': 'path is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            expires_in = min(max(int(request.data.get('expires_in', 3600)), 60), 7 * 24 * 3600)
        except (TypeError, ValueError):
            return Response(
                {'error': 'expires_in must be an integer'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            s3 = get_s3_storage()
            url = s3.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': s3.bucket_name, 'Key': path},
                ExpiresIn=expires_in,
            )
            return Response({'url': url, 'source': 's3', 'path': path, 'expires_in': expires_in})
        except Exception as e:
            return Response(
                {'error': f'Failed to create share link: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['get'])
    def logs(self, request):
        """
        Get recent file operation logs

        Query params:
            - limit: number of logs to return (default: 50)
        """
        limit = int(request.query_params.get('limit', 50))
        qs = FileOperation.objects.all()
        # Non-superusers only see their own operations
        if not request.user.is_superuser:
            qs = qs.filter(user=request.user)
        logs = qs[:limit]

        # Manual serialization
        data = [{
            'id': log.id,
            'operation': log.operation,
            'source': log.source,
            'user': log.user.username if log.user else None,
            'file_path': log.file_path,
            'old_path': log.old_path,
            'timestamp': log.timestamp,
            'success': log.success,
            'error_message': log.error_message,
            'file_size': log.file_size,
        } for log in logs]

        return Response({
            'count': len(data),
            'logs': data
        })
