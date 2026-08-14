# Cloud Drive Integration Plan (OneDrive & Google Drive)

## Overview

Add support for connecting to Microsoft OneDrive and Google Drive, allowing users to manage files from these cloud storage providers alongside local storage and AWS S3.

---

## Current State Assessment

### What We Have ✅
- Abstract `BaseStorage` interface
- Local filesystem storage backend
- AWS S3 storage backend
- Unified storage manager
- No authentication system

### What We Need ❌
- User authentication system
- OAuth 2.0 implementation
- Token management and storage
- OneDrive storage backend
- Google Drive storage backend
- OAuth callback handlers
- Token refresh mechanisms

---

## Architecture Design

### 1. Authentication Layer (Required First)

**Why Authentication is Needed:**
- OAuth 2.0 requires user accounts
- Tokens must be associated with users
- Secure token storage requires user isolation
- API rate limits are per-user

**Implementation Options:**

#### Option A: Django Built-in Authentication (Recommended for v2.0)
```python
# file_flux/settings.py
INSTALLED_APPS = [
    # ...
    'django.contrib.auth',
    'django.contrib.contenttypes',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

#### Option B: Social Authentication with python-social-auth (Future)
```python
# Allows login with Google/Microsoft accounts
# More complex but better UX
INSTALLED_APPS = [
    # ...
    'social_django',
]
```

### 2. Token Storage Model

```python
# manager/models.py

class CloudStorageToken(models.Model):
    """Store OAuth tokens for cloud storage providers"""

    PROVIDER_CHOICES = [
        ('onedrive', 'Microsoft OneDrive'),
        ('googledrive', 'Google Drive'),
    ]

    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='cloud_tokens'
    )
    provider = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES
    )
    access_token = models.TextField(
        help_text='OAuth 2.0 access token'
    )
    refresh_token = models.TextField(
        help_text='OAuth 2.0 refresh token'
    )
    token_expires_at = models.DateTimeField(
        help_text='Token expiration timestamp'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'provider']
        indexes = [
            models.Index(fields=['user', 'provider']),
        ]

    def is_expired(self):
        """Check if token is expired"""
        from django.utils import timezone
        return timezone.now() >= self.token_expires_at

    def __str__(self):
        return f"{self.user.username} - {self.get_provider_display()}"
```

### 3. Storage Backend Implementations

#### OneDrive Backend

```python
# manager/services/onedrive_storage.py

import requests
from datetime import datetime, timedelta
from typing import List, Optional
from django.conf import settings

from .base import BaseStorage, FileInfo
from .exceptions import FileOperationError, StorageConnectionError


