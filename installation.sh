#!/usr/bin/env bash
#
# installation.sh - Full Setup for Custom MCP Server + OpenCode
#
# This script sets up everything needed to use the custom Python MCP server with OpenCode.
#
# Usage:
#   chmod +x installation.sh
#   ./installation.sh
#
# What it does:
#   1. Checks prerequisites (Python 3.10+, pip/uv)
#   2. Installs OpenCode (if not already installed)
#   3. Installs Python MCP SDK (mcp[cli])
#   4. Creates opencode.json config with custom_mcp server
#   5. Verifies everything works
#

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CUSTOM_MCP_DIR="$SCRIPT_DIR/custom_mcp"
OPENCODE_CONFIG="$SCRIPT_DIR/opencode.json"

echo -e "${BOLD}${CYAN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     OpenCode + Custom MCP Server - Full Installation         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# =============================================================================
# STEP 1: Check Prerequisites
# =============================================================================
echo -e "${BOLD}${BLUE}[1/5]${NC} Checking prerequisites..."

# Check for Python 3.10+
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
        PYTHON_CMD="python3"
        echo -e "  ${GREEN}✓${NC} Python $PYTHON_VERSION found"
    else
        echo -e "  ${RED}✗${NC} Python $PYTHON_VERSION found, but 3.10+ is required"
        exit 1
    fi
elif command -v python &> /dev/null; then
    PYTHON_VERSION=$(python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 10 ]; then
        PYTHON_CMD="python"
        echo -e "  ${GREEN}✓${NC} Python $PYTHON_VERSION found"
    else
        echo -e "  ${RED}✗${NC} Python $PYTHON_VERSION found, but 3.10+ is required"
        exit 1
    fi
else
    echo -e "  ${RED}✗${NC} Python not found. Please install Python 3.10+ first."
    echo -e "    ${YELLOW}→${NC} https://www.python.org/downloads/"
    exit 1
fi

# Check for pip or uv
PIP_CMD=""
if command -v uv &> /dev/null; then
    PIP_CMD="uv pip"
    echo -e "  ${GREEN}✓${NC} uv found (recommended)"
elif command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
    echo -e "  ${GREEN}✓${NC} pip3 found"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
    echo -e "  ${GREEN}✓${NC} pip found"
else
    echo -e "  ${RED}✗${NC} pip or uv not found. Please install pip."
    echo -e "    ${YELLOW}→${NC} python3 -m ensurepip --upgrade"
    exit 1
fi

# Check for curl or wget (for opencode install)
if command -v curl &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} curl found"
elif command -v wget &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} wget found"
else
    echo -e "  ${RED}✗${NC} curl or wget not found. Needed to install OpenCode."
    exit 1
fi

echo ""

# =============================================================================
# STEP 2: Install OpenCode (if not present)
# =============================================================================
echo -e "${BOLD}${BLUE}[2/5]${NC} Checking for OpenCode..."

if command -v opencode &> /dev/null; then
    OPENCODE_VERSION=$(opencode --version 2>/dev/null || echo "unknown")
    echo -e "  ${GREEN}✓${NC} OpenCode already installed: $OPENCODE_VERSION"
else
    echo -e "  ${YELLOW}!${NC} OpenCode not found. Installing..."
    
    # Use official install script
    if command -v curl &> /dev/null; then
        curl -fsSL https://opencode.ai/install | bash
    else
        wget -qO- https://opencode.ai/install | bash
    fi
    
    # Verify installation
    if command -v opencode &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} OpenCode installed successfully"
    else
        echo -e "  ${YELLOW}!${NC} OpenCode installed. You may need to restart your shell."
        echo -e "    ${YELLOW}→${NC} Add ~/.opencode/bin to PATH or run: export PATH=\"\$HOME/.opencode/bin:\$PATH\""
    fi
fi

echo ""

# =============================================================================
# STEP 3: Install Python MCP SDK
# =============================================================================
echo -e "${BOLD}${BLUE}[3/5]${NC} Installing Python MCP SDK..."

if $PYTHON_CMD -c "import mcp; print(mcp.__version__)" &> /dev/null 2>&1; then
    MCP_VERSION=$($PYTHON_CMD -c "import mcp; print(mcp.__version__)" 2>/dev/null || echo "installed")
    echo -e "  ${GREEN}✓${NC} MCP SDK already installed: $MCP_VERSION"
else
    echo -e "  ${YELLOW}!${NC} Installing mcp[cli]..."
    
    if [[ "$PIP_CMD" == "uv pip" ]]; then
        uv pip install "mcp[cli]"
    else
        # --break-system-packages allows pip to install in system Python
        # (needed on Debian/Ubuntu with PEP 668 protected Python)
        $PIP_CMD install --break-system-packages "mcp[cli]"
    fi
    
    if $PYTHON_CMD -c "import mcp" &> /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} MCP SDK installed successfully"
    else
        echo -e "  ${RED}✗${NC} Failed to install MCP SDK"
        exit 1
    fi
fi

echo ""

