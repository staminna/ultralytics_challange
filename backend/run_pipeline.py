#!/usr/bin/env python3
"""
YOLO Pipeline Runner - Generate labeled images on disk

This script runs the complete YOLO pipeline:
1. Load COCO datasets
2. Run YOLO inference on images
3. Generate labeled images with bounding boxes
4. Save results to disk with identification labels
"""
import os
import sys
import cv2
import numpy as np
from pathlib import Path
from ultralytics import YOLO
import yaml
import json
from datetime import datetime

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir))

class YOLOPipeline:
    def __init__(self):
        self.model = YOLO('yolo11n.pt')  # Load YOLOv11 nano model
        self.datasets_dir = backend_dir / "datasets"
        self.output_dir = backend_dir / "pipeline_output"
        self.output_dir.mkdir(exist_ok=True)
        
        # COCO class names
        self.class_names = [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
            'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat',
            'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'backpack',
            'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
            'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
            'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
            'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake',
            'chair', 'couch', 'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop',
            'mouse', 'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
            'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
        ]
    
    def load_dataset_config(self, dataset_name):
        """Load dataset configuration from YAML file."""
        yaml_path = self.datasets_dir / "raw" / f"{dataset_name}.yaml"
        if not yaml_path.exists():
            raise FileNotFoundError(f"Dataset config not found: {yaml_path}")
        
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    
    def get_image_paths(self, dataset_name):
        """Get all image paths from a dataset."""
        config = self.load_dataset_config(dataset_name)
        dataset_path = Path(config['path'])
        
        image_paths = []
        
        # Check train images
        if 'train' in config:
            train_path = dataset_path / config['train']
            if train_path.exists():
                image_paths.extend(list(train_path.glob("*.jpg")))
                image_paths.extend(list(train_path.glob("*.jpeg")))
                image_paths.extend(list(train_path.glob("*.png")))
        
        # Check val images
        if 'val' in config:
            val_path = dataset_path / config['val']
            if val_path.exists():
                image_paths.extend(list(val_path.glob("*.jpg")))
                image_paths.extend(list(val_path.glob("*.jpeg")))
                image_paths.extend(list(val_path.glob("*.png")))
        
        return image_paths
    
    def draw_predictions(self, image, results, image_name):
        """Draw bounding boxes and labels on image."""
        annotated_image = image.copy()
        detections_info = []
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    # Get box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = box.conf[0].cpu().numpy()
                    class_id = int(box.cls[0].cpu().numpy())
                    
                    # Get class name
                    class_name = self.class_names[class_id] if class_id < len(self.class_names) else f"class_{class_id}"
                    
                    # Draw bounding box
                    cv2.rectangle(annotated_image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    
                    # Draw label with confidence
                    label = f"{class_name}: {confidence:.2f}"
                    label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                    cv2.rectangle(annotated_image, (int(x1), int(y1) - label_size[1] - 10), 
                                (int(x1) + label_size[0], int(y1)), (0, 255, 0), -1)
                    cv2.putText(annotated_image, label, (int(x1), int(y1) - 5), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
                    
                    # Store detection info
                    detections_info.append({
                        "class_id": class_id,
                        "class_name": class_name,
                        "confidence": float(confidence),
                        "bbox": [float(x1), float(y1), float(x2), float(y2)]
                    })
        
        return annotated_image, detections_info
    
    def process_dataset(self, dataset_name):
        """Process a complete dataset."""
        print(f"\n🔄 Processing dataset: {dataset_name}")
        
        # Create output directory for this dataset
        dataset_output_dir = self.output_dir / dataset_name
        dataset_output_dir.mkdir(exist_ok=True)
        
        # Get image paths
        image_paths = self.get_image_paths(dataset_name)
        print(f"📁 Found {len(image_paths)} images")
        
        if not image_paths:
            print(f"⚠️  No images found in {dataset_name}")
            return
        
        results_summary = {
            "dataset": dataset_name,
            "processed_at": datetime.now().isoformat(),
            "total_images": len(image_paths),
            "images": []
        }
        
        for i, image_path in enumerate(image_paths):
            print(f"🖼️  Processing {i+1}/{len(image_paths)}: {image_path.name}")
            
            # Load image
            image = cv2.imread(str(image_path))
            if image is None:
                print(f"❌ Failed to load image: {image_path}")
                continue
            
            # Run YOLO inference
            results = self.model(image, conf=0.25, iou=0.45)
            
            # Draw predictions
            annotated_image, detections = self.draw_predictions(image, results, image_path.name)
            
            # Save annotated image
            output_image_path = dataset_output_dir / f"labeled_{image_path.name}"
            cv2.imwrite(str(output_image_path), annotated_image)
            
            # Save original image for comparison
            original_image_path = dataset_output_dir / f"original_{image_path.name}"
            cv2.imwrite(str(original_image_path), image)
            
            # Add to summary
            image_info = {
                "filename": image_path.name,
                "original_path": str(image_path),
                "labeled_path": str(output_image_path),
                "detections_count": len(detections),
                "detections": detections
            }
            results_summary["images"].append(image_info)
            
            print(f"   ✅ Found {len(detections)} objects: {[d['class_name'] for d in detections]}")
        
        # Save results summary
        summary_path = dataset_output_dir / "results_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(results_summary, f, indent=2)
        
        print(f"✅ Dataset {dataset_name} processed successfully!")
        print(f"📊 Results saved to: {dataset_output_dir}")
        print(f"📋 Summary saved to: {summary_path}")
        
        return results_summary
    
    def run_complete_pipeline(self):
        """Run the complete pipeline on all available datasets."""
        print("🚀 Starting YOLO Pipeline")
        print(f"📁 Output directory: {self.output_dir}")
        
        # Available datasets
        datasets = ["coco8", "coco128"]
        
        all_results = {}
        
        for dataset in datasets:
            try:
                results = self.process_dataset(dataset)
                all_results[dataset] = results
            except Exception as e:
                print(f"❌ Error processing {dataset}: {e}")
                continue
        
        # Create overall summary
        overall_summary = {
            "pipeline_run_at": datetime.now().isoformat(),
            "datasets_processed": list(all_results.keys()),
            "total_images": sum(r["total_images"] for r in all_results.values() if r),
            "results": all_results
        }
        
        summary_path = self.output_dir / "pipeline_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(overall_summary, f, indent=2)
        
        print(f"\n🎉 Pipeline completed successfully!")
        print(f"📊 Overall summary: {summary_path}")
        print(f"📁 All results in: {self.output_dir}")
        
        # Print summary
        print(f"\n📋 Summary:")
        for dataset, results in all_results.items():
            if results:
                total_detections = sum(len(img["detections"]) for img in results["images"])
                print(f"  {dataset}: {results['total_images']} images, {total_detections} detections")
        
        return all_results

def main():
    """Main function to run the pipeline."""
    print("YOLO Dataset Annotation Pipeline")
    print("=" * 50)
    
    try:
        pipeline = YOLOPipeline()
        results = pipeline.run_complete_pipeline()
        
        print(f"\n✅ Pipeline completed successfully!")
        print(f"🔍 Check the 'pipeline_output' directory for labeled images")
        
        return 0
    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())
