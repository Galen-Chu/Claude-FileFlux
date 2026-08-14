# Changelog

All notable changes to the FileFlux project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.3.0] - 2026-08-14

### Added
- **CLAUDE.md**: repo-level development guide — commands, architecture, conventions, gotchas — for Claude Code sessions and collaborators.
- **Docker deployment**: `Dockerfile` (python:3.14-slim, gunicorn, whitenoise, entrypoint runs migrations) + `docker-compose.yml` (named volumes for SQLite via the new `DB_PATH` setting and for local storage; optional commented-out MinIO service) + `.dockerignore`.
- **S3-compatible endpoints**: `S3_ENDPOINT_URL` env var (and `S3Storage(endpoint_url=...)`) lets boto3 target MinIO/Spaces instead of real AWS S3.
- whitenoise middleware + `STATIC_ROOT` so the container serves static files; gunicorn + whitenoise added to requirements.

### Changed
- Documentation consolidated and condensed: root keeps README/VERSION/CHANGELOG/CLAUDE.md;
  `docs/` reduced to four files — `oauth-setup.md` (merged provider guides),
  `architecture.md` (merged tech deep-dives, current state), `history.md` (merged
  PLAN_ documents), plus an index. Redundant session logs (QUICKSTART, ROADMAP,
  RELEASE_NOTES, IMPLEMENTATION_SUMMARY, TESTING_*, *_ANALYSIS, superseded
  TECH_OAUTH demo doc) removed. README trimmed, made bilingual
  (English / Traditional Chinese, paired side by side), and its API reference
  completed with the 2.2/2.3 endpoints.

---

## [2.2.0] - 2026-08-14

