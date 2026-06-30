#!/bin/bash
# Video Thumbnail Matcher - Easy launcher for macOS / Linux
# Double-click this file on macOS (or run in Terminal)

set -e

echo "🎥 Video Thumbnail Matcher - Launcher"
echo "======================================"

# Detect Python
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo "❌ Python 3 not found."
    echo "Please install Python 3.10 or newer:"
    echo "  - macOS: brew install python   or download from python.org"
    echo "  - Then re-run this script."
    exit 1
fi

echo "Using: $($PYTHON --version)"

# Create virtual environment if it doesn't exist
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment..."
    $PYTHON -m venv "$VENV_DIR"
fi

# Activate venv
source "$VENV_DIR/bin/activate"

# Upgrade pip and install requirements
echo "📥 Installing dependencies (first time may take a minute)..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "✅ Ready! Starting the app..."
echo "The tool will open in your browser automatically."
echo "Press Ctrl+C in this window to stop the server."
echo ""

# Run Streamlit
streamlit run app.py --server.headless true --browser.gatherUsageStats false
