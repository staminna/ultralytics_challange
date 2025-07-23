import subprocess
from pathlib import Path
from google.cloud import datastore
from datetime import datetime
from .config import Config
import yaml

class YOLODatasetManager:
    def __init__(self, config: Config):
        self.config = config
    
    def train(self, dataset_path: str, epochs: int, imgsz: int):
        """Train YOLO model on a dataset"""
        dataset_path = Path(dataset_path)
        config_path = dataset_path / "data.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"data.yaml not found in {dataset_path}")
        
        print(f"🚀 Starting training on dataset: {dataset_path.name}")
        
        cmd = [
            "yolo", "detect", "train",
            f"data={config_path}",
            f"model={self.config.DEFAULT_MODEL}",
            f"epochs={epochs}",
            f"imgsz={imgsz}",
            f"project={self.config.RUNS_DIR}",
            f"name={dataset_path.name}_train"
        ]
        
        try:
            subprocess.run(cmd, check=True)
            print("✅ Training completed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Training failed: {e}")
            return False
    
    def upload_to_gcp(self, dataset_path: str):
        """Upload dataset metadata to GCP Datastore"""
        dataset_path = Path(dataset_path)
        client = datastore.Client(project=self.config.GCP_PROJECT_ID)
        
        dataset_name = dataset_path.name
        key = client.key(self.config.GCP_DATASTORE_KIND, dataset_name)
        
        # Count images and labels
        image_count = len(list(dataset_path.rglob("images/**/*")))
        label_count = len(list(dataset_path.rglob("labels/**/*.txt")))
        
        # Create/update dataset entity
        dataset = datastore.Entity(key=key)
        dataset.update({
            "name": dataset_name,
            "path": str(dataset_path.absolute()),
            "images_count": image_count,
            "labels_count": label_count,
            "last_updated": datetime.utcnow().isoformat()
        })
        
        client.put(dataset)
        print(f"📤 Uploaded dataset to GCP: {dataset_name}")
    
    @staticmethod
    def validate_dataset_structure(dataset_path: Path) -> bool:
        """Validate YOLO dataset structure"""
        required_dirs = {"images", "labels"}
        required_files = {"data.yaml"}
        
        if not all((dataset_path / d).exists() for d in required_dirs):
            return False
        if not (dataset_path / "data.yaml").exists():
            return False
        return True
