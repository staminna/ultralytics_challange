#!/usr/bin/env python3
"""
Debug script to test the get_dataset method directly
"""
import asyncio
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.services.dataset_service import DatasetService
from backend.app.core.database import connect_to_mongo

async def test_get_dataset():
    """Test the get_dataset method directly"""
    
    # Connect to MongoDB
    await connect_to_mongo()
    
    # Create service instance
    service = DatasetService()
    
    # Test with the known dataset ID
    dataset_id = "6881f919d4243591062879e9"
    print(f"Testing get_dataset with ID: {dataset_id}")
    
    try:
        result = await service.get_dataset(dataset_id)
        print(f"Result: {result}")
        if result:
            print(f"Dataset found: {result.name}")
        else:
            print("Dataset not found (returned None)")
    except Exception as e:
        print(f"Exception occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_get_dataset())
