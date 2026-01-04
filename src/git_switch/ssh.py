"""SSH key generation and management."""

import os
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from .utils import get_ssh_config_path, get_ssh_dir


def generate_ssh_key(email: str, key_path: Path) -> Tuple[bool, str]:
    """Generate an Ed25519 SSH key.

    Args:
        email: Email address for the key comment
        key_path: Path where the key should be saved (without extension)

    Returns:
        Tuple of (success: bool, message: str)
    """
    # Ensure .ssh directory exists
    ssh_dir = get_ssh_dir()
    ssh_dir.mkdir(mode=0o700, exist_ok=True)

    if key_path.exists():
        return False, f"Key already exists at {key_path}"

    try:
        result = subprocess.run(
            [
                "ssh-keygen",
                "-t", "ed25519",
                "-C", email,
                "-f", str(key_path),
                "-N", "",  # Empty passphrase
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return True, f"SSH key generated at {key_path}"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to generate SSH key: {e.stderr}"
    except FileNotFoundError:
        return False, "ssh-keygen command not found"


def delete_ssh_key(key_path: Path) -> Tuple[bool, str]:
    """Delete an SSH key (both private and public).

    Args:
        key_path: Path to the private key file

    Returns:
        Tuple of (success: bool, message: str)
    """
    public_key_path = Path(str(key_path) + ".pub")
    deleted = []

    try:
        if key_path.exists():
            key_path.unlink()
            deleted.append(str(key_path))
        if public_key_path.exists():
            public_key_path.unlink()
            deleted.append(str(public_key_path))

        if deleted:
            return True, f"Deleted: {', '.join(deleted)}"
        return False, "No key files found to delete"
    except OSError as e:
        return False, f"Failed to delete key: {e}"


def key_exists(key_path: Path) -> bool:
    """Check if an SSH key exists."""
    return key_path.exists()


def get_public_key(key_path: Path) -> Optional[str]:
    """Read the public key content.

    Args:
        key_path: Path to the private key file

    Returns:
        Public key content or None if not found.
    """
    public_key_path = Path(str(key_path) + ".pub")
    if public_key_path.exists():
        return public_key_path.read_text().strip()
    return None


def add_ssh_config_entry(
    profile_name: str,
    key_path: Path,
    host: str = "github.com",
) -> Tuple[bool, str]:
    """Add an SSH config entry for a profile.

    Creates a Host alias like 'github-<profile_name>' that uses the specified key.

    Args:
        profile_name: Name of the profile
        key_path: Path to the SSH private key
        host: The actual hostname (default: github.com)

    Returns:
        Tuple of (success: bool, message: str)
    """
    config_path = get_ssh_config_path()
    alias = f"{host.split('.')[0]}-{profile_name}"

    entry = f"""
# git-switch: {profile_name}
Host {alias}
    HostName {host}
    User git
    IdentityFile {key_path}
    IdentitiesOnly yes
"""

    try:
        # Read existing config if it exists
        existing_content = ""
        if config_path.exists():
            existing_content = config_path.read_text()

        # Check if entry already exists
        if f"# git-switch: {profile_name}" in existing_content:
            # Remove existing entry first
            remove_ssh_config_entry(profile_name)
            existing_content = config_path.read_text() if config_path.exists() else ""

        # Append new entry
        with open(config_path, "a") as f:
            f.write(entry)

        # Ensure proper permissions
        os.chmod(config_path, 0o600)

        return True, f"Added SSH config alias: {alias}"
    except OSError as e:
        return False, f"Failed to update SSH config: {e}"


def remove_ssh_config_entry(profile_name: str) -> Tuple[bool, str]:
    """Remove an SSH config entry for a profile.

    Args:
        profile_name: Name of the profile

    Returns:
        Tuple of (success: bool, message: str)
    """
    config_path = get_ssh_config_path()

    if not config_path.exists():
        return False, "SSH config file does not exist"

    try:
        content = config_path.read_text()
        marker = f"# git-switch: {profile_name}"

        if marker not in content:
            return False, f"No SSH config entry found for profile: {profile_name}"

        # Remove the entry block (from marker to next blank line or next Host)
        pattern = rf"\n?# git-switch: {re.escape(profile_name)}\nHost [^\n]+\n(?:    [^\n]+\n)*"
        new_content = re.sub(pattern, "", content)

        config_path.write_text(new_content)
        return True, f"Removed SSH config entry for: {profile_name}"
    except OSError as e:
        return False, f"Failed to update SSH config: {e}"


def add_key_to_agent(key_path: Path) -> Tuple[bool, str]:
    """Add an SSH key to the ssh-agent.

    Args:
        key_path: Path to the private key file

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        result = subprocess.run(
            ["ssh-add", str(key_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        return True, "Key added to ssh-agent"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to add key to agent: {e.stderr}"
    except FileNotFoundError:
        return False, "ssh-add command not found"
