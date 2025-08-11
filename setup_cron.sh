#!/bin/bash
set -e

# -----------------------------------------------------------------------------
# Setup script for automated monthly WordPress archiving with ArchiveBox
# -----------------------------------------------------------------------------

# Resolve script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_SCRIPT="$SCRIPT_DIR/archivebox_automation.py"
ARCHIVEBOX_DIR="$SCRIPT_DIR/srv/archivebox"
LOG_DIR="$SCRIPT_DIR/logs"

# Create necessary directories
mkdir -p "$ARCHIVEBOX_DIR"
mkdir -p "$LOG_DIR"

# --- Install system dependencies: Node.js, npm, wget if missing ---
echo "Checking for Node.js and npm..."
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "Node.js or npm not found. Attempting to install via package manager..."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y nodejs npm
  elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y nodejs npm
  else
    echo "Please install Node.js and npm manually. Exiting."
    exit 1
  fi
fi

# Check for wget and install if missing
echo "Checking for wget..."
if ! command -v wget >/dev/null 2>&1; then
  echo "wget not found. Attempting to install via package manager..."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get install -y wget
  elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y wget
  elif command -v brew >/dev/null 2>&1; then
    brew install wget
  else
    echo "Please install wget manually. It is required for ArchiveBox to function properly."
    exit 1
  fi
fi

# --- Install Python dependencies ---
echo "Installing Python dependencies..."
pip3 install --upgrade click pyyaml archivebox

# --- Cleanup any old extractor installs ---
echo "Cleaning up old extractor installs (if any)..."
npm uninstall -g --no-audit --no-fund \
  readability-extractor \
  @postlight/parser @postlight/mercury-parser \
  single-file || true

# --- Install ArchiveBox extractors via npm ---
echo "Installing Readability, Postlight (parser), and SingleFile extractors..."
npm install --global --no-audit --no-fund \
  git+https://github.com/ArchiveBox/readability-extractor.git \
  @postlight/parser \
  git+https://github.com/gildas-lormeau/SingleFile.git

# Symlink `postlight-parser` if ArchiveBox still expects it
if ! command -v postlight-parser >/dev/null 2>&1 && command -v parser >/dev/null 2>&1; then
  echo "Creating symlink: postlight-parser -> parser"
  sudo ln -sf "$(command -v parser)" /usr/local/bin/postlight-parser
fi

# Symlink `single-file` if needed (CLI may install as 'singlefile')
if ! command -v single-file >/dev/null 2>&1 && command -v singlefile >/dev/null 2>&1; then
  echo "Creating symlink: single-file -> singlefile"
  sudo ln -sf "$(command -v singlefile)" /usr/local/bin/single-file
fi

# --- Initialize ArchiveBox ---
echo "Initializing ArchiveBox..."
python3 "$PYTHON_SCRIPT" --data-dir "$ARCHIVEBOX_DIR" init

# --- Setup cron job for monthly snapshots ---
echo "Configuring cron job for monthly snapshots..."
CRON_CMD="0 2 1 * * cd $SCRIPT_DIR && /usr/bin/python3 $PYTHON_SCRIPT --data-dir $ARCHIVEBOX_DIR schedule >> $LOG_DIR/archivebox_monthly.log 2>&1"
(
  crontab -l 2>/dev/null | grep -v "$PYTHON_SCRIPT" ;
  echo "$CRON_CMD"
) | crontab -

echo "Cron job added. Monthly snapshots will run on the 1st of each month at 2 AM."

echo "Current cron entries:"
crontab -l | grep "$PYTHON_SCRIPT"

# --- Optional: Create systemd service for ArchiveBox web interface ---
cat > "$SCRIPT_DIR/archivebox-web.service" << EOF
[Unit]
Description=ArchiveBox Web Interface
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=/usr/bin/python3 $PYTHON_SCRIPT --data-dir $ARCHIVEBOX_DIR server --port 8001
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

echo "Systemd service file created: $SCRIPT_DIR/archivebox-web.service"
echo "To enable and start it, run:"
echo "  sudo cp $SCRIPT_DIR/archivebox-web.service /etc/systemd/system/"
echo "  sudo systemctl enable archivebox-web"
echo "  sudo systemctl start archivebox-web"
