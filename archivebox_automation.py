import os
import sys
import subprocess
import datetime
import time
from pathlib import Path

import click
import yaml

# Default Configuration
DEFAULT_ARCHIVEBOX_DIR = os.path.join(os.getcwd(), 'srv', 'archivebox')
DEFAULT_CONFIG_FILE = 'sites_config.yaml'
PORT = 8001


@click.group()
@click.option('--data-dir', 'archivebox_dir', default=DEFAULT_ARCHIVEBOX_DIR,
              help='Path to ArchiveBox data directory')
@click.option('--binary', 'archivebox_bin', default=None,
              help='Path to ArchiveBox CLI binary (default: auto-detect)')
@click.option('--config', 'config_file', default=DEFAULT_CONFIG_FILE,
              help='Path to sites configuration file')
@click.pass_context
def cli(ctx, archivebox_dir, archivebox_bin, config_file):
    """ArchiveBox WordPress Sites Automation CLI"""
    archivebox_dir = os.path.abspath(archivebox_dir)
    ctx.ensure_object(dict)
    ctx.obj['ARCHIVEBOX_DIR'] = archivebox_dir
    ctx.obj['ARCHIVEBOX_BIN'] = archivebox_bin
    ctx.obj['URLS_FILE'] = os.path.join(archivebox_dir, 'urls.txt')
    ctx.obj['CONFIG_FILE'] = config_file
    ctx.obj['SITES_CONFIG'] = _load_sites_config(config_file)


def _load_sites_config(config_file):
    """Load sites configuration from YAML or fallback to urls.txt"""
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    return None


