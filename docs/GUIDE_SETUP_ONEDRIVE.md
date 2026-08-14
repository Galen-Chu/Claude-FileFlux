# OneDrive OAuth Setup Guide for FileFlux

> **Quick Navigation:** [Before You Start](#before-you-start) | [Quick Reference](#quick-reference) | [Step-by-Step](#step-by-step-instructions) | [Troubleshooting](#troubleshooting)

---

## 📊 Overview

| Aspect | Details |
|--------|---------|
| **What you'll do** | Register Azure AD app, get credentials |
| **Time required** | 20-30 minutes |
| **Difficulty** | ⭐⭐⭐ (Medium) |
| **Account needed** | Microsoft account (personal or work) |
| **What you'll get** | 3 text strings to paste |

---

## ✅ Before You Start

### Prerequisites Checklist

- [ ] **Microsoft Account** - Any of these work:
  - Personal: @outlook.com, @hotmail.com, @live.com, @msn.com
  - Work/School: @yourcompany.com (Microsoft 365)
- [ ] **Web Browser** - Chrome, Firefox, Edge, or Safari
- [ ] **20-30 minutes** of uninterrupted time
- [ ] **Text editor** open to copy credentials (Notepad, Notes, etc.)

### What You'll Get

At the end, you'll have **3 text strings**:

```
Application ID:  12345678-1234-1234-1234-123456789abc
Client Secret:   abc123XYZ~def456.GHI789_jkl-1234567890ab
Tenant ID:       87654321-4321-4321-4321-cba987654321
```

---

## 🎯 Quick Reference Card

Print this section or keep it handy during setup:

```
┌─────────────────────────────────────────────┐
│        ONEDRIVE SETUP QUICK REFERENCE        │
├───────────────────────────���─────────────────┤
│                                             │
│ 1. Azure Portal: portal.azure.com          │
│                                             │
│ 2. App Name: FileFlux                       │
│                                             │
│ 3. Redirect URI:                            │
│    http://localhost:8000/oauth/callback/   │
│    ⚠️ INCLUDE trailing slash!              │
│                                             │
│ 4. Account Type:                            │
│    ✓ Multitenant + personal accounts        │
│                                             │
│ 5. Required Permissions:                    │
│    ✓ Files.Read.All                         │
│    ✓ Files.ReadWrite.All                   │
│    ✓ offline_access ⭐ CRITICAL!           │
│                                             │
│ 6. Copy These 3 Things:                    │
│    □ Application (client) ID               │
│    □ Client Secret VALUE (not ID!)         │
│    □ Directory (tenant) ID                 │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 🎯 Step-by-Step Instructions

### Step 1: Access Azure Portal (2 minutes)

1. **Open browser:** Go to https://portal.azure.com/

2. **Login:** Use your Microsoft account
   - Personal: @outlook.com, @hotmail.com, @live.com
   - Work: @yourcompany.com (Microsoft 365)

3. **Search for Azure Active Directory:**
   - In top search bar, type: `Azure Active Directory`
   - Click on "Azure Active Directory" from results

---

---

## 🛠️ What You'll Need

✅ **Microsoft account** (Outlook, Hotmail, Live, or Microsoft 365)
✅ **Web browser** (Chrome, Edge, Firefox)
✅ **20-30 minutes** of time

---

## 📋 Step-by-Step Instructions

### Step 1: Access Azure Portal (2 minutes)

**👉 Action:** Open https://portal.azure.com/

**Login** with your Microsoft account

1. **Navigate to App registrations:**
   - In left sidebar, click "App registrations"

2. **Create new registration:**
   - Click "+ New registration" button (top of page)

3. **Fill in registration form:**

   **Name:**
   - Enter: `FileFlux`

   **Supported account types:** Choose ONE:
   - ☑️ **Recommended:** "Accounts in any organizational directory and personal Microsoft accounts"
     - (This allows personal Microsoft accounts like @outlook.com)

   **Redirect URI (web):**
   - Platform: Select "Web"
   - Enter: `http://localhost:8000/oauth/callback/`
   - ⚠️ **Must match exactly** including trailing slash!

4. **Click "Register"**
   - Wait a few seconds for creation

---

### Step 3: Get Application ID (1 minute)

After registration, you'll see the app overview page:

1. **Copy Application (client) ID:**
   - Look for "Application (client) ID"
   - It looks like: `12345678-1234-1234-1234-123456789abc`
   - Click the copy icon 📋
   - **Save this!** You'll need it.

2. **Copy Directory (tenant) ID:**
   - Look for "Directory (tenant) ID"
   - It looks like: `87654321-4321-4321-4321-cba987654321`
   - Click the copy icon 📋
   - **Save this too!**

---

### Step 4: Create Client Secret (3 minutes)

1. **Navigate to Certificates & secrets:**
   - In left sidebar (under "Manage"), click "Certificates & secrets"

2. **Create new secret:**
   - Click "+ New client secret" button

3. **Fill in secret form:**
   - **Description:** Enter `FileFlux Secret`
   - **Expires:** Select "180 days (6 months)" or "365 days (1 year)"
   - Click "Add"

4. **Copy the secret value:**
   - **IMPORTANT:** You'll see two things:
     - **Secret ID:** (Don't need this)
     - **Value:** `abc123XYZ~def456.GHI789_jkl` ← **COPY THIS!**

   📸 **Copy the "Value" field** - You won't see it again!

---

### Step 5: Configure API Permissions (5 minutes)

1. **Navigate to API permissions:**
   - In left sidebar (under "Manage"), click "API permissions"

2. **Add Microsoft Graph permissions:**
   - Click "+ Add a permission"
   - Select "Microsoft Graph"

3. **Choose delegated permissions:**
   - Click "Delegated permissions" (NOT Application permissions)

4. **Search and select permissions:**
   - In search box, type: `Files`
   - Expand "Files" section
   - **Check these permissions:**
     - ☑️ `Files.Read`
     - ☑️ `Files.Read.All`
     - ☑️ `Files.ReadWrite`
     - ☑️ `Files.ReadWrite.All`
     - ☑️ `offline_access` (IMPORTANT - for refresh tokens!)

   - Click "Add permissions"

5. **Grant admin consent (if available):**
   - If you see "Grant admin consent for [your org]" button, click it
   - If not available (personal account), that's okay - skip this step

---

### Step 6: Configure Authentication (3 minutes)

1. **Navigate to Authentication:**
   - In left sidebar (under "Manage"), click "Authentication"

2. **Verify redirect URI:**
   - You should see: `http://localhost:8000/oauth/callback/`
   - If not, click "+ Add a platform" → "Web" → Add the URI

3. **Configure settings:**
   - **Allowed client flows:** Check "Authorization code flow" (should be auto-checked)
   - **Logout URL:** (Leave blank)

4. **Save:**
   - Click "Save" at top

---

---

## 📋 Quick Reference

### ⏱️ Time Required
**20-30 minutes**

### 📦 What You'll Get
**3 pieces of information:**
1. Application (client) ID
2. Client Secret (Value field)
3. Directory (tenant) ID

### ✅ Before You Start
- Microsoft account (Outlook, Hotmail, Live, Microsoft 365)
- Web browser
- 20-30 minutes

---

## 🚀 Step-by-Step Instructions

### Step 1: Access Azure Portal (2 minutes)

### What You Should Have Now:

You need **3 pieces of information:**

1. **Application (client) ID:** `12345678-1234-1234-1234-123456789abc`
2. **Client Secret Value:** `abc123XYZ~def456.GHI789_jkl`
3. **Directory (tenant) ID:** `87654321-4321-4321-4321-cba987654321`

---

---

## 📤 What to Provide Me

After completing the Azure Portal setup, provide these **3 pieces of information:**

### **Option 1: Paste in Chat**
Simply copy and paste in our chat:

```
My OneDrive credentials:

Application ID: [paste your Application ID here]
Client Secret: [paste your Client Secret Value here]
Tenant ID: [paste your Directory tenant ID here]
```

### **Option 2: Type Manually**
Or type them manually in a message to me.

**Example:**
```
My OneDrive credentials:

Application ID: 12345678-1234-1234-1234-123456789abc
Client Secret: abc123XYZ~def456.GHI789_jkl-1234567890ab
Tenant ID: 87654321-4321-4321-4321-cba987654321
```

---

## ✅ Verification Checklist

Before providing credentials, verify:

- [ ] Created app registration named "FileFlux"
- [ ] Copied Application (client) ID
- [ ] Copied Directory (tenant) ID
- [ ] Created client secret
- [ ] Copied secret **Value** (not Secret ID!)
- [ ] Added redirect URI: `http://localhost:8000/oauth/callback/`
- [ ] Added API permissions (Files.ReadWrite.All, offline_access)

---

## 🎉 What Happens Next

**After you provide the credentials:**

1. I'll update `.env` file with your credentials
2. I'll create OAuth callback handler code
3. I'll implement token exchange logic
4. I'll update connection flow to use real OAuth
5. I'll test with your real OneDrive!

**Result:** Real connection to YOUR OneDrive with actual file operations!

Copy and paste this information in our chat:

```
My OneDrive credentials:

Application ID: [paste your Application ID here]
Client Secret: [paste your Client Secret Value here]
Tenant ID: [paste your Directory tenant ID here]
```

**Example:**
```
My OneDrive credentials:

Application ID: 12345678-1234-1234-1234-123456789abc
Client Secret: abc123XYZ~def456.GHI789_jkl-1234567890ab
Tenant ID: 87654321-4321-4321-4321-cba987654321
```

---

## 🎉 What Happens After

When I implement the code with your credentials:

1. Click "Connect OneDrive" in your profile
2. Opens Microsoft login page (real!)
3. Login with YOUR Microsoft account
4. Shows consent screen: "FileFlux wants to access your files"
5. Click "Accept"
6. Redirects back to FileFlux
7. **Connected to YOUR real OneDrive!**

Now you can:
- ✅ List YOUR files from YOUR OneDrive
- ✅ Upload files to YOUR OneDrive
- ✅ Download files from YOUR OneDrive

---

## 🔒 Security Notes

- **Application ID** is public (okay to share)
- **Client Secret** should be kept private (but for development, it's okay to share with me)
- **Tenant ID** identifies your directory (okay to share)
- **Tokens** are stored in your local database only
- **OneDrive access** is read/write for files only
- **You can revoke** access anytime in your Microsoft account settings

---

## ❓ Troubleshooting

### "Need admin approval"
- This appears for work/school accounts if admin hasn't approved
- **Solution:** Use a personal Microsoft account (@outlook.com, @hotmail.com)

### "Redirect URI mismatch"
- Verify redirect URI in Azure Portal matches exactly: `http://localhost:8000/oauth/callback/`
- Check for trailing slash
- Make sure it's "Web" platform, not "Single-page application"

### Can't find Client Secret
- Go to "Certificates & secrets"
- If you didn't copy it, create a new secret (old one can't be retrieved)

### Permissions not working
- Make sure you added `Files.ReadWrite.All` and `offline_access`
- For personal accounts, you don't need admin consent

---

## 📸 What the Azure Portal Looks Like

### App Registration Overview:
```
┌─────────────────────────────────────────┐
│ FileFlux                                │
├─────────────────────────────────────────┤
│ Essentials                              │
│                                         │
│ Application (client) ID:                │
│ 12345678-1234-1234-1234-123456789abc 📋 │
│                                         │
│ Directory (tenant) ID:                  │
│ 87654321-4321-4321-4321-cba987654321 📋 │
│                                         │
│ Supported account types:                │
│ Multitenant and personal accounts       │
└─────────────────────────────────────────┘
```

### Certificates & Secrets:
```
┌─────────────────────────────────────────┐
│ Client secrets                          │
├────────────────────────────────────��────┤
│ Description        │ Expires  │ Value   │
│ FileFlux Secret    │ 2027-... │ abc123...│
│                              [Copy] 📋  │
└─────────────────────────────────────────┘
```

---

## 🚀 Quick Checklist

Before giving me the credentials, verify:

- [ ] Created app registration named "FileFlux"
- [ ] Copied Application (client) ID
- [ ] Copied Directory (tenant) ID
- [ ] Created client secret
- [ ] Copied secret **Value** (not Secret ID!)
- [ ] Added redirect URI: `http://localhost:8000/oauth/callback/`
- [ ] Added API permissions (Files.ReadWrite.All, offline_access)

---

## 🎯 Ready to Start?

1. **Open:** https://portal.azure.com/
2. **Follow the steps above** (20-30 minutes)
3. **Copy your 3 pieces of information**
4. **Paste them here**

I'll handle all the code implementation! 🎉

---

## 💡 Tips

- **Use personal account** (@outlook.com) to avoid admin approval
- **Save your client secret** - you can't see it again after leaving the page
- **Take your time** - no rush, follow each step carefully
- **Ask questions** if anything is unclear!

---

**Document Version:** 1.0
**Last Updated:** 2026-03-03
**Time Required:** 20-30 minutes
**Difficulty:** Easy-Medium
