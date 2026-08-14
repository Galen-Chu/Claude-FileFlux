# FileFlux — Unified Cloud File Manager · 統一雲端檔案管理器

[![Version](https://img.shields.io/badge/version-2.3.0-blue.svg)](./VERSION.md)
[![Django](https://img.shields.io/badge/Django-6.0.2-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.14+-brightgreen.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-43%20passing-brightgreen.svg)](#development)

A Django + DRF application giving one authenticated interface for files across
**local storage, AWS S3 (or MinIO), Google Drive, and OneDrive** — web UI + REST API,
per-user audit logging, OAuth tokens encrypted at rest, containerized deployment.

以 Django + DRF 打造的單一登入檔案管理介面，整合**本機儲存、AWS S3（或 MinIO）、Google Drive 與 OneDrive**——提供網頁 UI 與 REST API、逐使用者稽核日誌、OAuth Token 靜態加密，並支援容器化部署。

> **Status | 狀態：** v2.3.0 — all planned roadmap features implemented. Production still
> needs HTTPS and managed secrets (see [Security](#security)).
>
> v2.3.0 —— 規劃中的 Roadmap 功能已全部完成。正式環境仍需 HTTPS 與受管理的金鑰（見[安全性](#security)）。

<a id="features"></a>
## ✨ Features · 功能特色

- **Four backends, two contracts** 四種後端、兩種契約 — local/S3 (`BaseStorage`) and
  Google Drive/OneDrive (`CloudStorageService`), so cloud providers are interchangeable
  · 本機/S3 走 `BaseStorage`，Google Drive/OneDrive 走 `CloudStorageService`，雲端供應商可互換
- **Bulk rename** 批次重新命名 — prefix / suffix / find-and-replace, regex, sequential
  numbering · 支援前綴／後綴／尋找取代、正規表示式與流水號
- **Pagination + infinite scroll** 分頁與無限捲動 — on all sources; filename search on
  local/S3 · 全部來源皆支援；本機/S3 支援檔名搜尋
- **Transfers** 傳輸 — browser streaming download with progress, cancellable
  uploads/downloads · 瀏覽器串流下載附進度條，上傳／下載皆可取消
- **Preview & sharing** 預覽與分享 — preview images/PDFs; share S3 objects via
  time-limited presigned URLs · 圖片/PDF 即時預覽；S3 物件可產生限時分享連結
- **Drag-and-drop upload** 拖放上傳 — to S3 / Google Drive; **cross-source move**
  (local ↔ S3) · 上傳至 S3／Google Drive；支援跨來源搬移（本機 ↔ S3）
- **Bi-directional sync** 雙向同步 — preview-first, last-write-wins, timestamp
  convergence; `manage.py sync_storage` for cron · 先預覽再執行、新者為準、時間戳自動收斂；可搭配 cron 排程
- **S3 version history** S3 版本歷史 — list/download/restore old versions ·
  列出／下載／還原舊版本（`manage.py enable_s3_versioning` 一次性開啟）
- **Auth & security** 認證與安全 — session + token auth everywhere, tokens encrypted
  at rest (Fernet), OAuth `state` CSRF nonce, rate limiting, path-traversal validation
  · 全端點皆需認證、Token 靜態加密、OAuth state 防 CSRF、速率限制、路徑防護
- 43 automated tests 自動化測試；Docker deployment with optional MinIO backend
  附可選 MinIO 後端的容器化部署

<a id="quick-start"></a>
## 🚀 Quick Start · 快速開始

```bash
python -m venv venv && venv\Scripts\activate   # Windows (source venv/bin/activate on unix)
pip install -r requirements.txt
cp .env.template .env                          # fill in what you need (see file for all vars)
python manage.py migrate && python manage.py createsuperuser
python manage.py runserver                     # http://127.0.0.1:8000/
```

**Docker:** `cp .env.template .env` (set a strong `DJANGO_SECRET_KEY`) then
`docker compose up --build` — gunicorn + whitenoise, auto-migrations, SQLite and
storage on named volumes.

**Docker：** 先 `cp .env.template .env`（設定強隨機的 `DJANGO_SECRET_KEY`），再 `docker compose up --build`——內建 gunicorn + whitenoise、自動遷移，SQLite 與儲存空間掛在 named volume 上。

To use a local S3-compatible backend, uncomment the `minio` service in
`docker-compose.yml` and set `S3_ENDPOINT_URL=http://minio:9000`.

如要使用本機 S3 相容後端，把 `docker-compose.yml` 裡的 `minio` 服務取消註解，並設定 `S3_ENDPOINT_URL=http://minio:9000`。

Key env vars (full list in [.env.template](./.env.template)): `DJANGO_SECRET_KEY`,
`DEBUG`, `ALLOWED_HOSTS`, `FILEFLUX_ENCRYPTION_KEY`, `S3_ENDPOINT_URL`,
`AWS_*`/`BUCKET_NAME`, `GOOGLE_*` / `MS_*` (OAuth — see
[docs/oauth-setup.md](./docs/oauth-setup.md)).

重要環境變數（完整清單見 [.env.template](./.env.template)）：`DJANGO_SECRET_KEY`、`DEBUG`、`ALLOWED_HOSTS`、`FILEFLUX_ENCRYPTION_KEY`、`S3_ENDPOINT_URL`、`AWS_*`/`BUCKET_NAME`、`GOOGLE_*`／`MS_*`（OAuth 申請教學見 [docs/oauth-setup.md](./docs/oauth-setup.md)）。

<a id="usage"></a>
## 📖 Usage · 使用方式

**Web UI | 網頁介面：** register at `/register/`; manage files at `/manager/` (tabs per
source, bulk select, rename/delete/move, upload/download with progress, preview,
share, sync, drag-and-drop); connect cloud drives on `/profile/`.
於 `/register/` 註冊帳號；在 `/manager/` 管理檔案（依來源分頁、批次選取、重新命名／刪除／搬移、上傳下載附進度、預覽、分享、同步、拖放上傳）；於 `/profile/` 連接雲端硬碟。

**API** — all endpoints require auth (`Authorization: Token <token>`, or session).
所有端點皆需認證（`Authorization: Token <token>` 或 session）。

```bash
# List local files with search + pagination · 列出本機檔案（搜尋 + 分頁）
curl -H "Authorization: Token $T" "localhost:8000/api/files/?source=local&search=invoice&page=1"
# Bulk rename (find-and-replace + numbering) · 批次重新命名（取代 + 流水號）
curl -X POST -H "Authorization: Token $T" -H "Content-Type: application/json" \
  -d '{"files":["a.txt","b.txt"],"text":"final","mode":"suffix","add_sequence":true,"source":"local"}' \
  localhost:8000/api/files/rename/
# Preview a sync plan, then run it · 預覽同步計畫後執行
curl -H "Authorization: Token $T" localhost:8000/api/files/sync-preview/
```

### API Reference · API 參考 — Local / S3 (`/api/files/`)
| Endpoint | Method | Description · 說明 |
|----------|--------|-------------|
| `/api/files/` | GET | List files · 列出檔案（`source`, `path`, `search`, `page`, `page_size`） |
| `/api/files/rename/` | POST | Bulk rename · 批次重新命名（prefix/suffix/replace + 流水號） |
| `/api/files/delete/` | POST | Bulk delete · 批次刪除 |
| `/api/files/upload/` | POST | Upload to S3 · 上傳至 S3 |
| `/api/files/download/` | POST | Copy S3 → server local storage · S3 複製到伺服器本機 |
| `/api/files/download-file/` | GET | Stream to browser · 串流至瀏覽器（`inline=1` 預覽、`version_id` 指定版本） |
| `/api/files/move/` | POST | Move local ↔ S3 · 跨來源搬移（`files`, `source`, `dest_source`, `dest_path?`） |
| `/api/files/share/` | POST | Presigned S3 URL · 限時分享連結（`path`, `expires_in?`） |
| `/api/files/versions/` | GET | S3 version list · 版本列表（`path`） |
| `/api/files/versions/restore/` | POST | Restore old version · 還原舊版（`path`, `version_id`） |
| `/api/files/sync-preview/` | GET | Sync plan (dry run) · 同步計畫預覽 |
| `/api/files/sync-run/` | POST | Execute sync · 執行同步 |
| `/api/files/logs/` | GET | Per-user audit logs · 逐使用者稽核日誌 |

### API Reference · API 參考 — Cloud drives 雲端硬碟 (`/api/cloud/`, `provider=googledrive\|onedrive`)
| Endpoint | Method | Description · 說明 |
|----------|--------|-------------|
| `/api/cloud/files/` | GET | List files · 列出檔案（`folder_id`, `page_token`, `query`） |
| `/api/cloud/files/{id}/` | GET | File metadata · 檔案 metadata |
| `/api/cloud/upload/` | POST | Upload · 上傳（`file`, `parent_folder_id?`） |
| `/api/cloud/download/` | POST | Download to browser · 下載至瀏覽器（`file_id`） |
| `/api/cloud/create-folder/` | POST | Create folder · 建立資料夾（`name`） |
| `/api/cloud/files/{id}/` | DELETE | Delete · 刪除 |
| `/api/cloud/files/{id}/rename/` | PATCH | Rename · 重新命名（`new_name`） |

<a id="architecture"></a>
## 🏗️ Architecture · 架構

```
BaseStorage (abstract)             CloudStorageService (abstract)
    ├── LocalStorage                   ├── GoogleDriveService   (Drive API v3)
    ├── S3Storage                      └── OneDriveService      (Graph API)
    └── UnifiedStorage + SyncService        └── CloudDriveViewSet (provider-agnostic)
```

`manager/services/` holds the backends; `manager/api_views.py` /
`cloud_api_views.py` are thin DRF layers with per-user audit logging; OAuth
connect/callback flows live in `cloud_views.py` / `oauth_views.py`.

`manager/services/` 放儲存後端；`manager/api_views.py`／`cloud_api_views.py` 是薄薄的 DRF 層並附逐使用者稽核；OAuth 連接／回呼流程在 `cloud_views.py`／`oauth_views.py`。

Details: [docs/architecture.md](./docs/architecture.md), conventions: [CLAUDE.md](./CLAUDE.md).
詳細設計見 [docs/architecture.md](./docs/architecture.md)，開發慣例見 [CLAUDE.md](./CLAUDE.md)。

<a id="security"></a>
## 🔒 Security · 安全性

Implemented · 已實作： auth on all endpoints 全端點認證、OAuth tokens encrypted at
rest (Fernet) Token 靜態加密、`state` CSRF nonce on callbacks 回呼 state 驗證、
rate limiting 速率限制、path-traversal validation 路徑防護、file-size limits
檔案大小限制、password validators 密碼強度驗證。

Still required for production · 正式環境仍需： HTTPS + secure cookies、a reverse proxy
in front of the container 容器前方的反向代理（image 內已是 gunicorn + whitenoise）、
strong `DJANGO_SECRET_KEY` / `FILEFLUX_ENCRYPTION_KEY` from a secrets manager 由金鑰管理服務供應的強金鑰、
`DEBUG=False` + correct `ALLOWED_HOSTS`、rotating the committed dev secret key
更換 repo 內建的開發用金鑰。

<a id="development"></a>
## 🛠️ Development · 開發

```bash
python manage.py test manager     # 43 tests · 項測試
```

Full guide (commands, conventions, gotchas) · 完整開發指南（指令、慣例、注意事項）：
[CLAUDE.md](./CLAUDE.md)。

**Dependencies · 依賴：** Django 6.0.2 · DRF 3.16.1 · boto3 · python-dotenv · requests ·
requests-toolbelt · cryptography · gunicorn + whitenoise (Docker)。SQLite in development 開發環境使用 SQLite。

<a id="roadmap"></a>
## 🗺️ Roadmap · 路線圖

All planned features are done · 規劃功能已全部完成。Future ideas (unscheduled) ·
未排程的未來想法： true S3 continuation-token pagination 真 S3 接續 token 分頁、
background sync scheduler 背景同步排程器、Google Drive sync/sharing parity
Google Drive 同步／分享對等、local file versioning 本機版本控。
History · 歷史： [CHANGELOG](./CHANGELOG.md) · [docs/history.md](./docs/history.md)。

## 📄 License · 授權
For educational and development purposes · 供教育與開發用途。

---
**Version:** 2.3.0 · **Updated:** 2026-08-14