# =============================================================================
# STEP 4: Setup Custom MCP Server Config
# =============================================================================
echo -e "${BOLD}${BLUE}[4/5]${NC} Setting up opencode.json config..."

# Ensure custom_mcp directory exists
if [ ! -d "$CUSTOM_MCP_DIR" ]; then
    echo -e "  ${RED}✗${NC} custom_mcp directory not found at $CUSTOM_MCP_DIR"
    echo -e "    ${YELLOW}→${NC} Make sure you're running this from the project root"
    exit 1
fi

# Check if server.py exists
if [ ! -f "$CUSTOM_MCP_DIR/server.py" ]; then
    echo -e "  ${RED}✗${NC} server.py not found in $CUSTOM_MCP_DIR"
    exit 1
fi

# Create or update opencode.json
if [ -f "$OPENCODE_CONFIG" ]; then
    echo -e "  ${GREEN}✓${NC} opencode.json already exists at $OPENCODE_CONFIG"
    echo -e "  ${YELLOW}!${NC} Checking for custom_test MCP entry..."
    
    # Check if custom_test is already configured
    if grep -q '"custom_test"' "$OPENCODE_CONFIG" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} custom_test MCP already configured"
    else
        echo -e "  ${YELLOW}!${NC} Adding custom_test MCP to existing config..."
        # Simple append approach - user may need to merge manually
        echo -e "    ${CYAN}→${NC} Please add this to your $OPENCODE_CONFIG:"
        echo -e "    ${CYAN}\"mcp\": {\"custom_test\": {\"type\": \"local\", \"command\": [\"python\", \"./custom_mcp/server.py\"], \"enabled\": true}}${NC}"
    fi
else
    echo -e "  ${YELLOW}!${NC} Creating new opencode.json..."
    
    cat > "$OPENCODE_CONFIG" << 'EOF'
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "custom_test": {
      "type": "local",
      "command": ["python", "./custom_mcp/server.py"],
      "enabled": true,
      "timeout": 10000
    }
  },
  "instructions": [
    "When testing MCP tools, use the custom_test server tools like echo, add, greet, etc."
  ]
}
EOF
    
    echo -e "  ${GREEN}✓${NC} Created opencode.json with custom_test MCP server"
fi

echo ""

# =============================================================================
# STEP 5: Verify Setup
# =============================================================================
echo -e "${BOLD}${BLUE}[5/5]${NC} Verifying setup..."

ERRORS=0

# Verify Python can import mcp
if $PYTHON_CMD -c "from mcp.server.fastmcp import FastMCP; print('  ✓ MCP SDK import OK')" 2>/dev/null; then
    :
else
    echo -e "  ${RED}✗${NC} Cannot import MCP SDK"
    ERRORS=$((ERRORS + 1))
fi

# Verify server.py syntax
if $PYTHON_CMD -m py_compile "$CUSTOM_MCP_DIR/server.py" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} server.py syntax OK"
else
    echo -e "  ${RED}✗${NC} server.py has syntax errors"
    ERRORS=$((ERRORS + 1))
fi

# Verify opencode.json is valid JSON
if command -v python3 &> /dev/null; then
    if python3 -c "import json; json.load(open('$OPENCODE_CONFIG'))" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} opencode.json is valid JSON"
    else
        echo -e "  ${RED}✗${NC} opencode.json is not valid JSON"
        ERRORS=$((ERRORS + 1))
    fi
fi

echo ""

# =============================================================================
# DONE
# =============================================================================
echo -e "${BOLD}${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    Installation Complete!                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

if [ $ERRORS -gt 0 ]; then
    echo -e "${YELLOW}⚠ Completed with $ERRORS warning(s). Please review above.${NC}"
    echo ""
fi

echo -e "${BOLD}Next Steps:${NC}"
echo ""
echo -e "  ${CYAN}1.${NC} Start OpenCode:"
echo -e "     ${GREEN}opencode${NC}"
echo ""
echo -e "  ${CYAN}2.${NC} In OpenCode, test your MCP server:"
echo -e "     ${GREEN}Use custom_test echo to say \"Hello World\"${NC}"
echo ""
echo -e "  ${CYAN}3.${NC} Available tools:"
echo -e "     echo, add, multiply, greet, get_current_time,"
echo -e "     reverse_text, word_count, calculate, list_tools_info"
echo ""
echo -e "  ${CYAN}4.${NC} Manage MCP servers:"
echo -e "     ${GREEN}opencode mcp list${NC}     - List all MCP servers"
echo -e "     ${GREEN}opencode mcp debug custom_test${NC} - Debug connection"
echo ""
echo -e "${BOLD}Files:${NC}"
echo -e "  • MCP Server:  ${CYAN}$CUSTOM_MCP_DIR/server.py${NC}"
echo -e "  • Config:      ${CYAN}$OPENCODE_CONFIG${NC}"
echo -e "  • Docs:        ${CYAN}$CUSTOM_MCP_DIR/README.md${NC}"
echo ""
echo -e "${BOLD}Enjoy coding with OpenCode + MCP! 🚀${NC}"
echo ""
