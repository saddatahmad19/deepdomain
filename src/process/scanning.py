from pathlib import Path
import subprocess

from src.classes.filesystems import FileSystem
from src.classes.output import Output
from src.classes.execute import Execute


def prepare_scanning_workspace(fs: FileSystem) -> None:
    """Create the base ./scanning directory (README step 7)."""
    if not fs.base.joinpath("scanning").exists():
        fs.createFolder("scanning")


def run_resolve(fs: FileSystem, executor: Execute) -> None:
    """Execution set 5: dnsx and httpx resolve steps with outputs."""
    scanning_dir = fs.base.joinpath("scanning")
    if not scanning_dir.exists():
        fs.createFolder("scanning")
    resolve_dir = scanning_dir.joinpath("resolve")
    if not resolve_dir.exists():
        fs.createFolder("resolve", location="scanning")
    resolved_rel = "scanning/resolve/resolved.md"
    resolved_full = fs.base.joinpath(resolved_rel)
    if not resolved_full.exists():
        resolved_path = fs.createFile("resolved.md", location="scanning/resolve")
    else:
        resolved_path = resolved_full

    # Title - always add for first-time runs
    out = Output()
    out.addTitle("Resolved Hosts")
    out.newLine()
    out.write_to_file(resolved_path)

    # Child executor in ./scanning/resolve
    child_exec = Execute(workdir=Path(executor.workdir) / "scanning/resolve", tui=executor.tui)

    # d) dnsx from all_subdomains.txt - use absolute path
    all_subdomains_abs = fs.base.joinpath("recon/subdomains/all_subdomains.txt")
    dnsx_cmd = f"cat {all_subdomains_abs} | dnsx -silent -a -aaaa -resp -o {Path(child_exec.workdir)}/resolved_hosts.txt"
    _append_command(fs, [resolved_rel, "record.md"], dnsx_cmd)
    child_exec.run_command(dnsx_cmd)

    # e) append resolved_hosts.txt contents
    resolved_hosts_path = Path(child_exec.workdir) / "resolved_hosts.txt"
    if resolved_hosts_path.exists():
        _append_output(fs, resolved_rel, resolved_hosts_path.read_text())
    else:
        _append_output(fs, resolved_rel, "")

    # Continue resolve (step 9) - httpx
    httpx_cmd = f"httpx -l {all_subdomains_abs} -title -status-code -tech-detect -follow-redirects -mc 200,301,302 -o {Path(child_exec.workdir)}/live_subdomains.txt"
    _append_command(fs, [resolved_rel, "record.md"], httpx_cmd)
    child_exec.run_command(httpx_cmd)
    live_subdomains_path = Path(child_exec.workdir) / "live_subdomains.txt"
    if live_subdomains_path.exists():
        _append_output(fs, resolved_rel, live_subdomains_path.read_text())


