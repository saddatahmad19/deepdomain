from pathlib import Path
from typing import Optional

from .filesystems import FileSystem
from .output import Output
from .execute import Execute


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


def run_harvest(domain: str, fs: FileSystem, executor: Execute, record_file: str = "record.md") -> None:
    """Execution set 3: recon/harvest with theHarvester."""
    recon_dir = fs.base.joinpath("recon")
    if not recon_dir.exists():
        fs.createFolder("recon")
    harvest_dir = recon_dir.joinpath("harvest")
    if not harvest_dir.exists():
        fs.createFolder("harvest", location="recon")
    
    harvest_md_rel = "recon/harvest/harvest.md"
    harvest_md_full = fs.base.joinpath(harvest_md_rel)
    if not harvest_md_full.exists():
        harvest_md = fs.createFile("harvest.md", location="recon/harvest")
    else:
        harvest_md = harvest_md_full
    
    expected_title = "# Harvest"
    first_line = ""
    try:
        with harvest_md.open("r", encoding="utf-8") as fh:
            first_line = fh.readline().rstrip("\n\r")
    except Exception:
        first_line = ""
    if first_line != expected_title:
        out = Output()
        out.addTitle("Harvest")
        out.newLine()
        out.write_to_file(harvest_md)
    free_engines = ['baidu','certspotter','chaos','commoncrawl','crtsh','duckduckgo','gitlab','hackertarget','hudsonrock','linkedin','linkedin_links','netcraft','omnisint','otx','qwant','rapiddns','robtex','subdomaincenter','subdomainfinderc99','sublist3r','threatcrowd','threatminer','waybackarchive','yahoo']
    # Child executor in ./recon/harvest
    child_exec = Execute(workdir=Path(executor.workdir) / "recon/harvest")
    
    # Run theHarvester
    harvest_cmd = f"theHarvester -d {domain} -b {','.join(free_engines)}"
    _append_command(fs, [harvest_md_rel, record_file], harvest_cmd)
    stdout, stderr, _ = child_exec.run_command(harvest_cmd)
    
    # Store output
    _append_output(fs, harvest_md_rel, stdout or stderr or "")


def run_shodan(domain: str, fs: FileSystem, executor: Execute, record_file: str = "record.md") -> None:
    """Execution set 4: recon/shodan with shodan search."""
    recon_dir = fs.base.joinpath("recon")
    if not recon_dir.exists():
        fs.createFolder("recon")
    shodan_dir = recon_dir.joinpath("shodan")
    if not shodan_dir.exists():
        fs.createFolder("shodan", location="recon")
    
    shodan_md_rel = "recon/shodan/shodan.md"
    shodan_md_full = fs.base.joinpath(shodan_md_rel)
    if not shodan_md_full.exists():
        shodan_md = fs.createFile("shodan.md", location="recon/shodan")
    else:
        shodan_md = shodan_md_full
    
    expected_title = "# Shodan"
    first_line = ""
    try:
        with shodan_md.open("r", encoding="utf-8") as fh:
            first_line = fh.readline().rstrip("\n\r")
    except Exception:
        first_line = ""
    if first_line != expected_title:
        out = Output()
        out.addTitle("Shodan")
        out.newLine()
        out.write_to_file(shodan_md)
    
    # Child executor in ./recon/shodan
    child_exec = Execute(workdir=Path(executor.workdir) / "recon/shodan")
    
    # Run shodan search
    shodan_cmd = f"shodan search hostname:{domain} --fields ip_str,port,org,data --limit 100"
    _append_command(fs, [shodan_md_rel, record_file], shodan_cmd)
    stdout, stderr, _ = child_exec.run_command(shodan_cmd)
    
    # Store output
    _append_output(fs, shodan_md_rel, stdout or stderr or "")


def run_whoami(domain: str, fs: FileSystem, executor: Execute, record_file: str = "record.md") -> None:
    """Execution set 1: recon/whoami.md with host/whois steps and outputs."""
    # Ensure folder exists (check first)
    recon_dir = fs.base.joinpath("recon")
    if not recon_dir.exists():
        fs.createFolder("recon")
    whoami_rel = "recon/whoami.md"
    whoami_full = fs.base.joinpath(whoami_rel)
    if not whoami_full.exists():
        whoami_path = fs.createFile("whoami.md", location="recon")
    else:
        whoami_path = whoami_full

    # Title
    # Add title only if first line does not already match
    expected_title = "# WhoAmI"
    first_line = ""
    try:
        with whoami_path.open("r", encoding="utf-8") as fh:
            first_line = fh.readline().rstrip("\n\r")
    except Exception:
        first_line = ""
    if first_line != expected_title:
        head = Output()
        head.addTitle("WhoAmI")
        head.newLine()
        head.write_to_file(whoami_path)

    # host <domain>
    host_cmd = f"host {domain}"
    _append_command(fs, [whoami_rel, record_file], host_cmd)
    stdout, stderr, rc = executor.run_command(host_cmd)
    _append_output(fs, whoami_rel, stdout or stderr or "")
    ip = executor.extract_ip(stdout)

    # whois <domain_IP>
    if ip:
        whois_ip_cmd = f"whois {ip}"
        _append_command(fs, [whoami_rel, record_file], whois_ip_cmd)
        stdout2, stderr2, rc2 = executor.run_command(whois_ip_cmd)
        _append_output(fs, whoami_rel, stdout2 or stderr2 or "")

    # whois <domain>
    whois_domain_cmd = f"whois {domain}"
    _append_command(fs, [whoami_rel, record_file], whois_domain_cmd)
    stdout3, stderr3, rc3 = executor.run_command(whois_domain_cmd)
    _append_output(fs, whoami_rel, stdout3 or stderr3 or "")


