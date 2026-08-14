# Google Drive Connection: Demo vs. Real Implementation

> ⚠️ **SUPERSEDED (2026-08-13).** This document describes an earlier *demo mode* that
> stored fake tokens. That is no longer the case: real OAuth 2.0 is implemented
> (`manager/cloud_views.py` redirects to Google/Microsoft, `manager/oauth_views.py`
> exchanges the authorization code for real tokens, and `GoogleDriveService` /
> `OneDriveService` perform real file operations). The "Connect" button no longer
> creates fake tokens. The historical explanation below is retained for reference only.

---

## 🎭 Current Implementation: Demo Mode

### What Happens When You Click "Connect Google Drive"

**URL:** `/cloud/connect/googledrive/?demo=true`

```python
# Step 1: User clicks "Connect Google Drive" button
# Template sends request with demo=true parameter

# Step 2: View receives request (manager/cloud_views.py)
@login_required
def connect_googledrive(request):
    if request.GET.get('demo') == 'true':  # ← Demo flag detected
        # Step 3: Create FAKE tokens (NO GOOGLE INVOLVED)
        success = CloudDriveManager.connect_drive(
            user=request.user,
            provider='googledrive',
            access_token='demo_access_token',      # ← Hardcoded fake token
            refresh_token='demo_refresh_token',    # ← Hardcoded fake token
            expires_in=3600                        # ← 1 hour from now
        )

        # Step 4: Store fake tokens in database
        # INSERT INTO manager_cloudstoragetoken VALUES (...)
```

### What Gets Stored in Database

```sql
SELECT * FROM manager_cloudstoragetoken WHERE user_id = 1;

-- Result:
-- id | user_id | provider    | access_token          | refresh_token         | token_expires_at
-- 1  | 1       | googledrive | demo_access_token     | demo_refresh_token    | 2026-03-03 11:00:00
```

**Key Point:** This is just a database record. It's NOT connected to Google in any way!

### What You See in UI

✅ Profile page shows "Google Drive connected"
✅ Green checkmark "Active"
✅ Connection date displayed
✅ Disconnect button works

### What You CANNOT Do

❌ List files from Google Drive
❌ Upload files to Google Drive
❌ Download files from Google Drive
❌ Any actual Google Drive operations

**Why?** Because we don't have real Google tokens!

---

## 🔐 Real Google OAuth Flow (NOT Implemented Yet)

### What SHOULD Happen

```
User                    FileFlux              Google
  │                        │                    │
  │ 1. Click "Connect"     │                    │
  ├───────────────────────>│                    │
  │                        │                    │
  │                        │ 2. Generate auth URL
  │                        ├───────────────────>│
  │                        │                    │
  │ 3. Redirect to Google  │                    │
  │<───────────────────────┤                    │
  │                        │                    │
  │ 4. Login to Google     │                    │
  ├────────────────────────────────────────────>│
  │                        │                    │
  │ 5. Grant permission    │                    │
  │<────────────────────────────────────────────┤
  │                        │                    │
  │ 6. Redirect back with  │                    │
  │    authorization code  │                    │
  ├───────────────────────>│                    │
  │                        │                    │
  │                        │ 7. Exchange code   │
  │                        │    for tokens      │
  │                        ├───────────────────>│
  │                        │                    │
  │                        │ 8. Return tokens   │
  │                        │<───────────────────┤
  │                        │                    │
  │                        │ 9. Store tokens    │
  │                        │    in database     │
  │                        │                    │
  │ 10. Success message    │                    │
  │<───────────────────────┤                    │
```

### Code That SHOULD Exist (But Doesn't Yet)

```python
# Step 1: Redirect to Google OAuth
@login_required
def connect_googledrive(request):
    # Build Google OAuth URL
    params = {
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': 'http://localhost:8000/oauth/callback/',
        'response_type': 'code',
        'scope': 'https://www.googleapis.com/auth/drive.file',
        'access_type': 'offline',
        'prompt': 'consent',
        'state': 'googledrive'  # Identify provider in callback
    }

    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    # Redirect user to Google login
    return redirect(auth_url)


# Step 2: Handle OAuth callback (DOESN'T EXIST YET!)
def oauth_callback(request):
    code = request.GET.get('code')
    state = request.GET.get('state')  # 'googledrive'

    # Exchange authorization code for tokens
    response = requests.post('https://oauth2.googleapis.com/token', data={
        'code': code,
        'client_id': settings.GOOGLE_CLIENT_ID,
        'client_secret': settings.GOOGLE_CLIENT_SECRET,
        'redirect_uri': 'http://localhost:8000/oauth/callback/',
        'grant_type': 'authorization_code'
    })

    tokens = response.json()

    # REAL tokens from Google!
    access_token = tokens['access_token']      # ← Real token from Google
    refresh_token = tokens['refresh_token']    # ← Real refresh token
    expires_in = tokens['expires_in']          # ← Usually 3600 seconds

    # Store real tokens in database
    CloudStorageToken.objects.update_or_create(
        user=request.user,
        provider='googledrive',
        defaults={
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_expires_at': timezone.now() + timedelta(seconds=expires_in)
        }
    )

    return redirect('manager:profile')
```

### What Would Real Tokens Look Like

```sql
SELECT * FROM manager_cloudstoragetoken WHERE provider='googledrive';

-- Result with REAL OAuth:
-- id | user_id | provider    | access_token                              | refresh_token                           | token_expires_at
-- 1  | 1       | googledrive | ya29.a0AfH6SMBwN7hY9-... (700+ chars)    | 1//0g5vtd3... (100+ chars)             | 2026-03-03 11:00:00
```

