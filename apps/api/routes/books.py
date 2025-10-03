from beanie import PydanticObjectId
from beanie.operators import And
from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.models import Book, BookHistory, User
from apps.api.schemas import (BookCreate, BookListResponse, BookResponse,
                              BookUpdate, ChangeLogListResponse,
                              UserShortResponse)
from apps.utils.auth import get_current_active_user

router = APIRouter()


def convert_book_to_response(book: Book) -> dict:
    """Convert a Book model to response dict with proper user conversion"""
    book_dict = book.model_dump()
    book_dict["id"] = str(book.id)

    # Convert user to UserShortResponse if exists
    if book.user:
        book_dict["user"] = UserShortResponse(
            id=str(book.user.id),
            email=book.user.email,
            username=book.user.username,
            full_name=book.user.full_name,
        ).model_dump()
    else:
        book_dict["user"] = None

    return book_dict


@router.get("/", response_model=BookListResponse)
async def get_books(
    category: str | None = None,
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    rating: float | None = Query(None, ge=0, le=5),
    sort_by: str | None = Query(
        None, regex="^(rating|price|reviews_count|created_at)$"
    ),
    order: str = Query("desc", regex="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    """
    Get all books with optional filtering, sorting, and pagination.
    """
    # Build query filters
    query_filters = []

    if category:
        query_filters.append(Book.category == category)

    if min_price is not None:
        query_filters.append(Book.price >= min_price)

    if max_price is not None:
        query_filters.append(Book.price <= max_price)

    if rating is not None:
        query_filters.append(Book.rating >= rating)

    # Build query
    query = Book.find(And(*query_filters)) if query_filters else Book.find_all()
    # Apply sorting
    if sort_by:
        sort_field = getattr(Book, sort_by)
        query = query.sort(+sort_field) if order == "asc" else query.sort(-sort_field)
    # Get total count
    total = await query.count()

    # Apply pagination
    skip = (page - 1) * page_size
    books = await query.skip(skip).limit(page_size).to_list()

    # Fetch linked data
    for book in books:
        await book.fetch_all_links()

    # Convert books to response format
    book_responses = [convert_book_to_response(book) for book in books]

    total_pages = (total + page_size - 1) // page_size

    return BookListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=book_responses,
    )


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: PydanticObjectId):
    """Get a single book by ID"""
    book = await Book.get(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Fetch linked data
    await book.fetch_all_links()

    return convert_book_to_response(book)


@router.post("/", response_model=BookResponse, status_code=201)
async def create_book(
    book_data: BookCreate,
    current_user: User = Depends(get_current_active_user),
):
    """Create a new book (requires authentication)"""

    # Create book
    book = Book(
        **book_data.model_dump(),
        user=current_user,
    )
    await book.insert()

    # Create history entry
    history = BookHistory(
        book=book,
        changed_by=current_user,
        change_type="created",
        description="Book created",
    )
    await history.insert()

    # Fetch linked data for response
    await book.fetch_all_links()

    return convert_book_to_response(book)


@router.put("/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: PydanticObjectId,
    book_data: BookUpdate,
    current_user: User = Depends(get_current_active_user),
):
    """Update a book (requires authentication)"""
    book = await Book.get(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Get the update data
    update_data = book_data.model_dump(
        exclude_unset=True,
    )

    # Track changes for history
    changes = {}
    for field, new_value in update_data.items():
        old_value = getattr(book, field)
        if old_value != new_value:
            changes[field] = {"old": str(old_value), "new": str(new_value)}

            # Create individual history entry for each field
            change_dict = {
                field: {
                    "old": str(old_value),
                    "new": str(new_value),
                }
            }
            desc = f"{field} updated from {old_value} to {new_value}"
            history = BookHistory(
                book=book,
                changed_by=current_user,
                change_type="updated",
                field_name=field,
                old_value=str(old_value),
                new_value=str(new_value),
                changes=change_dict,
                description=desc,
            )
            await history.insert()

    # Update book fields
    for field, value in update_data.items():
        setattr(book, field, value)

    await book.save()

    # Fetch linked data for response
    await book.fetch_all_links()

    return convert_book_to_response(book)


@router.delete("/{book_id}")
async def delete_book(
    book_id: PydanticObjectId,
    current_user: User = Depends(get_current_active_user),
):
    """Delete a book (requires authentication)"""
    book = await Book.get(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Create history entry before deleting
    history = BookHistory(
        book=book,
        changed_by=current_user,
        change_type="deleted",
        description=f"Book '{book.title}' deleted",
    )
    await history.insert()

    await book.delete()

    return {"message": "Book deleted successfully"}


@router.get("/changes/recent", response_model=ChangeLogListResponse)
async def get_recent_changes(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    """Get recent changes to books"""
    query = BookHistory.find_all().sort(-BookHistory.created_at)

    # Get total count
    total = await query.count()

    # Apply pagination
    skip = (page - 1) * page_size
    changes = await query.skip(skip).limit(page_size).to_list()

    # Fetch linked data
    for change in changes:
        await change.fetch_all_links()

    total_pages = (total + page_size - 1) // page_size

    return ChangeLogListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        changes=changes,
    )
