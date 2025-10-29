# src/filesystem.py
from pathlib import Path
from typing import Union
from utils.atomic_ops import atomic_writer

class FileSystem:
    def __init__(self, base: Union[str, Path]):
        self.base = Path(base).resolve()

    # naming to match your spec (camelCase)
    def createFolder(self, name: str, location: str = "") -> Path:
        """
        name: folder name (expect lowercase + underscores)
        location: relative to base (e.g., "recon" or "recon/subdomains")
        """
        loc = self.base.joinpath(location) if location else self.base
        path = loc.joinpath(name)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def createFile(self, name: str, location: str = "") -> Path:
        """
        Creates a file. If name has no extension, .md is appended.
        Returns the Path to the created file.
        """
        if "." not in name:
            name = f"{name}.md"
        loc = self.base.joinpath(location) if location else self.base
        loc.mkdir(parents=True, exist_ok=True)
        full = loc.joinpath(name)
        # ensure file exists
        if not full.exists():
            full.write_text("")  # create empty file
        return full

    def appendOutput(self, file_location: str, output_text):
        """
        file_location: relative path from base (e.g., "recon/whoami.md" or "record.md")
        Uses atomic writes to prevent file corruption and TUI freezing.
        """
        target = self.base.joinpath(file_location)
        # if user passed directory + filename, allow both
        if not target.parent.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
        
        # Support either an Output-like object (with text()) or raw string
        if hasattr(output_text, "text") and callable(getattr(output_text, "text")):
            data = output_text.text()
        else:
            data = str(output_text) if output_text is not None else ""
        
        # Use atomic append to prevent file corruption
        atomic_writer.atomic_append(target, data)
