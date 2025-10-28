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

from .filesystems import FileSystem
from .output import Output
from .execute import Execute
from .recon import run_whoami, run_subdomains, run_harvest, run_shodan
from .scanning import prepare_scanning_workspace, run_resolve, run_network_discover

app = typer.Typer(help="DeepDomain — Advanced Security Reconnaissance Tool")
console = Console()

# Version information
__version__ = "1.0.0"

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
    console.print(f"\n{emoji} {title}", style="bold cyan", justify="center")


def _print_success(message: str):
    """Print a success message"""
    console.print(f"✓ {message}", style="bold green")


def _print_info(message: str):
    """Print an info message"""
    console.print(f"ℹ {message}", style="dim")


@app.callback()
def main(
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

    # initialize helpers
    fs = FileSystem(output)
    executor = Execute(workdir=output)
    # create record.md (with existence and title checks)
    record_rel = "record.md"
    record_full = (output / record_rel)
    if not record_full.exists():
        record_path = fs.createFile("record.md", location="")  # returns Path
        record_out = Output()
        record_out.addTitle("Record")
        record_out.newLine()
        record_out.write_to_file(record_path)
    else:
        # Only add title if first line does not already match
        first_line = ""
        try:
            with record_full.open("r", encoding="utf-8") as fh:
                first_line = fh.readline().rstrip("\n\r")
        except Exception:
            first_line = ""
        expected_title = "# Record"
        if first_line != expected_title:
            # Do not overwrite existing files; skip adding title if different content exists
            pass

    # Run the main phases
    run_recon(domain, fs, executor)
    run_scanning(fs, executor)
    
    # Final success message
    console.print("\n" + "="*60, style="bold green")
    console.print(Panel.fit(
        "[bold green]✓ DeepDomain scan complete![/bold green]\n"
        f"[dim]Results saved to:[/dim] [cyan]{output}[/cyan]",
        border_style="green"
    ))
    console.print("="*60 + "\n", style="bold green")


def run_recon(domain: str, fs: FileSystem, executor: Execute):
    """Run all reconnaissance phase execution sets."""
    _print_section_header("RECONNAISSANCE PHASE", "🔎")
    
    # Execution set 1: WhoAmI
    with console.status("[bold yellow]Running whoami execution set...", spinner="dots"):
        time.sleep(0.5)  # Brief pause for visual effect
        run_whoami(domain, fs, executor)
    _print_success("WhoAmI investigation complete")
    
    # Execution set 2: Subdomains
    with console.status("[bold yellow]Discovering subdomains...", spinner="dots2"):
        time.sleep(0.5)
        run_subdomains(domain, fs, executor)
    _print_success("Subdomain discovery complete")
    
    # Execution set 3: Harvest
    with console.status("[bold yellow]Harvesting information...", spinner="earth"):
        time.sleep(0.5)
        run_harvest(domain, fs, executor)
    _print_success("Information harvesting complete")
    
    # Execution set 4: Shodan
    with console.status("[bold yellow]Querying Shodan...", spinner="bouncingBall"):
        time.sleep(0.5)
        run_shodan(domain, fs, executor)
    _print_success("Shodan reconnaissance complete")
    
    console.print("\n[bold]✓[/bold] [green]Reconnaissance phase complete[/green]\n", justify="center")


def run_scanning(fs: FileSystem, executor: Execute):
    """Run all scanning phase execution sets."""
    _print_section_header("SCANNING PHASE", "📡")
    
    # Prepare scanning workspace
    with console.status("[bold yellow]Preparing scanning workspace...", spinner="dots"):
        time.sleep(0.3)
        prepare_scanning_workspace(fs)
    _print_info("Scanning workspace initialized")
    
    # Execution set 5 & 9: Resolve
    with console.status("[bold yellow]Resolving hosts and live endpoints...", spinner="clock"):
        time.sleep(0.5)
        run_resolve(fs, executor)
    _print_success("Host resolution complete")
    
    # Execution set 6: Network discovery
    with console.status("[bold yellow]Performing network discovery...", spinner="point"):
        time.sleep(0.5)
        run_network_discover(fs, executor)
    _print_success("Network discovery complete")
    
    console.print("\n[bold]✓[/bold] [green]Scanning phase complete[/green]\n", justify="center")
