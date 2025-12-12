# Johnny Decimal Alfred Workflow

An Alfred workflow for navigating and managing a [Johnny Decimal](https://johnnydecimal.com/) system.

## Features

- **Browse** your JD hierarchy (Areas → Categories → IDs)
- **Search** by name across all levels or filtered by level
- **Create** new ID folders with smart slot suggestions
- **Rebuild** the index when your filesystem changes

## Installation

1. Clone or download this repository
2. Symlink to Alfred's workflow folder:
   ```bash
   ln -s /path/to/alfred_jd ~/Library/Application\ Support/Alfred/Alfred.alfredpreferences/workflows/alfred-jd
   ```
3. Configure the workflow in Alfred Preferences (see Configuration below)

## Keywords

| Keyword | Description |
|---------|-------------|
| `jd` | Browse and search your JD system |
| `j` / `jdi` | Search IDs only |
| `jdc` | Search categories only |
| `jda` | Search areas only |
| `jdn` | Create a new JD folder |
| `jdb` | Rebuild the index |

## Actions

| Key | Action |
|-----|--------|
| `Enter` | Open folder in Finder |
| `Cmd+Enter` | Browse in Alfred |
| `Alt+Enter` | Copy path to clipboard |
| `Ctrl+Enter` | Open in Terminal |

## Configuration

Set these in Alfred Preferences → Workflows → Johnny Decimal → Configure:

| Variable | Default | Description |
|----------|---------|-------------|
| `JD_ROOT` | `~/Documents` | Root folder of your JD system |
| `JD_INDEX` | `~/.config/jd/index.json` | Path to the index file |

## Command Line Usage

The browse script also works from the command line:

```bash
# Search all levels
python3 jd_browse.py "health"

# Filter by level
python3 jd_browse.py -l id "inbox"
python3 jd_browse.py -l category "me"
python3 jd_browse.py -l area "life"

# Show help
python3 jd_browse.py --help
```

## File Structure

```
alfred_jd/
├── info.plist        # Alfred workflow manifest
├── jd_browse.py      # Browse and search script
├── jd_new.py         # New folder creation script
├── jd_build.py       # Index rebuild script
├── jd_core.py        # Core JD operations (index, paths, IDs)
├── jd_alfred.py      # Alfred JSON output helpers
└── icons/            # Workflow icons
```

## Requirements

- Python 3.10+
- Alfred 5 with Powerpack
- macOS

## License

MIT
