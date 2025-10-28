# test_tui_atomic.py
"""
Test script to demonstrate the new atomic TUI implementation.
This script shows how the TUI now updates atomically without freezing.
"""
import asyncio
import time
from pathlib import Path
from src.utils.tui import create_tui
from src.utils.optimized_executor import OptimizedExecutor
from src.classes.filesystems import FileSystem


def create_test_scanning_callback(domain: str, output_dir: Path):
    """Create a test scanning callback that demonstrates atomic updates"""
    
    def scanning_callback(tui_app):
        """Test scanning callback with atomic updates"""
        try:
            # Initialize executor
            executor = OptimizedExecutor(mode="quick")
            fs = FileSystem(output_dir)
            
            # Phase 1: Reconnaissance
            tui_app.update_phase("Reconnaissance", 20)
            tui_app.add_status_message("Starting reconnaissance phase", "info")
            
            # Simulate some work with atomic updates
            for i in range(5):
                tui_app.add_status_message(f"Running recon tool {i+1}/5", "info")
                
                # Simulate command execution
                test_command = f"echo 'Recon tool {i+1} output' && sleep 1"
                tui_app.run_command_async(
                    test_command,
                    output_dir,
                    callback=lambda stdout, stderr, rc: None
                )
                time.sleep(0.5)  # Brief pause to show updates
            
            # Phase 2: Network Discovery
            tui_app.update_phase("Network Discovery", 50)
            tui_app.add_status_message("Starting network discovery", "info")
            
            for i in range(3):
                tui_app.add_status_message(f"Scanning network {i+1}/3", "info")
                
                test_command = f"echo 'Network scan {i+1} output' && sleep 2"
                tui_app.run_command_async(
                    test_command,
                    output_dir,
                    callback=lambda stdout, stderr, rc: None
                )
                time.sleep(0.5)
            
            # Phase 3: Enumeration
            tui_app.update_phase("Enumeration", 80)
            tui_app.add_status_message("Starting enumeration phase", "info")
            
            for i in range(4):
                tui_app.add_status_message(f"Enumerating service {i+1}/4", "info")
                
                test_command = f"echo 'Enumeration {i+1} output' && sleep 1.5"
                tui_app.run_command_async(
                    test_command,
                    output_dir,
                    callback=lambda stdout, stderr, rc: None
                )
                time.sleep(0.5)
            
            # Completion
            tui_app.update_phase("Complete", 100)
            tui_app.add_status_message("Scan completed successfully!", "success")
            
        except Exception as e:
            tui_app.add_status_message(f"Scan error: {str(e)}", "error")
    
    return scanning_callback


def main():
    """Main function to test the atomic TUI"""
    domain = "example.com"
    output_dir = Path("./test_output")
    output_dir.mkdir(exist_ok=True)
    
    print("Starting DeepDomain TUI with atomic updates...")
    print("The TUI should now update smoothly without freezing!")
    print("Press 'q' to quit, 'c' to clear output, 'r' to clear status")
    print("=" * 60)
    
    # Create scanning callback
    scanning_callback = create_test_scanning_callback(domain, output_dir)
    
    # Create and run TUI
    tui = create_tui(domain, output_dir, scanning_callback)
    tui.start()
    
    # Update TUI with initial status
    tui.update_phase("Initializing", 10)
    tui.add_status_message("DeepDomain atomic TUI test starting...", "info")
    
    # Run the TUI
    tui.run_tui()
    
    print("\n" + "=" * 60)
    print("TUI test completed!")
    print("Check the output directory for results.")


if __name__ == "__main__":
    main()
