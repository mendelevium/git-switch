"""CLI commands for git-switch."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .config import ProfileConfig
from .git import detect_current_profile, get_current_git_user, set_git_user
from .ssh import (
    add_key_to_agent,
    add_ssh_config_entry,
    delete_ssh_key,
    generate_ssh_key,
    get_public_key,
    remove_ssh_config_entry,
)
from .utils import detect_os, get_ssh_dir

app = typer.Typer(
    name="git-switch",
    help="Switch between git user profiles.",
    no_args_is_help=False,
)
console = Console()
config = ProfileConfig()


def display_public_key(public_key: str) -> None:
    """Display a public key with the email on a separate line."""
    parts = public_key.split()
    if len(parts) >= 3:
        # Format: ssh-ed25519 AAAA... email@example.com
        key_type = parts[0]
        key_data = parts[1]
        email = " ".join(parts[2:])
        console.print(f"[cyan]{key_type} {key_data}[/cyan]")
        console.print(f"[dim]{email}[/dim]")
    else:
        console.print(f"[cyan]{public_key}[/cyan]")


def show_profiles_table(profiles: dict, current_profile: str | None) -> None:
    """Display profiles in a formatted table."""
    table = Table(show_header=True, header_style="bold")
    table.add_column("#", style="dim", width=3)
    table.add_column("Profile", style="cyan")
    table.add_column("Name")
    table.add_column("Email")
    table.add_column("SSH Key")
    table.add_column("Current", justify="center")

    for idx, (name, data) in enumerate(profiles.items(), 1):
        is_current = name == current_profile
        ssh_key = data.get("ssh_key", "-")
        if ssh_key != "-":
            ssh_key = Path(ssh_key).name
        table.add_row(
            str(idx),
            name,
            data.get("name", "-"),
            data.get("email", "-"),
            ssh_key,
            "[green]●[/green]" if is_current else "",
        )

    console.print(table)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Interactive profile picker (default command)."""
    if ctx.invoked_subcommand is not None:
        return

    profiles = config.list_profiles()

    if not profiles:
        console.print("[yellow]No profiles configured.[/yellow]")
        console.print("Create one with: [cyan]git-switch add <name>[/cyan]")
        raise typer.Exit(1)

    current = detect_current_profile(profiles)
    console.print("\n[bold]Git Profiles[/bold]")
    console.print(f"[dim]OS: {detect_os()}[/dim]\n")

    show_profiles_table(profiles, current)

    # Interactive selection
    profile_names = list(profiles.keys())
    choice = Prompt.ask(
        "\nSelect profile number",
        choices=[str(i) for i in range(1, len(profile_names) + 1)],
        default="1" if not current else str(profile_names.index(current) + 1),
    )

    selected_profile = profile_names[int(choice) - 1]
    _switch_to_profile(selected_profile)


def _switch_to_profile(profile_name: str) -> None:
    """Internal function to switch to a profile."""
    profile = config.get_profile(profile_name)

    if not profile:
        console.print(f"[red]Profile '{profile_name}' not found.[/red]")
        raise typer.Exit(1)

    success, error = set_git_user(profile["name"], profile["email"])

    if success:
        console.print(f"\n[green]Switched to profile:[/green] [bold]{profile_name}[/bold]")
        console.print(f"  Name:  {profile['name']}")
        console.print(f"  Email: {profile['email']}")

        if profile.get("ssh_key"):
            console.print(f"  SSH:   {profile['ssh_key']}")
            console.print(
                f"\n[dim]Use [cyan]git@github-{profile_name}:user/repo.git[/cyan] for SSH remotes[/dim]"
            )
    else:
        console.print(f"[red]Failed to switch profile: {error}[/red]")
        raise typer.Exit(1)


# =============================================================================
# Commands
# =============================================================================

@app.command("list", help="List all configured profiles.")
def list_profiles(
    # Short alias: git-switch -l
) -> None:
    """List all configured profiles."""
    profiles = config.list_profiles()

    if not profiles:
        console.print("[yellow]No profiles configured.[/yellow]")
        raise typer.Exit(1)

    current = detect_current_profile(profiles)
    show_profiles_table(profiles, current)


@app.command("use", help="Switch to a specific profile.")
def use_profile(
    name: str = typer.Argument(..., help="Profile name to switch to"),
) -> None:
    """Switch to a specific profile."""
    _switch_to_profile(name)


