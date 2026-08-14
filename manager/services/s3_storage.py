"""
AWS S3 storage implementation
"""
import os
import re
from datetime import datetime
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from .base import BaseStorage, FileInfo
from .exceptions import (
    FileOperationError,
    StorageConnectionError,
    FileNotFoundError as FileNotFound,
)


class S3Storage(BaseStorage):
    """AWS S3 storage backend"""

    def __init__(self, bucket_name: str, region: str = 'us-east-1',
                 access_key: str = None, secret_key: str = None,
                 endpoint_url: str = None):
        """
        Initialize S3 storage

        Args:
            bucket_name: S3 bucket name
            region: AWS region
            access_key: AWS access key (optional, uses env if not provided)
            secret_key: AWS secret key (optional, uses env if not provided)
            endpoint_url: optional endpoint for S3-compatible services (e.g. MinIO)
        """
        self.bucket_name = bucket_name
        self.region = region

        # Initialize S3 client
        try:
            client_kwargs = {
                'region_name': region,
                'aws_access_key_id': access_key or os.getenv('AWS_ACCESS_KEY_ID'),
                'aws_secret_access_key': secret_key or os.getenv('AWS_SECRET_ACCESS_KEY'),
            }
            if endpoint_url:
                client_kwargs['endpoint_url'] = endpoint_url
            self.client = boto3.client('s3', **client_kwargs)
        except NoCredentialsError as e:
            raise StorageConnectionError(
                "Failed to initialize S3 client: No credentials provided",
                storage_type='s3',
                original_error=e
            )
        except Exception as e:
            raise StorageConnectionError(
                f"Failed to initialize S3 client: {str(e)}",
                storage_type='s3',
                original_error=e
            )

    def list_files(self, path: str = '') -> List[FileInfo]:
        """
        List files in S3 bucket

        Args:
            path: Prefix path to list

        Returns:
            List of FileInfo objects
        """
        files = []

        try:
            # Use paginator for large buckets
            paginator = self.client.get_paginator('list_objects_v2')

            # Ensure path ends with / for proper prefix matching
            prefix = path.rstrip('/') + '/' if path else ''

            operation_parameters = {
                'Bucket': self.bucket_name,
            }

            if prefix:
                operation_parameters['Prefix'] = prefix

            for page in paginator.paginate(**operation_parameters):
                if 'Contents' not in page:
                    continue

                for obj in page['Contents']:
                    # Skip the directory itself
                    if obj['Key'] == prefix:
                        continue

                    # Get relative path
                    key = obj['Key']
                    name = key.split('/')[-1]

                    # Determine if it's a directory (ends with /)
                    is_dir = key.endswith('/')

                    file_info = FileInfo(
                        name=name,
                        path=key,
                        size=obj.get('Size', 0),
                        modified_time=obj.get('LastModified', datetime.now()),
                        source='s3',
                        is_directory=is_dir,
                        etag=obj.get('ETag', '').strip('"'),
                    )
                    files.append(file_info)

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise FileOperationError(
                f"Failed to list S3 files: {error_code}",
                operation='list',
                file_path=path,
                original_error=e
            )
        except Exception as e:
            raise FileOperationError(
                f"Failed to list S3 files",
                operation='list',
                file_path=path,
                original_error=e
            )

        # Sort by name
        files.sort(key=lambda x: x.name)
        return files

    def rename_files(self, files: List[str], text: str, mode: str = 'prefix',
                     add_sequence: bool = False, start_number: int = 1,
                     find_text: Optional[str] = None, case_sensitive: bool = False,
                     use_regex: bool = False, replace_all: bool = True) -> dict:
        """
        Rename files by adding prefix/suffix or replacing text (copy + delete in S3)

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
                # Check if file exists
                if not self.file_exists(file_path):
                    result['failed'].append({
                        'file': file_path,
                        'error': 'File not found'
                    })
                    continue

                # Get file name from path
                original_name = file_path.split('/')[-1]

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

                # Calculate new path
                path_parts = file_path.rsplit('/', 1)
                if len(path_parts) == 2:
                    directory, _ = path_parts
                    new_path = f"{directory}/{new_name}"
                else:
                    new_path = new_name

                # Check if new path already exists
                if self.file_exists(new_path) and new_path != file_path:
                    result['failed'].append({
                        'file': file_path,
                        'error': f'File already exists: {new_path}'
                    })
                    continue

                # Copy to new location
                self.client.copy_object(
                    Bucket=self.bucket_name,
                    CopySource={'Bucket': self.bucket_name, 'Key': file_path},
                    Key=new_path
                )

                # Delete original
                self.client.delete_object(
                    Bucket=self.bucket_name,
                    Key=file_path
                )

                result['success'].append({
                    'old_path': file_path,
                    'new_path': new_path
                })

            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                result['failed'].append({
                    'file': file_path,
                    'error': f'S3 error: {error_code}'
                })
            except Exception as e:
                result['failed'].append({
                    'file': file_path,
                    'error': str(e)
                })

        return result

    def delete_files(self, files: List[str]) -> dict:
        """
        Delete files from S3

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
                # Check if file exists
                if not self.file_exists(file_path):
                    result['failed'].append({
                        'file': file_path,
                        'error': 'File not found'
                    })
                    continue

                # Delete object
                self.client.delete_object(
                    Bucket=self.bucket_name,
                    Key=file_path
                )

                result['success'].append(file_path)

            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                result['failed'].append({
                    'file': file_path,
                    'error': f'S3 error: {error_code}'
                })
            except Exception as e:
                result['failed'].append({
                    'file': file_path,
                    'error': str(e)
                })

        return result

    def upload_file(self, source_path: str, dest_path: str) -> bool:
        """
        Upload file to S3

        Args:
            source_path: Local source file path
            dest_path: S3 destination path

        Returns:
            True if successful
        """
        try:
            if not os.path.exists(source_path):
                raise FileNotFound(source_path, operation='upload')

            self.client.upload_file(
                source_path,
                self.bucket_name,
                dest_path
            )

            return True

        except FileOperationError:
            raise
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise FileOperationError(
                f"Failed to upload to S3: {error_code}",
                operation='upload',
                file_path=dest_path,
                original_error=e
            )
        except Exception as e:
            raise FileOperationError(
                f"Failed to upload file to S3",
                operation='upload',
                file_path=dest_path,
                original_error=e
            )

    def download_file(self, source_path: str, dest_path: str) -> bool:
        """
        Download file from S3

        Args:
            source_path: S3 source path
            dest_path: Local destination path

        Returns:
            True if successful
        """
        try:
            # Check if file exists
            if not self.file_exists(source_path):
                raise FileNotFound(source_path, operation='download')

            # Ensure parent directory exists
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            self.client.download_file(
                self.bucket_name,
                source_path,
                dest_path
            )

            return True

        except FileOperationError:
            raise
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise FileOperationError(
                f"Failed to download from S3: {error_code}",
                operation='download',
                file_path=source_path,
                original_error=e
            )
        except Exception as e:
            raise FileOperationError(
                f"Failed to download file from S3",
                operation='download',
                file_path=source_path,
                original_error=e
            )

    def file_exists(self, path: str) -> bool:
        """
        Check if file exists in S3

        Args:
            path: S3 file path

        Returns:
            True if file exists
        """
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=path)
            return True
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                return False
            # For other errors, re-raise
            raise FileOperationError(
                f"Failed to check file existence in S3",
                operation='exists',
                file_path=path,
                original_error=e
            )
        except Exception:
            return False

    def get_file_info(self, path: str) -> Optional[FileInfo]:
        """
        Get information about a file

        Args:
            path: S3 file path

        Returns:
            FileInfo if exists, None otherwise
        """
        try:
            response = self.client.head_object(Bucket=self.bucket_name, Key=path)

            name = path.split('/')[-1]
            return FileInfo(
                name=name,
                path=path,
                size=response.get('ContentLength', 0),
                modified_time=response.get('LastModified', datetime.now()),
                source='s3',
                content_type=response.get('ContentType'),
                etag=response.get('ETag', '').strip('"'),
            )

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                return None
            raise FileOperationError(
                f"Failed to get file info from S3",
                operation='info',
                file_path=path,
                original_error=e
            )
        except Exception:
            return None
