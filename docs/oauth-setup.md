# Cloud Drive OAuth Setup

How to obtain the OAuth credentials that let FileFlux users connect Google Drive and
OneDrive. The redirect URI for both providers is `http://localhost:8000/oauth/callback/`
(set via `OAUTH_REDIRECT_URI`) and must match **exactly**, including the trailing slash.

## Google Drive (Google Cloud Console, ~15 min)

1. Create a project at <https://console.cloud.google.com/> (e.g. `FileFlux`).
2. **APIs & Services → Library** → enable the **Google Drive API**.
3. **APIs & Services → OAuth consent screen** (user type *External*):
   - App name `FileFlux`; add your Google address as a **test user**.
   - Scope: `https://www.googleapis.com/auth/drive.file`.
4. **APIs & Services → Credentials → Create credentials → OAuth client ID**
   (Web application) with authorized redirect URI
   `http://localhost:8000/oauth/callback/`.
5. Put the Client ID / Client Secret into `.env`:

   ```env
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   ```

While the project is in testing mode Google warns "app isn't verified" — choose
*Advanced → continue*; only accounts added as test users can consent.

## OneDrive (Azure Portal — Microsoft Graph, ~20 min)

1. **App registrations → New registration** at <https://portal.azure.com/>:
   - Name `FileFlux`
   - Account type: *accounts in any organizational directory and personal Microsoft accounts*
   - Redirect URI (Web): `http://localhost:8000/oauth/callback/`
2. From the app overview, copy the **Application (client) ID** and **Directory (tenant) ID**.
3. **Certificates & secrets → New client secret** — copy the secret **Value**
   (it is shown only once).
4. **API permissions → Microsoft Graph → Delegated**: add `Files.ReadWrite.All` and
   `offline_access` (required for refresh tokens).
5. Fill `.env`:

   ```env
   MS_CLIENT_ID=...
   MS_CLIENT_SECRET=...
   MS_TENANT_ID=common        # or your Directory (tenant) ID
   ```

## Verify

Restart the server, open `/profile/`, and click Connect — you should be redirected to
the provider's consent screen and back, with the drive shown as connected. Tokens are
stored encrypted (`CloudStorageToken`); Disconnect removes them.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `redirect_uri_mismatch` | URI must match exactly, including the trailing slash |
| "App isn't verified" (Google) | Advanced → continue; add yourself as a test user |
| "Need admin approval" (Microsoft) | Use a personal account, or have the tenant admin consent |
| Client secret lost | Create a new one — values are displayed only once |
