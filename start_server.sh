#!/bin/bash

# Kill any existing processes on port 8000
echo "🔄 Killing existing processes on port 8000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Activate conda environment
echo "🐍 Activating conda environment..."
source ~/miniconda3/etc/profile.d/conda.sh
conda activate dataset-annotation

# Change to backend directory
cd backend

# Start the server
echo "🚀 Starting FastAPI server..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
