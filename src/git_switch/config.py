"""Profile configuration storage and management."""

import json
from pathlib import Path
from typing import Optional

from .utils import get_profiles_path


class ProfileConfig:
    """Manages git-switch profile configuration."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or get_profiles_path()

    def load_profiles(self) -> dict:
        """Load profiles from the configuration file.

        Returns:
            Dictionary with profiles data, or empty structure if file doesn't exist.
        """
        if not self.config_path.exists():
            return {"profiles": {}}

        with open(self.config_path, "r") as f:
            return json.load(f)

    def save_profiles(self, data: dict) -> None:
        """Save profiles to the configuration file."""
        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_profile(self, name: str) -> Optional[dict]:
        """Get a specific profile by name.

        Returns:
            Profile dictionary or None if not found.
        """
        data = self.load_profiles()
        return data.get("profiles", {}).get(name)

    def add_profile(self, name: str, profile_data: dict) -> None:
        """Add or update a profile."""
        data = self.load_profiles()
        if "profiles" not in data:
            data["profiles"] = {}
        data["profiles"][name] = profile_data
        self.save_profiles(data)

    def remove_profile(self, name: str) -> bool:
        """Remove a profile by name.

        Returns:
            True if profile was removed, False if it didn't exist.
        """
        data = self.load_profiles()
        if name in data.get("profiles", {}):
            del data["profiles"][name]
            self.save_profiles(data)
            return True
        return False

    def list_profiles(self) -> dict:
        """Get all profiles.

        Returns:
            Dictionary of profile_name -> profile_data.
        """
        data = self.load_profiles()
        return data.get("profiles", {})

    def profile_exists(self, name: str) -> bool:
        """Check if a profile exists."""
        return self.get_profile(name) is not None
