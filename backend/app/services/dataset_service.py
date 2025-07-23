from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status

from ..core.gcp import get_storage_bucket
from ..models.mongo_models import Dataset, Image, Label, ClassDefinition
from ..schemas.dataset_schema import DatasetCreate, ImageCreate, LabelCreate


class DatasetService:
    def __init__(self):
        self.bucket = get_storage_bucket()

    async def get_datasets(self, skip: int = 0, limit: int = 10) -> List[Dataset]:
        """Retrieve datasets with pagination."""
        return await Dataset.find_all().skip(skip).limit(limit).to_list()

    async def get_dataset(self, dataset_id: UUID) -> Optional[Dataset]:
        """Retrieve a single dataset by its ID."""
        return await Dataset.get(dataset_id, fetch_links=True)

    async def create_dataset(self, dataset_create: DatasetCreate) -> Dataset:
        """Create a new dataset."""
        # Check if a dataset with the same name already exists
        existing_dataset = await Dataset.find_one(Dataset.name == dataset_create.name)
        if existing_dataset:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Dataset with name '{dataset_create.name}' already exists."
            )

        new_dataset = Dataset(**dataset_create.dict())
        await new_dataset.insert()
        return new_dataset

    async def get_images_for_dataset(
        self, dataset_id: UUID, skip: int = 0, limit: int = 10
    ) -> List[Image]:
        """Retrieve images for a specific dataset."""
        dataset = await self.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found"
            )

        return await Image.find(Image.dataset_id == dataset_id).skip(skip).limit(limit).to_list()

    async def upload_image_to_dataset(
        self, dataset_id: UUID, file: ImageCreate
    ) -> Image:
        """Upload a single image to a dataset."""
        dataset = await self.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found"
            )

        new_image = Image(**file.dict(), dataset_id=dataset_id)
        await new_image.insert()
        return new_image

    async def get_image(self, image_id: UUID) -> Optional[Image]:
        """Retrieve an image by its ID."""
        return await Image.get(image_id)

    async def update_image(self, image_id: UUID, filename: str = None, width: int = None, height: int = None) -> Optional[Image]:
        """Update an image."""
        image = await self.get_image(image_id)
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found"
            )

        if filename:
            image.filename = filename
        if width:
            image.width = width
        if height:
            image.height = height

        await image.save()
        return image

    async def delete_image(self, image_id: UUID) -> None:
        """Delete an image."""
        image = await self.get_image(image_id)
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found"
            )

        await image.delete()

    async def delete_dataset(self, dataset_id: UUID) -> None:
        """Delete a dataset and its associated images and GCS files."""
        dataset = await self.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dataset not found"
            )

        # Delete associated images from GCS
        if dataset.images:
            for image_link in dataset.images:
                image = await Image.get(image_link.id)
                if image and image.gcs_path:
                    blob = self.bucket.blob(image.gcs_path)
                    if blob.exists():
                        blob.delete()

        # Delete dataset from MongoDB
        await dataset.delete()
        return

    async def create_label(self, image_id: UUID, label_create: LabelCreate) -> Label:
        """Create a label for an image."""
        image = await self.get_image(image_id)
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found"
            )

        new_label = Label(**label_create.dict(), image_id=image_id)
        await new_label.insert()
        return new_label

    async def get_label(self, label_id: UUID) -> Optional[Label]:
        """Retrieve a label by its ID."""
        return await Label.get(label_id)

    async def update_label(self, label_id: UUID, class_id: int = None, x_center: float = None, y_center: float = None, width: float = None, height: float = None) -> Optional[Label]:
        """Update a label."""
        label = await self.get_label(label_id)
        if not label:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Label not found"
            )

        if class_id:
            label.class_id = class_id
        if x_center:
            label.x_center = x_center
        if y_center:
            label.y_center = y_center
        if width:
            label.width = width
        if height:
            label.height = height

        await label.save()
        return label

    async def delete_label(self, label_id: UUID) -> None:
        """Delete a label."""
        label = await self.get_label(label_id)
        if not label:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Label not found"
            )

        await label.delete()


def get_dataset_service() -> DatasetService:
    return DatasetService()
