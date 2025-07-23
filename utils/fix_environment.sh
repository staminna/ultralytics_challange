#!/bin/bash
# Fix pandas/numpy compatibility issues in conda environment

set -e  # Exit on any error

echo "🔧 Fixing pandas/numpy compatibility in conda environment..."

# Get current environment name
CURRENT_ENV=$(conda info --envs | grep '*' | awk '{print $1}')
echo "Current environment: $CURRENT_ENV"

# Backup current environment
echo "📦 Creating backup of current environment..."
conda env export > environment_backup_$(date +%Y%m%d_%H%M%S).yml

# Option 1: Update current environment
echo "🔄 Updating current environment with compatible packages..."

# Remove problematic packages first
echo "Removing incompatible packages..."
conda remove --yes pandas numpy ultralytics || true

# Install compatible versions from conda-forge
echo "Installing compatible numpy and pandas from conda-forge..."
conda install --yes -c conda-forge numpy=1.26.4 pandas=2.2.2

# Install PyTorch ecosystem
echo "Installing PyTorch ecosystem..."
conda install --yes -c pytorch pytorch=2.3.0 torchvision=0.18.0 torchaudio=2.3.0

# Install other conda packages
echo "Installing additional conda packages..."
conda install --yes -c conda-forge scipy=1.13.0 pillow=10.3.0 opencv=4.9.0

# Install ultralytics via pip (after conda packages are stable)
echo "Installing ultralytics via pip..."
pip install ultralytics>=8.3.0

# Verify installation
echo "🧪 Verifying installation..."
python -c "
import numpy as np
import pandas as pd
import ultralytics
print(f'✅ NumPy: {np.__version__}')
print(f'✅ Pandas: {pd.__version__}')
print(f'✅ Ultralytics: {ultralytics.__version__}')
print('✅ All packages imported successfully!')
"

echo "🎉 Environment fixed successfully!"
echo ""
echo "📋 Summary of changes:"
echo "  - NumPy: 1.26.4 (conda-forge)"
echo "  - Pandas: 2.2.2 (conda-forge)"
echo "  - PyTorch: 2.3.0 (pytorch channel)"
echo "  - Ultralytics: latest (pip)"
echo ""
echo "🚀 You can now run YOLO training without pandas/numpy errors!"
