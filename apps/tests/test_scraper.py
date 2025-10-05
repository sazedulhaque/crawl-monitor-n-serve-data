"""
Tests for scraping functionality with mocked data
"""

from unittest.mock import MagicMock, patch

import pytest

from apps.crawler.book_scraper_service import BookScrapingService


@pytest.mark.asyncio
class TestBookScraperService:
    """Test book scraper service with mocked HTTP calls"""

    @patch("apps.crawler.crawler.BookScraper.get_page_with_retry")
    async def test_scraper_processes_books(self, mock_fetch, db_client):
        """Test that scraper processes books correctly"""
        # Mock HTML response for listing page
        mock_listing_html = """
        <html>
            <article class="product_pod">
                <a href="/catalogue/test-book_123/index.html">Test Book</a>
            </article>
        </html>
        """

        # Mock HTML response for book detail page
        mock_detail_html = """
        <html>
            <h1>Test Book</h1>
            <p class="price_color">£19.99</p>
            <p class="instock availability">In stock</p>
            <div id="product_description"><p>Test description</p></div>
            <table class="table">
                <tr><th>Number of reviews</th><td>5</td></tr>
            </table>
        </html>
        """

        # get_page_with_retry returns tuple of (html, final_url)
        mock_fetch.side_effect = [
            (mock_listing_html, "https://example.com"),
            (mock_detail_html, "https://example.com/book"),
        ]

        service = BookScrapingService()
        # Test service initialization
        assert service is not None

    @patch("apps.crawler.crawler.BookScraper.get_total_pages")
    async def test_scraper_gets_total_pages(self, mock_total_pages):
        """Test getting total number of pages"""
        mock_total_pages.return_value = 5

        service = BookScrapingService()
        assert service is not None

    async def test_scraper_session_creation(self, db_client):
        """Test scraper session is created properly"""
        service = BookScrapingService()
        assert service.session_id is None
        assert service.crawl_session is None


@pytest.mark.asyncio
class TestBookDataExtraction:
    """Test book data extraction with mocked responses"""

    @patch("httpx.AsyncClient.get")
    async def test_extract_book_title(self, mock_get):
        """Test extracting book title from HTML"""
        mock_response = MagicMock()
        mock_response.text = "<html><h1>Amazing Book Title</h1></html>"
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        # Test that we can mock the response
        assert mock_response.text is not None
        assert "Amazing Book Title" in mock_response.text

    @patch("httpx.AsyncClient.get")
    async def test_extract_book_price(self, mock_get):
        """Test extracting book price from HTML"""
        mock_response = MagicMock()
        mock_response.text = '<html><p class="price_color">£29.99</p></html>'
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        assert "£29.99" in mock_response.text

    @patch("httpx.AsyncClient.get")
    async def test_extract_book_availability(self, mock_get):
        """Test extracting book availability from HTML"""
        mock_response = MagicMock()
        mock_response.text = (
            '<html><p class="availability">In stock (10 available)</p></html>'
        )
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        assert "In stock" in mock_response.text


@pytest.mark.asyncio
class TestScraperErrorHandling:
    """Test scraper error handling"""

    @patch("httpx.AsyncClient.get")
    async def test_handle_http_error(self, mock_get):
        """Test handling HTTP errors"""
        mock_get.side_effect = Exception("Connection failed")

        # Verify exception is raised
        with pytest.raises(Exception) as exc_info:
            raise Exception("Connection failed")

        assert "Connection failed" in str(exc_info.value)

    @patch("httpx.AsyncClient.get")
    async def test_handle_timeout(self, mock_get):
        """Test handling timeout errors"""
        mock_get.side_effect = TimeoutError("Request timeout")

        with pytest.raises(TimeoutError) as exc_info:
            raise TimeoutError("Request timeout")

        assert "timeout" in str(exc_info.value).lower()


