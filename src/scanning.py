from pathlib import Path

from .filesystems import FileSystem
from .output import Output
from .execute import Execute


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

    expected_title = "# Resolved Hosts"
    first_line = ""
    try:
        with resolved_path.open("r", encoding="utf-8") as fh:
            first_line = fh.readline().rstrip("\n\r")
    except Exception:
        first_line = ""
    if first_line != expected_title:
        out = Output()
        out.addTitle("Resolved Hosts")
        out.newLine()
        out.write_to_file(resolved_path)

    # Child executor in ./scanning/resolve
    child_exec = Execute(workdir=Path(executor.workdir) / "scanning/resolve")

    # d) dnsx from all_subdomains.txt
    dnsx_cmd = "cat ./recon/subdomains/all_subdomains.txt | dnsx -silent -a -aaaa -resp -o resolved_hosts.txt"
    _append_command(fs, [resolved_rel, "record.md"], dnsx_cmd)
    child_exec.run_command(dnsx_cmd)

    # e) append resolved_hosts.txt contents
    resolved_hosts_path = Path(child_exec.workdir) / "resolved_hosts.txt"
    if resolved_hosts_path.exists():
        _append_output(fs, resolved_rel, resolved_hosts_path.read_text())
    else:
        _append_output(fs, resolved_rel, "")


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
    quick_expected = "# Quick Discovery"
    q_first = ""
    try:
        with quick_md.open("r", encoding="utf-8") as fh:
            q_first = fh.readline().rstrip("\n\r")
    except Exception:
        q_first = ""
    if q_first != quick_expected:
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
    det_expected = "# Detailed Discovery"
    d_first = ""
    try:
        with det_md.open("r", encoding="utf-8") as fh:
            d_first = fh.readline().rstrip("\n\r")
    except Exception:
        d_first = ""
    if d_first != det_expected:
        det_out = Output()
        det_out.addTitle("Detailed Discovery")
        det_out.newLine()
        det_out.write_to_file(det_md)

    # Child executors for quick/detailed
    quick_exec = Execute(workdir=Path(executor.workdir) / "scanning/network_discover/quick")
    det_exec = Execute(workdir=Path(executor.workdir) / "scanning/network_discover/detailed")

    # c) nmap ping sweep
    nmap_ping_cmd = "nmap -sn -T4 -iL ./scanning/resolve/resolved_hosts.txt -oN nmap_ping.txt"
    _append_command(fs, ["scanning/network_discover/quick/quick_discovery.md", "record.md"], nmap_ping_cmd)
    quick_exec.run_command(nmap_ping_cmd)
    nmap_ping_path = Path(quick_exec.workdir) / "nmap_ping.txt"
    if nmap_ping_path.exists():
        _append_output(fs, "scanning/network_discover/quick/quick_discovery.md", nmap_ping_path.read_text())

    # e) masscan
    masscan_cmd = "masscan -p1-65535 --rate=1000 -iL ./scanning/resolve/resolved_hosts.txt --banners -oG masscan_results.grep"
    _append_command(fs, ["scanning/network_discover/quick/quick_discovery.md", "record.md"], masscan_cmd)
    quick_exec.run_command(masscan_cmd)
    masscan_out_path = Path(quick_exec.workdir) / "masscan_results.grep"
    if masscan_out_path.exists():
        _append_output(fs, "scanning/network_discover/quick/quick_discovery.md", masscan_out_path.read_text())

    # h) detailed nmap using ports parsed from masscan grep file
    parse_ports = (
        "$(grep open ./scanning/network_discover/quick/masscan_results.grep | cut -d' ' -f4 | cut -d/ -f1 | sort -u | tr '\n' ',')"
    )
    nmap_det_cmd = f"nmap -sV -O -sC -T3 -p {parse_ports} -iL ./scanning/resolve/resolved_hosts.txt -oA nmap_detailed"
    _append_command(fs, ["scanning/network_discover/detailed/detailed_discovery.md", "record.md"], nmap_det_cmd)
    det_exec.run_command(nmap_det_cmd)
    nmap_det_out = Path(det_exec.workdir) / "nmap_detailed.nmap"
    if nmap_det_out.exists():
        _append_output(fs, "scanning/network_discover/detailed/detailed_discovery.md", nmap_det_out.read_text())


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

