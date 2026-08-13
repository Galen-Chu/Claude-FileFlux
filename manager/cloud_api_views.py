"""
Cloud Drive API Views

API endpoints for Google Drive and OneDrive operations.
Both providers implement the same service interface, so the viewset is
provider-agnostic: it resolves the service class from the provider name
and delegates to it.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import CloudStorageToken, FileOperation
from .services.google_drive_service import GoogleDriveService
from .services.onedrive_service import OneDriveService

# Maps provider name -> service class. Both expose the same methods with
# identical signatures and return shapes, so the viewset logic below is shared.
SUPPORTED_PROVIDERS = {
    'googledrive': GoogleDriveService,
    'onedrive': OneDriveService,
}


class CloudDriveViewSet(viewsets.ViewSet):
    """ViewSet for cloud drive operations (Google Drive, OneDrive)"""

    permission_classes = [IsAuthenticated]

    def _resolve(self, request, provider):
        """
        Resolve a provider to its stored token and a service instance.

        Returns:
            (token, service) on success
            (None, Response) with an error response on failure
        """
        if provider not in SUPPORTED_PROVIDERS:
            return None, Response(
                {'error': f'Provider {provider} not supported. Use one of: {", ".join(SUPPORTED_PROVIDERS)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = CloudStorageToken.objects.get(user=request.user, provider=provider)
        except CloudStorageToken.DoesNotExist:
            return None, Response(
                {'error': f'{provider} is not connected'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return token, SUPPORTED_PROVIDERS[provider](token)

    @action(detail=False, methods=['get'], url_path='files')
    def list_files(self, request):
        """
        List files from a connected cloud drive.

        Query params:
            - provider: 'googledrive' or 'onedrive'
            - folder_id: folder ID to list (optional, defaults to root)
            - page_size: number of items per page (default 50)
            - page_token: pagination token / next link (optional)
            - query: search query (optional)
        """
        provider = request.query_params.get('provider', 'googledrive')
        token, service = self._resolve(request, provider)
        if token is None:
            return service

        result = service.list_files(
            page_size=int(request.query_params.get('page_size', 50)),
            page_token=request.query_params.get('page_token'),
            folder_id=request.query_params.get('folder_id'),
            query=request.query_params.get('query'),
        )

        if result.get('error'):
            return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'files': result['files'],
            'next_page_token': result.get('next_page_token'),
            'provider': provider,
        })

    @action(detail=False, methods=['get'], url_path='files/(?P<file_id>[^/.]+)')
    def get_file(self, request, file_id=None):
        """
        Get file metadata from a cloud drive.

        Query params:
            - provider: 'googledrive' or 'onedrive'
        """
        provider = request.query_params.get('provider', 'googledrive')
        token, service = self._resolve(request, provider)
        if token is None:
            return service

        result = service.get_file(file_id)

        if result.get('error'):
            return Response({'error': result['error']}, status=status.HTTP_404_NOT_FOUND)

        return Response(result)

    @action(detail=False, methods=['post'], url_path='upload')
    def upload_file(self, request):
        """
        Upload a file to a cloud drive.

        Request body (multipart/form-data):
            - file: file to upload
            - provider: 'googledrive' or 'onedrive'
            - parent_folder_id: folder ID to upload to (optional)
        """
        provider = request.data.get('provider', 'googledrive')
        token, service = self._resolve(request, provider)
        if token is None:
            return service

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        result = service.upload_file(
            file_content=uploaded_file.read(),
            filename=uploaded_file.name,
            mime_type=uploaded_file.content_type,
            parent_folder_id=request.data.get('parent_folder_id'),
        )

        if result.get('error'):
            return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

        FileOperation.objects.create(
            operation='UPLOAD',
            user=request.user,
            source=provider,
            file_path=result['name'],
            success=True,
            file_size=result['size'],
        )

        return Response(result, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='download')
    def download_file(self, request):
        """
        Download a file from a cloud drive.

        Request body (JSON):
            - file_id: ID of file to download
            - provider: 'googledrive' or 'onedrive'
        """
        provider = request.data.get('provider', 'googledrive')
        file_id = request.data.get('file_id')
        if not file_id:
            return Response({'error': 'file_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        token, service = self._resolve(request, provider)
        if token is None:
            return service

        result = service.download_file(file_id)

        if result.get('error'):
            return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

        from django.http import HttpResponse
        response = HttpResponse(result['content'], content_type=result['mime_type'])
        response['Content-Disposition'] = f'attachment; filename="{result["name"]}"'

        FileOperation.objects.create(
            operation='DOWNLOAD',
            user=request.user,
            source=provider,
            file_path=result['name'],
            success=True,
            file_size=result['size'],
        )

        return response

    @action(detail=False, methods=['post'], url_path='create-folder')
    def create_folder(self, request):
        """
        Create a folder in a cloud drive.

        Request body (JSON):
            - name: folder name
            - provider: 'googledrive' or 'onedrive'
            - parent_folder_id: parent folder ID (optional)
        """
        provider = request.data.get('provider', 'googledrive')
        folder_name = request.data.get('name')
        if not folder_name:
            return Response({'error': 'name is required'}, status=status.HTTP_400_BAD_REQUEST)

        token, service = self._resolve(request, provider)
        if token is None:
            return service

        result = service.create_folder(
            folder_name=folder_name,
            parent_folder_id=request.data.get('parent_folder_id'),
        )

        if result.get('error'):
            return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['delete'], url_path='files/(?P<file_id>[^/.]+)')
    def delete_file(self, request, file_id=None):
        """
        Delete a file from a cloud drive.

        Query params:
            - provider: 'googledrive' or 'onedrive'
        """
        provider = request.query_params.get('provider', 'googledrive')
        token, service = self._resolve(request, provider)
        if token is None:
            return service

        result = service.delete_file(file_id)

        if not result.get('success'):
            return Response(
                {'error': result.get('error', 'Delete failed')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        FileOperation.objects.create(
            operation='DELETE',
            user=request.user,
            source=provider,
            file_path=file_id,
            success=True,
        )

        return Response({'success': True, 'message': 'File deleted'})

    @action(detail=False, methods=['patch'], url_path='files/(?P<file_id>[^/.]+)/rename')
    def rename_file(self, request, file_id=None):
        """
        Rename a file in a cloud drive.

        Request body (JSON):
            - new_name: new filename
            - provider: 'googledrive' or 'onedrive'
        """
        provider = request.data.get('provider', 'googledrive')
        new_name = request.data.get('new_name')
        if not new_name:
            return Response({'error': 'new_name is required'}, status=status.HTTP_400_BAD_REQUEST)

        token, service = self._resolve(request, provider)
        if token is None:
            return service

        result = service.rename_file(file_id, new_name)

        if result.get('error'):
            return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

        FileOperation.objects.create(
            operation='RENAME',
            user=request.user,
            source=provider,
            file_path=result['name'],
            success=True,
        )

        return Response(result)
