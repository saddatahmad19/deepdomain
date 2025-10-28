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
if [ -d "${VENV_DIR}" ]; then
  PRINT_NOTICE "Virtual environment '${VENV_DIR}' already exists — skipping creation."
else
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
  - This script installs a set of apt packages useful for recon development
    (nmap, nikto, jq, whois, libmagic, etc.). Many recon tools (subfinder, dnsx, httpx, etc.)
    are Go binaries or separate installers and are NOT installed by this script.
  - If you want, I can extend this script to:
      * install Go and use `go install` to fetch subfinder/dnsx/httpx,
      * install shodan-cli via pip or other OS-specific installers,
      * or add an interactive prompt for which extra recon tools to install.

EOF
