from beanie import init_beanie
from pymongo import AsyncMongoClient

# Import all models here so Beanie can initialize them
from apps.api.models import Book, BookHistory, User
from core.config import settings


class Database:
    client: AsyncMongoClient | None = None

    @classmethod
    async def connect_db(cls):
        """Connect to MongoDB and initialize Beanie"""
        cls.client = AsyncMongoClient(settings.MONGODB_URL)
        await init_beanie(
            database=cls.client[settings.DATABASE_NAME],
            document_models=[User, Book, BookHistory],
        )

    @classmethod
    async def close_db(cls):
        """Close MongoDB connection"""
        if cls.client:
            cls.client.close()


db = Database()
