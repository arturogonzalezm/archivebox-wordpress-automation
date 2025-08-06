# ArchiveBox WordPress Site Automation

A comprehensive solution for creating monthly visual snapshots of WordPress client sites, providing "time travel" capabilities to see how sites looked at any point in history.

## 🎯 Purpose & Problem Solved

When managing multiple WordPress sites for clients, common issues include:
- Clients accidentally breaking their sites
- Content being deleted or modified without record
- No visual proof of how the site looked at a specific date
- Difficulty explaining to clients what changed and when
- Need for evidence in disputes or for compliance

This tool creates automatic monthly visual archives of all your WordPress sites, allowing you to:
- Browse how any site looked at any point in time
- Recover lost content (text, images, layouts)
- Show clients exactly what changed
- Maintain compliance/legal documentation
- Track visual evolution of sites over time

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────┐
│         WordPress Sites (Live)              │
├──────────────┬──────────────────────────────┤
│ Site 1       │ Site 2       │ Site 3       │
│ burgis.de    │ arturo.com   │ feigen.de    │
└──────┬───────┴──────┬───────┴───────┬──────┘
       │              │                │
       └──────────────┼────────────────┘
                      │
                 (Monthly Cron)
                      │
                      ▼
        ┌──────────────────────────┐
        │  ArchiveBox Automation   │
        │    Python Script          │
        └────────────┬──────────────┘
                     │
                     ▼
        ┌──────────────────────────┐
        │    ArchiveBox Core       │
        │  - Screenshots           │
        │  - PDF Exports           │
        │  - HTML/CSS/JS           │
        │  - WARC Files            │
        └────────────┬──────────────┘
                     │
                     ▼
        ┌──────────────────────────┐
        │   Archive Storage        │
        │  srv/archivebox/         │
        │  - Tagged by month       │
        │  - Searchable            │
        │  - Browseable            │
        └──────────────────────────┘
```

## 📋 Prerequisites

- Python 3.11+
- Linux/Mac OS (Windows via WSL)
- 10-50GB storage (depending on number of sites)
- Chrome/Chromium (for screenshots)
- Basic command line knowledge

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/arturogonzalezm/archivebox-wordpress-automation.git
cd archivebox-wordpress-automation

# Create virtual environment (recommended)
python3.11 -m venv .venv
source .venv/bin/activate  # On Mac/Linux
# OR
.venv\Scripts\activate  # On Windows

# Install dependencies
pip install click pyyaml archivebox

# Make setup script executable
chmod +x setup_cron.sh

# Run automated setup
./setup_cron.sh
```

### 2. Initialise ArchiveBox

```bash
# Initialise the ArchiveBox environment
python3.11 archivebox_automation.py init
```

### 3. Configure Your Sites

Edit `sites_config.yaml` with your WordPress sites:

```yaml
sites:
  - name: "Client Site Name"
    url: "https://example.com/"
    client: "Client Name"
    monthly_snapshot: true
    depth: 1  # How many links deep to archive
    archive_subpages:
      - "contact"
      - "about"
      - "services"
```

Or use the simpler `srv/archivebox/urls.txt`:
```
https://example.com
https://another-site.com
https://third-site.com
```

### 4. Run Initial Archive

```bash
# Create your first baseline snapshot
python3.11 archivebox_automation.py schedule

# View the archives
python3.11 archivebox_automation.py server
# Open browser to http://localhost:8001
```

## 📚 Complete Command Reference

### Core Commands

| Command | Description                       | Example |
|---------|-----------------------------------|---------|
| `init` | Initialise ArchiveBox environment | `python3.11 archivebox_automation.py init` |
| `add` | Archive a single URL              | `python3.11 archivebox_automation.py add https://site.com` |
| `bulk` | Archive all sites from config     | `python3.11 archivebox_automation.py bulk` |
| `schedule` | Run monthly snapshot routine      | `python3.11 archivebox_automation.py schedule` |
| `server` | Start web interface               | `python3.11 archivebox_automation.py server` |
| `status` | Show system status                | `python3.11 archivebox_automation.py status` |
| `list` | List archived snapshots           | `python3.11 archivebox_automation.py list` |
| `cleanup` | Remove old snapshots              | `python3.11 archivebox_automation.py cleanup --days 180` |
| `compare` | Compare snapshots between dates   | `python3.11 archivebox_automation.py compare https://site.com 2024-01 2024-12` |

