"""
Pytest configuration and fixtures for testing
"""

import asyncio
from collections.abc import AsyncGenerator, Generator

import pytest
from beanie import init_beanie
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient
from pymongo import AsyncMongoClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from apps.api.models import Book, BookHistory, CrawlSession, User
from apps.api.routes import auth, books
from core.config import settings
from core.limiter import limiter


def create_test_app() -> FastAPI:
    """Create FastAPI app for testing without scheduler"""
    test_app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Test application",
        version=settings.VERSION,
    )

    test_app.state.limiter = limiter
    test_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS middleware
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    test_app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    test_app.include_router(books.router, prefix="/api/v1/books", tags=["Books"])

    @test_app.get("/")
    async def root():
        return {
            "application": "Test",
            "environment": "test",
            "version": settings.VERSION,
        }

    return test_app


@pytest.fixture(scope="function")
def event_loop() -> Generator:
    """Create an instance of the event loop for each test function."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="function", autouse=True)
async def db_client() -> AsyncGenerator:
    """Create test database connection and initialize Beanie"""
    # Use a separate test database
    test_db_name = f"{settings.DATABASE_NAME}_test"

    # Create fresh client for each test to avoid event loop issues
    client = AsyncMongoClient(
        settings.MONGODB_URL,
        serverSelectionTimeoutMS=5000,  # 5 second timeout
        connectTimeoutMS=5000,  # 5 second connection timeout
    )

    # Initialize Beanie with test database - this is crucial for FastAPI routes to work
    await init_beanie(
        database=client[test_db_name],
        document_models=[User, Book, BookHistory, CrawlSession],
    )

    yield client

    # Clean up: drop test database after tests
    try:
        await client.drop_database(test_db_name)
    except Exception:
        pass  # Ignore cleanup errors
    finally:
        try:
            await client.aclose()
        except Exception:
            pass  # Ignore close errors


@pytest.fixture(scope="function")
async def test_client(db_client) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client with database"""
    # Create a test-specific FastAPI app without scheduler
    test_app = create_test_app()

    async with AsyncClient(app=test_app, base_url="http://testserver") as client:
        yield client


@pytest.fixture
async def test_user(db_client):
    """Create a test user"""
    # Clean up any existing user first
    existing = await User.find_one(User.username == "testuser")
    if existing:
        await existing.delete()

    user = User(
        email="testuser@example.com",
        username="testuser",
        password="testpassword123",
        full_name="Test User",
    )
    await user.save(hash_password=True)
    yield user
    try:
        await user.delete()
    except Exception:
        pass


@pytest.fixture
async def admin_user(db_client):
    """Create an admin test user"""
    # Clean up any existing admin first
    existing = await User.find_one(User.username == "adminuser")
    if existing:
        await existing.delete()

    # Also check by email
    existing = await User.find_one(User.email == "admin@example.com")
    if existing:
        await existing.delete()

    user = User(
        email="admin@example.com",
        username="adminuser",
        password="adminpassword123",
        full_name="Admin User",
        is_admin=True,
    )
    await user.save(hash_password=True)

    # Verify the user was created and can be found
    found_user = await User.find_one(User.username == "adminuser")
    assert found_user is not None, "Admin user was not created properly"
    assert found_user.is_admin is True, "Admin user is_admin flag not set"

    yield user
    try:
        await user.delete()
    except Exception:
        pass


@pytest.fixture(scope="function")
async def auth_token(test_client: AsyncClient, test_user: User) -> str:
    """Get authentication token for test user"""
    response = await test_client.post(
        "/api/v1/auth/token",
        data={"username": "testuser", "password": "testpassword123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture(scope="function")
async def admin_token(test_client: AsyncClient, admin_user: User) -> str:
    """Get authentication token for admin user"""
    response = await test_client.post(
        "/api/v1/auth/token",
        data={
            "username": "adminuser",
            "password": "adminpassword123",
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture(scope="function")
async def sample_book(db_client, test_user: User) -> Book:
    """Create a sample book for testing"""
    book = Book(
        title="Test Book",
        description="A test book description",
        category="Fiction",
        price=19.99,
        price_including_tax=19.99,
        price_excluding_tax=19.99,
        in_stock=True,
        reviews_count=10,
        rating=4.5,
        cover_image="https://example.com/cover.jpg",
        remote_book_id="test-book-001",
        source_url="https://example.com/books/test-book",
        content_hash="abc123def456",
        user=test_user,
    )
    await book.insert()
    return book


@pytest.fixture(scope="function")
async def sample_books(db_client, test_user: User) -> list[Book]:
    """Create multiple sample books for testing"""
    books = [
        Book(
            title=f"Test Book {i}",
            description=f"Description for test book {i}",
            category="Fiction" if i % 2 == 0 else "Non-Fiction",
            price=10.0 + i,
            price_including_tax=10.0 + i,
            price_excluding_tax=10.0 + i,
            in_stock=True,
            reviews_count=i * 5,
            rating=3.0 + (i % 3),
            cover_image=f"https://example.com/cover{i}.jpg",
            remote_book_id=f"test-book-{i:03d}",
            source_url=f"https://example.com/books/test-book-{i}",
            content_hash=f"hash{i:03d}",
            user=test_user,
        )
        for i in range(1, 6)
    ]

    for book in books:
        await book.insert()

    return books
