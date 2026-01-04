# git-switch

A CLI tool to manage and switch between multiple git user profiles (personal, work, etc.) with SSH key management.

## Installation

```bash
pip install -e .
```

## Usage

### Interactive Mode (default)

Simply run `git-switch` to see all profiles and select one:

```bash
git-switch
```

```
Git Profiles
OS: darwin

┏━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
┃ #   ┃ Profile ┃ Name          ┃ Email            ┃ SSH Key         ┃ Current ┃
┡━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
│ 1   │ perso   │ John Doe      │ john@personal.com│ id_ed25519_per… │    ●    │
│ 2   │ work    │ John Doe      │ john@company.com │ id_ed25519_work │         │
└─────┴─────────┴───────────────┴──────────────────┴─────────────────┴─────────┘

Select profile number [1/2] (1):
```

### Commands

| Command | Shortcut | Description |
|---------|----------|-------------|
| `git-switch` | - | Interactive profile picker |
| `git-switch list` | `l` | List all profiles |
| `git-switch add <name>` | `a` | Add a new profile |
| `git-switch edit <name>` | `e` | Edit an existing profile |
| `git-switch use <name>` | `u` | Switch to a profile |
| `git-switch remove <name>` | `r` | Remove a profile |
| `git-switch current` | `c` | Show current profile |

### Add a Profile

```bash
# Interactive
git-switch add work

# With options (no prompts)
git-switch add work -n "John Doe" -e "john@company.com" --ssh

# Without SSH key
git-switch add work -n "John Doe" -e "john@company.com" --no-ssh
```

**Options:**
- `-n, --name` - Git user name
- `-e, --email` - Git email
- `-s, --ssh` - Generate SSH key
- `-S, --no-ssh` - Skip SSH key generation

### Edit a Profile

```bash
# Interactive
git-switch edit work

# Update name and email
git-switch edit work -n "New Name" -e "new@email.com"

# Regenerate SSH key
git-switch edit work --ssh

# Edit without touching SSH
git-switch edit work -n "New Name" --no-ssh
```

**Options:**
- `-n, --name` - New git user name
- `-e, --email` - New git email
- `-s, --ssh` - Generate/regenerate SSH key
- `-S, --no-ssh` - Skip SSH key prompt

### Switch Profile

```bash
git-switch use work
# or
git-switch u work
```

### Remove a Profile

```bash
# Interactive (asks for confirmation)
git-switch remove work

# Force remove (no confirmation)
git-switch remove work -f

# Also delete SSH key
git-switch remove work -f -d
```

**Options:**
- `-f, --force` - Skip confirmation
- `-d, --delete-key` - Also delete SSH key files

## SSH Key Management

When creating or editing a profile, you can generate an Ed25519 SSH key. The tool will:

1. Generate a new key at `~/.ssh/id_ed25519_<profile>`
2. Display the public key (for adding to GitHub/GitLab)
3. Add an entry to `~/.ssh/config` with alias `github-<profile>`
4. Optionally add the key to ssh-agent

### Using SSH Aliases

After creating a profile with SSH, use the alias in your git remotes:

```bash
# Clone with specific profile's SSH key
git clone git@github-work:username/repo.git
git clone git@github-perso:username/repo.git

# Or update existing remote
git remote set-url origin git@github-work:username/repo.git
```

## Configuration

Profiles are stored in `~/.git-switch-profiles.json`:

```json
{
  "profiles": {
    "perso": {
      "name": "John Doe",
      "email": "john@personal.com",
      "ssh_key": "/Users/john/.ssh/id_ed25519_perso"
    },
    "work": {
      "name": "John Doe",
      "email": "john@company.com",
      "ssh_key": "/Users/john/.ssh/id_ed25519_work"
    }
  }
}
```

## Requirements

- Python 3.9+
- Git
- ssh-keygen (for SSH key generation)