### Command Options

#### `add` Command Options
```bash
python3.11 archivebox_automation.py add <URL> [OPTIONS]
  --index-only              # Add to index without archiving
  --depth INTEGER           # Crawl depth (default: 1)
  --tag TEXT               # Add tags (can use multiple)

# Examples:
python3.11 archivebox_automation.py add https://burgis.de --depth 2 --tag "before-update" --tag "critical"
```

#### `list` Command Options
```bash
python3.11 archivebox_automation.py list [OPTIONS]
  --client TEXT            # Filter by client name
  --month TEXT            # Filter by month (YYYY-MM)
  --format [text|json|csv] # Output format

# Examples:
python3.11 archivebox_automation.py list --month 2024-12
python3.11 archivebox_automation.py list --client "Burgis" --format json
```

#### `cleanup` Command Options
```bash
python3.11 archivebox_automation.py cleanup [OPTIONS]
  --days INTEGER          # Keep snapshots from last N days
  --keep-monthly         # Always keep first snapshot of each month
  --dry-run             # Preview what would be deleted

# Examples:
python3.11 archivebox_automation.py cleanup --days 90 --keep-monthly --dry-run
```

#### `server` Command Options
```bash
python3.11 archivebox_automation.py server [OPTIONS]
  --port INTEGER         # Port to run server on (default: 8001)
  --host TEXT           # Host to bind to (default: 0.0.0.0)

# Examples:
python3.11 archivebox_automation.py server --port 8080
```

## 🔄 WordPress Integration Strategy

### Complementary Backup Approach

This tool works **alongside** WordPress backup plugins, not as a replacement:

| Tool | Purpose | Restore Capability | Use Case |
|------|---------|-------------------|----------|
| **ArchiveBox** | Visual archives | Browse/view only | See how site looked, recover content |
| **UpdraftPlus** | Full WP backup | Complete restore | Restore broken WordPress |
| **BackWPup** | Database/files | Complete restore | Restore functionality |
| **ArchiveBox + WP Backup** | Complete solution | Full + Visual | Best protection |

### Recommended WordPress Plugin Stack

1. **UpdraftPlus** (Free/Premium)
   - Automated WordPress backups
   - One-click restoration
   - Remote storage (Google Drive, S3)
   - Handles database + files

2. **WP Activity Log** (Free)
   - Track who changed what
   - Identify when issues occurred
   - Complement ArchiveBox timestamps

3. **MainWP** (For Agencies)
   - Centralised management
   - Bulk updates tracking
   - Coordinate with ArchiveBox schedule

## 📅 Workflows

### Initial Setup Workflow

```bash
# 1. Install dependencies
pip install click pyyaml archivebox

# 2. Initialise environment
python3.11 archivebox_automation.py init

# 3. Configure sites
nano sites_config.yaml

# 4. Test with one site
python3.11 archivebox_automation.py add https://test-site.com --tag initial

# 5. Run full archive
python3.11 archivebox_automation.py schedule

# 6. View results
python3.11 archivebox_automation.py server
```

### Monthly Automated Workflow

1. **1st of Month, 2:00 AM**: Cron triggers `schedule` command
2. **Archive Process**:
   - Reads sites from `sites_config.yaml`
   - Archives each site with monthly tag
   - Captures screenshots, PDFs, HTML
   - Logs results to `logs/archivebox_monthly.log`
3. **Storage**: Saves with tags like `snapshot-2024-12`
4. **Notification**: Optional email/Slack alert

### Emergency Archive Workflow

When a client is about to make major changes:

```bash
# 1. Create pre-change snapshot
python3.11 archivebox_automation.py add https://client-site.com \
  --tag "before-redesign" \
  --tag "2024-12-15" \
  --depth 2

# 2. Let client make changes

# 3. Create post-change snapshot
python3.11 archivebox_automation.py add https://client-site.com \
  --tag "after-redesign" \
  --tag "2024-12-16" \
  --depth 2

# 4. Compare if needed
python3.11 archivebox_automation.py server
# Browse both snapshots in web UI
```

### Disaster Recovery Workflow

When a client says "our site is broken":

```bash
# 1. Check when the last good snapshot was
python3.11 archivebox_automation.py list --client "ClientName"

# 2. View the archive
python3.11 archivebox_automation.py server
# Navigate to http://localhost:8001
# Search for the client's site
# Browse snapshots to find last good version

# 3. Recovery options:
#    a) Show client the old version for reference
#    b) Extract specific content (text, images)
#    c) Use HTML/CSS for layout reference
#    d) Coordinate with UpdraftPlus for full restore
```

