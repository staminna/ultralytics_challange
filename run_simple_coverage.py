#!/usr/bin/env python3
"""
Simple coverage test runner that avoids MongoDB connection issues.
"""

import sys
import os
import subprocess
import time

# Add project root to path
sys.path.insert(0, os.getcwd())

def test_imports():
    """Test that key modules can be imported."""
    print("🧪 Testing imports...")
    
    try:
        # Test core imports
        from backend.app.core.storage_paths import StoragePaths
        print("✅ StoragePaths imported")
        
        from backend.app.core.config import settings
        print("✅ Config imported")
        
        from backend.app.models.mongo_models import DatasetModel
        print("✅ Mongo models imported")
        
        from backend.app.schemas.dataset import DatasetCreate
        print("✅ Schemas imported")
        
        # Test storage paths functionality
        storage = StoragePaths()
        dataset_path = storage.get_dataset_path("test-123")
        print(f"✅ Storage paths working: {dataset_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def run_coverage_with_timeout():
    """Run coverage tests with timeout to avoid hanging."""
    print("🚀 Running coverage tests with timeout...")
    
    try:
        # Run pytest with timeout
        cmd = [
            "python", "-m", "pytest", 
            "--cov=backend/app", 
            "tests/test_coverage_boost.py",
            "--cov-report=term-missing",
            "-v",
            "--tb=short"
        ]
        
        print(f"Running: {' '.join(cmd)}")
        
        # Set environment variables
        env = os.environ.copy()
        env['PYTHONPATH'] = '.'
        
        result = subprocess.run(
            cmd, 
            timeout=60,  # 60 second timeout
            capture_output=True, 
            text=True,
            env=env
        )
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Tests timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def main():
    """Main function."""
    print("🎯 Simple Coverage Test Runner")
    print("=" * 50)
    
    # Test imports first
    if not test_imports():
        print("❌ Import tests failed")
        return 1
    
    print("\n" + "=" * 50)
    
    # Run coverage tests
    if run_coverage_with_timeout():
        print("✅ Coverage tests completed successfully")
        return 0
    else:
        print("❌ Coverage tests failed or timed out")
        return 1

if __name__ == "__main__":
    sys.exit(main())
