# FileFlux — Unified Cloud File Manager

[![Version](https://img.shields.io/badge/version-2.3.0-blue.svg)](./VERSION.md)
[![Django](https://img.shields.io/badge/Django-6.0.2-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.14+-brightgreen.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-43%20passing-brightgreen.svg)](#-development)

A Django + DRF application giving one authenticated interface for files across
**local storage, AWS S3 (or MinIO), Google Drive, and OneDrive** — web UI + REST API,
per-user audit logging, OAuth tokens encrypted at rest, containerized deployment.

> **Status:** v2.3.0 — all planned roadmap features implemented. Production still needs
> HTTPS and managed secrets (see [Security](#-security)).

## ✨ Features

- **Four backends, two contracts** — local/S3 (`BaseStorage`) and Google Drive/OneDrive
  (`CloudStorageService`), so cloud providers are interchangeable
- **Bulk rename** — prefix / suffix / find-and-replace, regex, sequential numbering
- **Pagination + infinite scroll** on all sources; **filename search** on local/S3
- **Transfers** — browser streaming download with progress, cancellable uploads/downloads
- **Preview** images/PDFs; **share** S3 objects via time-limited presigned URLs
- **Drag-and-drop upload** (S3 / Google Drive); **cross-source move** (local ↔ S3)
- **Bi-directional local ↔ S3 sync** — preview-first, last-write-wins, timestamp
  convergence; `manage.py sync_storage` for cron
- **S3 version history** — list/download/restore; `manage.py enable_s3_versioning`
- **Auth & security** — session + token auth everywhere, tokens encrypted at rest
  (Fernet), OAuth `state` CSRF nonce, rate limiting, path-traversal validation
- 43 automated tests; Docker deployment with optional MinIO backend

## 🚀 Quick Start

```bash
python -m venv venv && venv\Scripts\activate   # Windows (source venv/bin/activate on unix)
pip install -r requirements.txt
cp .env.template .env                          # fill in what you need (see file for all vars)
python manage.py migrate && python manage.py createsuperuser
python manage.py runserver                     # http://127.0.0.1:8000/
```

**Docker:** `cp .env.template .env` (set a strong `DJANGO_SECRET_KEY`) then
`docker compose up --build` — gunicorn + whitenoise, auto-migrations, SQLite and
storage on named volumes. Uncomment the `minio` service in `docker-compose.yml` and
set `S3_ENDPOINT_URL=http://minio:9000` for a local S3 backend.

Key env vars (full list in [.env.template](./.env.template)): `DJANGO_SECRET_KEY`,
`DEBUG`, `ALLOWED_HOSTS`, `FILEFLUX_ENCRYPTION_KEY`, `S3_ENDPOINT_URL`,
`AWS_*`/`BUCKET_NAME`, `GOOGLE_*` / `MS_*` (OAuth — see [docs/oauth-setup.md](./docs/oauth-setup.md)).

## 📖 Usage

**Web UI:** register at `/register/`; manage files at `/manager/` (tabs per source,
bulk select, rename/delete/move, upload/download with progress, preview, share,
sync, drag-and-drop); connect cloud drives on `/profile/`.

**API** — all endpoints require auth (`Authorization: Token <token>`, or session):

```bash
# List local files with search + pagination
curl -H "Authorization: Token $T" "localhost:8000/api/files/?source=local&search=invoice&page=1"
# Bulk rename (find-and-replace + numbering)
curl -X POST -H "Authorization: Token $T" -H "Content-Type: application/json" \
  -d '{"files":["a.txt","b.txt"],"text":"final","mode":"suffix","add_sequence":true,"source":"local"}' \
  localhost:8000/api/files/rename/
# Preview a sync plan, then run it
curl -H "Authorization: Token $T" localhost:8000/api/files/sync-preview/
```

### API Reference — Local / S3 (`/api/files/`)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/files/` | GET | List (`source`, `path`, `search`, `page`, `page_size`) |
| `/api/files/rename/` | POST | Bulk rename (prefix/suffix/replace + sequence) |
| `/api/files/delete/` | POST | Bulk delete |
| `/api/files/upload/` | POST | Upload to S3 |
| `/api/files/download/` | POST | Copy S3 → server local storage |
| `/api/files/download-file/` | GET | Stream to browser (`source`, `path`, `inline=1` for preview, `version_id`) |
| `/api/files/move/` | POST | Move local ↔ S3 (`files`, `source`, `dest_source`, `dest_path?`) |
| `/api/files/share/` | POST | Time-limited presigned S3 URL (`path`, `expires_in?`) |
| `/api/files/versions/` | GET | S3 version list (`path`) |
| `/api/files/versions/restore/` | POST | Restore old version as latest (`path`, `version_id`) |
| `/api/files/sync-preview/` | GET | Local ↔ S3 sync plan (dry run) |
| `/api/files/sync-run/` | POST | Execute sync |
| `/api/files/logs/` | GET | Per-user audit logs |

### API Reference — Cloud drives (`/api/cloud/`, `provider=googledrive\|onedrive`)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/cloud/files/` | GET | List (`folder_id`, `page_token`, `query`) |
| `/api/cloud/files/{id}/` | GET | File metadata |
| `/api/cloud/upload/` | POST | Upload (`file`, `parent_folder_id?`) |
| `/api/cloud/download/` | POST | Download to browser (`file_id`) |
| `/api/cloud/create-folder/` | POST | Create folder (`name`) |
| `/api/cloud/files/{id}/` | DELETE | Delete |
| `/api/cloud/files/{id}/rename/` | PATCH | Rename (`new_name`) |

## 🏗️ Architecture

```
BaseStorage (abstract)             CloudStorageService (abstract)
    ├── LocalStorage                   ├── GoogleDriveService   (Drive API v3)
    ├── S3Storage                      └── OneDriveService      (Graph API)
    └── UnifiedStorage + SyncService        └── CloudDriveViewSet (provider-agnostic)
```

`manager/services/` holds the backends; `manager/api_views.py` / `cloud_api_views.py`
are thin DRF layers with per-user audit logging; OAuth connect/callback flows live in
`cloud_views.py` / `oauth_views.py`. Details: [docs/architecture.md](./docs/architecture.md),
conventions: [CLAUDE.md](./CLAUDE.md).

## 🔒 Security

Implemented: auth on all endpoints, OAuth tokens encrypted at rest (Fernet),
`state` CSRF nonce on callbacks, rate limiting, path-traversal validation,
file-size limits, password validators.

Still required for production: HTTPS + secure cookies, a reverse proxy in front of
the container (the image runs gunicorn + whitenoise), strong `DJANGO_SECRET_KEY` /
`FILEFLUX_ENCRYPTION_KEY` from a secrets manager, `DEBUG=False` + correct
`ALLOWED_HOSTS`, and rotating the committed dev secret key.

## 🛠️ Development

```bash
python manage.py test manager     # 43 tests
```

Full guide (commands, conventions, gotchas): [CLAUDE.md](./CLAUDE.md).

**Dependencies:** Django 6.0.2 · DRF 3.16.1 · boto3 · python-dotenv · requests ·
requests-toolbelt · cryptography · gunicorn + whitenoise (Docker). SQLite in development.

## 🗺️ Roadmap

All planned features are done. Future ideas (unscheduled): true S3
continuation-token pagination, background sync scheduler, Google Drive sync/sharing
parity, local file versioning. History: [CHANGELOG](./CHANGELOG.md) · [docs/history.md](./docs/history.md).

## 📄 License
For educational and development purposes.

---
**Version:** 2.3.0 · **Updated:** 2026-08-14
