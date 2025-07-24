#!/usr/bin/env python3
"""
YOLO11 Configuration - Centralized YOLO11 model settings
"""

from pathlib import Path
from typing import Dict, List

class YOLO11Config:
    """Centralized configuration for YOLO11 models and settings"""
    
    # YOLO11 Model Variants
    MODELS = {
        'nano': 'yolo11n.pt',
        'small': 'yolo11s.pt', 
        'medium': 'yolo11m.pt',
        'large': 'yolo11l.pt',
        'extra_large': 'yolo11x.pt'
    }
    
    # Segmentation Models
    SEGMENTATION_MODELS = {
        'nano': 'yolo11n-seg.pt',
        'small': 'yolo11s-seg.pt',
        'medium': 'yolo11m-seg.pt', 
        'large': 'yolo11l-seg.pt',
        'extra_large': 'yolo11x-seg.pt'
    }
    
    # Classification Models
    CLASSIFICATION_MODELS = {
        'nano': 'yolo11n-cls.pt',
        'small': 'yolo11s-cls.pt',
        'medium': 'yolo11m-cls.pt',
        'large': 'yolo11l-cls.pt',
        'extra_large': 'yolo11x-cls.pt'
    }
    
    # Pose Detection Models
    POSE_MODELS = {
        'nano': 'yolo11n-pose.pt',
        'small': 'yolo11s-pose.pt',
        'medium': 'yolo11m-pose.pt',
        'large': 'yolo11l-pose.pt',
        'extra_large': 'yolo11x-pose.pt'
    }
    
    # Default Settings
    DEFAULT_MODEL = MODELS['nano']  # yolo11n.pt
    DEFAULT_DETECTION_MODEL = MODELS['medium']  # yolo11m.pt for production
    DEFAULT_TRAINING_MODEL = MODELS['nano']  # yolo11n.pt for training/testing
    
    # Training Configuration
    TRAINING_DEFAULTS = {
        'epochs': 100,
        'imgsz': 640,
        'batch': 16,
        'lr0': 0.01,
        'patience': 50,
        'save_period': 10,
        'workers': 8,
        'device': 'auto'  # auto-detect GPU/CPU
    }
    
    # Inference Configuration
    INFERENCE_DEFAULTS = {
        'conf': 0.25,  # confidence threshold
        'iou': 0.45,   # IoU threshold for NMS
        'max_det': 1000,  # maximum detections per image
        'imgsz': 640,
        'device': 'auto'
    }
    
    @classmethod
    def get_model_path(cls, model_type: str = 'detection', size: str = 'nano') -> str:
        """Get the model path for a specific type and size"""
        model_maps = {
            'detection': cls.MODELS,
            'segmentation': cls.SEGMENTATION_MODELS,
            'classification': cls.CLASSIFICATION_MODELS,
            'pose': cls.POSE_MODELS
        }
        
        if model_type not in model_maps:
            raise ValueError(f"Unknown model type: {model_type}")
        
        if size not in model_maps[model_type]:
            raise ValueError(f"Unknown model size: {size}")
            
        return model_maps[model_type][size]
    
    @classmethod
    def get_training_command(cls, data_path: str, model_size: str = 'nano', **kwargs) -> List[str]:
        """Generate YOLO11 training command"""
        model = cls.MODELS[model_size]
        
        cmd = [
            'yolo', 'detect', 'train',
            f'data={data_path}',
            f'model={model}'
        ]
        
        # Add training defaults
        for key, value in cls.TRAINING_DEFAULTS.items():
            if key not in kwargs:
                kwargs[key] = value
        
        # Add custom parameters
        for key, value in kwargs.items():
            cmd.append(f'{key}={value}')
            
        return cmd
    
    @classmethod
    def get_validation_command(cls, data_path: str, model_size: str = 'nano', **kwargs) -> List[str]:
        """Generate YOLO11 validation command"""
        model = cls.MODELS[model_size]
        
        cmd = [
            'yolo', 'detect', 'val',
            f'data={data_path}',
            f'model={model}'
        ]
        
        # Add custom parameters
        for key, value in kwargs.items():
            cmd.append(f'{key}={value}')
            
        return cmd
    
    @classmethod
    def get_prediction_command(cls, source: str, model_size: str = 'nano', **kwargs) -> List[str]:
        """Generate YOLO11 prediction command"""
        model = cls.MODELS[model_size]
        
        cmd = [
            'yolo', 'detect', 'predict',
            f'source={source}',
            f'model={model}'
        ]
        
        # Add inference defaults
        for key, value in cls.INFERENCE_DEFAULTS.items():
            if key not in kwargs:
                kwargs[key] = value
        
        # Add custom parameters
        for key, value in kwargs.items():
            cmd.append(f'{key}={value}')
            
        return cmd

# Convenience functions
def get_default_model() -> str:
    """Get the default YOLO11 model"""
    return YOLO11Config.DEFAULT_MODEL

def get_production_model() -> str:
    """Get the recommended production YOLO11 model"""
    return YOLO11Config.DEFAULT_DETECTION_MODEL

def get_training_model() -> str:
    """Get the recommended training YOLO11 model"""
    return YOLO11Config.DEFAULT_TRAINING_MODEL

if __name__ == "__main__":
    # Demo usage
    config = YOLO11Config()
    
    print("🎯 YOLO11 Configuration")
    print("=" * 50)
    print(f"Default Model: {config.DEFAULT_MODEL}")
    print(f"Production Model: {config.DEFAULT_DETECTION_MODEL}")
    print(f"Training Model: {config.DEFAULT_TRAINING_MODEL}")
    
    print(f"\n📦 Available Models:")
    for size, model in config.MODELS.items():
        print(f"  {size:12}: {model}")
    
    print(f"\n🚀 Example Commands:")
    train_cmd = config.get_training_command("coco8.yaml", "nano", epochs=10)
    print(f"Training: {' '.join(train_cmd)}")
    
    val_cmd = config.get_validation_command("coco8.yaml", "nano")
    print(f"Validation: {' '.join(val_cmd)}")
    
    pred_cmd = config.get_prediction_command("image.jpg", "nano")
    print(f"Prediction: {' '.join(pred_cmd)}")
