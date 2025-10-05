from datetime import datetime, timezone
from enum import Enum
from typing import Any

from beanie import Document, Indexed, Link
from pwdlib import PasswordHash
from pydantic import EmailStr, Field, HttpUrl

password_hash = PasswordHash.recommended()


def utc_now():
    """Helper function to get current UTC time"""
    return datetime.now(timezone.utc)


class BookStatus(str, Enum):
    """Enum for book crawl status"""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class CrawlSessionStatus(str, Enum):
    """Enum for crawl session status"""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class BaseModel(Document):
    """Base model with common fields for all documents"""

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    class Settings:
        use_state_management = True

    async def save(self, *args, **kwargs):
        """Override save to update updated_at timestamp"""
        self.updated_at = datetime.now(timezone.utc)
        return await super().save(*args, **kwargs)


class User(BaseModel):
    """User model for authentication"""

    email: EmailStr = Indexed(str, unique=True)
    username: str = Indexed(str, unique=True, min_length=3, max_length=50)
    password: str
    full_name: str | None = None
    is_active: bool = True
    is_admin: bool = False

    class Settings:
        name = "users"
        validate_on_save = True
        indexes = [
            "email",
            "username",
        ]

    def verify_password(self, plain_password: str) -> bool:
        """Verify password against hashed password"""
        return password_hash.verify(plain_password, self.password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash password"""
        return password_hash.hash(password)

    def set_password(self, password: str) -> None:
        """Set and hash the password"""
        self.password = self.get_password_hash(password)

    async def save(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Saves the user to the database.

        Args:
            *args (Any): The arguments to pass to the save method.
            **kwargs (Any): The keyword arguments to pass to the save method.

        Returns:
            None
        """
        if kwargs.pop("hash_password", True) and self.password is not None:
            self.set_password(self.password)
        return await super().save(*args, **kwargs)


class Book(BaseModel):
    """Book model with relationships to User and Product"""

    title: str = Field(..., min_length=1, max_length=500, index=True)
    description: str | None = None
    category: str = Field(..., index=True)
    price: float = Field(..., gt=0)
    price_including_tax: float | None = Field(default=None, gt=0)
    price_excluding_tax: float | None = Field(default=None, gt=0)
    in_stock: bool = True
    reviews_count: int = Field(default=0, ge=0)
    rating: float = Field(default=0.0, ge=0, le=5)
    cover_image: HttpUrl | None = None
    user: Link[User] | None = None
    crawl_timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: BookStatus = Field(default=BookStatus.SUCCESS)  # Use enum
    html_snapshot: str = ""
    remote_book_id: str | None = Field(default=None, index=True)
    content_hash: str | None = Field(default=None, index=True)
    source_url: HttpUrl | None = None
    last_crawl_timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "books"
        indexes = [
            "category",
            "price",
            "rating",
            "remote_book_id",
            "content_hash",
            "source_url",
            "crawl_timestamp",
            [("title", 1), ("category", 1)],
            [("remote_book_id", 1), ("source_url", 1)],
        ]


class CrawlSession(BaseModel):
    """Track crawl sessions for monitoring and resumability"""

    session_id: str = Field(..., index=True)
    status: CrawlSessionStatus = Field(
        default=CrawlSessionStatus.RUNNING, index=True
    )  # Use enum
    started_by: Link[User] | None = None
    total_pages: int = 0
    processed_pages: int = 0
    new_books: int = 0
    updated_books: int = 0
    failed_books: int = 0
    last_processed_url: str | None = None
    error_message: str | None = None
    completed_at: datetime | None = None

    class Settings:
        name = "crawl_sessions"
        indexes = ["session_id", "status", "started_by", "created_at"]


class BookHistory(BaseModel):
    """Track changes to books"""

    book: Link[Book]
    change_type: str = Field(..., index=True)
    field_changed: str | None = None  # Which field changed
    old_value: Any | None = None
    new_value: Any | None = None
    changes: dict[str, Any] | None = None  # Full change dict
    description: str | None = None
    crawl_session_id: str | None = None

    class Settings:
        name = "book_history"
        indexes = ["book", "change_type", "created_at", "crawl_session_id"]