class OneDriveStorage(BaseStorage):
    """Microsoft OneDrive storage backend using Microsoft Graph API"""

    GRAPH_API_BASE = 'https://graph.microsoft.com/v1.0'

    def __init__(self, access_token: str, refresh_token: str = None,
                 token_expires_at: datetime = None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expires_at = token_expires_at
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

    def _refresh_access_token(self):
        """Refresh expired access token"""
        if not self.refresh_token:
            raise StorageConnectionError("No refresh token available")

        # Microsoft token endpoint
        token_url = f"https://login.microsoftonline.com/{settings.MS_TENANT_ID}/oauth2/v2.0/token"

        data = {
            'client_id': settings.MS_CLIENT_ID,
            'client_secret': settings.MS_CLIENT_SECRET,
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token',
            'scope': 'files.readwrite.all'
        }

        response = requests.post(token_url, data=data)

        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.token_expires_at = datetime.now() + timedelta(seconds=token_data['expires_in'])
            self.headers['Authorization'] = f'Bearer {self.access_token}'
            return True
        else:
            raise StorageConnectionError("Failed to refresh OneDrive token")

    def _check_token(self):
        """Check and refresh token if needed"""
        if self.token_expires_at and datetime.now() >= self.token_expires_at:
            self._refresh_access_token()

    def list_files(self, path: str = '') -> List[FileInfo]:
        """List files in OneDrive"""
        self._check_token()

        try:
            # Build URL
            url = f"{self.GRAPH_API_BASE}/me/drive/root"
            if path:
                url += f":/{path}:/children"
            else:
                url += "/children"

            response = requests.get(url, headers=self.headers)

            if response.status_code == 401:
                # Token expired, try refresh
                self._refresh_access_token()
                response = requests.get(url, headers=self.headers)

            if response.status_code != 200:
                raise FileOperationError(
                    f"Failed to list OneDrive files: {response.text}"
                )

            data = response.json()
            files = []

            for item in data.get('value', []):
                file_info = FileInfo(
                    name=item.get('name', ''),
                    path=item.get('parentReference', {}).get('path', '') + '/' + item.get('name', ''),
                    size=item.get('size', 0),
                    modified_time=datetime.fromisoformat(
                        item.get('lastModifiedDateTime', '').replace('Z', '+00:00')
                    ),
                    source='onedrive',
                    is_directory='folder' in item,
                    content_type=None,
                    etag=item.get('eTag', '')
                )
                files.append(file_info)

            return files

        except Exception as e:
            raise FileOperationError(
                f"Failed to list OneDrive files",
                operation='list',
                original_error=e
            )

    def upload_file(self, source_path: str, dest_path: str) -> bool:
        """Upload file to OneDrive using Microsoft Graph API"""
        self._check_token()

        try:
            # Read file
            with open(source_path, 'rb') as f:
                file_data = f.read()

            # Upload URL
            url = f"{self.GRAPH_API_BASE}/me/drive/root:/{dest_path}:/content"

            headers = self.headers.copy()
            headers['Content-Type'] = 'application/octet-stream'

            response = requests.put(url, headers=headers, data=file_data)

            if response.status_code in [200, 201]:
                return True
            else:
                raise FileOperationError(
                    f"Failed to upload to OneDrive: {response.text}",
                    operation='upload'
                )

        except Exception as e:
            raise FileOperationError(
                f"Failed to upload file to OneDrive",
                operation='upload',
                original_error=e
            )

    def download_file(self, source_path: str, dest_path: str) -> bool:
        """Download file from OneDrive"""
        self._check_token()

        try:
            url = f"{self.GRAPH_API_BASE}/me/drive/root:/{source_path}:/content"
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                with open(dest_path, 'wb') as f:
                    f.write(response.content)
                return True
            else:
                raise FileOperationError(
                    f"Failed to download from OneDrive: {response.text}",
                    operation='download'
                )

        except Exception as e:
            raise FileOperationError(
                f"Failed to download file from OneDrive",
                operation='download',
                original_error=e
            )

    # Implement other required methods...
    def rename_files(self, files, text, mode='prefix', add_sequence=False,
                     start_number=1, find_text=None, case_sensitive=False,
                     use_regex=False, replace_all=True):
        # Use Microsoft Graph API to rename
        # Similar to S3 (copy + delete pattern)
        pass

    def delete_files(self, files):
        # Use Microsoft Graph API to delete
        pass

    def file_exists(self, path):
        # Check if file exists
        pass

    def get_file_info(self, path):
        # Get file metadata
        pass
```

#### Google Drive Backend

```python
# manager/services/googledrive_storage.py

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from datetime import datetime
from typing import List
import io

from .base import BaseStorage, FileInfo
from .exceptions import FileOperationError, StorageConnectionError


class GoogleDriveStorage(BaseStorage):
    """Google Drive storage backend using Google Drive API v3"""

    SCOPES = ['https://www.googleapis.com/auth/drive.file']

    def __init__(self, access_token: str, refresh_token: str = None,
                 client_id: str = None, client_secret: str = None):
        self.credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret,
            token_uri='https://oauth2.googleapis.com/token',
            scopes=self.SCOPES
        )

        self.service = build('drive', 'v3', credentials=self.credentials)

    def list_files(self, path: str = '') -> List[FileInfo]:
        """List files in Google Drive"""
        try:
            # Google Drive doesn't have traditional paths
            # We'll list files in root or by parent folder ID

            query = "trashed = false"
            if path:
                # Need to resolve path to folder ID
                # This is more complex in Google Drive
                pass

            results = self.service.files().list(
                q=query,
                pageSize=100,
                fields="nextPageToken, files(id, name, size, modifiedTime, mimeType, md5Checksum)"
            ).execute()

            files = []
            for item in results.get('files', []):
                file_info = FileInfo(
                    name=item['name'],
                    path=item['id'],  # Use ID as path in Google Drive
                    size=int(item.get('size', 0)),
                    modified_time=datetime.fromisoformat(
                        item['modifiedTime'].replace('Z', '+00:00')
                    ),
                    source='googledrive',
                    is_directory=item.get('mimeType') == 'application/vnd.google-apps.folder',
                    content_type=item.get('mimeType'),
                    etag=item.get('md5Checksum', '')
                )
                files.append(file_info)

            return files

        except Exception as e:
            raise FileOperationError(
                f"Failed to list Google Drive files",
                operation='list',
                original_error=e
            )

    def upload_file(self, source_path: str, dest_path: str) -> bool:
        """Upload file to Google Drive"""
        try:
            file_metadata = {
                'name': dest_path.split('/')[-1]
            }

            media = MediaFileUpload(
                source_path,
                resumable=True
            )

            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

            return True

        except Exception as e:
            raise FileOperationError(
                f"Failed to upload file to Google Drive",
                operation='upload',
                original_error=e
            )

    def download_file(self, source_path: str, dest_path: str) -> bool:
        """Download file from Google Drive"""
        try:
            # source_path is the file ID in Google Drive
            request = self.service.files().get_media(fileId=source_path)

            with open(dest_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()

            return True

        except Exception as e:
            raise FileOperationError(
                f"Failed to download file from Google Drive",
                operation='download',
                original_error=e
            )

    # Implement other required methods...
```

---

## OAuth 2.0 Implementation

### 1. Settings Configuration

```python
# file_flux/settings.py

# Microsoft OneDrive
MS_CLIENT_ID = os.getenv('MS_CLIENT_ID')
MS_CLIENT_SECRET = os.getenv('MS_CLIENT_SECRET')
MS_TENANT_ID = os.getenv('MS_TENANT_ID', 'common')  # 'common' for multi-tenant

# Google Drive
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

# OAuth redirect URI
OAUTH_REDIRECT_URI = os.getenv('OAUTH_REDIRECT_URI', 'http://localhost:8000/oauth/callback/')
```

### 2. OAuth Views

```python
# manager/oauth_views.py

from django.shortcuts import redirect
from django.conf import settings
from django.urls import reverse
import requests
from urllib.parse import urlencode

def onedrive_auth(request):
    """Initiate OneDrive OAuth flow"""
    params = {
        'client_id': settings.MS_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': settings.OAUTH_REDIRECT_URI,
        'scope': 'files.readwrite.all offline_access',
        'response_mode': 'query',
    }

    auth_url = f"https://login.microsoftonline.com/{settings.MS_TENANT_ID}/oauth2/v2.0/authorize?{urlencode(params)}"
    return redirect(auth_url)


def google_auth(request):
    """Initiate Google Drive OAuth flow"""
    params = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': settings.OAUTH_REDIRECT_URI,
        'scope': 'https://www.googleapis.com/auth/drive.file',
        'access_type': 'offline',
        'prompt': 'consent',
    }

    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
    return redirect(auth_url)


