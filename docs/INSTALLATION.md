# 🚀 Installation Guide - YOLO Dataset Annotation Service

## 📋 **Overview**

This guide provides instructions for setting up the YOLO Dataset Annotation Service with proper dependency management to avoid pandas/numpy compatibility issues.

## 🔧 **Prerequisites**

- Python 3.12
- Conda (Miniconda or Anaconda)
- Git

## 🎯 **Quick Setup (Recommended)**

### Option 1: Using Conda Environment (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd ultra-assesment

# Create conda environment with compatible packages
conda env create -f environment.yml

# Activate environment
conda activate dataset-annotation

# Verify installation
python -c "import numpy, pandas, ultralytics; print('✅ All packages working!')"
```

### Option 2: Fix Existing Environment

If you already have an environment with compatibility issues:

```bash
# Run the automated fix script
./fix_environment.sh
```

## 📦 **Manual Installation**

If you prefer manual setup:

```bash
# Create new conda environment
conda create -n dataset-annotation python=3.12

# Activate environment
conda activate dataset-annotation

# Install compatible scientific packages via conda
conda install -c conda-forge numpy=1.26.4 pandas=2.2.2 scipy=1.13.0

# Install PyTorch ecosystem
conda install -c pytorch pytorch=2.3.0 torchvision=0.18.0 torchaudio=2.3.0

# Install image processing
conda install -c conda-forge pillow=10.3.0 opencv=4.9.0

# Install remaining packages via pip
pip install -r requirements.txt
```

## 🧪 **Verify Installation**

### Test Core Packages
```bash
python -c "
import numpy as np
import pandas as pd
import ultralytics
import torch
import cv2
print(f'✅ NumPy: {np.__version__}')
print(f'✅ Pandas: {pd.__version__}')
print(f'✅ Ultralytics: {ultralytics.__version__}')
print(f'✅ PyTorch: {torch.__version__}')
print('🎉 All packages imported successfully!')
"
```

### Test YOLO Training
```bash
cd backend/datasets
yolo detect train data=raw/coco8.yaml model=yolo11n.pt epochs=1
```

## 🔍 **Troubleshooting**

### Common Issues

#### 1. **Pandas/NumPy Compatibility Error**
```
ValueError: numpy.dtype size changed, may indicate binary incompatibility
```

**Solution**: Use conda to install numpy and pandas first:
```bash
conda remove numpy pandas ultralytics
conda install -c conda-forge numpy=1.26.4 pandas=2.2.2
pip install ultralytics
```

#### 2. **YOLO Training Fails at End**
The training completes successfully but fails when saving results due to pandas issues.

**Workaround**: Use training flags that avoid result saving:
```bash
yolo detect train data=raw/coco8.yaml model=yolo11n.pt epochs=10 save=False plots=False
```

#### 3. **Missing Dependencies**
If you get import errors, ensure all packages are installed:
```bash
pip install -r requirements.txt
```

## 📁 **Project Structure**

```
ultra-assesment/
├── requirements.txt          # Single comprehensive requirements file
├── environment.yml          # Conda environment with compatible versions
├── fix_environment.sh       # Automated environment fix script
├── recreate_environment.sh  # Environment recreation script
├── backend/
│   ├── datasets/            # YOLO datasets (coco8, coco128)
│   └── scripts/             # Utility scripts
└── INSTALLATION.md          # This file
```

## 🎯 **Key Dependencies**

### Conda-managed (for compatibility):
- `numpy=1.26.4`
- `pandas=2.2.2`
- `pytorch=2.3.0`
- `torchvision=0.18.0`
- `opencv=4.9.0`

### Pip-managed:
- `ultralytics>=8.3.0`
- `fastapi>=0.104.1`
- `google-cloud-*` packages
- Development tools

## 🚀 **Next Steps**

1. **Start the backend server**:
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

2. **Test YOLO training**:
   ```bash
   cd backend/datasets
   yolo detect train data=raw/coco8.yaml model=yolo11n.pt epochs=10
   ```

3. **Run tests**:
   ```bash
   pytest
   ```

## 📞 **Support**

If you encounter issues:
1. Check this troubleshooting section
2. Verify your conda/pip environment
3. Try recreating the environment from scratch
4. Check the GitHub issues for similar problems

---

✅ **Environment ready!** Your YOLO Dataset Annotation Service should now work without pandas/numpy compatibility issues.
