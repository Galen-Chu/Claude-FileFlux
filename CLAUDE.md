# CLAUDE.md — Development Guide for Claude Code

Guidance for Claude Code when working in this repository. For user-facing
documentation see [README.md](./README.md); for history see [CHANGELOG.md](./CHANGELOG.md).

## Commands

```bash
# Virtual environment (Python 3.14)
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # Linux/macOS
pip install -r requirements.txt

# Database
python manage.py migrate
python manage.py createsuperuser

# Dev server
python manage.py runserver       # http://127.0.0.1:8000/

# Tests — ALWAYS run before committing
python manage.py test manager

# System check
python manage.py check

# S3 sync (bi-directional, last-write-wins; needs AWS credentials)
python manage.py sync_storage --dry-run

# One-time S3 bucket versioning setup
python manage.py enable_s3_versioning
```

## Environment

- Copy `.env.template` to `.env` and fill in values. Dev works with no
  credentials (local storage only); S3 / Google Drive / OneDrive features need
  their respective credentials in `.env`.
- `DJANGO_SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `FILEFLUX_ENCRYPTION_KEY`
  control deployment behavior; `S3_ENDPOINT_URL` points boto3 at an
  S3-compatible service (e.g. MinIO in docker-compose).
- `db.sqlite3` and `storage/` are gitignored local state — user accounts are
  per-installation; register via `/register/`.

## Architecture (see README → Architecture for the diagram)

- `manager/services/` — storage backends. `BaseStorage` (local/S3 +
  `UnifiedStorage`) and `CloudStorageService` (Google Drive / OneDrive) are the
  two service contracts; both cloud providers conform to the latter so
  `CloudDriveViewSet` is provider-agnostic. `SyncService` handles local↔S3 sync.
- `manager/api_views.py` — `/api/files/` viewset (list/rename/delete/upload/
  download/move/share/sync/versions). `manager/cloud_api_views.py` — `/api/cloud/`.
- OAuth flows: `cloud_views.py` (connect, session-bound `state` nonce) →
  `oauth_views.py` (callback, validates the nonce, exchanges the code).
- OAuth tokens are stored encrypted at rest (`manager/fields.py`,
  `EncryptedTextField`) — never read/write ciphertext manually; the field is
  transparent.
- All endpoints require auth (DRF token or session).
- Tests mock S3 (`unittest.mock`) — no AWS credentials are needed to run the
  suite. Service singletons in `manager/services/__init__.py` must be reset in
  tests that override `LOCAL_STORAGE_PATH` (see `FileSearchAPITest` for the
  pattern).

## Conventions

- Commits: conventional-ish prefixes (`feat:`, `fix:`, `docs:`,
  `refactor:`), layer-split (backend vs frontend) commits on feature branches;
  fast-forward merge to `main`; push only when asked.
- Every feature ships with tests; keep `python manage.py test manager` green.
- API responses are additive — don't change existing response fields'
  meanings; add new fields instead.
- Migrations: `makemigrations manager` + commit the migration file.
- Docs: README / VERSION / CHANGELOG / CLAUDE.md at the root are current;
  `docs/` holds oauth-setup, architecture, and the condensed design history.

## Gotchas

- Django dev server on Windows: use `--noreload` when scripting around it.
- `FileResponse` keeps file handles open — close responses in tests or
  Windows teardown fails (`PermissionError: WinError 32`).
- The OAuth `state` parameter is `"<provider>:<nonce>"` and is validated
  against the session (flow diagram in `docs/architecture.md`).