### New Client Onboarding

```bash
# 1. Add to configuration
nano sites_config.yaml

# 2. Create initial baseline
python3.11 archivebox_automation.py add https://newclient.com \
  --tag "onboarding" \
  --tag "baseline" \
  --depth 2

# 3. Verify archive
python3.11 archivebox_automation.py list --client "New Client"

# 4. Site is now in monthly rotation
```

## 🗂️ File Structure

```
archivebox-wordpress-automation/
├── archivebox_automation.py    # Main automation script
├── sites_config.yaml           # Sites configuration
├── setup_cron.sh              # Setup script
├── README.md                  # This file
├── srv/
│   └── archivebox/           # Archive data directory
│       ├── archive/          # Actual snapshots
│       ├── index.sqlite3     # Archive database
│       └── urls.txt         # Simple URL list (backup)
└── logs/
    └── archivebox_monthly.log # Execution logs
```

## 🏷️ Tagging System

Tags help organise and find snapshots:

- **Automatic Tags**:
  - `snapshot-YYYY-MM` - Monthly snapshots
  - `client:ClientName` - Client identifier
  - `site:SiteName` - Site identifier

- **Manual Tags**:
  - `before-update`, `after-update`
  - `emergency-backup`
  - `baseline`, `onboarding`
  - `hacked-recovery`
  - Custom tags for special events

## ⏰ Cron Setup

The setup script automatically adds a cron job, but you can manage it manually:

```bash
# View current cron jobs
crontab -l

# Edit cron jobs
crontab -e

# Add this line for monthly snapshots (1st of month at 2 AM)
0 2 1 * * cd /path/to/script && python3.11 archivebox_automation.py schedule >> logs/archivebox_monthly.log 2>&1

# For weekly snapshots (every Sunday at 2 AM)
0 2 * * 0 cd /path/to/script && python3.11 archivebox_automation.py schedule >> logs/archivebox_weekly.log 2>&1

# For daily snapshots (every day at 2 AM)
0 2 * * * cd /path/to/script && python3.11 archivebox_automation.py schedule >> logs/archivebox_daily.log 2>&1
```

## 🔧 Advanced Configuration

### Custom Extractors per Site

```yaml
sites:
  - name: "JavaScript Heavy Site"
    url: "https://spa-site.com/"
    extractors:
      - singlefile  # Better for SPAs
      - screenshot
      - dom        # Capture DOM state
```

### Depth Settings

- `depth: 0` - Homepage only
- `depth: 1` - Homepage + directly linked pages (recommended)
- `depth: 2` - Include secondary level pages
- `depth: 3+` - Deep archive (large storage required)

### Storage Optimisation

```yaml
archive:
  retention_days: 365        # Keep for 1 year
  keep_monthly_first: true   # Never delete first of month
  compression: true          # Compress old snapshots
```

## 📊 Monitoring & Maintenance

### Daily Health Check

Add to crontab:
```bash
0 9 * * * python3.11 /path/to/archivebox_automation.py status || \
  echo "ArchiveBox issue detected" | mail -s "Archive Alert" admin@example.com
```

### Check Logs

```bash
# View real-time logs
tail -f logs/archivebox_monthly.log

# Check for errors
grep -i error logs/archivebox_monthly.log

# View last run
tail -n 50 logs/archivebox_monthly.log
```

### Storage Management

```bash
# Check storage usage
du -sh srv/archivebox/

# Count snapshots per client
python3.11 archivebox_automation.py list --format json | \
  jq '.[] | select(.tags | contains(["client:Burgis"]))' | wc -l

# Quarterly cleanup
python3.11 archivebox_automation.py cleanup --days 180 --keep-monthly
```

## 🚨 Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| "Chrome not found" | Install: `sudo apt install chromium-browser` |
| "Timeout errors" | Increase timeout in sites_config.yaml |
| "Disk space full" | Run cleanup command or increase storage |
| "Cron not running" | Check: `grep CRON /var/log/syslog` |
| "Can't access web UI" | Check firewall, ensure port 8001 is open |
| "Permission denied" | Check file permissions: `chmod +x archivebox_automation.py` |
| "Module not found" | Activate venv: `source .venv/bin/activate` |

