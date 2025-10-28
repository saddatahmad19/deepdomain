# src/utils/optimized_executor.py
"""
Optimized executor module for DeepDomain.
Integrates atomic operations with optimization patterns from documentation.
"""
import asyncio
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any, Tuple
from concurrent.futures import ThreadPoolExecutor
import time

from .atomic_ops import AsyncCommandRunner, atomic_writer
from ..classes.filesystems import FileSystem


class OptimizedExecutor:
    """
    Optimized executor that implements patterns from optimization documentation.
    Provides atomic writes, concurrent execution, and resource management.
    """
    
    def __init__(self, 
                 max_network_workers: int = 8,
                 max_cpu_workers: int = 2,
                 mode: str = "quick"):
        self.max_network_workers = max_network_workers
        self.max_cpu_workers = max_cpu_workers
        self.mode = mode
        
        # Initialize executors
        self.network_runner = AsyncCommandRunner(max_concurrent=max_network_workers)
        self.cpu_executor = ThreadPoolExecutor(max_workers=max_cpu_workers)
        
        # Tool availability cache
        self._tool_cache = {}
        
        # Configuration based on mode
        self.config = self._get_mode_config(mode)
    
    def _get_mode_config(self, mode: str) -> Dict[str, Any]:
        """Get configuration based on scan mode"""
        configs = {
            "quick": {
                "masscan_rate": 250,
                "masscan_ports": "--top-ports 1000",
                "nmap_timing": "-T3",
                "max_subdomains": 500,
                "max_hosts_detailed": 200,
                "httpx_threads": 4,
                "run_nuclei": False,
                "dnsx_concurrency": 20,
                "gobuster_threads": 10,
                "nikto_maxtime": 300
            },
            "deep": {
                "masscan_rate": 500,
                "masscan_ports": "-p1-65535",
                "nmap_timing": "-T4",
                "max_subdomains": 2000,
                "max_hosts_detailed": 1000,
                "httpx_threads": 8,
                "run_nuclei": True,
                "dnsx_concurrency": 40,
                "gobuster_threads": 20,
                "nikto_maxtime": 600
            }
        }
        return configs.get(mode, configs["quick"])
    
    def check_tools(self, tools: List[str]) -> Dict[str, Optional[str]]:
        """Check tool availability with caching"""
        result = {}
        for tool in tools:
            if tool not in self._tool_cache:
                self._tool_cache[tool] = shutil.which(tool)
            result[tool] = self._tool_cache[tool]
        return result
    
    def get_available_tools(self, tools: List[str]) -> Tuple[List[str], List[str]]:
        """Get available and missing tools"""
        tool_status = self.check_tools(tools)
        available = [tool for tool, path in tool_status.items() if path is not None]
        missing = [tool for tool, path in tool_status.items() if path is None]
        return available, missing
    
    async def run_recon_tools_parallel(self, domain: str, fs: FileSystem, workspace: Path) -> List[str]:
        """
        Run reconnaissance tools in parallel with atomic writes.
        Based on optimization documentation patterns.
        """
        # Define tool commands
        tools_config = [
            {
                "name": "subfinder",
                "command": f"subfinder -d {domain} -silent -t {self.config['httpx_threads']}",
                "output_file": "subfinder.txt",
                "required": True
            },
            {
                "name": "crt.sh",
                "command": f"curl -s 'https://crt.sh/?q=%25.{domain}&output=json' | jq -r '.[].name_value' | sort -u",
                "output_file": "crtsh.txt",
                "required": False
            },
            {
                "name": "theHarvester",
                "command": f"theHarvester -d {domain} -b all -f {workspace}/theharvester.xml",
                "output_file": "theharvester.txt",
                "required": False
            }
        ]
        
        # Check tool availability
        tool_names = [tool["name"] for tool in tools_config]
        available_tools, missing_tools = self.get_available_tools(tool_names)
        
        # Filter to only available tools
        available_configs = [tool for tool in tools_config if tool["name"] in available_tools]
        
        if not available_configs:
            raise RuntimeError("No reconnaissance tools available")
        
        # Prepare commands for parallel execution
        commands = []
        for tool_config in available_configs:
            output_path = workspace / tool_config["output_file"]
            error_path = workspace / f"{tool_config['name']}.err"
            commands.append((
                tool_config["command"],
                output_path,
                error_path
            ))
        
        # Run commands in parallel
        results = await self.network_runner.run_many(commands, cwd=workspace)
        
        # Merge and process results
        all_subdomains = []
        for i, (tool_config, result) in enumerate(zip(available_configs, results)):
            return_code, stdout, stderr = result
            output_path = workspace / tool_config["output_file"]
            
            if return_code == 0 and output_path.exists():
                try:
                    content = output_path.read_text(encoding='utf-8', errors='ignore')
                    subdomains = [line.strip() for line in content.splitlines() if line.strip()]
                    all_subdomains.extend(subdomains)
                except Exception as e:
                    print(f"Error reading {tool_config['name']} output: {e}")
        
        return self._canonicalize_and_cap_subdomains(all_subdomains)
    
    def _canonicalize_and_cap_subdomains(self, subdomains: List[str]) -> List[str]:
        """Canonicalize and cap subdomains based on optimization patterns"""
        # Canonicalize domains
        canonical = []
        seen = set()
        
        for domain in subdomains:
            if not domain:
                continue
            domain = domain.strip().lower()
            domain = domain.lstrip('*.')  # Remove wildcard prefix
            
            # Remove protocols and ports
            domain = domain.replace('https://', '').replace('http://', '')
            domain = domain.split('/')[0].split(':')[0]
            
            if domain and domain not in seen:
                seen.add(domain)
                canonical.append(domain)
        
        # Apply cap
        max_subdomains = self.config["max_subdomains"]
        if len(canonical) > max_subdomains:
            canonical = sorted(canonical)[:max_subdomains]
        
        return canonical
    
    async def run_live_check(self, subdomains: List[str], workspace: Path) -> List[str]:
        """
        Run httpx live check with optimized settings.
        """
        # Check if httpx is available
        httpx_path = shutil.which("httpx")
        if not httpx_path:
            print("httpx not available, skipping live check")
            return subdomains
        
        # Write subdomains to file atomically
        subdomains_file = workspace / "all_subdomains.txt"
        atomic_writer.atomic_write(subdomains_file, '\n'.join(subdomains))
        
        # Run httpx with optimized flags
        httpx_cmd = (
            f"httpx -silent -status-code -title -tech-detect "
            f"-threads {self.config['httpx_threads']} -timeout 10 "
            f"-l {subdomains_file} -o {workspace}/live.txt"
        )
        
        output_path = workspace / "httpx.out"
        error_path = workspace / "httpx.err"
        
        return_code, stdout, stderr = await self.network_runner.run_command_async(
            httpx_cmd,
            workspace,
            output_callback=lambda x: None,  # We'll read from file
            error_callback=lambda x: None
        )
        
        # Parse live hosts
        live_hosts = []
        live_file = workspace / "live.txt"
        if live_file.exists():
            try:
                content = live_file.read_text(encoding='utf-8', errors='ignore')
                for line in content.splitlines():
                    if line.strip():
                        host = line.split()[0].strip().lower()
                        host = host.replace('https://', '').replace('http://', '')
                        host = host.split('/')[0].split(':')[0]
                        if host:
                            live_hosts.append(host)
            except Exception as e:
                print(f"Error reading live hosts: {e}")
        
        return live_hosts
    
    async def run_network_scan(self, live_hosts: List[str], workspace: Path) -> None:
        """
        Run network scanning with optimized settings.
        """
        if not live_hosts:
            print("No live hosts to scan")
            return
        
        # Check tool availability
        masscan_path = shutil.which("masscan")
        nmap_path = shutil.which("nmap")
        
        if not nmap_path:
            print("nmap not available, skipping network scan")
            return
        
        # Write live hosts to file
        hosts_file = workspace / "live_hosts.txt"
        atomic_writer.atomic_write(hosts_file, '\n'.join(live_hosts))
        
        # Run quick nmap scan
        nmap_quick_cmd = (
            f"nmap -sS -Pn {self.config['nmap_timing']} -F "
            f"--max-retries 1 --min-parallelism 10 "
            f"-iL {hosts_file} -oA {workspace}/quick_scan"
        )
        
        await self.network_runner.run_command_async(
            nmap_quick_cmd,
            workspace,
            output_callback=lambda x: None,
            error_callback=lambda x: None
        )
        
        # Run masscan if available and in deep mode
        if masscan_path and self.mode == "deep":
            masscan_cmd = (
                f"masscan {self.config['masscan_ports']} "
                f"--rate {self.config['masscan_rate']} "
                f"--wait 10 -iL {hosts_file} -oJ {workspace}/masscan.json"
            )
            
            await self.network_runner.run_command_async(
                masscan_cmd,
                workspace,
                output_callback=lambda x: None,
                error_callback=lambda x: None
            )
        
        # Run detailed nmap if host count is within limits
        max_detailed = self.config["max_hosts_detailed"]
        if len(live_hosts) <= max_detailed or self.mode == "deep":
            nmap_detailed_cmd = (
                f"nmap -sS -sV -Pn -p- {self.config['nmap_timing']} "
                f"--max-retries 2 --min-rate 50 --host-timeout 5m "
                f"-iL {hosts_file} -oA {workspace}/detailed_scan"
            )
            
            await self.network_runner.run_command_async(
                nmap_detailed_cmd,
                workspace,
                output_callback=lambda x: None,
                error_callback=lambda x: None
            )
        else:
            print(f"Skipping detailed nmap: {len(live_hosts)} hosts > {max_detailed}")
    
    async def run_enumeration(self, live_hosts: List[str], workspace: Path) -> None:
        """
        Run enumeration tools with optimized settings.
        """
        if not live_hosts:
            print("No live hosts to enumerate")
            return
        
        # Check tool availability
        tools_to_check = ["nikto", "gobuster", "nuclei"]
        available_tools, missing_tools = self.get_available_tools(tools_to_check)
        
        if missing_tools:
            print(f"Missing tools: {', '.join(missing_tools)}")
        
        # Run enumeration for each live host
        for host in live_hosts[:10]:  # Limit to first 10 hosts for performance
            host_workspace = workspace / f"enum_{host.replace('.', '_')}"
            host_workspace.mkdir(exist_ok=True)
            
            # Run nikto if available
            if "nikto" in available_tools:
                nikto_cmd = (
                    f"nikto -h https://{host} -Tuning 1234567890 "
                    f"-maxtime {self.config['nikto_maxtime']} "
                    f"-output {host_workspace}/nikto.txt"
                )
                
                await self.network_runner.run_command_async(
                    nikto_cmd,
                    workspace,
                    output_callback=lambda x: None,
                    error_callback=lambda x: None
                )
            
            # Run gobuster if available
            if "gobuster" in available_tools:
                gobuster_cmd = (
                    f"gobuster dir -u https://{host} "
                    f"-w /usr/share/wordlists/dirb/common.txt "
                    f"-t {self.config['gobuster_threads']} "
                    f"-o {host_workspace}/gobuster.txt"
                )
                
                await self.network_runner.run_command_async(
                    gobuster_cmd,
                    workspace,
                    output_callback=lambda x: None,
                    error_callback=lambda x: None
                )
        
        # Run nuclei if available and enabled
        if "nuclei" in available_tools and self.config["run_nuclei"]:
            nuclei_cmd = (
                f"nuclei -l {workspace}/live_hosts.txt "
                f"-c {self.config['httpx_threads']} "
                f"-rate-limit 20 -timeout 10 "
                f"-o {workspace}/nuclei_results.txt"
            )
            
            await self.network_runner.run_command_async(
                nuclei_cmd,
                workspace,
                output_callback=lambda x: None,
                error_callback=lambda x: None
            )
    
    def cleanup(self):
        """Clean up resources"""
        self.network_runner.stop_all_processes()
        self.cpu_executor.shutdown(wait=True)
