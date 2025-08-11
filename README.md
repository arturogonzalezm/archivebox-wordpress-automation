# ArchiveBox WordPress Automation

A tool for archiving and recovering hundreds of WordPress websites using ArchiveBox.

## Overview

This tool automates the process of archiving WordPress websites using ArchiveBox. It provides:

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

**Note:** The readability extractor is disabled by default due to JSON parsing issues. The tool automatically handles this by removing the `--without-readability` flag (which is not supported by the current version of ArchiveBox) while still ensuring the readability extractor is not used.

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

# Run scheduled archiving (with cleanup)
python3.11 archivebox_automation.py schedule

# Clean up old snapshots
python3.11 archivebox_automation.py cleanup --days=180 --keep-monthly

# Start web server
python3.11 archivebox_automation.py server

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