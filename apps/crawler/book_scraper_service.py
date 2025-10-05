"""
Book scraping service with change detection and database operations
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone

from apps.api.models import (Book, BookHistory, CrawlSession,
                             CrawlSessionStatus, User)
from apps.crawler.crawler import BookScraper

# Configure logger for scraping service
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class BookScrapingService:
    """Service to orchestrate book scraping with change detection"""

    def __init__(self):
        self.scraper: BookScraper | None = None
        self.session_id: str | None = None
        self.crawl_session: CrawlSession | None = None

    async def start_scraping(
        self,
        user: User | None = None,
    ) -> dict[str, any]:
        """
        Start the complete scraping process
        Returns status information about the scraping session
        """
        try:
            self.session_id = str(uuid.uuid4())
            logger.info(
                f"Starting scraping session: {self.session_id} "
                f"(User: {user.username if user else 'Anonymous'})"
            )

            async with BookScraper() as scraper:
                self.scraper = scraper
                self.scraper.session_id = self.session_id

                # Get total pages first
                total_pages = await scraper.get_total_pages()
                logger.info(f"Discovered {total_pages} pages to process")

                # Start crawl session with total pages
                self.crawl_session = await scraper.start_crawl_session(
                    user, total_pages=total_pages
                )
                logger.info("Crawl session created in database")

                # Process all pages
                logger.info("Starting page processing...")
                results = await self._process_all_pages(total_pages)

                # Update final session status
                await scraper.update_crawl_session(
                    status="completed",
                    completed_at=datetime.now(timezone.utc),
                    processed_pages=total_pages,
                )

                logger.info(
                    f"Scraping completed successfully - "
                    f"New: {results['new_books']}, "
                    f"Updated: {results['updated_books']}, "
                    f"Failed: {results['failed_books']}"
                )

                return {
                    "session_id": self.session_id,
                    "status": CrawlSessionStatus.COMPLETED.value,
                    "message": "Scraping completed successfully",
                    "total_books_found": results["total_processed"],
                    "new_books_added": results["new_books"],
                    "books_updated": results["updated_books"],
                    "failed_operations": results["failed_books"],
                    "total_pages": total_pages,
                    "started_at": self.crawl_session.created_at,
                    "completed_at": datetime.now(timezone.utc),
                }

        except Exception as e:
            logger.error(
                f"Scraping session {self.session_id} failed: {str(e)}", exc_info=True
            )
            # Update session with error status
            if self.crawl_session:
                await self.scraper.update_crawl_session(
                    status=CrawlSessionStatus.FAILED,
                    error_message=str(e),
                    completed_at=datetime.now(timezone.utc),
                )

            return {
                "session_id": self.session_id,
                "status": CrawlSessionStatus.FAILED.value,
                "message": f"Scraping failed: {str(e)}",
                "total_books_found": 0,
                "new_books_added": 0,
                "books_updated": 0,
                "failed_operations": 0,
                "started_at": (
                    self.crawl_session.created_at if self.crawl_session else None
                ),
                "completed_at": datetime.now(timezone.utc),
            }

    async def _process_all_pages(self, total_pages: int) -> dict[str, int]:
        """Process all pages and return statistics"""
        results = {
            "total_processed": 0,
            "new_books": 0,
            "updated_books": 0,
            "failed_books": 0,
        }

        # Process pages concurrently (in batches to avoid overloading)
        batch_size = 3  # Process 3 pages concurrently

        for page_start in range(1, total_pages + 1, batch_size):
            """
            to covering the edge case we put this logic
            for confirm not to escap a single page
            """
            page_end = min(page_start + batch_size, total_pages + 1)
            page_range = list(range(page_start, page_end))

            # Process batch of pages
            tasks = [self._process_page(page_num) for page_num in page_range]
            page_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Aggregate results
            for page_result in page_results:
                if isinstance(page_result, Exception):
                    results["failed_books"] += 1
                    continue

                for key in results:
                    if key in page_result:
                        results[key] += page_result[key]

            # Update progress
            processed_pages = min(page_end - 1, total_pages)
            await self.scraper.update_crawl_session(
                processed_pages=processed_pages,
                new_books=results["new_books"],
                updated_books=results["updated_books"],
                failed_books=results["failed_books"],
            )

            # Small delay between batches to be respectful
            await asyncio.sleep(1)

        return results

    async def _process_page(self, page_num: int) -> dict[str, int]:
        """Process a single page with number of books and return statistics"""
        page_results = {
            "total_processed": 0,
            "new_books": 0,
            "updated_books": 0,
            "failed_books": 0,
        }

        try:
            # Get book URLs from page
            book_urls = await self.scraper.get_book_urls_from_page(page_num)

            if not book_urls:
                logger.warning(f"Page {page_num}: No book URLs found")
                return page_results

            # Process each book
            for book_url in book_urls:
                try:
                    book_result = await self._process_single_book(book_url)
                    page_results["total_processed"] += 1

                    if book_result == "new":
                        page_results["new_books"] += 1
                    elif book_result == "updated":
                        page_results["updated_books"] += 1

                except Exception:
                    page_results["failed_books"] += 1

                # Small delay between requests to be respectful
                await asyncio.sleep(1)

            return page_results

        except Exception as e:
            logger.error(
                f"Page {page_num}: Failed to process - {str(e)}", exc_info=True
            )
            # If entire page fails, mark all expected books as failed
            page_results["failed_books"] += 20  # Estimate books per page
            return page_results

    async def _process_single_book(self, book_url: str) -> str:
        """
        Process a single book URL
        Returns: 'new', 'updated', 'unchanged', or 'failed'
        """
        try:
            # Fetch and parse book data with rate limiting
            html, final_url = await self.scraper.get_page_with_retry(book_url)
            if not html:
                logger.warning(f"Failed to fetch HTML from {book_url}")
                return "failed"

            book_data = self.scraper.extract_book_data(html, final_url)

            if not book_data:
                logger.warning(f"Failed to extract book data from {book_url}")
                return "failed"

            # Check if book exists (by remote_book_id or content hash)
            existing_book = await self._find_existing_book(
                book_data["remote_book_id"], book_data["source_url"]
            )

            if existing_book:

                """
                Check if HTML snapshot is identical
                - if so, skip further processing
                """

                if existing_book.content_hash == book_data["content_hash"]:
                    # Update last crawl timestamp even though content is unchanged
                    existing_book.last_crawl_timestamp = datetime.now(timezone.utc)
                    await existing_book.save()
                    # logger.warning(
                    #     f"book of {existing_book.remote_book_id} remain same"
                    # )
                    return "unchanged"

                # Check for changes

                changes = await self._detect_changes(existing_book, book_data)
                if changes:
                    await self._update_existing_book(
                        existing_book,
                        book_data,
                        changes,
                    )
                    return "updated"
                else:
                    # Update last crawl timestamp even if no changes
                    existing_book.last_crawl_timestamp = datetime.now(timezone.utc)
                    existing_book.content_hash = book_data["content_hash"]
                    await existing_book.save()
                    return "unchanged"
            else:
                # Create new book
                await self._create_new_book(book_data)
                return "new"

        except Exception as e:
            logger.error(
                f"Failed to process book at {book_url}: {str(e)}", exc_info=True
            )
            return "failed"

    async def _find_existing_book(
        self, remote_book_id: str, source_url: str
    ) -> Book | None:
        """Find existing book by remote_book_id or source_url"""
        # Try to find by remote_book_id first
        if remote_book_id:
            existing = await Book.find_one(Book.remote_book_id == remote_book_id)
            if existing:
                return existing

        # Fallback to source_url
        if source_url:
            existing = await Book.find_one(Book.source_url == source_url)
            if existing:
                return existing

        return None

    async def _detect_changes(
        self, existing_book: Book, new_data: dict
    ) -> dict[str, dict[str, any]]:
        """
        Detect changes between existing book and new data
        Returns dict of {field_name: {old: value, new: value}}
        """
        changes = {}

        # Fields to monitor for changes
        monitored_fields = [
            "title",
            "description",
            "category",
            "price",
            "price_including_tax",
            "price_excluding_tax",
            "in_stock",
            "rating",
            "reviews_count",
            "cover_image",
        ]

        for field in monitored_fields:
            old_value = getattr(existing_book, field, None)
            new_value = new_data.get(field)

            # Handle different data types appropriately
            # For numeric fields, consider small differences as no change
            if (
                field
                in [
                    "price",
                    "price_including_tax",
                    "price_excluding_tax",
                    "rating",
                ]
                and old_value is not None
                and new_value is not None
                and abs(float(old_value) - float(new_value)) > 0.01
            ):
                changes[field] = {"old": old_value, "new": new_value}
            elif field == "in_stock" and bool(old_value) != bool(new_value):
                # Boolean field
                changes[field] = {"old": old_value, "new": new_value}
            elif (
                field
                not in [
                    "price",
                    "price_including_tax",
                    "price_excluding_tax",
                    "rating",
                    "in_stock",
                ]
                and str(old_value or "").strip() != str(new_value or "").strip()
            ):
                # String fields
                changes[field] = {"old": old_value, "new": new_value}
        logger.warning("Change:{changes}")
        return changes

    async def _update_existing_book(
        self, existing_book: Book, new_data: dict, changes: dict[str, dict[str, any]]
    ) -> None:
        """Update existing book with new data and log changes"""

        # Update the book fields
        for field, change_info in changes.items():
            setattr(existing_book, field, change_info["new"])

        # Update metadata fields
        existing_book.last_crawl_timestamp = datetime.now(timezone.utc)
        existing_book.content_hash = new_data["content_hash"]
        existing_book.html_snapshot = new_data["html_snapshot"]

        await existing_book.save()
        logger.warning(f"book of {existing_book.remote_book_id} changes:{changes}")
        # Log changes in history
        await self._log_book_changes(existing_book, changes)

    async def _create_new_book(self, book_data: dict) -> Book:
        """Create a new book record"""
        book = Book(**book_data)
        await book.insert()
        logger.debug(
            f"Created new book: {book_data['title']} "
            f"(ID: {book_data['remote_book_id']})"
        )
        return book

    async def _log_book_changes(
        self, book: Book, changes: dict[str, dict[str, any]]
    ) -> None:
        """Log book changes to history"""
        logger.warning(
            f"Logging {len(changes)} changes for book: {book.remote_book_id}"
        )
        logger.info(f"Book ID: {book.id}, Book type: {type(book)}")

        try:
            # Create a general update entry
            history_entry = BookHistory(
                book=book,
                change_type="updated",
                changes=changes,
                description=f"Updated {len(changes)} field(s) during crawl",
                crawl_session_id=self.session_id,
            )
            await history_entry.insert()
            logger.info(
                f"Successfully inserted general history entry "
                f"with ID: {history_entry.id}"
            )

            # Create specific entries for important changes
            important_changes = ["price", "in_stock", "price_including_tax"]
            for field, change_info in changes.items():
                if field in important_changes:
                    description = (
                        f"{field.replace('_', ' ').title()} changed from "
                        f"{change_info['old']} to {change_info['new']}"
                    )
                    specific_entry = BookHistory(
                        book=book,
                        change_type=f"{field}_changed",
                        field_changed=field,
                        old_value=change_info["old"],
                        new_value=change_info["new"],
                        description=description,
                        crawl_session_id=self.session_id,
                    )
                    await specific_entry.insert()
                    logger.info(
                        f"Successfully inserted {field}_changed history "
                        f"entry with ID: {specific_entry.id}"
                    )
        except Exception as e:
            logger.error(f"Error inserting BookHistory: {e}", exc_info=True)

    async def resume_failed_crawl(
        self, session_id: str, user: User | None = None
    ) -> dict[str, any]:
        """Resume a failed crawl session"""
        logger.info(f"Attempting to resume failed session: {session_id}")

        crawl_session = await CrawlSession.find_one(
            CrawlSession.session_id == session_id
        )

        if not crawl_session or crawl_session.status != CrawlSessionStatus.FAILED:
            logger.warning(
                f"Cannot resume session {session_id}: "
                f"Not found or not in failed state"
            )
            return {
                "session_id": session_id,
                "status": "error",
                "message": "Cannot resume: session not found or not in failed state",
            }

        # Update session status to running
        await crawl_session.update(
            {
                "$set": {
                    "status": CrawlSessionStatus.RUNNING.value,
                    "error_message": None,
                }
            }
        )
        logger.info(f"Resuming session {session_id} from failed state")

        # Continue processing from where it left off
        self.session_id = session_id
        self.crawl_session = crawl_session

        # Resume processing
        async with BookScraper() as scraper:
            self.scraper = scraper
            self.scraper.session_id = session_id

            remaining_pages = crawl_session.total_pages - crawl_session.processed_pages
            logger.info(
                f"Resuming from page {crawl_session.processed_pages + 1}, "
                f"{remaining_pages} pages remaining"
            )

            if remaining_pages > 0:
                # Process remaining pages
                results = await self._process_remaining_pages(
                    crawl_session.processed_pages + 1, crawl_session.total_pages
                )

                # Update final status
                await scraper.update_crawl_session(
                    status=CrawlSessionStatus.COMPLETED,
                    completed_at=datetime.now(timezone.utc),
                    processed_pages=crawl_session.total_pages,
                    new_books=crawl_session.new_books + results["new_books"],
                    updated_books=(
                        crawl_session.updated_books + results["updated_books"]
                    ),
                    failed_books=(crawl_session.failed_books + results["failed_books"]),
                )

                logger.info(
                    f"Resume completed for session {session_id} - "
                    f"New: {results['new_books']}, "
                    f"Updated: {results['updated_books']}, "
                    f"Failed: {results['failed_books']}"
                )

            return {
                "session_id": session_id,
                "status": CrawlSessionStatus.COMPLETED.value,
                "message": "Resume completed successfully",
            }

    async def _process_remaining_pages(
        self, start_page: int, end_page: int
    ) -> dict[str, int]:
        """Process pages from start_page to end_page"""
        logger.info(f"Processing remaining pages: {start_page} to {end_page}")
        results = {"new_books": 0, "updated_books": 0, "failed_books": 0}

        for page_num in range(start_page, end_page + 1):
            try:
                page_result = await self._process_page(page_num)
                for key in ["new_books", "updated_books", "failed_books"]:
                    results[key] += page_result.get(key, 0)

                await asyncio.sleep(1)  # Respectful delay

            except Exception as e:
                logger.error(
                    f"Failed to process page {page_num} during resume: " f"{str(e)}",
                    exc_info=True,
                )
                results["failed_books"] += 20  # Estimate

        logger.info(
            f"Finished processing remaining pages - "
            f"New: {results['new_books']}, "
            f"Updated: {results['updated_books']}, "
            f"Failed: {results['failed_books']}"
        )
        return results
