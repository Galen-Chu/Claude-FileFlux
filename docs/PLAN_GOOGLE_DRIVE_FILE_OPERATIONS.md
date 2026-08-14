# Phase A Implementation Plan: Google Drive File Operations

## Overview

This document outlines the implementation plan for Google Drive file operations in FileFlux.

## Completed Components

### 1. Service Layer
✅ **File**: `manager/services/google_drive_service.py`
✅ **Features**:
- List files with pagination
- Get file metadata
- Upload files (multipart upload)
- Download files
- Create folders
- Delete files
- Automatic token refresh

### 2. API Endpoints
✅ **File**: `manager/cloud_api_views.py`
✅ **Endpoints**:
- `GET /api/cloud/files/` - List Google Drive files
- `GET /api/cloud/files/{file_id}/` - Get file metadata
- `POST /api/cloud/upload/` - Upload file
- `POST /api/cloud/download/` - Download file
- `POST /api/cloud/create-folder/` - Create folder
- `DELETE /api/cloud/files/{file_id}/` - Delete file

### 3. URL Configuration
✅ **File**: `manager/api_urls.py`
✅ **Updated**: Added CloudDriveViewSet to router

### 4. Dependencies
✅ **File**: `requirements.txt`
✅ **Added**: `requests-toolbelt==1.0.0` (for multipart uploads)

### 5. Testing
✅ **File**: `test_google_drive_api.py`
✅ **Features**: Interactive test script for service layer and API endpoints

## API Endpoint Details

### List Files
```
GET /api/cloud/files/?provider=googledrive&folder_id=xxx&page_size=50

Response:
{
  "files": [
    {
      "id": "abc123",
      "name": "My Document.pdf",
      "type": "file",
      "mime_type": "application/pdf",
      "size": 123456,
      "modified_time": "2026-03-10T10:00:00Z",
      "parents": ["root"],
      "web_view_link": "https://drive.google.com/...",
      "source": "googledrive"
    }
  ],
  "next_page_token": "xyz789",
  "provider": "googledrive"
}
```

### Upload File
```
POST /api/cloud/upload/
Content-Type: multipart/form-data

Parameters:
- file: (binary file)
- provider: "googledrive"
- parent_folder_id: (optional)

Response:
{
  "id": "new_file_id",
  "name": "uploaded_file.pdf",
  "type": "file",
  "mime_type": "application/pdf",
  "size": 123456,
  "source": "googledrive",
  "error": null
}
```

### Download File
```
POST /api/cloud/download/
Content-Type: application/json

Parameters:
{
  "file_id": "abc123",
  "provider": "googledrive"
}

Response: Binary file download with headers
```

### Create Folder
```
POST /api/cloud/create-folder/
Content-Type: application/json

Parameters:
{
  "name": "New Folder",
  "provider": "googledrive",
  "parent_folder_id": (optional)
}

Response:
{
  "id": "folder_id",
  "name": "New Folder",
  "type": "folder",
  "mime_type": "application/vnd.google-apps.folder",
  "source": "googledrive",
  "error": null
}
```

### Delete File
```
DELETE /api/cloud/files/abc123/?provider=googledrive

Response:
{
  "success": true,
  "message": "File deleted"
}
```

## Next Steps

### Immediate Testing
1. **Start Django server**: `python manage.py runserver`
2. **Get auth token**: Login to FileFlux and get session ID
3. **Run test script**: `python test_google_drive_api.py`
4. **Choose option 1** to test service layer
5. **Choose option 2** to test API endpoints

### Phase B: Frontend Integration (Next)
- Update file manager UI to add Google Drive tab
- Connect to API endpoints
- Add file browser for Google Drive
- Implement upload/download UI

- Add loading states and error handling

### Security Considerations
- ✅ All endpoints require authentication
- ✅ Tokens are user-specific
- ✅ File operations are logged
- ⏳ Consider adding rate limiting
- ⏳ Consider file size limits
- ⏳ Consider allowed file types

## Troubleshooting

### Common Issues

1. **401 Unauthorized**
   - Token may be expired
   - Solution: Token refresh is automatic

2. **403 Forbidden**
   - Token doesn't have permission
   - Solution: Re-authorize with proper scopes

3. **404 Not Found**
   - File ID doesn't exist
   - Solution: Handle error gracefully

4. **400 Bad Request**
   - Missing parameters
   - Solution: Check request format

## Success Criteria

✅ Service layer can list files from Google Drive
✅ API endpoints return correct responses
✅ Token refresh works automatically
✅ File upload creates file in Google Drive
✅ File download returns correct file
✅ Folder creation works
✅ File deletion removes file
✅ All operations logged to database

## Status: Ready for Testing
