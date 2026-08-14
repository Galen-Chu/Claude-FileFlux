# FileFlux Version Information

## Current Version: 2.2.0

**Release Date:** 2026-08-14
**Status:** All planned roadmap features implemented; production hardening in place (see README → Security)

---

## Version History

### Version 2.2.0 (2026-08-14)

**New Features:**
- **Pagination + infinite scroll** for local/S3 listings (all sources now paginate)
- **Browser streaming download** for local/S3 with progress bar; **cancel** for in-progress uploads/downloads
- **File preview** modal (images/PDFs; inline serving + Google Drive embed URLs)
- **Shareable links** — time-limited S3 presigned URLs with copy-to-clipboard
- **Drag-and-drop upload** to S3 / Google Drive current folder
- **Cross-source move** (local ↔ S3) via copy + delete, with `MOVE` audit operations
- **Bi-directional local ↔ S3 sync** — preview-first, last-write-wins, timestamp convergence; `SyncRun` model; `manage.py sync_storage [--dry-run]` for cron
- **S3 version history** — list / download / restore versions; `manage.py enable_s3_versioning`

**Tests:** 43 automated tests.

---

### Version 2.1.0 (2026-08-13)

**New Features:**
- **OneDrive file operations** (Microsoft Graph API) — list, get, upload, download, create folder, delete, rename, token refresh
- **Cloud service interface** — `GoogleDriveService` and `OneDriveService` now share a uniform `CloudStorageService` contract; `CloudDriveViewSet` is provider-agnostic
- **API filename search** (`?search=`) over local/S3 listings
- **Token encryption at rest** (Fernet via `EncryptedTextField`)
- **OAuth `state` CSRF nonce** on all cloud connect/callback flows
- **DRF rate limiting** (anon 60/min, user 300/min)
- **Per-user audit logging** (`FileOperation.user` FK + per-user logs endpoint)
- **Automated test suite** (22 tests)

**Fixed:**
- Google Drive upload JSON serialization bug (dict-repr → `json.dumps`)
- Bare `except:` → `except Exception:` in `LocalStorage.file_exists`

**Security:**
- `SECRET_KEY` / `DEBUG` / `ALLOWED_HOSTS` now environment-driven
- Removed dead `get_authorization_url()` placeholder method

**Dependencies:** + `cryptography==50.0.0`

---

### Version 2.0.0 (2026-03-03)

**New Features:**
- **User Authentication System** 🎉
  - User registration and login
  - Session-based authentication for web interface
  - Token-based authentication for REST API
  - User profile page
  - Protected file manager and API endpoints

- **Cloud Drive Integration Foundation** ☁️
  - OneDrive and Google Drive connection UI
  - CloudStorageToken model for OAuth tokens
  - Cloud drive manager service
  - Demo mode for testing without OAuth credentials
  - Connect/disconnect cloud drives functionality
  - Connection status display

**Improvements:**
- All API endpoints now require authentication
- Enhanced security with login required for file operations
- User-specific cloud drive connections
- Profile page with cloud drive management
- Settings icon in file manager header
- Comprehensive cloud drive setup documentation

**Technical Changes:**
- Added Django REST Framework authentication classes
- Added rest_framework.authtoken app
- Created CloudStorageToken model for OAuth tokens
- Created auth_views.py with registration/login/logout views
- Created cloud_views.py for cloud drive connections
- Created cloud_manager.py service
- Updated FileManagementViewSet with IsAuthenticated permission
- Added login/logout/profile URLs
- Added cloud drive connection URLs
- Created registration and profile templates
- Updated file_manager.html with user info and logout button
- Updated FileManagerView with login_required decorator
- Added cloud drive configuration to settings

**Files Modified:**
- `file_flux/settings.py`
- `manager/models.py`
- `manager/views.py`
- `manager/urls.py`
- `manager/api_views.py`
- `templates/file_manager.html`
- `.env`
- `requirements.txt`

**Files Created:**
- `manager/auth_views.py`
- `manager/cloud_views.py`
- `manager/services/cloud_manager.py`
- `templates/registration/login.html`
- `templates/registration/register.html`
- `templates/registration/profile.html`
- `manager/migrations/0002_cloudstoragetoken.py`
- `DOCUMENTATION_CLOUD_DRIVE_SETUP.md`
- `test_v2.0.0.py`

---

### Version 1.2.0 (2026-03-03)

**New Features:**
- **Enhanced Rename with Replace Mode** 🎉
  - Find and replace text in filenames
  - Case-sensitive and case-insensitive matching
  - Regular expression support for advanced patterns
  - Replace all occurrences or just the first
  - Replace with empty string (delete text)
  - Combine replace with sequential numbering

