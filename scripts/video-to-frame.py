#!/usr/bin/env python3
"""
Enhanced Video to YOLO Dataset Converter
- Handles filenames with spaces
- Processes more frames from videos
- Better progress tracking
"""

import argparse
import os
import random
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import cv2
import yaml
from tqdm import tqdm


class VideoToYOLODataset:
    def __init__(self, 
                 video_paths,
                 output_dir="yolo_dataset",
                 frame_interval=5,
                 target_size=(1280, 720),
                 train_ratio=0.8,
                 max_frames_per_video=2000,
                 min_confidence=0.7,
                 workers=4):
        """Initialize with proper path handling."""
        # Convert string input to list if needed
        if isinstance(video_paths, str):
            video_paths = [video_paths]
            
        self.video_paths = self._get_video_paths(video_paths)
        self.output_dir = Path(output_dir).resolve()
        self.frame_interval = frame_interval
        self.target_size = target_size
        self.train_ratio = train_ratio
        self.max_frames_per_video = max_frames_per_video
        self.min_confidence = min_confidence
        self.workers = workers
        
        # Create output directories
        self.images_dir = self.output_dir / "images"
        self.labels_dir = self.output_dir / "labels"
        self.train_dir = self.images_dir / "train"
        self.val_dir = self.images_dir / "val"
        self.train_labels_dir = self.labels_dir / "train"
        self.val_labels_dir = self.labels_dir / "val"
        
        # Example class names for wildlife
        self.class_names = [
            "elephant", "lion", "zebra", "giraffe", "cheetah",
            "hippopotamus", "rhinoceros", "crocodile", "antelope", "bird"
        ]
        
        self.setup_directories()
    
    def _get_video_paths(self, input_paths):
        """Get list of video file paths from input path(s)."""
        video_paths = []
        
        for path in input_paths:
            path = Path(path.strip('"\' '))  # Remove any surrounding quotes and spaces
            if path.is_file() and path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
                video_paths.append(str(path))
            elif path.is_dir():
                for ext in ['*.mp4', '*.avi', '*.mov', '*.mkv']:
                    video_paths.extend([str(p) for p in path.glob(ext)])
        
        if not video_paths:
            raise ValueError(f"No valid video files found in: {input_paths}")
            
        return video_paths
    
    def setup_directories(self):
        """Create the necessary directory structure."""
        for d in [self.train_dir, self.val_dir, 
                 self.train_labels_dir, self.val_labels_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def _process_video(self, video_path):
        """Process a single video file."""
        video_path = Path(video_path)
        if not video_path.exists():
            print(f"⚠️  File not found: {video_path}")
            return 0
            
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            print(f"⚠️  Could not open video: {video_path}")
            return 0
            
        try:
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / fps if fps > 0 else 0
            
            print(f"\nProcessing: {video_path.name}")
            print(f"  - Frames: {total_frames}")
            print(f"  - FPS: {fps:.1f}")
            print(f"  - Duration: {duration//60:.0f}m {duration%60:.1f}s")
            
            total_to_process = min(total_frames // self.frame_interval, 
                                 self.max_frames_per_video)
            if total_to_process == 0:
                total_to_process = 1
                
            saved_count = 0
            frame_count = 0
            
            with tqdm(total=total_to_process, desc="Extracting frames", leave=False) as pbar:
                while saved_count < total_to_process and frame_count < total_frames:
                    ret, frame = cap.read()
                    if not ret:
                        break
                        
                    if frame_count % self.frame_interval == 0:
                        if self._is_good_frame(frame):
                            is_train = random.random() < self.train_ratio
                            subset = "train" if is_train else "val"
                            
                            frame_id = f"{video_path.stem}_{frame_count:08d}"
                            img_path = (self.train_dir if is_train else self.val_dir) / f"{frame_id}.jpg"
                            
                            frame = cv2.resize(frame, self.target_size)
                            cv2.imwrite(str(img_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
                            
                            # Create empty label file
                            label_path = (self.train_labels_dir if is_train else self.val_labels_dir) / f"{frame_id}.txt"
                            with open(label_path, 'w'):
                                pass
                            
                            saved_count += 1
                            pbar.update(1)
                            
                    frame_count += 1
                    
            print(f"  - Saved {saved_count} frames")
            return saved_count
            
        except Exception as e:
            print(f"⚠️  Error processing {video_path.name}: {str(e)}")
            return 0
        finally:
            cap.release()
    
    def _is_good_frame(self, frame, threshold=100.0):
        """Check if frame has sufficient quality."""
        if frame is None:
            return False
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            fm = cv2.Laplacian(gray, cv2.CV_64F).var()
            return fm > threshold
        except:
            return False
    
    def process_videos_parallel(self):
        """Process multiple videos in parallel."""
        print(f"Processing {len(self.video_paths)} videos using {self.workers} workers...")
        total_frames = 0
        
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {executor.submit(self._process_video, vp): vp 
                     for vp in self.video_paths}
            
            for future in tqdm(as_completed(futures), total=len(futures), 
                            desc="Processing videos"):
                try:
                    frames_processed = future.result()
                    total_frames += frames_processed
                except Exception as e:
                    video_path = futures[future]
                    print(f"⚠️  Error processing {video_path}: {str(e)}")
        
        self._create_metadata_files()
        self._print_summary(total_frames)
    
    def process_videos(self):
        """Process videos sequentially (for debugging)."""
        print(f"Processing {len(self.video_paths)} videos...")
        total_frames = 0
        
        for video_path in tqdm(self.video_paths, desc="Processing videos"):
            frames_processed = self._process_video(video_path)
            total_frames += frames_processed
        
        self._create_metadata_files()
        self._print_summary(total_frames)
    
    def _create_metadata_files(self):
        """Create YOLO metadata files."""
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
    
    def _print_summary(self, total_frames):
        """Print dataset creation summary."""
        train_count = len(list(self.train_dir.glob('*.jpg')))
        val_count = len(list(self.val_dir.glob('*.jpg')))
        
        print(f"\n✅ Dataset created at: {self.output_dir}")
        print(f"   - Total images: {total_frames}")
        print(f"   - Training images: {train_count}")
        print(f"   - Validation images: {val_count}")
        print(f"   - Classes: {', '.join(self.class_names)}")

def main():
    parser = argparse.ArgumentParser(
        description="Create YOLO dataset from videos",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "input", 
        nargs='+',
        help="Input video file(s) or directory containing videos"
    )
    parser.add_argument(
        "-o", "--output", 
        default="yolo_dataset",
        help="Output directory"
    )
    parser.add_argument(
        "--frame-interval", 
        type=int, 
        default=5,
        help="Extract one frame every N frames"
    )
    parser.add_argument(
        "--width", 
        type=int, 
        default=1280, 
        help="Target image width"
    )
    parser.add_argument(
        "--height", 
        type=int, 
        default=720, 
        help="Target image height"
    )
    parser.add_argument(
        "--train-ratio", 
        type=float, 
        default=0.8,
        help="Ratio of frames for training (0-1)"
    )
    parser.add_argument(
        "--max-frames", 
        type=int, 
        default=2000,
        help="Maximum frames to extract per video"
    )
    parser.add_argument(
        "--workers", 
        type=int, 
        default=4,
        help="Number of parallel workers"
    )
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel processing (for debugging)"
    )
    
    args = parser.parse_args()
    
    try:
        # Create dataset
        dataset = VideoToYOLODataset(
            video_paths=args.input,
            output_dir=args.output,
            frame_interval=args.frame_interval,
            target_size=(args.width, args.height),
            train_ratio=args.train_ratio,
            max_frames_per_video=args.max_frames,
            workers=args.workers
        )
        
        # Process videos
        if len(dataset.video_paths) > 1 and not args.no_parallel:
            dataset.process_videos_parallel()
        else:
            dataset.process_videos()
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return 1
        
    return 0

if __name__ == "__main__":
    start_time = time.time()
    exit_code = main()
    print(f"\n⏱️  Total processing time: {time.time() - start_time:.1f} seconds")
    exit(exit_code)