### Debug Mode

```bash
# Verbose output
PYTHONPATH=. python3.11 -m pdb archivebox_automation.py schedule

# Check ArchiveBox directly
cd srv/archivebox
archivebox status
archivebox list
cd ../..

# Verify dependencies
pip list | grep -E "archivebox|click|pyyaml"

# Test with single URL
python3.11 archivebox_automation.py add https://example.com --tag debug
```

## 🔒 Security Considerations

1. **Access Control**: Web interface has no authentication by default
   - Use firewall rules
   - Set up reverse proxy with auth (nginx/Apache)
   - Or keep local-only access

2. **Storage**: Archives may contain sensitive data
   - Encrypt srv/archivebox directory
   - Regular backups to secure location
   - Limit access permissions: `chmod 700 srv/archivebox`

3. **Client Privacy**: 
   - Separate archives per client if needed
   - Consider data retention policies
   - GDPR compliance for EU clients

## 📈 Scaling Considerations

### For 10-50 Sites
- Current setup works well
- ~20-100GB storage needed
- Monthly runs take 1-4 hours

### For 50+ Sites
- Consider multiple ArchiveBox instances
- Implement parallel processing: `bulk --parallel`
- Use dedicated archive server
- Set up CDN for serving archives

### Storage Estimates
- Small site (20 pages): ~50MB per snapshot
- Medium site (100 pages): ~200MB per snapshot
- Large site (500+ pages): ~1GB per snapshot
- Monthly storage: Sites × Size × 12 months

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch
3. Add tests if applicable
4. Submit pull request

## 📄 License

MIT License - See LICENSE file for details

## 🆘 Support

- GitHub Issues: [Report bugs](https://github.com/yourusername/archivebox-wordpress-automation/issues)
- ArchiveBox Docs: [archivebox.io](https://archivebox.io)
- WordPress Backup Guide: [WordPress.org backup docs](https://wordpress.org/support/article/wordpress-backups/)

## 🎯 Quick Reference Card

```bash
# Essential Commands - Print and keep handy!

# Take snapshot NOW
python3.11 archivebox_automation.py add https://site.com --tag "emergency"

# View archives
python3.11 archivebox_automation.py server
# Browse: http://localhost:8001

# Run monthly archive manually
python3.11 archivebox_automation.py schedule

# Check what's archived
python3.11 archivebox_automation.py list --month $(date +%Y-%m)

# System status
python3.11 archivebox_automation.py status

# Quick cleanup (keep last 6 months)
python3.11 archivebox_automation.py cleanup --days 180 --keep-monthly
```

## 📝 Example Configuration Files

### sites_config.yaml
```yaml
sites:
  - name: "Burgis DE"
    url: "https://burgis.de/"
    client: "Burgis"
    monthly_snapshot: true
    depth: 1
    archive_subpages:
      - "produkte"
      - "kontakt"
    extractors:
      - screenshot
      - pdf
      - wget
    
  - name: "Arturo Solutions"
    url: "https://arturosolutions.com/"
    client: "Arturo"
    monthly_snapshot: true
    depth: 1
    archive_subpages:
      - "portfolio"
      - "services"
    
  - name: "Nordfrost Karriere"
    url: "https://karriere.nordfrost.de/"
    client: "Nordfrost"
    monthly_snapshot: true
    depth: 2

defaults:
  depth: 1
  timeout: 60
  extractors:
    - screenshot
    - pdf
    - wget
```

- depth: 0 = Only the homepage
- depth: 1 = Homepage + ALL pages linked from homepage (usually enough!)
- depth: 2 = Homepage + linked pages + pages linked from those pages
- depth: 3+ = Goes even deeper (can be hundreds of pages)

Note:
- archive_subpages: Specific pages to guarantee capture (e.g., contact, about)
- Just use depth: 1 and ArchiveBox will automatically find and archive pages
- Only use archive_subpages for specific critical pages you want to guarantee are captured
- Start simple, adjust if needed

### srv/archivebox/urls.txt
```
https://arturosolutions.com/
https://burgis.de/
https://karriere.nordfrost.de/
https://feigen-graf.de/
# Add more URLs here, one per line
```

---

**Remember**: ArchiveBox creates *visual archives* for reference and content recovery. Always use proper WordPress backup plugins (UpdraftPlus, BackWPup) for full site restoration capabilities. This tool complements, not replaces, traditional backups!