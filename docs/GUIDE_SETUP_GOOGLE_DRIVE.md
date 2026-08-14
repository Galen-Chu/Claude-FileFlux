# Google Drive Setup Guide for FileFlux

## 📋 What You'll Do (Step-by-Step)

### Overview
You'll create a Google Cloud Project and get two text strings (Client ID and Client Secret).
**Time:** 15-20 minutes
**Requirements:** Gmail account

---

## 🎯 Step-by-Step Instructions

### Step 1: Create Google Cloud Project (5 minutes)

1. **Open browser:** Go to https://console.cloud.google.com/

2. **Login:** Use your Gmail account

3. **Create project:**
   - Click "Select a project" dropdown (top left)
   - Click "New Project"
   - **Project name:** Enter `FileFlux`
   - Click "Create"
   - Wait ~30 seconds
   - Select your "FileFlux" project from dropdown

---

### Step 2: Configure OAuth Consent Screen (5 minutes)

1. **Navigate:**
   - Left sidebar → "APIs & Services"
   - Click "OAuth consent screen"

2. **Choose user type:**
   - Select "External" (allows personal Gmail)
   - Click "Create"

3. **Fill in OAuth consent screen form:**

   **App information:**
   - **App name:** `FileFlux`
   - **User support email:** Select your email from dropdown
   - **App logo:** (Leave blank - skip for now)

   **App domain:** (Leave all blank)
   - Application home page
   - Application privacy policy link
   - Application terms of service link

   **Developer contact information:**
   - **Email addresses:** Enter your email

   Click "Save and Continue"

4. **Scopes page:**
   - Click "Add or remove scopes"
   - In search box, type: `drive`
   - **Check this box:** `https://www.googleapis.com/auth/drive.file`
     (View and manage Google Drive files that you have created or opened)
   - Click "Update"
   - Click "Save and Continue"

5. **Test users page:**
   - Click "+ Add users"
   - **Enter your Gmail address** (the one you're testing with)
   - Click "Add"
   - Click "Save and Continue"

6. **Summary page:**
   - Review your settings
   - Click "Back to Dashboard"

---

### Step 3: Create OAuth Credentials (3 minutes)

1. **Navigate:**
   - Left sidebar → "APIs & Services"
   - Click "Credentials"

2. **Create OAuth client:**
   - Click "+ Create credentials" (top of page)
   - Select "OAuth client ID"

3. **Configure OAuth client:**
   - **Application type:** Select "Web application"
   - **Name:** Enter `FileFlux Web Client`

4. **Authorized redirect URIs** (IMPORTANT!):
   - Click "Add URI"
   - Enter exactly: `http://localhost:8000/oauth/callback/`
   - ⚠️ **Must match exactly** including the trailing slash!

5. **Create:**
   - Click "Create"

6. **Copy your credentials:**

   A popup will show:

   ```
   Your Client ID: 123456789-abcdefghijklmnop.apps.googleusercontent.com
   Your Client Secret: GOCSPX-abcdefghijklmnopqrstuv
   ```

   📸 **COPY BOTH OF THESE** - You'll need them!

   Click "OK"

---

### Step 4: Enable Google Drive API (1 minute)

1. **Navigate:**
   - Left sidebar → "APIs & Services"
   - Click "Library"

2. **Enable API:**
   - In search box, type: `Google Drive API`
   - Click on "Google Drive API" in results
   - Click "Enable" button
   - Wait for it to enable (few seconds)

---

## ✅ Setup Complete!

### What You Should Have Now:

- **Client ID:** `123456789-abc...apps.googleusercontent.com`
- **Client Secret:** `GOCSPX-xyz...`

### What to Do Next:

1. **Copy your Client ID and Client Secret**
2. **Paste them in our chat** like this:

```
My Google Drive credentials:
Client ID: 123456789-abcdefghijklmnop.apps.googleusercontent.com
Client Secret: GOCSPX-abcdefghijklmnopqrstuv
```

3. **I'll update the code** with your credentials and implement real OAuth!

---

## 🎉 What Happens After

When I implement the code with your credentials:

1. Click "Connect Google Drive" in your profile
2. Opens Google login page (real!)
3. Login with YOUR Google account
4. Shows consent screen: "FileFlux wants to access your Google Drive"
5. Click "Allow"
6. Redirects back to FileFlux
7. **Connected to YOUR real Google Drive!**

Now you can:
- ✅ List YOUR files from YOUR Google Drive
- ✅ Upload files to YOUR Google Drive
- ✅ Download files from YOUR Google Drive

---

## 🔒 Security Notes

- **Client ID** is public (okay to share)
- **Client Secret** should be kept private (but for development, it's okay)
- **Tokens** are stored in your local database only
- **Google Drive access** is read/write for files created by FileFlux only
- **You can revoke** access anytime in your Google account settings

---

## ❓ Troubleshooting

### "This app isn't verified"
- This is normal for development apps
- Click "Advanced" → "Go to FileFlux (unsafe)"
- This only appears because the app is in testing mode

### "Access blocked"
- Make sure you added your email as a test user
- Check that Google Drive API is enabled
- Verify redirect URI matches exactly

### Can't see credentials
- Go to "APIs & Services" → "Credentials"
- Look for "OAuth 2.0 Client IDs"
- Click the pencil icon to view Client ID
- Client Secret can be viewed once during creation only

---

## 📸 What the Console Looks Like

### Credentials Page:
```
┌─────────────────────────────────────────┐
│ Credentials                             │
├─────────────────────────────────────────┤
│ + Create credentials  ▼                 │
│                                         │
│ OAuth 2.0 Client IDs                    │
│ ┌─────────────────────────────────────┐│
│ │ FileFlux Web Client                 ││
│ │ Client ID: 123456789-abc...         ││
│ │ [View] ✏️ 🗑️                       ││
│ └─────────────────────────────────────┘│
└─────────────────────────────────────────┘
```

---

## 🚀 Ready to Start?

1. **Open:** https://console.cloud.google.com/
2. **Follow the steps above**
3. **Copy your Client ID and Client Secret**
4. **Paste them here**

I'll handle all the code implementation! 🎉

---

**Document Version:** 1.0
**Last Updated:** 2026-03-03
**Time Required:** 15-20 minutes
