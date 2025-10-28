# src/cli.py
from pathlib import Path
import shutil
import typer
from typing import List, Tuple

from .filesystems import FileSystem
from .output import Output
from .execute import Execute
from .recon import run_whoami, run_subdomains
from .scanning import prepare_scanning_workspace

app = typer.Typer(help="DeepDomain — modular recon & scanning scaffold")

# Tools used across the flow (modify per your final toolset)
DEFAULT_TOOLS = [
    "nmap", "nikto", "subfinder", "sublist3r", "theHarvester", "shodan",
    "dnsx", "httpx", "curl", "jq", "whois", "host"
]

def _check_tools(tools: List[str]) -> Tuple[List[str], str]:
    """Return (missing_tools, install_command)"""
    missing = [t for t in tools if shutil.which(t) is None]
    install_cmd = " ".join(missing) if missing else ""
    return missing, install_cmd

@app.command()
def run(
    domain: str = typer.Option(..., "-d", "--domain", help="Target domain (required)"),
    output: Path | None = typer.Option(None, "-o", "--output", help="Output directory (optional)")
):
    # prompt for output dir if not provided
    if output is None:
        default = Path.cwd()
        out_str = typer.prompt("The output directory is:", default=str(default))
        output = Path(out_str)

    if not output.exists():
        typer.echo(f"Output path {output} does not exist.")
        raise typer.Exit(code=1)
    if not output.is_dir():
        typer.echo(f"Output path {output} is not a directory.")
        raise typer.Exit(code=1)

    missing, install_cmd = _check_tools(DEFAULT_TOOLS)
    if missing:
        typer.secho("Missing programs detected:", fg=typer.colors.YELLOW)
        for t in missing:
            typer.echo(f" - {t}")
        typer.secho(f"\nInstall missing programs with: sudo apt install {install_cmd}", fg=typer.colors.CYAN)

    # initialize helpers
    fs = FileSystem(output)
    executor = Execute(workdir=output)
    # create record.md
    record_path = fs.createFile("record.md", location="")  # returns Path
    record_out = Output()
    record_out.addTitle("Record")
    record_out.newLine()
    record_out.write_to_file(record_path)

    # Example: run whoami set (execution set 1)
    typer.secho("Running whoami execution set...", fg=typer.colors.GREEN)
    run_whoami(domain, fs, executor)

    # Example: run subdomains set (execution set 2) — skeleton
    typer.secho("Preparing subdomains execution set...", fg=typer.colors.GREEN)
    run_subdomains(domain, fs, executor)

    # Prepare scanning workspace (README step 7)
    typer.secho("Preparing scanning workspace...", fg=typer.colors.GREEN)
    prepare_scanning_workspace(fs)

    typer.secho("Done (scaffold complete). Expand each execution set in src/execute.py", fg=typer.colors.BLUE)