def oauth_callback(request):
    """Handle OAuth callback from providers"""
    code = request.GET.get('code')
    state = request.GET.get('state')  # Contains provider info

    if not code:
        return redirect('/manager/?error=auth_failed')

    # Exchange code for tokens
    # This would be determined by the state parameter
    provider = state or 'onedrive'

    if provider == 'onedrive':
        token_url = f"https://login.microsoftonline.com/{settings.MS_TENANT_ID}/oauth2/v2.0/token"
        data = {
            'client_id': settings.MS_CLIENT_ID,
            'client_secret': settings.MS_CLIENT_SECRET,
            'code': code,
            'redirect_uri': settings.OAUTH_REDIRECT_URI,
            'grant_type': 'authorization_code',
        }
    elif provider == 'googledrive':
        token_url = 'https://oauth2.googleapis.com/token'
        data = {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'code': code,
            'redirect_uri': settings.OAUTH_REDIRECT_URI,
            'grant_type': 'authorization_code',
        }

    response = requests.post(token_url, data=data)

    if response.status_code == 200:
        token_data = response.json()

        # Store tokens in database
        from .models import CloudStorageToken
        from django.utils import timezone
        from datetime import timedelta

        CloudStorageToken.objects.update_or_create(
            user=request.user,
            provider=provider,
            defaults={
                'access_token': token_data['access_token'],
                'refresh_token': token_data.get('refresh_token', ''),
                'token_expires_at': timezone.now() + timedelta(seconds=token_data['expires_in']),
            }
        )

        return redirect('/manager/?connected=true')
    else:
        return redirect('/manager/?error=token_exchange_failed')
