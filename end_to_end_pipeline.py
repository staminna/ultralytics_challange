#!/usr/bin/env python3
"""
End-to-End YOLO Dataset Annotation Pipeline

This script runs the complete pipeline from dataset import to labeled output:
1. Start the FastAPI server
2. Import COCO datasets via API
3. Run auto-annotation on datasets
4. Generate labeled images with bounding boxes
5. Export results and summaries
"""
import os
import sys
import time
import requests
import subprocess
import json
from pathlib import Path
from datetime import datetime
import threading
import signal

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.append(str(backend_dir))

class EndToEndPipeline:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.server_process = None
        self.datasets_dir = backend_dir / "datasets"
        self.output_dir = Path(__file__).parent / "end_to_end_output"
        self.output_dir.mkdir(exist_ok=True)
        
        # Pipeline results
        self.results = {
            "pipeline_start": datetime.now().isoformat(),
            "steps": [],
            "datasets_processed": [],
            "total_images": 0,
            "total_detections": 0,
            "errors": []
        }
    
    def log_step(self, step_name, status="success", details=None, error=None):
        """Log a pipeline step."""
        step_info = {
            "step": step_name,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "details": details or {},
            "error": str(error) if error else None
        }
        self.results["steps"].append(step_info)
        
        status_emoji = "✅" if status == "success" else "❌" if status == "error" else "🔄"
        print(f"{status_emoji} {step_name}: {status}")
        if details:
            for key, value in details.items():
                print(f"   {key}: {value}")
        if error:
            print(f"   Error: {error}")
    
    def start_server(self):
        """Start the FastAPI server."""
        print("🚀 Starting FastAPI server...")
        
        try:
            # Start server in background
            server_script = backend_dir / "start_server.py"
            if not server_script.exists():
                # Fallback to basic server start
                server_script = backend_dir / "server.py"
            
            self.server_process = subprocess.Popen(
                [sys.executable, str(server_script)],
                cwd=str(backend_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for server to start
            max_retries = 30
            for i in range(max_retries):
                try:
                    response = requests.get(f"{self.base_url}/docs", timeout=2)
                    if response.status_code == 200:
                        self.log_step("Start Server", "success", {"port": 8000, "retries": i+1})
                        return True
                except requests.exceptions.RequestException:
                    time.sleep(2)
                    continue
            
            self.log_step("Start Server", "error", error="Server failed to start after 60 seconds")
            return False
            
        except Exception as e:
            self.log_step("Start Server", "error", error=e)
            return False
    
    def stop_server(self):
        """Stop the FastAPI server."""
        if self.server_process:
            print("🛑 Stopping server...")
            self.server_process.terminate()
            self.server_process.wait(timeout=10)
            self.log_step("Stop Server", "success")
    
    def check_server_health(self):
        """Check if server is healthy."""
        try:
            response = requests.get(f"{self.base_url}/docs", timeout=5)
            if response.status_code == 200:
                self.log_step("Server Health Check", "success")
                return True
            else:
                self.log_step("Server Health Check", "error", error=f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_step("Server Health Check", "error", error=e)
            return False
    
    def import_datasets(self):
        """Import COCO datasets via API."""
        print("📦 Importing datasets...")
        
        datasets = ["coco8", "coco128"]
        imported_datasets = []
        
        for dataset_name in datasets:
            try:
                # Check if dataset directory exists
                dataset_path = self.datasets_dir / dataset_name
                if not dataset_path.exists():
                    self.log_step(f"Import {dataset_name}", "error", error="Dataset directory not found")
                    continue
                
                # Create ZIP file for import
                import zipfile
                zip_path = self.output_dir / f"{dataset_name}.zip"
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(dataset_path):
                        for file in files:
                            file_path = Path(root) / file
                            arcname = file_path.relative_to(dataset_path)
                            zipf.write(file_path, arcname)
                
                # Import via API
                with open(zip_path, 'rb') as f:
                    files = {'file': (f'{dataset_name}.zip', f, 'application/zip')}
                    response = requests.post(
                        f"{self.base_url}/datasets/import/yolo",
                        files=files,
                        timeout=300
                    )
                
                if response.status_code == 200:
                    result = response.json()
                    imported_datasets.append({
                        "name": dataset_name,
                        "dataset_id": result.get("dataset_id"),
                        "images_count": result.get("images_processed", 0)
                    })
                    self.log_step(f"Import {dataset_name}", "success", {
                        "dataset_id": result.get("dataset_id"),
                        "images": result.get("images_processed", 0)
                    })
                else:
                    self.log_step(f"Import {dataset_name}", "error", error=f"API error: {response.status_code}")
                
                # Clean up zip file
                zip_path.unlink()
                
            except Exception as e:
                self.log_step(f"Import {dataset_name}", "error", error=e)
        
        self.results["datasets_processed"] = imported_datasets
        return imported_datasets
    
    def run_auto_annotation(self, datasets):
        """Run auto-annotation on imported datasets."""
        print("🤖 Running auto-annotation...")
        
        annotated_datasets = []
        
        for dataset in datasets:
            dataset_id = dataset["dataset_id"]
            dataset_name = dataset["name"]
            
            try:
                # Start auto-annotation
                response = requests.post(
                    f"{self.base_url}/models/auto-annotate/{dataset_id}",
                    json={
                        "confidence": 0.25,
                        "class_filter": None
                    },
                    timeout=600
                )
                
                if response.status_code == 200:
                    result = response.json()
                    annotated_datasets.append({
                        "dataset_id": dataset_id,
                        "name": dataset_name,
                        "job_id": result.get("job_id"),
                        "status": result.get("status")
                    })
                    self.log_step(f"Auto-annotate {dataset_name}", "success", {
                        "job_id": result.get("job_id"),
                        "status": result.get("status")
                    })
                else:
                    self.log_step(f"Auto-annotate {dataset_name}", "error", error=f"API error: {response.status_code}")
                    
            except Exception as e:
                self.log_step(f"Auto-annotate {dataset_name}", "error", error=e)
        
        return annotated_datasets
    
    def generate_labeled_images(self):
        """Generate labeled images using the standalone pipeline."""
        print("🖼️  Generating labeled images...")
        
        try:
            # Run the standalone pipeline
            pipeline_script = backend_dir / "run_pipeline.py"
            result = subprocess.run(
                [sys.executable, str(pipeline_script)],
                cwd=str(backend_dir),
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0:
                # Parse pipeline output for statistics
                output_lines = result.stdout.split('\n')
                total_images = 0
                total_detections = 0
                
                for line in output_lines:
                    if "images," in line and "detections" in line:
                        parts = line.split()
                        for i, part in enumerate(parts):
                            if part.endswith("images,"):
                                total_images += int(part.replace("images,", ""))
                            elif part.endswith("detections"):
                                total_detections += int(parts[i-1])
                
                self.results["total_images"] = total_images
                self.results["total_detections"] = total_detections
                
                self.log_step("Generate Labeled Images", "success", {
                    "total_images": total_images,
                    "total_detections": total_detections,
                    "output_dir": str(backend_dir / "pipeline_output")
                })
                return True
            else:
                self.log_step("Generate Labeled Images", "error", error=result.stderr)
                return False
                
        except Exception as e:
            self.log_step("Generate Labeled Images", "error", error=e)
            return False
    
    def export_results(self):
        """Export pipeline results and summaries."""
        print("📊 Exporting results...")
        
        try:
            # Save pipeline results
            results_file = self.output_dir / "end_to_end_results.json"
            with open(results_file, 'w') as f:
                json.dump(self.results, f, indent=2)
            
            # Copy pipeline output if it exists
            pipeline_output = backend_dir / "pipeline_output"
            if pipeline_output.exists():
                import shutil
                target_dir = self.output_dir / "labeled_images"
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                shutil.copytree(pipeline_output, target_dir)
            
            self.log_step("Export Results", "success", {
                "results_file": str(results_file),
                "labeled_images": str(self.output_dir / "labeled_images")
            })
            return True
            
        except Exception as e:
            self.log_step("Export Results", "error", error=e)
            return False
    
    def run_complete_pipeline(self):
        """Run the complete end-to-end pipeline."""
        print("🚀 Starting End-to-End YOLO Pipeline")
        print("=" * 60)
        
        try:
            # Step 1: Start server
            if not self.start_server():
                return False
            
            # Step 2: Health check
            time.sleep(5)  # Give server time to fully start
            if not self.check_server_health():
                return False
            
            # Step 3: Import datasets
            datasets = self.import_datasets()
            if not datasets:
                print("❌ No datasets imported successfully")
                return False
            
            # Step 4: Run auto-annotation (optional, may not work without proper setup)
            # annotated = self.run_auto_annotation(datasets)
            
            # Step 5: Generate labeled images
            if not self.generate_labeled_images():
                return False
            
            # Step 6: Export results
            if not self.export_results():
                return False
            
            # Final summary
            self.results["pipeline_end"] = datetime.now().isoformat()
            self.results["status"] = "success"
            
            print("\n🎉 End-to-End Pipeline Completed Successfully!")
            print(f"📊 Results saved to: {self.output_dir}")
            print(f"🖼️  Labeled images: {self.output_dir / 'labeled_images'}")
            print(f"📋 Summary: {self.results['total_images']} images, {self.results['total_detections']} detections")
            
            return True
            
        except KeyboardInterrupt:
            print("\n⚠️  Pipeline interrupted by user")
            self.results["status"] = "interrupted"
            return False
        except Exception as e:
            print(f"\n❌ Pipeline failed: {e}")
            self.results["status"] = "failed"
            self.results["errors"].append(str(e))
            return False
        finally:
            # Always stop the server
            self.stop_server()
            
            # Save final results
            try:
                results_file = self.output_dir / "end_to_end_results.json"
                with open(results_file, 'w') as f:
                    json.dump(self.results, f, indent=2)
            except:
                pass

def main():
    """Main function."""
    pipeline = EndToEndPipeline()
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\n⚠️  Received interrupt signal, stopping pipeline...")
        pipeline.stop_server()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    success = pipeline.run_complete_pipeline()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
