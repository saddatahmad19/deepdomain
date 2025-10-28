# DeepDomain

DeepDomain is a comprehensive cybersecurity reconnaissance and scanning tool designed specifically for Kali Linux. It automates the entire penetration testing workflow from initial reconnaissance through vulnerability assessment, providing structured output and detailed reporting for security professionals. The tool follows a modular architecture with separate phases for reconnaissance, scanning, and enumeration, making it suitable for both red team operations and security assessments.

## Use Case

DeepDomain streamlines the penetration testing process by automating common reconnaissance and scanning tasks. It's designed for cybersecurity professionals who need to perform comprehensive security assessments efficiently.

### Basic Usage

```bash
# Run with required domain parameter (pipx installation)
deepdomain -d example.com

# Specify custom output directory
deepdomain -d example.com -o /path/to/output

# The tool will prompt for output directory if not specified
deepdomain -d example.com
# Output: The output directory is: /current/directory

# For development installation, use:
python main.py -d example.com
```

### Workflow Phases

**Reconnaissance Phase:**
- **WhoAmI Investigation**: Performs `host` and `whois` lookups to gather basic domain information
- **Subdomain Discovery**: Uses `subfinder` and `crt.sh` to enumerate subdomains, then filters for high-value targets
- **Information Harvesting**: Leverages `theHarvester` to gather emails, subdomains, and other intelligence
- **Shodan Integration**: Queries Shodan for exposed services and infrastructure details

**Scanning Phase:**
- **Host Resolution**: Uses `dnsx` and `httpx` to identify live hosts and services
- **Network Discovery**: Performs quick ping sweeps with `nmap` and port scanning with `masscan`
- **Detailed Analysis**: Conducts comprehensive `nmap` scans on discovered open ports

**Enumeration Phase:**
- **Vulnerability Assessment**: Runs `nikto`, `gobuster`, and `nuclei` to identify potential security issues
- **Directory Enumeration**: Discovers hidden directories and files
- **Automated Vulnerability Detection**: Scans for known CVEs and misconfigurations

### Output Structure

All results are organized in a structured directory layout:

```
output_directory/
├── record.md                    # Master log of all executed commands
├── recon/
│   ├── whoami.md               # Domain information and whois data
│   ├── subdomains/
│   │   ├── subdomains.md       # Subdomain discovery results
│   │   ├── all_subdomains.txt  # Complete subdomain list
│   │   └── live_subdomains.txt # Verified live subdomains
│   ├── harvest/
│   │   └── harvest.md          # Information harvesting results
│   └── shodan/
│       └── shodan.md           # Shodan intelligence data
├── scanning/
│   ├── resolve/
│   │   └── resolved.md         # Host resolution results
│   └── network_discover/
│       ├── quick/
│       │   └── quick_discovery.md    # Quick network scans
│       └── detailed/
│           └── detailed_discovery.md # Detailed port analysis
└── enumeration/
    └── vulnerable/
        └── vulnerable.md       # Vulnerability assessment results
```

## Installation

### Recommended: pipx Installation (Global Access)

The easiest way to install DeepDomain is using `pipx`, which installs the tool globally while keeping it isolated:

1. **Install pipx (if not already installed):**
   ```bash
   # On Ubuntu/Debian
   sudo apt install pipx
   
   # Or via pip
   pip install pipx
   pipx ensurepath
   ```

2. **Install DeepDomain:**
   ```bash
   # Install from GitHub (latest version)
   pipx install git+https://github.com/yourusername/deepdomain.git
   
   # Or install from PyPI (when published)
   pipx install deepdomain
   ```

3. **Install system dependencies:**
   ```bash
   # Run the bootstrap script to install required system tools
   curl -sSL https://raw.githubusercontent.com/yourusername/deepdomain/main/bootstrap.sh | bash
   ```

4. **Run DeepDomain from anywhere:**
   ```bash
   deepdomain -d example.com
   ```

### Development Setup

For development or if you prefer local installation:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/deepdomain.git
   cd deepdomain
   ```

2. **Run the bootstrap script:**
   ```bash
   chmod +x bootstrap.sh
   ./bootstrap.sh
   ```

3. **Activate the virtual environment:**
   ```bash
   source .venv/bin/activate
   ```

4. **Run DeepDomain:**
   ```bash
   python main.py -d example.com
   ```

### Manual Installation

If you prefer manual setup or the bootstrap script fails:

1. **Install system dependencies:**
   ```bash
   sudo apt update
   sudo apt install -y build-essential git curl jq whois python3 python3-venv python3-dev python3-pip libmagic1 nmap nikto gobuster nuclei masscan dnsutils
   ```

2. **Create and activate virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirement.txt
   ```

