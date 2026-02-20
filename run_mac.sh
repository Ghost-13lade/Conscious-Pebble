#!/bin/bash
#
# Conscious Pebble - macOS Launcher (Full Version with Voice)
#
# This script starts all Conscious Pebble services:
#   1. Senses Service (Voice: Whisper STT + Kokoro TTS) on port 8081
#   2. Home Control GUI on port 7860
#
# Usage:
#   chmod +x run_mac.sh
#   ./run_mac.sh
#

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Virtual environment
VENV_DIR="$SCRIPT_DIR/.pebble_env"

# Check if venv exists
if [[ ! -d "$VENV_DIR" ]]; then
    echo -e "${RED}Error: Virtual environment not found!${NC}"
    echo "Please run setup_mac.sh first:"
    echo "  ./setup_mac.sh"
    exit 1
fi

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║          Conscious Pebble - Starting Services                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    if [[ ! -z "$SENSES_PID" ]]; then
        kill $SENSES_PID 2>/dev/null
        echo "  Stopped Senses Service"
    fi
    deactivate
    exit 0
}
trap cleanup SIGINT SIGTERM

# =============================================================================
# Start Senses Service (Voice)
# =============================================================================
echo -e "${YELLOW}[1/2] Starting Senses Service (Voice)...${NC}"
echo "  Port: 8081"
echo "  This may take a moment to load models..."

# Start senses service in background
python -m uvicorn senses_service:app --host 0.0.0.0 --port 8081 --log-level warning &
SENSES_PID=$!

# Wait for senses to be ready
echo "  Waiting for service to be ready..."
MAX_WAIT=30
WAIT_COUNT=0
while [[ $WAIT_COUNT -lt $MAX_WAIT ]]; do
    if curl -s http://localhost:8081/ > /dev/null 2>&1; then
        break
    fi
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
    echo -n "."
done
echo ""

if [[ $WAIT_COUNT -ge $MAX_WAIT ]]; then
    echo -e "${YELLOW}⚠ Warning: Senses service may not be ready yet.${NC}"
    echo "  Voice features might not work immediately."
else
    echo -e "${GREEN}✓ Senses Service running on port 8081${NC}"
fi

# =============================================================================
# Start Home Control GUI
# =============================================================================
echo -e "${YELLOW}[2/2] Starting Home Control GUI...${NC}"
echo "  Port: 7860"
echo "  Opening browser..."

# Open browser after a short delay
sleep 2 && open "http://localhost:7860" &

# Start the GUI (this blocks)
echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Conscious Pebble is running!${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "  GUI:      ${BLUE}http://localhost:7860${NC}"
echo "  Voice:    ${BLUE}http://localhost:8081${NC}"
echo ""
echo "  Press ${YELLOW}Ctrl+C${NC} to stop all services"
echo ""

python home_control.py

# Cleanup (will be called on exit)
cleanup