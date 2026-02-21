#!/bin/bash
#
# Conscious Pebble - macOS Installer (Full Version with Voice)
#
# This script sets up the complete Conscious Pebble environment on macOS
# including voice services (Whisper STT + Kokoro TTS).
#
# Usage:
#   chmod +x setup_mac.sh
#   ./setup_mac.sh
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        Conscious Pebble - macOS Installer                    ║"
echo "║              Full Version with Voice Services                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# =============================================================================
# STEP 1: Check Prerequisites
# =============================================================================
echo -e "${YELLOW}[Step 1/5] Checking prerequisites...${NC}"

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 is not installed.${NC}"
    echo "  Please install Python 3 from https://www.python.org or via Homebrew:"
    echo "  brew install python3"
    exit 1
fi
echo -e "${GREEN}✓ Python 3 found: $(python3 --version)${NC}"

# Check for pip
if ! command -v pip3 &> /dev/null && ! python3 -m pip --version &> /dev/null; then
    echo -e "${RED}✗ pip is not installed.${NC}"
    echo "  Please install pip:"
    echo "  python3 -m ensurepip --upgrade"
    exit 1
fi
echo -e "${GREEN}✓ pip found${NC}"

# Check for Apple Silicon (M1/M2/M3/M4)
ARCH=$(uname -m)
if [[ "$ARCH" != "arm64" ]]; then
    echo -e "${YELLOW}⚠ Warning: Not running on Apple Silicon (arm64).${NC}"
    echo "  Architecture detected: $ARCH"
    echo "  MLX voice features may not work correctly."
    read -p "  Continue anyway? (y/n): " continue_anyway
    if [[ "${continue_anyway,,}" != "y" ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓ Apple Silicon detected: $ARCH${NC}"
fi

# =============================================================================
# STEP 2: Create Virtual Environment
# =============================================================================
echo -e "${YELLOW}[Step 2/5] Creating virtual environment...${NC}"

VENV_DIR="$SCRIPT_DIR/.pebble_env"

if [[ -d "$VENV_DIR" ]]; then
    echo -e "${YELLOW}  Virtual environment already exists. Removing old one...${NC}"
    rm -rf "$VENV_DIR"
fi

python3 -m venv "$VENV_DIR"
echo -e "${GREEN}✓ Virtual environment created at: $VENV_DIR${NC}"

# Activate venv
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "  Upgrading pip..."
pip install --upgrade pip --quiet

# =============================================================================
# STEP 3: Install Dependencies
# =============================================================================
echo -e "${YELLOW}[Step 3/5] Installing Python dependencies...${NC}"

REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"

if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
    echo -e "${RED}✗ requirements.txt not found!${NC}"
    deactivate
    exit 1
fi

echo "  Installing from requirements.txt..."
pip install -r "$REQUIREMENTS_FILE" --quiet

echo -e "${GREEN}✓ Dependencies installed${NC}"

# =============================================================================
# STEP 4: Download Voice Models
# =============================================================================
echo -e "${YELLOW}[Step 4/5] Downloading voice models (Whisper + Kokoro)...${NC}"
echo -e "${BLUE}  This may take a few minutes depending on your internet connection.${NC}"

DOWNLOAD_SCRIPT="$SCRIPT_DIR/download_models.py"

if [[ ! -f "$DOWNLOAD_SCRIPT" ]]; then
    echo -e "${RED}✗ download_models.py not found!${NC}"
    deactivate
    exit 1
fi

python "$DOWNLOAD_SCRIPT"
DOWNLOAD_EXIT=$?

if [[ $DOWNLOAD_EXIT -ne 0 ]]; then
    echo -e "${YELLOW}⚠ Some models failed to download.${NC}"
    echo "  You can retry later with: python download_models.py"
fi

# =============================================================================
# STEP 5: Create Data Directory and Initial Config
# =============================================================================
echo -e "${YELLOW}[Step 5/5] Setting up data directory...${NC}"

DATA_DIR="$SCRIPT_DIR/data"
mkdir -p "$DATA_DIR"

# Create initial .env file if it doesn't exist
ENV_FILE="$DATA_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    echo "  Creating initial .env file..."
    cat > "$ENV_FILE" << 'EOF'
# Conscious Pebble Configuration
# Edit these values or use the Settings tab in the GUI

LLM_PROVIDER=Local MLX
OPENAI_BASE_URL=http://localhost:8080/v1
OPENAI_API_KEY=local-dev-key
OPENAI_MODEL=local-model

TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
ALLOWED_USER_ID=

# Voice Service Settings
SENSES_BASE_URL=http://localhost:8081

# MLX Settings (Apple Silicon)
MLX_MODEL_PATH=mlx-community/Llama-3.2-3B-Instruct-4bit
MLX_KV_BITS=4
EOF
    echo -e "${GREEN}✓ Created .env file at: $ENV_FILE${NC}"
else
    echo -e "${GREEN}✓ .env file already exists${NC}"
fi

# Deactivate venv
deactivate

# =============================================================================
# COMPLETE
# =============================================================================
echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              Installation Complete!                          ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo ""
echo "To start Conscious Pebble:"
echo -e "  ${BLUE}./run_mac.sh${NC}"
echo ""
echo "Or manually:"
echo "  1. source .pebble_env/bin/activate"
echo "  2. python -m uvicorn senses_service:app --port 8081 &"
echo "  3. python home_control.py"
echo ""
echo "Then open: ${BLUE}http://localhost:7860${NC}"
echo ""
echo -e "${YELLOW}Note: Configure your LLM provider in the Settings tab!${NC}"
echo "  For OpenRouter, get your API key from: https://openrouter.ai/keys"
echo ""