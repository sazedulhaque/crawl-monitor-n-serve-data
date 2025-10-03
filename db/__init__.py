from pymongo import AsyncMongoClient

from core.config import settings

# Global database client
client: AsyncMongoClient = None
database = None


async def init_db():
    """Initialize the database connection."""
    global client, database
    client = AsyncMongoClient(settings.MONGODB_URL)
    database = client[settings.DATABASE_NAME]
    print(f"Connected to MongoDB: {settings.DATABASE_NAME}")


async def close_db():
    """Close the database connection."""
    global client
    if client:
        client.close()
        print("Database connection closed")


def get_database():
    """Get the database instance."""
    return database


def get_client():
    """Get the MongoDB client instance."""
    return client
