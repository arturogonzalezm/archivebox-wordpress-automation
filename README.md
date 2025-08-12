# ArchiveBox WordPress Automation

A tool for archiving and recovering hundreds of WordPress websites using ArchiveBox.

## Overview

This tool automates the process of archiving WordPress websites using ArchiveBox. Its goal in this project is to capture website snapshots for viewing how sites looked in the past; backup/restore of live sites is out of scope and handled by a separate application. It provides:

- Configuration-based site management
- Scheduled monthly snapshots
- Retention policies for efficient storage
- Notification system (email and Slack)
- Web interface for browsing archives

## Key Components

- `archivebox_automation.py`: Main Python CLI tool
- `sites_config.yaml`: Configuration file for sites and settings
- `setup_cron.sh`: Setup script for dependencies and scheduling
- `srv/archivebox/`: Directory for ArchiveBox data

## Usage

### Per-website snapshots (separate instances)

You can archive a snapshot per website into its own ArchiveBox instance. This keeps each site's archives isolated with their own index and UI.

Ways to enable per-site archiving:
- CLI: use the --per-site flag with bulk
  python3.11 archivebox_automation.py bulk --per-site
- Config: set archive.per_site: true in sites_config.yaml and run bulk normally

Per-site data directories are created under your data-dir (default srv/archivebox) using a slugified site name, e.g. srv/archivebox/example-site/.

You can also target a single per-site instance when serving or generating links:
- Serve a specific site instance:
  python3.11 archivebox_automation.py server --site "Example Site" --port 8001
- Generate a snapshot link from a specific site instance:
  python3.11 archivebox_automation.py snapshot_link https://example.com --site "Example Site" --months-ago 2 --server-base http://localhost:8001

### Dependencies

This tool requires the following system dependencies:
- Node.js and npm (for extractors)
- wget (for downloading web content)
- Python 3.x with pip
- Chromium or Google Chrome (for screenshot and PDF generation)

The setup script will attempt to install most dependencies automatically. For Chromium/Chrome, you'll need to install it manually if it's not already available. The tool will automatically detect and use Chrome if Chromium is not found, or disable screenshot and PDF extractors if neither browser is available.

### Extractors

The following extractors are used by default:
- Screenshot (if Chromium/Chrome is available)
- PDF (if Chromium/Chrome is available)
- wget (if installed)
- SingleFile (for sites that specify it)

**Note:** The readability, mercury/postlight, and htmltotext extractors are disabled by default to avoid common parsing failures (e.g., JSON errors, "Extractor failed: Mercury was not able to get article text from the URL", and "htmltotext could not find HTML to parse"). The tool automatically removes legacy `--without-readability` and `--without-mercury` CLI flags (not supported in newer ArchiveBox) while setting the appropriate options in ArchiveBox.conf to keep these extractors off.

### Initial Setup

```bash
# Run the setup script to install dependencies and configure cron job
chmod +x setup_cron.sh
./setup_cron.sh
```

### Commands

```bash
# Initialize ArchiveBox environment
python3.11 archivebox_automation.py init

# Add a single URL
python3.11 archivebox_automation.py add https://example.com

# Archive all configured sites
python3.11 archivebox_automation.py bulk

python3.11 archivebox_automation.py bulk --parallel

python3.11 archivebox_automation.py status

# Run scheduled archiving (with cleanup)
python3.11 archivebox_automation.py schedule

# Clean up old snapshots
python3.11 archivebox_automation.py cleanup --days=180 --keep-monthly

# Start web server
python3.11 archivebox_automation.py server

# Get a link to the snapshot nearest to a specific date (for viewing-only use cases)
python3.11 archivebox_automation.py snapshot_link https://example.com --months-ago 2 --server-base http://localhost:8001
# or with explicit date
python3.11 archivebox_automation.py snapshot_link https://example.com --date 2025-06 --server-base http://localhost:8001
# Without server-base, you'll get a relative /archive/<timestamp>/ and a local file path fallback

# Create a superuser for the web interface 
cd /srv/archivebox
archivebox manage createsuperuser
```

### Real-time Logging

The tool now displays command output in real-time when run interactively, making it easier to monitor progress. When run via cron, output is still saved to log files for later review.

Functions that parse command output (like `cleanup` and `status`) will still capture the output rather than displaying it in real-time.

## Recommendations

1. **Performance Optimization**:
   - Consider batching for very large numbers of sites
   - Add rate limiting options to avoid overloading servers

2. **Additional Features**:
   - Implement a reporting dashboard
   - Add prioritization for more frequent archiving of important sites

3. **Maintenance and Monitoring**:
   - Add disk space monitoring
   - Implement automatic compression of older archives

## Configuration

See `sites_config.yaml` for examples of site configuration, archive settings, and notification options.

---

**Remember**: ArchiveBox creates *visual archives* for reference and content recovery. Always use proper WordPress backup plugins (UpdraftPlus, BackWPup) for full site restoration capabilities. This tool complements, not replaces, traditional backups!