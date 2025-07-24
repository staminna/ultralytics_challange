"""
Optimized dataset service methods to fix timeout issues during deletion.
These methods should replace the existing delete_image and delete_dataset methods.
"""

async def delete_image_optimized(self, image_id: str) -> bool:
    """Delete an image and all its labels using batch operations."""
    image_ref = self.db.collection(IMAGE_COLLECTION).document(image_id)
    image_doc = image_ref.get()
    
    if not image_doc.exists:
        return False
    
    image_data = image_doc.to_dict()
    
    # Delete from Cloud Storage (with better error handling)
    try:
        storage_path = image_data.get("storage_path")
        if storage_path:
            blob = self.bucket.blob(storage_path)
            if blob.exists():
                blob.delete()
    except Exception as e:
        # Only log actual errors, not 404s for missing files
        if "404" not in str(e) and "No such object" not in str(e):
            print(f"Warning: Could not delete image from storage: {e}")
    
    # Use batch operations for better performance
    batch = self.db.batch()
    
    # Delete all labels for this image
    labels_query = self.db.collection(LABEL_COLLECTION).where("image_id", "==", image_id)
    label_docs = labels_query.stream()
    
    for label_doc in label_docs:
        batch.delete(label_doc.reference)
    
    # Delete image document
    batch.delete(image_ref)
    
    # Commit batch operation
    try:
        batch.commit()
    except Exception as e:
        print(f"Warning: Batch delete failed for image {image_id}: {e}")
        return False
    
    return True

async def delete_dataset_optimized(self, dataset_id: str) -> bool:
    """Delete a dataset and all its images and labels using optimized batch operations."""
    dataset_ref = self.db.collection(DATASET_COLLECTION).document(dataset_id)
    dataset_doc = dataset_ref.get()
    
    if not dataset_doc.exists:
        return False
    
    try:
        # Get all images in the dataset
        images_query = self.db.collection(IMAGE_COLLECTION).where("dataset_id", "==", dataset_id)
        image_docs = list(images_query.stream())
        
        print(f"Deleting {len(image_docs)} images for dataset {dataset_id}")
        
        # Process images in smaller batches to avoid timeouts
        batch_size = 5  # Smaller batches to prevent timeouts
        for i in range(0, len(image_docs), batch_size):
            batch_images = image_docs[i:i + batch_size]
            
            # Create batch for Firestore operations
            batch = self.db.batch()
            
            for image_doc in batch_images:
                image_data = image_doc.to_dict()
                
                # Delete from Cloud Storage (silently handle missing files)
                try:
                    storage_path = image_data.get("storage_path")
                    if storage_path:
                        blob = self.bucket.blob(storage_path)
                        if blob.exists():
                            blob.delete()
                except Exception:
                    # Silently ignore storage deletion errors
                    pass
                
                # Get all labels for this image and add to batch
                labels_query = self.db.collection(LABEL_COLLECTION).where("image_id", "==", image_doc.id)
                label_docs = labels_query.stream()
                
                for label_doc in label_docs:
                    batch.delete(label_doc.reference)
                
                # Delete image document
                batch.delete(image_doc.reference)
            
            # Commit this batch
            try:
                batch.commit()
                print(f"Deleted batch {i//batch_size + 1}/{(len(image_docs) + batch_size - 1)//batch_size}")
            except Exception as e:
                print(f"Warning: Batch delete failed for images batch {i//batch_size + 1}: {e}")
        
        # Delete class definitions for this dataset
        classes_query = self.db.collection(CLASS_COLLECTION).where("dataset_id", "==", dataset_id)
        class_docs = list(classes_query.stream())
        
        if class_docs:
            batch = self.db.batch()
            for class_doc in class_docs:
                batch.delete(class_doc.reference)
            
            try:
                batch.commit()
                print(f"Deleted {len(class_docs)} class definitions")
            except Exception as e:
                print(f"Warning: Could not delete class definitions: {e}")
        
        # Delete dataset folder from Cloud Storage (silently handle missing folders)
        dataset_data = dataset_doc.to_dict()
        storage_path = dataset_data.get("storage_path", f"datasets/{dataset_id}")
        
        try:
            # List and delete all blobs in the dataset folder
            blobs = list(self.bucket.list_blobs(prefix=storage_path))
            print(f"Deleting {len(blobs)} storage objects")
            for blob in blobs:
                try:
                    blob.delete()
                except Exception:
                    # Silently ignore individual blob deletion errors
                    pass
        except Exception:
            # Silently ignore storage folder deletion errors
            pass
        
        # Delete dataset document
        dataset_ref.delete()
        print(f"Dataset {dataset_id} deleted successfully")
        
        return True
        
    except Exception as e:
        print(f"Error deleting dataset {dataset_id}: {e}")
        return False