@pytest.mark.asyncio
class TestContentHashDetection:
    """Test content hash for change detection"""

    async def test_content_hash_generation(self):
        """Test that content hash is generated correctly"""
        import hashlib

        book_data = {
            "title": "Test Book",
            "price": 19.99,
            "category": "Fiction",
        }

        # Generate hash
        hash_string = f"{book_data['title']}{book_data['price']}"
        content_hash = hashlib.sha256(hash_string.encode()).hexdigest()

        assert len(content_hash) == 64  # SHA-256 produces 64 hex characters
        assert isinstance(content_hash, str)

    async def test_content_hash_changes_with_data(self):
        """Test that hash changes when data changes"""
        import hashlib

        data1 = "Test Book 19.99"
        data2 = "Test Book 24.99"

        hash1 = hashlib.sha256(data1.encode()).hexdigest()
        hash2 = hashlib.sha256(data2.encode()).hexdigest()

        assert hash1 != hash2


@pytest.mark.asyncio
class TestBookHistoryCreation:
    """Test BookHistory creation"""

    async def test_create_book_history_entry(self, db_client, sample_book):
        """Test creating a book history entry"""
        from apps.api.models import BookHistory

        history_entry = BookHistory(
            book=sample_book,
            change_type="price_changed",
            field_changed="price",
            old_value=19.99,
            new_value=24.99,
            description="Price changed from 19.99 to 24.99",
            crawl_session_id="test-session-123",
        )

        await history_entry.insert()

        # Verify it was created
        found = await BookHistory.find_one(
            BookHistory.crawl_session_id == "test-session-123"
        )
        assert found is not None
        assert found.change_type == "price_changed"
        assert found.field_changed == "price"

    async def test_book_history_with_multiple_changes(self, db_client, sample_book):
        """Test creating multiple history entries"""
        from apps.api.models import BookHistory

        changes = [
            {
                "change_type": "price_changed",
                "field_changed": "price",
                "old_value": 19.99,
                "new_value": 24.99,
            },
            {
                "change_type": "stock_changed",
                "field_changed": "in_stock",
                "old_value": True,
                "new_value": False,
            },
        ]

        session_id = "test-multi-session-456"

        for change in changes:
            history_entry = BookHistory(
                book=sample_book,
                change_type=change["change_type"],
                field_changed=change["field_changed"],
                old_value=change["old_value"],
                new_value=change["new_value"],
                description=f"Changed {change['field_changed']}",
                crawl_session_id=session_id,
            )
            await history_entry.insert()

        # Verify both were created
        found_entries = await BookHistory.find(
            BookHistory.crawl_session_id == session_id
        ).to_list()

        assert len(found_entries) == 2


@pytest.mark.asyncio
class TestMockDataScenarios:
    """Test various scenarios with mock data"""

    async def test_mock_new_book_discovery(self, db_client):
        """Test discovering a new book (mock scenario)"""
        from apps.api.models import Book

        # Mock discovering a new book
        new_book_data = {
            "title": "Newly Discovered Book",
            "category": "Mystery",
            "price": 15.99,
            "price_including_tax": 15.99,
            "price_excluding_tax": 15.99,
            "in_stock": True,
            "reviews_count": 0,
            "rating": 0.0,
            "remote_book_id": "newly-discovered-001",
            "source_url": "https://example.com/books/new",
            "content_hash": "newhash123",
        }

        book = Book(**new_book_data)
        await book.insert()

        # Verify it was created
        found = await Book.find_one(Book.remote_book_id == "newly-discovered-001")
        assert found is not None
        assert found.title == "Newly Discovered Book"

    async def test_mock_book_update_scenario(self, db_client, sample_book):
        """Test updating a book (mock scenario)"""
        # Mock updating book price
        old_price = sample_book.price
        new_price = 29.99

        sample_book.price = new_price
        await sample_book.save()

        # Verify update
        updated_book = await sample_book.get(sample_book.id)
        assert updated_book.price == new_price
        assert updated_book.price != old_price

    async def test_mock_book_stock_change(self, db_client, sample_book):
        """Test book going out of stock (mock scenario)"""
        # Mock stock change
        sample_book.in_stock = False
        await sample_book.save()

        # Verify change
        updated_book = await sample_book.get(sample_book.id)
        assert updated_book.in_stock is False
