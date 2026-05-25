# Quick Start: Version Management

## For Developers: Making a Release

### 1. Update VERSION in all three repos

```bash
# Update all three repos to same version
cd c:\Users\Asus\QuantTraderTools\qcdemo
echo "1.4.0" > VERSION
git add VERSION
git commit -m "bump: version to 1.4.0"

cd c:\Users\Asus\QuantTraderTools\QuantCopierUI
echo "1.4.0" > VERSION
git add VERSION
git commit -m "bump: version to 1.4.0"

cd c:\Users\Asus\QuantTraderTools\QuantCopierReleaseNotes
echo "1.4.0" > VERSION
git add VERSION
git commit -m "bump: version to 1.4.0"
```

### 2. Push the tag from qcdemo (This triggers everything)

```bash
cd c:\Users\Asus\QuantTraderTools\qcdemo
git tag -a v1.4.0 -m "Release version 1.4.0"
git push origin v1.4.0
```

### 3. Wait for workflows to complete

- qcdemo: Builds `qcdemo.exe`
- QuantCopierUI: Builds `setup.exe` and `quantcopierapi.exe`
- QuantCopierReleaseNotes: Updates `public/releases.json`

All exes are uploaded to: `gs://finsentric-website-hosting.firebasestorage.app/v1.4.0/`

### 4. Verify files in bucket

```bash
gsutil ls -lh gs://finsentric-website-hosting.firebasestorage.app/v1.4.0/
```

Expected:
```
qcdemo.exe
setup.exe
quantcopierapi.exe
```

---

## For Applications: Auto-Updating

Add this to your app startup (before main window):

```python
from auto_update import auto_update_on_startup
import sys

# Check for updates on startup
if auto_update_on_startup():
    sys.exit(0)  # App was updated and will restart

# Continue with normal startup
main_window()
```

The auto-updater:
- Checks GCS bucket for newer version
- Downloads if found
- Backs up current exe
- Replaces with new version
- Restarts app

No additional configuration needed!

---

## Bucket Structure

```
gs://finsentric-website-hosting.firebasestorage.app/
├── v1.4.0/
│   ├── qcdemo.exe
│   ├── setup.exe
│   └── quantcopierapi.exe
└── v1.3.2/
    ├── qcdemo.exe
    ├── setup.exe
    └── quantcopierapi.exe
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "VERSION file not found" | Ensure VERSION exists in repo root |
| Build fails | Check GitHub Actions logs for specific error |
| Exe won't update | Verify new version is higher and in bucket |
| Permission denied on upload | Check GCP service account permissions |

See `VERSION_MANAGEMENT.md` for detailed docs.
