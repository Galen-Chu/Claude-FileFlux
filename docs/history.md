# Design History

Condensed from the original implementation plans (merged; no per-version splits).
Release-by-release changes live in the root [CHANGELOG.md](../CHANGELOG.md);
current design in [architecture.md](./architecture.md).

## Initial build — unified local + S3 manager

Goal: one interface over the local filesystem and an S3 bucket with bulk operations.
Decisions that still shape the code:

- Strategy-pattern service layer: abstract `BaseStorage`, `LocalStorage` /
  `S3Storage` implementations, `UnifiedStorage` aggregation, factory singletons
  (`manager/services/__init__.py`).
- DRF REST API with audit logging (`FileOperation`) from day one.
- Path-traversal validation and size limits; Tailwind UI with modal dialogs.

## Rename replace-mode

Added find-and-replace (case options, regex, replace-all/first) alongside
prefix/suffix rename. Validation moved into `BulkRenameRequestSerializer`
(regex compiled to validate, guarding against ReDoS-ish input); each backend
implements the same transform. This established the serializer shape still used.

## Cloud drive integration

- Authentication came first because OAuth needs per-user tokens:
  registration/login, session + DRF token auth on every endpoint.
- Chose **native OAuth over rclone**: connect views, a unified callback routed
  by the `state` parameter, code-for-token exchange, refresh handling.
- Shipped initially with a *demo mode* (fake tokens) so the connection UI could
  be tested without provider credentials; later superseded by the real flow,
  then hardened with at-rest encryption and a true CSRF `state` nonce.

## Google Drive file operations + frontend

Drive API v3 service (list/upload/download/folders/rename with token refresh),
folder navigation with breadcrumbs, XHR upload/download progress, pagination
with infinite scroll. These patterns were later generalized: local/S3 adopted
the same pagination/progress/cancel UX, and `OneDriveService` mirrors the
service against Microsoft Graph.

## Later evolution

Provider-agnostic cloud API; per-user audit log and encrypted tokens;
filename search; browser streaming downloads; preview and presigned sharing;
drag-and-drop upload; cross-source move; `SyncService` (last-write-wins with
preview and timestamp convergence); S3 version history; Docker deployment
with an S3-compatible endpoint for MinIO.
