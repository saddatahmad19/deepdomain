# src/cli.py
from pathlib import Path
import shutil
import typer
from typing import List, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.spinner import Spinner
from rich import print as rprint
from rich.text import Text
import time

from classes.filesystems import FileSystem
from classes.output import Output
from classes.execute import Execute
from process.recon import run_whoami, run_subdomains, run_harvest, run_shodan
from process.scanning import prepare_scanning_workspace, run_resolve, run_network_discover
from process.enumerate import prepare_enumeration_workspace, run_vulnerable
from utils.tui import create_tui

app = typer.Typer(help="DeepDomain — Advanced Security Reconnaissance Tool")
console = Console()

# Tools used across the flow (modify per your final toolset)
DEFAULT_TOOLS = [
    "nmap", "nikto", "subfinder", "sublist3r", "theHarvester", "shodan",
    "dnsx", "httpx", "curl", "jq", "whois", "host", "masscan", "gobuster", "nuclei"
]

def _check_tools(tools: List[str]) -> Tuple[List[str], str]:
    """Return (missing_tools, install_command)"""
    missing = [t for t in tools if shutil.which(t) is None]
    install_cmd = " ".join(missing) if missing else ""
    return missing, install_cmd


def _print_section_header(title: str, emoji: str = "🔍"):
    """Print a formatted section header"""
    console.print(f"\n{emoji} {title}", style="bold cyan", justify="left")


def _print_success(message: str):
    """Print a success message"""
    console.print(f"✓ {message}", style="bold green")


def _print_info(message: str):
    """Print an info message"""
    console.print(f"ℹ {message}", style="dim")


@app.command()
def run(
    domain: str = typer.Option(..., "-d", "--domain", help="Target domain (required)"),
    output: Path | None = typer.Option(None, "-o", "--output", help="Output directory (optional)")
):
    """DeepDomain — Advanced Security Reconnaissance Tool
    
    A comprehensive cybersecurity reconnaissance and scanning tool designed for Kali Linux.
    Performs domain reconnaissance, subdomain discovery, information harvesting, and network scanning.
    """
    # Print startup banner
    console.print("\n" + "="*60, style="bold cyan")
    console.print(Panel.fit(
        f"[bold cyan]DeepDomain[/bold cyan] - Advanced Security Reconnaissance Tool\n"
        f"[dim]Target Domain:[/dim] [yellow]{domain}[/yellow]",
        border_style="cyan"
    ), style="bold")
    console.print("="*60 + "\n", style="bold cyan")
    
    # prompt for output dir if not provided
    if output is None:
        default = Path.cwd()
        out_str = typer.prompt("The output directory is:", default=str(default))
        output = Path(out_str)

    if not output.exists():
        console.print(f"\n[bold red]✗ Error:[/bold red] Output path does not exist: [cyan]{output}[/cyan]")
        raise typer.Exit(code=1)
    if not output.is_dir():
        console.print(f"\n[bold red]✗ Error:[/bold red] Output path is not a directory: [cyan]{output}[/cyan]")
        raise typer.Exit(code=1)

    missing, install_cmd = _check_tools(DEFAULT_TOOLS)
    if missing:
        console.print("\n[bold yellow]⚠ Missing Required Tools:[/bold yellow]")
        console.print(Panel(
            "\n".join([f"[yellow]•[/yellow] {t}" for t in missing]),
            title="[yellow]Install Required Tools[/yellow]",
            border_style="yellow"
        ))
        console.print(f"[bold cyan]Run:[/bold cyan] [bold white]sudo apt install {install_cmd}[/bold white]\n")

    # Define scanning callback
    def scanning_callback(tui_app):
        """Callback function to run scanning phases within TUI"""
        try:
            # initialize helpers with TUI integration
            fs = FileSystem(output)
            executor = Execute(workdir=output, tui=tui_app)
            
            # create record.md (always add title for first-time runs)
            record_rel = "record.md"
            record_full = (output / record_rel)
            if not record_full.exists():
                record_path = fs.createFile("record.md", location="")  # returns Path
                record_out = Output()
                record_out.addTitle("Record")
                record_out.newLine()
                record_out.write_to_file(record_path)

            tui_app.add_status_message("Workspace initialized", "success")
            tui_app.update_phase("Ready to begin", 20)

            # Run the main phases with TUI integration
            run_recon(domain, fs, executor, tui_app)
            run_scanning(fs, executor, tui_app)
            run_enumeration(fs, executor, tui_app)
            
            # Final success message
            tui_app.update_phase("Complete", 100)
            tui_app.add_status_message("DeepDomain scan complete!", "success")
            tui_app.add_status_message(f"Results saved to: {output}", "info")
            
        except Exception as e:
            tui_app.add_status_message(f"Scanning error: {str(e)}", "error")
            raise

    # Initialize TUI with scanning callback
    tui = create_tui(domain, output, scanning_callback)
    tui.start()
    
    # Update TUI with initial status
    tui.update_phase("Initializing", 10)
    tui.add_status_message("DeepDomain scan starting...", "info")

    # Run the TUI in the main thread - this will block until TUI exits
    tui.run_tui()
    
    # Also show final message in console
    console.print("\n" + "="*60, style="bold green")
    console.print(Panel.fit(
        "[bold green]✓ DeepDomain scan complete![/bold green]\n"
        f"[dim]Results saved to:[/dim] [cyan]{output}[/cyan]",
        border_style="green"
    ))
    console.print("="*60 + "\n", style="bold green")


