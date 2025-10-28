#!/usr/bin/env bash
# bootstrap.sh - Bootstrap script for DeepDomain (Debian/Ubuntu Linux)
# Installs apt packages, creates python venv, installs pip deps
set -euo pipefail

# Config - adjust if desired
VENV_DIR=".venv"
REQ_FILE="requirements.txt"
APT_PACKAGES=(
  build-essential
  git
  curl
  jq
  whois
  python3
  python3-venv
  python3-dev
  python3-pip
  libmagic1
  nmap
  nikto
  gobuster
  nuclei
  masscan
  dnsutils
)

PRINT_NOTICE() {
  echo -e "\n==> $*\n"
}

ERR_EXIT() {
  echo >&2 "ERROR: $*"
  exit 1
}

# Check apt-get available
if ! command -v apt-get >/dev/null 2>&1; then
  ERR_EXIT "apt-get not found. This script is designed for Debian/Ubuntu systems with apt."
fi

# Ensure script is run from project root (best-effort)
PROJECT_ROOT="$(pwd)"
PRINT_NOTICE "Bootstrapping project in: ${PROJECT_ROOT}"

# Update apt and install packages
PRINT_NOTICE "Updating apt and installing packages..."
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y "${APT_PACKAGES[@]}"

# Ensure git, python3 available
if ! command -v python3 >/dev/null 2>&1; then
  ERR_EXIT "python3 not found after apt install."
fi

# Create venv if missing
if [ -d "${VENV_DIR}" ] && [ -f "${VENV_DIR}/pyvenv.cfg" ]; then
  PRINT_NOTICE "Virtual environment '${VENV_DIR}' already exists and appears valid — skipping creation."
  PRINT_NOTICE "If you need to recreate it, remove the directory first: rm -rf ${VENV_DIR}"
else
  if [ -d "${VENV_DIR}" ]; then
    PRINT_NOTICE "Removing incomplete virtual environment directory..."
    rm -rf "${VENV_DIR}"
  fi
  PRINT_NOTICE "Creating virtual environment at ./${VENV_DIR}..."
  python3 -m venv "${VENV_DIR}"
fi

# Activate venv for this script's remainder
# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

# Upgrade pip
PRINT_NOTICE "Upgrading pip inside venv..."
python -m pip install --upgrade pip setuptools wheel

# If requirements.txt missing, create a sensible default (from earlier suggestions)
if [ ! -f "${REQ_FILE}" ]; then
  PRINT_NOTICE "'${REQ_FILE}' not found — creating a default requirements.txt"
  cat > "${REQ_FILE}" <<'PYREQ'
# CLI & UX
typer[all]
rich

# config / env / data
python-dotenv
pyyaml

# networking / HTTP libs used from Python
httpx
requests

# Shodan API (python library + CLI)
shodan

# small utilities
tqdm
python-magic
PYREQ
fi

# Install pip packages
PRINT_NOTICE "Installing Python packages from ${REQ_FILE}..."
python -m pip install -r "${REQ_FILE}"

# Install Go-based tools (subfinder, dnsx, httpx, theHarvester)
PRINT_NOTICE "Installing Go-based reconnaissance tools..."

# Provide instructions if Go is missing; otherwise install tools
if ! command -v go >/dev/null 2>&1; then
  PRINT_NOTICE "Go is not installed. Skipping Go tool installation."
  cat <<'GOINSTALL'
Go is required to install subfinder, dnsx, httpx, and theHarvester.

Install Go (choose one):

Option A: Debian/Ubuntu packages (simplest)
  sudo apt-get update -y
  sudo apt-get install -y golang

Option B: Official tarball (latest stable)
  GO_VERSION="$(curl -s https://go.dev/VERSION?m=text | head -n1)"
  wget "https://go.dev/dl/${GO_VERSION}.linux-amd64.tar.gz"
  sudo rm -rf /usr/local/go
  sudo tar -C /usr/local -xzf "${GO_VERSION}.linux-amd64.tar.gz"
  rm "${GO_VERSION}.linux-amd64.tar.gz"
  echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
  export PATH=$PATH:/usr/local/go/bin

After installing Go, ensure your GOPATH bin is on PATH:
  echo 'export PATH=$PATH:$(go env GOPATH)/bin' >> ~/.bashrc
  export PATH=$PATH:$(go env GOPATH)/bin

Then re-run this script:
  bash bootstrap.sh
GOINSTALL
else
  PRINT_NOTICE "Go detected: $(go version)"
  PRINT_NOTICE "Installing subfinder, dnsx, httpx, theHarvester..."
  go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
  go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest
  go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
  go install -v github.com/laramies/theHarvester@latest

  # Add Go bin to PATH for this session
  export PATH=$PATH:$(go env GOPATH)/bin
fi

# Install shodan CLI if not present
if ! command -v shodan >/dev/null 2>&1; then
  PRINT_NOTICE "Installing shodan CLI..."
  python -m pip install shodan
fi

# Final messages
deactivate 2>/dev/null || true

cat <<EOF

Bootstrap complete!

Next steps:
  1) Activate the virtual environment:
       source ${VENV_DIR}/bin/activate

  2) Run your CLI (example):
       python main.py -d example.com -o /path/to/output

Notes:
  - This script installs apt packages (nmap, nikto, gobuster, nuclei, masscan, etc.)
    and Go-based tools (subfinder, dnsx, httpx, theHarvester) via go install.
  - The shodan CLI is installed via pip.
  - All tools should now be available for the DeepDomain reconnaissance workflow.
  - If you encounter issues with Go tools, ensure your PATH includes $(go env GOPATH)/bin

EOF
