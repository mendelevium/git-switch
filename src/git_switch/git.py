"""Git configuration operations."""

import subprocess
from typing import Optional, Tuple


def run_git_command(args: list[str]) -> Tuple[bool, str]:
    """Run a git command and return success status and output.

    Returns:
        Tuple of (success: bool, output: str)
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            check=True,
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()
    except FileNotFoundError:
        return False, "git command not found"


def get_current_git_user() -> Tuple[Optional[str], Optional[str]]:
    """Get the current global git user name and email.

    Returns:
        Tuple of (name, email), either can be None if not set.
    """
    success_name, name = run_git_command(["config", "--global", "user.name"])
    success_email, email = run_git_command(["config", "--global", "user.email"])

    return (
        name if success_name else None,
        email if success_email else None,
    )


def set_git_user(name: str, email: str) -> Tuple[bool, str]:
    """Set the global git user name and email.

    Returns:
        Tuple of (success: bool, error_message: str)
    """
    success_name, error_name = run_git_command(
        ["config", "--global", "user.name", name]
    )
    if not success_name:
        return False, f"Failed to set user.name: {error_name}"

    success_email, error_email = run_git_command(
        ["config", "--global", "user.email", email]
    )
    if not success_email:
        return False, f"Failed to set user.email: {error_email}"

    return True, ""


def detect_current_profile(profiles: dict) -> Optional[str]:
    """Detect which profile matches the current git configuration.

    Args:
        profiles: Dictionary of profile_name -> profile_data

    Returns:
        Profile name if a match is found, None otherwise.
    """
    current_name, current_email = get_current_git_user()

    if current_name is None or current_email is None:
        return None

    for profile_name, profile_data in profiles.items():
        if (
            profile_data.get("name") == current_name
            and profile_data.get("email") == current_email
        ):
            return profile_name

    return None