@app.command("add", help="Add a new profile.")
def add_profile(
    name: str = typer.Argument(..., help="Name for the new profile"),
    user_name: Optional[str] = typer.Option(None, "--name", "-n", help="Git user name"),
    email: Optional[str] = typer.Option(None, "--email", "-e", help="Git email"),
    ssh: Optional[bool] = typer.Option(None, "--ssh/--no-ssh", "-s/-S", help="Generate SSH key"),
) -> None:
    """Add a new profile."""
    if config.profile_exists(name):
        console.print(f"[red]Profile '{name}' already exists. Use 'edit' to modify.[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Adding profile: {name}[/bold]\n")

    # Prompt for details if not provided
    if user_name is None:
        user_name = Prompt.ask("Git user name")
    if email is None:
        email = Prompt.ask("Git email")

    profile_data = {
        "name": user_name,
        "email": email,
    }

    # SSH key generation
    generate_ssh = ssh if ssh is not None else Confirm.ask("Generate SSH key?", default=True)
    if generate_ssh:
        key_path = get_ssh_dir() / f"id_ed25519_{name}"
        success, message = generate_ssh_key(email, key_path)

        if success:
            profile_data["ssh_key"] = str(key_path)
            console.print(f"[green]{message}[/green]")

            # Show public key
            public_key = get_public_key(key_path)
            if public_key:
                console.print("\n[bold]Public key (add to GitHub/GitLab):[/bold]")
                display_public_key(public_key)

            # Add to SSH config
            ssh_success, ssh_message = add_ssh_config_entry(name, key_path)
            if ssh_success:
                console.print(f"[green]{ssh_message}[/green]")
            else:
                console.print(f"[yellow]Warning: {ssh_message}[/yellow]")

            # Add to agent
            if Confirm.ask("Add key to ssh-agent?", default=True):
                agent_success, agent_message = add_key_to_agent(key_path)
                if agent_success:
                    console.print(f"[green]{agent_message}[/green]")
                else:
                    console.print(f"[yellow]Warning: {agent_message}[/yellow]")
        else:
            console.print(f"[yellow]Warning: {message}[/yellow]")

    # Save profile
    config.add_profile(name, profile_data)
    console.print(f"\n[green]Profile '{name}' added successfully![/green]")

    if Confirm.ask("Switch to this profile now?", default=True):
        _switch_to_profile(name)


@app.command("edit", help="Edit an existing profile.")
def edit_profile(
    name: str = typer.Argument(..., help="Profile name to edit"),
    user_name: Optional[str] = typer.Option(None, "--name", "-n", help="New git user name"),
    email: Optional[str] = typer.Option(None, "--email", "-e", help="New git email"),
    ssh: Optional[bool] = typer.Option(None, "--ssh/--no-ssh", "-s/-S", help="Generate SSH key"),
) -> None:
    """Edit an existing profile."""
    profile = config.get_profile(name)

    if not profile:
        console.print(f"[red]Profile '{name}' not found.[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Editing profile: {name}[/bold]")
    console.print(f"[dim]Leave blank to keep current value[/dim]\n")

    # Current values
    current_name = profile.get("name", "")
    current_email = profile.get("email", "")

    # Prompt for new values if not provided via options
    if user_name is None:
        new_name = Prompt.ask(f"Git user name", default=current_name)
    else:
        new_name = user_name

    if email is None:
        new_email = Prompt.ask(f"Git email", default=current_email)
    else:
        new_email = email

    # Update profile
    profile["name"] = new_name
    profile["email"] = new_email

    # Handle SSH key
    has_existing_key = bool(profile.get("ssh_key"))

    if has_existing_key:
        # Ask to regenerate existing key
        if ssh is True:
            regenerate = True
        elif ssh is False:
            regenerate = False
        else:
            regenerate = Confirm.ask("Regenerate SSH key?", default=False)

        if regenerate:
            # Delete old key first
            old_key_path = Path(profile["ssh_key"])
            delete_ssh_key(old_key_path)
            remove_ssh_config_entry(name)
            console.print(f"[dim]Removed old SSH key[/dim]")

            # Generate new key
            key_path = get_ssh_dir() / f"id_ed25519_{name}"
            success, message = generate_ssh_key(new_email, key_path)

            if success:
                profile["ssh_key"] = str(key_path)
                console.print(f"[green]{message}[/green]")

                public_key = get_public_key(key_path)
                if public_key:
                    console.print("\n[bold]New public key (update on GitHub/GitLab):[/bold]")
                    display_public_key(public_key)

                ssh_success, ssh_message = add_ssh_config_entry(name, key_path)
                if ssh_success:
                    console.print(f"[green]{ssh_message}[/green]")

                if Confirm.ask("Add key to ssh-agent?", default=True):
                    agent_success, agent_message = add_key_to_agent(key_path)
                    if agent_success:
                        console.print(f"[green]{agent_message}[/green]")
            else:
                console.print(f"[yellow]Warning: {message}[/yellow]")
    else:
        # No existing key - offer to generate one
        generate_ssh = ssh if ssh is not None else Confirm.ask("Generate SSH key?", default=False)
        if generate_ssh:
            key_path = get_ssh_dir() / f"id_ed25519_{name}"
            success, message = generate_ssh_key(new_email, key_path)

            if success:
                profile["ssh_key"] = str(key_path)
                console.print(f"[green]{message}[/green]")

                public_key = get_public_key(key_path)
                if public_key:
                    console.print("\n[bold]Public key (add to GitHub/GitLab):[/bold]")
                    display_public_key(public_key)

                ssh_success, ssh_message = add_ssh_config_entry(name, key_path)
                if ssh_success:
                    console.print(f"[green]{ssh_message}[/green]")

                if Confirm.ask("Add key to ssh-agent?", default=True):
                    agent_success, agent_message = add_key_to_agent(key_path)
                    if agent_success:
                        console.print(f"[green]{agent_message}[/green]")
            else:
                console.print(f"[yellow]Warning: {message}[/yellow]")

    # Save updated profile
    config.add_profile(name, profile)
    console.print(f"\n[green]Profile '{name}' updated successfully![/green]")

    # Show updated profile
    console.print(f"  Name:  {profile['name']}")
    console.print(f"  Email: {profile['email']}")
    if profile.get("ssh_key"):
        console.print(f"  SSH:   {profile['ssh_key']}")


