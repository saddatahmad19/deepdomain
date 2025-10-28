# src/execute.py
from pathlib import Path
import subprocess
import re
from typing import Tuple, Optional

class Execute:
    def __init__(self, workdir: Path | str):
        self.workdir = Path(workdir)

    def run_command(self, command: str) -> Tuple[str, str, int]:
        """
        Runs a command via shell. Returns (stdout, stderr, returncode).
        Note: using shell=True for convenience; change to list args for stricter behavior.
        """
        proc = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=self.workdir)
        return proc.stdout, proc.stderr, proc.returncode

    def extract_ip(self, host_output: str) -> Optional[str]:
        """
        Extract first IPv4 from a host-like output.
        """
        if not host_output:
            return None
        m = re.search(r'(\d{1,3}(?:\.\d{1,3}){3})', host_output)
        return m.group(1) if m else None
