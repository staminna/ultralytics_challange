import os
from typing import Optional

import motor.motor_asyncio
from beanie import init_beanie

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
    """Initialize the database connection and Beanie ODM."""
    print("Connecting to MongoDB...")
    client = motor.motor_asyncio.AsyncIOMotorClient(settings.DATABASE_URL)
    await init_beanie(
        database=client[settings.MONGO_DB],
        document_models=[
            Dataset,
            Image,
            Label,
            ClassDefinition
        ]
    )
    print("Successfully connected to MongoDB and initialized Beanie.")


async def close_mongo_connection():
    """This function is kept for symmetry, but Beanie manages connections automatically."""
    # Motor's client doesn't have an explicit close method that needs to be called here.
    # Connection pooling is handled automatically.
    print("MongoDB connection does not require explicit closing.")


db_manager = DBManager()
