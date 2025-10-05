from beanie import PydanticObjectId
from beanie.operators import And
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi_pagination import Page, Params
from fastapi_pagination.ext.beanie import apaginate

from apps.api.models import Book, BookHistory, CrawlSession, User
from apps.api.schemas import BookCreate, BookResponse, BookUpdate, UserShortResponse
from apps.utils.auth import get_current_active_user
from core.limiter import limiter

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


@router.get("/", response_model=Page[BookResponse])
@limiter.limit("100/hour")
async def get_books(
    request: Request,
    params: Params = Depends(),
    category: str | None = None,
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    rating: float | None = Query(None, ge=0, le=5),
    sort_by: str | None = Query(
        None, regex="^(rating|price|reviews_count|created_at)$"
    ),
    order: str = Query("desc", regex="^(asc|desc)$"),
):
    """
    Get all books with optional filtering, sorting and pagination.
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
    sort = None
    if sort_by:
        sort = [(sort_by, 1 if order == "asc" else -1)]

    return await apaginate(
        query,
        params,
        sort=sort,
        fetch_links=True,
        transformer=lambda items: [convert_book_to_response(book) for book in items],
    )


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(request: Request, book_id: PydanticObjectId):
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
                change_type="updated",
                field_changed=field,
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
        change_type="deleted",
        description=f"Book '{book.title}' deleted",
    )
    await history.insert()

    await book.delete()

    return {"message": "Book deleted successfully"}


@router.get(
    "/changes/recent",
    response_model=Page[BookHistory],
    response_model_exclude={"created_at", "updated_at", "id", "book"},
)
@limiter.limit("100/hour")
async def get_recent_changes(
    request: Request,
    params: Params = Depends(),
):
    """Get recent changes to books"""
    query = BookHistory.find_all()

    return await apaginate(query)


@router.get("/session/data", response_model=Page[CrawlSession])
@limiter.limit("100/hour")
async def get_session_datas(
    request: Request,
    params: Params = Depends(),
):
    """Get recent changes to books"""
    query = CrawlSession.find_all()

    return await apaginate(query)
