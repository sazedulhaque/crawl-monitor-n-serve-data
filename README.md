# Crawl Monitor and Serve Data

A web crawling, monitoring and data serving application built with FastAPI, MongoDB and Beanie ODM.

## Features

- Web crawling with BeautifulSoup
- Scheduled crawling tasks with APScheduler
- REST API with FastAPI
- MongoDB data storage with Beanie ODM
- Docker containerization

## Prerequisites

- Python 3.12
- Docker and Docker Compose

## Setup Instructions

1. Clone the repository:

   ```bash
   git clone https://github.com/sazedulhaque/crawl-monitor-n-serve-data.git
   cd crawl-monitor-n-serve-data
   ```

2. Create a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

5. Edit `.env` with your configuration.

6. Run with Docker Compose:

   ```bash
   docker-compose up --build
   ```

   Or run locally:

   ```bash
   uvicorn main:app --reload
   ```

## Environment Variables

Create a `.env` file based on `.env.example`:

```
MONGODB_URL=mongodb://db:27017
DATABASE_NAME=crawl_monitor
CRAWL_INTERVAL=60
```

## Dependencies

### Core Framework

- fastapi==0.115.4
- uvicorn[standard]==0.32.0
- beanie==2.0.0
- pydantic==2.9.2
- pydantic-settings==2.6.0

### Authentication & Security

- python-multipart==0.0.17
- python-jose[cryptography]==3.3.0
- pwdlib[argon2]
- argon2-cffi==23.1.0
- email-validator

### Web Scraping & HTTP

- requests
- httpx==0.27.2
- beautifulsoup4==4.12.3
- lxml==5.3.0

### Task Scheduling & Utils

- apscheduler==3.10.4
- slowapi==0.1.9
- aiofiles

### Development & Code Quality

- ruff
- black
- pre-commit

### Testing

- pytest==8.3.3
- pytest-asyncio==0.24.0
- pytest-cov==6.0.0
- pytest-mock==3.14.0

## API Testing

The API includes built-in Swagger UI documentation. When running the application:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Sample API Endpoints

- `GET /` - Health check
- `GET /api/v1/` - List all items
- `POST /api/v1/` - Create an item
- `GET /api/v1/{item_id}` - Get item by ID
- `PUT /api/v1/{item_id}` - Update item by ID
- `DELETE /api/v1/{item_id}` - Delete item by ID

## Sample MongoDB Document Structure

```json
{
  "_id": "ObjectId('...')",
  "name": "Sample Item",
  "description": "This is a sample document",
  "url": "https://example.com",
  "crawl_timestamp": "2023-09-30T12:00:00Z",
  "status_code": 200,
  "content_length": 12345
}
```

## Screenshots and Logs

### Successful Crawl Run

![Crawl Success](screenshots/crawl_success.png)

### Scheduler Logs

```
2023-09-30 12:00:00 - Scheduler started
2023-09-30 12:01:00 - Crawl task executed successfully
2023-09-30 12:02:00 - Data saved to MongoDB
```

## Development

### Code Formatting

This project uses Black for automatic code formatting. The VS Code settings are configured to format Python files on save.

#### Setup

1. Install development dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Install pre-commit hooks (recommended for maintaining code quality):

   ```bash
   pre-commit install
   ```

   This ensures code formatting and linting checks run automatically before each commit.

3. Run pre-commit manually (optional):

   ```bash
   # Run on all files
   pre-commit run --all-files

   # Run on staged files only
   pre-commit run
   ```

#### VS Code Configuration

The `.vscode/settings.json` file is configured to:

- Use Black as the Python formatter
- Format code on save
- Organize imports automatically
- Enable Ruff linting

### Running Tests

```bash
pytest apps/tests
pytest
```

## Trouble with linter, execute pre-commit manually on local machine

```shell
pre-commit run --all-files
```

### How can we check the changes

To verify that the change detection system is working correctly:

1. Modify book data directly in the MongoDB database, or use the GET and PUT API endpoints
2. **Important**: When updating a book, you must also update the `content_hash` field to reflect the content changes. Otherwise, the change detection mechanism will not recognize the modifications.

### Note of improvment

1. As it is a test base project So I try to make it simple with the given criteria. But in production level develoopment we can Follow the best practices like Dependency invertion .etc
2. Scrping has challenges like pagination, change detection but here we try to put some delay and present the crawler as a legit by using user agent in headers but there is still room for improvment.

3. I added create/update/delete API for book so we can test it properly.

4. Normally we try to put every static in a constant variable with upper caps but here we did not add it due to time limit.

5. We can improve the rate limiter more robust by using a middleware for applying global limits.

6. In user registration normally i put password & reconfirm password field. Here I escaped it;

7. We also used MD5 hash for content hasing as this hash is for comparing not for security purpose.

## We can get daily change report in

`http://localhost:8001/api/v1/books/changes/recent?page=1&size=50`

### Sample:

```json
[
  {
    "_id": "68e2732809965e46fd391304",
    "created_at": "2025-10-05T13:31:20.854000",
    "updated_at": "2025-10-05T13:31:20.854000",
    "book": {
      "id": "68e2717bdc898bab9b1a6b97",
      "collection": "books"
    },
    "change_type": "updated",
    "field_changed": "in_stock",
    "old_value": "True",
    "new_value": "False",
    "changes": {
      "in_stock": {
        "old": "True",
        "new": "False"
      }
    },
    "description": "in_stock updated from True to False",
    "crawl_session_id": null
  },
  {
    "_id": "68e27b1909965e46fd391308",
    "created_at": "2025-10-05T14:05:13.836000",
    "updated_at": "2025-10-05T14:05:13.836000",
    "book": {
      "id": "68e2717bdc898bab9b1a6b97",
      "collection": "books"
    },
    "change_type": "updated",
    "field_changed": null,
    "old_value": null,
    "new_value": null,
    "changes": {
      "title": {
        "old": "Penny Maybe Gone",
        "new": "Penny Maybe"
      },
      "in_stock": {
        "old": false,
        "new": true
      },
      "rating": {
        "old": 4,
        "new": 3
      },
      "reviews_count": {
        "old": 1,
        "new": 0
      }
    },
    "description": "Updated 4 field(s) during crawl",
    "crawl_session_id": "0e0c63aa-5bd9-466e-aa6a-66031ac56cbc"
  }
]
```

## We can get session data in

`http://localhost:8001/api/v1/books/session/data?page=1&size=50`

### Sample:

```json
[
  {
    "_id": "68e27aff09965e46fd391307",
    "created_at": "2025-10-05T14:04:47.332000",
    "updated_at": "2025-10-05T14:14:19.773000",
    "session_id": "0e0c63aa-5bd9-466e-aa6a-66031ac56cbc",
    "status": "running",
    "started_by": null,
    "total_pages": 50,
    "processed_pages": 48,
    "new_books": 0,
    "updated_books": 1,
    "failed_books": 0,
    "last_processed_url": null,
    "error_message": null,
    "completed_at": null
  },
  {
    "_id": "68e27163dc898bab9b1a6b65",
    "created_at": "2025-10-05T13:23:47.184000",
    "updated_at": "2025-10-05T13:33:40.930000",
    "session_id": "ddb19f48-d5e4-49f3-a041-c4cf8bc82a5c",
    "status": "completed",
    "started_by": null,
    "total_pages": 50,
    "processed_pages": 50,
    "new_books": 1000,
    "updated_books": 0,
    "failed_books": 0,
    "last_processed_url": null,
    "error_message": null,
    "completed_at": "2025-10-05T13:33:40.930000"
  }
]
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
