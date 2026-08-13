"""
OneDrive API Service

Handles all OneDrive operations using the Microsoft Graph API.
Uses OAuth 2.0 tokens stored in CloudStorageToken model.

Return shapes mirror GoogleDriveService so CloudDriveViewSet can treat
both providers uniformly.
"""

import requests
from datetime import timedelta
from django.utils import timezone
from django.conf import settings

from .cloud_base import CloudStorageService


class OneDriveService(CloudStorageService):
    """Service class for OneDrive operations via Microsoft Graph"""

    BASE_URL = 'https://graph.microsoft.com/v1.0'

    def __init__(self, token):
        """
        Initialize OneDrive service with user's token

        Args:
            token: CloudStorageToken instance for OneDrive
        """
        self.token = token
        self.user = token.user

    def _get_headers(self):
        """Get authorization headers for Graph API requests"""
        return {
            'Authorization': f'Bearer {self.token.access_token}',
        }

    def _refresh_token_if_needed(self):
        """
        Refresh access token if expired

        Returns:
            bool: True if token is valid (refreshed or not expired)
            False if refresh failed
        """
        if self.token.token_expires_at and timezone.now() < self.token.token_expires_at:
            return True

        if not self.token.refresh_token:
            return False

        try:
            tenant = getattr(settings, 'MS_TENANT_ID', 'common')
            response = requests.post(
                f'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token',
                data={
                    'client_id': settings.MS_CLIENT_ID,
                    'client_secret': settings.MS_CLIENT_SECRET,
                    'refresh_token': self.token.refresh_token,
                    'grant_type': 'refresh_token',
                    'scope': 'files.readwrite.all offline_access',
                }
            )

            if response.status_code != 200:
                return False

            token_data = response.json()

            self.token.access_token = token_data['access_token']
            if token_data.get('refresh_token'):
                self.token.refresh_token = token_data['refresh_token']
            expires_in = token_data.get('expires_in', 3600)
            self.token.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
            self.token.save()

            return True

        except requests.RequestException as e:
            print(f"Error refreshing OneDrive token: {str(e)}")
            return False

    @staticmethod
    def _format_item(item):
        """Normalize a Graph driveItem into the shared file dict shape"""
        is_folder = 'folder' in item
        return {
            'id': item['id'],
            'name': item.get('name', ''),
            'type': 'folder' if is_folder else 'file',
            'mime_type': item.get('file', {}).get('mimeType', '') if not is_folder else '',
            'size': int(item.get('size', 0)),
            'modified_time': item.get('lastModifiedDateTime', ''),
            'parents': [item['parentReference']['id']] if item.get('parentReference', {}).get('id') else [],
            'web_view_link': item.get('webUrl', ''),
            'source': 'onedrive',
        }

    def list_files(self, page_size=50, page_token=None, folder_id=None, query=None):
        """
        List files from OneDrive

        Args:
            page_size: Number of items to return (max 250)
            page_token: Full @odata.nextLink URL for pagination (or None)
            folder_id: ID of folder to list (None for root)
            query: Optional search query

        Returns:
            dict: {'files': [...], 'next_page_token': str|None, 'error': str|None}
        """
        if not self._refresh_token_if_needed():
            return {'files': [], 'next_page_token': None, 'error': 'Token expired and refresh failed'}

        try:
            # If we have a continuation link, follow it directly
            if page_token:
                response = requests.get(
                    page_token,
                    headers=self._get_headers(),
                )
            else:
                select = 'id,name,size,lastModifiedDateTime,folder,file,parentReference,webUrl'
                params = {
                    '$top': min(page_size, 250),
                    '$select': select,
                    '$orderby': 'lastModifiedDateTime desc',
                }

                if folder_id:
                    url = f'{self.BASE_URL}/me/drive/items/{folder_id}/children'
                else:
                    url = f'{self.BASE_URL}/me/drive/root/children'

                # $search is incompatible with $orderby, only use it when querying
                if query:
                    params.pop('$orderby')
                    params['$search'] = f'"{query}"'

                response = requests.get(url, headers=self._get_headers(), params=params)

            if response.status_code != 200:
                return {
                    'files': [],
                    'next_page_token': None,
                    'error': f'OneDrive API error: {response.text}'
                }

            data = response.json()
            files = [self._format_item(item) for item in data.get('value', [])]

            return {
                'files': files,
                'next_page_token': data.get('@odata.nextLink'),
                'error': None
            }

        except requests.RequestException as e:
            return {
                'files': [],
                'next_page_token': None,
                'error': f'Error listing OneDrive files: {str(e)}'
            }

    def get_file(self, file_id):
        """
        Get file metadata by ID

        Args:
            file_id: OneDrive item ID

        Returns:
            dict: File metadata or error
        """
        if not self._refresh_token_if_needed():
            return {'error': 'Token expired and refresh failed'}

        try:
            response = requests.get(
                f'{self.BASE_URL}/me/drive/items/{file_id}',
                headers=self._get_headers(),
                params={
                    '$select': 'id,name,size,lastModifiedDateTime,folder,file,parentReference,webUrl'
                }
            )

            if response.status_code == 404:
                return {'error': 'File not found'}

            if response.status_code != 200:
                return {'error': f'OneDrive API error: {response.text}'}

            result = self._format_item(response.json())
            result['error'] = None
            return result

        except requests.RequestException as e:
            return {'error': f'Error getting file: {str(e)}'}

    def download_file(self, file_id):
        """
        Download file content from OneDrive

        Args:
            file_id: OneDrive item ID

        Returns:
            dict: {'content': bytes, 'name': str, 'mime_type': str, 'size': int, 'error': str|None}
        """
        if not self._refresh_token_if_needed():
            return {'error': 'Token expired and refresh failed'}

        try:
            file_metadata = self.get_file(file_id)
            if file_metadata.get('error'):
                return file_metadata

            # Graph redirects (302) to a pre-authenticated URL; requests follows it
            response = requests.get(
                f'{self.BASE_URL}/me/drive/items/{file_id}/content',
                headers=self._get_headers(),
            )

            if response.status_code != 200:
                return {'error': f'Download failed: {response.text}'}

            return {
                'content': response.content,
                'name': file_metadata['name'],
                'mime_type': file_metadata['mime_type'],
                'size': len(response.content),
                'error': None
            }

        except requests.RequestException as e:
            return {'error': f'Error downloading file: {str(e)}'}

    def upload_file(self, file_content, filename, mime_type, parent_folder_id=None):
        """
        Upload a file to OneDrive (small upload, < 4 MB via simple PUT)

        Args:
            file_content: bytes (file content)
            filename: str (name for the file)
            mime_type: str (MIME type)
            parent_folder_id: str (folder ID to upload to, None for root)

        Returns:
            dict: Uploaded file metadata or error
        """
        if not self._refresh_token_if_needed():
            return {'error': 'Token expired and refresh failed'}

        try:
            if parent_folder_id:
                url = f'{self.BASE_URL}/me/drive/items/{parent_folder_id}:/{filename}:/content'
            else:
                url = f'{self.BASE_URL}/me/drive/root:/{filename}:/content'

            response = requests.put(
                url,
                headers={
                    **self._get_headers(),
                    'Content-Type': mime_type or 'application/octet-stream',
                },
                data=file_content,
            )

            if response.status_code not in (200, 201):
                return {'error': f'Upload failed: {response.text}'}

            item = response.json()
            result = self._format_item(item)
            result['size'] = len(file_content)
            result['error'] = None
            return result

        except requests.RequestException as e:
            return {'error': f'Error uploading file: {str(e)}'}

    def create_folder(self, folder_name, parent_folder_id=None):
        """
        Create folder in OneDrive

        Args:
            folder_name: str (name for the folder)
            parent_folder_id: str (parent folder ID, None for root)

        Returns:
            dict: Created folder metadata or error
        """
        if not self._refresh_token_if_needed():
            return {'error': 'Token expired and refresh failed'}

        try:
            if parent_folder_id:
                url = f'{self.BASE_URL}/me/drive/items/{parent_folder_id}/children'
            else:
                url = f'{self.BASE_URL}/me/drive/root/children'

            response = requests.post(
                url,
                headers={
                    **self._get_headers(),
                    'Content-Type': 'application/json',
                },
                json={
                    'name': folder_name,
                    'folder': {},
                    '@microsoft.graph.conflictBehavior': 'rename',
                },
            )

            if response.status_code not in (200, 201):
                return {'error': f'Create folder failed: {response.text}'}

            result = self._format_item(response.json())
            result['error'] = None
            return result

        except requests.RequestException as e:
            return {'error': f'Error creating folder: {str(e)}'}

    def delete_file(self, file_id):
        """
        Delete file from OneDrive

        Args:
            file_id: OneDrive item ID

        Returns:
            dict: {'success': bool, 'error': str|None}
        """
        if not self._refresh_token_if_needed():
            return {'success': False, 'error': 'Token expired and refresh failed'}

        try:
            response = requests.delete(
                f'{self.BASE_URL}/me/drive/items/{file_id}',
                headers=self._get_headers(),
            )

            if response.status_code == 204:
                return {'success': True, 'error': None}

            if response.status_code == 404:
                return {'success': False, 'error': 'File not found'}

            return {'success': False, 'error': f'Delete failed: {response.text}'}

        except requests.RequestException as e:
            return {'success': False, 'error': f'Error deleting file: {str(e)}'}

    def rename_file(self, file_id, new_name):
        """
        Rename file in OneDrive

        Args:
            file_id: OneDrive item ID
            new_name: New name for the file

        Returns:
            dict: Updated file metadata or error
        """
        if not self._refresh_token_if_needed():
            return {'error': 'Token expired and refresh failed'}

        try:
            response = requests.patch(
                f'{self.BASE_URL}/me/drive/items/{file_id}',
                headers={
                    **self._get_headers(),
                    'Content-Type': 'application/json',
                },
                json={'name': new_name},
            )

            if response.status_code == 404:
                return {'error': 'File not found'}

            if response.status_code != 200:
                return {'error': f'Rename failed: {response.text}'}

            result = self._format_item(response.json())
            result['error'] = None
            return result

        except requests.RequestException as e:
            return {'error': f'Error renaming file: {str(e)}'}
