#!/usr/bin/env python3
"""
Test script for DeepDomain TUI integration
"""
import sys
import time
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

from tui import create_tui
from execute import Execute

def test_tui_basic():
    """Test basic TUI functionality"""
    print("Testing TUI basic functionality...")
    
    # Create test directory
    test_dir = Path("test_output")
    test_dir.mkdir(exist_ok=True)
    
    try:
        # Create TUI
        tui = create_tui("example.com", test_dir)
        tui.start()
        
        # Give TUI time to initialize
        time.sleep(1)
        
        # Test status updates
        tui.update_phase("Testing", 25)
        tui.add_status_message("TUI test starting...", "info")
        tui.add_status_message("This is a test message", "success")
        tui.add_status_message("Warning message", "warning")
        
        # Test command execution
        executor = Execute(workdir=test_dir, tui=tui)
        
        # Test a simple command
        print("Testing command execution...")
        stdout, stderr, returncode = executor.run_command("echo 'Hello from TUI test'")
        print(f"Command result: {returncode}")
        print(f"Output: {stdout}")
        
        # Keep TUI running for a bit to see the output
        time.sleep(3)
        
        # Test async command
        print("Testing async command execution...")
        def callback(stdout, stderr, returncode):
            print(f"Async command completed with return code: {returncode}")
        
        executor.run_command_async("echo 'Async test command'", callback)
        
        # Keep running for a bit more
        time.sleep(2)
        
        tui.add_status_message("TUI test completed", "success")
        tui.update_phase("Complete", 100)
        
        # Keep TUI running for final display
        time.sleep(2)
        
        print("TUI test completed successfully!")
        
    except Exception as e:
        print(f"TUI test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        tui.stop()
        print("TUI stopped")

if __name__ == "__main__":
    test_tui_basic()
