#!/usr/bin/env bash
#
# Claude ACE - Quick Install (Minimal Version)
# Ultra-lightweight installer for piping from curl/wget
#

set -e

# Configuration
REPO="YOUR_USERNAME/claude-ace"  # Update this!
RAW_BASE="https://raw.githubusercontent.com/$REPO/main"

# Colors
G='\033[0;32m'; R='\033[0;31m'; Y='\033[1;33m'; C='\033[0;36m'; NC='\033[0m'

echo -e "${C}🚀 Claude ACE Quick Installer${NC}\n"

# Check Python
if ! command -v python3 &>/dev/null; then
    echo -e "${R}✗ Python 3 required${NC}"; exit 1
fi
echo -e "${G}✓ Python found${NC}"

# Get install dir
DIR="${1:-$(pwd)}"
[ ! -d "$DIR" ] && { echo -e "${R}✗ Directory not found: $DIR${NC}"; exit 1; }
echo -e "${G}✓ Target: $DIR${NC}"

# Create temp directory
TMP=$(mktemp -d)
trap "rm -rf $TMP" EXIT

echo -e "${Y}⬇ Downloading...${NC}"

# Download files
cd "$TMP"
mkdir -p ace_core/{hooks,prompts,scripts,templates}

# Download core files
download() {
    local file=$1
    if command -v curl &>/dev/null; then
        curl -fsSL "$RAW_BASE/$file" -o "$file"
    else
        wget -q "$RAW_BASE/$file" -O "$file"
    fi
}

# Download structure
download "install.py"
download "ace_core/hooks/common.py"
download "ace_core/hooks/user_prompt_inject.py"
download "ace_core/hooks/precompact.py"
download "ace_core/hooks/session_end.py"
download "ace_core/prompts/reflection.txt"
download "ace_core/prompts/playbook.txt"
download "ace_core/scripts/view_playbook.py"
download "ace_core/scripts/cleanup_playbook.py"
download "ace_core/scripts/analyze_diagnostics.py"
download "ace_core/templates/settings.json"
download "ace_core/templates/playbook.json"
download "ace_core/templates/ace_config.json"

echo -e "${G}✓ Downloaded${NC}"

# Run installer
echo -e "${Y}⚙ Installing...${NC}"
python3 install.py --project "$DIR" ${FORCE:+--force} ${SKIP_HOOKS:+--skip-hooks}

echo -e "\n${G}✅ Installation complete!${NC}"
echo -e "${C}View your playbook: python $DIR/.claude/scripts/view_playbook.py${NC}\n"