@app.command("remove", help="Remove a profile.")
def remove_profile(
    name: str = typer.Argument(..., help="Profile name to remove"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
    delete_key: bool = typer.Option(False, "--delete-key", "-d", help="Also delete SSH key"),
) -> None:
    """Remove a profile."""
    profile = config.get_profile(name)

    if not profile:
        console.print(f"[red]Profile '{name}' not found.[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Profile: {name}[/bold]")
    console.print(f"  Name:  {profile.get('name')}")
    console.print(f"  Email: {profile.get('email')}")
    if profile.get("ssh_key"):
        console.print(f"  SSH:   {profile.get('ssh_key')}")

    if not force and not Confirm.ask("\nAre you sure you want to remove this profile?", default=False):
        console.print("[dim]Cancelled.[/dim]")
        raise typer.Exit(0)

    # Handle SSH key deletion
    if profile.get("ssh_key"):
        should_delete = delete_key or (not force and Confirm.ask("Also delete the SSH key?", default=False))
        if should_delete:
            key_path = Path(profile["ssh_key"])
            success, message = delete_ssh_key(key_path)
            if success:
                console.print(f"[green]{message}[/green]")
            else:
                console.print(f"[yellow]Warning: {message}[/yellow]")

            # Remove from SSH config
            ssh_success, ssh_message = remove_ssh_config_entry(name)
            if ssh_success:
                console.print(f"[green]{ssh_message}[/green]")

    # Remove profile
    config.remove_profile(name)
    console.print(f"[green]Profile '{name}' removed.[/green]")


@app.command("current", help="Show the current active profile.")
def current_profile() -> None:
    """Show the current active profile."""
    name, email = get_current_git_user()

    if not name or not email:
        console.print("[yellow]No git user configured globally.[/yellow]")
        raise typer.Exit(1)

    profiles = config.list_profiles()
    current = detect_current_profile(profiles)

    if current:
        profile = profiles[current]
        console.print(f"[bold cyan]{current}[/bold cyan]")
        console.print(f"  Name:  {name}")
        console.print(f"  Email: {email}")
        if profile.get("ssh_key"):
            console.print(f"  SSH:   {profile.get('ssh_key')}")
    else:
        console.print("[yellow]Current git config doesn't match any profile:[/yellow]")
        console.print(f"  Name:  {name}")
        console.print(f"  Email: {email}")


# =============================================================================
# Short aliases (single letter commands)
# =============================================================================

@app.command("l", hidden=True)
def _alias_list() -> None:
    """Alias for 'list'."""
    list_profiles()


@app.command("a", hidden=True)
def _alias_add(
    name: str = typer.Argument(...),
    user_name: Optional[str] = typer.Option(None, "--name", "-n"),
    email: Optional[str] = typer.Option(None, "--email", "-e"),
    ssh: Optional[bool] = typer.Option(None, "--ssh/--no-ssh", "-s/-S"),
) -> None:
    """Alias for 'add'."""
    add_profile(name, user_name, email, ssh)


@app.command("e", hidden=True)
def _alias_edit(
    name: str = typer.Argument(...),
    user_name: Optional[str] = typer.Option(None, "--name", "-n"),
    email: Optional[str] = typer.Option(None, "--email", "-e"),
    ssh: Optional[bool] = typer.Option(None, "--ssh/--no-ssh", "-s/-S"),
) -> None:
    """Alias for 'edit'."""
    edit_profile(name, user_name, email, ssh)


@app.command("u", hidden=True)
def _alias_use(name: str = typer.Argument(...)) -> None:
    """Alias for 'use'."""
    use_profile(name)


@app.command("r", hidden=True)
def _alias_remove(
    name: str = typer.Argument(...),
    force: bool = typer.Option(False, "--force", "-f"),
    delete_key: bool = typer.Option(False, "--delete-key", "-d"),
) -> None:
    """Alias for 'remove'."""
    remove_profile(name, force, delete_key)


@app.command("c", hidden=True)
def _alias_current() -> None:
    """Alias for 'current'."""
    current_profile()


if __name__ == "__main__":
    app()
