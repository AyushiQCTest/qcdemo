"""
Unified Auto-Updater for QuantCopier Executables
Checks Firebase Storage bucket for newer versions and auto-updates the executable

Bucket structure: gs://finsentric-website-hosting.firebasestorage.app/v1.3.2/{setup.exe, qcdemo.exe, quantcopierapi.exe}

Parent-Sibling Relationship:
  - Parent (setup.exe): Checks and updates itself + siblings (qcdemo.exe, quantcopierapi.exe)
  - Siblings: Check and update only themselves, unless triggered by parent
"""

import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple, List
from packaging import version as pkg_version

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger("QuantCopierAutoUpdate")


def get_current_version() -> str:
    """
    Get the current application version from VERSION file
    
    Looks for VERSION file in:
    1. Parent directory (if running from subdirectory)
    2. Current directory
    3. Repo root
    
    Returns:
        Version string (e.g., "1.3.2")
    """
    possible_paths = [
        Path(__file__).parent / "VERSION",
        Path(__file__).parent.parent / "VERSION",
        Path.cwd() / "VERSION",
    ]
    
    for version_file in possible_paths:
        if version_file.exists():
            try:
                return version_file.read_text().strip()
            except Exception as e:
                logger.warning(f"Failed to read {version_file}: {e}")
    
    logger.warning("No VERSION file found, using 1.0.0")
    return "1.0.0"


def get_executable_name() -> str:
    """Get the name of the current executable"""
    if hasattr(sys, 'frozen') and sys.frozen:
        return Path(sys.executable).name
    return Path(sys.argv[0]).name


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two version strings using packaging.version
    
    Args:
        v1: First version string (e.g., "1.3.2")
        v2: Second version string (e.g., "1.4.0")
    
    Returns:
        -1 if v1 < v2, 0 if equal, 1 if v1 > v2
    """
    try:
        v1_parsed = pkg_version.parse(v1)
        v2_parsed = pkg_version.parse(v2)
        
        if v1_parsed < v2_parsed:
            return -1
        elif v1_parsed > v2_parsed:
            return 1
        else:
            return 0
    except Exception as e:
        logger.error(f"Error comparing versions {v1} vs {v2}: {e}")
        return 0


def check_firebase_for_update(exe_name: str) -> Optional[dict]:
    """
    Check Firebase Storage bucket for newer version of the executable
    
    Expected bucket structure: gs://finsentric-website-hosting.firebasestorage.app/v1.3.2/qcdemo.exe
    
    Args:
        exe_name: Name of executable (e.g., 'qcdemo.exe')
    
    Returns:
        Dict with 'version', 'blob_name' and other metadata, or None if no update available
    """
    try:
        from google.cloud import storage
        
        current_version = get_current_version()
        logger.info(f"Checking GCS bucket for {exe_name} (current: {current_version})...")
        
        client = storage.Client()
        bucket = client.bucket("finsentric-website-hosting.firebasestorage.app")
        
        # List all blobs and find versions
        versions = {}
        
        try:
            blobs = client.list_blobs("finsentric-website-hosting.firebasestorage.app")
        except Exception as e:
            logger.error(f"Failed to list bucket: {e}")
            return None
        
        for blob in blobs:
            # Match pattern: v1.3.2/qcdemo.exe
            if exe_name in blob.name and '/v' in blob.name:
                parts = blob.name.split('/')
                if len(parts) >= 2 and parts[0].startswith('v'):
                    version_str = parts[0][1:]  # Remove 'v' prefix
                    try:
                        versions[version_str] = {
                            'version': version_str,
                            'blob_name': blob.name,
                            'size': blob.size,
                            'exe_name': exe_name,
                        }
                    except (ValueError, AttributeError):
                        continue
        
        if not versions:
            logger.info(f"No versions found in GCS bucket for {exe_name}")
            return None
        
        # Get the highest version
        latest_version = max(versions.keys(), key=lambda x: pkg_version.parse(x))
        latest_info = versions[latest_version]
        
        logger.info(f"Latest version in GCS: {latest_version}")
        
        # Check if update is available
        if compare_versions(current_version, latest_version) < 0:
            logger.info(f"Update available: {current_version} -> {latest_version}")
            return latest_info
        else:
            logger.info(f"Already on latest version ({current_version})")
            return None
    
    except ImportError:
        logger.warning("google-cloud-storage not installed. Install with: pip install google-cloud-storage")
        return None
    except Exception as e:
        logger.error(f"Error checking GCS bucket: {e}")
        return None


def download_update(blob_name: str, destination_path: str) -> bool:
    """
    Download update file from Firebase Storage bucket
    
    Args:
        blob_name: Name of blob in Firebase bucket (e.g., v1.3.2/qcdemo.exe)
        destination_path: Local path to save file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from google.cloud import storage
        
        logger.info(f"Downloading {blob_name}...")
        
        client = storage.Client()
        bucket = client.bucket("finsentric-website-hosting.firebasestorage.app")
        blob = bucket.blob(blob_name)
        blob.download_to_filename(destination_path)
        
        logger.info(f"Downloaded to {destination_path}")
        return True
    except Exception as e:
        logger.error(f"Error downloading update: {e}")
        return False


