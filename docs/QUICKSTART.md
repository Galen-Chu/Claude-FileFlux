# Quick Start Guide - FileFlux v2.0.0

## 🚀 Get Started in 5 Minutes

### Step 1: Start the Server
```bash
cd D:\FileFlux
./venv/Scripts/python.exe manage.py runserver
```

The server is now running at: **http://localhost:8000/**

---

### Step 2: Create Your Account

1. **Open browser:** http://localhost:8000/register/
2. **Fill in the form:**
   - Username: `your_username`
   - Password: `your_password` (at least 8 characters)
   - Confirm Password: `your_password`
3. **Click "Create Account"**

You'll be redirected to the login page.

---

### Step 3: Log In

1. **Enter credentials:**
   - Username: `your_username`
   - Password: `your_password`
2. **Click "Sign In"**

You'll be redirected to the file manager!

---

### Step 4: Test Cloud Drive Connections (Demo Mode)

1. **Click the gear icon (⚙) in the top right** of the file manager header
2. **On your profile page**, you'll see two buttons:
   - **Connect OneDrive**
   - **Connect Google Drive**
3. **Click either button** to test the connection flow
4. The system will simulate a connection (demo mode)
5. **You'll see** the connected drive appear on your profile with:
   - Provider name
   - Connection date
   - Status (Active)
   - Disconnect button

---

### Step 5: Test File Operations

**Navigate back to file manager** by clicking "Back to File Manager" or visiting:
http://localhost:8000/manager/

Try these operations:
- ✅ **List files** from Local or S3
- ✅ **Select multiple files** with checkboxes
- ✅ **Rename files** with prefix/suffix/replace modes
- ✅ **Delete files** (with confirmation)
- ✅ **Upload files** to S3
- ✅ **Download files** from S3

All operations now require you to be logged in! 🔐

---

## 🧪 Run Automated Tests

Want to verify everything is working? Run the test suite:

```bash
cd D:\FileFlux
./venv/Scripts/python.exe test_v2.0.0.py
```

**Expected output:**
```
[OK] All Tests Passed!

Test Summary:
  - User registration: [OK]
  - Authentication system: [OK]
  - Cloud drive manager: [OK]
  - Token model: [OK]
  - API authentication: [OK]
```

---

## 📱 What You'll See

### Registration Page
- Beautiful purple gradient design
- Form validation
- Error messages
- Link to login

### Login Page
- Clean, modern interface
- Success/error notifications
- Link to register

### File Manager
- User greeting: "Welcome, your_username"
- Settings icon (⚙) for profile
- Logout button
- All file operations

### Profile Page
- Account information
- Connected cloud drives section
- Connect/disconnect buttons
- Connection status indicators

---

## 🎯 Key Features to Test

### Authentication
- [ ] Register new account
- [ ] Login with credentials
- [ ] Access protected pages (file manager, profile)
- [ ] Logout and verify redirect to login

### Cloud Drives
- [ ] Connect OneDrive (demo mode)
- [ ] Connect Google Drive (demo mode)
- [ ] View connection status
- [ ] Disconnect a drive
- [ ] Reconnect a drive

### File Operations
- [ ] List files from different sources
- [ ] Rename with prefix mode
- [ ] Rename with suffix mode
- [ ] Rename with replace mode (NEW!)
- [ ] Use regex patterns in replace mode (NEW!)
- [ ] Delete selected files
- [ ] Upload file to S3
- [ ] Download file from S3

---

## 🔧 Troubleshooting

### Can't Access Pages?
- Make sure you're logged in
- Clear browser cache
- Check server is running

### Server Not Starting?
- Check virtual environment is activated
- Verify all migrations applied: `python manage.py migrate`
- Check for error messages in console

### Cloud Drive Connection Issues?
- Demo mode should work without configuration
- Check console for JavaScript errors
- Verify you're logged in

---

## 📚 Documentation

For detailed information, see:
- **DOCUMENTATION_CLOUD_DRIVE_SETUP.md** - Cloud drive configuration
- **VERSION.md** - Version history and features
- **RELEASE_NOTES_v2.0.0.md** - Complete release summary

---

## 🎉 What's New in v2.0.0

### 🔐 Authentication System
- User registration and login
- Protected file operations
- User profiles
- Session management

### ☁️ Cloud Drive Integration
- OneDrive connection UI
- Google Drive connection UI
- Demo mode for testing
- Token management

### 🎨 UI Improvements
- User greeting in header
- Profile link with settings icon
- Beautiful login/register pages
- Enhanced profile page

---

## 🚦 Current Status

✅ **Server Running** at http://localhost:8000/
✅ **Authentication Working** - Login/Register functional
✅ **Cloud Drive UI Ready** - Demo mode available
✅ **All Tests Passing** - Integration tests verified
✅ **Documentation Complete** - Setup guides available

---

**Ready to explore! Open http://localhost:8000/register/ to get started!** 🚀
