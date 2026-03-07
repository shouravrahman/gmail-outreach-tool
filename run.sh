#!/bin/bash
# Quick Start - Bulk Email Tool (Local Development)

set -e  # Exit on error

echo "🚀 Bulk Email Tool - Starting..."
echo "================================="

# Activate virtual environment
if [ ! -d "venv" ]; then
    echo "� Creating virtual environment..."
    python3 -m venv venv
fi

echo "✓ Activating virtual environment..."
source venv/bin/activate

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  No .env file found."
    echo "   Please copy the example and fill in your API keys and database URL:"
    echo "   cp .env.example .env"
    echo ""
fi

# Run Streamlit
echo "Starting Streamlit app..."
echo "Visit: http://localhost:8501"
echo ""
streamlit run app.py
