from .filesystems import FileSystem
from .output import Output
from .execute import Execute


def prepare_scanning_workspace(fs: FileSystem) -> None:
    """Create the base ./scanning directory (README step 7)."""
    fs.createFolder("scanning")


def run_resolve(fs: FileSystem, executor: Execute) -> None:
    """Execution set 5 scaffold: create ./scanning/resolve and resolved.md with title."""
    fs.createFolder("scanning")
    fs.createFolder("resolve", location="scanning")
    resolved_path = fs.createFile("resolved.md", location="scanning/resolve")

    out = Output()
    out.addTitle("Resolved Hosts")
    out.newLine()
    out.write_to_file(resolved_path)


def run_network_discover(fs: FileSystem, executor: Execute) -> None:
    """Execution set 6 scaffold: create quick/detailed dirs and base files with titles."""
    fs.createFolder("scanning")
    fs.createFolder("network_discover", location="scanning")

    # quick
    fs.createFolder("quick", location="scanning/network_discover")
    quick_md = fs.createFile("quick_discovery.md", location="scanning/network_discover/quick")
    quick_out = Output()
    quick_out.addTitle("Quick Discovery")
    quick_out.newLine()
    quick_out.write_to_file(quick_md)

    # detailed
    fs.createFolder("detailed", location="scanning/network_discover")
    det_md = fs.createFile("detailed_discovery.md", location="scanning/network_discover/detailed")
    det_out = Output()
    det_out.addTitle("Detailed Discovery")
    det_out.newLine()
    det_out.write_to_file(det_md)

