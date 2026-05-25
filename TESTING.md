# Version Management System - Testing Guide

## Testing Phases

### Phase 1: Local Testing (Before pushing anything)

#### 1.1 Test auto_update.py Module
```bash
cd c:\Users\Asus\QuantTraderTools\qcdemo

# Install test dependencies
pip install google-cloud-storage packaging pytest

# Test version comparison logic
python -c "
from auto_update import compare_versions
assert compare_versions('1.3.2', '1.4.0') == -1  # v1.3.2 < v1.4.0
assert compare_versions('1.4.0', '1.3.2') == 1   # v1.4.0 > v1.3.2
assert compare_versions('1.3.2', '1.3.2') == 0   # equal
print('✓ Version comparison working')
"

# Test VERSION file reading
python -c "
from auto_update import get_current_version
version = get_current_version()
print(f'✓ Current version: {version}')
assert version == '1.3.2'
"

# Test exe name detection
python -c "
from auto_update import get_executable_name
exe = get_executable_name()
print(f'✓ Executable name: {exe}')
"
```

#### 1.2 Test Firebase Storage Bucket Configuration
```bash
# First, ensure your GCP credentials are set up
# Option A: Using Application Default Credentials (gcloud)
gcloud auth application-default login

# Option B: Using service account key
$env:GOOGLE_APPLICATION_CREDENTIALS = "path/to/service-account-key.json"

# Then test bucket access
gsutil ls gs://finsentric-website-hosting.firebasestorage.app/

# Check if bucket exists and is accessible
gsutil ls -h gs://finsentric-website-hosting.firebasestorage.app/ 2>&1 | head -20
```

---

### Phase 2: Workflow Testing (Test tag release)

#### 2.1 Create a test tag (don't push yet)
```bash
cd c:\Users\Asus\QuantTraderTools\qcdemo

# Create VERSION test file
echo "1.3.2-test1" > VERSION

# Commit it
git add VERSION
git commit -m "test: version management testing"

# Create a test tag locally (don't push)
git tag -a v1.3.2-test1 -m "Test release"

# List the tag to verify
git tag -l v1.3.2-test1
```

#### 2.2 Validate GitHub Actions workflow syntax
```bash
# Install act (GitHub Actions local runner)
# https://github.com/nektos/act

# Then test the workflow locally
act push --event-name push -e trigger.json

# OR validate YAML syntax manually
# Check qcdemo/.github/workflows/build-and-release.yml is valid YAML
```

#### 2.3 Push test tag and monitor workflow
```bash
# If everything looks good, push the test tag
git push origin v1.3.2-test1

# Monitor GitHub Actions in browser:
# https://github.com/AyushiQCTest/qcdemo/actions
# 
# Watch for:
# 1. Workflow starts
# 2. Build completes
# 3. qcdemo.exe is created in dist/
# 4. Upload to GCS succeeds
# 5. GitHub Release is created
```

---

### Phase 3: Bucket Verification

#### 3.1 Verify files uploaded correctly
```bash
# Check the bucket after workflow completes
gsutil ls -lh gs://finsentric-website-hosting.firebasestorage.app/v1.3.2-test1/

# Expected output:
# gs://finsentric-website-hosting.firebasestorage.app/v1.3.2-test1/qcdemo.exe  [FILE_SIZE]  [DATE]

# Verify file is public (readable)
gsutil stat gs://finsentric-website-hosting.firebasestorage.app/v1.3.2-test1/qcdemo.exe
# Look for: "Access Control:" should allow AllUsers:Reader
```

#### 3.2 Test manual download from bucket
```bash
# Download the exe to test it
gsutil cp gs://finsentric-website-hosting.firebasestorage.app/v1.3.2-test1/qcdemo.exe ./test-qcdemo.exe

# Check file size is reasonable (> 10MB for PyInstaller)
Get-Item ./test-qcdemo.exe | Select-Object Length

# Verify PE header (Windows executable signature)
[byte[]]$header = Get-Content -Encoding Byte -ReadCount 2 -Path ./test-qcdemo.exe -TotalCount 2
if ([System.Text.Encoding]::ASCII.GetString($header) -eq "MZ") {
    Write-Host "✓ Valid Windows executable"
} else {
    Write-Host "✗ Invalid executable"
}
```

---

### Phase 4: Auto-Update Logic Testing

