"""
Local filesystem storage implementation
"""
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .base import BaseStorage, FileInfo
from .exceptions import (
    FileOperationError,
    FileNotFoundError as FileNotFound,
    PermissionDeniedError,
    InvalidPathError,
)


class LocalStorage(BaseStorage):
    """Local filesystem storage backend"""

    def __init__(self, base_path: str):
        """
        Initialize local storage

        Args:
            base_path: Base directory path for local storage
        """
        self.base_path = Path(base_path).resolve()
        self._ensure_base_path()

    def _ensure_base_path(self):
        """Ensure base path exists"""
        if not self.base_path.exists():
            self.base_path.mkdir(parents=True, exist_ok=True)

    def _validate_path(self, path: str) -> Path:
        """
        Validate and resolve file path

        Args:
            path: Relative file path

        Returns:
            Resolved absolute Path object

        Raises:
            InvalidPathError: If path is invalid or attempts directory traversal
        """
        if '..' in path or path.startswith('/') or path.startswith('\\'):
            raise InvalidPathError(path, "Path contains forbidden characters")

        full_path = (self.base_path / path).resolve()

        # Ensure path is within base_path (prevent directory traversal)
        try:
            full_path.relative_to(self.base_path)
        except ValueError:
            raise InvalidPathError(path, "Path attempts to escape base directory")

        return full_path

    def list_files(self, path: str = '') -> List[FileInfo]:
        """
        List files in local storage

        Args:
            path: Relative path to list

        Returns:
            List of FileInfo objects
        """
        files = []

        try:
            target_path = self._validate_path(path) if path else self.base_path

            if not target_path.exists():
                return files

            if not target_path.is_dir():
                return files

            with os.scandir(target_path) as entries:
                for entry in entries:
                    try:
                        stat = entry.stat()
                        file_info = FileInfo(
                            name=entry.name,
                            path=str(Path(path) / entry.name) if path else entry.name,
                            size=stat.st_size,
                            modified_time=datetime.fromtimestamp(stat.st_mtime),
                            source='local',
                            is_directory=entry.is_dir(),
                        )
                        files.append(file_info)
                    except (OSError, PermissionError) as e:
                        # Skip files we can't access
                        continue

            # Sort by name
            files.sort(key=lambda x: x.name)

        except Exception as e:
            raise FileOperationError(
                f"Failed to list files in {path}",
                operation='list',
                file_path=path,
                original_error=e
            )

        return files

    def rename_files(self, files: List[str], text: str, mode: str = 'prefix',
                     add_sequence: bool = False, start_number: int = 1,
                     find_text: Optional[str] = None, case_sensitive: bool = False,
                     use_regex: bool = False, replace_all: bool = True) -> dict:
        """
        Rename files by adding prefix/suffix or replacing text

        Args:
            files: List of file paths to rename
            text: Text to add as prefix/suffix or replacement text
            mode: 'prefix', 'suffix', or 'replace'
            add_sequence: Whether to add sequential numbering
            start_number: Starting number for sequence

            Replace mode specific:
            find_text: Text to find and replace (required for replace mode)
            case_sensitive: Case-sensitive matching (default: False)
            use_regex: Treat find_text as regex (default: False)
            replace_all: Replace all occurrences or just first (default: True)

        Returns:
            Dict with 'success' and 'failed' lists
        """
        result = {
            'success': [],
            'failed': []
        }

        for index, file_path in enumerate(files):
            try:
                full_path = self._validate_path(file_path)

                if not full_path.exists():
                    result['failed'].append({
                        'file': file_path,
                        'error': 'File not found'
                    })
                    continue

                parent = full_path.parent
                original_name = full_path.name

                # Split name and extension
                if '.' in original_name:
                    name_parts = original_name.rsplit('.', 1)
                    name_without_ext = name_parts[0]
                    extension = '.' + name_parts[1]
                else:
                    name_without_ext = original_name
                    extension = ''

                # Apply transformation based on mode
                if mode == 'prefix':
                    new_name = text + name_without_ext
                elif mode == 'suffix':
                    new_name = name_without_ext + text
                elif mode == 'replace':
                    if not find_text:
                        result['failed'].append({
                            'file': file_path,
                            'error': 'find_text is required for replace mode'
                        })
                        continue

                    # Perform replacement
                    if use_regex:
                        # Validate regex pattern
                        try:
                            pattern = re.compile(find_text)
                        except re.error as e:
                            result['failed'].append({
                                'file': file_path,
                                'error': f'Invalid regex pattern: {str(e)}'
                            })
                            continue

                        flags = 0 if case_sensitive else re.IGNORECASE
                        count = 0 if replace_all else 1
                        try:
                            new_name = re.sub(find_text, text, name_without_ext,
                                             count=count, flags=flags)
                        except Exception as e:
                            result['failed'].append({
                                'file': file_path,
                                'error': f'Regex replacement failed: {str(e)}'
                            })
                            continue
                    else:
                        # Simple string replacement
                        if case_sensitive:
                            if replace_all:
                                new_name = name_without_ext.replace(find_text, text)
                            else:
                                new_name = name_without_ext.replace(find_text, text, 1)
                        else:
                            # Case-insensitive replacement using regex
                            pattern = re.escape(find_text)
                            count = 0 if replace_all else 1
                            new_name = re.sub(pattern, text, name_without_ext,
                                             count=count, flags=re.IGNORECASE)
                else:
                    result['failed'].append({
                        'file': file_path,
                        'error': f'Invalid mode: {mode}'
                    })
                    continue

                # Add sequence number if requested
                if add_sequence:
                    sequence_num = start_number + index
                    new_name = new_name + f'_{sequence_num:03d}'

                # Add extension back
                new_name = new_name + extension
                new_path = parent / new_name

                # Check if new path already exists
                if new_path.exists() and new_path != full_path:
                    result['failed'].append({
                        'file': file_path,
                        'error': f'File already exists: {new_name}'
                    })
                    continue

                # Rename the file
                full_path.rename(new_path)

                result['success'].append({
                    'old_path': file_path,
                    'new_path': str(new_path.relative_to(self.base_path))
                })

            except FileOperationError as e:
                result['failed'].append({
                    'file': file_path,
                    'error': str(e)
                })
            except Exception as e:
                result['failed'].append({
                    'file': file_path,
                    'error': str(e)
                })

        return result

    def delete_files(self, files: List[str]) -> dict:
        """
        Delete files

        Args:
            files: List of file paths to delete

        Returns:
            Dict with 'success' and 'failed' lists
        """
        result = {
            'success': [],
            'failed': []
        }

        for file_path in files:
            try:
                full_path = self._validate_path(file_path)

                if not full_path.exists():
                    result['failed'].append({
                        'file': file_path,
                        'error': 'File not found'
                    })
                    continue

                if full_path.is_dir():
                    shutil.rmtree(full_path)
                else:
                    full_path.unlink()

                result['success'].append(file_path)

            except FileOperationError as e:
                result['failed'].append({
                    'file': file_path,
                    'error': str(e)
                })
            except PermissionError as e:
                result['failed'].append({
                    'file': file_path,
                    'error': 'Permission denied'
                })
            except Exception as e:
                result['failed'].append({
                    'file': file_path,
                    'error': str(e)
                })

        return result

    def upload_file(self, source_path: str, dest_path: str) -> bool:
        """
        Upload (copy) a file to local storage

        Args:
            source_path: Source file path (local)
            dest_path: Destination path in storage

        Returns:
            True if successful
        """
        try:
            source = Path(source_path)
            dest = self._validate_path(dest_path)

            if not source.exists():
                raise FileNotFound(source_path, operation='upload')

            # Ensure parent directory exists
            dest.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(source, dest)

            return True

        except FileOperationError:
            raise
        except PermissionError as e:
            raise PermissionDeniedError(dest_path, operation='upload')
        except Exception as e:
            raise FileOperationError(
                f"Failed to upload file to {dest_path}",
                operation='upload',
                file_path=dest_path,
                original_error=e
            )

    def download_file(self, source_path: str, dest_path: str) -> bool:
        """
        Download (copy) a file from local storage

        Args:
            source_path: Source path in storage
            dest_path: Local destination path

        Returns:
            True if successful
        """
        try:
            source = self._validate_path(source_path)
            dest = Path(dest_path)

            if not source.exists():
                raise FileNotFound(source_path, operation='download')

            # Ensure parent directory exists
            dest.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(source, dest)

            return True

        except FileOperationError:
            raise
        except PermissionError as e:
            raise PermissionDeniedError(source_path, operation='download')
        except Exception as e:
            raise FileOperationError(
                f"Failed to download file from {source_path}",
                operation='download',
                file_path=source_path,
                original_error=e
            )

    def file_exists(self, path: str) -> bool:
        """
        Check if file exists

        Args:
            path: File path

        Returns:
            True if file exists
        """
        try:
            full_path = self._validate_path(path)
            return full_path.exists()
        except Exception:
            return False

    def get_file_info(self, path: str) -> Optional[FileInfo]:
        """
        Get information about a file

        Args:
            path: File path

        Returns:
            FileInfo if exists, None otherwise
        """
        try:
            full_path = self._validate_path(path)

            if not full_path.exists():
                return None

            stat = full_path.stat()
            return FileInfo(
                name=full_path.name,
                path=path,
                size=stat.st_size,
                modified_time=datetime.fromtimestamp(stat.st_mtime),
                source='local',
                is_directory=full_path.is_dir(),
            )

        except Exception:
            return None
