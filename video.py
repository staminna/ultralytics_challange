#!/usr/bin/env python3
"""
Script to create a YOLO dataset by extracting frames from videos.
This script will:
1. Process input videos to extract frames
2. Optionally apply data augmentation
3. Create proper YOLO directory structure
4. Generate metadata files (classes.txt, data.yaml)
"""

import argparse
import os
import random
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import yaml
from tqdm import tqdm


class VideoToYOLODataset:
    def __init__(self, 
                 video_paths,
                 output_dir="yolo_dataset",
                 frame_interval=10,  # Extract every Nth frame
                 target_size=(640, 640),
                 train_ratio=0.8,
                 augment_data=True,
                 max_frames_per_video=1000):
        """
        Initialize the dataset creator.
        
        Args:
            video_paths: List of video file paths or a directory containing videos
            output_dir: Output directory for the YOLO dataset
            frame_interval: Extract one frame every N frames
            target_size: Target size for resizing frames (width, height)
            train_ratio: Ratio of frames to use for training (rest for validation)
            augment_data: Whether to apply data augmentation
            max_frames_per_video: Maximum number of frames to extract per video
        """
        self.video_paths = self._get_video_paths(video_paths)
        self.output_dir = Path(output_dir)
        self.frame_interval = frame_interval
        self.target_size = target_size
        self.train_ratio = train_ratio
        self.augment_data = augment_data
        self.max_frames_per_video = max_frames_per_video
        
        # Create output directories
        self.images_dir = self.output_dir / "images"
        self.labels_dir = self.output_dir / "labels"
        self.train_dir = self.images_dir / "train"
        self.val_dir = self.images_dir / "val"
        self.train_labels_dir = self.labels_dir / "train"
        self.val_labels_dir = self.labels_dir / "val"
        
        # Example class names (customize as needed)
        self.class_names = ["person", "car", "bicycle", "dog", "cat"]
        
        self.setup_directories()
        
    def _get_video_paths(self, input_path):
        """Get list of video file paths from input path(s)."""
        if isinstance(input_path, (list, tuple)):
            return [str(p) for p in input_path]
            
        input_path = Path(input_path)
        if input_path.is_file():
            return [str(input_path)]
        elif input_path.is_dir():
            return [str(p) for p in input_path.glob("*") 
                   if p.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']]
        else:
            raise ValueError(f"Invalid input path: {input_path}")
    
    def setup_directories(self):
        """Create the necessary directory structure."""
        for d in [self.train_dir, self.val_dir, 
                 self.train_labels_dir, self.val_labels_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def process_videos(self):
        """Process all videos and extract frames."""
        print(f"Processing {len(self.video_paths)} videos...")
        
        for video_path in tqdm(self.video_paths, desc="Processing videos"):
            self._process_video(video_path)
        
        # Create metadata files
        self._create_metadata_files()
        
        print(f"\n✅ Dataset created at: {self.output_dir}")
        print(f"   - Training images: {len(list(self.train_dir.glob('*')))}")
        print(f"   - Validation images: {len(list(self.val_dir.glob('*')))}")
    
    def _process_video(self, video_path):
        """Extract frames from a single video."""
        video_path = Path(video_path)
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            print(f"⚠️  Could not open video: {video_path}")
            return
            
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        duration = total_frames / fps if fps > 0 else 0
        
        print(f"\nProcessing: {video_path.name}")
        print(f"  - Frames: {total_frames}")
        print(f"  - FPS: {fps:.1f}")
        print(f"  - Duration: {duration//60:.0f}m {duration%60:.1f}s")
        
        frame_count = 0
        saved_count = 0
        
        with tqdm(total=min(total_frames, self.max_frames_per_video), 
                 desc="Extracting frames", leave=False) as pbar:
            while frame_count < self.max_frames_per_video:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                # Skip frames based on interval
                if frame_count % self.frame_interval == 0:
                    # Determine if this is train or validation
                    is_train = random.random() < self.train_ratio
                    subset = "train" if is_train else "val"
                    
                    # Generate unique filename
                    frame_id = f"{video_path.stem}_{frame_count:06d}"
                    img_path = (self.train_dir if is_train else self.val_dir) / f"{frame_id}.jpg"
                    label_path = (self.train_labels_dir if is_train else self.val_labels_dir) / f"{frame_id}.txt"
                    
                    # Resize and save frame
                    frame = cv2.resize(frame, self.target_size)
                    cv2.imwrite(str(img_path), frame)
                    
                    # Here you would typically add code to generate labels
                    # For now, we'll create empty label files
                    with open(label_path, 'w') as f:
                        pass  # Empty label file
                    
                    saved_count += 1
                    pbar.update(1)
                    
                frame_count += 1
                
        cap.release()
        print(f"  - Saved {saved_count} frames")
    
    def _create_metadata_files(self):
        """Create YOLO metadata files (classes.txt and data.yaml)."""
        # Create classes.txt
        with open(self.output_dir / "classes.txt", 'w') as f:
            for class_name in self.class_names:
                f.write(f"{class_name}\n")
        
        # Create data.yaml
        data = {
            'path': str(self.output_dir.absolute()),
            'train': str(self.train_dir.relative_to(self.output_dir)),
            'val': str(self.val_dir.relative_to(self.output_dir)),
            'nc': len(self.class_names),
            'names': self.class_names
        }
        
        with open(self.output_dir / "data.yaml", 'w') as f:
            yaml.dump(data, f, sort_keys=False)

def main():
    parser = argparse.ArgumentParser(description="Create YOLO dataset from videos")
    parser.add_argument("input", help="Input video file or directory containing videos")
    parser.add_argument("-o", "--output", default="yolo_dataset", help="Output directory")
    parser.add_argument("--frame-interval", type=int, default=10, 
                       help="Extract one frame every N frames")
    parser.add_argument("--width", type=int, default=640, help="Target image width")
    parser.add_argument("--height", type=int, default=640, help="Target image height")
    parser.add_argument("--train-ratio", type=float, default=0.8, 
                       help="Ratio of frames for training (0-1)")
    parser.add_argument("--max-frames", type=int, default=1000,
                       help="Maximum frames to extract per video")
    
    args = parser.parse_args()
    
    # Create dataset
    dataset = VideoToYOLODataset(
        video_paths=args.input,
        output_dir=args.output,
        frame_interval=args.frame_interval,
        target_size=(args.width, args.height),
        train_ratio=args.train_ratio,
        max_frames_per_video=args.max_frames
    )
    
    dataset.process_videos()

if __name__ == "__main__":
    main()
