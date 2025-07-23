#!/usr/bin/env python3
"""
Quick Pipeline Validation Script
================================

Fast validation of the YOLO Dataset Annotation Service core functionality.
This script performs essential tests without hanging operations.

Usage:
    python quick_pipeline_test.py
"""

import requests
import time
import json
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime

class QuickValidator:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.results = []
        
    def test_health(self):
        """Test service health"""
        print("🔍 Testing service health...")
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Service is healthy")
                self.results.append(("Health Check", "PASS"))
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                self.results.append(("Health Check", "FAIL"))
                return False
        except Exception as e:
            print(f"❌ Service not accessible: {e}")
            self.results.append(("Health Check", "FAIL"))
            return False
    
    def test_list_datasets(self):
        """Test dataset listing"""
        print("📋 Testing dataset listing...")
        try:
            response = requests.get(f"{self.base_url}/api/v1/datasets/", timeout=10)
            if response.status_code == 200:
                datasets = response.json()
                print(f"✅ Found {len(datasets)} datasets")
                self.results.append(("List Datasets", "PASS"))
                return True
            else:
                print(f"❌ Dataset listing failed: {response.status_code}")
                self.results.append(("List Datasets", "FAIL"))
                return False
        except Exception as e:
            print(f"❌ Dataset listing error: {e}")
            self.results.append(("List Datasets", "FAIL"))
            return False
    
    def test_create_dataset(self):
        """Test dataset creation"""
        print("➕ Testing dataset creation...")
        try:
            dataset_data = {
                "name": f"test_dataset_{int(time.time())}",
                "description": "Quick validation test dataset",
                "format": "yolo"
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/datasets/",
                json=dataset_data,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                dataset = response.json()
                dataset_id = dataset["id"]
                print(f"✅ Created dataset: {dataset_id}")
                self.results.append(("Create Dataset", "PASS"))
                return dataset_id
            else:
                print(f"❌ Dataset creation failed: {response.status_code}")
                print(f"Response: {response.text}")
                self.results.append(("Create Dataset", "FAIL"))
                return None
        except Exception as e:
            print(f"❌ Dataset creation error: {e}")
            self.results.append(("Create Dataset", "FAIL"))
            return None
    
    def create_small_test_zip(self):
        """Create a tiny test YOLO dataset"""
        temp_dir = Path(tempfile.mkdtemp())
        dataset_dir = temp_dir / "test_dataset"
        
        # Create structure
        (dataset_dir / "images" / "train").mkdir(parents=True)
        (dataset_dir / "labels" / "train").mkdir(parents=True)
        
        # Create one test file
        img_path = dataset_dir / "images" / "train" / "test.jpg"
        img_path.write_bytes(b"fake_image_data" * 10)
        
        label_path = dataset_dir / "labels" / "train" / "test.txt"
        label_path.write_text("0 0.5 0.5 0.3 0.3\n")
        
        # Create data.yaml
        yaml_content = "train: images/train\nval: images/train\nnc: 1\nnames: ['test_class']\n"
        (dataset_dir / "data.yaml").write_text(yaml_content)
        
        # Create ZIP
        zip_path = temp_dir / "test_dataset.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_path in dataset_dir.rglob('*'):
                if file_path.is_file():
                    zipf.write(file_path, file_path.relative_to(temp_dir))
        
        return zip_path
    
    def test_chunked_upload(self, dataset_id):
        """Test chunked upload with tiny dataset"""
        print("📦 Testing chunked upload...")
        try:
            zip_path = self.create_small_test_zip()
            file_size = zip_path.stat().st_size
            print(f"📁 Test file size: {file_size} bytes")
            
            # Upload in 2 chunks
            chunk_size = file_size // 2 + 1
            upload_id = f"test_upload_{int(time.time())}"
            
            with open(zip_path, 'rb') as f:
                file_data = f.read()
            
            total_chunks = 2
            
            # Upload chunks
            for chunk_num in range(total_chunks):
                start_idx = chunk_num * chunk_size
                end_idx = min(start_idx + chunk_size, len(file_data))
                chunk_data = file_data[start_idx:end_idx]
                
                if not chunk_data:  # Skip empty chunks
                    continue
                
                files = {'chunk_file': ('chunk.zip', chunk_data, 'application/zip')}
                params = {
                    'dataset_id': dataset_id,
                    'upload_id': upload_id,
                    'chunk_number': chunk_num,
                    'total_chunks': total_chunks
                }
                
                response = requests.post(
                    f"{self.base_url}/api/v1/datasets/import/yolo/chunk",
                    files=files,
                    params=params,
                    timeout=30
                )
                
                if response.status_code in [200, 201]:
                    print(f"✅ Chunk {chunk_num + 1} uploaded successfully")
                else:
                    print(f"❌ Chunk {chunk_num + 1} failed: {response.status_code}")
                    print(f"Response: {response.text}")
                    self.results.append(("Chunked Upload", "FAIL"))
                    return False
            
            print("✅ Chunked upload completed successfully")
            self.results.append(("Chunked Upload", "PASS"))
            
            # Clean up
            zip_path.unlink()
            return True
            
        except Exception as e:
            print(f"❌ Chunked upload error: {e}")
            self.results.append(("Chunked Upload", "FAIL"))
            return False
    
    def test_api_docs(self):
        """Test API documentation accessibility"""
        print("📚 Testing API documentation...")
        try:
            response = requests.get(f"{self.base_url}/docs", timeout=5)
            if response.status_code == 200:
                print("✅ API docs accessible")
                self.results.append(("API Docs", "PASS"))
                return True
            else:
                print("⚠️  API docs not accessible")
                self.results.append(("API Docs", "WARN"))
                return False
        except Exception as e:
            print(f"⚠️  API docs error: {e}")
            self.results.append(("API Docs", "WARN"))
            return False
    
    def display_results(self):
        """Display final results"""
        print("\n" + "="*60)
        print("🎯 QUICK PIPELINE VALIDATION RESULTS")
        print("="*60)
        
        passed = sum(1 for _, status in self.results if status == "PASS")
        failed = sum(1 for _, status in self.results if status == "FAIL")
        warned = sum(1 for _, status in self.results if status == "WARN")
        total = len(self.results)
        
        for test_name, status in self.results:
            emoji = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
            print(f"{emoji} {test_name}: {status}")
        
        print("-" * 60)
        print(f"📊 Summary: {passed} PASSED, {failed} FAILED, {warned} WARNINGS")
        
        success_rate = (passed / total * 100) if total > 0 else 0
        print(f"🎯 Success Rate: {success_rate:.1f}%")
        
        if failed == 0:
            print("\n🎉 PIPELINE VALIDATION SUCCESSFUL! 🎉")
            print("✅ Your YOLO Dataset Annotation Service is operational!")
            print("✅ Chunked upload system is working!")
            print("✅ Core API endpoints are functional!")
            return True
        else:
            print(f"\n⚠️  VALIDATION COMPLETED WITH {failed} ISSUES")
            print("Please check the failed tests above.")
            return False
    
    def run_validation(self):
        """Run quick validation"""
        print("🚀 YOLO Dataset Service - Quick Pipeline Validation")
        print("="*60)
        
        start_time = time.time()
        
        # Run tests
        if not self.test_health():
            print("❌ Service not healthy, stopping validation")
            return False
        
        self.test_api_docs()
        self.test_list_datasets()
        
        dataset_id = self.test_create_dataset()
        if dataset_id:
            self.test_chunked_upload(dataset_id)
        
        # Show results
        elapsed = time.time() - start_time
        print(f"\n⏱️  Total time: {elapsed:.2f} seconds")
        
        return self.display_results()

def main():
    """Main function"""
    validator = QuickValidator()
    
    try:
        success = validator.run_validation()
        
        # Save results
        report = {
            "timestamp": datetime.now().isoformat(),
            "results": validator.results,
            "success": success
        }
        
        with open("quick_validation_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Report saved to: quick_validation_report.json")
        
        if success:
            print("\n🎊 CONGRATULATIONS! Your pipeline is working! 🎊")
            return 0
        else:
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️  Validation interrupted")
        return 1
    except Exception as e:
        print(f"\n💥 Validation failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