#### 4.1 Test update check with different versions
```bash
cd c:\Users\Asus\QuantTraderTools\qcdemo

# Create a test script
@"
from auto_update import check_gcs_for_update, get_current_version
import os

# Ensure GCP credentials are available
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'path/to/key.json'  # if needed

print(f"Current version: {get_current_version()}")
print("\nChecking for updates in bucket...")

result = check_gcs_for_update("qcdemo.exe")
if result:
    print(f"✓ Update found!")
    print(f"  Version: {result['version']}")
    print(f"  Blob: {result['blob_name']}")
    print(f"  Size: {result['size']} bytes")
else:
    print("✓ No update available (as expected, we're on latest)")
"@ | Out-File test_update_check.py

python test_update_check.py
```

#### 4.2 Test the download function
```bash
cd c:\Users\Asus\QuantTraderTools\qcdemo

# Create test script
@"
from auto_update import download_update
import tempfile
import os

# Setup credentials if needed
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'path/to/key.json'

with tempfile.TemporaryDirectory() as tmpdir:
    dest_path = os.path.join(tmpdir, 'test_download.exe')
    
    # Download a test file
    success = download_update('v1.3.2-test1/qcdemo.exe', dest_path)
    
    if success and os.path.exists(dest_path):
        size = os.path.getsize(dest_path)
        print(f"✓ Download successful")
        print(f"  File size: {size} bytes")
    else:
        print("✗ Download failed")
"@ | Out-File test_download.py

python test_download.py
```

---

### Phase 5: Full Release Testing

#### 5.1 Prepare for real test release
```bash
# Update VERSION in ALL THREE repos to same test version
cd c:\Users\Asus\QuantTraderTools\qcdemo
echo "1.3.3-test" > VERSION
git add VERSION && git commit -m "test: v1.3.3-test"

cd c:\Users\Asus\QuantTraderTools\QuantCopierUI
echo "1.3.3-test" > VERSION
git add VERSION && git commit -m "test: v1.3.3-test"

cd c:\Users\Asus\QuantTraderTools\QuantCopierReleaseNotes
echo "1.3.3-test" > VERSION
git add VERSION && git commit -m "test: v1.3.3-test"
```

#### 5.2 Push test tag
```bash
cd c:\Users\Asus\QuantTraderTools\qcdemo

# Create and push tag
git tag -a v1.3.3-test -m "Test release v1.3.3-test"
git push origin v1.3.3-test

# Monitor all three repos:
# 1. qcdemo: https://github.com/AyushiQCTest/qcdemo/actions
# 2. QuantCopierUI: https://github.com/AyushiQCTest/QuantCopierUI/actions
# 3. QuantCopierReleaseNotes: https://github.com/AyushiQCTest/QuantCopierReleaseNotes/actions
```

#### 5.3 Verify all artifacts
```bash
# Wait for all workflows to complete, then check:

# 1. Bucket structure
gsutil ls -R gs://finsentric-website-hosting.firebasestorage.app/v1.3.3-test/

# 2. GitHub Releases
# Check: https://github.com/AyushiQCTest/qcdemo/releases
# Should see: Release v1.3.3-test with qcdemo.exe attached

# 3. Release notes JSON
gsutil cat gs://finsentric-website-hosting.firebasestorage.app/releases.json | jq . | head -50
# Or check QuantCopierReleaseNotes/public/releases.json
```

---

### Phase 6: Simulate App Updating

#### 6.1 Test auto-update in controlled environment
```bash
# Setup a test scenario:

# 1. Create test app directory
mkdir C:\temp\qcdemo-update-test
cd C:\temp\qcdemo-update-test

# 2. Copy current qcdemo.exe (simulating old version)
cp c:\Users\Asus\QuantTraderTools\qcdemo\dist\qcdemo.exe .\old_qcdemo.exe

# 3. Copy auto_update.py and VERSION
cp c:\Users\Asus\QuantTraderTools\qcdemo\auto_update.py .
cp c:\Users\Asus\QuantTraderTools\qcdemo\VERSION .

# 4. Update VERSION to simulate older version
echo "1.3.2" > VERSION

# 5. Test the update check
python -c "
import sys
sys.path.insert(0, '.')
from auto_update import check_gcs_for_update, get_current_version

print(f'Current version: {get_current_version()}')
update = check_gcs_for_update('qcdemo.exe')
if update:
    print(f'✓ Update available: {update[\"version\"]}')
else:
    print('✓ No update available')
"
```

