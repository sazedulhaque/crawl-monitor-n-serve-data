from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator

from apps.api.models import BookStatus, CrawlSessionStatus


class UserRegister(BaseModel):
    """Schema for user registration"""

    email: EmailStr = Field(..., unique=True)
    username: str = Field(..., index=True, min_length=3, max_length=50, unique=True)
    password: str = Field(..., min_length=6)
    full_name: str | None = None


class UserShortResponse(BaseModel):
    """Schema for user response"""

    id: str
    email: EmailStr
    full_name: str | None = None

    @field_validator("id", mode="before")
    @classmethod
    def convert_objectid_to_str(cls, value):
        """Convert ObjectId to string before validation"""
        return str(value) if value else None


class Token(BaseModel):
    """Schema for JWT token response"""

    access_token: str
    token_type: str = "bearer"


class BookBase(BaseModel):
    """Base schema for book"""

    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    category: str
    price: float = Field(..., gt=0)
    price_including_tax: float | None = Field(default=None, gt=0)
    price_excluding_tax: float | None = Field(default=None, gt=0)
    in_stock: bool = True
    reviews_count: int = Field(default=0, ge=0)
    rating: float = Field(default=0.0, ge=0, le=5)
    cover_image: HttpUrl | None = None
    remote_book_id: str | None = None
    source_url: HttpUrl | None = None


class BookCreate(BookBase):
    """Schema for creating a book"""

    pass


class BookUpdate(BaseModel):
    """Schema for updating a book"""

    title: str | None = Field(None, min_length=1, max_length=500)
    category: str | None = None
    description: str | None = None
    price: float | None = Field(None, gt=0)
    rating: float | None = Field(None, ge=0, le=5)
    reviews_count: int | None = Field(None, ge=0)
    cover_image: HttpUrl | None = None
    in_stock: bool | None = None


class BookShortResponse(BaseModel):
    """Schema for books Short data"""

    title: str | None = Field(None, min_length=1, max_length=500)
    category: str | None = None
    price: float | None = Field(None, gt=0)
    rating: float | None = Field(None, ge=0, le=5)
    reviews_count: int | None = Field(None, ge=0)
    in_stock: bool | None = None


class BookResponse(BookBase):
    """Schema for book response"""

    id: str
    user: UserShortResponse | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def convert_objectid_to_str(cls, value):
        """Convert ObjectId to string before validation"""

        return str(value) if value else None

    class Config:
        from_attributes = True


class ChangeLogResponse(BaseModel):
    """Schema for change log response"""

    id: str
    book: BookShortResponse | None = None
    book_title: str | None = None
    change_type: str
    field_changed: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    description: str | None = None

    @field_validator("id", mode="before")
    @classmethod
    def convert_objectid_to_str(cls, value):
        """Convert ObjectId to string before validation"""
        return str(value) if value else None

    class Config:
        from_attributes = True
