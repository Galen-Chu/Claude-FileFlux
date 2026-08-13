"""
Shared interface for cloud storage services.

GoogleDriveService and OneDriveService both implement this contract, which
lets CloudDriveViewSet treat any connected provider uniformly. Every method
returns a plain dict carrying an 'error' key (None on success) so that the
view layer can surface failures without exceptions.
"""
from abc import ABC, abstractmethod


class CloudStorageService(ABC):
    """Abstract interface for an OAuth-backed cloud-drive file service."""

    def __init__(self, token):
        self.token = token
        self.user = token.user

    @abstractmethod
    def _refresh_token_if_needed(self):
        """Ensure the access token is valid, refreshing when possible. Returns bool."""
        ...

    @abstractmethod
    def list_files(self, page_size=50, page_token=None, folder_id=None, query=None):
        """Return {'files': [...], 'next_page_token': str|None, 'error': str|None}."""
        ...

    @abstractmethod
    def get_file(self, file_id):
        """Return file metadata dict; includes 'error': None on success."""
        ...

    @abstractmethod
    def download_file(self, file_id):
        """Return {'content': bytes, 'name', 'mime_type', 'size', 'error'}."""
        ...

    @abstractmethod
    def upload_file(self, file_content, filename, mime_type, parent_folder_id=None):
        """Return uploaded-file metadata dict; includes 'error': None on success."""
        ...

    @abstractmethod
    def create_folder(self, folder_name, parent_folder_id=None):
        """Return created-folder metadata dict; includes 'error': None on success."""
        ...

    @abstractmethod
    def delete_file(self, file_id):
        """Return {'success': bool, 'error': str|None}."""
        ...

    @abstractmethod
    def rename_file(self, file_id, new_name):
        """Return updated-file metadata dict; includes 'error': None on success."""
        ...
