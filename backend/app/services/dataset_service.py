from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status

from ..core.gcp import get_storage_bucket
from ..models.mongo_models import Dataset as DatasetModel, Image, Label, ClassDefinition
from ..schemas.dataset import Dataset as DatasetSchema
from ..schemas.dataset_schema import DatasetCreate, ImageCreate, LabelCreate


class DatasetService:
    def __init__(self):
        self._bucket = None
    
    @property
    def bucket(self):
        """Lazy initialization of GCP storage bucket."""
        if self._bucket is None:
            self._bucket = get_storage_bucket()
        return self._bucket

    def _convert_to_schema(self, dataset_model: DatasetModel) -> DatasetSchema:
        """Convert MongoDB model to API schema."""
        return DatasetSchema(
            id=str(dataset_model.id),
            name=dataset_model.name,
            description=dataset_model.description,
            format=dataset_model.format,
            file_hash=dataset_model.file_hash,
            gcs_path=dataset_model.gcs_path,
            storage_path=dataset_model.storage_path,
            metadata=dataset_model.metadata,
            created_at=dataset_model.created_at,
            updated_at=dataset_model.updated_at,
            image_count=len(dataset_model.images) if dataset_model.images else 0
        )

    async def get_datasets(self, skip: int = 0, limit: int = 10) -> List[DatasetSchema]:
        """Retrieve datasets with pagination."""
        dataset_models = await DatasetModel.find_all().skip(skip).limit(limit).to_list()
        return [self._convert_to_schema(dataset) for dataset in dataset_models]

    async def get_dataset(self, dataset_id: UUID) -> Optional[DatasetSchema]:
        """Retrieve a single dataset by its ID."""
        dataset_model = await DatasetModel.get(dataset_id, fetch_links=True)
        return self._convert_to_schema(dataset_model) if dataset_model else None

    async def create_dataset(self, dataset_create: DatasetCreate) -> DatasetSchema:
        """Create a new dataset."""
        # Check if a dataset with the same name already exists
        existing_dataset = await DatasetModel.find_one(DatasetModel.name == dataset_create.name)
        if existing_dataset:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Dataset with name '{dataset_create.name}' already exists."
            )

        new_dataset = DatasetModel(**dataset_create.dict())
        await new_dataset.insert()
        return self._convert_to_schema(new_dataset)

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

        # Convert UUID to string for MongoDB query
        dataset_id_str = str(dataset_id)
        return await Image.find(Image.dataset_id == dataset_id_str).skip(skip).limit(limit).to_list()

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

    async def delete_dataset(self, dataset_id: str) -> bool:
        """Delete a dataset and its associated images and storage files."""
        try:
            from bson import ObjectId
            
            # Convert string to ObjectId
            if not ObjectId.is_valid(dataset_id):
                return False
                
            obj_id = ObjectId(dataset_id)
            
            # Find the dataset
            dataset_model = await DatasetModel.get(obj_id)
            if not dataset_model:
                return False

            # Delete associated images from storage if they exist
            if dataset_model.images:
                for image in dataset_model.images:
                    try:
                        # Delete from storage if GCS path exists
                        if hasattr(image, 'gcs_path') and image.gcs_path:
                            blob = self.bucket.blob(image.gcs_path)
                            if blob.exists():
                                blob.delete()
                        
                        # Delete from local storage if storage_path exists
                        if hasattr(image, 'storage_path') and image.storage_path:
                            import os
                            if os.path.exists(image.storage_path):
                                os.remove(image.storage_path)
                                
                    except Exception as e:
                        print(f"Warning: Failed to delete image storage for {image.id}: {e}")
                        # Continue with deletion even if storage cleanup fails

            # Delete the dataset from MongoDB
            await dataset_model.delete()
            return True
            
        except Exception as e:
            print(f"Error deleting dataset {dataset_id}: {e}")
            return False

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