#### 6.2 Test update scenario with mock
```bash
# Create a test that simulates downloading and swapping
@"
import tempfile
import os
import shutil
from pathlib import Path
from auto_update import download_update, apply_update

test_dir = Path('test_update_scenario')
test_dir.mkdir(exist_ok=True)

# Simulate old exe
old_exe = test_dir / 'qcdemo.exe'
old_exe.write_bytes(b'OLD EXE CONTENT')

# Create temp dir with new exe
with tempfile.TemporaryDirectory() as tmpdir:
    new_exe = Path(tmpdir) / 'qcdemo.exe'
    # In real scenario, this would be downloaded from bucket
    new_exe.write_bytes(b'NEW EXE CONTENT')
    
    # Test apply_update
    success = apply_update(
        str(old_exe),
        str(new_exe),
        '1.3.2'
    )
    
    if success:
        print('✓ Update applied successfully')
        
        # Verify files
        print(f'  Current exe size: {old_exe.stat().st_size}')
        print(f'  Backup exists: {(test_dir / \"qcdemo-1.3.2.bak\").exists()}')
        print(f'  Content updated: {old_exe.read_bytes() == b\"NEW EXE CONTENT\"}')
    else:
        print('✗ Update failed')

# Cleanup
shutil.rmtree(test_dir)
"@ | Out-File test_update_scenario.py

python test_update_scenario.py
```

---

### Phase 7: End-to-End Integration Test

#### 7.1 Full workflow test checklist

- [ ] VERSION file exists in all 3 repos with same version
- [ ] GitHub Actions workflows have correct YAML syntax
- [ ] GCP credentials (Workload Identity) are configured
- [ ] GCS bucket exists and is accessible
- [ ] GCS bucket is public-readable for downloads
- [ ] Service account has write permissions to bucket
- [ ] Create test tag v1.3.3-test
- [ ] qcdemo workflow builds qcdemo.exe
- [ ] qcdemo.exe uploaded to gs://finsentric-website-hosting.firebasestorage.app/v1.3.3-test/
- [ ] QuantCopierUI builds setup.exe and quantcopierapi.exe
- [ ] Both exes uploaded to same bucket path
- [ ] QuantCopierReleaseNotes generates releases.json
- [ ] All exes can be downloaded from bucket
- [ ] Downloaded exes have valid PE header (MZ)
- [ ] auto_update.py detects newer versions
- [ ] auto_update.py successfully downloads updates
- [ ] Backup is created before replacing exe
- [ ] Old exe is replaced with new one

#### 7.2 Cleanup after testing
```bash
# Remove test versions from bucket
gsutil -m rm gs://finsentric-website-hosting.firebasestorage.app/v1.3.3-test/**
gsutil -m rm gs://finsentric-website-hosting.firebasestorage.app/v1.3.2-test1/**

# Remove test tags from repos
git push origin :v1.3.3-test
git push origin :v1.3.2-test1

# Delete test GitHub Releases
# (Do manually in GitHub web UI or via GitHub CLI)
```

---

## Testing Checklist Summary

```
Phase 1: Local Testing
  ☐ Version comparison logic
  ☐ VERSION file reading
  ☐ Exe name detection
  ☐ GCS bucket access
  
Phase 2: Workflow Testing
  ☐ Create test tag locally
  ☐ Validate workflow YAML
  ☐ Push test tag
  ☐ Monitor workflow execution
  
Phase 3: Bucket Verification
  ☐ Files uploaded to correct path
  ☐ Files are publicly readable
  ☐ Manual download from bucket
  ☐ Downloaded exe is valid Windows executable
  
Phase 4: Auto-Update Logic
  ☐ Version check function works
  ☐ Download function works
  ☐ File exists after download
  
Phase 5: Full Release Testing
  ☐ All 3 repos have same VERSION
  ☐ Tag created and pushed
  ☐ All 3 workflows complete
  ☐ All artifacts present in bucket
  ☐ GitHub Releases created
  
Phase 6: Update Simulation
  ☐ Auto-update detects newer version
  ☐ Download succeeds
  ☐ Backup created
  ☐ Exe replaced
  
Phase 7: Integration
  ☐ Full workflow works end-to-end
  ☐ All artifacts in correct location
  ☐ All checks pass
```

---

## Troubleshooting Common Issues

| Issue | Solution |
|-------|----------|
| "Bucket not found" | Check GCS bucket exists, credentials valid |
| "Permission denied" | Verify service account has roles/storage.objectAdmin |
| "Workflow doesn't trigger" | Check tag matches `v*` pattern |
| "Exe download fails" | Verify bucket is public, file exists in path |
| "Backup not created" | Check write permissions in exe directory |
| "Invalid executable" | Verify PyInstaller built exe correctly |

---

## Next Steps After Testing

1. ✅ All tests pass → Ready for production
2. ⚠️ Some tests fail → Fix issues, retest
3. 🎉 All tests pass → Push real release tag (v1.4.0, etc.)
4. 📋 Monitor first production release carefully
5. 🚀 Set up continuous monitoring of updates
