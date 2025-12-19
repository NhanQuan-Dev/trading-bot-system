#!/bin/bash
# Development run script

set -e

echo "=== Trading Bot Platform - Development Mode ==="
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Create necessary directories
mkdir -p logs data

# Set environment
export ENVIRONMENT=development
export DEBUG=true

# Run application
echo "Starting application..."
cd src
python -m trading.main

deactivate
