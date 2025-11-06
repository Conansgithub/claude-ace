#!/usr/bin/env bash
#
# Claude ACE - One-Line Installation Script
# Install Claude ACE into any Claude Code project
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/claude-ace/main/install.sh | bash
#   OR
#   wget -qO- https://raw.githubusercontent.com/YOUR_USERNAME/claude-ace/main/install.sh | bash
#
# Options:
#   INSTALL_DIR - Target project directory (default: current directory)
#   FORCE       - Force overwrite existing files (default: false)
#   SKIP_HOOKS  - Skip hooks configuration (default: false)
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/YOUR_USERNAME/claude-ace"
RAW_URL="https://raw.githubusercontent.com/YOUR_USERNAME/claude-ace/main"
INSTALL_DIR="${INSTALL_DIR:-$(pwd)}"
FORCE="${FORCE:-false}"
SKIP_HOOKS="${SKIP_HOOKS:-false}"
TEMP_DIR=""

# Helper functions
print_header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  🚀 Claude ACE Installer${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Cleanup on exit
cleanup() {
    if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
}
trap cleanup EXIT

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not found"
        print_info "Please install Python 3.8 or higher"
        exit 1
    fi

    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
        print_error "Python 3.8+ required, found $PYTHON_VERSION"
        exit 1
    fi

    print_success "Python $PYTHON_VERSION found"

    # Check git or curl/wget
    if command -v git &> /dev/null; then
        DOWNLOAD_METHOD="git"
        print_success "Git found - will use for download"
    elif command -v curl &> /dev/null; then
        DOWNLOAD_METHOD="curl"
        print_success "Curl found - will use for download"
    elif command -v wget &> /dev/null; then
        DOWNLOAD_METHOD="wget"
        print_success "Wget found - will use for download"
    else
        print_error "Git, curl, or wget is required"
        exit 1
    fi
}

# Download Claude ACE
download_ace() {
    print_info "Downloading Claude ACE..."

    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"

    if [ "$DOWNLOAD_METHOD" = "git" ]; then
        # Use git clone
        git clone --depth 1 "$REPO_URL" claude-ace &> /dev/null
        if [ $? -ne 0 ]; then
            print_error "Failed to clone repository"
            print_info "Please check your internet connection and repository URL"
            exit 1
        fi
    else
        # Download as archive
        ARCHIVE_URL="$REPO_URL/archive/refs/heads/main.zip"

        if [ "$DOWNLOAD_METHOD" = "curl" ]; then
            curl -fsSL "$ARCHIVE_URL" -o claude-ace.zip
        else
            wget -q "$ARCHIVE_URL" -O claude-ace.zip
        fi

        if [ $? -ne 0 ]; then
            print_error "Failed to download archive"
            exit 1
        fi

        # Extract (requires unzip)
        if ! command -v unzip &> /dev/null; then
            print_error "unzip is required but not found"
            print_info "Please install unzip or use git for installation"
            exit 1
        fi

        unzip -q claude-ace.zip
        mv claude-ace-main claude-ace
    fi

    print_success "Downloaded Claude ACE"
}

# Run installation
run_installation() {
    print_info "Installing Claude ACE to: $INSTALL_DIR"

    cd "$TEMP_DIR/claude-ace"

    # Build Python command
    PYTHON_CMD="python3 install.py --project \"$INSTALL_DIR\""

    if [ "$FORCE" = "true" ]; then
        PYTHON_CMD="$PYTHON_CMD --force"
    fi

    if [ "$SKIP_HOOKS" = "true" ]; then
        PYTHON_CMD="$PYTHON_CMD --skip-hooks"
    fi

    # Run installation
    eval $PYTHON_CMD

    if [ $? -eq 0 ]; then
        print_success "Installation complete!"
    else
        print_error "Installation failed"
        exit 1
    fi
}

# Print usage information
print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  INSTALL_DIR=<path>    Target project directory (default: current)"
    echo "  FORCE=true            Force overwrite existing files"
    echo "  SKIP_HOOKS=true       Skip hooks configuration"
    echo ""
    echo "Examples:"
    echo "  # Install in current directory"
    echo "  curl -fsSL $RAW_URL/install.sh | bash"
    echo ""
    echo "  # Install in specific directory"
    echo "  INSTALL_DIR=/path/to/project curl -fsSL $RAW_URL/install.sh | bash"
    echo ""
    echo "  # Force overwrite with environment variables"
    echo "  FORCE=true INSTALL_DIR=/path/to/project curl -fsSL $RAW_URL/install.sh | bash"
    echo ""
}

# Main installation flow
main() {
    print_header

    # Check if help requested
    if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        print_usage
        exit 0
    fi

    # Validate install directory
    if [ ! -d "$INSTALL_DIR" ]; then
        print_error "Directory does not exist: $INSTALL_DIR"
        print_info "Please create the directory first or use an existing one"
        exit 1
    fi

    print_info "Target directory: $INSTALL_DIR"

    # Run installation steps
    check_prerequisites
    download_ace
    run_installation

    # Success message
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ✅ Claude ACE installed successfully!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}Next steps:${NC}"
    echo "  1. Start using Claude Code in your project"
    echo "  2. View playbook: python $INSTALL_DIR/.claude/scripts/view_playbook.py"
    echo "  3. Enable diagnostics: touch $INSTALL_DIR/.claude/diagnostic_mode"
    echo ""
    echo -e "${CYAN}Documentation:${NC}"
    echo "  • GitHub: $REPO_URL"
    echo "  • Usage Guide: $REPO_URL/blob/main/docs/USAGE.md"
    echo ""
}

# Run main function
main "$@"