**Improvements:**
- Enhanced rename API with new parameters
- Updated frontend modal with three rename modes
- Better validation for regex patterns
- Improved error handling for replace operations

**Technical Changes:**
- Updated service layer to support replace mode
- Enhanced serializers with replace mode fields and validation
- Updated API views to handle all replace parameters
- Improved frontend JavaScript for mode switching

**Files Modified:**
- `manager/services/base.py`
- `manager/services/local_storage.py`
- `manager/services/s3_storage.py`
- `manager/services/unified_storage.py`
- `manager/serializers.py`
- `manager/api_views.py`
- `templates/file_manager.html`

---

### Version 1.1.0 (2026-03-03)

**New Features:**
- **Enhanced Rename Functionality** 🎉
  - Added prefix/suffix mode selection
  - Added optional sequential numbering with zero-padding
  - Configurable starting number for sequences
  - Improved rename modal UI with radio buttons and checkboxes
  - Three-digit sequence format (001, 002, 003, etc.)

**Improvements:**
- Better file extension handling during rename operations
- Enhanced UI/UX with clear labeling and helpful tooltips
- Updated rename API to support all new parameters
- Comprehensive testing of all rename scenarios

**Technical Changes:**
- Updated service layer to support mode, add_sequence, and start_number parameters
- Enhanced serializers with validation for new rename options
- Updated frontend JavaScript for dynamic form handling
- Improved error messages for rename failures

**Files Modified:**
- `manager/services/base.py`
- `manager/services/local_storage.py`
- `manager/services/s3_storage.py`
- `manager/services/unified_storage.py`
- `manager/serializers.py`
- `manager/api_views.py`
- `templates/file_manager.html`

---

### Version 1.0.0 (2026-03-03)

**Initial Release Features:**

**Core Functionality:**
- ✅ Unified file management across local storage and AWS S3
- ✅ Service layer architecture with abstract base storage
- ✅ RESTful API with Django REST Framework
- ✅ Web-based GUI with Tailwind CSS
- ✅ Multi-file selection and bulk operations
- ✅ Audit logging for all file operations

**File Operations:**
- ✅ List files from local storage
- ✅ List files from AWS S3 bucket
- ✅ Bulk rename with prefix (basic)
- ✅ Bulk delete files
- ✅ Upload files to S3
- ✅ Download files from S3 to local
- ✅ File metadata display (size, date, source)

**Technical Implementation:**
- ✅ Strategy pattern for storage backends
- ✅ Factory functions for service instantiation
- ✅ Comprehensive error handling
- ✅ Path validation and security checks
- ✅ Pagination for large file lists
- ✅ S3 paginator for buckets with 1000+ objects
- ✅ File size validation
- ✅ Cross-platform path handling

**Frontend Features:**
- ✅ Responsive design
- ✅ Source filter tabs (All/Local/S3)
- ✅ File table with sorting
- ✅ Multi-select with checkboxes
- ✅ Modal dialogs for operations
- ✅ Error/success notifications
- ✅ Loading states

**Database:**
- ✅ FileOperation model for audit logging
- ✅ SQLite database with migrations
- ✅ Operation tracking (UPLOAD, DOWNLOAD, RENAME, DELETE)

---

## Upcoming Features (Roadmap)

### Version 1.3.0 (Planned)
- [ ] Bi-directional sync between local and S3
- [ ] File versioning support
- [ ] Shareable links for S3 files
- [ ] Real-time updates via WebSocket

### Version 2.0.0 (Future)
- [ ] Authentication and authorization
- [ ] Multi-user support
- [ ] Advanced search with filters
- [ ] Batch operation queue
- [ ] Operation scheduling

---

## Feature Comparison

