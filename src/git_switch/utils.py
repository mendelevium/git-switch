"""Utility functions for OS detection and path management."""

import platform
from pathlib import Path


def detect_os() -> str:
    """Detect the current operating system.

    Returns:
        "darwin" for macOS, "linux" for Linux, "windows" for Windows
    """
    system = platform.system().lower()
    if system == "darwin":
        return "darwin"
    elif system == "linux":
        return "linux"
    elif system == "windows":
        return "windows"
    return system


def get_home_dir() -> Path:
    """Get the user's home directory."""
    return Path.home()


def get_ssh_dir() -> Path:
    """Get the SSH directory path."""
    return get_home_dir() / ".ssh"


def get_profiles_path() -> Path:
    """Get the path to the profiles configuration file."""
    return get_home_dir() / ".git-switch-profiles.json"


def get_ssh_config_path() -> Path:
    """Get the path to the SSH config file."""
    return get_ssh_dir() / "config"