```

### 3. URL Configuration

```python
# manager/urls.py

urlpatterns = [
    # ... existing patterns
    path('oauth/onedrive/', onedrive_auth, name='onedrive_auth'),
    path('oauth/google/', google_auth, name='google_auth'),
    path('oauth/callback/', oauth_callback, name='oauth_callback'),
]
```

---

## Frontend Integration

### Connect Cloud Drives UI

```html
<!-- In file_manager.html -->

<div class="mb-6">
    <h3 class="text-sm font-medium text-gray-700 mb-2">Connected Storage</h3>
    <div class="flex space-x-3">
        <button onclick="connectOneDrive()" class="flex items-center px-4 py-2 border rounded-lg hover:bg-gray-50">
            <img src="/static/onedrive-icon.png" class="w-5 h-5 mr-2">
            Connect OneDrive
        </button>
        <button onclick="connectGoogleDrive()" class="flex items-center px-4 py-2 border rounded-lg hover:bg-gray-50">
            <img src="/static/googledrive-icon.png" class="w-5 h-5 mr-2">
            Connect Google Drive
        </button>
    </div>
</div>

<script>
function connectOneDrive() {
    window.location.href = '/oauth/onedrive/';
}

function connectGoogleDrive() {
    window.location.href = '/oauth/google/';
}
</script>
```

---

## Implementation Phases

### Phase 1: Authentication System (v2.0.0) ⭐ Priority
- [ ] Add Django authentication
- [ ] User registration/login views
- [ ] Token authentication for API
- [ ] User model and permissions
- [ ] Login/logout UI

**Estimated Time:** 3-5 days

### Phase 2: OneDrive Integration (v2.1.0)
- [ ] Register Azure AD app
- [ ] Implement OneDriveStorage backend
- [ ] OAuth 2.0 flow for OneDrive
- [ ] Token storage model
- [ ] Token refresh mechanism
- [ ] Test all operations (list, upload, download, rename, delete)

**Estimated Time:** 5-7 days

### Phase 3: Google Drive Integration (v2.2.0)
- [ ] Register Google Cloud project
- [ ] Implement GoogleDriveStorage backend
- [ ] OAuth 2.0 flow for Google
- [ ] Token management
- [ ] Test all operations

**Estimated Time:** 5-7 days

### Phase 4: Unified Multi-Cloud (v2.3.0)
- [ ] Update UnifiedStorage to support multiple clouds
- [ ] UI for selecting storage source
- [ ] File operations across all sources
- [ ] Connection status indicators
- [ ] Error handling for disconnected accounts

**Estimated Time:** 3-4 days

---

## Configuration Requirements

### .env File Additions

```bash
# Microsoft OneDrive
MS_CLIENT_ID=your_azure_app_client_id
MS_CLIENT_SECRET=your_azure_app_client_secret
MS_TENANT_ID=common  # or specific tenant ID

# Google Drive
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# OAuth
OAUTH_REDIRECT_URI=http://localhost:8000/oauth/callback/
```

### Azure AD Setup (OneDrive)

1. Go to Azure Portal → Azure Active Directory → App registrations
2. Create new registration
3. Set redirect URI: `http://localhost:8000/oauth/callback/`
4. Grant API permissions: `Files.ReadWrite.All`, `offline_access`
5. Generate client secret
6. Copy client ID and secret to .env

### Google Cloud Setup (Google Drive)

1. Go to Google Cloud Console → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID
3. Application type: Web application
4. Add authorized redirect URI: `http://localhost:8000/oauth/callback/`
5. Enable Google Drive API
6. Copy client ID and secret to .env

