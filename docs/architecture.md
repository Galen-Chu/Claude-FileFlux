# Architecture

## Two storage contracts

```
BaseStorage (abstract)             CloudStorageService (abstract)
    ├── LocalStorage                   ├── GoogleDriveService   (Drive API v3)
    ├── S3Storage                      └── OneDriveService      (Graph API)
    └── UnifiedStorage + SyncService        └── CloudDriveViewSet (provider-agnostic)
```

Why two interfaces instead of one:

| | `BaseStorage` (local/S3) | `CloudStorageService` (Google Drive/OneDrive) |
|---|---|---|
| Identity | file **path/key** | provider **file ID** |
| Scope | application-wide | per-user (OAuth tokens) |
| Credentials | env vars, long-lived | 1-hour tokens + refresh, stored encrypted |
| Instantiation | module singletons | per request, bound to the user's token |
| Bulk ops | pattern-based bulk rename | per-file operations |

`CloudDriveViewSet` resolves the provider name to a service instance and delegates —
the view code is identical for both cloud providers.

## S3 vs cloud drives at a glance

| Aspect | AWS S3 | Google Drive / OneDrive |
|---|---|---|
| Auth | Access keys (IAM) | OAuth 2.0 |
| Token expiry | never | ~1 h, refreshable |
| Token storage | `.env` | DB, Fernet-encrypted |
| File identity | bucket + key | ID + parent |
| Compatible services | MinIO, Spaces (`S3_ENDPOINT_URL`) | — |

## OAuth flow (both providers)

1. `/cloud/connect/<provider>/` builds the provider's authorize URL with a
   session-bound `state` nonce (`"<provider>:<random>"`) and redirects.
2. The provider redirects back to `/oauth/callback/?code=...&state=...`.
3. The callback validates `state` against the session (CSRF protection), then
   exchanges the code for access/refresh tokens.
4. Tokens are stored encrypted in `CloudStorageToken`
   (`manager/fields.py` `EncryptedTextField` — encrypt-on-write,
   decrypt-on-read, plaintext never hits the DB).
5. Services call `_refresh_token_if_needed()` before each operation.

S3 credentials skip all of this: one boto3 client per process, keys from `.env`.

## Frontend

A single-page file manager (`templates/file_manager.html`, Tailwind CSS + vanilla JS):

- `loadFiles()` renders per source; infinite scroll works for all sources
  (opaque page tokens for cloud drives, page numbers for local/S3).
- All transfers use `XMLHttpRequest` for progress events; the active XHR is
  kept so Cancel buttons can `abort()`.
- Per-row actions (Preview / Download / Share / History) are built in
  `renderFileTable()` from file metadata; modals are plain hidden divs.

Design history: [history.md](./history.md). Conventions and gotchas: [../CLAUDE.md](../CLAUDE.md).
