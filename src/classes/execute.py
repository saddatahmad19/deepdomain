# src/execute.py
from pathlib import Path
import subprocess
import re
from typing import Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.utils.tui import TUIWrapper

class Execute:
    def __init__(self, workdir: Path | str, tui: Optional['TUIWrapper'] = None):
        self.workdir = Path(workdir)
        self.tui = tui

    def run_command(self, command: str) -> Tuple[str, str, int]:
        """
        Runs a command via shell. Returns (stdout, stderr, returncode).
        If TUI is available, uses live output streaming. Otherwise falls back to regular subprocess.
        """
        if self.tui:
            return self.tui.run_command_live(command, self.workdir)
        else:
            # Fallback to regular subprocess if TUI not available
            proc = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=self.workdir)
            return proc.stdout, proc.stderr, proc.returncode

    def run_command_async(self, command: str, callback: Optional[callable] = None) -> None:
        """
        Run a command asynchronously with live output streaming.
        The callback will be called with (stdout, stderr, returncode) when complete.
        """
        if self.tui:
            self.tui.run_command_async(command, self.workdir, callback)
        else:
            # Fallback to regular subprocess if TUI not available
            import threading
            def run_fallback():
                result = self.run_command(command)
                if callback:
                    callback(*result)
            threading.Thread(target=run_fallback, daemon=True).start()

    def extract_ip(self, host_output: str) -> Optional[str]:
        """
        Extract first IPv4 from a host-like output.
        """
        if not host_output:
            return None
        m = re.search(r'(\d{1,3}(?:\.\d{1,3}){3})', host_output)
        return m.group(1) if m else None
