#!/bin/bash
# Build script for Render - Forces Python 3.11

set -e

echo "Setting Python version to 3.11..."
export PYTHON_VERSION=3.11.9

# Install Python 3.11 if not available
if ! command -v python3.11 &> /dev/null; then
    echo "Python 3.11 not found, using available Python..."
    python3 --version
else
    echo "Using Python 3.11"
    python3.11 --version
fi

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright
echo "Installing Playwright browsers..."
playwright install chromium

echo "Build complete!"

