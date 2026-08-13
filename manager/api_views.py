"""
API views for file management
"""
import os
import tempfile
from pathlib import Path

from django.conf import settings
from django.http import FileResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import FileOperation
from .serializers import (
    FileInfoSerializer,
    FileListRequestSerializer,
    BulkRenameRequestSerializer,
    FileDeleteRequestSerializer,
    FileUploadRequestSerializer,
    FileDownloadRequestSerializer,
    OperationResultSerializer,
)
from .services import get_unified_storage
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

            # Serialize results
            serializer = FileInfoSerializer(files, many=True)

            return Response({
                'count': len(files),
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