def run_network_discover(fs: FileSystem, executor: Execute) -> None:
    """Execution set 6: quick (nmap ping, masscan) and detailed (nmap with ports)."""
    scanning_dir = fs.base.joinpath("scanning")
    if not scanning_dir.exists():
        fs.createFolder("scanning")
    net_dir = scanning_dir.joinpath("network_discover")
    if not net_dir.exists():
        fs.createFolder("network_discover", location="scanning")

    # quick
    quick_dir = net_dir.joinpath("quick")
    if not quick_dir.exists():
        fs.createFolder("quick", location="scanning/network_discover")
    quick_md_full = fs.base.joinpath("scanning/network_discover/quick/quick_discovery.md")
    if not quick_md_full.exists():
        quick_md = fs.createFile("quick_discovery.md", location="scanning/network_discover/quick")
    else:
        quick_md = quick_md_full
    # Title - always add for first-time runs
    quick_out = Output()
    quick_out.addTitle("Quick Discovery")
    quick_out.newLine()
    quick_out.write_to_file(quick_md)

    # detailed
    detailed_dir = net_dir.joinpath("detailed")
    if not detailed_dir.exists():
        fs.createFolder("detailed", location="scanning/network_discover")
    det_md_full = fs.base.joinpath("scanning/network_discover/detailed/detailed_discovery.md")
    if not det_md_full.exists():
        det_md = fs.createFile("detailed_discovery.md", location="scanning/network_discover/detailed")
    else:
        det_md = det_md_full
    # Title - always add for first-time runs
    det_out = Output()
    det_out.addTitle("Detailed Discovery")
    det_out.newLine()
    det_out.write_to_file(det_md)

    # Child executors for quick/detailed
    quick_exec = Execute(workdir=Path(executor.workdir) / "scanning/network_discover/quick", tui=executor.tui)
    det_exec = Execute(workdir=Path(executor.workdir) / "scanning/network_discover/detailed", tui=executor.tui)

    # Use absolute paths
    resolved_hosts_abs = fs.base.joinpath("scanning/resolve/resolved_hosts.txt")
    masscan_results_abs = Path(quick_exec.workdir) / "masscan_results.grep"

    # c) nmap ping sweep
    nmap_ping_cmd = f"nmap -sS -Pn -T4 -F -oA {resolved_hosts_abs} -oN {Path(quick_exec.workdir)}/nmap_ping.txt"
    _append_command(fs, ["scanning/network_discover/quick/quick_discovery.md", "record.md"], nmap_ping_cmd)
    quick_exec.run_command(nmap_ping_cmd)
    nmap_ping_path = Path(quick_exec.workdir) / "nmap_ping.txt"
    if nmap_ping_path.exists():
        _append_output(fs, "scanning/network_discover/quick/quick_discovery.md", nmap_ping_path.read_text())
    else:
        _append_output(fs, "scanning/network_discover/quick/quick_discovery.md", "")

    # e) masscan
    masscan_cmd = f"masscan -p1-65535 --rate=1000 -iL {resolved_hosts_abs} --banners -oG {masscan_results_abs}"
    _append_command(fs, ["scanning/network_discover/quick/quick_discovery.md", "record.md"], masscan_cmd)
    quick_exec.run_command(masscan_cmd)
    if masscan_results_abs.exists():
        _append_output(fs, "scanning/network_discover/quick/quick_discovery.md", masscan_results_abs.read_text())
    else:
        _append_output(fs, "scanning/network_discover/quick/quick_discovery.md", "")

    # h) detailed nmap using ports parsed from masscan grep file
    # First, check if we have ports to scan
    ports_to_scan = ""
    if masscan_results_abs.exists() and masscan_results_abs.stat().st_size > 0:
        # Parse ports from masscan output
        grep_cmd = f"grep open {masscan_results_abs} | cut -d' ' -f4 | cut -d/ -f1 | sort -u"
        proc = subprocess.run(grep_cmd, shell=True, capture_output=True, text=True, cwd=str(quick_exec.workdir), timeout=30)
        ports_str = proc.stdout.strip()
        if ports_str:
            # Convert newlines to commas for nmap
            ports_to_scan = ports_str.replace('\n', ',').rstrip(',')
    
    # Only run detailed nmap if we have ports
    if ports_to_scan:
        nmap_det_cmd = f"nmap -sV -O -sC -T3 -p {ports_to_scan} -iL {resolved_hosts_abs} -oA {Path(det_exec.workdir)}/nmap_detailed"
        _append_command(fs, ["scanning/network_discover/detailed/detailed_discovery.md", "record.md"], nmap_det_cmd)
        det_exec.run_command(nmap_det_cmd)
        nmap_det_out = Path(det_exec.workdir) / "nmap_detailed.nmap"
        if nmap_det_out.exists():
            _append_output(fs, "scanning/network_discover/detailed/detailed_discovery.md", nmap_det_out.read_text())
        else:
            _append_output(fs, "scanning/network_discover/detailed/detailed_discovery.md", "")
    else:
        # No ports found, skip detailed scan
        skip_msg = "No open ports found from masscan results. Skipping detailed nmap scan."
        _append_output(fs, "scanning/network_discover/detailed/detailed_discovery.md", skip_msg)


# local helpers (shared with recon)
def _append_command(fs: FileSystem, files: list[str], command: str) -> None:
    out = Output()
    out.addCommand(command)
    out.newLine()
    for f in files:
        fs.appendOutput(f, out)


def _append_output(fs: FileSystem, file: str, text: str) -> None:
    out = Output()
    out.addCommandOutput(text)
    out.newLine()
    fs.appendOutput(file, out)