def run_recon(domain: str, fs: FileSystem, executor: Execute, tui=None):
    """Run all reconnaissance phase execution sets."""
    tui.update_phase("Reconnaissance Phase", 30)
    tui.add_status_message("Starting reconnaissance phase...", "info")
    
    try:
        # Execution set 1: WhoAmI
        tui.add_status_message("Running whoami execution set...", "info")
        run_whoami(domain, fs, executor)
        tui.add_status_message("WhoAmI investigation complete", "success")
        
        # Execution set 2: Subdomains
        tui.add_status_message("Discovering subdomains...", "info")
        run_subdomains(domain, fs, executor)
        tui.add_status_message("Subdomain discovery complete", "success")
        
        # Execution set 3: Harvest
        tui.add_status_message("Harvesting information...", "info")
        run_harvest(domain, fs, executor)
        tui.add_status_message("Information harvesting complete", "success")
        
        # Execution set 4: Shodan
        tui.add_status_message("Querying Shodan...", "info")
        run_shodan(domain, fs, executor)
        tui.add_status_message("Shodan reconnaissance complete", "success")
        
        tui.add_status_message("Reconnaissance phase complete", "success")
    except Exception as e:
        tui.add_status_message(f"Reconnaissance phase failed: {str(e)}", "error")
        raise


def run_scanning(fs: FileSystem, executor: Execute, tui=None):
    """Run all scanning phase execution sets."""
    tui.update_phase("Scanning Phase", 60)
    tui.add_status_message("Starting scanning phase...", "info")
    
    try:
        # Prepare scanning workspace
        tui.add_status_message("Preparing scanning workspace...", "info")
        prepare_scanning_workspace(fs)
        tui.add_status_message("Scanning workspace initialized", "success")
        
        # Execution set 5 & 9: Resolve
        tui.add_status_message("Resolving hosts and live endpoints...", "info")
        run_resolve(fs, executor)
        tui.add_status_message("Host resolution complete", "success")
        
        # Execution set 6: Network discovery
        tui.add_status_message("Performing network discovery...", "info")
        run_network_discover(fs, executor)
        tui.add_status_message("Network discovery complete", "success")
        
        tui.add_status_message("Scanning phase complete", "success")
    except Exception as e:
        tui.add_status_message(f"Scanning phase failed: {str(e)}", "error")
        raise


def run_enumeration(fs: FileSystem, executor: Execute, tui=None):
    """Run all enumeration phase execution sets."""
    tui.update_phase("Enumeration Phase", 80)
    tui.add_status_message("Starting enumeration phase...", "info")
    
    try:
        # Prepare enumeration workspace
        tui.add_status_message("Preparing enumeration workspace...", "info")
        prepare_enumeration_workspace(fs)
        tui.add_status_message("Enumeration workspace initialized", "success")
        
        # Run vulnerable enumeration (execution sets 13-15)
        tui.add_status_message("Running vulnerability enumeration...", "info")
        run_vulnerable(fs, executor)
        tui.add_status_message("Vulnerability enumeration complete", "success")
        
        tui.add_status_message("Enumeration phase complete", "success")
    except Exception as e:
        tui.add_status_message(f"Enumeration phase failed: {str(e)}", "error")
        raise
