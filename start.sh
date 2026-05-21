#!/bin/bash

echo "Starting AllInOne Backend..."

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing dependencies..."
pip install poetry
poetry install --no-root

echo "Starting FastAPI server..."
uvicorn src.main:app --host $APP_HOST --port $APP_PORT --reload