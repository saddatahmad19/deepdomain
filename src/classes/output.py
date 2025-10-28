# src/output.py
from pathlib import Path

class Output:
    def __init__(self):
        self._parts = []

    def addTitle(self, title: str):
        # Make first letter uppercase, leave internal spacing as-is
        if title:
            title = title[0].upper() + title[1:]
        self._parts.append(f"# {title}\n")

    def addCommand(self, command: str):
        self._parts.append(f"```bash\n{command}\n```\n")

    def addCommandOutput(self, output: str):
        if output is None:
            output = ""
        self._parts.append("**Output**\n\n```\n")
        self._parts.append(output.rstrip())
        self._parts.append("\n```\n")

    def newLine(self):
        self._parts.append("\n")

    def text(self) -> str:
        return "".join(self._parts)

    def write_to_file(self, path: Path, append: bool = False):
        mode = "a" if append else "w"
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open(mode, encoding="utf-8") as fh:
            fh.write(self.text())
