#!/bin/bash

# Exit on any error
set -e

echo "=== FastAPI Chat API Installation Script ==="

# 1. Check if Python 3 is installed
if ! command -v python3 &> /dev/null
then
    echo "❌ Python3 is not installed. Please install Python 3.8+ and re-run."
    exit 1
fi

# 2. Check if pip is installed
if ! command -v pip3 &> /dev/null
then
    echo "❌ pip3 is not installed. Please install pip and re-run."
    exit 1
fi

# 3. Create virtual environment
echo "Creating virtual environment..."
python3 -m venv ChaTCFD

# 4. Activate virtual environment
source ChaTCFD/bin/activate

# 5. Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# 6. Install dependencies
echo "Installing dependencies..."
pip install fastapi uvicorn pydantic requests

# 7. Create .env example (optional)
if [ ! -f ".env" ]; then
    echo "PORT=8000" > .env
    echo "Created default .env file (PORT=8000)"
fi

echo "=== Installation complete! ==="
echo ""
echo "To activate the environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To start the server, run:"
echo "  uvicorn main:app --reload --port 8000"
echo ""
