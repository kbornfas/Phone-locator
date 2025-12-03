#!/usr/bin/env python3
"""
PhoneTracker CLI - Main Entry Point

A command-line tool for tracking phone locations via VoIP calls.

LEGAL NOTICE: This tool is for authorized use only. Ensure you have proper
legal authorization before tracking any phone number.
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import Config
from core.voip import VoIPService, VoIPError
from core.location import LocationFetcher, LocationError
from core.enhanced_location import EnhancedLocationFetcher
from db.models import Database

# Initialize rich console for pretty output
console = Console()

# ASCII art banner
BANNER = """
╔═══════════════════════════════════════════════════════════════╗
║         📞 PhoneTracker CLI v1.0.0                            ║
║         Track phone locations via calls                        ║
╚═══════════════════════════════════════════════════════════════╝
"""


def print_banner():
    """Print the application banner."""
    console.print(BANNER, style="green")


def get_config_manager():
    """Get the configuration manager instance."""
    return Config()


@click.group()
@click.version_option(version='1.0.0', prog_name='phonetracker')
@click.pass_context
def cli(ctx):
    """
    PhoneTracker CLI - Track phone locations via calls.
    
    \b
    ⚠️  LEGAL NOTICE: This tool requires explicit authorization.
    Unauthorized phone tracking is ILLEGAL.
    
    \b
    Quick Start:
      1. Configure Twilio: phonetracker config --set voip.account_sid=ACxxx
      2. Track a number:   phonetracker track +1234567890
      3. View history:     phonetracker history
    """
    ctx.ensure_object(dict)
    ctx.obj['config'] = get_config_manager()


@cli.command()
@click.argument('number')
@click.option('--method', '-m', default='cell_tower', 
              type=click.Choice(['basic', 'enhanced', 'cell_tower', 'carrier', 'gps']),
              help='Location tracking method (cell_tower gives best accuracy)')
@click.option('--timeout', '-t', default=60, type=int,
              help='Call timeout in seconds')
@click.option('--silent', '-s', is_flag=True,
              help='Skip confirmation prompts')
@click.option('--no-call', is_flag=True,
              help='Skip making a call (location lookup only)')
@click.pass_context
def track(ctx, number, method, timeout, silent, no_call):
    """
    Track a phone number by calling it.
    
    \b
    Examples:
      phonetracker track +254712345678
      phonetracker track +254712345678 --accuracy 3
      phonetracker track +1234567890 --method enhanced
      phonetracker track +1234567890 --silent --timeout 30
      phonetracker track +1234567890 --no-call
    
    \b
    Accuracy Levels:
      1 = Basic (country/city, ~5-50 km)
      2 = Enhanced (district, ~1-5 km)
      3 = Cell Tower (simulated, ~100-500 m) [DEFAULT]
      4 = Precise (requires GPS/APIs, ~1-50 m)
    
    NUMBER should be in E.164 format (e.g., +1234567890)
    """
    config_mgr = ctx.obj['config']
    config = config_mgr.load_config()
    
    # Validate phone number format
    if not number.startswith('+'):
        console.print("[yellow]Warning: Phone number should start with '+' (E.164 format)[/yellow]")
        console.print(f"[yellow]Example: +{number}[/yellow]")
        if not silent:
            if not click.confirm("Continue anyway?"):
                return
    
    # Check Twilio configuration (only if making calls)
    if not no_call and not config_mgr.is_configured():
        console.print("[red]Error: Twilio credentials not configured![/red]")
        console.print("\nRun these commands to configure:")
        console.print("  [yellow]phonetracker config --set voip.account_sid=ACxxxxxxxxx[/yellow]")
        console.print("  [yellow]phonetracker config --set voip.auth_token=your_token[/yellow]")
        console.print("  [yellow]phonetracker config --set voip.phone_number=+1234567890[/yellow]")
        return
    
    # Authorization check
    if not silent and config['auth']['require_confirmation']:
        console.print("\n[yellow]⚠️  LEGAL AUTHORIZATION REQUIRED[/yellow]")
        console.print("[yellow]This will make a call to the target number.[/yellow]")
        console.print("[yellow]Unauthorized tracking is ILLEGAL.[/yellow]\n")
        
        if not click.confirm("Do you have legal authorization to track this number?"):
            console.print("[red]Tracking cancelled.[/red]")
            return
    
    # Initialize database
    db = Database(config_mgr.db_file)
    
    # Log the tracking attempt
    if config['auth']['log_all_requests']:
        db.add_auth_log(
            action='track',
            phone_number=number,
            success=True,
            details=f"method={method}, timeout={timeout}"
        )
    
    call_sid = None
    call_status = 'skipped' if no_call else None
    
    try:
        if not no_call:
            # Initialize VoIP service
            voip = VoIPService(
                config['voip']['account_sid'],
                config['voip']['auth_token'],
                config['voip']['phone_number']
            )
            
            # Make the call
            console.print(f"\n[blue]📞 Initiating call to {number}...[/blue]")
            call = voip.make_call(number, timeout=timeout)
            call_sid = call.call_sid
            
            # Wait for answer
            with console.status("[cyan]⏳ Waiting for answer...[/cyan]"):
                call_status = call.wait_for_answer(max_wait=timeout)
            
            if call_status != 'answered':
                console.print(f"[red]✗ Call not answered (status: {call_status})[/red]")
                
                # Still try to get location
                console.print("[yellow]Attempting location lookup anyway...[/yellow]")
            else:
                console.print("[green bold]✓ Call answered![/green bold]")
            
            # Hang up the call
            try:
                call.hangup()
            except Exception:
                pass
        else:
            console.print(f"\n[blue]📍 Looking up location for {number}...[/blue]")
        
        # Always use cell tower method for best accuracy
        locator = LocationFetcher(
            method='cell_tower',
            carrier_api_key=config['location'].get('carrier_api_key')
        )
        
        # Fetch location with cell tower triangulation
        with console.status("[yellow]📡 Triangulating location via cell towers...[/yellow]"):
            location = locator.get_location(number)
        
        if location:
            console.print("[green bold]✓ Location acquired![/green bold]\n")
            
            # Display location info
            console.print("[blue]📍 Location Found:[/blue]")
            console.print(f"   Latitude:  {location.latitude}°")
            console.print(f"   Longitude: {location.longitude}°")
            console.print(f"   Accuracy:  [green]±{location.accuracy}m[/green]")
            console.print(f"   Method:    {location.method}")
            
            if location.city:
                console.print(f"   Area:      {location.city}")
            if location.country:
                console.print(f"   Country:   {location.country}")
            if location.carrier:
                console.print(f"   Carrier:   {location.carrier}")
            
            console.print(f"   Time:      {location.timestamp}")
            
            # Generate and display map link
            if config['display']['show_map_link']:
                map_url = locator.get_map_url(location)
                console.print(f"\n[cyan]🗺️  Map: {map_url}[/cyan]")
            
            # Save to database
            db.add_tracking_log(
                phone_number=number,
                call_sid=call_sid,
                location=location.to_dict(),
                call_status=call_status
            )
            console.print("\n[green]✓ Saved to tracking history[/green]")
            
        else:
            console.print("[red]✗ Could not determine location[/red]")
            db.add_tracking_log(
                phone_number=number,
                call_sid=call_sid,
                call_status=call_status,
                notes="Location lookup failed"
            )
    
    except VoIPError as e:
        console.print(f"\n[red]✗ VoIP Error: {str(e)}[/red]")
        db.add_auth_log(
            action='track',
            phone_number=number,
            success=False,
            error_message=str(e)
        )
    
    except LocationError as e:
        console.print(f"\n[red]✗ Location Error: {str(e)}[/red]")
    
    except Exception as e:
        console.print(f"\n[red]✗ Unexpected error: {str(e)}[/red]")
        if config['display']['verbose']:
            console.print_exception()
    
    finally:
        db.close()


@cli.command()
@click.argument('number', required=False)
@click.option('--limit', '-l', default=10, type=int,
              help='Number of records to show')
@click.option('--export', '-e', type=click.Choice(['csv', 'json']),
              help='Export format')
@click.option('--output', '-o', type=click.Path(),
              help='Output file path for export')
@click.pass_context
def history(ctx, number, limit, export, output):
    """
    View tracking history.
    
    \b
    Examples:
      phonetracker history
      phonetracker history +254712345678
      phonetracker history --limit 20
      phonetracker history --export csv --output ./tracks.csv
    """
    config_mgr = ctx.obj['config']
    db = Database(config_mgr.db_file)
    
    try:
        records = db.get_history(phone_number=number, limit=limit)
        
        if not records:
            console.print("[yellow]No tracking history found.[/yellow]")
            if number:
                console.print(f"[yellow]No records for {number}[/yellow]")
            return
        
        # Export if requested
        if export:
            data = db.export_history(format=export, phone_number=number)
            
            if output:
                with open(output, 'w') as f:
                    f.write(data)
                console.print(f"[green]✓ Exported {len(records)} records to {output}[/green]")
            else:
                console.print(data)
            return
        
        # Display as table
        table = Table(title="📋 Tracking History", show_lines=True)
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Phone Number", style="green")
        table.add_column("Location", style="blue")
        table.add_column("City/Country", style="magenta")
        table.add_column("Accuracy", style="yellow")
        table.add_column("Status", style="white")
        table.add_column("Timestamp", style="dim")
        
        for record in records:
            location = f"{record.latitude:.4f}, {record.longitude:.4f}" if record.latitude else "N/A"
            city_country = f"{record.city or 'Unknown'}, {record.country or 'Unknown'}"
            accuracy = f"±{record.accuracy}m" if record.accuracy else "N/A"
            status = record.call_status or "N/A"
            timestamp = record.timestamp.strftime("%Y-%m-%d %H:%M") if record.timestamp else "N/A"
            
            # Color status
            if status == 'answered':
                status = f"[green]{status}[/green]"
            elif status in ['no-answer', 'busy', 'failed']:
                status = f"[red]{status}[/red]"
            
            table.add_row(
                str(record.id),
                record.phone_number,
                location,
                city_country,
                accuracy,
                status,
                timestamp
            )
        
        console.print(table)
        console.print(f"\n[dim]Showing {len(records)} of {db.get_tracking_count(number)} records[/dim]")
    
    finally:
        db.close()


@cli.command()
@click.option('--set', 'set_value', metavar='KEY=VALUE',
              help='Set a configuration value')
@click.option('--show', is_flag=True,
              help='Show current configuration')
@click.option('--reset', is_flag=True,
              help='Reset configuration to defaults')
@click.pass_context
def config(ctx, set_value, show, reset):
    """
    Configure API keys and settings.
    
    \b
    Examples:
      phonetracker config --show
      phonetracker config --set voip.account_sid=ACxxxxxxxx
      phonetracker config --set voip.auth_token=your_token
      phonetracker config --set voip.phone_number=+1234567890
      phonetracker config --reset
    
    \b
    Available Settings:
      voip.account_sid      - Twilio Account SID
      voip.auth_token       - Twilio Auth Token
      voip.phone_number     - Your Twilio phone number
      location.method       - Default location method (basic/carrier/gps)
      auth.require_confirmation - Require confirmation before tracking
      display.show_map_link - Show Google Maps link in output
      display.verbose       - Show detailed error messages
    """
    config_mgr = ctx.obj['config']
    
    if reset:
        if click.confirm("Reset all configuration to defaults?"):
            config_mgr.reset()
            console.print("[green]✓ Configuration reset to defaults[/green]")
        return
    
    if show:
        cfg = config_mgr.display()
        console.print("\n[cyan bold]Current Configuration:[/cyan bold]")
        console.print(f"[dim]Config file: {config_mgr.config_file}[/dim]\n")
        
        # Pretty print config
        import yaml
        formatted = yaml.dump(cfg, default_flow_style=False, sort_keys=False)
        console.print(Panel(formatted, title="config.yaml", border_style="blue"))
        
        # Show status
        if config_mgr.is_configured():
            console.print("\n[green]✓ Twilio credentials configured[/green]")
        else:
            console.print("\n[yellow]⚠ Twilio credentials not configured[/yellow]")
        return
    
    if set_value:
        try:
            if '=' not in set_value:
                console.print("[red]Error: Use format KEY=VALUE[/red]")
                console.print("Example: phonetracker config --set voip.account_sid=ACxxx")
                return
            
            key, value = set_value.split('=', 1)
            config_mgr.set_value(key.strip(), value.strip())
            console.print(f"[green]✓ Set {key} = {value}[/green]")
            
            # Provide helpful feedback
            if 'account_sid' in key:
                console.print("[dim]Next: Set your auth_token[/dim]")
            elif 'auth_token' in key:
                console.print("[dim]Next: Set your phone_number[/dim]")
            elif 'phone_number' in key and config_mgr.is_configured():
                console.print("[green]✓ All Twilio credentials configured![/green]")
                console.print("[dim]You can now run: phonetracker track +1234567890[/dim]")
        
        except Exception as e:
            console.print(f"[red]Error setting config: {str(e)}[/red]")
        return
    
    # No options provided - show help
    console.print("[yellow]Use --show to view config or --set KEY=VALUE to update[/yellow]")
    console.print("\nQuick setup:")
    console.print("  [cyan]phonetracker config --set voip.account_sid=ACxxx[/cyan]")
    console.print("  [cyan]phonetracker config --set voip.auth_token=xxx[/cyan]")
    console.print("  [cyan]phonetracker config --set voip.phone_number=+1xxx[/cyan]")


@cli.command()
@click.option('--limit', '-l', default=50, type=int,
              help='Number of log entries to show')
@click.pass_context
def logs(ctx, limit):
    """
    View authorization and audit logs.
    
    Shows all tracking attempts for compliance and auditing purposes.
    """
    config_mgr = ctx.obj['config']
    db = Database(config_mgr.db_file)
    
    try:
        records = db.get_auth_logs(limit=limit)
        
        if not records:
            console.print("[yellow]No audit logs found.[/yellow]")
            return
        
        table = Table(title="🔒 Authorization Logs", show_lines=True)
        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Action", style="blue")
        table.add_column("Phone Number", style="green")
        table.add_column("User", style="magenta")
        table.add_column("Status", style="white")
        table.add_column("Timestamp", style="dim")
        
        for record in records:
            status = "[green]✓[/green]" if record.success else f"[red]✗ {record.error_message or ''}[/red]"
            timestamp = record.timestamp.strftime("%Y-%m-%d %H:%M") if record.timestamp else "N/A"
            
            table.add_row(
                str(record.id),
                record.action,
                record.phone_number or "N/A",
                record.user or "N/A",
                status,
                timestamp
            )
        
        console.print(table)
    
    finally:
        db.close()


@cli.command()
@click.option('--phone', '-p', help='Delete history for specific phone number')
@click.option('--all', 'delete_all', is_flag=True, help='Delete all history')
@click.pass_context
def clear(ctx, phone, delete_all):
    """
    Clear tracking history.
    
    \b
    Examples:
      phonetracker clear --phone +254712345678
      phonetracker clear --all
    """
    if not phone and not delete_all:
        console.print("[yellow]Specify --phone NUMBER or --all[/yellow]")
        return
    
    config_mgr = ctx.obj['config']
    db = Database(config_mgr.db_file)
    
    try:
        if delete_all:
            if not click.confirm("[red]Delete ALL tracking history?[/red]"):
                return
            count = db.delete_history()
        else:
            if not click.confirm(f"Delete history for {phone}?"):
                return
            count = db.delete_history(phone_number=phone)
        
        console.print(f"[green]✓ Deleted {count} records[/green]")
    
    finally:
        db.close()


@cli.command()
def info():
    """
    Show system and configuration information.
    """
    print_banner()
    
    config_mgr = get_config_manager()
    
    console.print("[cyan bold]System Information:[/cyan bold]")
    console.print(f"  Config directory: {config_mgr.config_dir}")
    console.print(f"  Config file:      {config_mgr.config_file}")
    console.print(f"  Database file:    {config_mgr.db_file}")
    
    # Check Twilio status
    console.print("\n[cyan bold]Service Status:[/cyan bold]")
    if config_mgr.is_configured():
        console.print("  Twilio: [green]✓ Configured[/green]")
    else:
        console.print("  Twilio: [yellow]⚠ Not configured[/yellow]")
    
    # Database stats
    db = Database(config_mgr.db_file)
    try:
        count = db.get_tracking_count()
        console.print(f"  Tracking records: {count}")
    finally:
        db.close()
    
    console.print("\n[dim]For help, run: phonetracker --help[/dim]")


# Entry point
def main():
    """Main entry point for the CLI."""
    cli(obj={})


if __name__ == '__main__':
    main()
