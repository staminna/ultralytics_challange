"""
Storage path utilities for consistent directory structure across local and cloud storage.
"""

from typing import Optional
from beanie import PydanticObjectId


class StoragePaths:
    """Utility class for generating consistent storage paths."""
    
    @staticmethod
    def dataset_base_path(dataset_id: PydanticObjectId) -> str:
        """Get the base storage path for a dataset."""
        return f"datasets/{dataset_id}"
    
    @staticmethod
    def dataset_images_path(dataset_id: PydanticObjectId) -> str:
        """Get the storage path for dataset images."""
        return f"datasets/{dataset_id}/images"
    
    @staticmethod
    def dataset_labels_path(dataset_id: PydanticObjectId) -> str:
        """Get the storage path for dataset labels."""
        return f"datasets/{dataset_id}/labels"
    
    @staticmethod
    def dataset_metadata_path(dataset_id: PydanticObjectId) -> str:
        """Get the storage path for dataset metadata files."""
        return f"datasets/{dataset_id}/metadata"
    
    @staticmethod
    def dataset_image_file_path(dataset_id: PydanticObjectId, image_filename: str) -> str:
        """Get the full storage path for a specific image file."""
        return f"datasets/{dataset_id}/images/{image_filename}"
    
    @staticmethod
    def dataset_label_file_path(dataset_id: PydanticObjectId, label_filename: str) -> str:
        """Get the full storage path for a specific label file."""
        return f"datasets/{dataset_id}/labels/{label_filename}"
    
    @staticmethod
    def model_weights_path(model_id: PydanticObjectId) -> str:
        """Get the storage path for model weights."""
        return f"models/{model_id}/weights"
    
    @staticmethod
    def model_config_path(model_id: PydanticObjectId) -> str:
        """Get the storage path for model configuration."""
        return f"models/{model_id}/config"
    
    @staticmethod
    def model_file_path(model_id: PydanticObjectId, filename: str) -> str:
        """Get the full storage path for a specific model file."""
        return f"models/{model_id}/{filename}"
    
    @staticmethod
    def training_output_path(training_id: PydanticObjectId) -> str:
        """Get the storage path for training outputs."""
        return f"outputs/training/{training_id}"
    
    @staticmethod
    def inference_output_path(inference_id: PydanticObjectId) -> str:
        """Get the storage path for inference outputs."""
        return f"outputs/inference/{inference_id}"
    
    @staticmethod
    def annotation_output_path(annotation_id: PydanticObjectId) -> str:
        """Get the storage path for annotation outputs."""
        return f"outputs/annotation/{annotation_id}"
    
    @staticmethod
    def temp_upload_path(upload_id: str) -> str:
        """Get the storage path for temporary uploads."""
        return f"temp/uploads/{upload_id}"
    
    @staticmethod
    def backup_path(backup_id: str) -> str:
        """Get the storage path for backups."""
        return f"backups/{backup_id}"


# Convenience functions for common operations
def get_dataset_storage_paths(dataset_id: PydanticObjectId) -> dict:
    """Get all storage paths for a dataset."""
    return {
        "images": StoragePaths.dataset_images_path(dataset_id),
        "labels": StoragePaths.dataset_labels_path(dataset_id),
        "metadata": StoragePaths.dataset_metadata_path(dataset_id)
    }


def get_model_storage_paths(model_id: PydanticObjectId) -> dict:
    """Get all storage paths for a model."""
    return {
        "weights": StoragePaths.model_weights_path(model_id),
        "config": StoragePaths.model_config_path(model_id)
    }


def get_output_storage_paths(output_id: PydanticObjectId, output_type: str = "training") -> dict:
    """Get storage paths for outputs."""
    if output_type == "training":
        base_path = StoragePaths.training_output_path(output_id)
    elif output_type == "inference":
        base_path = StoragePaths.inference_output_path(output_id)
    elif output_type == "annotation":
        base_path = StoragePaths.annotation_output_path(output_id)
    else:
        raise ValueError(f"Unknown output type: {output_type}")
    
    return {
        "base": base_path,
        "results": f"{base_path}/results",
        "logs": f"{base_path}/logs",
        "metrics": f"{base_path}/metrics"
    }
