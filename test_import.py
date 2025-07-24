#!/usr/bin/env python3
"""Simple test to check if imports work."""

import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.getcwd())

try:
    print("Testing imports...")
    from backend.app.core.storage_paths import StoragePaths
    print("✅ StoragePaths imported successfully")
    
    from backend.app.main import app
    print("✅ FastAPI app imported successfully")
    
    print("🎯 All imports successful!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Other error: {e}")
    sys.exit(1)
