#!/bin/bash
# Setup script for LLM Analysis Quiz Solver

echo "Setting up LLM Analysis Quiz Solver..."

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env and fill in your configuration"
echo "2. Activate the virtual environment: source venv/bin/activate"
echo "3. Run the server: python main.py"


