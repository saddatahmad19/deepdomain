from pathlib import Path

from src.classes.filesystems import FileSystem
from src.classes.output import Output
from src.classes.execute import Execute


def prepare_enumeration_workspace(fs: FileSystem) -> None:
    """Create the base ./enumeration directory (README step 12)."""
    if not fs.base.joinpath("enumeration").exists():
        fs.createFolder("enumeration")


def run_vulnerable(fs: FileSystem, executor: Execute, record_file: str = "record.md") -> None:
    """Execution sets 13-15: nikto, gobuster, nuclei under ./enumeration/vulnerable."""
    enum_dir = fs.base.joinpath("enumeration")
    if not enum_dir.exists():
        fs.createFolder("enumeration")

    vuln_dir = enum_dir.joinpath("vulnerable")
    if not vuln_dir.exists():
        fs.createFolder("vulnerable", location="enumeration")

    vuln_md_rel = "enumeration/vulnerable/vulnerable.md"
    vuln_md_full = fs.base.joinpath(vuln_md_rel)
    if not vuln_md_full.exists():
        vuln_md = fs.createFile("vulnerable.md", location="enumeration/vulnerable")
    else:
        vuln_md = vuln_md_full

    # Title - always add for first-time runs
    out = Output()
    out.addTitle("Vulnerable")
    out.newLine()
    out.write_to_file(vuln_md)

    # Child executor in ./enumeration/vulnerable
    child_exec = Execute(workdir=Path(executor.workdir) / "enumeration/vulnerable", tui=executor.tui)

    # Shared absolute path to live_subdomains produced in recon step 5
    live_subdomains_abs = fs.base.joinpath("recon/subdomains/live_subdomains.txt")

    # 13) nikto
    nikto_results_path = Path(child_exec.workdir) / "nikto_results.txt"
    nikto_cmd = (
        f"nikto -h -Tuning 1234567890 -o {nikto_results_path} $(cat {live_subdomains_abs} | cut -d' ' -f1)"
    )
    _append_command(fs, [vuln_md_rel, record_file], nikto_cmd)
    child_exec.run_command(nikto_cmd)
    if nikto_results_path.exists():
        _append_output(fs, vuln_md_rel, nikto_results_path.read_text())
    else:
        _append_output(fs, vuln_md_rel, "")

    # 14) gobuster
    gobuster_results_path = Path(child_exec.workdir) / "gobuster_results.txt"
    gobuster_cmd = (
        f"gobuster dir -u $(head -n1 {live_subdomains_abs}) -w /usr/share/wordlists/dirb/common.txt "
        f"-t 50 -o {gobuster_results_path} -x php,html,txt"
    )
    _append_command(fs, [vuln_md_rel, record_file], gobuster_cmd)
    child_exec.run_command(gobuster_cmd)
    if gobuster_results_path.exists():
        _append_output(fs, vuln_md_rel, gobuster_results_path.read_text())
    else:
        _append_output(fs, vuln_md_rel, "")

    # 15) nuclei
    nuclei_results_path = Path(child_exec.workdir) / "nuclei_vulns.txt"
    nuclei_cmd = (
        f"nuclei -l {live_subdomains_abs} -t /usr/share/nuclei-templates/ -severity low,medium,high,critical "
        f"-o {nuclei_results_path}"
    )
    _append_command(fs, [vuln_md_rel, record_file], nuclei_cmd)
    child_exec.run_command(nuclei_cmd)
    if nuclei_results_path.exists():
        _append_output(fs, vuln_md_rel, nuclei_results_path.read_text())
    else:
        _append_output(fs, vuln_md_rel, "")


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