### Added
- **Local/S3 pagination**: `page`/`page_size` on `/api/files/` (returns `total`/`has_next`/`next_page`); infinite scroll enabled for all sources.
- **Browser streaming download** (`GET /api/files/download-file/`) for local and S3 with progress; the UI Download button now saves to the browser. `?inline=1` serves preview-friendly content.
- **Cancel transfers**: Cancel buttons abort in-progress uploads/downloads (XHR abort).
- **File preview**: modal viewer for images/PDFs (inline URL for local/S3, embed URLs for Google Drive).
- **Share links**: `POST /api/files/share/` generates time-limited S3 presigned URLs (expiry clamped 60s–7d); UI Share button with copy-to-clipboard.
- **Drag-and-drop upload**: the file table is a drop zone targeting the active cloud source.
- **Cross-source move**: `POST /api/files/move/` (local ↔ S3 via copy + delete, destination folder prefix); `MOVE` audit operation (migration 0005).
- **Bi-directional sync**: `SyncService` (last-write-wins, 2s epsilon, timestamp convergence so pairs don't ping-pong), `SyncRun` model (migration 0006), `/api/files/sync-preview/` + `/api/files/sync-run/`, `manage.py sync_storage [--dry-run]`.
- **S3 versioning**: `/api/files/versions/` list, `/api/files/versions/restore/`, `version_id` on download-file, `manage.py enable_s3_versioning`.

### Tests
- Suite grown from 22 to 43 tests (pagination, streaming download, share links, move, sync plan/execute/convergence, versioning — S3 paths mocked).

---

## [2.1.0] - 2026-08-13

### Added
- **OneDrive file operations**: new `OneDriveService` implementing the full operation set (list, get, upload, download, create folder, delete, rename, token refresh) against the Microsoft Graph API. Cloud drives now share a uniform `CloudStorageService` interface, and `CloudDriveViewSet` is provider-agnostic — OneDrive endpoints return real results instead of "not yet supported".
- **API filename search**: `?search=` parameter on `/api/files/` for case-insensitive filtering of local/S3 listings.
- **Token encryption at rest**: `EncryptedTextField` (Fernet) transparently encrypts OAuth `access_token`/`refresh_token` in the database; reads decrypt automatically. Existing code is unchanged.
- **OAuth `state` CSRF nonce**: connect flows now bind a random nonce to the session, validated on the callback (forged callbacks are rejected).
- **DRF rate limiting**: anon 60/min, authenticated 300/min.
- **Per-user audit logs**: `FileOperation` gained a `user` FK; the logs endpoint filters to the requesting user (superusers see all).
- **Profile flash messages**: OAuth success/error messages now render on the profile page.
- **Test suite**: 22 automated tests covering models, encryption, local-storage logic, the cloud-service interface, API auth/routing, OAuth state, and search.

### Changed
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` are now environment-driven (dev fallback retained).
- `requirements.txt`: added `cryptography==50.0.0`.
- Cloud ViewSet refactored to a single provider-agnostic path via a `_resolve()` helper.

### Fixed
- Google Drive upload metadata was built with a Python `dict`-repr-to-JSON hack (`str().replace`) that produced invalid JSON for filenames containing quotes; now uses `json.dumps`.
- Bare `except:` in `LocalStorage.file_exists` narrowed to `except Exception:`.

### Removed
- Dead `CloudDriveManager.get_authorization_url()` (returned placeholder URLs; unused — real URLs are built in `cloud_views.py`).

---

## [1.1.0] - 2026-03-03

### Added

#### Enhanced Rename Functionality
- **Prefix/Suffix Mode Selection**: Users can now choose to add text as either a prefix (before filename) or suffix (after filename, before extension)
  - Example: `file.txt` with text `"backup_"` → `backup_file.txt` (prefix mode)
  - Example: `file.txt` with text `"_backup"` → `file_backup.txt` (suffix mode)

- **Sequential Numbering**: Optional feature to add zero-padded sequential numbers to filenames
  - Format: Three-digit padding (001, 002, 003, etc.)
  - Configurable starting number (default: 1, range: 0+)
  - Works with both prefix and suffix modes
  - Example: `file1.txt`, `file2.txt`, `file3.txt` → `file1_001.txt`, `file2_002.txt`, `file3_003.txt`

- **Enhanced Rename Modal UI**:
  - Radio buttons for mode selection (prefix/suffix)
  - Checkbox to enable sequential numbering
  - Number input field for start number (conditional display)
  - Helpful tooltips and examples
  - Clear visual feedback

#### Backend Enhancements
- Updated `BaseStorage.rename_files()` signature to accept:
  - `text: str` - Text to add as prefix or suffix
  - `mode: str` - 'prefix' or 'suffix' (default: 'prefix')
  - `add_sequence: bool` - Enable sequential numbering (default: False)
  - `start_number: int` - Starting number for sequence (default: 1)

- Enhanced file extension handling:
  - Extensions are preserved correctly in all rename operations
  - Sequence numbers added before extension
  - Proper handling of files without extensions

#### API Improvements
- `/api/files/rename/` now accepts additional parameters:
  ```json
  {
    "files": ["file1.txt", "file2.txt"],
    "text": "backup_",
    "mode": "prefix",  // NEW: "prefix" or "suffix"
    "add_sequence": true,  // NEW: optional
    "start_number": 1,  // NEW: optional
    "source": "local"
  }
  ```

- Response format enhanced to include new path names with proper formatting

### Changed

#### Service Layer
- `manager/services/local_storage.py`: Enhanced `rename_files()` method
  - Added logic for prefix vs suffix application
  - Implemented sequence number generation with zero-padding
  - Improved file extension handling
  - Better error messages for rename failures

- `manager/services/s3_storage.py`: Enhanced `rename_files()` method
  - S3-compatible rename with new parameters
  - Maintains S3 path structure during rename
  - Proper handling of directory paths in S3 keys

- `manager/services/unified_storage.py`: Updated parameter passing
  - Routes all new parameters to appropriate storage backend
  - Maintains consistent interface across backends

#### Serializers
- `manager/serializers.py`: Updated `BulkRenameRequestSerializer`
  - Changed `prefix` field to `text` for clarity
  - Added `mode` field with choices validation
  - Added `add_sequence` boolean field
  - Added `start_number` integer field with min value validation
  - Updated help text and field descriptions

#### Views
- `manager/api_views.py`: Updated `rename()` action
  - Extracts and validates all new parameters
  - Passes parameters to unified storage service
  - Maintains backward compatibility (old API calls still work)

#### Frontend
- `templates/file_manager.html`: Enhanced rename modal
  - Radio button group for mode selection
  - Conditional display of sequence options
  - Dynamic form validation
  - Improved user guidance with examples

- JavaScript functions updated:
  - `toggleSequenceOptions()`: Shows/hides sequence number options
  - `confirmRename()`: Collects and sends all new parameters
  - `hideRenameModal()`: Resets all form fields including new inputs

### Fixed

- File extension handling now works correctly for files with multiple dots (e.g., `archive.tar.gz`)
- Sequence numbers are properly zero-padded to three digits
- Modal properly resets all fields when closed
- Backend validation prevents invalid mode values

### Security

- No new security concerns
- Path validation still enforced for all rename operations
- Input sanitization maintained for all new parameters

### Performance

- No performance degradation
- Rename operations remain efficient
- API response times unchanged

### Backward Compatibility

- **Fully backward compatible** with v1.0.0
- Old API calls with only `prefix` parameter still work (defaults to prefix mode, no sequence)
- Existing integrations continue to work without changes

---

## [1.0.0] - 2026-03-03

### Added

#### Core Infrastructure
- **Service Layer Architecture**
  - Abstract `BaseStorage` class defining storage interface
  - `FileInfo` dataclass for unified file information
  - Custom exception classes for error handling

- **Local Storage Backend**
  - `LocalStorage` implementation using pathlib
  - Cross-platform path handling
  - Directory traversal prevention
  - File operations: list, rename, delete, upload, download

- **S3 Storage Backend**
  - `S3Storage` implementation using boto3
  - AWS credential management
  - S3 paginator for large buckets
  - Copy+delete pattern for rename operations

- **Unified Storage Service**
  - `UnifiedStorage` aggregating multiple backends
  - Single interface for all storage operations
  - Source-based routing to correct backend

#### REST API
- **FileManagementViewSet** with actions:
  - `list()` - GET `/api/files/` - List files with optional source filter
  - `rename()` - POST `/api/files/rename/` - Bulk rename files
  - `delete()` - POST `/api/files/delete/` - Bulk delete files
  - `upload()` - POST `/api/files/upload/` - Upload file to S3
  - `download()` - POST `/api/files/download/` - Download file from S3
  - `logs()` - GET `/api/files/logs/` - View operation audit trail

- **Serializers** for request/response validation:
  - FileInfoSerializer
  - FileListRequestSerializer
  - BulkRenameRequestSerializer
  - FileDeleteRequestSerializer
  - FileUploadRequestSerializer
  - FileDownloadRequestSerializer
  - OperationResultSerializer
  - FileOperationLogSerializer

#### Database Models
- **FileOperation** model for audit logging:
  - Tracks operation type (UPLOAD, DOWNLOAD, RENAME, DELETE)
  - Records source (local/s3)
  - Stores file paths and metadata
  - Success/failure status with error messages
  - Automatic timestamp

#### Web Interface
- **File Manager GUI** (`/manager/`):
  - Responsive design with Tailwind CSS
  - Source filter tabs (All Files, Local, S3)
  - File table with columns: checkbox, name, size, modified, source, actions
  - Multi-file selection with checkboxes
  - Select all/none functionality

- **Bulk Operations**:
  - Rename modal with prefix input
  - Delete with confirmation
  - Upload modal with file selection
  - Individual file download buttons

- **User Experience**:
  - Loading states and indicators
  - Error toast notifications
  - Success toast notifications
  - Empty state display
  - Selection count display

#### Configuration
- Environment variables support via python-dotenv
- Configurable settings:
  - LOCAL_STORAGE_PATH
  - AWS credentials and bucket
  - AWS_REGION
  - MAX_UPLOAD_SIZE_MB

#### Error Handling
- Custom `FileOperationError` exception
- Specific exception types:
  - FileNotFoundError
  - PermissionDeniedError
  - StorageConnectionError
  - InvalidPathError
  - FileSizeExceededError

#### Security Features
- Path validation to prevent directory traversal
- File size validation for uploads
- Input sanitization in serializers
- Security documentation for production deployment

#### Documentation
- Comprehensive IMPLEMENTATION_PLAN.md
- README.md with setup instructions
- API reference documentation
- Verification and testing guides
- Troubleshooting guide

### Technical Details

#### Dependencies
- Django 6.0.2
- Django REST Framework 3.16.1
- boto3 1.42.59
- python-dotenv 1.2.2

#### Database
- SQLite3 for development
- Django migrations
- Indexed fields for performance

#### Frontend
- Tailwind CSS via CDN
- Vanilla JavaScript (no frameworks)
- Fetch API for HTTP requests
- No build step required

---

## Version Planning

### [1.2.0] - Planned

#### To Be Added
- File preview functionality
  - Image thumbnails in file table
  - PDF preview modal
  - Video player integration

- Search and filter features
  - Search by filename
  - Filter by date range
  - Filter by file size
  - Filter by file type

- Enhanced upload
  - Drag & drop interface
  - Multiple file selection
  - Upload progress indicators
  - Cancel upload capability

### [1.3.0] - Planned

#### To Be Added
- Synchronization features
  - Bi-directional sync between local and S3
  - Conflict detection and resolution
  - Scheduled sync jobs
  - Sync status display

- File versioning
  - Track file versions
  - Restore previous versions
  - Version history display
  - Diff viewer for text files

- Sharing capabilities
  - Generate shareable S3 links
  - Set link expiration times
  - Access control settings
  - Share link management

- Real-time updates
  - WebSocket integration
  - Live file list updates
  - Operation notifications
  - Multi-user awareness

### [2.0.0] - Future

#### Breaking Changes Expected
- Authentication system
  - User accounts and sessions
  - API token authentication
  - Role-based permissions
  - Access control lists

- Multi-tenancy
  - Multi-user support
  - User-specific storage
  - Shared resources
  - Team collaboration

- Advanced features
  - Batch operation queue
  - Operation scheduling
  - Advanced search with indexing
  - Custom metadata fields

---

## Release Notes Format

Each release includes:
1. **Added**: New features
2. **Changed**: Changes to existing features
3. **Deprecated**: Features to be removed
4. **Removed**: Features removed in this version
5. **Fixed**: Bug fixes
6. **Security**: Security improvements

---

## Migration Guides

### Migrating to v1.1.0

**No database migrations required** - fully backward compatible.

**API Changes:**
- Old rename API calls continue to work
- New parameters are optional with sensible defaults

**Frontend Changes:**
- New modal fields are optional
- Old functionality preserved

**Recommended Actions:**
1. Update to take advantage of new rename features
2. Update any API clients to use new parameters if desired
3. Clear browser cache for updated UI

---

## Support Policy

- **Current version (1.1.0)**: Full support
- **Previous version (1.0.0)**: Security fixes only
- **Older versions**: No support

---

**Last Updated:** 2026-03-03
**Maintained By:** FileFlux Development Team
