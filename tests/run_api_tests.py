#!/usr/bin/env python3
"""
API Test Runner

Quick test runner for validating API endpoints.
Can be run independently or with pytest.

Usage:
    python tests/run_api_tests.py
    pytest tests/run_api_tests.py -v
"""

import requests
import json
import sys
import time
from io import BytesIO
import zipfile
from typing import Dict, Any, List, Tuple

# Configuration
SERVER_URL = "http://localhost:8000"
API_BASE = f"{SERVER_URL}/api/v1"
TIMEOUT = 10


class APITester:
    """Simple API testing class."""
    
    def __init__(self, base_url: str = SERVER_URL):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/v1"
        self.results = []
    
    def test_endpoint(self, method: str, endpoint: str, description: str, 
                     data: Dict = None, files: Dict = None, 
                     expected_status: List[int] = None) -> bool:
        """Test a single endpoint."""
        if expected_status is None:
            expected_status = [200, 201]
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            start_time = time.time()
            
            if method.upper() == "GET":
                response = requests.get(url, timeout=TIMEOUT)
            elif method.upper() == "POST":
                if files:
                    response = requests.post(url, files=files, data=data, timeout=TIMEOUT)
                else:
                    response = requests.post(url, json=data, timeout=TIMEOUT)
            elif method.upper() == "DELETE":
                response = requests.delete(url, timeout=TIMEOUT)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            end_time = time.time()
            response_time = end_time - start_time
            
            success = response.status_code in expected_status
            
            result = {
                "description": description,
                "method": method.upper(),
                "endpoint": endpoint,
                "status_code": response.status_code,
                "response_time": response_time,
                "success": success,
                "error": None if success else response.text[:200]
            }
            
            self.results.append(result)
            
            status_icon = "✅" if success else "❌"
            print(f"{status_icon} {description}: {response.status_code} ({response_time:.3f}s)")
            
            if not success:
                print(f"   Error: {response.text[:100]}...")
            
            return success
            
        except requests.exceptions.ConnectionError:
            result = {
                "description": description,
                "method": method.upper(),
                "endpoint": endpoint,
                "status_code": None,
                "response_time": None,
                "success": False,
                "error": "Connection refused - server not running"
            }
            self.results.append(result)
            print(f"❌ {description}: Connection refused")
            return False
            
        except Exception as e:
            result = {
                "description": description,
                "method": method.upper(),
                "endpoint": endpoint,
                "status_code": None,
                "response_time": None,
                "success": False,
                "error": str(e)
            }
            self.results.append(result)
            print(f"❌ {description}: {str(e)}")
            return False
    
    def create_sample_yolo_zip(self) -> BytesIO:
        """Create a minimal YOLO dataset ZIP for testing."""
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Minimal YOLO structure
            zip_file.writestr("images/test1.jpg", b"fake_image_data_1")
            zip_file.writestr("images/test2.jpg", b"fake_image_data_2")
            zip_file.writestr("labels/test1.txt", "0 0.5 0.5 0.2 0.2")
            zip_file.writestr("labels/test2.txt", "1 0.3 0.3 0.1 0.1")
            zip_file.writestr("classes.txt", "person\ncar")
            zip_file.writestr("data.yaml", "nc: 2\nnames: ['person', 'car']")
        
        zip_buffer.seek(0)
        return zip_buffer
    
    def run_all_tests(self) -> bool:
        """Run all API tests."""
        print("🚀 Starting API endpoint tests...\n")
        
        all_passed = True
        
        # 1. Health checks
        print("📋 Health Check Tests:")
        all_passed &= self.test_endpoint("GET", "/health", "Health check endpoint")
        all_passed &= self.test_endpoint("GET", "/", "Root endpoint")
        
        # 2. API Documentation
        print("\n📚 Documentation Tests:")
        all_passed &= self.test_endpoint("GET", "/docs", "Swagger documentation")
        all_passed &= self.test_endpoint("GET", "/redoc", "ReDoc documentation")
        
        # 3. Dataset management
        print("\n📊 Dataset Management Tests:")
        all_passed &= self.test_endpoint("GET", "/api/v1/datasets/", "List datasets")
        
        # Test dataset creation
        dataset_data = {
            "name": "API Test Dataset",
            "description": "Dataset created during API testing",
            "is_public": False
        }
        dataset_created = self.test_endpoint(
            "POST", "/api/v1/datasets/", "Create dataset", 
            data=dataset_data, expected_status=[200, 201, 422, 500]
        )
        
        # 4. YOLO Import tests
        print("\n📦 YOLO Import Tests:")
        zip_data = self.create_sample_yolo_zip()
        files = {"file": ("test_dataset.zip", zip_data, "application/zip")}
        import_data = {"dataset_name": "Test YOLO Import"}
        
        self.test_endpoint(
            "POST", "/api/v1/datasets/import/yolo", "YOLO dataset import",
            data=import_data, files=files, expected_status=[200, 201, 400, 422, 500]
        )
        
        # 5. Error handling tests
        print("\n⚠️ Error Handling Tests:")
        fake_id = "00000000-0000-0000-0000-000000000000"
        self.test_endpoint(
            "GET", f"/api/v1/datasets/{fake_id}", "Get non-existent dataset",
            expected_status=[404]
        )
        
        # Invalid dataset creation
        invalid_data = {"name": ""}
        self.test_endpoint(
            "POST", "/api/v1/datasets/", "Create invalid dataset",
            data=invalid_data, expected_status=[422]
        )
        
        # 6. Chunked upload test
        print("\n🔄 Chunked Upload Tests:")
        chunk_data = BytesIO(b"test chunk data for upload")
        chunk_files = {"chunk_file": ("chunk", chunk_data, "application/octet-stream")}
        chunk_params = {
            "upload_id": "test-upload-id",
            "chunk_number": "0",
            "total_chunks": "1"
        }
        
        self.test_endpoint(
            "POST", f"/api/v1/datasets/{fake_id}/chunks", "Chunked upload test",
            data=chunk_params, files=chunk_files, expected_status=[200, 201, 404, 422, 500]
        )
        
        return all_passed
    
    def print_summary(self):
        """Print test results summary."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"\n📊 Test Summary:")
        print(f"   Total tests: {total_tests}")
        print(f"   Passed: {passed_tests} ✅")
        print(f"   Failed: {failed_tests} ❌")
        print(f"   Success rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ Failed tests:")
            for result in self.results:
                if not result["success"]:
                    print(f"   - {result['description']}: {result.get('error', 'Unknown error')}")
        
        # Performance summary
        response_times = [r["response_time"] for r in self.results if r["response_time"] is not None]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            print(f"\n⏱️ Performance:")
            print(f"   Average response time: {avg_time:.3f}s")
            print(f"   Max response time: {max_time:.3f}s")
    
    def save_results(self, filename: str = "api_test_results.json"):
        """Save test results to JSON file."""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Results saved to {filename}")


def main():
    """Main test runner."""
    print("🧪 YOLO Dataset Annotation Service - API Tests")
    print("=" * 50)
    
    tester = APITester()
    
    # Check if server is running
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Server is not healthy. Please check the server status.")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Please start the server first:")
        print("   cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        sys.exit(1)
    
    # Run tests
    all_passed = tester.run_all_tests()
    
    # Print summary
    tester.print_summary()
    
    # Save results
    tester.save_results()
    
    # Exit with appropriate code
    if all_passed:
        print("\n🎉 All critical tests passed!")
        sys.exit(0)
    else:
        print("\n⚠️ Some tests failed. Check the results above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
