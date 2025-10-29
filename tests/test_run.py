#!/usr/bin/env python3
"""
Test runner for DeepDomain that emulates the full TUI and process flow
without actually running real commands. This is a mock implementation
that demonstrates the complete workflow in about 15 seconds.
"""

import time
import random
from pathlib import Path
from typing import List, Tuple
from datetime import datetime

# Mock classes to simulate the real functionality
class MockFileSystem:
    """Mock FileSystem that simulates file operations without actually creating files"""
    
    def __init__(self, base: Path):
        self.base = Path(base)
        self.created_files = []
        self.created_folders = []
    
    def createFolder(self, name: str, location: str = "") -> Path:
        """Simulate folder creation"""
        loc = self.base.joinpath(location) if location else self.base
        path = loc.joinpath(name)
        self.created_folders.append(str(path))
        print(f"[FOLDER] Created folder: {path}")
        return path
    
    def createFile(self, name: str, location: str = "") -> Path:
        """Simulate file creation"""
        if "." not in name:
            name = f"{name}.md"
        loc = self.base.joinpath(location) if location else self.base
        full = loc.joinpath(name)
        self.created_files.append(str(full))
        print(f"[FILE] Created file: {full}")
        return full
    
    def appendOutput(self, file_location: str, output_text):
        """Simulate appending output to files"""
        print(f"[APPEND] Appended output to: {file_location}")


class MockExecute:
    """Mock Execute class that simulates command execution"""
    
    def __init__(self, workdir: Path, tui=None):
        self.workdir = workdir
        self.tui = tui
        self.command_count = 0
    
    def run_command(self, command: str) -> Tuple[str, str, int]:
        """Simulate command execution with mock output"""
        self.command_count += 1
        print(f"[CMD] Executing command #{self.command_count}: {command}")
        
        # Simulate command execution time
        time.sleep(0.1)
        
        # Generate mock output based on command type
        if "host" in command:
            stdout = f"example.com has address 192.168.1.100\n"
            stderr = ""
            return_code = 0
        elif "whois" in command:
            stdout = f"Domain: example.com\nRegistrar: Mock Registrar\n"
            stderr = ""
            return_code = 0
        elif "subfinder" in command:
            stdout = f"sub1.example.com\nsub2.example.com\napi.example.com\n"
            stderr = ""
            return_code = 0
        elif "theHarvester" in command:
            stdout = f"Found emails: admin@example.com, info@example.com\n"
            stderr = ""
            return_code = 0
        elif "shodan" in command:
            stdout = f"192.168.1.100:80 - Apache/2.4.41\n"
            stderr = ""
            return_code = 0
        elif "dnsx" in command:
            stdout = f"sub1.example.com [192.168.1.101]\nsub2.example.com [192.168.1.102]\n"
            stderr = ""
            return_code = 0
        elif "httpx" in command:
            stdout = f"https://sub1.example.com [200] [Apache]\nhttps://sub2.example.com [301]\n"
            stderr = ""
            return_code = 0
        elif "nmap" in command:
            stdout = f"Starting Nmap scan...\nHost is up (0.1s latency).\n80/tcp open  http\n443/tcp open  https\n"
            stderr = ""
            return_code = 0
        elif "masscan" in command:
            stdout = f"Starting masscan...\nDiscovered open port 80/tcp on 192.168.1.100\n"
            stderr = ""
            return_code = 0
        elif "nikto" in command:
            stdout = f"Nikto scan complete\nFound 3 potential vulnerabilities\n"
            stderr = ""
            return_code = 0
        elif "gobuster" in command:
            stdout = f"Found: /admin (Status: 200)\nFound: /api (Status: 200)\n"
            stderr = ""
            return_code = 0
        elif "nuclei" in command:
            stdout = f"Nuclei scan complete\nFound 2 medium severity issues\n"
            stderr = ""
            return_code = 0
        else:
            stdout = f"Mock output for: {command}\n"
            stderr = ""
            return_code = 0
        
        return stdout, stderr, return_code
    
    def extract_ip(self, host_output: str) -> str:
        """Extract IP from mock host output"""
        return "192.168.1.100"


