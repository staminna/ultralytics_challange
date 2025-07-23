import os
import zipfile
import tempfile
from pathlib import Path
from typing import List, Dict
from uuid import UUID

import yaml
from fastapi import UploadFile, HTTPException, status

from ..core.gcp import get_storage_bucket
from ..models.mongo_models import Dataset, Image, Label, ClassDefinition

class YoloImportService:
    def __init__(self):
        self.bucket = get_storage_bucket()

    async def import_yolo_dataset(self, file: UploadFile) -> Dataset:
        dataset_name = Path(file.filename).stem

        existing_dataset = await Dataset.find_one(Dataset.name == dataset_name)
        if existing_dataset:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Dataset '{dataset_name}' already exists."
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            zip_path = temp_path / file.filename
            with open(zip_path, "wb") as buffer:
                buffer.write(await file.read())

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_path)

            # Find the extracted directory
            extracted_dirs = [d for d in temp_path.iterdir() if d.is_dir()]
            if not extracted_dirs:
                raise HTTPException(status_code=400, detail="No directory found in ZIP file.")
            dataset_dir = extracted_dirs[0]

            # Create dataset in DB
            new_dataset = Dataset(name=dataset_name)
            await new_dataset.insert()

            await self._process_yolo_files(dataset_dir, new_dataset)

            return new_dataset

    async def _process_yolo_files(self, dataset_path: Path, dataset: Dataset):
        images_path = dataset_path / 'images'
        labels_path = dataset_path / 'labels'

        class_names = []
        if (dataset_path / 'classes.txt').exists():
            with open(dataset_path / 'classes.txt', 'r') as f:
                class_names = [line.strip() for line in f.readlines()]

        class_map = {}
        for name in class_names:
            class_def = ClassDefinition(name=name, dataset_id=dataset.id)
            await class_def.insert()
            class_map[name] = class_def

        for image_file in images_path.rglob('*.*'):
            if not image_file.is_file():
                continue

            gcs_path = f"datasets/{dataset.id}/images/{image_file.name}"
            blob = self.bucket.blob(gcs_path)
            blob.upload_from_filename(str(image_file))

            new_image = Image(
                dataset_id=dataset.id,
                file_name=image_file.name,
                gcs_path=gcs_path,
                width=0, # Placeholder, should be updated
                height=0 # Placeholder, should be updated
            )
            await new_image.insert()
            dataset.images.append(new_image)

            label_file = labels_path / (image_file.stem + '.txt')
            if label_file.exists():
                with open(label_file, 'r') as f:
                    for line in f.readlines():
                        parts = line.strip().split()
                        class_idx, x_center, y_center, width, height = parts
                        class_name = class_names[int(class_idx)]
                        class_def = class_map[class_name]

                        new_label = Label(
                            class_id=class_def.id,
                            x_center=float(x_center),
                            y_center=float(y_center),
                            width=float(width),
                            height=float(height)
                        )
                        await new_label.insert()
                        new_image.labels.append(new_label)
                await new_image.save()

        await dataset.save()

def get_yolo_import_service() -> YoloImportService:
    return YoloImportService()