| Feature | v1.0.0 | v1.1.0 | v1.2.0 | v2.0.0 |
|---------|--------|--------|--------|--------|
| List files (Local/S3) | ✅ | ✅ | ✅ | ✅ |
| Bulk rename - Prefix only | ✅ | ✅ | ✅ | ✅ |
| Bulk rename - Prefix/Suffix | ❌ | ✅ | ✅ | ✅ |
| Bulk rename - Replace mode | ❌ | ❌ | ✅ | ✅ |
| Sequential numbering | ❌ | ✅ | ✅ | ✅ |
| Configurable start number | ❌ | ✅ | ✅ | ✅ |
| Case-sensitive replace | ❌ | ❌ | ✅ | ✅ |
| Regex pattern matching | ❌ | ❌ | ✅ | ✅ |
| Bulk delete | ✅ | ✅ | ✅ | ✅ |
| Upload to S3 | ✅ | ✅ | ✅ | ✅ |
| Download from S3 | ✅ | ✅ | ✅ | ✅ |
| Multi-file selection | ✅ | ✅ | ✅ | ✅ |
| Audit logging | ✅ | ✅ | ✅ | ✅ |
| Source filtering | ✅ | ✅ | ✅ | ✅ |
| Responsive UI | ✅ | ✅ | ✅ | ✅ |
| Error notifications | ✅ | ✅ | ✅ | ✅ |
| User authentication | ❌ | ❌ | ❌ | ✅ |
| User registration | ❌ | ❌ | ❌ | ✅ |
| Token-based API auth | ❌ | ❌ | ❌ | ✅ |
| User profile page | ❌ | ❌ | ❌ | ✅ |
| Cloud drive connection UI | ❌ | ❌ | ❌ | ✅ |
| OneDrive integration | ❌ | ❌ | ❌ | 🔧* |
| Google Drive integration | ❌ | ❌ | ❌ | 🔧* |

*🔧 = Foundation implemented, full OAuth requires credentials configuration

---

## Compatibility

### System Requirements
- **Python:** 3.14+
- **Django:** 6.0.2
- **Django REST Framework:** 3.16.1
- **boto3:** 1.42.59
- **python-dotenv:** 1.2.2

### Browser Support
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### AWS Services
- Amazon S3 (all regions)
- Compatible with S3-compatible storage (MinIO, etc.)

---

## Upgrade Guide

### Upgrading from v1.2.0 to v2.0.0

**IMPORTANT:** This version introduces authentication. All existing API endpoints now require authentication.

1. **Pull latest changes:**
   ```bash
   git pull origin main
   ```

2. **Update dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

4. **Create a user account:**
   - Navigate to `http://localhost:8000/register/`
   - Create your account
   - Or use Django admin: `python manage.py createsuperuser`

5. **Clear browser cache** to load updated frontend

6. **Restart development server:**
   ```bash
   python manage.py runserver
   ```

**Breaking Changes:**
- All API endpoints now require authentication (Session or Token)
- File manager now requires login
- Anonymous access is no longer supported

**API Changes:**
- All endpoints require authentication header:
  - Session auth: Login via `/login/` first
  - Token auth: Add `Authorization: Token <your-token>` header
- Token can be obtained via Django admin or `rest_framework.authtoken`

**Migration Notes:**
- New `CloudStorageToken` model added for future cloud drive integration
- `authtoken` app added to INSTALLED_APPS
- Authentication tables created automatically

---

### Upgrading from v1.1.0 to v1.2.0

1. **Pull latest changes:**
   ```bash
   git pull origin main
   ```

2. **Update dependencies (if changed):**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run migrations (if any):**
   ```bash
   python manage.py migrate
   ```

4. **Clear browser cache** to load updated frontend

5. **Restart development server:**
   ```bash
   python manage.py runserver
   ```

**Breaking Changes:** None - fully backward compatible

**API Changes:**
- `/api/files/rename/` now accepts additional optional parameters for replace mode:
  - `mode` can now be "replace" (in addition to "prefix" and "suffix")
  - `find_text` (required when mode is "replace")
  - `case_sensitive` (default: false)
  - `use_regex` (default: false)
  - `replace_all` (default: true)
- The `text` parameter can now be blank (useful for deleting text in replace mode)
- Old API calls continue to work (backward compatible)

---

### Upgrading from v1.0.0 to v1.1.0

1. **Pull latest changes:**
   ```bash
   git pull origin main
   ```

2. **Update dependencies (if changed):**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run migrations (if any):**
   ```bash
   python manage.py migrate
   ```

4. **Clear browser cache** to load updated frontend

5. **Restart development server:**
   ```bash
   python manage.py runserver
   ```

**Breaking Changes:** None - fully backward compatible

**API Changes:**
- `/api/files/rename/` now accepts additional optional parameters:
  - `mode` (default: "prefix")
  - `add_sequence` (default: false)
  - `start_number` (default: 1)
- Old API calls with only `prefix` parameter still work (backward compatible)

---

## Version Naming Convention

FileFlux follows [Semantic Versioning](https://semver.org/):

- **MAJOR** version (X.0.0): Incompatible API changes
- **MINOR** version (1.X.0): New features, backward compatible
- **PATCH** version (1.1.X): Bug fixes, backward compatible

---

## Support

For questions or issues with specific versions:
1. Check the CHANGELOG.md for detailed changes
2. Review IMPLEMENTATION_PLAN.md for technical details
3. See README.md for setup and usage instructions

---

**Last Updated:** 2026-03-03
**Maintained By:** FileFlux Development Team