---

## Security Considerations

### Critical Security Requirements

1. **HTTPS in Production**
   - OAuth requires HTTPS in production
   - Use secure cookies
   - Enable HSTS

2. **Token Encryption**
   ```python
   # Encrypt tokens in database
   from cryptography.fernet import Fernet

   # In CloudStorageToken model
   def set_access_token(self, token):
       f = Fernet(settings.ENCRYPTION_KEY)
       self.access_token = f.encrypt(token.encode())

   def get_access_token(self):
       f = Fernet(settings.ENCRYPTION_KEY)
       return f.decrypt(self.access_token).decode()
   ```

3. **State Parameter**
   - Use state parameter in OAuth to prevent CSRF
   - Validate state in callback

4. **Token Scope Limitation**
   - Request minimum required scopes
   - OneDrive: `files.readwrite.all`
   - Google Drive: `drive.file` (only files created by app)

5. **Rate Limiting**
   - Implement API rate limiting
   - Respect provider quotas

---

## API Rate Limits

### OneDrive (Microsoft Graph)
- Throttling varies by endpoint
- Usually 10-20 requests per 10 seconds
- Retry-After header provided

### Google Drive
- 1,000 requests per 100 seconds per user
- 10 requests per second per user
- Quota can be increased in Google Cloud Console

---

## Cost Considerations

### Free Tiers

**OneDrive (Personal):**
- Free: 5 GB
- Microsoft 365 Personal: 1 TB

**Google Drive:**
- Free: 15 GB
- Google One: 100 GB - 2 TB

### API Costs
- OneDrive API: Free
- Google Drive API: Free (within quota)

---

## Alternative: Use Rclone (Simpler Approach)

Instead of implementing OAuth from scratch, use Rclone as a backend:

```bash
# Install rclone
pip install rclone-python

# Rclone already supports OneDrive, Google Drive, and 40+ providers
# Configure via rclone config (handles OAuth automatically)
```

**Benefits:**
- No OAuth implementation needed
- 40+ cloud providers supported
- Battle-tested code
- Handles token refresh automatically

**Implementation:**
```python
# manager/services/rclone_storage.py
import rclone

class RcloneStorage(BaseStorage):
    def __init__(self, remote_name: str):
        self.rclone = rclone.with_config({
            remote_name: {
                'type': 'onedrive',
                'token': access_token,
            }
        })

    def list_files(self, path=''):
        result = self.rclone.ls(f"{self.remote_name}:{path}")
        # Parse and return FileInfo objects
```

**Recommendation:** Use Rclone for v2.0 to save development time

---

## Recommendation for Implementation Order

### Option A: Full OAuth Implementation (Professional)
**Timeline:** 3-4 weeks
**Pros:**
- Full control
- Better UX
- More professional

**Cons:**
- Significant development effort
- More maintenance
- Security complexity

### Option B: Rclone Backend (Pragmatic) ⭐ Recommended
**Timeline:** 1-2 weeks
**Pros:**
- Much faster to implement
- 40+ providers supported
- Less maintenance
- Already handles OAuth

**Cons:**
- External dependency
- Less control
- Requires rclone installation

### Option C: Phase Approach (Balanced)
1. **v2.0.0:** Add authentication only
2. **v2.1.0:** Implement Replace Mode rename feature
3. **v2.2.0:** Add cloud drives using Rclone
4. **v3.0.0:** Native OAuth if needed

---

## Success Metrics

- [ ] Users can connect OneDrive account
- [ ] Users can connect Google Drive account
- [ ] Files from all sources display in unified list
- [ ] Upload/download works for all providers
- [ ] Token refresh works automatically
- [ ] Connection status visible in UI
- [ ] All operations logged to database

---

## Next Steps

1. **Decide approach:** Native OAuth vs Rclone
2. **Implement authentication system** (required for both)
3. **Create cloud storage tokens model**
4. **Implement chosen cloud provider**
5. **Test thoroughly with real accounts**
6. **Document setup process**

---

**Estimated Total Time:**
- With Rclone: 2-3 weeks
- Native OAuth: 4-5 weeks

**Target Version:** 2.0.0 (authentication), 2.1.0 (cloud drives)