def backup_executable(exe_path: Path) -> Path:
    """Create a backup of the current executable"""
    try:
        current_version = get_current_version()
        backup_path = exe_path.parent / f"{exe_path.stem}-{current_version}.bak"
        shutil.copy2(exe_path, backup_path)
        logger.info(f"Backed up to {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to backup executable: {e}")
        raise


def apply_update(current_exe_path: str, new_exe_path: str, new_version: str) -> bool:
    """
    Apply the downloaded update by replacing the executable
    
    Steps:
    1. Backup current executable
    2. Replace with new one
    3. Return True to indicate restart is needed
    
    Args:
        current_exe_path: Path to current executable
        new_exe_path: Path to downloaded executable
        new_version: New version string
    
    Returns:
        True if successful, False otherwise
    """
    try:
        current_path = Path(current_exe_path)
        new_path = Path(new_exe_path)
        
        if not current_path.exists():
            logger.error(f"Current executable not found: {current_exe_path}")
            return False
        
        if not new_path.exists():
            logger.error(f"New executable not found: {new_exe_path}")
            return False
        
        # Backup current executable
        backup_executable(current_path)
        
        # Wait for file handles to close
        import time
        time.sleep(1)
        
        # Remove current and move new into place
        current_path.unlink()
        new_path.rename(current_path)
        
        logger.info(f"Update applied successfully to version {new_version}")
        return True
    
    except Exception as e:
        logger.error(f"Error applying update: {e}")
        return False


def check_and_update(exe_name: Optional[str] = None, sibling_exes: Optional[List[str]] = None) -> bool:
    """
    Check for updates and apply them if available
    
    This function should be called at application startup.
    Use sibling_exes parameter only when called from parent app (setup.exe).
    
    Args:
        exe_name: Name of executable to check for. If None, uses current executable name
        sibling_exes: List of sibling exe names to update (only used by parent app)
                     Example: ['qcdemo.exe', 'quantcopierapi.exe']
    
    Returns:
        True if update was applied and restart is needed, False otherwise
    """
    try:
        if exe_name is None:
            exe_name = get_executable_name()
        
        logger.info(f"Starting auto-update check for {exe_name}...")
        
        # Check for update
        update_info = check_firebase_for_update(exe_name)
        
        if not update_info:
            logger.info("No update available")
            
            # If parent app, also check siblings
            if sibling_exes:
                logger.info(f"Checking {len(sibling_exes)} sibling apps for updates...")
                for sibling in sibling_exes:
                    sibling_update = check_firebase_for_update(sibling)
                    if sibling_update:
                        logger.info(f"Update available for sibling: {sibling}")
                        # Parent app can trigger sibling updates here
                        # For now, log and notify user to restart
            
            return False
        
        # Create temp directory for download
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_exe_path = str(Path(temp_dir) / exe_name)
            
            # Download update
            if not download_update(update_info['blob_name'], temp_exe_path):
                logger.error("Failed to download update")
                return False
            
            # Get current executable path
            if hasattr(sys, 'frozen') and sys.frozen:
                current_exe_path = sys.executable
            else:
                current_exe_path = str(Path(sys.argv[0]).resolve())
            
            # Apply update
            if apply_update(current_exe_path, temp_exe_path, update_info['version']):
                logger.info("Update applied, restart needed")
                return True
            else:
                logger.error("Failed to apply update")
                return False
    
    except Exception as e:
        logger.error(f"Unexpected error in check_and_update: {e}")
        return False


def restart_application(exe_name: Optional[str] = None):
    """
    Restart the application
    
    Args:
        exe_name: Name of executable to restart (if None, restarts current)
    """
    try:
        if exe_name is None:
            if hasattr(sys, 'frozen') and sys.frozen:
                exe_path = sys.executable
            else:
                exe_path = str(Path(sys.argv[0]).resolve())
        else:
            exe_path = str(Path.cwd() / exe_name)
        
        logger.info(f"Restarting application: {exe_path}")
        
        if sys.platform == 'win32':
            subprocess.Popen(exe_path, shell=False)
        else:
            os.execv(exe_path, [exe_path])
        
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"Error restarting application: {e}")
        sys.exit(1)


def auto_update_on_startup(is_parent: bool = False, sibling_exes: Optional[List[str]] = None) -> bool:
    """
    Automatically check and update on startup
    If update is applied, this will restart the application
    
    Args:
        is_parent: Set to True if this is the parent app (setup.exe)
        sibling_exes: List of sibling exe names (only used when is_parent=True)
                     Example: ['qcdemo.exe', 'quantcopierapi.exe']
    
    Returns:
        True if restart was initiated, False otherwise
    """
    if is_parent and sibling_exes:
        if check_and_update(sibling_exes=sibling_exes):
            logger.info("Restarting application with new version...")
            import time
            time.sleep(2)
            restart_application()
            return True
    else:
        if check_and_update():
            logger.info("Restarting application with new version...")
            import time
            time.sleep(2)
            restart_application()
            return True
    return False


if __name__ == "__main__":
    result = check_and_update()
    print(f"Update check result: {result}")
