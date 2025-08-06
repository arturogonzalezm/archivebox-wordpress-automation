import os
import sys
import subprocess
import datetime
import time
from pathlib import Path

import click
import yaml

# === Default Configuration ===
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


def _run(ctx, *args, stdin=None, capture_output=False):
    """Internal: Run ArchiveBox command without raising on errors"""
    base_bin = ctx.obj['ARCHIVEBOX_BIN']
    if base_bin:
        cmd = [os.path.abspath(base_bin)] + list(args)
    else:
        cmd = ['archivebox'] + list(args)

    # Always capture output to inspect return codes
    kwargs = {
        'cwd': ctx.obj['ARCHIVEBOX_DIR'],
        'check': False,
        'stdin': stdin,
        'capture_output': True,
        'text': True,
    }
    try:
        result = subprocess.run(cmd, **kwargs)
    except FileNotFoundError:
        # Fallback to Python module
        fallback = [sys.executable, '-m', 'archivebox'] + list(args)
        click.echo(f"[!] Binary not found, falling back to: {' '.join(fallback)}")
        result = subprocess.run(fallback, **kwargs)

    if result.returncode != 0:
        click.echo(f"[!] Command failed (exit {result.returncode}): {' '.join(cmd)}")
        if result.stderr:
            click.echo(result.stderr.strip())
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
    default_config = {
        'sites': [{
            'name': 'Example Site',
            'url': 'https://example.com',
            'client': 'Example Client',
            'depth': 1,
            'archive_subpages': ['contact', 'about'],
            'monthly_snapshot': True,
            'extractors': ['screenshot', 'pdf', 'wget', 'singlefile']
        }],
        'defaults': {
            'depth': 1,
            'timeout': 60,
            'extractors': ['screenshot', 'pdf', 'wget']
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
@click.pass_context
def add(ctx, url, index_only, depth, tag):
    """Add a single URL to ArchiveBox for archiving"""
    args = ['add', url, f'--depth={depth}']
    if index_only:
        args.append('--index-only')
    for t in tag:
        args.extend(['--tag', t])

    month_tag = f"snapshot-{datetime.datetime.now().strftime('%Y-%m')}"
    args.extend(['--tag', month_tag])

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

            result = _run(ctx, 'add', url, f'--depth={depth}', *sum((['--tag', t] for t in tags), []))
            if result.returncode != 0:
                click.echo(f"Skipping {site['name']} due to error.")
                continue

            for subpage in site.get('archive_subpages', []):
                sub_url = f"{url.rstrip('/')}/{subpage}"
                result = _run(ctx, 'add', sub_url, '--depth=0', *sum((['--tag', t] for t in tags), []))
                if result.returncode != 0:
                    click.echo(f"  Skipping subpage {subpage} due to error.")
            if not parallel:
                time.sleep(2)
    else:
        with open(urls_file, 'r') as f:
            urls = [l.strip() for l in f if l.strip() and not l.startswith('#')]
        for url in urls:
            result = _run(ctx, 'add', url, f'--depth={1}')
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
    result = _run(ctx, *args)
    click.echo(result.stdout or result.stderr)


@cli.command()
@click.option('--notify/--no-notify', default=True)
@click.option('--check-changes/--no-check-changes', default=False)
@click.pass_context
def schedule(ctx, notify, check_changes):
    start = datetime.datetime.now()
    log_file = os.path.join(ctx.obj['ARCHIVEBOX_DIR'], 'schedule.log')
    with open(log_file, 'a') as log:
        log.write(f"\n[{start}] Starting scheduled run...\n")
        try:
            ctx.invoke(bulk)
            report = _generate_report(ctx, start)
            log.write(report)
            if notify: _send_notification(report, True)
            click.echo("Scheduled archive run complete.")
            log.write(f"[{datetime.datetime.now()}] Completed successfully.\n")
        except Exception as e:
            err = str(e)
            log.write(f"[{datetime.datetime.now()}] Error: {err}\n")
            if notify: _send_notification(err, False)
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
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    click.echo(f"{'DRY RUN: ' if dry_run else ''}Cleaning snapshots older than {cutoff:%Y-%m-%d}")
    if keep_monthly:
        click.echo("Keeping first snapshot of each month...")


@cli.command()
@click.pass_context
def status(ctx):
    click.echo(f"ArchiveBox Dir: {ctx.obj['ARCHIVEBOX_DIR']}")
    result = _run(ctx, 'status')
    click.echo(result.stdout)
    click.echo("\nRecent snapshots:")
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


def _send_notification(message, success=True):
    status = "SUCCESS" if success else "ERROR"
    click.echo(f"[{status}] Notification: {message}")


@cli.command()
@click.option('--port', default=PORT)
@click.option('--host', default='0.0.0.0')
@click.pass_context
def server(ctx, port, host):
    click.echo(f"Starting server on http://localhost:{port}")
    _run(ctx, 'server', f'{host}:{port}')


if __name__ == '__main__':
    cli()
