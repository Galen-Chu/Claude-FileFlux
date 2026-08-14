# FileFlux v1.2.0 & v2.0.0 Feature Planning Summary

## Overview

This document summarizes two proposed features for upcoming versions of FileFlux and provides recommendations for implementation.

---

## Feature 1: Replace Mode in Rename (v1.2.0) ✅ Ready to Implement

### Status
- **Planning:** Complete ✅
- **Implementation Plan:** [PLAN_v1.2.0_replace_mode.md](./PLAN_v1.2.0_replace_mode.md)
- **Estimated Time:** 1-2 days
- **Complexity:** Low-Medium
- **Dependencies:** None (builds on existing v1.1.0 code)

### What It Does
Allows users to find and replace text in filenames with these options:
- Simple text replacement (case-sensitive/insensitive)
- Regular expression support (advanced users)
- Replace all occurrences or just the first
- Combine with sequential numbering
- Replace with empty string (delete text)

### Example Use Cases
```
# Update version numbers
report_v1.pdf → report_v2.pdf (find: "v1", replace: "v2")

# Remove unwanted text
file_backup_2024.txt → file_2024.txt (find: "_backup", replace: "")

# Batch rename with sequence
doc_draft.txt, report_draft.txt → doc_final_001.txt, report_final_002.txt
(find: "draft", replace: "final", + sequence)

# Regex pattern matching
IMG_2024_0303.jpg → PHOTO_2024_0303.jpg (regex find: "IMG_(\d+)", replace: "PHOTO_\1")
```

### Implementation Steps
1. Update `BaseStorage` interface (add replace parameters)
2. Implement in `LocalStorage` and `S3Storage`
3. Update `BulkRenameRequestSerializer`
4. Update `FileManagementViewSet.rename()`
5. Enhance frontend modal UI
6. Add JavaScript handlers
7. Write unit tests
8. Update documentation

### Files to Modify
- `manager/services/base.py`
- `manager/services/local_storage.py`
- `manager/services/s3_storage.py`
- `manager/services/unified_storage.py`
- `manager/serializers.py`
- `manager/api_views.py`
- `templates/file_manager.html`
- `VERSION.md`
- `CHANGELOG.md`
- `README.md`

### Backward Compatibility
✅ **Fully backward compatible** - Old API calls continue to work
- New parameters are optional
- Default mode remains 'prefix'
- Existing integrations unaffected

### Security Concerns
- ✅ Regex validation to prevent ReDoS attacks
- ✅ Input length limits
- ✅ Timeout for complex regex operations

### Recommendation
**👍 Implement in v1.2.0** - Straightforward addition that provides significant value to users.

---

## Feature 2: Cloud Drive Integration (v2.0.0+) ⚠️ Requires Planning

### Status
- **Planning:** Complete ✅
- **Implementation Plan:** [PLAN_v2.0.0_cloud_drive.md](./PLAN_v2.0.0_cloud_drive.md)
- **Estimated Time:** 2-5 weeks (depending on approach)
- **Complexity:** High
- **Dependencies:** Authentication system (major requirement)

### What It Does
Allows users to connect and manage files from:
- Microsoft OneDrive
- Google Drive
- Potentially 40+ other cloud providers

### Why Authentication is Required First
⚠️ **Critical Dependency:** OAuth 2.0 requires user accounts because:
1. OAuth tokens must be associated with specific users
2. Each user needs their own cloud drive connections
3. Tokens need secure storage per-user
4. API rate limits are per-user
5. Security requires user isolation

### Implementation Approaches

#### Approach A: Native OAuth Implementation
**Time:** 4-5 weeks total
**Phases:**
1. Add Django authentication system (3-5 days)
2. Implement OneDrive with OAuth (5-7 days)
3. Implement Google Drive with OAuth (5-7 days)
4. Unified multi-cloud UI (3-4 days)

**Pros:**
- Full control over implementation
- Professional user experience
- Can customize OAuth flow
- Better error handling

**Cons:**
- Significant development time
- Complex security requirements
- Ongoing maintenance burden
- Need to register apps with Microsoft & Google
- OAuth token management complexity

**Requirements:**
- Register Azure AD application
- Register Google Cloud project
- Implement OAuth 2.0 flows
- Token encryption in database
- Token refresh mechanisms
- HTTPS required in production

#### Approach B: Rclone Backend ⭐ Recommended
**Time:** 1-2 weeks total
**Phases:**
1. Add Django authentication (3-5 days)
2. Implement RcloneStorage wrapper (2-3 days)
3. Test with multiple providers (2-3 days)
4. UI integration (2-3 days)

**Pros:**
- Much faster to implement
- 40+ cloud providers supported out-of-box
- OAuth handled by rclone
- Battle-tested, production-ready
- Less code to maintain
- Regular updates from rclone community

**Cons:**
- External dependency
- Less customization
- Requires rclone installation
- Additional system dependency

**Supported Providers (with Rclone):**
- OneDrive, Google Drive, Dropbox
- Amazon S3, Backblaze B2
- Box, pCloud, Yandex.Disk
- FTP, WebDAV
- And 35+ more...

### Recommendation

**✅ Use Rclone Approach** for these reasons:
1. **80% less development time**
2. **40+ providers vs 2**
3. **OAuth complexity handled for you**
4. **Production-ready reliability**
5. **Community support**

