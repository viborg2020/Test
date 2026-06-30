#!/bin/bash
#
# Video Thumbnail Matcher - macOS Double-Click Launcher
# For Apple Silicon (M1/M2/M3/M4) Macs
#
# Instructions:
# 1. Double-click this file in Finder
# 2. If macOS blocks it, right-click → Open (do this twice if needed)
# 3. The app will set itself up and open in your browser
#

set -e

# Change to the directory where this script lives
cd "$(dirname "$0")"

echo "🎥 Starting Video Thumbnail Matcher for Mac..."
echo "=============================================="
echo ""

# Check for Python 3 (prefer native arm64 on Apple Silicon)
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python 3 is not installed on your Mac."
    echo ""
    echo "Please install it using Homebrew (recommended for M1/M-series chips):"
    echo "1. Open Terminal and run:"
    echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    echo "2. Then run:"
    echo "   brew install python"
    echo "3. After installation finishes, double-click this file again."
    echo ""
    read -p "Press Enter to close this window..."
    exit 1
fi

echo "✅ Found Python: $($PYTHON_CMD --version)"
echo ""

VENV_DIR=".venv"

# Create virtual environment if missing
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating isolated Python environment (first time only)..."
    $PYTHON_CMD -m venv "$VENV_DIR"
fi

# Activate the virtual environment
source "$VENV_DIR/bin/activate"

echo "📥 Installing required packages (this may take 1-2 minutes the first time)..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "🚀 Launching Video Thumbnail Matcher..."
echo "It will open automatically in your default browser."
echo "You can close this Terminal window after the browser opens."
echo ""
echo "To stop the app later: Press Ctrl + C in this window."
echo ""

# Launch Streamlit (headless mode so it doesn't try to control the browser strangely)
streamlit run app.py \
    --server.headless true \
    --browser.gatherUsageStats false \
    --server.port 8501
