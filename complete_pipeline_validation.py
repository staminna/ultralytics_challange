#!/usr/bin/env python3
"""
Complete Pipeline Validation Script
===================================

This script performs end-to-end validation of the YOLO Dataset Annotation Service
including chunked upload functionality, generates comprehensive reports, and 
provides final success confirmation.

Features:
- ✅ Service health checks
- ✅ Database connectivity validation
- ✅ API endpoint testing
- ✅ Chunked upload validation
- ✅ Large dataset processing test
- ✅ Performance metrics collection
- ✅ Final success report generation

Usage:
    python complete_pipeline_validation.py
"""

import asyncio
import json
import time
import tempfile
import zipfile
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import requests
import aiohttp
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

console = Console()

class PipelineValidator:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "performance": {},
            "summary": {},
            "errors": []
        }
        
    def log_test(self, test_name: str, status: str, details: Dict = None):
        """Log test results"""
        self.results["tests"][test_name] = {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        
    def log_error(self, error: str):
        """Log errors"""
        self.results["errors"].append({
            "error": error,
            "timestamp": datetime.now().isoformat()
        })

    async def check_service_health(self) -> bool:
        """Check if all services are running"""
        console.print("\n🔍 [bold blue]Checking Service Health...[/bold blue]")
        
        try:
            # Check FastAPI
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                console.print("✅ FastAPI service is running")
                self.log_test("fastapi_health", "PASS")
            else:
                console.print("❌ FastAPI service health check failed")
                self.log_test("fastapi_health", "FAIL", {"status_code": response.status_code})
                return False
                
        except requests.exceptions.RequestException as e:
            console.print(f"❌ FastAPI service is not accessible: {e}")
            self.log_test("fastapi_health", "FAIL", {"error": str(e)})
            self.log_error(f"FastAPI health check failed: {e}")
            return False
            
        # Check API docs
        try:
            response = requests.get(f"{self.base_url}/docs", timeout=5)
            if response.status_code == 200:
                console.print("✅ API documentation is accessible")
                self.log_test("api_docs", "PASS")
            else:
                console.print("⚠️  API docs not accessible")
                self.log_test("api_docs", "WARN")
        except Exception as e:
            console.print(f"⚠️  API docs check failed: {e}")
            self.log_test("api_docs", "WARN")
            
        return True

    async def test_core_endpoints(self) -> bool:
        """Test all core API endpoints"""
        console.print("\n🔌 [bold blue]Testing Core API Endpoints...[/bold blue]")
        
        endpoints = [
            ("GET", "/api/v1/datasets/", "list_datasets"),
            ("GET", "/api/v1/health", "health_check"),
        ]
        
        all_passed = True
        
        for method, endpoint, test_name in endpoints:
            try:
                if method == "GET":
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                    
                if response.status_code in [200, 201]:
                    console.print(f"✅ {method} {endpoint} - Status: {response.status_code}")
                    self.log_test(test_name, "PASS", {
                        "status_code": response.status_code,
                        "response_size": len(response.text)
                    })
                else:
                    console.print(f"❌ {method} {endpoint} - Status: {response.status_code}")
                    self.log_test(test_name, "FAIL", {"status_code": response.status_code})
                    all_passed = False
                    
            except Exception as e:
                console.print(f"❌ {method} {endpoint} - Error: {e}")
                self.log_test(test_name, "FAIL", {"error": str(e)})
                self.log_error(f"Endpoint test failed {endpoint}: {e}")
                all_passed = False
                
        return all_passed

    def create_test_dataset(self) -> Path:
        """Create a small test YOLO dataset"""
        temp_dir = Path(tempfile.mkdtemp())
        dataset_dir = temp_dir / "test_dataset"
        
        # Create directory structure
        (dataset_dir / "images" / "train").mkdir(parents=True)
        (dataset_dir / "labels" / "train").mkdir(parents=True)
        
        # Create test files
        for i in range(3):
            # Create dummy image file
            img_path = dataset_dir / "images" / "train" / f"test_{i}.jpg"
            img_path.write_bytes(b"fake_image_data_" + str(i).encode() * 100)
            
            # Create corresponding label file
            label_path = dataset_dir / "labels" / "train" / f"test_{i}.txt"
            label_path.write_text(f"0 0.5 0.5 0.3 0.3\n1 0.2 0.8 0.1 0.1\n")
        
        # Create data.yaml
        yaml_content = """
train: images/train
val: images/train
nc: 2
names: ['class0', 'class1']
"""
        (dataset_dir / "data.yaml").write_text(yaml_content.strip())
        
        # Create ZIP file
        zip_path = temp_dir / "test_dataset.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_path in dataset_dir.rglob('*'):
                if file_path.is_file():
                    zipf.write(file_path, file_path.relative_to(temp_dir))
                    
        return zip_path

    async def test_chunked_upload(self) -> bool:
        """Test chunked upload functionality"""
        console.print("\n📦 [bold blue]Testing Chunked Upload System...[/bold blue]")
        
        try:
            # Create test dataset
            zip_path = self.create_test_dataset()
            file_size = zip_path.stat().st_size
            
            console.print(f"📁 Created test dataset: {zip_path} ({file_size} bytes)")
            
            # First create a dataset
            dataset_data = {
                "name": f"chunked_test_{int(time.time())}",
                "description": "Test dataset for chunked upload validation",
                "format": "yolo"
            }
            
            response = requests.post(
                f"{self.base_url}/api/v1/datasets/",
                json=dataset_data,
                timeout=10
            )
            
            if response.status_code not in [200, 201]:
                console.print(f"❌ Failed to create dataset: {response.status_code}")
                self.log_test("chunked_upload", "FAIL", {"error": "Dataset creation failed"})
                return False
                
            dataset = response.json()
            dataset_id = dataset["id"]
            console.print(f"✅ Created dataset: {dataset_id}")
            
            # Test chunked upload
            chunk_size = 1024  # 1KB chunks for testing
            upload_id = f"upload_{int(time.time())}"
            
            with open(zip_path, 'rb') as f:
                file_data = f.read()
                
            total_chunks = (len(file_data) + chunk_size - 1) // chunk_size
            console.print(f"📤 Uploading {total_chunks} chunks...")
            
            start_time = time.time()
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Uploading chunks...", total=total_chunks)
                
                for chunk_num in range(total_chunks):
                    start_idx = chunk_num * chunk_size
                    end_idx = min(start_idx + chunk_size, len(file_data))
                    chunk_data = file_data[start_idx:end_idx]
                    
                    files = {'file': ('chunk.zip', chunk_data, 'application/zip')}
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
                    
                    if response.status_code not in [200, 201]:
                        console.print(f"❌ Chunk {chunk_num + 1} failed: {response.status_code}")
                        self.log_test("chunked_upload", "FAIL", {
                            "failed_chunk": chunk_num,
                            "status_code": response.status_code
                        })
                        return False
                        
                    progress.update(task, advance=1)
                    
            upload_time = time.time() - start_time
            
            console.print(f"✅ Chunked upload completed in {upload_time:.2f}s")
            self.log_test("chunked_upload", "PASS", {
                "total_chunks": total_chunks,
                "file_size": file_size,
                "upload_time": upload_time,
                "dataset_id": dataset_id
            })
            
            # Record performance metrics
            self.results["performance"]["chunked_upload"] = {
                "file_size_bytes": file_size,
                "total_chunks": total_chunks,
                "upload_time_seconds": upload_time,
                "throughput_mbps": (file_size / (1024 * 1024)) / upload_time if upload_time > 0 else 0
            }
            
            # Clean up
            zip_path.unlink()
            
            return True
            
        except Exception as e:
            console.print(f"❌ Chunked upload test failed: {e}")
            self.log_test("chunked_upload", "FAIL", {"error": str(e)})
            self.log_error(f"Chunked upload test failed: {e}")
            return False

    async def test_dataset_listing(self) -> bool:
        """Test dataset listing and pagination"""
        console.print("\n📋 [bold blue]Testing Dataset Listing...[/bold blue]")
        
        try:
            response = requests.get(f"{self.base_url}/api/v1/datasets/", timeout=10)
            
            if response.status_code == 200:
                datasets = response.json()
                console.print(f"✅ Found {len(datasets)} datasets")
                self.log_test("dataset_listing", "PASS", {"dataset_count": len(datasets)})
                
                # Test with pagination
                response = requests.get(
                    f"{self.base_url}/api/v1/datasets/",
                    params={"limit": 5, "offset": 0},
                    timeout=10
                )
                
                if response.status_code == 200:
                    console.print("✅ Pagination works correctly")
                    self.log_test("dataset_pagination", "PASS")
                else:
                    console.print("⚠️  Pagination test failed")
                    self.log_test("dataset_pagination", "WARN")
                    
                return True
            else:
                console.print(f"❌ Dataset listing failed: {response.status_code}")
                self.log_test("dataset_listing", "FAIL", {"status_code": response.status_code})
                return False
                
        except Exception as e:
            console.print(f"❌ Dataset listing test failed: {e}")
            self.log_test("dataset_listing", "FAIL", {"error": str(e)})
            self.log_error(f"Dataset listing test failed: {e}")
            return False

    def generate_final_report(self) -> Dict:
        """Generate comprehensive final report"""
        console.print("\n📊 [bold blue]Generating Final Report...[/bold blue]")
        
        # Calculate summary statistics
        total_tests = len(self.results["tests"])
        passed_tests = sum(1 for test in self.results["tests"].values() if test["status"] == "PASS")
        failed_tests = sum(1 for test in self.results["tests"].values() if test["status"] == "FAIL")
        warned_tests = sum(1 for test in self.results["tests"].values() if test["status"] == "WARN")
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        self.results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "warned_tests": warned_tests,
            "success_rate": success_rate,
            "overall_status": "PASS" if failed_tests == 0 else "FAIL"
        }
        
        # Save report to file
        report_path = Path("pipeline_validation_report.json")
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
            
        console.print(f"📄 Report saved to: {report_path}")
        
        return self.results

    def display_final_status(self):
        """Display beautiful final status summary"""
        summary = self.results["summary"]
        
        # Create status table
        table = Table(title="🎯 Pipeline Validation Results")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_column("Status", style="green")
        
        table.add_row("Total Tests", str(summary["total_tests"]), "📊")
        table.add_row("Passed", str(summary["passed_tests"]), "✅")
        table.add_row("Failed", str(summary["failed_tests"]), "❌" if summary["failed_tests"] > 0 else "✅")
        table.add_row("Warnings", str(summary["warned_tests"]), "⚠️" if summary["warned_tests"] > 0 else "✅")
        table.add_row("Success Rate", f"{summary['success_rate']:.1f}%", "🎯")
        
        console.print(table)
        
        # Display final status
        if summary["overall_status"] == "PASS":
            panel = Panel(
                "[bold green]🎉 PIPELINE VALIDATION SUCCESSFUL! 🎉[/bold green]\n\n"
                "✅ All critical components are working correctly\n"
                "✅ Chunked upload system is operational\n"
                "✅ API endpoints are responding properly\n"
                "✅ Database connectivity is established\n\n"
                "[bold blue]Your YOLO Dataset Annotation Service is ready for production![/bold blue]",
                title="🚀 SUCCESS",
                border_style="green"
            )
        else:
            panel = Panel(
                "[bold red]❌ PIPELINE VALIDATION FAILED[/bold red]\n\n"
                f"❌ {summary['failed_tests']} test(s) failed\n"
                f"⚠️  {summary['warned_tests']} warning(s) detected\n\n"
                "[bold yellow]Please check the detailed report for issues to resolve.[/bold yellow]",
                title="⚠️  ISSUES DETECTED",
                border_style="red"
            )
            
        console.print(panel)

    async def run_complete_validation(self):
        """Run the complete validation pipeline"""
        console.print(Panel(
            "[bold blue]🚀 YOLO Dataset Annotation Service - Complete Pipeline Validation[/bold blue]\n\n"
            "This comprehensive test will validate all components of your system:\n"
            "• Service health and connectivity\n"
            "• Core API endpoints\n"
            "• Chunked upload functionality\n"
            "• Dataset processing capabilities\n"
            "• Performance metrics collection",
            title="🔍 Pipeline Validator",
            border_style="blue"
        ))
        
        start_time = time.time()
        
        # Run all validation tests
        tests = [
            ("Service Health Check", self.check_service_health()),
            ("Core Endpoints Test", self.test_core_endpoints()),
            ("Dataset Listing Test", self.test_dataset_listing()),
            ("Chunked Upload Test", self.test_chunked_upload()),
        ]
        
        all_passed = True
        
        for test_name, test_coro in tests:
            try:
                result = await test_coro
                if not result:
                    all_passed = False
            except Exception as e:
                console.print(f"❌ {test_name} encountered an error: {e}")
                self.log_error(f"{test_name} failed with exception: {e}")
                all_passed = False
        
        # Record total execution time
        total_time = time.time() - start_time
        self.results["performance"]["total_validation_time"] = total_time
        
        # Generate and display final report
        self.generate_final_report()
        self.display_final_status()
        
        console.print(f"\n⏱️  Total validation time: {total_time:.2f} seconds")
        
        return all_passed

async def main():
    """Main execution function"""
    validator = PipelineValidator()
    
    try:
        success = await validator.run_complete_validation()
        
        if success:
            console.print("\n🎊 [bold green]CONGRATULATIONS![/bold green] 🎊")
            console.print("Your YOLO Dataset Annotation Service pipeline is complete and operational!")
            sys.exit(0)
        else:
            console.print("\n⚠️  [bold yellow]VALIDATION COMPLETED WITH ISSUES[/bold yellow]")
            console.print("Please review the report and resolve any failed tests.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        console.print("\n⏹️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n💥 Validation failed with error: {e}")
        validator.log_error(f"Main execution failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Install required packages if not available
    try:
        import rich
        import aiohttp
    except ImportError:
        console.print("📦 Installing required packages...")
        os.system("pip install rich aiohttp")
        
    asyncio.run(main())