class MockTUI:
    """Mock TUI that simulates the Textual interface"""
    
    def __init__(self, domain: str, output_dir: Path):
        self.domain = domain
        self.output_dir = output_dir
        self.current_phase = "Initializing"
        self.phase_progress = 0
        self.status_messages = []
        self.current_command = ""
        self.is_running = False
    
    def update_phase(self, phase: str, progress: int = 0):
        """Update the current phase"""
        self.current_phase = phase
        self.phase_progress = progress
        print(f"[PHASE] Phase: {phase} ({progress}%)")
    
    def add_status_message(self, message: str, msg_type: str = "info"):
        """Add a status message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        icon = "[OK]" if msg_type == "success" else "[INFO]" if msg_type == "info" else "[WARN]" if msg_type == "warning" else "[ERR]"
        formatted_msg = f"[{timestamp}] {icon} {message}"
        self.status_messages.append(formatted_msg)
        print(f"[STATUS] {formatted_msg}")
    
    def start_command(self, command: str):
        """Start tracking a command"""
        self.current_command = command
        self.is_running = True
        print(f"[START] Starting: {command}")
    
    def add_command_output(self, text: str):
        """Add command output"""
        if self.is_running and text.strip():
            print(f"[OUTPUT] Output: {text.strip()[:50]}...")
    
    def finish_command(self):
        """Mark command as finished"""
        self.is_running = False
        print(f"[DONE] Command completed: {self.current_command}")
    
    def run_command_live(self, command: str, workdir: Path) -> Tuple[str, str, int]:
        """Run command with live output simulation"""
        self.start_command(command)
        
        # Simulate live output streaming
        stdout, stderr, return_code = self.run_command_sync(command)
        
        # Simulate streaming the output
        for line in stdout.split('\n'):
            if line.strip():
                self.add_command_output(line)
                time.sleep(0.05)  # Simulate streaming delay
        
        self.finish_command()
        return stdout, stderr, return_code
    
    def run_command_sync(self, command: str) -> Tuple[str, str, int]:
        """Synchronous command execution for simulation"""
        time.sleep(0.2)  # Simulate command execution time
        
        # Generate mock output
        if "host" in command:
            stdout = f"example.com has address 192.168.1.100\n"
        elif "whois" in command:
            stdout = f"Domain: example.com\nRegistrar: Mock Registrar\n"
        elif "subfinder" in command:
            stdout = f"sub1.example.com\nsub2.example.com\napi.example.com\n"
        elif "theHarvester" in command:
            stdout = f"Found emails: admin@example.com, info@example.com\n"
        elif "shodan" in command:
            stdout = f"192.168.1.100:80 - Apache/2.4.41\n"
        elif "dnsx" in command:
            stdout = f"sub1.example.com [192.168.1.101]\nsub2.example.com [192.168.1.102]\n"
        elif "httpx" in command:
            stdout = f"https://sub1.example.com [200] [Apache]\nhttps://sub2.example.com [301]\n"
        elif "nmap" in command:
            stdout = f"Starting Nmap scan...\nHost is up (0.1s latency).\n80/tcp open  http\n443/tcp open  https\n"
        elif "masscan" in command:
            stdout = f"Starting masscan...\nDiscovered open port 80/tcp on 192.168.1.100\n"
        elif "nikto" in command:
            stdout = f"Nikto scan complete\nFound 3 potential vulnerabilities\n"
        elif "gobuster" in command:
            stdout = f"Found: /admin (Status: 200)\nFound: /api (Status: 200)\n"
        elif "nuclei" in command:
            stdout = f"Nuclei scan complete\nFound 2 medium severity issues\n"
        else:
            stdout = f"Mock output for: {command}\n"
        
        return stdout, "", 0


def mock_run_whoami(domain: str, fs: MockFileSystem, executor: MockExecute, tui: MockTUI):
    """Mock execution set 1: WhoAmI investigation"""
    tui.add_status_message("Running whoami execution set...", "info")
    
    # Create whoami.md file
    fs.createFile("whoami.md", location="recon")
    
    # Run host command
    host_cmd = f"host {domain}"
    stdout, stderr, rc = executor.run_command(host_cmd)
    tui.add_command_output(stdout)
    
    # Extract IP and run whois
    ip = executor.extract_ip(stdout)
    if ip:
        whois_ip_cmd = f"whois {ip}"
        stdout2, stderr2, rc2 = executor.run_command(whois_ip_cmd)
        tui.add_command_output(stdout2)
    
    # Run whois on domain
    whois_domain_cmd = f"whois {domain}"
    stdout3, stderr3, rc3 = executor.run_command(whois_domain_cmd)
    tui.add_command_output(stdout3)
    
    tui.add_status_message("WhoAmI investigation complete", "success")


def mock_run_subdomains(domain: str, fs: MockFileSystem, executor: MockExecute, tui: MockTUI):
    """Mock execution set 2: Subdomain discovery"""
    tui.add_status_message("Discovering subdomains...", "info")
    
    # Create subdomains directory and file
    fs.createFolder("subdomains", location="recon")
    fs.createFile("subdomains.md", location="recon/subdomains")
    
    # Run subfinder
    subfinder_cmd = f"subfinder -d {domain} -oD ./ -o subfinder_results.md"
    executor.run_command(subfinder_cmd)
    
    # Run crt.sh query
    crt_cmd = f"curl \"https://crt.sh/?q=%25.{domain}&output=json\" | jq -r '.[].name_value' | sort -u > crtsh_subdomains.md"
    executor.run_command(crt_cmd)
    
    # Combine and sort results
    combine_cmd = "cat subfinder_results.md crtsh_subdomains.md > combined_subdomains.md"
    executor.run_command(combine_cmd)
    
    sort_cmd = "sort -u combined_subdomains.md"
    stdout_sort, stderr_sort, _ = executor.run_command(sort_cmd)
    tui.add_command_output(stdout_sort)
    
    # Run httpx on live subdomains
    httpx_cmd = f"httpx -l all_subdomains.txt -title -status-code -tech-detect -follow-redirects -mc 200,301,302 -o live_subdomains.txt"
    executor.run_command(httpx_cmd)
    
    tui.add_status_message("Subdomain discovery complete", "success")


def mock_run_harvest(domain: str, fs: MockFileSystem, executor: MockExecute, tui: MockTUI):
    """Mock execution set 3: Information harvesting"""
    tui.add_status_message("Harvesting information...", "info")
    
    # Create harvest directory and file
    fs.createFolder("harvest", location="recon")
    fs.createFile("harvest.md", location="recon/harvest")
    
    # Run theHarvester
    harvest_cmd = f"theHarvester -d {domain} -b baidu,certspotter,chaos,commoncrawl,crtsh"
    stdout, stderr, _ = executor.run_command(harvest_cmd)
    tui.add_command_output(stdout)
    
    tui.add_status_message("Information harvesting complete", "success")


def mock_run_shodan(domain: str, fs: MockFileSystem, executor: MockExecute, tui: MockTUI):
    """Mock execution set 4: Shodan reconnaissance"""
    tui.add_status_message("Querying Shodan...", "info")
    
    # Create shodan directory and file
    fs.createFolder("shodan", location="recon")
    fs.createFile("shodan.md", location="recon/shodan")
    
    # Run shodan search
    shodan_cmd = f"shodan search hostname:{domain} --fields ip_str,port,org,data --limit 100"
    stdout, stderr, _ = executor.run_command(shodan_cmd)
    tui.add_command_output(stdout)
    
    tui.add_status_message("Shodan reconnaissance complete", "success")


def mock_run_resolve(fs: MockFileSystem, executor: MockExecute, tui: MockTUI):
    """Mock execution set 5: Host resolution"""
    tui.add_status_message("Resolving hosts and live endpoints...", "info")
    
    # Create resolve directory and file
    fs.createFolder("resolve", location="scanning")
    fs.createFile("resolved.md", location="scanning/resolve")
    
    # Run dnsx
    dnsx_cmd = "cat all_subdomains.txt | dnsx -silent -a -aaaa -resp -o resolved_hosts.txt"
    executor.run_command(dnsx_cmd)
    
    # Run httpx
    httpx_cmd = "httpx -l all_subdomains.txt -title -status-code -tech-detect -follow-redirects -mc 200,301,302 -o live_subdomains.txt"
    executor.run_command(httpx_cmd)
    
    tui.add_status_message("Host resolution complete", "success")


def mock_run_network_discover(fs: MockFileSystem, executor: MockExecute, tui: MockTUI):
    """Mock execution set 6: Network discovery"""
    tui.add_status_message("Performing network discovery...", "info")
    
    # Create network discovery directories
    fs.createFolder("network_discover", location="scanning")
    fs.createFolder("quick", location="scanning/network_discover")
    fs.createFolder("detailed", location="scanning/network_discover")
    
    fs.createFile("quick_discovery.md", location="scanning/network_discover/quick")
    fs.createFile("detailed_discovery.md", location="scanning/network_discover/detailed")
    
    # Run nmap ping sweep
    nmap_ping_cmd = "nmap -sS -Pn -T4 -F -oA resolved_hosts.txt -oN nmap_ping.txt"
    executor.run_command(nmap_ping_cmd)
    
    # Run masscan
    masscan_cmd = "masscan -p1-65535 --rate=1000 -iL resolved_hosts.txt --banners -oG masscan_results.grep"
    executor.run_command(masscan_cmd)
    
    # Run detailed nmap
    nmap_det_cmd = "nmap -sV -O -sC -T3 -p 80,443 -iL resolved_hosts.txt -oA nmap_detailed"
    executor.run_command(nmap_det_cmd)
    
    tui.add_status_message("Network discovery complete", "success")


def mock_run_vulnerable(fs: MockFileSystem, executor: MockExecute, tui: MockTUI):
    """Mock execution sets 13-15: Vulnerability enumeration"""
    tui.add_status_message("Running vulnerability enumeration...", "info")
    
    # Create vulnerable directory and file
    fs.createFolder("vulnerable", location="enumeration")
    fs.createFile("vulnerable.md", location="enumeration/vulnerable")
    
    # Run nikto
    nikto_cmd = "nikto -h -Tuning 1234567890 -o nikto_results.txt $(cat live_subdomains.txt | cut -d' ' -f1)"
    executor.run_command(nikto_cmd)
    
    # Run gobuster
    gobuster_cmd = "gobuster dir -u $(head -n1 live_subdomains.txt) -w /usr/share/wordlists/dirb/common.txt -t 50 -o gobuster_results.txt -x php,html,txt"
    executor.run_command(gobuster_cmd)
    
    # Run nuclei
    nuclei_cmd = "nuclei -l live_subdomains.txt -t /usr/share/nuclei-templates/ -severity low,medium,high,critical -o nuclei_vulns.txt"
    executor.run_command(nuclei_cmd)
    
    tui.add_status_message("Vulnerability enumeration complete", "success")


def mock_run_recon(domain: str, fs: MockFileSystem, executor: MockExecute, tui: MockTUI):
    """Mock reconnaissance phase"""
    tui.update_phase("Reconnaissance Phase", 30)
    tui.add_status_message("Starting reconnaissance phase...", "info")
    
    # Create recon directory
    fs.createFolder("recon")
    
    # Run all reconnaissance execution sets
    mock_run_whoami(domain, fs, executor, tui)
    mock_run_subdomains(domain, fs, executor, tui)
    mock_run_harvest(domain, fs, executor, tui)
    mock_run_shodan(domain, fs, executor, tui)
    
    tui.add_status_message("Reconnaissance phase complete", "success")


def mock_run_scanning(fs: MockFileSystem, executor: MockExecute, tui: MockTUI):
    """Mock scanning phase"""
    tui.update_phase("Scanning Phase", 60)
    tui.add_status_message("Starting scanning phase...", "info")
    
    # Create scanning directory
    fs.createFolder("scanning")
    
    # Run scanning execution sets
    mock_run_resolve(fs, executor, tui)
    mock_run_network_discover(fs, executor, tui)
    
    tui.add_status_message("Scanning phase complete", "success")


def mock_run_enumeration(fs: MockFileSystem, executor: MockExecute, tui: MockTUI):
    """Mock enumeration phase"""
    tui.update_phase("Enumeration Phase", 80)
    tui.add_status_message("Starting enumeration phase...", "info")
    
    # Create enumeration directory
    fs.createFolder("enumeration")
    
    # Run enumeration execution sets
    mock_run_vulnerable(fs, executor, tui)
    
    tui.add_status_message("Enumeration phase complete", "success")


def main():
    """Main test function that emulates the complete DeepDomain workflow"""
    
    # Configuration
    domain = "example.com"
    output_dir = Path("./test_output")
    output_dir.mkdir(exist_ok=True)
    
    print("=" * 80)
    print("DeepDomain Test Run - Mock Implementation")
    print("=" * 80)
    print(f"Target Domain: {domain}")
    print(f"Output Directory: {output_dir}")
    print(f"Estimated Duration: ~15 seconds")
    print("=" * 80)
    print()
    
    # Initialize mock components
    fs = MockFileSystem(output_dir)
    tui = MockTUI(domain, output_dir)
    executor = MockExecute(output_dir, tui)
    
    # Create record.md file
    fs.createFile("record.md", location="")
    tui.add_status_message("Workspace initialized", "success")
    tui.update_phase("Ready to begin", 20)
    
    try:
        # Run the main phases
        start_time = time.time()
        
        # Phase 1: Reconnaissance
        mock_run_recon(domain, fs, executor, tui)
        
        # Phase 2: Scanning
        mock_run_scanning(fs, executor, tui)
        
        # Phase 3: Enumeration
        mock_run_enumeration(fs, executor, tui)
        
        # Final completion
        tui.update_phase("Complete", 100)
        tui.add_status_message("DeepDomain scan complete!", "success")
        tui.add_status_message(f"Results saved to: {output_dir}", "info")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print()
        print("=" * 80)
        print("[SUCCESS] DeepDomain Test Run Complete!")
        print("=" * 80)
        print(f"[STATS] Total Duration: {duration:.2f} seconds")
        print(f"[STATS] Files Created: {len(fs.created_files)}")
        print(f"[STATS] Folders Created: {len(fs.created_folders)}")
        print(f"[STATS] Commands Executed: {executor.command_count}")
        print(f"[STATS] Status Messages: {len(tui.status_messages)}")
        print("=" * 80)
        print()
        print("[STRUCTURE] Summary of Created Structure:")
        print("├── record.md")
        print("├── recon/")
        print("│   ├── whoami.md")
        print("│   ├── subdomains/")
        print("│   │   └── subdomains.md")
        print("│   ├── harvest/")
        print("│   │   └── harvest.md")
        print("│   └── shodan/")
        print("│       └── shodan.md")
        print("├── scanning/")
        print("│   ├── resolve/")
        print("│   │   └── resolved.md")
        print("│   └── network_discover/")
        print("│       ├── quick/")
        print("│       │   └── quick_discovery.md")
        print("│       └── detailed/")
        print("│           └── detailed_discovery.md")
        print("└── enumeration/")
        print("    └── vulnerable/")
        print("        └── vulnerable.md")
        print()
        print("[SUCCESS] Test completed successfully! This demonstrates the complete")
        print("          DeepDomain workflow without actually running real commands.")
        
    except Exception as e:
        tui.add_status_message(f"Test error: {str(e)}", "error")
        print(f"[ERROR] Test failed with error: {str(e)}")


if __name__ == "__main__":
    main()
