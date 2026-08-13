"""
Google Drive API Service

Handles all Google Drive operations using the Google Drive API v3.
Uses OAuth 2.0 tokens stored in CloudStorageToken model.
"""

import json

import requests
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings

from .cloud_base import CloudStorageService


class GoogleDriveService(CloudStorageService):
    """Service class for Google Drive operations"""

    BASE_URL = 'https://www.googleapis.com/drive/v3'
    UPLOAD_URL = 'https://www.googleapis.com/upload/drive/v3'

    def __init__(self, token):
        """
        Initialize Google Drive service with user's token

        Args:
            token: CloudStorageToken instance for Google Drive
        """
        self.token = token
        self.user = token.user

    def _get_headers(self):
        """Get authorization headers for API requests"""
        return {
            'Authorization': f'Bearer {self.token.access_token}',
            'Content-Type': 'application/json'
        }

    def _refresh_token_if_needed(self):
        """
        Refresh access token if expired

        Returns:
            bool: True if token is valid (refreshed or not expired)
            False if refresh failed
        """
        # Check if token is still valid
        if self.token.token_expires_at and timezone.now() < self.token.token_expires_at:
            return True

        # Token is expired, need to refresh
        if not self.token.refresh_token:
            return False

        try:
            response = requests.post(
                'https://oauth2.googleapis.com/token',
                data={
                    'client_id': settings.GOOGLE_CLIENT_ID,
                    'client_secret': settings.GOOGLE_CLIENT_SECRET,
                    'refresh_token': self.token.refresh_token,
                    'grant_type': 'refresh_token'
                }
            )

            if response.status_code != 200:
                return False

            token_data = response.json()

            # Update token in database
            self.token.access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 3600)
            self.token.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
            self.token.save()

            return True

        except Exception as e:
            print(f"Error refreshing Google Drive token: {str(e)}")
            return False

    def list_files(self, page_size=50, page_token=None, folder_id=None, query=None):
        """
        List files from Google Drive

        Args:
            page_size: Number of files to return (max 100)
            page_token: Token for pagination
            folder_id: ID of folder to list (None for root)
            query: Optional search query

        Returns:
            dict: {
                'files': list of file objects,
                'next_page_token': token for next page (or None),
                'error': error message (or None)
            }
        """
        if not self._refresh_token_if_needed():
            return {'files': [], 'next_page_token': None, 'error': 'Token expired and refresh failed'}

        try:
            params = {
                'pageSize': min(page_size, 100),
                'fields': 'nextPageToken, files(id, name, mimeType, size, modifiedTime, parents, webViewLink)',
                'orderBy': 'modifiedTime desc'
            }

            if page_token:
                params['pageToken'] = page_token

            # Build query
            query_parts = []
            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")
            else:
                # Root folder - exclude files in trash
                query_parts.append("'root' in parents")

            if query:
                query_parts.append(f"name contains '{query}'")

            query_parts.append("trashed = false")
            params['q'] = ' and '.join(query_parts)

            response = requests.get(
                f'{self.BASE_URL}/files',
                headers=self._get_headers(),
                params=params
            )

            if response.status_code != 200:
                return {
                    'files': [],
                    'next_page_token': None,
                    'error': f'Google Drive API error: {response.text}'
                }

            data = response.json()

            # Format file objects
            files = []
            for file in data.get('files', []):
                files.append({
                    'id': file['id'],
                    'name': file['name'],
                    'type': 'folder' if file['mimeType'] == 'application/vnd.google-apps.folder' else 'file',
                    'mime_type': file.get('mimeType', ''),
                    'size': int(file.get('size', 0)),
                    'modified_time': file.get('modifiedTime', ''),
                    'parents': file.get('parents', []),
                    'web_view_link': file.get('webViewLink', ''),
                    'source': 'googledrive'
                })

            return {
                'files': files,
                'next_page_token': data.get('nextPageToken'),
                'error': None
            }

        except Exception as e:
            return {
                'files': [],
                'next_page_token': None,
                'error': f'Error listing Google Drive files: {str(e)}'
            }

    def get_file(self, file_id):
        """
        Get file metadata by ID

        Args:
            file_id: Google Drive file ID

        Returns:
            dict: File metadata or error
        """
        if not self._refresh_token_if_needed():
            return {'error': 'Token expired and refresh failed'}

        try:
            response = requests.get(
                f'{self.BASE_URL}/files/{file_id}',
                headers=self._get_headers(),
                params={
                    'fields': 'id, name, mimeType, size, modifiedTime, parents, webViewLink'
                }
            )

            if response.status_code == 404:
                return {'error': 'File not found'}

            if response.status_code != 200:
                return {'error': f'Google Drive API error: {response.text}'}

            file = response.json()

            return {
                'id': file['id'],
                'name': file['name'],
                'type': 'folder' if file['mimeType'] == 'application/vnd.google-apps.folder' else 'file',
                'mime_type': file.get('mimeType', ''),
                'size': int(file.get('size', 0)),
                'modified_time': file.get('modifiedTime', ''),
                'parents': file.get('parents', []),
                'web_view_link': file.get('webViewLink', ''),
                'source': 'googledrive',
                'error': None
            }

        except Exception as e:
            return {'error': f'Error getting file: {str(e)}'}

    def download_file(self, file_id):
        """
        Download file content from Google Drive

        Args:
            file_id: Google Drive file ID

        Returns:
            dict: {
                'content': bytes (file content),
                'name': str (filename),
                'mime_type': str,
                'error': str (or None)
            }
        """
        if not self._refresh_token_if_needed():
            return {'error': 'Token expired and refresh failed'}

        try:
            # First get file metadata
            file_metadata = self.get_file(file_id)
            if file_metadata.get('error'):
                return file_metadata

            # Download file content
            response = requests.get(
                f'{self.BASE_URL}/files/{file_id}',
                headers={
                    'Authorization': f'Bearer {self.token.access_token}'
                },
                params={'alt': 'media'}
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

        except Exception as e:
            return {'error': f'Error downloading file: {str(e)}'}

    def upload_file(self, file_content, filename, mime_type, parent_folder_id=None):
        """
        Upload file to Google Drive

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
            # Prepare metadata
            metadata = {
                'name': filename,
                'mimeType': mime_type
            }

            if parent_folder_id:
                metadata['parents'] = [parent_folder_id]
            else:
                metadata['parents'] = ['root']

            # Upload using multipart upload
            from io import BytesIO
            from requests_toolbelt.multipart.encoder import MultipartEncoder

            multipart_data = MultipartEncoder(
                fields={
                    'metadata': (None, json.dumps(metadata), 'application/json'),
                    'file': (filename, BytesIO(file_content), mime_type)
                }
            )

            response = requests.post(
                f'{self.UPLOAD_URL}/files',
                headers={
                    'Authorization': f'Bearer {self.token.access_token}',
                    'Content-Type': multipart_data.content_type
                },
                data=multipart_data,
                params={'uploadType': 'multipart'}
            )

            if response.status_code != 200:
                return {'error': f'Upload failed: {response.text}'}

            file = response.json()

            return {
                'id': file['id'],
                'name': file['name'],
                'type': 'file',
                'mime_type': file.get('mimeType', ''),
                'size': len(file_content),
                'source': 'googledrive',
                'error': None
            }

        except Exception as e:
            return {'error': f'Error uploading file: {str(e)}'}

    def create_folder(self, folder_name, parent_folder_id=None):
        """
        Create folder in Google Drive

        Args:
            folder_name: str (name for the folder)
            parent_folder_id: str (parent folder ID, None for root)

        Returns:
            dict: Created folder metadata or error
        """
        if not self._refresh_token_if_needed():
            return {'error': 'Token expired and refresh failed'}

        try:
            metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }

            if parent_folder_id:
                metadata['parents'] = [parent_folder_id]
            else:
                metadata['parents'] = ['root']

            response = requests.post(
                f'{self.BASE_URL}/files',
                headers=self._get_headers(),
                json=metadata
            )

            if response.status_code != 200:
                return {'error': f'Create folder failed: {response.text}'}

            folder = response.json()

            return {
                'id': folder['id'],
                'name': folder['name'],
                'type': 'folder',
                'mime_type': 'application/vnd.google-apps.folder',
                'source': 'googledrive',
                'error': None
            }

        except Exception as e:
            return {'error': f'Error creating folder: {str(e)}'}

    def delete_file(self, file_id):
        """
        Delete file from Google Drive

        Args:
            file_id: Google Drive file ID

        Returns:
            dict: {'success': bool, 'error': str or None}
        """
        if not self._refresh_token_if_needed():
            return {'success': False, 'error': 'Token expired and refresh failed'}

        try:
            response = requests.delete(
                f'{self.BASE_URL}/files/{file_id}',
                headers={
                    'Authorization': f'Bearer {self.token.access_token}'
                }
            )

            if response.status_code == 204:
                return {'success': True, 'error': None}

            if response.status_code == 404:
                return {'success': False, 'error': 'File not found'}

            return {
                'success': False,
                'error': f'Delete failed: {response.text}'
            }

        except Exception as e:
            return {'success': False, 'error': f'Error deleting file: {str(e)}'}

    def rename_file(self, file_id, new_name):
        """
        Rename file in Google Drive

        Args:
            file_id: Google Drive file ID
            new_name: New name for the file

        Returns:
            dict: Updated file metadata or error
        """
        if not self._refresh_token_if_needed():
            return {'error': 'Token expired and refresh failed'}

        try:
            metadata = {'name': new_name}

            response = requests.patch(
                f'{self.BASE_URL}/files/{file_id}',
                headers=self._get_headers(),
                json=metadata,
                params={'fields': 'id, name, mimeType, size, modifiedTime, parents, webViewLink'}
            )

            if response.status_code == 404:
                return {'error': 'File not found'}

            if response.status_code != 200:
                return {'error': f'Rename failed: {response.text}'}

            file = response.json()

            return {
                'id': file['id'],
                'name': file['name'],
                'type': 'folder' if file['mimeType'] == 'application/vnd.google-apps.folder' else 'file',
                'mime_type': file.get('mimeType', ''),
                'size': int(file.get('size', 0)),
                'modified_time': file.get('modifiedTime', ''),
                'parents': file.get('parents', []),
                'web_view_link': file.get('webViewLink', ''),
                'source': 'googledrive',
                'error': None
            }

        except Exception as e:
            return {'error': f'Error renaming file: {str(e)}'}
