import os
from typing import Optional

import motor.motor_asyncio
from beanie import init_beanie
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from bson.codec_options import CodecOptions
from bson.binary import UuidRepresentation

from ..models.mongo_models import Dataset, Image, Label, ClassDefinition
from .config import settings


class DBManager:
    client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
    db_name: str = "yolo_datasets"

    async def connect_to_database(self):
        await connect_to_mongo()

    async def close_database_connection(self):
        await close_mongo_connection()


async def connect_to_mongo():
    """Initialize the database connection and Beanie ODM with proper UUID handling."""
    print("Connecting to MongoDB...")
    
    # Create client with proper UUID representation
    client = motor.motor_asyncio.AsyncIOMotorClient(
        settings.DATABASE_URL,
        uuidRepresentation='standard'
    )
    
    # Test connection
    try:
        await client.admin.command('ping')
        print("MongoDB connection successful")
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        raise
    
    # Get database with proper codec options for UUID handling
    database = client[settings.MONGO_DB]
    
    # Initialize Beanie with the configured database
    await init_beanie(
        database=database,
        document_models=[
            Dataset,
            Image,
            Label,
            ClassDefinition
        ]
    )
    print("Successfully connected to MongoDB and initialized Beanie with UUID support.")


async def close_mongo_connection():
    """This function is kept for symmetry, but Beanie manages connections automatically."""
    # Motor's client doesn't have an explicit close method that needs to be called here.
    # Connection pooling is handled automatically.
    print("MongoDB connection does not require explicit closing.")


db_manager = DBManager()
