from dataclasses import dataclass
import os
from pathlib import Path

@dataclass
class Config:
    # Project
    PROJECT_ROOT: Path = Path(__file__).parent.parent
    DATASETS_DIR: Path = PROJECT_ROOT / "datasets"
    RUNS_DIR: Path = PROJECT_ROOT / "runs"
    
    # GCP
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "your-project-id")
    GCP_DATASTORE_KIND: str = "YoloDataset"
    
    # Training defaults
    DEFAULT_MODEL: str = "yolov8n.pt"
    DEFAULT_EPOCHS: int = 100
    DEFAULT_IMG_SIZE: int = 640
    
    def __post_init__(self):
        # Create required directories
        self.DATASETS_DIR.mkdir(exist_ok=True)
        self.RUNS_DIR.mkdir(exist_ok=True)