**Key Difference:**
- Demo: `demo_access_token` (20 chars)
- Real: `ya29.a0AfH6SMBwN7hY9-...` (700+ chars, cryptographically secure)

---

## 🆚 Side-by-Side Comparison

| Aspect | Demo Mode (Current) | Real OAuth (Needed) |
|--------|---------------------|---------------------|
| **User Flow** | Click button → Done | Redirect to Google → Login → Consent → Redirect back |
| **Google Login** | ❌ No | ✅ Yes |
| **Consent Screen** | ❌ No | ✅ Yes ("FileFlux wants to access your Google Drive") |
| **Authorization Code** | ❌ No | ✅ Yes |
| **Access Token** | `demo_access_token` | `ya29.a0AfH6SMBwN7hY9-...` (700 chars) |
| **Refresh Token** | `demo_refresh_token` | `1//0g5vtd3...` (100 chars) |
| **Token Source** | Hardcoded string | Google OAuth server |
| **Can List Files** | ❌ No | ✅ Yes |
| **Can Upload Files** | ❌ No | ✅ Yes |
| **Setup Required** | None | Google Cloud project, OAuth credentials |

---

## 🔍 Why We Use Demo Mode

### Advantages of Demo Mode

1. ✅ **No setup required**
   - No Google Cloud project
   - No OAuth credentials
   - No consent screen configuration

2. ✅ **Test UI/UX**
   - Test connection flow
   - Test disconnect functionality
   - Test token display

3. ✅ **Development speed**
   - Instant testing
   - No external dependencies
   - Works offline

### Disadvantages of Demo Mode

1. ❌ **No actual Google Drive access**
   - Can't list files
   - Can't upload/download
   - Just UI simulation

2. ❌ **Fake tokens**
   - Would fail if used with Google API
   - No refresh capability
   - No real permissions

---

## 🚀 How to Switch to Real OAuth

### Step 1: Create Google Cloud Project

```bash
1. Go to https://console.cloud.google.com/
2. Create new project: "FileFlux"
3. Enable Google Drive API
4. Create OAuth 2.0 credentials
5. Copy client_id and client_secret
```

### Step 2: Update .env

```bash
GOOGLE_CLIENT_ID=123456789.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-abc123...
OAUTH_REDIRECT_URI=http://localhost:8000/oauth/callback/
```

### Step 3: Implement Callback Handler

Create `manager/oauth_views.py`:

```python
def google_oauth_callback(request):
    code = request.GET.get('code')

    # Exchange code for real tokens
    tokens = exchange_code_for_tokens(code)

    # Store real tokens
    save_tokens_to_database(
        user=request.user,
        access_token=tokens['access_token'],
        refresh_token=tokens['refresh_token'],
        expires_in=tokens['expires_in']
    )

    return redirect('manager:profile')
```

### Step 4: Update connect_googledrive View

```python
@login_required
def connect_googledrive(request):
    # Remove demo mode check
    # if request.GET.get('demo') == 'true':  # ← REMOVE THIS

    # Always use real OAuth
    auth_url = build_google_oauth_url()
    return redirect(auth_url)  # ← Redirect to Google login
```

---

## 📊 Current Architecture

```
┌─────────────────────────────────────────┐
│  User Profile Page                      │
│                                         │
│  [Connect Google Drive?demo=true]       │
│                 │                       │
└─────────────────┼───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  manager/cloud_views.py                 │
│                                         │
│  def connect_googledrive():             │
│    if demo=true:                        │
│      create_fake_tokens()  ◄── YOU ARE HERE
│    else:                                │
│      redirect_to_google()  ◄── NOT IMPLEMENTED
│                                         │
└─────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│  Database                               │
│                                         │
│  access_token: "demo_access_token"      │
│  (Fake, not from Google)                │
└─────────────────────────────────────────┘
```

---

## 🎯 What We Have vs. What We Need

### ✅ What We HAVE

1. **Database Model**
   ```python
   class CloudStorageToken(models.Model):
       user = ForeignKey(User)
       provider = CharField()
       access_token = TextField()
       refresh_token = TextField()
       token_expires_at = DateTimeField()
   ```

2. **UI Components**
   - Connect button
   - Connection status display
   - Disconnect button
   - Profile page integration

3. **Demo Mode**
   - Simulates connection
   - Stores fake tokens
   - Shows UI flow

### ❌ What We NEED (For Real OAuth)

1. **Google Cloud Project**
   - OAuth 2.0 credentials
   - Drive API enabled
   - Consent screen configured

2. **OAuth Implementation**
   - Redirect to Google login
   - Callback handler
   - Code exchange logic
   - Token refresh logic

3. **Google Drive API Integration**
   - File listing
   - File upload/download
   - Error handling
   - Rate limiting

---

## 🎓 Summary

**Current State:**
- ✅ UI is ready
- ✅ Database is ready
- ✅ Demo mode works
- ❌ No real Google OAuth
- ❌ No actual Google Drive access

**What "Connect Google Drive" Does:**
- Creates a database record with fake tokens
- Shows "Connected" in UI
- Does NOT connect to Google
- Does NOT provide Google Drive access

**It's a UI/UX prototype** that demonstrates the connection flow without requiring:
- Google Cloud project setup
- OAuth credential configuration
- Consent screen approval

**For Production:**
- Need to implement full OAuth flow
- Need Google Cloud credentials
- Need callback handler
- Then it will connect to real Google Drive

---

**Document Version:** 1.0
**Date:** 2026-03-03
**Purpose:** Explain demo mode vs. real OAuth implementation
