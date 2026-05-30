#!/usr/bin/env python3
"""
Auto-update script for qcdemo .exe files (Backend sidecar)
Checks Firebase Storage for newer versions and auto-updates the executable
"""

import os
import sys
import json
import subprocess
import urllib.request
import urllib.error
import tempfile
import shutil
import hashlib
import logging
from pathlib import Path
from typing import Optional, Tuple
from packaging import version

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)


class AutoUpdater:
    """Handles auto-updates for QuantCopier executable"""
    
    # Configuration
    FIREBASE_BUCKET_RAW = os.getenv('FIREBASE_STORAGE_BUCKET', 'finsentric-website-hosting.firebasestorage.app')
    # Strip .firebasestorage.app suffix if present to get GCS bucket name
    FIREBASE_BUCKET = FIREBASE_BUCKET_RAW.replace('.firebasestorage.app', '') if '.firebasestorage.app' in FIREBASE_BUCKET_RAW else FIREBASE_BUCKET_RAW
    RELEASES_JSON_URL = f"https://storage.googleapis.com/{FIREBASE_BUCKET}/releases.json"
    RELEASE_METADATA_URL = f"https://firebasestorage.googleapis.com/v0/b/{FIREBASE_BUCKET}/o/releases.json?alt=media"
    GITHUB_API_RELEASES = "https://api.github.com/repos/AyushiQCTest/QuantCopierUI/releases"
    
    # Update check interval (in days)
    CHECK_INTERVAL_DAYS = 7
    
    def __init__(self, exe_path: Optional[str] = None):
        """
        Initialize the auto-updater
        
        Args:
            exe_path: Path to the current executable. If None, uses sys.executable
        """
        self.exe_path = exe_path or sys.executable
        self.app_dir = Path(self.exe_path).parent
        self.config_dir = self.app_dir / '.update-config'
        self.config_dir.mkdir(exist_ok=True)
        self.version_file = self.config_dir / 'last_check.json'
    
    def get_current_version(self) -> str:
        """Get the current version from the VERSION file or default"""
        try:
            version_file = Path(__file__).parent.parent / "VERSION"
            if version_file.exists():
                return version_file.read_text().strip()
        except Exception as e:
            logger.warning(f"Could not read VERSION file: {e}")
        
        return "1.3.2"  # Fallback version
    
    def fetch_latest_release_info(self) -> Optional[dict]:
        """
        Fetch the latest release information from releases.json in GCS bucket
        Falls back to GitHub API if releases.json is not available
        
        Returns:
            dict with 'version' and 'download_url' keys, or None if failed
        """
        # Try releases.json first (primary method)
        release_info = self._fetch_from_releases_json()
        if release_info:
            return release_info
        
        # Fallback to GitHub API
        logger.info("releases.json not available, falling back to GitHub API...")
        return self._fetch_from_github_api()
    
    def _fetch_from_releases_json(self) -> Optional[dict]:
        """
        Fetch the latest release information from releases.json in GCS bucket
        
        Returns:
            dict with version and download_url, or None if failed
        """
        try:
            logger.info("Checking for updates from releases.json...")
            
            req = urllib.request.Request(
                self.RELEASES_JSON_URL,
                headers={'User-Agent': 'QuantCopier-AutoUpdater/1.0'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                
                latest_version = data.get('latest', '').lstrip('v')
                base_url = data.get('url') or data.get('baseUrl', '')
                files = data.get('files') if isinstance(data.get('files'), dict) else {}
                downloads = data.get('downloads') if isinstance(data.get('downloads'), dict) else {}

                if not latest_version:
                    logger.warning("releases.json missing required fields")
                    return None
                
                # Determine component key from current executable name.
                exe_name = self.exe_path.name if self.exe_path else None
                if not exe_name:
                    exe_name = 'setup.exe'

                component_key = None
                exe_name_lower = exe_name.lower()
                if 'setup' in exe_name_lower:
                    component_key = 'mainInstaller'
                elif 'telegram' in exe_name_lower or 'qc-demo' in exe_name_lower or 'qcdemo' in exe_name_lower:
                    component_key = 'qcdemoSidecar'
                elif 'api' in exe_name_lower:
                    component_key = 'apiSidecar'

                mapped_name = files.get(component_key) if component_key else None
                if mapped_name:
                    exe_name = mapped_name

                download_url = downloads.get(component_key) if component_key else None
                if not download_url:
                    if not base_url:
                        logger.warning("releases.json missing url/baseUrl and component downloads")
                        return None
                    download_url = f"{base_url}{exe_name}"
                
                return {
                    'version': latest_version,
                    'name': exe_name,
                    'download_url': download_url,
                    'size': 0  # Size not provided by releases.json
                }
                
        except urllib.error.URLError as e:
            logger.warning(f"Failed to fetch releases.json: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error parsing releases.json: {e}")
            return None
    
    def _fetch_from_github_api(self) -> Optional[dict]:
        """
        Fetch the latest release information from GitHub API
        
        Returns:
            dict with 'version' and 'download_url' keys, or None if failed
        """
        try:
            logger.info("Checking for updates from GitHub API...")
            
            req = urllib.request.Request(
                self.GITHUB_API_RELEASES,
                headers={'User-Agent': 'QuantCopier-AutoUpdater/1.0'}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                releases = json.loads(response.read().decode('utf-8'))
                
                if not releases:
                    logger.info("No releases found")
                    return None
                
                # Get the latest non-prerelease release
                for release in releases:
                    if release.get('prerelease'):
                        continue
                    
                    tag_name = release.get('tag_name', '').lstrip('v')
                    
                    # Find installer asset
                    for asset in release.get('assets', []):
                        if asset['name'].endswith('.exe'):
                            return {
                                'version': tag_name,
                                'name': asset['name'],
                                'download_url': asset['browser_download_url'],
                                'size': asset['size']
                            }
                
                logger.info("No suitable release found")
                return None
                
        except urllib.error.URLError as e:
            logger.warning(f"Failed to fetch release info from GitHub: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching release info from GitHub: {e}")
            return None
    
    def should_update(self, latest_version: str) -> bool:
        """
        Check if an update is needed
        
        Args:
            latest_version: The latest available version
            
        Returns:
            True if update is needed, False otherwise
        """
        current = self.get_current_version()
        
        try:
            return version.parse(latest_version) > version.parse(current)
        except Exception as e:
            logger.warning(f"Could not compare versions: {e}")
            return False
    
    def download_file(self, url: str, dest_path: Path, expected_size: int = 0) -> bool:
        """
        Download a file with progress reporting
        
        Args:
            url: URL to download from
            dest_path: Path to save the file
            expected_size: Expected file size in bytes (optional for validation)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Downloading from {url}...")
            
            def download_progress(block_num, block_size, total_size):
                downloaded = block_num * block_size
                percent = min(downloaded * 100 // max(total_size, 1), 100)
                logger.info(f"Progress: {percent}% ({downloaded / 1024 / 1024:.1f}MB)")
            
            urllib.request.urlretrieve(url, dest_path, download_progress)
            
            # Validate file size if expected
            if expected_size > 0:
                actual_size = dest_path.stat().st_size
                if actual_size != expected_size:
                    logger.warning(
                        f"File size mismatch: expected {expected_size}, "
                        f"got {actual_size}"
                    )
                    return False
            
            logger.info(f"Downloaded to {dest_path}")
            return True
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False
    
    def verify_executable(self, exe_path: Path) -> bool:
        """
        Verify that the downloaded file is a valid executable
        
        Args:
            exe_path: Path to the executable to verify
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Basic checks
            if not exe_path.exists():
                logger.error("File does not exist")
                return False
            
            if exe_path.suffix.lower() != '.exe':
                logger.error("File is not an .exe")
                return False
            
            if exe_path.stat().st_size < 1024:  # Less than 1KB is suspicious
                logger.error("File size is too small")
                return False
            
            # Check PE header (Windows executable format)
            with open(exe_path, 'rb') as f:
                header = f.read(2)
                if header != b'MZ':
                    logger.error("Invalid PE header (not an executable)")
                    return False
            
            logger.info("Executable verification passed")
            return True
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False
    
    def backup_current_executable(self) -> Path:
        """
        Create a backup of the current executable
        
        Returns:
            Path to the backup file
        """
        try:
            backup_path = self.app_dir / f"{self.exe_path.stem}.bak"
            shutil.copy2(self.exe_path, backup_path)
            logger.info(f"Backed up current executable to {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise
    
    def replace_executable(self, new_exe_path: Path) -> bool:
        """
        Replace the current executable with the new one
        
        Args:
            new_exe_path: Path to the new executable
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create backup
            self.backup_current_executable()
            
            # On Windows, we need to handle file locks
            # The executable might be in use
            if os.name == 'nt':
                # Move current to .old and move new to current
                old_path = self.exe_path.with_suffix('.exe.old')
                if old_path.exists():
                    old_path.unlink()
                
                shutil.move(str(self.exe_path), str(old_path))
                shutil.copy2(str(new_exe_path), str(self.exe_path))
                
                logger.info(f"Replaced executable: {self.exe_path}")
            else:
                shutil.copy2(new_exe_path, self.exe_path)
                logger.info(f"Replaced executable: {self.exe_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to replace executable: {e}")
            return False
    
    def relaunch_application(self):
        """Relaunch the application after update"""
        try:
            logger.info("Relaunching application...")
            
            if os.name == 'nt':
                # Windows
                os.startfile(str(self.exe_path))
            else:
                # Unix-like
                subprocess.Popen([str(self.exe_path)])
            
            logger.info("Application relaunched successfully")
            
        except Exception as e:
            logger.error(f"Failed to relaunch: {e}")
            raise
    
    def check_and_update(self, force: bool = False) -> bool:
        """
        Check for updates and perform the update if available
        
        Args:
            force: Force update even if check interval hasn't passed
            
        Returns:
            True if updated, False otherwise
        """
        logger.info("=== Auto-Update Check Started ===")
        
        try:
            # Check if we should skip this check
            if not force and self._should_skip_check():
                logger.info("Skipping check (within check interval)")
                return False
            
            # Fetch latest release info
            latest_info = self.fetch_latest_release_info()
            if not latest_info:
                logger.info("Could not fetch release information")
                return False
            
            logger.info(f"Latest version available: {latest_info['version']}")
            
            # Check if update is needed
            if not self.should_update(latest_info['version']):
                logger.info("Already on latest version or newer")
                self._update_last_check()
                return False
            
            logger.info(f"Update available! Current: {self.get_current_version()}, "
                       f"Latest: {latest_info['version']}")
            
            # Download the new version
            with tempfile.TemporaryDirectory() as tmpdir:
                new_exe_path = Path(tmpdir) / latest_info['name']
                
                if not self.download_file(
                    latest_info['download_url'],
                    new_exe_path,
                    latest_info.get('size', 0)
                ):
                    logger.error("Failed to download update")
                    return False
                
                # Verify the downloaded executable
                if not self.verify_executable(new_exe_path):
                    logger.error("Downloaded file verification failed")
                    return False
                
                # Replace the executable
                if not self.replace_executable(new_exe_path):
                    logger.error("Failed to replace executable")
                    return False
            
            # Update check timestamp
            self._update_last_check()
            
            logger.info("✓ Update successful!")
            logger.info("=== Auto-Update Check Completed ===")
            
            return True
            
        except Exception as e:
            logger.error(f"Update check failed: {e}")
            return False
    
    def _should_skip_check(self) -> bool:
        """Check if we should skip the update check based on interval"""
        try:
            import time
            
            if not self.version_file.exists():
                return False
            
            data = json.loads(self.version_file.read_text())
            last_check = data.get('last_check', 0)
            current_time = time.time()
            
            # Check if enough time has passed
            days_passed = (current_time - last_check) / (24 * 3600)
            return days_passed < self.CHECK_INTERVAL_DAYS
            
        except Exception:
            return False
    
    def _update_last_check(self):
        """Update the last check timestamp"""
        try:
            import time
            
            data = {
                'last_check': time.time(),
                'version': self.get_current_version()
            }
            
            self.version_file.write_text(json.dumps(data, indent=2))
            
        except Exception as e:
            logger.warning(f"Failed to update check timestamp: {e}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Auto-update tool for QuantCopier executables'
    )
    parser.add_argument(
        '--exe',
        type=str,
        default=None,
        help='Path to the executable to update'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force update check even within interval'
    )
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='Only check for updates without performing the update'
    )
    
    args = parser.parse_args()
    
    updater = AutoUpdater(exe_path=args.exe)
    
    if args.check_only:
        logger.info("Checking for updates...")
        latest_info = updater.fetch_latest_release_info()
        if latest_info:
            logger.info(f"Update available: {latest_info['version']}")
            logger.info(f"Download URL: {latest_info['download_url']}")
        else:
            logger.info("No updates available")
    else:
        success = updater.check_and_update(force=args.force)
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
