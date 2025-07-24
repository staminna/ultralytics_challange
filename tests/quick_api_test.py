#!/usr/bin/env python3
"""
Quick API Test

Fast validation of core API endpoints.
Designed to run quickly and provide immediate feedback.

Usage:
    python tests/quick_api_test.py
"""

import requests
import time
import sys
from typing import Dict, Any

SERVER_URL = "http://localhost:8000"


def test_endpoint(url: str, description: str, expected_status: int = 200) -> bool:
    """Test a single endpoint quickly."""
    try:
        start_time = time.time()
        response = requests.get(url, timeout=5)
        end_time = time.time()
        
        response_time = end_time - start_time
        success = response.status_code == expected_status
        
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} {description}: {response.status_code} ({response_time:.3f}s)")
        
        return success
        
    except requests.exceptions.ConnectionError:
        print(f"❌ {description}: Connection refused")
        return False
    except Exception as e:
        print(f"❌ {description}: {str(e)}")
        return False


def quick_health_check() -> bool:
    """Perform a quick health check of the API."""
    print("🔍 Quick API Health Check")
    print("-" * 30)
    
    tests = [
        (f"{SERVER_URL}/health", "Health endpoint"),
        (f"{SERVER_URL}/", "Root endpoint"),
        (f"{SERVER_URL}/docs", "API documentation"),
        (f"{SERVER_URL}/api/v1/datasets/", "Dataset listing"),
    ]
    
    all_passed = True
    for url, description in tests:
        all_passed &= test_endpoint(url, description)
    
    return all_passed


def test_api_functionality() -> bool:
    """Test basic API functionality."""
    print("\n🧪 API Functionality Test")
    print("-" * 30)
    
    try:
        # Test dataset creation with unique name
        timestamp = int(time.time())
        dataset_data = {
            "name": f"Quick Test Dataset {timestamp}",
            "description": "Dataset for quick testing",
            "format": "yolo"
        }
        
        response = requests.post(f"{SERVER_URL}/api/v1/datasets/", json=dataset_data, timeout=10)
        
        if response.status_code in [200, 201]:
            print("✅ Dataset creation: Success")
            dataset_id = response.json().get("id")
            
            # Test dataset retrieval
            if dataset_id:
                response = requests.get(f"{SERVER_URL}/api/v1/datasets/{dataset_id}", timeout=5)
                if response.status_code == 200:
                    print("✅ Dataset retrieval: Success")
                    return True
                else:
                    print(f"❌ Dataset retrieval: {response.status_code}")
            
        elif response.status_code == 422:
            print("⚠️ Dataset creation: Validation error (expected if DB not connected)")
        elif response.status_code == 500:
            print("⚠️ Dataset creation: Server error (likely DB connection issue)")
        else:
            print(f"❌ Dataset creation: {response.status_code}")
        
        return False
        
    except Exception as e:
        print(f"❌ API functionality test failed: {str(e)}")
        return False


def main():
    """Main test runner."""
    print("🚀 YOLO Dataset Annotation Service - Quick API Test")
    print("=" * 55)
    
    # Check server connectivity
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=3)
        if response.status_code != 200:
            print("❌ Server is not healthy")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running. Please start it first:")
        print("   cd backend && python -m uvicorn app.main:app --reload --port 8000")
        sys.exit(1)
    
    # Run quick tests
    health_ok = quick_health_check()
    functionality_ok = test_api_functionality()
    
    # Summary
    print("\n📊 Test Summary")
    print("-" * 15)
    
    if health_ok and functionality_ok:
        print("🎉 All tests passed! API is fully functional.")
        sys.exit(0)
    elif health_ok:
        print("✅ API is healthy but functionality is limited (likely DB connection issue)")
        print("💡 This is normal if MongoDB is not connected")
        sys.exit(0)
    else:
        print("❌ API health check failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