def run_subdomains(domain: str, fs: FileSystem, executor: Execute, record_file: str = "record.md") -> None:
    """Execution set 2: recon/subdomains discovery, combine, unique, grep highlights."""
    # Create folders only if absent
    recon_dir = fs.base.joinpath("recon")
    if not recon_dir.exists():
        fs.createFolder("recon")
    sub_dir = recon_dir.joinpath("subdomains")
    if not sub_dir.exists():
        fs.createFolder("subdomains", location="recon")
    sub_rel_dir = "recon/subdomains"
    sub_md_rel = f"{sub_rel_dir}/subdomains.md"
    sub_md_full = fs.base.joinpath(sub_md_rel)
    if not sub_md_full.exists():
        sub_md_path = fs.createFile("subdomains.md", location=sub_rel_dir)
    else:
        sub_md_path = sub_md_full

    # Title
    expected_title = "# Subdomains"
    first_line = ""
    try:
        with sub_md_path.open("r", encoding="utf-8") as fh:
            first_line = fh.readline().rstrip("\n\r")
    except Exception:
        first_line = ""
    if first_line != expected_title:
        head = Output()
        head.addTitle("Subdomains")
        head.newLine()
        head.write_to_file(sub_md_path)

    # Use a child executor scoped to recon/subdomains so file outputs land there
    child_exec = Execute(workdir=Path(executor.workdir) / sub_rel_dir)

    # d) subfinder - domain
    subfinder_cmd = f"subfinder -d {domain} -oD ./ -o subfinder_results.md"
    _append_command(fs, [sub_md_rel, record_file], subfinder_cmd)
    child_exec.run_command(subfinder_cmd)

    # e) crt.sh via curl|jq
    crt_cmd = (
        f"curl \"https://crt.sh/?q=%25.{domain}&output=json\" | jq -r '.[].name_value' | sort -u > crtsh_subdomains.md"
    )
    _append_command(fs, [sub_md_rel, record_file], crt_cmd)
    child_exec.run_command(crt_cmd)

    # f) combine two files
    combine_cmd = "cat subfinder_results.md crtsh_subdomains.md > combined_subdomains.md"
    _append_command(fs, [sub_md_rel, record_file], combine_cmd)
    child_exec.run_command(combine_cmd)

    # g) unique sort
    # Note README mentions .txt here; we'll keep combined_subdomains.md then sort to .txt for clarity
    sort_cmd = "sort -u combined_subdomains.md"
    _append_command(fs, [sub_md_rel, record_file], sort_cmd)
    stdout_sort, stderr_sort, _ = child_exec.run_command(sort_cmd)

    # h) write all_subdomains.txt from sort output
    all_txt_path = Path(child_exec.workdir) / "all_subdomains.txt"
    all_txt_path.write_text(stdout_sort or (stderr_sort or ""))

    # i) store sort output into subdomains.md
    _append_output(fs, sub_md_rel, stdout_sort or stderr_sort or "")

    # j) grep high-value domains
    grep_cmd = (
        "grep -i \"admin|api|vpn|dev|test|staging|internal|portal|login|db|mail|backup|advisor\" all_subdomains.txt"
    )
    _append_command(fs, [sub_md_rel, record_file], grep_cmd)
    stdout_grep, stderr_grep, _ = child_exec.run_command(grep_cmd)

    # k) store grep output
    _append_output(fs, sub_md_rel, stdout_grep or stderr_grep or "")

    # 5) HTTPX execution (README step 5)
    #    Use all_subdomains.txt to find live subdomains and append results
    httpx_out_rel = Path(child_exec.workdir) / "live_subdomains.txt"
    httpx_cmd = (
        f"httpx -l all_subdomains.txt -title -status-code -tech-detect -follow-redirects "
        f"-mc 200,301,302 -o {httpx_out_rel}"
    )
    _append_command(fs, [sub_md_rel, record_file], httpx_cmd)
    child_exec.run_command(httpx_cmd)
    if httpx_out_rel.exists():
        _append_output(fs, sub_md_rel, httpx_out_rel.read_text())
    else:
        _append_output(fs, sub_md_rel, "")

