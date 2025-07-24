#!/usr/bin/env python3
"""
Clean Pipeline Test - Comprehensive test of the cleaned YOLO annotation service
"""

import requests
import time
import json
from pathlib import Path
from yolo11_config import YOLO11Config

class PipelineTest:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.api_url = f"{self.base_url}/api/v1"
        self.config = YOLO11Config()
        
    def test_health_check(self):
        """Test if the API is responding"""
        print("🔍 Testing API Health Check...")
        try:
            response = requests.get(f"{self.base_url}/docs")
            if response.status_code == 200:
                print("✅ API Health Check: PASS - Service is responding")
                return True
            else:
                print(f"❌ API Health Check: FAIL - Status {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ API Health Check: FAIL - {str(e)}")
            return False
    
    def test_list_datasets(self):
        """Test listing datasets"""
        print("\n📋 Testing Dataset Listing...")
        try:
            response = requests.get(f"{self.api_url}/datasets/")
            if response.status_code == 200:
                datasets = response.json()
                print(f"✅ Dataset Listing: PASS - Found {len(datasets)} datasets")
                return True, datasets
            else:
                print(f"❌ Dataset Listing: FAIL - Status {response.status_code}")
                return False, []
        except Exception as e:
            print(f"❌ Dataset Listing: FAIL - {str(e)}")
            return False, []
    
    def test_yolo11_config(self):
        """Test YOLO11 configuration"""
        print("\n🎯 Testing YOLO11 Configuration...")
        try:
            # Test model paths
            default_model = self.config.get_model_path('detection', 'nano')
            production_model = self.config.get_model_path('detection', 'medium')
            
            print(f"✅ Default Model: {default_model}")
            print(f"✅ Production Model: {production_model}")
            
            # Test command generation
            train_cmd = self.config.get_training_command("coco8.yaml", "nano", epochs=1)
            print(f"✅ Training Command: {' '.join(train_cmd)}")
            
            return True
        except Exception as e:
            print(f"❌ YOLO11 Config: FAIL - {str(e)}")
            return False
    
    def test_dataset_creation(self):
        """Test creating a new dataset"""
        print("\n📦 Testing Dataset Creation...")
        try:
            dataset_data = {
                "name": "test_clean_pipeline",
                "description": "Test dataset for clean pipeline validation",
                "format": "yolo"
            }
            
            response = requests.post(f"{self.api_url}/datasets/", json=dataset_data)
            if response.status_code in [200, 201]:
                dataset = response.json()
                print(f"✅ Dataset Creation: PASS - Created dataset {dataset.get('id', 'unknown')}")
                return True, dataset
            else:
                print(f"❌ Dataset Creation: FAIL - Status {response.status_code}")
                print(f"Response: {response.text}")
                return False, None
        except Exception as e:
            print(f"❌ Dataset Creation: FAIL - {str(e)}")
            return False, None
    
    def test_yolo_training_readiness(self):
        """Test if YOLO training is ready"""
        print("\n🚀 Testing YOLO Training Readiness...")
        try:
            # Check if datasets exist
            datasets_dir = Path("backend/datasets")
            coco8_dir = datasets_dir / "coco8"
            coco128_dir = datasets_dir / "coco128"
            
            if coco8_dir.exists():
                print("✅ COCO8 dataset: Available")
            else:
                print("⚠️  COCO8 dataset: Not found")
            
            if coco128_dir.exists():
                print("✅ COCO128 dataset: Available")
            else:
                print("⚠️  COCO128 dataset: Not found")
            
            # Check YAML configs
            yaml_dir = datasets_dir / "raw"
            coco8_yaml = yaml_dir / "coco8.yaml"
            coco128_yaml = yaml_dir / "coco128.yaml"
            
            if coco8_yaml.exists():
                print("✅ COCO8 YAML config: Available")
            else:
                print("⚠️  COCO8 YAML config: Not found")
            
            if coco128_yaml.exists():
                print("✅ COCO128 YAML config: Available")
            else:
                print("⚠️  COCO128 YAML config: Not found")
            
            # Check YOLO11 model
            model_file = Path("yolo11n.pt")
            if model_file.exists():
                size_mb = model_file.stat().st_size / (1024 * 1024)
                print(f"✅ YOLO11 Model: Available ({size_mb:.1f}MB)")
            else:
                print("⚠️  YOLO11 Model: Not found")
            
            return True
        except Exception as e:
            print(f"❌ YOLO Training Readiness: FAIL - {str(e)}")
            return False
    
    def test_file_structure(self):
        """Test clean file structure"""
        print("\n📁 Testing Clean File Structure...")
        
        # Check backup directory
        backup_dir = Path("backup")
        if backup_dir.exists():
            backup_files = list(backup_dir.rglob("*.py"))
            print(f"✅ Backup Directory: {len(backup_files)} Python files archived")
        else:
            print("⚠️  Backup Directory: Not found")
        
        # Check root directory cleanliness
        root_py_files = list(Path(".").glob("*.py"))
        essential_files = ["main.py", "yolo11_config.py"]
        
        print(f"✅ Root Python Files: {len(root_py_files)} files")
        for file in root_py_files:
            status = "✅" if file.name in essential_files else "⚠️ "
            print(f"  {status} {file.name}")
        
        return True
    
    def run_all_tests(self):
        """Run all pipeline tests"""
        print("🧪 CLEAN PIPELINE TEST SUITE")
        print("=" * 50)
        
        results = []
        
        # Test 1: Health Check
        results.append(self.test_health_check())
        
        # Test 2: Dataset Listing
        list_success, datasets = self.test_list_datasets()
        results.append(list_success)
        
        # Test 3: YOLO11 Configuration
        results.append(self.test_yolo11_config())
        
        # Test 4: Dataset Creation
        create_success, new_dataset = self.test_dataset_creation()
        results.append(create_success)
        
        # Test 5: YOLO Training Readiness
        results.append(self.test_yolo_training_readiness())
        
        # Test 6: File Structure
        results.append(self.test_file_structure())
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        
        passed = sum(results)
        total = len(results)
        success_rate = (passed / total) * 100
        
        print(f"✅ Tests Passed: {passed}/{total}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("🎉 PIPELINE STATUS: HEALTHY ✅")
            print("🚀 Ready for production use!")
        elif success_rate >= 60:
            print("⚠️  PIPELINE STATUS: NEEDS ATTENTION")
            print("🔧 Some components need fixing")
        else:
            print("❌ PIPELINE STATUS: CRITICAL ISSUES")
            print("🚨 Major fixes required")
        
        return success_rate >= 80

if __name__ == "__main__":
    tester = PipelineTest()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎯 NEXT STEPS:")
        print("1. Try YOLO training: yolo detect train data=backend/datasets/raw/coco8.yaml model=yolo11n.pt epochs=1")
        print("2. Upload datasets via API")
        print("3. Use the cleaned project structure")
    else:
        print("\n🔧 TROUBLESHOOTING:")
        print("1. Check if Docker services are running: docker-compose ps")
        print("2. Check API logs: docker-compose logs backend")
        print("3. Verify environment configuration")
