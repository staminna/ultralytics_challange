#!/bin/bash
# Recreate conda environment from scratch with fixed dependencies

set -e

echo "🔄 Recreating conda environment with fixed dependencies..."

# Backup current environment
echo "📦 Creating backup..."
conda env export > environment_backup_$(date +%Y%m%d_%H%M%S).yml

# Remove existing environment (optional - comment out if you want to keep it)
# echo "🗑️  Removing existing environment..."
# conda env remove -n dataset-annotation --yes || true

# Create new environment from the fixed environment.yml
echo "🆕 Creating new environment from environment.yml..."
conda env create -f environment.yml --force

echo "✅ Environment recreated successfully!"
echo ""
echo "🔧 To activate the fixed environment, run:"
echo "   conda activate dataset-annotation"
echo ""
echo "🧪 To test YOLO training, run:"
echo "   cd backend/datasets"
echo "   yolo detect train data=raw/coco8.yaml model=yolo11n.pt epochs=1"
