"""
Serializers for file management API
"""
from rest_framework import serializers


class FileInfoSerializer(serializers.Serializer):
    """Serializer for file information"""

    name = serializers.CharField()
    path = serializers.CharField()
    size = serializers.IntegerField()
    modified_time = serializers.DateTimeField()
    source = serializers.CharField()
    is_directory = serializers.BooleanField(default=False)
    content_type = serializers.CharField(allow_null=True, required=False)
    etag = serializers.CharField(allow_null=True, required=False)


class FileListRequestSerializer(serializers.Serializer):
    """Serializer for file list request parameters"""

    source = serializers.CharField(
        required=False,
        allow_null=True,
        help_text='Filter by source: local, s3, or all (default: all)'
    )
    path = serializers.CharField(
        required=False,
        default='',
        help_text='Path to list files from'
    )
    search = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Optional case-insensitive filename search (local & S3)'
    )

    def validate_source(self, value):
        """Validate source parameter"""
        if value and value not in ['local', 's3']:
            raise serializers.ValidationError(
                "Source must be 'local', 's3', or omitted for all"
            )
        return value


class BulkRenameRequestSerializer(serializers.Serializer):
    """Serializer for bulk rename request"""

    files = serializers.ListField(
        child=serializers.CharField(),
        help_text='List of file paths to rename'
    )
    text = serializers.CharField(
        max_length=100,
        allow_blank=True,
        help_text='Text to add as prefix/suffix or replacement text (can be blank for replace mode to delete text)'
    )
    mode = serializers.ChoiceField(
        choices=['prefix', 'suffix', 'replace'],
        default='prefix',
        help_text='Mode: prefix, suffix, or replace'
    )
    add_sequence = serializers.BooleanField(
        default=False,
        help_text='Whether to add sequential numbering'
    )
    start_number = serializers.IntegerField(
        default=1,
        min_value=0,
        help_text='Starting number for sequence (default: 1)'
    )
    source = serializers.CharField(
        help_text='Storage source: local or s3'
    )

    # Replace mode specific fields
    find_text = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        help_text='Text to find (required for replace mode)'
    )
    case_sensitive = serializers.BooleanField(
        default=False,
        help_text='Case-sensitive matching (replace mode only)'
    )
    use_regex = serializers.BooleanField(
        default=False,
        help_text='Treat find_text as regular expression'
    )
    replace_all = serializers.BooleanField(
        default=True,
        help_text='Replace all occurrences or just the first'
    )

    def validate_source(self, value):
        """Validate source parameter"""
        if value not in ['local', 's3']:
            raise serializers.ValidationError("Source must be 'local' or 's3'")
        return value

    def validate_files(self, value):
        """Validate files list"""
        if not value:
            raise serializers.ValidationError("Files list cannot be empty")
        return value

    def validate(self, data):
        """Cross-field validation"""
        if data['mode'] == 'replace' and not data.get('find_text'):
            raise serializers.ValidationError(
                "find_text is required when mode is 'replace'"
            )

        # Validate regex if use_regex is True
        if data.get('use_regex') and data.get('find_text'):
            import re
            try:
                re.compile(data['find_text'])
            except re.error as e:
                raise serializers.ValidationError({
                    'find_text': f'Invalid regex pattern: {str(e)}'
                })

        return data


class FileDeleteRequestSerializer(serializers.Serializer):
    """Serializer for file delete request"""

    files = serializers.ListField(
        child=serializers.CharField(),
        help_text='List of file paths to delete'
    )
    source = serializers.CharField(
        help_text='Storage source: local or s3'
    )

    def validate_source(self, value):
        """Validate source parameter"""
        if value not in ['local', 's3']:
            raise serializers.ValidationError("Source must be 'local' or 's3'")
        return value

    def validate_files(self, value):
        """Validate files list"""
        if not value:
            raise serializers.ValidationError("Files list cannot be empty")
        return value


class FileUploadRequestSerializer(serializers.Serializer):
    """Serializer for file upload request"""

    file = serializers.FileField(
        help_text='File to upload'
    )
    dest_path = serializers.CharField(
        required=False,
        help_text='Destination path in S3 (default: original filename)'
    )


class FileDownloadRequestSerializer(serializers.Serializer):
    """Serializer for file download request"""

    source_path = serializers.CharField(
        help_text='Source path in S3'
    )
    dest_path = serializers.CharField(
        required=False,
        help_text='Local destination path (default: storage directory + filename)'
    )


class OperationResultSerializer(serializers.Serializer):
    """Serializer for operation results"""

    success = serializers.ListField(
        child=serializers.CharField(),
        help_text='List of successful operations'
    )
    failed = serializers.ListField(
        child=serializers.DictField(),
        help_text='List of failed operations with error messages'
    )


class FileOperationLogSerializer(serializers.Serializer):
    """Serializer for file operation log"""

    id = serializers.IntegerField()
    operation = serializers.CharField()
    source = serializers.CharField()
    file_path = serializers.CharField()
    old_path = serializers.CharField()
    timestamp = serializers.DateTimeField()
    success = serializers.BooleanField()
    error_message = serializers.CharField()
    file_size = serializers.IntegerField(allow_null=True)