### Implementation Phases (Rclone Approach)

#### Phase 1: Authentication (v2.0.0)
- Add Django authentication
- User registration/login
- Session + token authentication
- Basic user profile
- **Time:** 3-5 days

#### Phase 2: Replace Mode (v2.0.0)
- Implement replace mode in rename
- See Feature 1 plan
- **Time:** 1-2 days

#### Phase 3: Rclone Integration (v2.1.0)
- Install and configure rclone
- Implement RcloneStorage backend
- UI for connecting providers
- File operations across all providers
- **Time:** 5-7 days

#### Phase 4: Enhanced Features (v2.2.0+)
- File preview
- Search across all sources
- Drag & drop upload
- Real-time sync

### Cloud Drive Setup (User Perspective)

With Rclone approach, users would:
1. Install rclone on their system
2. Run `rclone config` (one-time setup)
3. Authorize cloud drives via rclone (handles OAuth)
4. Enter rclone remote name in FileFlux UI
5. Start managing files

### Security with Rclone

✅ Still secure because:
- OAuth tokens stored locally by rclone
- User's own credentials
- No tokens in FileFlux database
- Each user has their own rclone config
- Can still use Django auth for FileFlux access

---

## Version Roadmap

### v1.2.0 (Next Release - 1-2 days)
- ✅ Replace mode in rename
- ✅ Enhanced documentation
- ✅ Bug fixes and improvements

### v2.0.0 (Major Release - 1 week)
- 🔐 Authentication system
- 👤 User accounts and profiles
- 🔄 Replace mode (if not in v1.2.0)
- 📝 Enhanced audit logging per-user

### v2.1.0 (2-3 weeks after v2.0.0)
- ☁️ Cloud drive integration (Rclone)
- 🔗 Multi-provider support
- 📂 Unified file view across all sources
- 🎨 Enhanced UI for cloud sources

### v2.2.0+ (Future)
- 👁️ File preview
- 🔍 Search and filter
- 📤 Drag & drop upload
- 🔄 Bi-directional sync
- 🌐 Real-time updates

---

## Decision Matrix

| Feature | Time | Value | Complexity | Dependencies | Recommendation |
|---------|------|-------|------------|--------------|----------------|
| Replace Mode | 1-2 days | High | Low | None | ✅ Do Now (v1.2.0) |
| Authentication | 3-5 days | Critical | Medium | None | ✅ Do Next (v2.0.0) |
| Cloud Drives (OAuth) | 4-5 weeks | High | Very High | Auth + App Registration | ⚠️ Consider Alternatives |
| Cloud Drives (Rclone) | 1-2 weeks | Very High | Medium | Auth + Rclone Install | ✅ Recommended (v2.1.0) |

---

## Action Items

### Immediate (v1.2.0)
- [ ] Review and approve Replace Mode plan
- [ ] Implement Replace Mode feature
- [ ] Update tests and documentation
- [ ] Release v1.2.0

### Short-term (v2.0.0)
- [ ] Design authentication flow
- [ ] Implement Django authentication
- [ ] Add user model and profiles
- [ ] Update API to require authentication
- [ ] Migrate existing data to support users
- [ ] Release v2.0.0

### Medium-term (v2.1.0)
- [ ] Evaluate Rclone vs native OAuth
- [ ] Install and test Rclone
- [ ] Implement RcloneStorage backend
- [ ] Create cloud drive connection UI
- [ ] Test with real cloud accounts
- [ ] Release v2.1.0

---

## Questions to Consider

1. **Replace Mode Priority**
   - Should this be in v1.2.0 or combined with v2.0.0?
   - **Recommendation:** v1.2.0 (quick win, no dependencies)

2. **Authentication Scope**
   - Basic Django auth or social auth (Google/Microsoft login)?
   - **Recommendation:** Start with Django auth, add social auth in v2.2.0

3. **Cloud Drive Approach**
   - Native OAuth or Rclone?
   - **Recommendation:** Rclone (faster, more providers, less maintenance)

4. **User Experience**
   - Should cloud drives be per-user or system-wide?
   - **Recommendation:** Per-user (more secure, better multi-tenancy)

5. **MVP Scope**
   - Which cloud providers for initial release?
   - **Recommendation:** OneDrive + Google Drive (covers most users)

---

## Summary

**v1.2.0 (Next):**
- ✅ Replace Mode: **Do it** (1-2 days, high value, low risk)

**v2.0.0:**
- 🔐 Authentication: **Required first** (3-5 days, enables cloud drives)

**v2.1.0:**
- ☁️ Cloud Drives: **Use Rclone** (1-2 weeks, 40+ providers, proven solution)

**Total Timeline:**
- v1.2.0: 2 days
- v2.0.0: 1 week
- v2.1.0: 2-3 weeks after v2.0.0

**Next Step:** Review plans and decide on v1.2.0 implementation start date

---

## Documentation References

- [Replace Mode Implementation Plan](./PLAN_v1.2.0_replace_mode.md)
- [Cloud Drive Integration Plan](./PLAN_v2.0.0_cloud_drive.md)
- [Initial Implementation Plan](./PLAN_v1.0.0_initial_implementation.md)
- [Version History](./VERSION.md)
- [Changelog](./CHANGELOG.md)