4. **Install Go-based tools:**
   ```bash
   # Install Go (if not already installed)
   sudo apt install golang
   
   # Install reconnaissance tools
   go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
   go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest
   go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
   go install -v github.com/laramies/theHarvester@latest
   
   # Add Go bin to PATH
   echo 'export PATH=$PATH:$(go env GOPATH)/bin' >> ~/.bashrc
   source ~/.bashrc
   ```

### Dependency Installation

#### System Dependencies (via apt)

The following tools are installed via `sudo apt install`:

- **Core Tools**: `build-essential`, `git`, `curl`, `jq`, `whois`
- **Python Environment**: `python3`, `python3-venv`, `python3-dev`, `python3-pip`
- **System Libraries**: `libmagic1`
- **Network Scanning**: `nmap`, `masscan`
- **Web Testing**: `nikto`, `gobuster`, `nuclei`
- **DNS Utilities**: `dnsutils`

#### Python Dependencies (via pip)

Installed from `requirement.txt`:

- **CLI Framework**: `typer[all]` - Modern command-line interface
- **Rich Output**: `rich` - Beautiful terminal output and progress bars
- **Configuration**: `python-dotenv`, `pyyaml` - Environment and config management
- **HTTP Libraries**: `httpx`, `requests` - HTTP client libraries
- **Shodan Integration**: `shodan` - Shodan API client
- **Utilities**: `tqdm`, `python-magic` - Progress bars and file type detection

#### Go-based Tools (via go install)

These tools provide advanced reconnaissance capabilities:

- **subfinder**: Subdomain discovery tool
- **dnsx**: DNS toolkit for enumeration
- **httpx**: HTTP probe and web server analysis
- **theHarvester**: Information gathering and email harvesting

#### Additional Tools

- **Shodan CLI**: Installed via pip for infrastructure intelligence
- **Wordlists**: Standard Kali Linux wordlists (included in `/usr/share/wordlists/`)

### Prerequisites

- **Operating System**: Kali Linux (recommended) or Debian/Ubuntu-based systems
- **Python**: 3.8 or higher
- **Go**: 1.19 or higher (for Go-based tools)
- **Permissions**: Some tools require sudo privileges for network scanning
- **Internet**: Required for API calls and tool downloads

### Troubleshooting

**Missing Tools Error:**
If you encounter missing tool errors, the script will display the exact command to install them:
```bash
sudo apt install [missing-tools-list]
```

**Go Tools Not Found:**
Ensure Go is installed and the Go bin directory is in your PATH:
```bash
echo 'export PATH=$PATH:$(go env GOPATH)/bin' >> ~/.bashrc
source ~/.bashrc
```

**Permission Issues:**
Some network scanning tools require elevated privileges. Run with appropriate permissions or configure sudo access for specific tools.

## Updating DeepDomain

### Updating pipx Installation

If you installed DeepDomain using `pipx`, updating is simple:

```bash
# Update to the latest version from GitHub
pipx upgrade deepdomain

# Or reinstall from GitHub for latest changes
pipx reinstall git+https://github.com/yourusername/deepdomain.git
```

### Updating Development Installation

For local development installations:

```bash
# Navigate to the project directory
cd deepdomain

# Pull latest changes
git pull origin main

# Update Python dependencies
source .venv/bin/activate
pip install -r requirement.txt

# Update system dependencies (if needed)
./bootstrap.sh
```

### Checking Current Version

```bash
# Check installed version
deepdomain --version

# Or check pipx installation info
pipx list deepdomain
```

### Updating System Dependencies

System tools (nmap, nikto, etc.) can be updated through your package manager:

```bash
# Update all system packages
sudo apt update && sudo apt upgrade

# Update specific tools
sudo apt install --only-upgrade nmap nikto gobuster nuclei masscan
```

### Updating Go-based Tools

```bash
# Update Go tools to latest versions
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest
go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
go install -v github.com/laramies/theHarvester@latest
```
