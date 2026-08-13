# FileFlux — Unified Cloud File Manager

[![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)](./VERSION.md)
[![Django](https://img.shields.io/badge/Django-6.0.2-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.14+-brightgreen.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-22%20passing-brightgreen.svg)](#-development)

A Django + Django REST Framework application that gives you one authenticated interface for managing files across **local storage, AWS S3, Google Drive, and OneDrive**, with a responsive web UI, a REST API, per-user audit logging, and OAuth tokens encrypted at rest.

> **Status:** v2.1.0 — feature-complete for local/S3/Google Drive/OneDrive file operations and authentication. Production-grade security hardening is in place but a production deployment still needs HTTPS, a real WSGI server, and managed secrets (see [Security](#-security)).

## ✨ Key Features

**Storage backends**
- 📁 **Local filesystem** and **AWS S3** (S3-compatible: MinIO, DigitalOcean Spaces, etc.)
- ☁️ **Google Drive** — full file operations via the Drive API v3 (list, upload, download, create folder, delete, rename, folder navigation, token refresh)
- ☁️ **OneDrive** — full file operations via the Microsoft Graph API
- 🔗 **Cloud drives share a uniform service interface** (`CloudStorageService`), so the API treats every provider the same

**File operations**
- 🔄 **Bulk rename** with prefix / suffix / **find-and-replace** modes, optional zero-padded sequential numbering, and regex support
- 🗑️ Bulk delete, upload, download
- 🔍 **Server-side filename search** over local/S3 listings (`?search=`)
- 📝 **Per-user audit logging** of every operation

**Auth & security**
- 👤 User registration / login (session auth for the web UI, DRF **token auth** for the API); all endpoints require authentication
- 🔐 **OAuth tokens encrypted at rest** (Fernet) — plaintext never stored in the DB
- 🛡️ OAuth **`state` CSRF nonce** validated on every cloud callback
- 🚦 **Rate limiting** (anon 60/min, authenticated 300/min)
- 🧱 Path-traversal validation, file-size limits, input sanitization

**Architecture**
- 🏗️ Strategy-pattern service layer (`BaseStorage` for local/S3; `CloudStorageService` for cloud providers)
- 🎨 Responsive Tailwind CSS UI, upload/download progress bars, Google Drive infinite-scroll pagination
- ✅ 22 automated tests (`python manage.py test`)

## 🚀 Quick Start

### Prerequisites
- Python 3.14+
- An AWS account (for S3), and Google Cloud / Microsoft Azure projects (for cloud drives) — only needed for those features

### Installation
```bash
# 1. Create + activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.template .env           # then edit .env (see below)

# 4. Apply migrations and create a user
python manage.py migrate
python manage.py createsuperuser   # or register via /register/

# 5. Run
python manage.py runserver
```

Open http://127.0.0.1:8000/ (file manager at `/manager/`, API browser at `/api/files/`).

### Environment variables (`.env`)
```env
# Django
DJANGO_SECRET_KEY=change-me-to-a-long-random-string   # required for production
DEBUG=True                                            # set False in production
ALLOWED_HOSTS=localhost,127.0.0.1                      # comma-separated

# Token encryption (Fernet urlsafe base64). If unset, one is derived from SECRET_KEY.
# Generate one: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FILEFLUX_ENCRYPTION_KEY=

# AWS / S3
AWS_ACCESS_KEY=...
AWS_SECRET_KEY=...
BUCKET_NAME=...
AWS_REGION=us-east-1

# Local storage
LOCAL_STORAGE_PATH=./storage
MAX_UPLOAD_SIZE_MB=100

# Google Drive OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Microsoft OneDrive OAuth
MS_CLIENT_ID=...
MS_CLIENT_SECRET=...
MS_TENANT_ID=common

# OAuth callback (must match the redirect URI registered with Google/Microsoft)
OAUTH_REDIRECT_URI=http://localhost:8000/oauth/callback/
```

## 📖 Usage

### Web UI
1. Register at `/register/` and log in.
2. Use the **file manager** (`/manager/`) — filter by source (All / Local / S3 / Google Drive), select files for bulk rename/delete, upload/download.
3. On your **profile** (`/profile/`), connect/disconnect Google Drive and OneDrive (real OAuth flow; runs against the provider once credentials are configured).

### REST API
All endpoints require auth. Pass `Authorization: Token <your-token>` (get a token via the Django admin or `rest_framework.authtoken`), or log in for session auth.

**Local / S3 files**
```bash
TOKEN=...   # DRF token

# List local files (with optional search)
curl -H "Authorization: Token $TOKEN" \
  "http://127.0.0.1:8000/api/files/?source=local&search=invoice"

# Bulk rename: find-and-replace + sequential numbering
curl -X POST http://127.0.0.1:8000/api/files/rename/ \
  -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -d '{"files":["doc1.txt","doc2.txt"],"text":"final","mode":"suffix",
       "add_sequence":true,"start_number":1,"source":"local"}'

# Upload to S3
curl -X POST http://127.0.0.1:8000/api/files/upload/ \
  -H "Authorization: Token $TOKEN" -F "file=@local.txt" -F "dest_path=remote.txt"

# Audit logs
curl -H "Authorization: Token $TOKEN" "http://127.0.0.1:8000/api/files/logs/?limit=20"
```

**Cloud drives** (`provider=googledrive` or `onedrive`)
```bash
# List files
curl -H "Authorization: Token $TOKEN" \
  "http://127.0.0.1:8000/api/cloud/files/?provider=googledrive"

# Upload to a cloud drive
curl -X POST http://127.0.0.1:8000/api/cloud/upload/ \
  -H "Authorization: Token $TOKEN" -F "file=@local.txt" -F "provider=onedrive"

# Rename a cloud file
curl -X PATCH http://127.0.0.1:8000/api/cloud/files/<file_id>/rename/ \
  -H "Authorization: Token $TOKEN" -H "Content-Type: application/json" \
  -d '{"new_name":"renamed.txt","provider":"googledrive"}'
```

## 🔌 API Reference

### Local / S3 (`/api/files/`)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/files/` | GET | List files (`source=local\|s3`, `path=`, `search=`) |
| `/api/files/rename/` | POST | Bulk rename (prefix/suffix/replace + sequence) |
| `/api/files/delete/` | POST | Bulk delete |
| `/api/files/upload/` | POST | Upload to S3 |
| `/api/files/download/` | POST | Download from S3 to local |
| `/api/files/logs/` | GET | Per-user audit logs |

### Cloud drives (`/api/cloud/`)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/cloud/files/` | GET | List files (`provider`, `folder_id`, `page_token`, `query`) |
| `/api/cloud/files/{id}/` | GET | File metadata (`provider`) |
| `/api/cloud/upload/` | POST | Upload (`file`, `provider`, `parent_folder_id?`) |
| `/api/cloud/download/` | POST | Download (`file_id`, `provider`) |
| `/api/cloud/create-folder/` | POST | Create folder (`name`, `provider`) |
| `/api/cloud/files/{id}/` | DELETE | Delete (`provider`) |
| `/api/cloud/files/{id}/rename/` | PATCH | Rename (`new_name`, `provider`) |

## 🏗️ Architecture

```
BaseStorage (abstract)            CloudStorageService (abstract)
    ├── LocalStorage                  ├── GoogleDriveService   (Drive API v3)
    ├── S3Storage                     └── OneDriveService      (Graph API)
    └── UnifiedStorage (local + S3)        └── CloudDriveViewSet (provider-agnostic)
```

- **Service layer** (`manager/services/`) — storage backends, cloud providers, and the cloud-drive connection manager. Each cloud provider conforms to the same interface, so the API is provider-agnostic.
- **API layer** (`manager/api_views.py`, `manager/cloud_api_views.py`) — DRF viewsets, validation, per-user audit logging.
- **Auth/OAuth** (`manager/auth_views.py`, `manager/cloud_views.py`, `manager/oauth_views.py`) — registration/login, OAuth connect flows with CSRF-protected `state`, token-exchange callbacks.
- **Models** (`manager/models.py`) — `FileOperation` (per-user audit log) and `CloudStorageToken` (encrypted OAuth tokens).
- **Frontend** (`templates/`) — Tailwind CSS + vanilla JS.

## 🔒 Security

**Implemented:**
- ✅ Authentication required on all endpoints (session + token)
- ✅ OAuth tokens **encrypted at rest** (Fernet via `EncryptedTextField`)
- ✅ OAuth `state` **CSRF nonce** validated on every callback
- ✅ Rate limiting (anon + authenticated)
- ✅ Path-traversal validation, file-size limits, input sanitization, password validators

**Still required for a production deployment:**
- ⚠️ HTTPS (TLS termination) and secure cookie settings
- ⚠️ A production WSGI server (gunicorn/uwsgi) behind a reverse proxy — not Django's `runserver`
- ⚠️ A strong `DJANGO_SECRET_KEY` and `FILEFLUX_ENCRYPTION_KEY` sourced from a secrets manager (not the dev fallback)
- ⚠️ `DEBUG=False` and a correct `ALLOWED_HOSTS`
- ⚠️ Rotate the committed dev secret key before exposing the repo

## 🛠️ Development

```bash
python manage.py test          # 22 tests
python manage.py makemigrations && python manage.py migrate
python manage.py createsuperuser
```

## 📦 Dependencies
Django 6.0.2, Django REST Framework 3.16.1, boto3 1.42.59, python-dotenv 1.2.2, requests 2.31.0, requests-toolbelt 1.0.0, cryptography 50.0.0. SQLite for development.

## 🗺️ Roadmap

**Done in v2.1.0:** OneDrive file operations, token encryption at rest, OAuth CSRF hardening, per-user audit logs, API filename search, test suite.

**Remaining:**
- [ ] Local/S3 pagination + infinite scroll in the UI
- [ ] S3 download progress + cancel in-progress transfers
- [ ] File preview (images/PDFs)
- [ ] Drag & drop upload / move files
- [ ] Shareable links (S3 presigned URLs)
- [ ] Bi-directional local↔S3 sync, file versioning

See [VERSION.md](./VERSION.md) and [CHANGELOG.md](./CHANGELOG.md) for history.

## 📄 License
For educational and development purposes.

---
**Version:** 2.1.0 · **Updated:** 2026-08-13
