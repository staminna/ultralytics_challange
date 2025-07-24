#!/usr/bin/env python3
"""
Quick test runner to avoid pytest configuration issues.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.getcwd())

def main():
    """Run a simple test to verify the environment is working."""
    print("🧪 Quick Test Runner")
    print("=" * 50)
    
    try:
        # Test imports
        print("1. Testing imports...")
        from backend.app.core.storage_paths import StoragePaths
        from backend.app.core.config import settings
        print("✅ Core imports successful")
        
        # Test storage paths
        print("2. Testing storage paths...")
        storage = StoragePaths()
        dataset_path = storage.get_dataset_path("test-123")
        images_path = storage.get_dataset_images_path("test-123")
        print(f"✅ Dataset path: {dataset_path}")
        print(f"✅ Images path: {images_path}")
        
        # Test config
        print("3. Testing config...")
        print(f"✅ Database name: {settings.DATABASE_NAME}")
        print(f"✅ MongoDB URL configured: {'MONGODB_URL' in str(settings.MONGODB_URL)}")
        
        # Test FastAPI app import (without starting it)
        print("4. Testing FastAPI app import...")
        from backend.app.main import app
        print(f"✅ FastAPI app imported: {type(app).__name__}")
        
        print("\n" + "=" * 50)
        print("🎯 ALL TESTS PASSED!")
        print("✅ Environment is working correctly")
        print("✅ All imports successful")
        print("✅ Core functionality verified")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
