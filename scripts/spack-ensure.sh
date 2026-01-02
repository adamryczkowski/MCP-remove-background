#!/usr/bin/env bash
# spack-ensure.sh - Ensure Spack is installed and the project environment is ready
# This script is called by the justfile to bootstrap Spack if needed.
#
# ARCHITECTURE NOTE:
# This script contains bash-based version compatibility logic that mirrors the Python
# implementation in the Cookiecutters repository's version-discovery module.
#
# The version selection architecture has two phases:
# 1. TEMPLATE INSTANTIATION TIME: The Python-based spack-version-discovery module
#    (in the Cookiecutters repo) uses sophisticated algorithms to select optimal
#    tool versions based on what's available locally, in buildcaches, and in the
#    Spack repository. This runs when `cookiecutter` generates a new project.
#
# 2. RUNTIME (this script): Generated projects need self-contained bash logic for
#    runtime checks because they don't have access to the version-discovery module.
#    This script handles:
#    - Checking if compatible versions are already installed
#    - Installing missing packages via Spack
#    - Setting up the project environment
#
# The compatibility rules implemented here should match those in:
#   version-discovery/spack_version_discovery/selector.py::_is_version_compatible()
#
# Tool-specific compatibility rules:
#   - gcc/llvm/clang: major version match is enough (e.g., 21.x matches 21)
#   - python: major.minor must match (e.g., 3.12.x matches 3.12)
#   - cmake/ninja: major.minor must match
#   - node/openjdk: major version match is enough

set -euo pipefail

# Configuration
SPACK_USER_DIR="${SPACK_USER_DIR:-$HOME/.local/share/spack}"
SPACK_RELEASE_BRANCH="${SPACK_RELEASE_BRANCH:-releases/v1.1}"
SPACK_REPO_URL="${SPACK_REPO_URL:-https://github.com/spack/spack.git}"

# Colors for output (disabled if not a terminal)
if [[ -t 1 ]]; then
	RED='\033[0;31m'
	GREEN='\033[0;32m'
	YELLOW='\033[0;33m'
	NC='\033[0m' # No Color
else
	RED=''
	GREEN=''
	YELLOW=''
	NC=''
fi

function log_info() {
	echo -e "${GREEN}[spack-ensure]${NC} $*"
}

function log_warn() {
	echo -e "${YELLOW}[spack-ensure]${NC} $*" >&2
}

function log_error() {
	echo -e "${RED}[spack-ensure]${NC} $*" >&2
}

# Find Spack installation
function find_spack() {
	# Check if spack is already in PATH
	if command -v spack >/dev/null 2>&1; then
		echo "system"
		return 0
	fi

	# Check user-local installation
	if [[ -x "$SPACK_USER_DIR/bin/spack" ]]; then
		echo "$SPACK_USER_DIR"
		return 0
	fi

	# Not found
	return 1
}

# Install Spack to user directory
function install_spack() {
	log_info "Installing Spack to $SPACK_USER_DIR..."

	# Ensure parent directory exists
	mkdir -p "$(dirname "$SPACK_USER_DIR")"

	# Clone with shallow depth for faster download, using stable release branch
	if ! git clone --depth=2 --branch "$SPACK_RELEASE_BRANCH" "$SPACK_REPO_URL" "$SPACK_USER_DIR"; then
		log_error "Failed to clone Spack repository"
		return 1
	fi

	log_info "Spack installed successfully to $SPACK_USER_DIR"
	log_info "Using release branch: $SPACK_RELEASE_BRANCH"
}

# Source Spack setup script and export for current shell
function setup_spack_env() {
	local spack_root="$1"

	if [[ "$spack_root" == "system" ]]; then
		# Spack is already in PATH, just verify it works
		if ! spack --version >/dev/null 2>&1; then
			log_error "Spack command found but not working"
			return 1
		fi
		log_info "Using system Spack: $(command -v spack)"
		return 0
	fi

	# Source the setup script
	local setup_script="$spack_root/share/spack/setup-env.sh"
	if [[ ! -f "$setup_script" ]]; then
		log_error "Spack setup script not found: $setup_script"
		return 1
	fi

	# shellcheck disable=SC1090
	source "$setup_script"
	log_info "Spack environment sourced from $spack_root"
}

