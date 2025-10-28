#!/usr/bin/env python3
"""
Test script to verify TUI continuous updates work correctly.
This script simulates the scanning process to test atomic updates.
"""

import asyncio
import time
from pathlib import Path
from src.utils.tui import create_tui

def test_scanning_callback(tui_app):
    """Test scanning callback that simulates continuous updates"""
    try:
        # Simulate workspace initialization
        tui_app.add_status_message("Workspace initialized", "success")
        tui_app.update_phase("Ready to begin", 20)
        time.sleep(0.5)
        
        # Simulate reconnaissance phase
        tui_app.update_phase("Reconnaissance Phase", 30)
        tui_app.add_status_message("Starting reconnaissance phase...", "info")
        
        # Simulate running commands with live output
        commands = [
            "echo 'Running whoami investigation...'",
            "echo 'Discovering subdomains...'", 
            "echo 'Harvesting information...'",
            "echo 'Querying Shodan...'"
        ]
        
        for i, cmd in enumerate(commands):
            tui_app.add_status_message(f"Running command {i+1}/4...", "info")
            
            # Run command with live output
            stdout, stderr, return_code = tui_app.run_command_live(cmd, Path.cwd())
            
            # Update progress
            progress = 30 + (i + 1) * 10
            tui_app.update_phase(f"Reconnaissance Phase - Step {i+1}", progress)
            tui_app.add_status_message(f"Command {i+1} completed", "success")
            
            # Small delay to see updates
            time.sleep(1)
        
        # Simulate scanning phase
        tui_app.update_phase("Scanning Phase", 60)
        tui_app.add_status_message("Starting scanning phase...", "info")
        
        # Simulate more commands
        scan_commands = [
            "echo 'Resolving hosts...'",
            "echo 'Performing network discovery...'"
        ]
        
        for i, cmd in enumerate(scan_commands):
            tui_app.add_status_message(f"Running scan command {i+1}/2...", "info")
            stdout, stderr, return_code = tui_app.run_command_live(cmd, Path.cwd())
            
            progress = 60 + (i + 1) * 15
            tui_app.update_phase(f"Scanning Phase - Step {i+1}", progress)
            tui_app.add_status_message(f"Scan command {i+1} completed", "success")
            time.sleep(1)
        
        # Simulate enumeration phase
        tui_app.update_phase("Enumeration Phase", 80)
        tui_app.add_status_message("Starting enumeration phase...", "info")
        
        enum_cmd = "echo 'Running vulnerability enumeration...'"
        tui_app.add_status_message("Running enumeration command...", "info")
        stdout, stderr, return_code = tui_app.run_command_live(enum_cmd, Path.cwd())
        
        tui_app.update_phase("Enumeration Phase - Complete", 90)
        tui_app.add_status_message("Enumeration completed", "success")
        time.sleep(1)
        
        # Final completion
        tui_app.update_phase("Complete", 100)
        tui_app.add_status_message("DeepDomain scan complete!", "success")
        tui_app.add_status_message("Test completed successfully", "info")
        
    except Exception as e:
        tui_app.add_status_message(f"Test error: {str(e)}", "error")
        raise

def main():
    """Main test function"""
    domain = "example.com"
    output_dir = Path.cwd() / "test_output"
    output_dir.mkdir(exist_ok=True)
    
    print("Starting TUI update test...")
    print("You should see continuous updates in the TUI.")
    print("Press 'q' to quit when done testing.")
    
    # Create and run TUI
    tui = create_tui(domain, output_dir, test_scanning_callback)
    tui.start()
    
    # Update TUI with initial status
    tui.update_phase("Initializing", 10)
    tui.add_status_message("TUI update test starting...", "info")
    
    # Run the TUI
    tui.run_tui()
    
    print("Test completed!")

if __name__ == "__main__":
    main()
