import asyncio
import hashlib
import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from apps.api.models import BookStatus, CrawlSession, CrawlSessionStatus, User


class BookScraper:
    """Async scraper for books.toscrape.com with error handling"""

    def __init__(self, base_url: str = "https://books.toscrape.com"):
        self.base_url = base_url
        self.session_id = str(uuid.uuid4())
        self.crawl_session: CrawlSession | None = None

        # HTTP client configuration
        self.client_config = {
            # Don't wait forever - timeout after 30 seconds
            "timeout": httpx.Timeout(30.0),
            "limits": httpx.Limits(
                max_connections=10,  # Max 10 requests at once
                max_keepalive_connections=5,  # Reuse 5 connections
            ),
            "headers": {"User-Agent": "Mozilla/5.0 (compatible; BookScraper/1.0)"},
        }

    async def __aenter__(self):
        self.client = httpx.AsyncClient(**self.client_config)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def start_crawl_session(
        self,
        user: User | None = None,
        total_pages: int = 0,
    ) -> CrawlSession:
        """Initialize a new crawl session"""
        self.crawl_session = CrawlSession(
            session_id=self.session_id,
            status=CrawlSessionStatus.RUNNING,
            started_by=user,
            total_pages=total_pages,
            processed_pages=0,
            new_books=0,
            updated_books=0,
            failed_books=0,
        )
        await self.crawl_session.insert()
        return self.crawl_session

    async def update_crawl_session(self, **kwargs):
        """Update crawl session status"""
        if self.crawl_session:
            for key, value in kwargs.items():
                setattr(self.crawl_session, key, value)
            await self.crawl_session.save()

    async def get_page_with_retry(
        self, url: str, max_retries: int = 3, backoff_factor: float = 1.0
    ) -> tuple[str, str] | None:
        """
        Fetch a page with exponential backoff retry logic
        Returns tuple of (html_content, final_url) or None if failed
        """
        for attempt in range(max_retries + 1):
            try:
                response = await self.client.get(url, follow_redirects=True)
                response.raise_for_status()
                return response.text, str(response.url)

            except httpx.TimeoutException:
                if attempt < max_retries:
                    wait_time = backoff_factor * (2**attempt)
                    await asyncio.sleep(wait_time)
                    continue
                return None

            except httpx.HTTPStatusError as e:
                # Retry on server errors
                if (
                    e.response.status_code in [429, 503, 502, 504]
                    and attempt < max_retries
                ):
                    wait_time = backoff_factor * (2**attempt)
                    await asyncio.sleep(wait_time)
                    continue
                return None

            except Exception:
                if attempt < max_retries:
                    wait_time = backoff_factor * (2**attempt)
                    await asyncio.sleep(wait_time)
                    continue
                return None

        return None

    def generate_content_hash(self, book_data: dict) -> str:
        """Generate hash for content deduplication"""
        # Create hash from key fields that indicate content changes
        hash_fields = [
            book_data.get("title", ""),
            book_data.get("price", ""),
            book_data.get("in_stock", ""),
            book_data.get("description", "")[:100],  # First 100 chars
        ]
        content = "|".join(str(field) for field in hash_fields)
        return hashlib.md5(content.encode()).hexdigest()

    def extract_book_data(
        self,
        html: str,
        page_url: str,
    ) -> dict | None:
        """
        Extract book data from HTML content and return a structured dictionary.

        This method parses the HTML content of a book page and extracts various pieces of
        information including title, description, price, stock status, rating, and other metadata.

        Args:
            html (str): The HTML content of the book page to parse.
            page_url (str): The URL of the page being parsed, used for resolving relative URLs
                            and generating remote book IDs.

        Returns:
            Optional[dict]: A dictionary containing the extracted book data with the following keys:
                - title (str): The book's title
                - description (str): Book description from meta tag or product description section
                - category (str): Book category from breadcrumb navigation
                - price (float): Base price of the book
                - price_including_tax (float): Price including tax
                - price_excluding_tax (float): Price excluding tax
                - in_stock (bool): Whether the book is in stock
                - reviews_count (int): Number of reviews (currently always 0)
                - rating (float): Star rating (0-5)
                - cover_image (str): URL of the book's cover image
                - source_url (str): Original page URL
                - remote_book_id (str): Unique identifier generated from URL or title
                - crawl_timestamp (datetime): Timestamp when the data was crawled
                - last_crawl_timestamp (datetime): Last crawl timestamp
                - status (str): Status of the extraction ("success")
                - html_snapshot (str): Original HTML content
                - content_hash (str): Hash of the book content for change detection

                Returns None if extraction fails due to any exception.

        """
        try:
            soup = BeautifulSoup(html, "lxml")

            # Extract title
            title_elem = (
                soup.find("div", class_="product_main").find("h1")
                if soup.find("div", class_="product_main")
                else soup.find("h1")
            )
            title = title_elem.get_text(strip=True) if title_elem else "Unknown Title"

            # Extract description
            desc_elem = soup.find("meta", {"name": "description"})
            description = desc_elem.get("content", "").strip() if desc_elem else None
            if not description:
                # Try alternative description location
                desc_elem = soup.find("div", {"id": "product_description"})
                if desc_elem and desc_elem.find_next_sibling("p"):
                    sibling = desc_elem.find_next_sibling("p")
                    description = sibling.get_text(strip=True)

            # Extract category (breadcrumb)
            category = "General"
            breadcrumb = soup.find("ul", class_="breadcrumb")
            if breadcrumb:
                category_link = breadcrumb.find_all("a")
                if len(category_link) >= 2:  # Skip "Home"
                    category = category_link[-1].get_text(strip=True)

            # Extract price information
            price_elem = soup.find("p", class_="price_color")
            price = 0.0
            price_including_tax = None
            price_excluding_tax = None

            # Initialize reviews_count
            reviews_count = 0

            if price_elem:
                price_text = price_elem.get_text(strip=True)
                # Extract numeric price (remove currency symbols)
                if price_match := re.search(r"[\d.]+", price_text):
                    price = float(price_match.group())

            # Try to get tax information from product table
            product_table = soup.find("table", class_="table-striped")
            if product_table:
                for row in product_table.find_all("tr"):
                    header = row.find("th")
                    data = row.find("td")
                    if header and data:
                        header_text = header.get_text(strip=True)
                        data_text = data.get_text(strip=True)

                        if "Price (incl. tax)" in header_text:
                            if tax_match := re.search(r"[\d.]+", data_text):
                                price_including_tax = float(tax_match.group())
                        elif "Price (excl. tax)" in header_text:
                            if tax_match := re.search(r"[\d.]+", data_text):
                                price_excluding_tax = float(tax_match.group())
                        elif "Number of reviews" in header_text:
                            if review_match := re.search(r"\d+", data_text):
                                reviews_count = int(review_match.group())

            # Extract stock information
            in_stock = False
            stock_elem = soup.find("p", class_="instock availability")
            if stock_elem:
                stock_text = stock_elem.get_text(strip=True).lower()
                in_stock = "in stock" in stock_text

            # Extract rating
            rating = 0.0
            rating_elem = soup.find("p", class_=lambda x: x and "star-rating" in x)
            if rating_elem:
                rating_classes = rating_elem.get("class", [])
                rating_words = ["Zero", "One", "Two", "Three", "Four", "Five"]
                for class_name in rating_classes:
                    if class_name in rating_words:
                        rating = float(rating_words.index(class_name))
                        break

            # Extract cover image
            cover_image = None
            active_div = soup.find("div", class_="item active")
            img_elem = active_div.find("img") if active_div else None
            if img_elem:
                if img_src := img_elem.get("src"):
                    cover_image = urljoin(page_url, img_src)

            book_data = {
                "title": title,
                "description": description,
                "category": category,
                "price": price,
                "price_including_tax": price_including_tax,
                "price_excluding_tax": price_excluding_tax,
                "in_stock": in_stock,
                "reviews_count": reviews_count,
                "cover_image": cover_image,
                "rating": rating,
            }

            # Generate content hash
            book_data["content_hash"] = self.generate_content_hash(book_data)

            # Generate remote_book_id from URL
            remote_book_id = None
            url_parts = urlparse(page_url)
            path_parts = url_parts.path.split("/")
            for part in path_parts:
                part_index = path_parts.index(part)
                has_next = len(path_parts) > part_index + 1
                if part.startswith("catalogue") and has_next:
                    next_part = path_parts[path_parts.index(part) + 1]
                    if next_part and not next_part.startswith("index"):
                        remote_book_id = next_part.replace("_", "-")
                        break

            if not remote_book_id:
                # Fallback: use title as remote_book_id
                clean_title = re.sub(r"[^a-zA-Z0-9\s]", "", title)
                remote_book_id = clean_title.replace(" ", "-").lower()[:50]

            book_data |= {
                "source_url": page_url,
                "remote_book_id": remote_book_id,
                "crawl_timestamp": datetime.now(timezone.utc),
                "last_crawl_timestamp": datetime.now(timezone.utc),
                "status": BookStatus.SUCCESS.value,
                "html_snapshot": html,
            }

            return book_data

        except Exception:
            return None

    async def get_total_pages(self) -> int:
        """Get total number of pages to crawl"""
        try:
            page_url = f"{self.base_url}"
            html, _ = await self.get_page_with_retry(page_url)
            if not html:
                return 1

            soup = BeautifulSoup(html, "lxml")

            if pagination := soup.find(
                "li", class_="current"
            ):  # current class has the page info
                pagination_text = pagination.get_text(strip=True)
                # Split by space and get the last part which is the total pages
                parts = pagination_text.split()
                return int(parts[-1]) if parts and parts[-1].isdigit() else 1

            return 1

        except Exception:
            return 1

    async def get_book_urls_from_page(self, page_num: int) -> list[str]:
        """Get all book URLs from a specific page"""
        try:
            page_url = f"{self.base_url}/catalogue/page-{page_num}.html"
            html, _ = await self.get_page_with_retry(page_url)

            if not html:
                return []

            soup = BeautifulSoup(html, "lxml")
            book_urls = []

            # Find all book links by html tag == article & class == product_pod
            articles = soup.find_all("article", class_="product_pod")
            for article in articles:
                h3_elem = article.find("h3")
                title_link = h3_elem.find("a") if h3_elem else None
                if title_link:
                    if href := title_link.get("href"):
                        # Convert relative URL to absolute
                        book_url = urljoin(f"{self.base_url}/catalogue/", href)
                        book_urls.append(book_url)

            return book_urls

        except Exception:
            return []
