#!/usr/bin/env python3
"""
Test file for DeepDomain execution flow from main.py through cli.py to recon.py
Tests the integration between CLI, TUI, and reconnaissance phases.
Stops before scanning phase as requested.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess
from typing import List, Tuple

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from classes.filesystems import FileSystem
from classes.output import Output
from classes.execute import Execute
from process.recon import run_whoami, run_subdomains, run_harvest, run_shodan
from utils.cli import run_recon, _check_tools


class MockTUI:
    """Mock TUI class to simulate TUI behavior without actual GUI"""
    
    def __init__(self):
        self.status_messages = []
        self.current_phase = "Initializing"
        self.phase_progress = 0
        self.command_outputs = []
        self.current_command = None
        
    def add_status_message(self, message: str, msg_type: str = "info"):
        """Add a status message"""
        timestamp = "12:00:00"  # Mock timestamp
        icon_map = {
            "success": "✓",
            "info": "ℹ", 
            "warning": "⚠",
            "error": "✗"
        }
        icon = icon_map.get(msg_type, "ℹ")
        formatted_msg = f"[dim]{timestamp}[/dim] [{msg_type}]{icon}[/{msg_type}] {message}"
        self.status_messages.append(formatted_msg)
        print(f"TUI Status: {message} ({msg_type})")
        
    def update_phase(self, phase: str, progress: int = 0):
        """Update current phase and progress"""
        self.current_phase = phase
        self.phase_progress = progress
        print(f"TUI Phase: {phase} ({progress}%)")
        
    def start_command(self, command: str):
        """Start tracking a command"""
        self.current_command = command
        print(f"TUI Command Started: {command}")
        
    def finish_command(self):
        """Finish tracking current command"""
        if self.current_command:
            print(f"TUI Command Finished: {self.current_command}")
            self.current_command = None
            
    def run_command_live(self, command: str, workdir: Path) -> Tuple[str, str, int]:
        """Mock command execution"""
        print(f"Executing: {command}")
        print(f"Working directory: {workdir}")
        
        # Mock different commands with realistic outputs
        if "host " in command:
            domain = command.split()[-1]
            return f"{domain} has address 192.168.1.100\n{domain} has IPv6 address 2001:db8::1", "", 0
        elif "whois " in command:
            target = command.split()[-1]
            return f"Domain: {target}\nRegistrar: Example Registrar\nStatus: active", "", 0
        elif "subfinder -d" in command:  # More specific check for subfinder with -d flag
            domain = command.split("-d")[1].strip().split()[0]
            return f"subdomain1.{domain}\nsubdomain2.{domain}\nwww.{domain}", "", 0
        elif "curl" in command and "crt.sh" in command:
            domain = command.split("%25.")[1].split("&")[0]
            return f'[{{"name_value": "api.{domain}"}}, {{"name_value": "admin.{domain}"}}]', "", 0
        elif "theHarvester" in command:
            domain = command.split("-d")[1].strip().split()[0]
            return f"Searching for {domain}...\nFound: admin@{domain}\nFound: info@{domain}", "", 0
        elif "shodan" in command:
            domain = command.split("hostname:")[1].split()[0]
            return f"192.168.1.100:80\n192.168.1.100:443\nOrganization: Example Corp", "", 0
        elif "httpx" in command:
            return "https://subdomain1.example.com [200] [Apache]\nhttps://subdomain2.example.com [301] [nginx]", "", 0
        elif "cat " in command and ">" in command:  # Handle file combination commands
            return "", "", 0  # Success, no output for redirection commands
        elif "sort -u" in command:  # Handle sort commands
            return "subdomain1.example.com\nsubdomain2.example.com\nwww.example.com", "", 0
        elif "grep -i" in command:  # Handle grep commands
            return "admin.example.com\napi.example.com", "", 0
        else:
            return f"Mock output for: {command}", "", 0


class TestDeepDomainFlow:
    """Test class for DeepDomain execution flow"""
    
    def __init__(self):
        self.temp_dir = None
        self.fs = None
        self.executor = None
        self.mock_tui = None
        
    def setup(self):
        """Set up test environment"""
        print("=" * 60)
        print("Setting up DeepDomain Flow Test")
        print("=" * 60)
        
        # Create temporary directory for test
        self.temp_dir = Path(tempfile.mkdtemp(prefix="deepdomain_test_"))
        print(f"Test directory: {self.temp_dir}")
        
        # Initialize components
        self.fs = FileSystem(self.temp_dir)
        self.mock_tui = MockTUI()
        self.executor = Execute(workdir=self.temp_dir, tui=self.mock_tui)
        
        print("Test environment setup complete!")
        
    def teardown(self):
        """Clean up test environment"""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            print(f"Cleaned up test directory: {self.temp_dir}")
            
    def test_tool_check(self):
        """Test tool availability checking"""
        print("\n" + "=" * 40)
        print("Testing Tool Check")
        print("=" * 40)
        
        # Test with some common tools
        test_tools = ["host", "whois", "curl", "jq"]
        missing, install_cmd = _check_tools(test_tools)
        
        print(f"Test tools: {test_tools}")
        print(f"Missing tools: {missing}")
        print(f"Install command: {install_cmd}")
        
        # Most tools should be available on most systems
        assert len(missing) < len(test_tools), f"Too many missing tools: {missing}"
        print("✓ Tool check test passed")
        
    def test_filesystem_operations(self):
        """Test FileSystem operations"""
        print("\n" + "=" * 40)
        print("Testing FileSystem Operations")
        print("=" * 40)
        
        # Test folder creation
        recon_path = self.fs.createFolder("recon")
        assert recon_path.exists(), "Recon folder should exist"
        print(f"✓ Created folder: {recon_path}")
        
        # Test file creation
        test_file = self.fs.createFile("test.md", location="recon")
        assert test_file.exists(), "Test file should exist"
        print(f"✓ Created file: {test_file}")
        
        # Test file writing
        test_file.write_text("# Test\nThis is a test file.")
        content = test_file.read_text()
        assert "Test" in content, "File content should be written"
        print(f"✓ File content written and verified")
        
    def test_output_class(self):
        """Test Output class functionality"""
        print("\n" + "=" * 40)
        print("Testing Output Class")
        print("=" * 40)
        
        output = Output()
        output.addTitle("Test Title")
        output.addCommand("echo 'Hello World'")
        output.addCommandOutput("Hello World")
        output.newLine()
        
        text = output.text()
        assert "# Test Title" in text, "Title should be in output"
        assert "echo 'Hello World'" in text, "Command should be in output"
        assert "Hello World" in text, "Output should be in text"
        
        print("✓ Output class test passed")
        print("Sample output:")
        print(text)
        
    def test_execute_class(self):
        """Test Execute class functionality"""
        print("\n" + "=" * 40)
        print("Testing Execute Class")
        print("=" * 40)
        
        # Test command execution
        stdout, stderr, rc = self.executor.run_command("host example.com")
        assert rc == 0, f"Command should succeed, got return code {rc}"
        assert "example.com" in stdout, "Output should contain domain"
        
        print(f"✓ Command executed successfully")
        print(f"Output: {stdout}")
        
        # Test IP extraction
        ip = self.executor.extract_ip(stdout)
        assert ip is not None, "Should extract IP from host output"
        print(f"✓ Extracted IP: {ip}")
        
    def test_recon_whoami(self):
        """Test reconnaissance whoami phase"""
        print("\n" + "=" * 40)
        print("Testing Reconnaissance - WhoAmI")
        print("=" * 40)
        
        domain = "example.com"
        
        # Run whoami phase
        run_whoami(domain, self.fs, self.executor)
        
        # Check if files were created
        whoami_file = self.temp_dir / "recon" / "whoami.md"
        record_file = self.temp_dir / "record.md"
        
        assert whoami_file.exists(), "WhoAmI file should exist"
        assert record_file.exists(), "Record file should exist"
        
        # Check file contents
        whoami_content = whoami_file.read_text()
        record_content = record_file.read_text()
        
        assert "WhoAmI" in whoami_content, "WhoAmI file should contain title"
        assert "host example.com" in whoami_content, "Should contain host command"
        assert "whois" in whoami_content, "Should contain whois commands"
        
        print(f"✓ WhoAmI phase completed successfully")
        print(f"WhoAmI file size: {len(whoami_content)} characters")
        print(f"Record file size: {len(record_content)} characters")
        
    def test_recon_subdomains(self):
        """Test reconnaissance subdomains phase"""
        print("\n" + "=" * 40)
        print("Testing Reconnaissance - Subdomains")
        print("=" * 40)
        
        domain = "example.com"
        
        # Run subdomains phase
        run_subdomains(domain, self.fs, self.executor)
        
        # Check if files were created
        subdomains_file = self.temp_dir / "recon" / "subdomains" / "subdomains.md"
        all_subdomains_file = self.temp_dir / "recon" / "subdomains" / "all_subdomains.txt"
        
        assert subdomains_file.exists(), "Subdomains file should exist"
        assert all_subdomains_file.exists(), "All subdomains file should exist"
        
        # Check file contents
        subdomains_content = subdomains_file.read_text()
        all_subdomains_content = all_subdomains_file.read_text()
        
        assert "Subdomains" in subdomains_content, "Should contain title"
        assert "subfinder" in subdomains_content, "Should contain subfinder command"
        assert "crt.sh" in subdomains_content, "Should contain crt.sh command"
        
        print(f"✓ Subdomains phase completed successfully")
        print(f"Subdomains file size: {len(subdomains_content)} characters")
        print(f"All subdomains file size: {len(all_subdomains_content)} characters")
        
    def test_recon_harvest(self):
        """Test reconnaissance harvest phase"""
        print("\n" + "=" * 40)
        print("Testing Reconnaissance - Harvest")
        print("=" * 40)
        
        domain = "example.com"
        
        # Run harvest phase
        run_harvest(domain, self.fs, self.executor)
        
        # Check if files were created
        harvest_file = self.temp_dir / "recon" / "harvest" / "harvest.md"
        
        assert harvest_file.exists(), "Harvest file should exist"
        
        # Check file contents
        harvest_content = harvest_file.read_text()
        
        assert "Harvest" in harvest_content, "Should contain title"
        assert "theHarvester" in harvest_content, "Should contain theHarvester command"
        
        print(f"✓ Harvest phase completed successfully")
        print(f"Harvest file size: {len(harvest_content)} characters")
        
    def test_recon_shodan(self):
        """Test reconnaissance shodan phase"""
        print("\n" + "=" * 40)
        print("Testing Reconnaissance - Shodan")
        print("=" * 40)
        
        domain = "example.com"
        
        # Run shodan phase
        run_shodan(domain, self.fs, self.executor)
        
        # Check if files were created
        shodan_file = self.temp_dir / "recon" / "shodan" / "shodan.md"
        
        assert shodan_file.exists(), "Shodan file should exist"
        
        # Check file contents
        shodan_content = shodan_file.read_text()
        
        assert "Shodan" in shodan_content, "Should contain title"
        assert "shodan search" in shodan_content, "Should contain shodan command"
        
        print(f"✓ Shodan phase completed successfully")
        print(f"Shodan file size: {len(shodan_content)} characters")
        
    def test_full_recon_phase(self):
        """Test the complete reconnaissance phase"""
        print("\n" + "=" * 40)
        print("Testing Full Reconnaissance Phase")
        print("=" * 40)
        
        domain = "example.com"
        
        # Run the complete reconnaissance phase
        run_recon(domain, self.fs, self.executor, self.mock_tui)
        
        # Check TUI status messages
        assert len(self.mock_tui.status_messages) > 0, "Should have status messages"
        
        # Check that all phases were completed
        status_text = " ".join(self.mock_tui.status_messages)
        assert "whoami execution set" in status_text.lower(), "Should have whoami status"
        assert "subdomains" in status_text.lower(), "Should have subdomains status"
        assert "harvesting" in status_text.lower(), "Should have harvest status"
        assert "shodan" in status_text.lower(), "Should have shodan status"
        assert "reconnaissance phase complete" in status_text.lower(), "Should complete recon"
        
        print(f"✓ Full reconnaissance phase completed successfully")
        print(f"TUI status messages: {len(self.mock_tui.status_messages)}")
        print(f"Final phase: {self.mock_tui.current_phase}")
        print(f"Final progress: {self.mock_tui.phase_progress}%")
        
    def test_file_structure(self):
        """Test the final file structure"""
        print("\n" + "=" * 40)
        print("Testing Final File Structure")
        print("=" * 40)
        
        # Check main files
        record_file = self.temp_dir / "record.md"
        assert record_file.exists(), "Record file should exist"
        
        # Check recon directory structure
        recon_dir = self.temp_dir / "recon"
        assert recon_dir.exists(), "Recon directory should exist"
        
        whoami_file = recon_dir / "whoami.md"
        assert whoami_file.exists(), "WhoAmI file should exist"
        
        subdomains_dir = recon_dir / "subdomains"
        assert subdomains_dir.exists(), "Subdomains directory should exist"
        
        subdomains_file = subdomains_dir / "subdomains.md"
        all_subdomains_file = subdomains_dir / "all_subdomains.txt"
        assert subdomains_file.exists(), "Subdomains file should exist"
        assert all_subdomains_file.exists(), "All subdomains file should exist"
        
        harvest_dir = recon_dir / "harvest"
        assert harvest_dir.exists(), "Harvest directory should exist"
        
        harvest_file = harvest_dir / "harvest.md"
        assert harvest_file.exists(), "Harvest file should exist"
        
        shodan_dir = recon_dir / "shodan"
        assert shodan_dir.exists(), "Shodan directory should exist"
        
        shodan_file = shodan_dir / "shodan.md"
        assert shodan_file.exists(), "Shodan file should exist"
        
        print("✓ File structure test passed")
        print("Directory structure:")
        self._print_directory_tree(self.temp_dir, max_depth=3)
        
    def _print_directory_tree(self, path: Path, prefix="", max_depth=3, current_depth=0):
        """Print directory tree structure"""
        if current_depth >= max_depth:
            return
            
        items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            current_prefix = "└── " if is_last else "├── "
            print(f"{prefix}{current_prefix}{item.name}")
            
            if item.is_dir() and current_depth < max_depth - 1:
                next_prefix = prefix + ("    " if is_last else "│   ")
                self._print_directory_tree(item, next_prefix, max_depth, current_depth + 1)
                
    def run_all_tests(self):
        """Run all tests"""
        try:
            self.setup()
            
            print("\n" + "🚀 Starting DeepDomain Flow Tests")
            print("=" * 60)
            
            # Run individual tests
            self.test_tool_check()
            self.test_filesystem_operations()
            self.test_output_class()
            self.test_execute_class()
            
            # Run reconnaissance tests
            self.test_recon_whoami()
            self.test_recon_subdomains()
            self.test_recon_harvest()
            self.test_recon_shodan()
            
            # Run integration test
            self.test_full_recon_phase()
            self.test_file_structure()
            
            print("\n" + "=" * 60)
            print("🎉 ALL TESTS PASSED!")
            print("=" * 60)
            print("✅ Tool checking works")
            print("✅ FileSystem operations work")
            print("✅ Output class works")
            print("✅ Execute class works")
            print("✅ WhoAmI reconnaissance works")
            print("✅ Subdomains reconnaissance works")
            print("✅ Harvest reconnaissance works")
            print("✅ Shodan reconnaissance works")
            print("✅ Full reconnaissance phase works")
            print("✅ File structure is correct")
            print("\n🔍 Test completed successfully - stopped before scanning phase as requested")
            
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            self.teardown()
            
        return True


def main():
    """Main test runner"""
    print("DeepDomain Flow Test")
    print("Testing CLI → Reconnaissance integration")
    print("Stopping before scanning phase")
    
    test_runner = TestDeepDomainFlow()
    success = test_runner.run_all_tests()
    
    if success:
        print("\n🎯 Test Summary:")
        print("- Successfully tested main.py → cli.py → recon.py flow")
        print("- Verified TUI integration works")
        print("- Confirmed all reconnaissance phases execute properly")
        print("- File structure is created correctly")
        print("- Stopped before scanning phase as requested")
        sys.exit(0)
    else:
        print("\n💥 Test failed - check output above for details")
        sys.exit(1)


if __name__ == "__main__":
    main()
