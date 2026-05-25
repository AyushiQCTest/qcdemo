# QuantCopier Version Management System

## Overview

This is a unified, streamlined version management system for the QuantCopier multi-repo project. All three repositories follow the same versioning approach with a single source of truth.

**Bucket**: `gs://finsentric-website-hosting.firebasestorage.app`

**Parent-Sibling Architecture**:
- **Parent**: `setup.exe` (main UI, user-facing) - checks and updates itself + siblings on startup
- **Siblings**: `qcdemo.exe`, `quantcopierapi.exe` - can check/update independently OR be updated by parent

```
Tag on qcdemo (v1.3.2)
    ↓
    ├→ [qcdemo] GitHub Actions builds qcdemo.exe
    │   └→ Uploads to gs://finsentric-website-hosting.firebasestorage.app/v1.3.2/qcdemo.exe
    │
    ├→ [QuantCopierUI] GitHub Actions builds setup.exe & quantcopierapi.exe
    │   └→ Uploads to gs://finsentric-website-hosting.firebasestorage.app/v1.3.2/{setup.exe, quantcopierapi.exe}
    │
    └→ [QuantCopierReleaseNotes] Auto-generates public/releases.json
        └→ Displays on website
```

## Key Components

### 1. VERSION File (Single Source of Truth)
- **Location**: Root of each repo (qcdemo, QuantCopierUI, QuantCopierReleaseNotes)
- **Content**: Semantic version string (e.g., `1.3.2`)
- **Usage**: Read by auto-updaters and build workflows

### 2. GCS Bucket Structure
```
gs://finsentric-website-hosting.firebasestorage.app/
  ├── v1.3.2/
  │   ├── qcdemo.exe              (built by qcdemo)
  │   ├── setup.exe               (built by QuantCopierUI - PARENT)
  │   └── quantcopierapi.exe      (built by QuantCopierUI - SIBLING)
  │
  ├── v1.3.1/
  │   ├── qcdemo.exe
  │   ├── setup.exe
  │   └── quantcopierapi.exe
  │
  └── [previous versions...]
```

### 3. Auto-Updater (auto_update.py)
Present in all three repos. Does the following:
- **On startup**: Checks Firebase Storage bucket for newer versions
- **Parent mode** (setup.exe): Checks and updates itself + siblings (qcdemo.exe, quantcopierapi.exe)
- **Standalone mode** (qcdemo.exe, quantcopierapi.exe): Check and update only themselves
- **Comparison**: Uses `packaging.version` for semantic versioning
- **Download**: Downloads the newest exe from bucket path `v{VERSION}/{exe_name}`
- **Backup**: Creates backup before replacing (e.g., `qcdemo-1.3.2.bak`)
- **Replace**: Swaps old exe with new one
- **Restart**: Relaunches the updated application

**Usage (Standalone)**:
```python
from auto_update import auto_update_on_startup

if auto_update_on_startup():
    # App was updated and restarted
    sys.exit(0)
```

**Usage (Parent Mode - setup.exe)**:
```python
from auto_update import auto_update_on_startup

# setup.exe checks and updates all three apps
if auto_update_on_startup(is_parent=True, sibling_exes=['qcdemo.exe', 'quantcopierapi.exe']):
    # App will restart with new version
    sys.exit(0)
```

## Release Process (Step-by-Step)

### Step 1: Update VERSION files
Update the VERSION file in all three repos to the new version (e.g., 1.4.0):

```bash
# In qcdemo
echo "1.4.0" > VERSION
git add VERSION
git commit -m "bump: version to 1.4.0"

# In QuantCopierUI
echo "1.4.0" > VERSION
git add VERSION
git commit -m "bump: version to 1.4.0"

# In QuantCopierReleaseNotes
echo "1.4.0" > VERSION
git add VERSION
git commit -m "bump: version to 1.4.0"
```

### Step 2: Create Release Tag
Push the tag **from qcdemo repo** (this triggers all builds):

```bash
cd c:\Users\Asus\QuantTraderTools\qcdemo

git tag -a v1.4.0 -m "Release version 1.4.0"
git push origin v1.4.0
```

### Step 3: Automated Workflows
The following happen automatically:

1. **qcdemo** (GitHub Actions `build-and-release.yml`):
   - Detects tag `v1.4.0`
   - Builds `qcdemo.exe` using PyInstaller
   - Uploads to `gs://finsentric-website-hosting.firebasestorage.app/v1.4.0/qcdemo.exe`
   - Creates GitHub Release