def _check_dependencies():
    """Check if required dependencies are installed"""
    dependencies = {
        'wget': 'wget is required for downloading web pages. Install with: brew install wget (macOS) or apt-get install wget (Linux)'
    }
    
    # Check for Chromium browser (used for screenshot and PDF extractors)
    chromium_paths = [
        '/Applications/Chromium.app/Contents/MacOS/Chromium',  # macOS
        '/usr/bin/chromium',                                   # Linux
        '/usr/bin/chromium-browser',                           # Some Linux distros
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'  # Chrome on macOS as fallback
    ]
    
    has_chromium = False
    for path in chromium_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            has_chromium = True
            break
    
    missing = []
    for cmd, message in dependencies.items():
        try:
            # Use 'which' command to check if dependency exists
            subprocess.run(['which', cmd], check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append((cmd, message))
    
    # Add Chromium to missing dependencies if not found
    if not has_chromium:
        missing.append(('chromium', 'Chromium or Chrome is required for screenshot and PDF generation. Install Chromium or Chrome browser.'))
    
    return missing

def _run(ctx, *args, stdin=None, capture_output=False):
    """Internal: Run ArchiveBox command without raising on errors"""
    # Check for missing dependencies if this is an 'add' command
    if args and args[0] == 'add':
        # Filter out unsupported flags
        new_args = list(args)
        removed_flags = []
        if '--without-readability' in new_args:
            new_args.remove('--without-readability')
            removed_flags.append("--without-readability")
            
        # Print message about removed flags
        if removed_flags:
            message = f"[*] Removed unsupported flag: {removed_flags[0]}"
            # Always print to console for real-time feedback
            print(message, file=sys.stdout)
            sys.stdout.flush()
            # Also store the message to be included in the result
            ctx.obj['REMOVED_FLAGS_MESSAGE'] = message
        
        # Check for missing dependencies
        missing_deps = _check_dependencies()
        if missing_deps:
            for cmd, message in missing_deps:
                click.echo(f"[!] Missing dependency: {cmd}")
                click.echo(f"    {message}")
            
            # Modify args to disable extractors that require missing dependencies
            for cmd, _ in missing_deps:
                if cmd == 'wget':
                    # Looking at the issue description, the correct flag is '--without-wget'
                    # But we need to check if it's already in the args to avoid duplicates
                    if '--without-wget' not in new_args:
                        new_args.append('--without-wget')
                elif cmd == 'chromium':
                    # Disable screenshot and PDF extractors if Chromium/Chrome is missing
                    if '--without-screenshot' not in new_args:
                        new_args.append('--without-screenshot')
                        click.echo(f"[!] Disabled screenshot extractor due to missing Chromium/Chrome")
                    if '--without-pdf' not in new_args:
                        new_args.append('--without-pdf')
                        click.echo(f"[!] Disabled PDF extractor due to missing Chromium/Chrome")
            click.echo(f"[*] Continuing with modified command (disabled missing extractors)")
        
        args = tuple(new_args)
    
    base_bin = ctx.obj['ARCHIVEBOX_BIN']
    if base_bin:
        cmd = [os.path.abspath(base_bin)] + list(args)
    else:
        cmd = ['archivebox'] + list(args)

    # Set up command execution parameters
    kwargs = {
        'cwd': ctx.obj['ARCHIVEBOX_DIR'],
        'check': False,
        'stdin': stdin,
        'text': True,
    }

    # If capture_output is explicitly requested, capture it
    # Otherwise show output in real-time
    if capture_output:
        kwargs['capture_output'] = True
    else:
        kwargs['stdout'] = None  # Use default stdout (terminal)
        kwargs['stderr'] = None  # Use default stderr (terminal)
        click.echo(f"[*] Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, **kwargs)
    except FileNotFoundError:
        # Fallback to Python module
        fallback = [sys.executable, '-m', 'archivebox'] + list(args)
        click.echo(f"[!] Binary not found, falling back to: {' '.join(fallback)}")

        # For fallback, always show output in real-time unless capture is requested
        if not capture_output:
            result = subprocess.run(fallback, **kwargs)
        else:
            result = subprocess.run(fallback, **kwargs)

    # For real-time output, we need to create a result-like object
    # since we didn't capture the output
    if not capture_output:
        if result.returncode != 0:
            click.echo(f"[!] Command failed (exit {result.returncode}): {' '.join(cmd)}")

        # Create a minimal result object with stdout/stderr
        class MinimalResult:
            def __init__(self, returncode, ctx):
                self.returncode = returncode
                # Include any removed flags message in stdout
                self.stdout = ctx.obj.get('REMOVED_FLAGS_MESSAGE', "") + "\n"
                self.stderr = ""

        return MinimalResult(result.returncode, ctx)

    # For captured output, handle as before
    if result.returncode != 0:
        click.echo(f"[!] Command failed (exit {result.returncode}): {' '.join(cmd)}")
        if result.stderr:
            click.echo(result.stderr.strip())
    
    # If we have a removed flags message, prepend it to stdout
    if 'REMOVED_FLAGS_MESSAGE' in ctx.obj:
        result.stdout = ctx.obj['REMOVED_FLAGS_MESSAGE'] + "\n" + result.stdout

    return result


@cli.command()
@click.pass_context
def init(ctx):
    """Initialise ArchiveBox environment (force if directory not empty)"""
    d = ctx.obj['ARCHIVEBOX_DIR']
    os.makedirs(d, exist_ok=True)
    _run(ctx, 'init', '--force')

    urls_file = ctx.obj['URLS_FILE']
    if not os.path.exists(urls_file):
        with open(urls_file, 'w') as f:
            f.write("# Add URLs here, one per line\n")

    config_file = ctx.obj['CONFIG_FILE']
    if not os.path.exists(config_file):
        _create_default_config(config_file)

    click.echo(f"Initialised ArchiveBox in {d}.")


def _create_default_config(config_file):
    # Check if wget is available
    has_wget = True
    try:
        subprocess.run(['which', 'wget'], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        has_wget = False
    
    # Check for Chromium browser (used for screenshot and PDF extractors)
    has_chromium = False
    chromium_paths = [
        '/Applications/Chromium.app/Contents/MacOS/Chromium',  # macOS
        '/usr/bin/chromium',                                   # Linux
        '/usr/bin/chromium-browser',                           # Some Linux distros
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'  # Chrome on macOS as fallback
    ]
    
    for path in chromium_paths:
        if os.path.exists(path) and os.access(path, os.X_OK):
            has_chromium = True
            break
    
    # Create default extractors list based on available dependencies
    default_extractors = []
    if has_chromium:
        default_extractors.extend(['screenshot', 'pdf'])
    else:
        click.echo("[!] Warning: Chromium/Chrome not found. Screenshot and PDF extractors will be disabled.")
    
    if has_wget:
        default_extractors.append('wget')
    
    # Extended extractors for example site
    example_extractors = default_extractors.copy()
    example_extractors.append('singlefile')
    
    default_config = {
        'sites': [{
            'name': 'Example Site',
            'url': 'https://example.com',
            'client': 'Example Client',
            'depth': 1,
            'archive_subpages': ['contact', 'about'],
            'monthly_snapshot': True,
            'extractors': example_extractors
        }],
        'defaults': {
            'depth': 1,
            'timeout': 60,
            'extractors': default_extractors
        }
    }
    with open(config_file, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False)
    click.echo(f"Created default config: {config_file}")


@cli.command()
@click.argument('url')
@click.option('--index-only/--no-index-only', 'index_only', default=False,
              help='Only add to index without running extractors')
@click.option('--depth', default=1, help='Crawl depth for the site')
@click.option('--tag', multiple=True, help='Tags to add to the snapshot')
@click.option('--without-wget', is_flag=True, help='Skip wget extractor')
@click.option('--without-singlefile', is_flag=True, help='Skip singlefile extractor')
@click.option('--without-dom', is_flag=True, help='Skip dom extractor')
@click.option('--without-readability', is_flag=True, default=True, help='Skip readability extractor (disabled by default due to JSON parsing issues)')
@click.option('--without-pdf', is_flag=True, help='Skip pdf extractor')
@click.option('--without-screenshot', is_flag=True, help='Skip screenshot extractor')
@click.pass_context
def add(ctx, url, index_only, depth, tag, without_wget, without_singlefile, 
        without_dom, without_readability, without_pdf, without_screenshot):
    """Add a single URL to ArchiveBox for archiving"""
    args = ['add', url, f'--depth={depth}']
    if index_only:
        args.append('--index-only')
    for t in tag:
        args.extend(['--tag', t])

    month_tag = f"snapshot-{datetime.datetime.now().strftime('%Y-%m')}"
    args.extend(['--tag', month_tag])
    
    # Add the --without-* flags if specified
    if without_wget:
        args.append('--without-wget')
    if without_singlefile:
        args.append('--without-singlefile')
    if without_dom:
        args.append('--without-dom')
    if without_readability:
        args.append('--without-readability')
    if without_pdf:
        args.append('--without-pdf')
    if without_screenshot:
        args.append('--without-screenshot')

    _run(ctx, *args)
    click.echo(f"Added URL: {url} (depth={depth}, tags={list(tag) + [month_tag]})")


@cli.command()
@click.option('--index-only/--no-index-only', 'index_only', default=False)
@click.option('--parallel/--sequential', default=False)
@click.pass_context
def bulk(ctx, index_only, parallel):
    """Add all URLs from urls.txt or config file to ArchiveBox"""
    sites_config = ctx.obj['SITES_CONFIG']
    urls_file = ctx.obj['URLS_FILE']
    has_yaml = sites_config and 'sites' in sites_config
    has_urls_file = os.path.isfile(urls_file)

    if not has_yaml and not has_urls_file:
        click.echo("No sites configured for archiving!")
        click.echo("Run 'init' to create default files, then configure sites.")
        return

    if has_yaml:
        sites = sites_config['sites']
        defaults = sites_config.get('defaults', {})
        for site in sites:
            if not site.get('monthly_snapshot', True):
                continue
            url = site['url']
            depth = site.get('depth', defaults.get('depth', 1))
            tags = [
                f"client:{site.get('client', 'unknown')}",
                f"site:{site.get('name', 'unknown')}",
                f"snapshot-{datetime.datetime.now().strftime('%Y-%m')}"
            ]
            click.echo(f"Archiving {site['name']} ({url})...")

            # Always disable readability extractor due to JSON parsing issues
            result = _run(ctx, 'add', url, f'--depth={depth}', '--without-readability', *sum((['--tag', t] for t in tags), []))
            if result.returncode != 0:
                click.echo(f"Skipping {site['name']} due to error.")
                continue

            for subpage in site.get('archive_subpages', []):
                sub_url = f"{url.rstrip('/')}/{subpage}"
                result = _run(ctx, 'add', sub_url, '--depth=0', '--without-readability', *sum((['--tag', t] for t in tags), []))
                if result.returncode != 0:
                    click.echo(f"  Skipping subpage {subpage} due to error.")
            if not parallel:
                time.sleep(2)
    else:
        with open(urls_file, 'r') as f:
            urls = [l.strip() for l in f if l.strip() and not l.startswith('#')]
        for url in urls:
            # Always disable readability extractor due to JSON parsing issues
            result = _run(ctx, 'add', url, f'--depth={1}', '--without-readability')
            if result.returncode != 0:
                click.echo(f"Skipping URL {url} due to error.")
                continue
            if not parallel:
                time.sleep(2)

    click.echo("Bulk archive complete.")


@cli.command(name='list')
@click.option('--client', help='Filter by client name')
@click.option('--month', help='Filter by month (YYYY-MM)')
@click.option('--format', 'output_format', type=click.Choice(['text', 'json', 'csv']),
              default='text')
@click.pass_context
def _list(ctx, client, month, output_format):
    args = ['list']
    if output_format == 'json':
        args.append('--json')
    elif output_format == 'csv':
        args.append('--csv')
    # Need to capture output to access stdout/stderr
    result = _run(ctx, *args, capture_output=True)
    click.echo(result.stdout or result.stderr)


@cli.command()
@click.option('--notify/--no-notify', default=True)
@click.option('--check-changes/--no-check-changes', default=False)
@click.option('--cleanup/--no-cleanup', default=True,
              help='Run cleanup after archiving based on retention settings')
@click.pass_context
def schedule(ctx, notify, check_changes, cleanup):
    """Run scheduled archiving of all configured sites"""
    start = datetime.datetime.now()
    log_file = os.path.join(ctx.obj['ARCHIVEBOX_DIR'], 'schedule.log')

    with open(log_file, 'a') as log:
        log.write(f"\n[{start}] Starting scheduled run...\n")
        try:
            # Run bulk archiving
            ctx.invoke(bulk)

            # Run cleanup if enabled
            if cleanup:
                log.write(f"[{datetime.datetime.now()}] Running cleanup...\n")
                # Get retention settings from config
                sites_config = ctx.obj['SITES_CONFIG']
                days = 180  # Default
                keep_monthly = True  # Default

                if sites_config and 'archive' in sites_config:
                    archive_config = sites_config['archive']
                    if 'retention_days' in archive_config:
                        days = archive_config['retention_days']
                    if 'keep_monthly_first' in archive_config:
                        keep_monthly = archive_config['keep_monthly_first']

                # Invoke cleanup with settings from config
                ctx.invoke(cleanup, days=days, keep_monthly=keep_monthly, dry_run=False)

            # Generate and log report
            report = _generate_report(ctx, start)
            log.write(report)

            # Send notification if enabled
            if notify:
                _send_notification(report, True, ctx)

            click.echo("Scheduled archive run complete.")
            log.write(f"[{datetime.datetime.now()}] Completed successfully.\n")

        except Exception as e:
            err = str(e)
            log.write(f"[{datetime.datetime.now()}] Error: {err}\n")
            if notify:
                _send_notification(err, False, ctx)
            raise


@cli.command()
@click.argument('url')
@click.argument('date1')
@click.argument('date2', required=False)
@click.pass_context
def compare(ctx, url, date1, date2):
    click.echo(f"Comparing {url} between {date1} and {date2 or 'now'}...")
    click.echo(f"1. Open UI at http://localhost:{PORT}")
    click.echo(f"2. Search for: {url}")


@cli.command()
@click.option('--days', default=180)
@click.option('--keep-monthly', is_flag=True)
@click.option('--dry-run', is_flag=True)
@click.pass_context
def cleanup(ctx, days, keep_monthly, dry_run):
    """Remove old snapshots based on retention policy"""
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    click.echo(f"{'DRY RUN: ' if dry_run else ''}Cleaning snapshots older than {cutoff:%Y-%m-%d}")

    # Get retention settings from config if available
    sites_config = ctx.obj['SITES_CONFIG']
    if sites_config and 'archive' in sites_config:
        archive_config = sites_config['archive']
        config_days = archive_config.get('retention_days')
        if config_days and not days:
            days = config_days
            cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
            click.echo(f"Using config retention period: {days} days")

        if archive_config.get('keep_monthly_first') and not keep_monthly:
            keep_monthly = True
            click.echo("Using config setting: keeping first snapshot of each month")

    # Get list of snapshots in JSON format for processing
    # We need to capture this output for parsing, so use capture_output=True
    result = _run(ctx, 'list', '--json', capture_output=True)
    if result.returncode != 0:
        click.echo("Failed to get snapshot list")
        return

    try:
        import json
        snapshots = json.loads(result.stdout)

        # Track snapshots to remove
        to_remove = []
        monthly_kept = set()

        for snapshot in snapshots:
            # Parse timestamp
            timestamp = snapshot.get('timestamp')
            if not timestamp:
                continue

            try:
                # Convert timestamp to datetime
                snapshot_date = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

                # Check if snapshot is older than cutoff
                if snapshot_date < cutoff:
                    # For monthly retention, keep first snapshot of each month
                    month_key = f"{snapshot_date.year}-{snapshot_date.month}"

                    if keep_monthly and month_key not in monthly_kept:
                        monthly_kept.add(month_key)
                        click.echo(f"Keeping monthly snapshot from {snapshot_date:%Y-%m-%d}")
                        continue

                    to_remove.append(snapshot['url'])
            except (ValueError, TypeError) as e:
                click.echo(f"Error processing snapshot date: {e}")
                continue

        # Remove snapshots
        if not to_remove:
            click.echo("No snapshots to remove")
            return

        click.echo(f"Found {len(to_remove)} snapshots to remove")

        if dry_run:
            for url in to_remove[:5]:  # Show sample in dry run
                click.echo(f"Would remove: {url}")
            if len(to_remove) > 5:
                click.echo(f"... and {len(to_remove) - 5} more")
        else:
            # ArchiveBox remove command takes URLs as input
            for url in to_remove:
                _run(ctx, 'remove', url)
            click.echo(f"Removed {len(to_remove)} snapshots")

    except json.JSONDecodeError:
        click.echo("Failed to parse snapshot list")
    except Exception as e:
        click.echo(f"Error during cleanup: {str(e)}")


@cli.command()
@click.pass_context
def status(ctx):
    click.echo(f"ArchiveBox Dir: {ctx.obj['ARCHIVEBOX_DIR']}")
    # Need to capture output to access stdout
    result = _run(ctx, 'status', capture_output=True)
    click.echo(result.stdout)
    click.echo("\nRecent snapshots:")
    # Show recent snapshots in real-time
    _run(ctx, 'list', '--sort=timestamp', '--limit=10')
    data_dir = Path(ctx.obj['ARCHIVEBOX_DIR'])
    if data_dir.exists():
        size = sum(f.stat().st_size for f in data_dir.rglob('*') if f.is_file())
        click.echo(f"Total size: {size / (1024 ** 3):.2f} GB")


def _generate_report(ctx, start_time):
    duration = datetime.datetime.now() - start_time
    report = f"Archive Run Report\nStart: {start_time}\nDuration: {duration}\n"
    sites_cfg = ctx.obj['SITES_CONFIG']
    if sites_cfg and 'sites' in sites_cfg:
        for s in sites_cfg['sites']:
            report += f"- {s['name']}: {s['url']}\n"
    return report


def _send_notification(message, success=True, ctx=None):
    """Send notifications based on configuration settings"""
    status = "SUCCESS" if success else "ERROR"
    click.echo(f"[{status}] Notification: {message}")

    # If no context provided, we can't access config
    if not ctx:
        return

    # Check if notifications are configured and enabled
    sites_config = ctx.obj.get('SITES_CONFIG', {})
    if not sites_config or 'notifications' not in sites_config:
        return

    notif_config = sites_config['notifications']
    if not notif_config.get('enabled', False):
        return

    # Check if we should notify based on success/failure status
    if success and not notif_config.get('on_success', False):
        return
    if not success and not notif_config.get('on_failure', True):
        return

    # Email notifications
    if 'email' in notif_config and notif_config['email'].get('to') and notif_config['email'].get('from'):
        try:
            import smtplib
            from email.mime.text import MIMEText

            to_email = notif_config['email']['to']
            from_email = notif_config['email']['from']

            # Create message
            msg = MIMEText(message)
            msg['Subject'] = f"ArchiveBox {status}: WordPress Archive Report"
            msg['From'] = from_email
            msg['To'] = to_email

            # Get SMTP settings from config or use defaults
            smtp_host = notif_config['email'].get('smtp_host', 'localhost')
            smtp_port = notif_config['email'].get('smtp_port', 25)

            # Send email
            click.echo(f"Sending email notification to {to_email}")

            # Only attempt to send if not in dry-run mode
            if notif_config.get('dry_run', False):
                click.echo("DRY RUN: Email would be sent")
            else:
                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    # Use TLS if configured
                    if notif_config['email'].get('use_tls', False):
                        server.starttls()

                    # Login if credentials provided
                    if notif_config['email'].get('username') and notif_config['email'].get('password'):
                        server.login(
                            notif_config['email']['username'],
                            notif_config['email']['password']
                        )

                    server.send_message(msg)

        except Exception as e:
            click.echo(f"Failed to send email notification: {str(e)}")

    # Slack notifications
    if 'slack' in notif_config and notif_config['slack'].get('webhook_url'):
        try:
            import json
            import urllib.request

            webhook_url = notif_config['slack']['webhook_url']

            # Prepare Slack message
            slack_data = {
                'text': f"*ArchiveBox {status}*\n```{message}```",
                'username': notif_config['slack'].get('username', 'ArchiveBox Bot'),
                'icon_emoji': notif_config['slack'].get('icon_emoji', ':package:')
            }

            # Only attempt to send if not in dry-run mode
            if notif_config.get('dry_run', False):
                click.echo("DRY RUN: Slack notification would be sent")
            else:
                # Send to Slack
                data = json.dumps(slack_data).encode('utf-8')
                req = urllib.request.Request(
                    webhook_url,
                    data=data,
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req) as response:
                    if response.status != 200:
                        click.echo(f"Failed to send Slack notification: HTTP {response.status}")

        except Exception as e:
            click.echo(f"Failed to send Slack notification: {str(e)}")


@cli.command()
@click.option('--port', default=PORT)
@click.option('--host', default='0.0.0.0')
@click.pass_context
def server(ctx, port, host):
    click.echo(f"Starting server on http://localhost:{port}")
    _run(ctx, 'server', f'{host}:{port}')


if __name__ == '__main__':
    cli()