# Ensure project environment exists and is concretized
function ensure_project_env() {
	local project_dir
	project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

	if [[ ! -f "$project_dir/spack.yaml" ]]; then
		log_warn "No spack.yaml found in project root, skipping environment setup"
		return 0
	fi

	cd "$project_dir"

	# Check if environment is already fully set up (activation script is the last thing generated)
	if [[ -d ".spack-env" ]] && [[ -f "spack.lock" ]] && [[ -f ".spack-activate.sh" ]]; then
		# Check if the view directory exists and has python - quick proxy for "installed"
		if [[ -x ".spack-env/view/bin/python3" ]]; then
			log_info "Spack environment already set up and packages installed"
			return 0
		fi
	fi

	# Concretize if needed
	if [[ ! -f "spack.lock" ]]; then
		log_info "Setting up Spack environment..."

		# Concretize the environment
		if ! spack -e . concretize --reuse 2>&1; then
			log_error "Failed to concretize Spack environment"
			return 1
		fi

		log_info "Environment concretized successfully"
	fi

	# Install packages if not already installed
	log_info "Installing Spack packages (this may take a while on first run)..."
	if ! spack -e . install --reuse 2>&1; then
		log_error "Failed to install Spack packages"
		return 1
	fi

	log_info "Spack packages installed successfully"

	# Generate activation script for use by justfile
	generate_activation_script "$project_dir"
}

# Generate a script that can be sourced to activate the Spack environment
function generate_activation_script() {
	local project_dir="$1"
	local activate_script="$project_dir/.spack-activate.sh"

	cat > "$activate_script" << 'EOF'
# Auto-generated Spack activation script
# Source this file to activate the Spack environment

_SPACK_ENSURE_DIR="${SPACK_USER_DIR:-$HOME/.local/share/spack}"

# Find and source Spack
if command -v spack >/dev/null 2>&1; then
    : # Spack already available
elif [[ -f "$_SPACK_ENSURE_DIR/share/spack/setup-env.sh" ]]; then
    # shellcheck disable=SC1091
    source "$_SPACK_ENSURE_DIR/share/spack/setup-env.sh"
fi

# Activate the project environment if spack.yaml exists
if command -v spack >/dev/null 2>&1 && [[ -f "spack.yaml" ]]; then
    spack env activate . 2>/dev/null || true
fi

unset _SPACK_ENSURE_DIR
EOF

	chmod +x "$activate_script"
	log_info "Generated activation script: $activate_script"
}

# Check if environment is already fully set up (fast path)
# This avoids running any Spack commands if everything is already in place
function is_environment_ready() {
	local project_dir
	project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

	# All these files/directories must exist
	if [[ ! -d "$project_dir/.spack-env" ]] || \
		[[ ! -f "$project_dir/spack.lock" ]] || \
		[[ ! -f "$project_dir/.spack-activate.sh" ]]; then
		return 1
	fi

	# Python must be executable in the view
	local python_bin="$project_dir/.spack-env/view/bin/python3"

	if [[ -x "$python_bin" ]]; then
		return 0
	fi

	return 1
}

# Main entry point
function main() {
	local spack_location

	# Fast path: if environment is already fully set up, skip everything
	if is_environment_ready; then
		log_info "Spack environment already fully configured, skipping setup"
		return 0
	fi

	# Find or install Spack
	if spack_location=$(find_spack); then
		log_info "Found Spack at: $spack_location"
	else
		log_info "Spack not found, installing..."
		install_spack
		spack_location="$SPACK_USER_DIR"
	fi

	# Set up Spack environment
	setup_spack_env "$spack_location"

	# Ensure project environment
	ensure_project_env
}

main "$@"