2. **QuantCopierUI** (GitHub Actions `build-and-upload-v2.yml`):
   - Detects tag `v1.4.0`
   - Builds `setup.exe` using Inno Setup
   - Builds `quantcopierapi.exe` using PyInstaller
   - Uploads both to `gs://finsentric-website-hosting.firebasestorage.app/v1.4.0/`
   - Creates GitHub Release

3. **QuantCopierReleaseNotes** (GitHub Actions `update-releases-json.yml`):
   - Fetches all tags from qcdemo repo
   - Generates `public/releases.json` with latest version info
   - Commits and pushes updates
   - Website automatically displays new release

### Step 4: Verify
Check that all files are in the bucket:
```bash
gsutil ls -R gs://finsentric-website-hosting.firebasestorage.app/v1.4.0/
```

Expected output:
```
gs://finsentric-website-hosting.firebasestorage.app/v1.4.0/:
gs://finsentric-website-hosting.firebasestorage.app/v1.4.0/qcdemo.exe
gs://finsentric-website-hosting.firebasestorage.app/v1.4.0/quantcopierapi.exe
gs://finsentric-website-hosting.firebasestorage.app/v1.4.0/setup.exe
```

## Auto-Update Flow (On Application Startup)

1. App calls `auto_update_on_startup()`
2. **Get current version**: Read VERSION file (e.g., 1.3.2)
3. **Get exe name**: Determine which exe is running (qcdemo.exe, setup.exe, etc.)
4. **Check bucket**: List all versions in bucket for matching exe
5. **Compare**: Find highest version newer than current
6. **If update available**:
   - Download new exe to temp location
   - Backup current exe (e.g., `qcdemo-1.3.2.bak`)
   - Remove current exe
   - Move new exe to current location
   - Restart application
7. **If no update**: Return False, app continues normally

## Dependencies

### All Repos
- `packaging` - For semantic version comparison
- `google-cloud-storage` - For GCS bucket access

Install with:
```bash
pip install google-cloud-storage packaging
```

### qcdemo
- `pyinstaller` - For building exe
- All dependencies from `requirements.txt`

### QuantCopierUI
- `pyinstaller` - For building quantcopierapi.exe
- Inno Setup 6 - For building setup.exe
- All dependencies from `Backend/requirements.txt`

### QuantCopierReleaseNotes
- Node.js with GitHub API access

## GitHub Actions Secrets Required

Setup these secrets in each repo:

| Secret | Purpose | Example |
|--------|---------|---------|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | GCS authentication | `projects/123/locations/global/workloadIdentityPools/...` |
| `GCP_SERVICE_ACCOUNT` | GCS service account | `build@project.iam.gserviceaccount.com` |
| `GITHUB_TOKEN` | GitHub API access | *Automatic in GitHub Actions* |

## Bucket Access

The Firebase Storage bucket `gs://finsentric-website-hosting.firebasestorage.app` must be **publicly readable** for downloads, but only **GitHub Actions service account** can write.

Check permissions:
```bash
gsutil ls -L gs://finsentric-website-hosting.firebasestorage.app/
```

## Troubleshooting

### Build fails with "VERSION file not found"
- Ensure VERSION file exists in repo root
- Workflow reads it before building

### Upload fails with "Permission denied"
- Verify service account has `storage.objects.create` permission
- Check workload identity provider is configured correctly

### Auto-update downloads wrong exe
- Verify exe name matches exactly (case-sensitive on Linux)
- Check bucket has the version folder

### Updater won't find new version
- Ensure new version is actually higher (semantic versioning)
- Check GCS bucket for file
- Verify bucket is publicly readable

## Files Added/Modified

### qcdemo
- `VERSION` - Version file (NEW)
- `auto_update.py` - Unified auto-updater (NEW)
- `.github/workflows/build-and-release.yml` - Build workflow (NEW)

### QuantCopierUI
- `VERSION` - Version file (UPDATED)
- `auto_update.py` - Unified auto-updater (NEW)
- `.github/workflows/build-and-upload-v2.yml` - Build workflow (NEW)
- Removed: `AUTO_UPDATE_*.md` docs (DELETED)
- Removed: `GITHUB_RELEASES_SETUP.md` (DELETED)
- Removed: `QUICK_START_CHECKLIST.md` (DELETED)

### QuantCopierReleaseNotes
- `VERSION` - Version file (NEW)
- `auto_update.py` - Unified auto-updater (NEW)
- `.github/workflows/update-releases-json.yml` - Release notes generator (NEW)
- Removed: `VERSION_MANAGEMENT.md` (DELETED)

## Future Enhancements

- Add delta updates (only download changed files)
- Add automatic rollback on failed update
- Add update notifications in app UI
- Add update scheduling (don't update during business hours)
