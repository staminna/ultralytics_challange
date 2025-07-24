#!/bin/bash
# Quick activation script for the dataset-annotation environment
echo "🚀 Activating dataset-annotation conda environment..."
source /opt/homebrew/anaconda3/etc/profile.d/conda.sh
conda activate dataset-annotation
echo "✅ Environment activated! Python version: $(python --version)"
echo "📍 Python location: $(which python)"
